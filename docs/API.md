# HTTP API (`web/server.py`)

Stdlib `ThreadingHTTPServer`. JSON in and out (`Content-Type: application/json`), `Cache-Control:
no-store`. NaN/inf become `null`. Errors: `{"error": "..."}` with 400 (bad input), 404, 429 (ask
limit) or 500 (traceback printed to the server log).

Production prefix: `https://t.aryan.cfd/indiamacro/` (HTTP basic auth). nginx maps
`/indiamacro/api/*` → `http://127.0.0.1:8765/api/*`; static files are served by nginx from
`/var/www/indiamacro`, not by Python.

## Pages and static

| Method | Path | Returns |
|---|---|---|
| GET | `/`, `/index.html` | dashboard |
| GET | `/terminal`, `/terminal.html` | terminal |
| GET | `/static/<file>` | files from `web/static/` (path traversal is refused) |

## Dashboard

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET | `/api/catalog` | | `{sections, stories: [{id, title, section, question, kind}], categories}` |
| GET | `/api/story/<id>` | page params as query string | `framework.run()` result: `{id, title, ..., insights, blocks, method, caveats, seconds}` |
| GET | `/api/events` | | `{events: [...], categories, file}` |
| POST | `/api/events` | `{date, label, category, region?}` | the new event, 201 |
| DELETE | `/api/events/<id>` | | `{removed: bool}` |
| POST | `/api/refresh` | `{hard?: bool}` | clears memory caches and feed envelopes; `hard` also deletes the disk cache |

## Terminal

| Method | Path | Query / body | Returns |
|---|---|---|---|
| GET | `/api/live/quotes` | | envelope (TERMINAL.md lists every feed's rows) |
| GET | `/api/live/india` | | envelope |
| GET | `/api/live/quakes` | | envelope |
| GET | `/api/live/events` | | envelope |
| GET | `/api/live/weather` | | envelope |
| GET | `/api/live/chokepoints` | | envelope |
| GET | `/api/live/aircraft` | `bbox=lamin,lomin,lamax,lomax` (default India) | envelope |
| GET | `/api/live/satellites` | `group=gnss\|stations\|military` | envelope (400 for another group) |
| GET | `/api/live/econ` | `indicator=NGDP_RPCH` (IMF WEO code), `year=` | envelope |
| GET | `/api/live/world.geojson` | | GeoJSON |
| GET | `/api/series` | | `{series: [{key, label, unit, source, aliases}], transforms}` |
| GET | `/api/ask/status` | | `{mode: "llm"\|"mock", model, endpoint_host}` |
| POST | `/api/ask` | `{question, history?: [{role, content}], context?: str}` | `{answer, charts, tools, sources, sim, mode, model, endpoint_host, elapsed, error}`; 429 past `INDIAMACRO_ASK_PER_HOUR` per IP (`X-Real-IP` from nginx, else socket address) |
| POST | `/api/tool` | `{name, args}`; name ∈ `list_series, get_series, correlate, compare_countries, window, live_snapshot` | tool result `{text, charts, sources, sim, stats?}` |

### Tool arguments (`query.TOOLS`, also sent to the LLM as JSON Schema)

| Tool | Args |
|---|---|
| `get_series` | `names: [str]` (≤6, keys or aliases), `start?: "YYYY-MM-DD"`, `transform?: level\|yoy\|pct\|diff\|log\|zscore\|index100`, `freq?: D\|W\|M\|Q\|A` |
| `correlate` | `a, b`, `freq?: W\|M\|Q\|A` (default M), `transform?: auto\|...` (auto = diff for % series, yoy otherwise), `max_lag?: int` (12), `start?` |
| `compare_countries` | `indicator` (key of `compare.INDICATORS` or a raw code), `countries?` (group or "IND,CHN"), `start?: int` |
| `window` | `series, date`, `before?: days` (30), `after?: days` (60) |
| `live_snapshot`, `list_series` | none |

## Examples

```bash
B=http://localhost:8765
curl -s $B/api/live/quakes | jq '.status, (.data | length)'
curl -s -X POST $B/api/tool -d '{"name":"correlate","args":{"a":"brent","b":"usdinr"}}' | jq -r .text
curl -s -X POST $B/api/ask -d '{"question":"what is happening right now?"}' | jq -r '.mode, .answer'
# production (password from .env via a netrc on a pipe; never put it on the command line)
curl -s --netrc-file <(uv run --quiet python -c 'from indiamacro.monitor import env; print("machine t.aryan.cfd login", env.get("INDIAMACRO_USERNAME"), "password", env.get("INDIAMACRO_KEY"))') \
  https://t.aryan.cfd/indiamacro/api/ask/status
```
