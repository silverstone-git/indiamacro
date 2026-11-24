# Debugging

Start from the symptom table, then use the toolbox below.

## Symptom → first thing to check

| Symptom | Likely cause | Check / fix |
|---|---|---|
| A dashboard chart shows an error card | that source failed or changed format | Message on the card; `uv run indiamacro-ping`; rerun the loader in Python (below) |
| A terminal panel shows **SIM** | its live source raised | Hover the badge (the `note` holds the exception); `curl .../api/live/<feed> \| jq .note`; server log has the traceback |
| Everything SIM | `INDIAMACRO_DEMO=1` set, or no internet | `env \| grep INDIAMACRO`; `curl -sI https://earthquake.usgs.gov` |
| Badge **ERR** | the API request itself failed (server down, 500, 401) | browser devtools network tab; `curl` the route |
| 502 at t.aryan.cfd/indiamacro/api | service down or on the wrong port | `systemctl status indiamacro-web`; `ss -ltnp \| grep indiamacro` (must be 8765); PITFALLS #28 |
| 401 | basic auth | expected without the password; credentials come from `.env` (DEPLOYMENT.md) |
| AI pill says MOCK | no `LLM_ENDPOINT`/`OPENAI_*` seen by the process | `curl .../api/ask/status`; restart after editing `.env`; env vars override `.env` |
| Answer has "LLM unavailable" or mode `llm-grounded` | endpoint error or no function calling | the `error` field in the `/api/ask` response; model name (`GET {base}/models`) |
| `Invalid model name passed in model=...` | proxy doesn't serve that alias | set `OPENAI_MODEL` / `LLM_MODEL` (production uses `heavy-tool`) |
| Map empty / watermarked | tile provider issue | Esri tiles reachable? GIBS date has data? (PITFALLS #11) |
| Night shading invisible | renderer/pane issue or colour | PITFALLS #9, #10 |
| No aircraft | OpenSky quota or outage | `curl '.../api/live/aircraft' \| jq .status,.note` |
| Satellites missing in MIL | a name query failed or 404 | `feeds._sats_live("military")` in Python; CelesTrak status |
| Stale numbers | caches | `POST /api/refresh` (memory), `{"hard": true}` (disk); see the cache table in ARCHITECTURE.md |
| Page works locally, broken under /indiamacro/ | an absolute URL | `grep -n '"/api\|"/static' src/indiamacro/web/static/*` (PITFALLS #12) |

## Toolbox

### Run things directly in Python

```bash
uv run python -c "from indiamacro import india; s = india.cpi_inflation(); print(s.tail(), s.attrs)"
uv run python -c "from indiamacro.monitor import feeds; e = feeds.quakes(); print(e['status'], e['note'], len(e['data']))"
uv run python -c "from indiamacro.monitor import query; print(query.correlate('brent', 'usdinr')['text'])"
uv run python -c "from indiamacro.monitor import assistant as a; print(a.plan('did oil drive the rupee since 2015?'))"
uv run python -c "from indiamacro.analysis import run; r = run('overview'); print([b.get('kind') for b in r['blocks']])"
INDIAMACRO_NO_CACHE=1 uv run python -c "..."     # bypass the disk cache for one run
INDIAMACRO_DEMO=1 uv run indiamacro-web --port 8780 --no-browser   # whole UI on simulated data (offline)
```

`_envelope` swallows exceptions (prints the traceback to stderr) and returns sim. To see the raw error,
call the private live function: `feeds._quotes_live()`, `feeds._quakes_live()`, `feeds._sats_live("gnss")`,
`feeds._weather_live()`, `feeds._choke_live()`, `feeds._events_live()`.

### Health check of every source and feed

```bash
uv run indiamacro-ping              # table; --fresh bypasses cache; --markdown docs/SOURCE_STATUS.md writes the report
uv run pytest -m live -k "USGS or CelesTrak"
```

### Local server

```bash
./interact --no-browser --port 8780          # or: uv run indiamacro-web --no-browser --port 8780
# the port moves to the next free one if taken; read the "running at" line
curl -s localhost:8780/api/ask/status
```

Don't kill a server you didn't start: port 8765 is production (systemd). Use another port for experiments.

### Production

```bash
systemctl status indiamacro-web
sudo journalctl -u indiamacro-web -n 100 --no-pager      # API access log + tracebacks
ss -ltnp | grep indiamacro                                # expect 127.0.0.1:8765
sudo nginx -t; sudo tail -n 50 /var/log/nginx/error.log
```

### The LLM endpoint

```bash
uv run python - <<'EOF'
import requests
from indiamacro.monitor import assistant as a
print(a.status())
base = a._endpoint().rstrip("/").removesuffix("/chat/completions")
print([m["id"] for m in requests.get(base + "/models", headers={"Authorization": "Bearer " + a._key()}).json()["data"]])
print(a._chat([{"role": "user", "content": "Reply with: ok"}], tools=False)["choices"][0]["message"]["content"])
EOF
```

Fake endpoint for testing the tool loop without a key:
`uv run python -m indiamacro.monitor.fake_llm` and `LLM_ENDPOINT=http://127.0.0.1:8799/v1 LLM_API_KEY=x`.

### Front end

- Screenshots and console/network errors at four sizes: `scripts/screenshots.py` (TESTING.md).
- In a page (devtools or Playwright `page.evaluate`), the global `S` holds all state:
  `S.mode`, `S.feeds.quakes.status`, `S.sats.length`, `S.layers.night.getLayers().length`,
  `S.map.getPane('night')`. `setMode('gnss')`, `ask('...')`, `runCommand('CORR brent usdinr')` drive it.
- Syntax check after editing JS: `node --check src/indiamacro/web/static/terminal.js`.
- To test a pure function from terminal.js in Node (e.g. `sunMoon`, `nightPolygon`, `md`), extract it by
  name from the source and `eval` it; there is no module system. See `TESTING.md`.

### Caches on disk

`~/.cache/indiamacro/<host>/<sha256-prefix>`: raw response bodies. Find one source's files with
`ls -lt ~/.cache/indiamacro/celestrak.org/`. Delete a host's directory to force a refetch of just that
source.
