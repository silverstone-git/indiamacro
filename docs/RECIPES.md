# Recipes: how to add or change things

Each recipe lists the files to touch, in order, and how to verify. Always finish with
`uv run pytest` and, for anything visible, `scripts/screenshots.py` (TESTING.md).

## Add a data source

1. `src/indiamacro/sources/<name>.py`: a module docstring (what, URL, key needs, quirks), `SOURCE = "<name>"`,
   `BASE = "https://..."`. Functions return the long format (`date, country, series, value` + extras) with
   `df.attrs["source"]` set. Dates = start of period (use `utils`). Countries ISO3 (`countries.iso3`).
2. Fetch only via `_http.get(url, params, ttl=..., source=SOURCE)` / `_http.get_json`. Pick a ttl: default
   1 day; `None` for versioned files; short for live data. Raise `_http.SourceError(SOURCE, msg)` when the
   answer is unusable (empty, error JSON, HTML instead of CSV).
3. Export: `src/indiamacro/__init__.py` (`from .sources import ...` and `__all__`). (Note: `energy` is
   currently *not* exported; see PITFALLS.md.)
4. `ping.CHECKS`: add a `Check(source, what, lambda: df_with_date_and_value)`. This also adds a live test.
5. Offline test in `tests/test_offline.py` that monkeypatches `_http.get_json`/`get` with a canned payload
   (see `test_query_follows_pagination`). Never hit the network in offline tests.
6. Docs: README source table, `docs/SOURCES.md` (endpoint, codes, quirks), `LIMITATIONS.md` if it lags,
   is a proxy, or is fragile.
7. Verify: `uv run indiamacro-ping` (all sources) and `uv run pytest -m live -k <name>`.

## Add an India headline series

`india.py`: build with `_series(values, name, source, unit, note)` so `attrs` are set. Add it to
`snapshot()` if it belongs on the headline panel, to `INDIA_LABELS`/`INDIA_SERIES` in `terminal.js`
(label + which query key to chart on click), and to the live test list in `tests/test_live.py`.

## Add a dashboard page

```python
@story("my_id", "Title", section="Energy", question="What does X do to Y?",
       params=[Param("post", "Days after", "number", 10)], method="...", caveats=["..."])
def _(s: Builder):
    s.chart(lambda: C.line(D.cracks()["diesel_crack"], "Diesel crack", unit="$/bbl", source="EIA via FRED"),
            width="half")
    s.insight(f"... computed from the data, using {s.p['post']} ...")
```

Put it in the matching `analysis/stories_*.py` (Overview, India, Energy, Shocks, Trends, Tools). Use
loaders from `analysis/data.py` (add one there with `@memo()` if new). Insights are computed, never
hard-coded. Verify live: `uv run python -c "from indiamacro.analysis import run; print(run('my_id'))"`.

## Add a built-in event

Append to `events.BUILTIN` as `(date, label, category, region)`. Date it from the data or a primary
source (see the Hormuz entry dated from PortWatch). The category must be in `events.CATEGORIES`;
adding a category also needs a colour in `EVENT_COLORS` in `app.js`.

## Add a series the terminal can query (`G`, `CORR`, the analyst)

1. `monitor/query.py` → `SERIES["my_key"] = Spec(label, unit, source, loader, aliases, sim)`.
   - `loader`: zero-arg callable returning a date-indexed Series. Reuse `analysis/data.py` loaders or
     `_yahoo("TICKER")` (memoised daily Yahoo closes).
   - `unit` starting with `%` makes `correlate(transform="auto")` use differences; otherwise yoy.
   - `aliases`: lowercase words users type. They match on word boundaries. Check they don't collide with
     other series (run `query.mentions("...")` on a few phrasings).
   - `sim`: kwargs for `sim.series()` so the fallback has a plausible scale and frequency.
2. Add a planner test row in `tests/test_monitor.py::test_mentions` if the alias is tricky.
3. The series is automatically in `/api/series`, command hints, `list_series` and the LLM's tools.

## Add an analyst tool

1. Write `def my_tool(...) -> dict` in `monitor/query.py` returning `{text, charts, sources, sim}`. Put the
   numbers, dates and caveats in `text`, and say SIMULATED when inputs are simulated.
2. Register it in `TOOLS["my_tool"] = (callable, json_schema, description)`. The schema is sent to the
   LLM; keep descriptions specific.
3. If the mock should use it, add a rule to `assistant.plan()` and a branch to `_mock_writeup()`.
4. Optional command: add a branch in `runCommand()` (terminal.js) that calls `tool("my_tool", args, line)`.
5. Tests: a unit test on simulated data (the `demo_mode` fixture) and, if planned, a `test_planner_picks_tool` row.

## Add a live feed

1. `monitor/feeds.py`: `def my_feed() -> dict: return _envelope("my_feed", "Source, what it is", ttl, live, fallback)`.
   `live()` fetches via `_http` (short ttl) and returns JSON-safe rows; `fallback()` comes from `sim.py`.
2. `monitor/sim.py`: a generator with plausible values (seed it with `_rng(...)` so screens are stable).
3. `web/server.py` → `_live()`: add to `simple` (no params) or a dedicated branch.
4. `terminal.js`: a loader (`loadX`) storing `S.feeds.x`, polling interval in `boot()`, drawing in the
   relevant mode, optional `addWire(...)` items.
5. `ping.CHECKS`: `Check("Name", "what", lambda: _feed(lambda f: f.my_feed(), "date_col", "value_col"))`.
6. Docs: TERMINAL.md feed table, README terminal table, LIMITATIONS terminal section.

## Add a watchlist ticker

Append `(yahoo_ticker, label, group, sim_base_level)` to `feeds.WATCHLIST`. Groups render in order of
first appearance. If it should chart on click, map it in `symbolSeries()` (terminal.js) to a `SERIES` key.

## Add a map layer to an existing mode

In the mode's `enter*()` add a checkbox to `#map-ctl`; draw in its `draw*()` into `S.layers.mode` (cleared
on every redraw) or `S.layers.overlay`. Use `renderer: S.canvas` for many circle markers; divIcons for
rotated or emoji markers (slower past ~1,000). For a new pane, create a matching renderer
(see PITFALLS #9). Imagery: `gibsLayer(layer, date, level, ext)`, or add an entry to `GIBS`.

## Add a map mode

1. `terminal.html`: a button in `#modes` (`data-mode="x"`), keeping the number order for Alt+N.
2. `terminal.js`: `MODES.x = {enter: enterX, label: "X"}`; write `enterX()` (controls into `#map-ctl`,
   data loads, timers in `S.timers.*` so `setMode` clears them) and a draw function that returns early
   if `S.mode !== "x"` (async loads can land after the user switched mode).
3. Add command aliases in `runCommand()`'s `modes` map and a row in `COMMANDS`.
4. Check phone layout: the side panel becomes a normal block under the map.

## Change the LLM / model

Edit `.env` (`OPENAI_MODEL=...` or `LLM_*`), then restart the server (`sudo systemctl restart
indiamacro-web` in production). The model must support function calling, or answers fall back to
"grounded" mode (planner picks tools). Check: `curl .../api/ask/status`, then one real question.

## Deploy

`./deploy.sh` (DEPLOYMENT.md).
