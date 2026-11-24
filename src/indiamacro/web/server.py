"""Local web app: ``indiamacro-web`` (or ``./interact``) serves the dashboard and opens a browser tab.

Standard library only. The browser asks ``/api/story/<id>`` for a page; the server runs
the story (fetching and caching data as needed) and returns charts as JSON, which the
front end draws with Plotly.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import threading
import time
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from .. import _http
from ..analysis import catalog, events, framework, run
from ..monitor import assistant, feeds
from ..monitor import query as mquery

STATIC = Path(__file__).parent / "static"
TYPES = {".geojson": "application/geo+json", ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".ico": "image/x-icon"}
SECTIONS = ["Overview", "India", "Energy", "Shocks", "Trends", "Tools"]

_cache: dict = {}
_cache_lock = threading.Lock()
STORY_TTL = 600

# The analyst spends the owner's LLM credits, and the server may sit behind a public proxy:
# cap questions per client IP per hour (INDIAMACRO_ASK_PER_HOUR, default 30; 0 = unlimited).
ASK_PER_HOUR = int(os.environ.get("INDIAMACRO_ASK_PER_HOUR", "30"))
_asks: dict[str, list[float]] = {}
_asks_lock = threading.Lock()


def _ask_allowed(ip: str) -> bool:
    if ASK_PER_HOUR <= 0:
        return True
    now = time.time()
    with _asks_lock:
        recent = [t for t in _asks.get(ip, []) if now - t < 3600]
        if len(recent) >= ASK_PER_HOUR:
            _asks[ip] = recent
            return False
        _asks[ip] = recent + [now]
        return True


def _story(story_id: str, params: dict) -> dict:
    key = (story_id, tuple(sorted(params.items())))
    with _cache_lock:
        hit = _cache.get(key)
    if hit and time.time() - hit[0] < STORY_TTL:
        return hit[1]
    result = run(story_id, params)
    with _cache_lock:
        _cache[key] = (time.time(), result)
    return result


def _clean(obj):
    """Replace NaN/inf (which JSON can't carry) with null, recursively."""
    if isinstance(obj, float):
        return obj if obj == obj and obj not in (float("inf"), float("-inf")) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return obj


def _clear_memory() -> None:
    with _cache_lock:
        _cache.clear()
    with framework._memo_lock:
        framework._memo.clear()


class Handler(BaseHTTPRequestHandler):
    server_version = "indiamacro"

    def log_message(self, format, *args):  # quieter console: only API calls and errors
        if "/api/" in str(args[0] if args else "") or (len(args) > 1 and str(args[1])[:1] in "45"):
            sys.stderr.write(f"  {format % args}\n")

    # ------------------------------------------------------------ helpers
    def _send(self, status: int, body: bytes, ctype: str = "application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status: int = 200):
        self._send(status, json.dumps(_clean(obj), default=str, allow_nan=False).encode())

    def _error(self, status: int, message: str):
        self._json({"error": message}, status)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    # ------------------------------------------------------------ routes
    def do_GET(self):
        url = urlsplit(self.path)
        path, query = url.path, dict(parse_qsl(url.query))
        try:
            if path in ("/", "/index.html"):
                return self._static("index.html")
            if path.startswith("/static/"):
                return self._static(path.removeprefix("/static/"))
            if path in ("/terminal", "/terminal.html"):
                return self._static("terminal.html")
            if path.startswith("/api/live/"):
                return self._live(path.removeprefix("/api/live/"), query)
            if path == "/api/ask/status":
                return self._json(assistant.status())
            if path == "/api/series":
                return self._json({"series": [{"key": k, "label": s.label, "unit": s.unit, "source": s.source,
                                               "aliases": s.aliases} for k, s in mquery.SERIES.items()],
                                   "transforms": mquery.TRANSFORMS})
            if path == "/api/catalog":
                return self._json({"sections": SECTIONS, "stories": catalog(),
                                   "categories": events.CATEGORIES})
            if path.startswith("/api/story/"):
                story_id = path.removeprefix("/api/story/")
                if story_id not in framework.STORIES:
                    return self._error(404, f"no such page: {story_id}")
                return self._json(_story(story_id, query))
            if path == "/api/events":
                df = events.load()
                df["date"] = df["date"].dt.strftime("%Y-%m-%d")
                return self._json({"events": df.to_dict("records"), "categories": events.CATEGORIES,
                                   "file": str(events.USER_FILE)})
            return self._error(404, "not found")
        except Exception as e:
            traceback.print_exc()
            return self._error(500, f"{type(e).__name__}: {e}")

    def do_POST(self):
        path = urlsplit(self.path).path
        try:
            if path == "/api/events":
                b = self._body()
                ev = events.add(b["date"], b["label"], b["category"], b.get("region", ""))
                _clear_memory()
                return self._json(ev, 201)
            if path == "/api/ask":
                b = self._body()
                q = str(b.get("question", "")).strip()[:2000]
                if not q:
                    return self._error(400, "empty question")
                ip = self.headers.get("X-Real-IP") or self.client_address[0]
                if not _ask_allowed(ip):
                    return self._error(429, f"limit of {ASK_PER_HOUR} questions per hour reached; commands "
                                            "(G, CORR, CMP, WIN) still work without the AI")
                return self._json(assistant.ask(q, b.get("history") or [], str(b.get("context", ""))[:2000]))
            if path == "/api/tool":
                b = self._body()
                if b.get("name") not in mquery.TOOLS:
                    return self._error(400, f"unknown tool; choose from {list(mquery.TOOLS)}")
                return self._json(mquery.call(b["name"], dict(b.get("args") or {})))
            if path == "/api/refresh":
                hard = self._body().get("hard", False)
                _clear_memory()
                feeds.clear()
                if hard:
                    _http.clear_cache()
                return self._json({"ok": True, "hard": hard})
            return self._error(404, "not found")
        except (KeyError, ValueError, TypeError) as e:
            return self._error(400, str(e))
        except Exception as e:
            traceback.print_exc()
            return self._error(500, f"{type(e).__name__}: {e}")

    def do_DELETE(self):
        path = urlsplit(self.path).path
        if path.startswith("/api/events/"):
            ok = events.remove(path.removeprefix("/api/events/"))
            _clear_memory()
            return self._json({"removed": ok}, 200 if ok else 404)
        return self._error(404, "not found")

    def _live(self, feed: str, q: dict):
        if feed == "world.geojson":
            return self._send(200, feeds.world_geojson(), "application/geo+json")
        simple = {"quotes": feeds.quotes, "quakes": feeds.quakes, "events": feeds.natural_events,
                  "weather": feeds.weather, "chokepoints": feeds.chokepoints, "india": feeds.india_snapshot}
        if feed in simple:
            return self._json(simple[feed]())
        if feed == "aircraft":
            bbox = tuple(float(x) for x in q.get("bbox", "").split(",")) if q.get("bbox") else feeds.INDIA_BBOX
            if len(bbox) != 4:
                return self._error(400, "bbox=lamin,lomin,lamax,lomax")
            return self._json(feeds.aircraft(bbox))
        if feed == "satellites":
            return self._json(feeds.satellites(q.get("group", "gnss")))
        if feed == "econ":
            return self._json(feeds.econ_map(q.get("indicator", "NGDP_RPCH"), q.get("year") or None))
        return self._error(404, f"no live feed {feed!r}")

    def _static(self, name: str):
        f = (STATIC / name).resolve()
        if STATIC.resolve() not in f.parents or not f.is_file():
            return self._error(404, "not found")
        self._send(200, f.read_bytes(), TYPES.get(f.suffix, "application/octet-stream"))


def _free_port(host: str, preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket() as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port found")


def _warm_up():
    """Fetch the overview in the background so the first page loads fast."""
    try:
        _story("overview", {})
    except Exception:
        traceback.print_exc()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="indiamacro dashboard")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 to allow other devices on your network")
    ap.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = ap.parse_args(argv)

    port = _free_port(args.host, args.port)
    httpd = ThreadingHTTPServer((args.host, port), Handler)
    httpd.daemon_threads = True
    url = f"http://{'localhost' if args.host in ('127.0.0.1', '0.0.0.0') else args.host}:{port}/"
    print(f"indiamacro dashboard running at {url}  (Ctrl+C to stop)")
    print(f"data cache: {_http.CACHE_DIR}   your events: {events.USER_FILE}")
    threading.Thread(target=_warm_up, daemon=True).start()
    if not args.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
