# CLAUDE.md

`indiamacro` is a Python library (plus a local dashboard) for India-first, **free** macroeconomic
data with international comparators. Its audience is students and researchers who will cite the
numbers, so correctness, provenance and honest caveats matter more than features.

## Commands

```bash
uv sync                                  # install (Python >= 3.10, hatchling build)
uv run pytest                            # offline tests only (addopts = -m 'not live'); ~3 s
uv run pytest -m live                    # live tests: hit every real source over the network
uv run indiamacro-ping [--fresh] [--markdown docs/SOURCE_STATUS.md]   # live health check of all sources
./interact [--port 9000] [--no-browser]  # dashboard at http://localhost:8765 (= uv run indiamacro-web)
uv run --extra plot python examples/india_vs_peers.py                 # writes examples/output/ (gitignored)
```

No linter/formatter is configured. Match the existing style: `from __future__ import annotations`,
type hints, long lines (~110-120 chars), module docstrings that explain the source and its quirks.

## Layout

```
src/indiamacro/
  _http.py        single requests session, retries, on-disk cache, SourceError, settings, clear_cache
  utils.py        date parsing (fy_start, fy_label, fy_quarter_start, parse_period, month_number), wide, yoy
  countries.py    name/ISO2/ISO3 resolution and groups (BRICS, G7, G20, SOUTH_ASIA, ASEAN, EM_ASIA, QUAD)
  india.py        headline helpers -> pandas.Series with .attrs {source, unit, note}; snapshot()
  compare.py      compare(indicator, countries) over IMF WEO; INDICATORS
  ping.py         CHECKS list (also drives tests/test_live.py) + CLI
  sources/        one module per provider: mospi (incl. RBI tables), budget, fred, worldbank, imf,
                  oecd, bis, pwt, owid, energy (EIA/NYMEX/Pink Sheet/PPAC/JODI/Comtrade/CREA/PortWatch)
  analysis/
    framework.py  @story registry, Builder, Param, run(), catalog(), memo()
    charts.py     chart-spec builders (line, bar, scatter, kpi, kpis, error) -> JSON dicts for Plotly
    data.py       @memo'd loaders shared between pages
    events.py     built-in + user event registry, event_study()
    stories_*.py  the dashboard pages (india, energy, templates = shock/trend analyses, tools)
  web/            stdlib http.server + static/ (index.html, app.js, style.css; Plotly front end)
docs/SOURCES.md        codes, coverage and quirks per source
docs/SOURCE_STATUS.md  output of the last ping run
LIMITATIONS.md         missing data, lags, proxies, method caveats, fragile connections
```

## Conventions (keep these invariants)

- **Long format.** Source functions return `date, country, series, value` (+ source-specific
  columns such as `period`, `base_year`, `revision`, `projection`), with `df.attrs["source"]` set.
  Countries are ISO3. `im.wide(df)` pivots; India always comes first in comparisons.
- **Dates mark the start of the period.** Year -> Jan 1, quarter -> first month, Indian fiscal
  year 2024-25 -> 2024-04-01. Keep the original label in `period`. Use the helpers in `utils.py`,
  don't hand-roll date logic.
- **All network access goes through `_http.get` / `_http.get_json`** with `source=SOURCE` and an
  appropriate `ttl` (default one day; `None` = forever, for versioned files like PWT). Raise
  `_http.SourceError(SOURCE, msg)` when a source answers with unusable data.
- **Never splice series across base years.** MoSPI rebased GDP/IIP to 2022-23 and CPI to 2024;
  every MoSPI function exposes `base_year`. Same care for GDP revision vintages and IMF projections.
- **`india.*` series** must carry `attrs["source"]`, `attrs["unit"]` and notes (used for captions
  and citations).

## HTTP quirks (do not "fix" these)

- Keep the stock python-requests User-Agent: FRED resets connections for browser/unknown UAs and
  IMF DataMapper 403s browser UAs.
- `api.mospi.gov.in` needs OpenSSL legacy renegotiation; it is enabled for that host only
  (`_LEGACY_TLS_HOSTS`). MoSPI pages are capped at 200 rows, so filter queries.
- Disk cache: `~/.cache/indiamacro` (override `INDIAMACRO_CACHE`; disable with
  `INDIAMACRO_NO_CACHE` or `im.settings.cache = False`). Writes are atomic via temp file + replace.

## Adding a dashboard page

```python
@story("my_id", "Title", section="Energy", question="What does X do to Y?",
       params=[Param("post", "Days after", "number", 10)], method="...", caveats=["..."],
       kind="story")            # or "template" for parameterised analyses
def _(s: Builder):
    s.chart(lambda: C.line(D.cracks()["diesel_crack"], "Diesel crack", unit="$/bbl"), width="half")
    s.insight(f"... computed from the data, using s.p['post'] ...")
```

- Put it in the matching `stories_*.py` (they are imported in `analysis/__init__.py` to register).
  Sections shown by the server: Overview, India, Energy, Shocks, Trends, Tools.
- Charts are lambdas run in parallel; a failing chart becomes an `error` block instead of breaking
  the page. Reuse loaders from `analysis/data.py` (memoised 15 min) rather than calling sources
  directly. The server also caches whole pages for 10 min.
- Insights must be computed from the numbers, not hard-coded claims. Document method and caveats;
  if the page uses a proxy or has a known gap, also add it to LIMITATIONS.md.
- Offline tests don't render real pages (they need network). To verify a page, run it live:
  `uv run python -c "from indiamacro.analysis import run; print(run('my_id'))"` or open it in
  `./interact`. Framework-level behaviour is tested in `tests/test_analysis.py`.

## Events

`events.CATEGORIES` defines valid categories; `BUILTIN` holds dated built-in events (date them from
the data, not guesses). User events live in `~/.local/share/indiamacro/events.json`
(`INDIAMACRO_EVENTS` overrides). `event_study(series, events, pre, post, log)` is a constant-mean
event study; use `log=False` for spreads/levels such as cracks.

## Adding or changing a source

1. New module in `sources/` with a docstring (what, URL, key needs, quirks), `SOURCE`, `BASE`,
   tidy long-format output.
2. Export it in `src/indiamacro/__init__.py` (`from .sources import ...` and `__all__`).
3. Add a `Check` to `ping.CHECKS` (this automatically adds a live test).
4. Document it in README's source table, `docs/SOURCES.md`, and LIMITATIONS.md if relevant.
5. Offline tests in `tests/test_offline.py` should parse canned payloads, never hit the network.

## Known issue

`sources.energy` is not imported in `src/indiamacro/__init__.py`, so `im.energy` (used in the
README) raises `AttributeError`; use `from indiamacro.sources import energy` until that is fixed.

## Docs and tone

README, SOURCES.md, LIMITATIONS.md and the in-page method notes are written for students:
plain language, say what to do about each limitation, and cite the original producer (e.g.
"National Statistics Office, MoSPI ... accessed via the eSankhyiki API on <date>"), not this
package. Live data facts in docs are dated ("as of Oct 2026"); update the date when you re-verify.
Paid or login-gated sources (RBI DBIE, CMIE, Platts, Kpler, IEA OMR) are out of scope on purpose.
