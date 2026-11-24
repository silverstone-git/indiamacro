# Architecture

## Layers

```
                        ┌──────────────────────── browser ────────────────────────┐
                        │  index.html + app.js        terminal.html + terminal.js │
                        │  (dashboard, Plotly)        (Leaflet, satellite.js,     │
                        │                              Plotly)                    │
                        └──────────────┬────────────────────────┬─────────────────┘
                              relative URLs: api/...    static/...
                                       │                        │
   production only:  Cloudflare ─► nginx (basic auth) ─► /var/www/indiamacro (static)
                                       │                 /indiamacro/api/ ─► 127.0.0.1:8765
                                       ▼
   web/server.py  (stdlib ThreadingHTTPServer; routes in Handler.do_GET/do_POST/do_DELETE)
        │                      │                               │
        │ /api/story/<id>      │ /api/live/<feed>              │ /api/ask, /api/tool
        ▼                      ▼                               ▼
   analysis/                monitor/feeds.py               monitor/assistant.py ─► LLM endpoint
     framework.run()          envelope + sim fallback          (OpenAI-compatible, optional)
     stories_*.py             (in-memory TTL cache)            monitor/query.py (tools)
     data.py (@memo)                │                               │
        │                           │                               │
        └──────────────┬────────────┴───────────────┬───────────────┘
                       ▼                            ▼
             india.py, compare.py            sources/*.py  (one module per provider)
                       │                            │
                       └──────────────┬─────────────┘
                                      ▼
                         _http.py (requests session, retries, disk cache)
                         + yfinance (wrapped by energy._yahoo_close / feeds._quotes_live)
```

## Modules and their single job

| Module | Job | Notes |
|---|---|---|
| `_http.py` | Every HTTP GET/POST, retries, on-disk cache (`~/.cache/indiamacro/<host>/<sha>`), `SourceError`, `settings` | Per-host TLS quirk for MoSPI. Keep the stock python-requests User-Agent. |
| `utils.py` | Fiscal-year and period parsing, `wide`, `yoy`, `rebase`, `deflate`, `cagr` | Use these; never hand-roll date logic. |
| `countries.py` | Name/ISO2/ISO3 lookup, groups (BRICS, G7, G20, SOUTH_ASIA, ASEAN, EM_ASIA, QUAD), `expand()` puts India first | BRICS here is the original five. |
| `sources/*.py` | One provider each, tidy long DataFrames | mospi, budget, fred, worldbank, imf, oecd, bis, pwt, owid, energy |
| `india.py` | Headline India series as `pd.Series` with `attrs` {source, unit, note}; `snapshot()` | Used by dashboard tiles, terminal INDIA MACRO panel, query registry |
| `compare.py` | `compare(indicator, countries)`: date × country table, IMF by default, World Bank fallback | `INDICATORS` maps friendly names to codes |
| `ping.py` | `CHECKS` list = health check CLI = live test parametrisation | Includes terminal feeds (sim fallback counts as failure) |
| `analysis/framework.py` | `@story` registry, `Builder`, `Param`, `run()`, `catalog()`, `memo()` | Charts are lambdas run in a thread pool; failures become error cards |
| `analysis/charts.py` | Dashboard chart-spec builders (`line`, `bar`, `scatter`, `table`, `kpi(s)`, `error`) | Different spec format from the terminal's charts, see DATA_MODEL.md |
| `analysis/data.py` | `@memo`'d loaders shared by pages (and by `monitor/query.py`) | 15-min in-memory memo on top of the disk cache |
| `analysis/events.py` | Built-in + user events, `event_study()` | User events in `~/.local/share/indiamacro/events.json` |
| `analysis/stories_*.py` | Dashboard pages | Imported by `analysis/__init__.py` to register |
| `monitor/env.py` | Loads `.env` at import; `get()`, `demo()` | Existing environment variables win over `.env` |
| `monitor/feeds.py` | Live feeds → envelopes `{status: live|sim, ...}` with in-memory TTL | Simulated fallback on any exception |
| `monitor/sim.py` | Labelled fake data for every feed and series | Deterministic-ish (seeded) so screens are stable |
| `monitor/query.py` | `SERIES` registry + analyst tools (`get_series`, `correlate`, `compare_countries`, `window`, `live_snapshot`, `list_series`) and their JSON schemas (`TOOLS`) | All numbers in answers come from here |
| `monitor/assistant.py` | `ask()`: LLM tool loop, grounded fallback, or rule-based mock; `plan()` keyword planner | Reads LLM_* / OPENAI_* env vars |
| `monitor/fake_llm.py` | Fake OpenAI-compatible server for tests/dev | Uses `plan()` to emit tool calls |
| `web/server.py` | Routes, JSON encoding (`_clean` turns NaN/inf into null), story cache, ask rate limit | Stdlib only, no framework |
| `web/static/` | Front ends; no build step | CDN libraries: Plotly 2.35.2, Leaflet 1.9.4, satellite.js 5.0.0 |

