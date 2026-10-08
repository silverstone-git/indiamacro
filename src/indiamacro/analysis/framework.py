"""The story framework: a story is a page of charts + numbers + explanation.

    @story("oil_prices", "Oil prices", section="Energy", question="...")
    def _(s: Builder):
        s.chart(lambda: charts.line(...), width="half")
        s.insight("Brent is ...")

Charts are registered as callables and computed in parallel when the story runs, so
one slow or broken source doesn't hold up (or break) the rest of the page.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from . import charts


@dataclass
class Param:
    name: str
    label: str
    type: str = "select"            # select | text | number
    default: Any = None
    options: list = field(default_factory=list)   # [(value, label)]
    help: str = ""

    def coerce(self, raw):
        if raw is None or raw == "":
            return self.default
        if self.type == "number":
            return int(float(raw))
        return str(raw)

    def to_json(self) -> dict:
        return {"name": self.name, "label": self.label, "type": self.type, "default": self.default,
                "options": [{"value": v, "label": l} for v, l in self.options], "help": self.help}


@dataclass
class StoryDef:
    id: str
    title: str
    section: str
    question: str
    fn: Callable
    params: list[Param] = field(default_factory=list)
    method: str = ""
    caveats: list[str] = field(default_factory=list)
    kind: str = "story"             # story | template (analysis templates get their own nav group)


STORIES: dict[str, StoryDef] = {}


def story(id: str, title: str, section: str, question: str, params: list[Param] | None = None,
          method: str = "", caveats: list[str] | None = None, kind: str = "story"):
    def register(fn):
        STORIES[id] = StoryDef(id, title, section, question, fn, params or [], method, caveats or [], kind)
        return fn
    return register


class Builder:
    def __init__(self, params: dict):
        self.p = params
        self._blocks: list[tuple[str, Any, str, str]] = []   # (kind, payload, width, title)
        self._insights: list[tuple[int, str]] = []
        self._lock = threading.Lock()

    def chart(self, fn: Callable[[], dict], width: str = "full", title: str = "") -> None:
        """Register a chart (computed later, in parallel). ``width``: full | half | third."""
        self._blocks.append(("chart", fn, width, title))

    def text(self, markdown: str) -> None:
        self._blocks.append(("text", markdown, "full", ""))

    def insight(self, text: str, order: int = 50) -> None:
        """A finding computed from the data; shown at the top of the page."""
        with self._lock:
            self._insights.append((order, text))


_pool = ThreadPoolExecutor(max_workers=8)


def run(story_id: str, raw_params: dict | None = None) -> dict:
    d = STORIES[story_id]
    params = {p.name: p.coerce((raw_params or {}).get(p.name)) for p in d.params}
    b = Builder(params)
    t0 = time.perf_counter()
    d.fn(b)

    def compute(block):
        kind, payload, width, title = block
        if kind == "text":
            return {"kind": "text", "markdown": payload, "width": width}
        try:
            spec = payload()
        except Exception as e:  # show the failure in place of the chart
            spec = charts.error(title or "Chart unavailable", e)
        spec["width"] = width
        return spec

    blocks = list(_pool.map(compute, b._blocks))
    return {
        "id": d.id, "title": d.title, "section": d.section, "question": d.question,
        "params": [p.to_json() for p in d.params], "values": params,
        "insights": [t for _, t in sorted(b._insights, key=lambda x: x[0])],
        "blocks": blocks, "method": d.method, "caveats": d.caveats,
        "seconds": round(time.perf_counter() - t0, 1),
    }


def catalog() -> list[dict]:
    return [{"id": d.id, "title": d.title, "section": d.section, "question": d.question, "kind": d.kind}
            for d in STORIES.values()]


# ---------------------------------------------------------------- small in-memory memo

_memo: dict = {}
_memo_lock = threading.Lock()


def memo(ttl: float = 900):
    """Cache a zero/hashable-arg function's result in memory for ``ttl`` seconds."""
    def wrap(fn):
        def inner(*args):
            key = (fn.__module__, fn.__name__, args)
            with _memo_lock:
                hit = _memo.get(key)
            if hit and time.time() - hit[0] < ttl:
                return hit[1]
            value = fn(*args)
            with _memo_lock:
                _memo[key] = (time.time(), value)
            return value
        inner.__name__ = fn.__name__
        return inner
    return wrap
