"""Tiny ``.env`` loader (no dependency): KEY=VALUE lines, ``#`` comments, optional quotes.

Looks in the current directory and its parents, then in the project root. Variables that
are already set in the environment win, so ``LLM_API_KEY=... ./interact`` still works.

Recognised variables:
    LLM_ENDPOINT    OpenAI-compatible base URL (".../v1") or full ".../chat/completions" URL
    LLM_API_KEY     bearer token for that endpoint
    LLM_MODEL       model name to send (default "gpt-4o-mini")
    OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL are accepted as fallbacks for the three above
    INDIAMACRO_DEMO set to 1 to use simulated data for every live feed (offline demos)
"""

from __future__ import annotations

import os
from pathlib import Path

_loaded: Path | None = None


def _candidates() -> list[Path]:
    here = Path.cwd().resolve()
    out = [d / ".env" for d in (here, *here.parents)]
    out.append(Path(__file__).resolve().parents[3] / ".env")   # repo root when installed editable
    return out


def load(path: str | Path | None = None) -> Path | None:
    global _loaded
    files = [Path(path)] if path else _candidates()
    for f in files:
        if f.is_file():
            for line in f.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.removeprefix("export ").partition("=")
                key, val = key.strip(), val.strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
                    val = val[1:-1]
                elif " #" in val:
                    val = val.split(" #", 1)[0].strip()
                os.environ.setdefault(key, val)
            _loaded = f
            return f
    return None


def get(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def demo() -> bool:
    return get("INDIAMACRO_DEMO").lower() in ("1", "true", "yes", "on")


load()