## Request lifecycles

### Dashboard page (`GET /api/story/<id>?param=...`)
1. `server._story()` checks a 10-minute in-memory page cache keyed on (id, params).
2. `framework.run()` coerces params, calls the story function with a `Builder`.
3. The story registers chart lambdas and insights; lambdas run in a pool of 8 threads.
4. Each lambda calls `analysis/data.py` loaders (`@memo`, 15 min) → `india`/`sources` → `_http` (disk cache, 1 day default).
5. A lambda that raises becomes `charts.error(...)`; the rest of the page still renders.
6. `_clean()` converts NaN/inf to null; app.js renders specs with Plotly.

### Terminal feed (`GET /api/live/quakes`)
1. `feeds.quakes()` → `_envelope(feed, source, ttl, live, fallback)`.
2. In-memory hit younger than `ttl` → returned as is.
3. Else `live()` runs (through `_http` with its own short disk ttl). On exception, or when
   `INDIAMACRO_DEMO=1`, `fallback()` (from `sim.py`) runs and the envelope says `status: "sim"` with the
   error in `note`. Failed results are re-tried after 60 s instead of the full ttl.
4. terminal.js shows LIVE/SIM/ERR on the panel badge (hover = source, time, note).

### Analyst question (`POST /api/ask {question, history, context}`)
1. Per-IP rate limit (`INDIAMACRO_ASK_PER_HOUR`, default 30).
2. `assistant.ask()`:
   - **No endpoint configured → mock:** `plan(question)` picks tool calls by keyword rules,
     `_run()` executes them, `_mock_writeup()` templates an answer from the computed stats.
   - **Endpoint configured → LLM:** up to 5 rounds of chat completions with `tools`; each tool call runs
     `query.call()` and its `text` goes back as a `tool` message. Charts are collected from all results.
   - **LLM error → grounded:** the planner runs tools, the LLM (if reachable) writes from their text
     without function calling; if even that fails, the mock write-up is returned with the error.
3. Response: `{answer, charts, tools, sources, sim, mode, model, endpoint_host, elapsed, error}`.

### Terminal command (`POST /api/tool {name, args}`)
Same tools as the analyst, no LLM: `G`, `CORR`, `CMP`, `WIN`, `LIST` in the command bar map onto it.

## Caching, all layers

| Layer | Where | TTL | Clear with |
|---|---|---|---|
| HTTP disk cache | `~/.cache/indiamacro/<host>/` (`INDIAMACRO_CACHE`) | per call: default 1 day; PWT/Natural Earth forever; feeds 20 s–6 h; Yahoo CSVs 6 h | `im.clear_cache()`, dashboard "Re-download data", `POST /api/refresh {"hard":true}` |
| `@memo` loaders | process memory | 15 min (some 1 h) | `POST /api/refresh` |
| Story pages | process memory (`server._cache`) | 10 min | `POST /api/refresh` |
| Feed envelopes | process memory (`feeds._mem`) | per feed; sim results 60 s | `POST /api/refresh`, `feeds.clear()` |
| Browser | `Cache-Control: no-store` on API; nginx `no-cache` on static | – | hard reload |

Disable all disk caching with `INDIAMACRO_NO_CACHE=1` or `im.settings.cache = False`.

## Process model

- One Python process, `ThreadingHTTPServer` with daemon threads. All caches are process-local, so two
  server instances don't share memory caches (they do share the disk cache).
- Production: systemd unit `indiamacro-web` runs `uv run indiamacro-web --host 127.0.0.1 --port 8765`
  from the repo checkout, so it uses this repo's `.env` and whatever branch is checked out.
- Long LLM answers block one thread each (fine at this scale). nginx allows 300 s on the API.

## External front-end dependencies (CDN, need internet)

Plotly (jsdelivr), Leaflet (unpkg), satellite.js (jsdelivr), Google Fonts, Esri basemap tiles,
NASA GIBS imagery tiles. The geometry for the ECON choropleth is Natural Earth 1:110m, fetched by the
server once from GitHub and cached forever.
