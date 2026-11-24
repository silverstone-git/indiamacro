# Testing

## Suites

| Command | What | Time | Network |
|---|---|---|---|
| `uv run pytest` | offline tests (`addopts = -m 'not live'`) | ~2 s | none (must stay that way) |
| `uv run pytest -m live` | every `ping.CHECKS` entry + India headline series + compare + every dashboard page renders | minutes | yes |
| `uv run indiamacro-ping` | same checks as a table | < 1 min warm | yes |
| `scripts/screenshots.py` | UI at phone/tablet/laptop/desktop; JS errors, failed requests, overflow | ~1 min | needs a running server |

## Files

| File | Covers |
|---|---|
| `tests/test_offline.py` | date helpers, number cleaning, `yoy`/`rebase`/`cagr`, country lookup and groups, MoSPI pagination/errors (monkeypatched `_http.get_json`), revision handling, disk cache round trip |
| `tests/test_analysis.py` | event study maths (planted jumps), events store, story framework (error cards), chart specs, server helpers |
| `tests/test_monitor.py` | terminal: `.env` parsing, OPENAI_* fallbacks, alias matching, planner choices, transforms, correlation finds a planted lead, no dual axes, mock answer labelled, feeds fall back to labelled SIM, TLE parsing, EONET centroids, full LLM tool loop against `fake_llm` on a random port |
| `tests/test_live.py` | network checks (marked `live`) |

## Patterns

- **No network offline.** Monkeypatch `_http.get_json` / `_http.get` / `_http.session` with canned payloads,
  or (terminal) rely on the `demo_mode` autouse fixture in `test_monitor.py`: it sets `INDIAMACRO_DEMO=1`,
  removes all LLM variables and clears feed caches, so every loader returns labelled simulated data.
- **Planted signals.** Test maths by constructing data with a known answer (a series that jumps 5 % on
  event dates; `b = a.shift(3)` for a 3-month lead) and asserting the method recovers it.
- **Registry injection.** `monkeypatch.setitem(query.SERIES, "ta", query.Spec(...))` adds a temporary series.
- **JSON-safety.** Anything returned by the server must survive `json.dumps` (test does this for `ask`).
- **Fake LLM.** `ThreadingHTTPServer(("127.0.0.1", 0), fake_llm.Handler)` in a thread, point
  `LLM_ENDPOINT` at it, call `assistant.ask()`, assert tools/charts/mode.
- **Adding a source** adds a live test automatically through `ping.CHECKS`.

## UI verification with screenshots

```bash
./interact --no-browser --port 8780 &                      # or test production with --prod
uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py --url http://localhost:8780
uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py --prod --sizes phone,desktop \
    --modes econ,mil --ask "how does oil relate to the rupee?" --out /tmp/shots
```

Then look at the PNGs (an agent can read images). The script prints per size: badge states, elements
overflowing horizontally (ignoring clipped/scrolling containers), JS errors, failed requests; exit 1 on
errors. Things screenshots have caught so far: watermarked tiles, invisible night shading, dim
choropleth, legend over title, header overflow and wrapped tabs on phones, raw "- " bullets in answers.

Checklist for a UI change:
1. `node --check src/indiamacro/web/static/terminal.js`
2. screenshots at phone + desktop, in the modes you touched
3. look for: SIM/ERR badges, overflow, overlapping text, empty panels, unreadable contrast
4. deployed? run with `--prod` too (relative-URL mistakes only show there)

## Testing a JS function without a browser

terminal.js has no module system. Extract a function by name and `eval` it in Node:

```js
// node check.js src/indiamacro/web/static/terminal.js
const src = require("fs").readFileSync(process.argv[2], "utf8");
const pick = (name) => { const i = src.indexOf("function " + name); let d = 0, j = src.indexOf("{", i);
  for (;; j++) { if (src[j] == "{") d++; if (src[j] == "}" && !--d) break; } return src.slice(i, j + 1); };
eval(`const D2R=Math.PI/180,R2D=180/Math.PI; const wrapLon=(l)=>((l+540)%360)-180;
${pick("sunMoon")} ${pick("nightPolygon")}
console.log(sunMoon(new Date("2026-11-24T19:38:00Z")).sun);   // expect lat ≈ -20.7, lon ≈ -117.8`);
```

Sanity values used before: at 2026-11-24 19:38 UTC the sub-solar point is about (−20.7°, −117.8°), the Moon
is ~100 % lit (full moon), and New Delhi's Sun elevation is about −74°.
