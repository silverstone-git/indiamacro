# Data model: the shapes that move through the system

Five shapes matter. Getting one wrong usually fails silently (an empty chart, a misdated point), so
check them when you add anything.

## 1. Source DataFrames: long format

Every `sources/*` function returns a long DataFrame:

| column | type | meaning |
|---|---|---|
| `date` | datetime64 | **start** of the period (see dates below) |
| `country` | str | ISO3 (`IND`, `CHN`...) |
| `series` | str | indicator code or name |
| `value` | float | the number |
| extras | | source-specific: `period` (original label), `base_year`, `revision`, `projection`, `unit`... |

`df.attrs["source"]` is set (and often `unit`). `im.wide(df)` pivots to date × country. In comparisons,
India is always the first column (`countries.expand()` guarantees it).

Exceptions that are documented in their docstrings: `energy.prices()`/`cracks()` return wide daily
frames (one column per product), `energy.chokepoints()` returns `date, chokepoint, n_tanker, n_total,
capacity_tanker`, `fred.series()` returns a Series.

### Dates mark the start of the period

| Period | Stored as | Keep original in |
|---|---|---|
| Year 2024 | 2024-01-01 | `period` |
| Quarter 2024 Q3 | 2024-07-01 | `period` |
| Indian fiscal year 2024-25 | 2024-04-01 | `period` |
| FY quarter Q1 2024-25 | 2024-04-01 | `period` |
| Month | first of month | |

Use `utils.fy_start`, `fy_label`, `fy_quarter_start`, `parse_period`, `month_number`, `month_start`.

### Base years, revisions, projections

- MoSPI GDP/IIP have 2011-12 and 2022-23 bases; CPI has 2012 (and 2024, not yet in the API).
  Every MoSPI function exposes `base_year`. **Never splice** levels across bases; compute growth
  within a base.
- GDP estimates come as advance/provisional/revised/final; `india._latest_revision` keeps the most
  final per date.
- IMF WEO rows carry `projection` (True after the latest actual year, from `imf.latest_actual`).

## 2. India headline Series

`india.*()` returns a `pd.Series` indexed by date with `attrs = {"source", "unit", "note"}` and a
`name` like `cpi_inflation`. These attrs feed captions, the terminal INDIA MACRO panel and citations.
`india.snapshot()` returns rows `{series, date, value, unit, source}` or `{series, error}`.

## 3. Dashboard chart specs (`analysis/charts.py` → `app.js`)

```python
{"kind": "line" | "area" | "bar" | "hbar" | "stackbar" | "scatter" | "table" | "kpis" | "text" | "error",
 "title": str, "unit": str, "y2_unit": str, "source": str, "note": str,
 "traces": [{"name", "x": ["YYYY-MM-DD", ...], "y": [float|None], "axis": "y"|"y2", "dash": bool}],
 "events": [{"x", "label", "category"}], "bands": [...], "hbands": [...],
 "range_buttons": bool, "width": "full"|"half"|"third"}   # width added by framework.run
```

KPI tiles: `{label, value, unit, date, delta, delta_label, source, hint, decimals, spark: {x, y}}`.
Build these with the helpers; don't write dicts by hand. NaN must become `None` (`charts._num` and
`server._clean` both do this; JSON can't carry NaN).

The dashboard supports a secondary axis (`y2`) for historical pages. **The terminal does not**:
see section 5.

## 4. Terminal feed envelope (`monitor/feeds.py` → `terminal.js`)

```python
{"feed": "quakes", "status": "live" | "sim", "source": str, "asof": "YYYY-MM-DDTHH:MM:SSZ",
 "note": str,            # error message when status == "sim", else an informational note
 "data": list | dict}    # feed-specific rows, see TERMINAL.md
```

`source` becomes `"SIMULATED (source unavailable)"` when `status == "sim"`. The front end must show the
SIM badge for any sim envelope; never strip it.

## 5. Analyst tool results (`monitor/query.py`)

```python
{"text": str,            # plain-language summary with every number computed in Python
 "charts": [spec, ...],  # terminal chart specs (below)
 "sources": [str, ...],  # original producers, or "SIMULATED (source unavailable)"
 "sim": bool,            # True if any input was simulated; text then contains "SIMULATED"/"WARNING"
 "stats": {...}}         # optional machine-readable numbers (correlate: r0, best_lag, best_r, n)
```

`text` is what the LLM sees (truncated to 6,000 characters per tool message), so put the important
numbers, dates and caveats in it. Keep it short and factual.

### Terminal chart specs (`query.py` → `terminal.js renderChart`)

```python
{"type": "line", "title": str, "yaxis": str,
 "traces": [{"name", "x": ["YYYY-MM-DD"...], "y": [...], "axis": "y"}],
 "sources": [str], "shade_from": "YYYY-MM-DD" (optional, projections), "vline": "YYYY-MM-DD" (optional)}
{"type": "bar", "title": str, "x": [lags], "y": [r], "yaxis": "r", "band": float (noise band), "sources": [...]}
```

Rules: **one y-axis** per chart. When units differ, return several charts (small multiples) or a
`zscore`/`index100` transform. Colours are assigned in fixed order by the front end (`CAT` palette).
Series are thinned to ~1,500 points by `_thin()`.

## 6. Series registry (`query.SERIES`)

```python
Spec(label="India CPI inflation", unit="% y/y", source="MoSPI CPI, base 2012 (...)",
     loader=india.cpi_inflation,              # zero-arg callable -> pd.Series (date index)
     aliases=["inflation", "cpi", ...],       # words users type; matched on word boundaries
     sim={"mean_revert": 5, "vol": .15})      # kwargs for sim.series() when the loader fails
```

`query.load(key)` returns a float Series sorted by date with `attrs = {source, unit, sim}`.
`query.resolve(name)` maps keys/labels/aliases to a key; `query.mentions(text)` finds keys in free text,
earliest first, with longer aliases shadowing shorter ones ("food inflation" beats "inflation").

## 7. Events

`events.load()` → DataFrame `date, label, category, region, id, builtin`. Categories are fixed in
`events.CATEGORIES`. Built-in events are dated from data or primary sources, not guessed.
