# The terminal (`/terminal`)

A one-screen, keyboard-first monitor: markets, India macro, six map modes, a chart workspace, an AI
analyst and a wire. Backend in `src/indiamacro/monitor/`, front end in
`src/indiamacro/web/static/terminal.{html,css,js}` (no build step, no framework).

URLs: local `http://localhost:8765/terminal` (or `/terminal.html`); production
`https://t.aryan.cfd/indiamacro/terminal` (password).

## Screen layout

```
┌ top: brand │ command bar (/ focuses) │ AI status │ DASHBOARD │ clocks ─────────────────────────────┐
├ tape: scrolling quotes ──────────────────────────────────────────────────────────────────────────┤
│ left 290px          │ center                                        │ right 390px                │
│ WATCH (#watch)      │ map panel: mode tabs #modes, #map,            │ ASK (#chat, #ask-form)     │
│ INDIA MACRO(#india) │   #map-ctl (top-right), #map-side (bottom-l)  │ WIRE (#wire)               │
│                     │ CHART workspace (#work, tabs #work-tabs)      │                            │
└ foot: data credits ──────────────────────────────────────────────────────────────────────────────┘
```

CSS grid in `.term`. Under 1200 px it becomes one scrolling column (center, right, left). Under 760 px
(phone): the header wraps with the command bar on its own row, mode tabs scroll sideways, and
`#map-ctl`/`#map-side` drop below the map instead of floating over it. Inputs are 16 px on phones so
iOS doesn't zoom on focus.

## Feeds (`monitor/feeds.py`)

All return the envelope from DATA_MODEL.md. TTL = in-memory cache; the underlying `_http` call has
its own disk ttl.

| Function | Route | Source | TTL | `data` rows |
|---|---|---|---|---|
| `quotes()` | `/api/live/quotes` | Yahoo via yfinance, 5-min bars, `WATCHLIST` (20 tickers) | 60 s | `{symbol, label, group, last, prev_close, chg_pct, time, spark[]}` |
| `india_snapshot()` | `/api/live/india` | `india.snapshot()` | 1 h | `{series, date, value, unit, source}` or `{series, error}` |
| `quakes()` | `/api/live/quakes` | USGS M4.5+ week GeoJSON | 120 s | `{id, lat, lon, depth, mag, place, time(ms), url, tsunami, alert}` |
| `natural_events()` | `/api/live/events` | NASA EONET v3, open, 30 days | 15 min | `{id, title, category, lat, lon, date, link, track[]}` |
| `aircraft(bbox)` | `/api/live/aircraft?bbox=lamin,lomin,lamax,lomax` | OpenSky states/all, anonymous | 20 s per snapped bbox | `{icao24, callsign, country, lat, lon, alt, ground, vel, track}` |
| `weather()` | `/api/live/weather` | Open-Meteo forecast + air-quality (CAMS), 26 `CITIES` in 2 calls | 15 min | `{city, lat, lon, temp, humidity, wind, precip, code, pm25, aqi, time}` |
| `chokepoints()` | `/api/live/chokepoints` | `energy.chokepoints()` (IMF PortWatch) | 1 h | `{name, lat, lon, date, last7, avg365, tanker7, tanker365, spark[]}` |
| `satellites(group)` | `/api/live/satellites?group=gnss\|stations\|military` | CelesTrak GP TLE, `SAT_GROUPS` queries | 2 h (disk 6 h) | `{name, norad, l1, l2, tag}` or sim `{name, norad, tag, sim: {inc, raan, ma, alt_km}}` |
| `econ_map(indicator, year)` | `/api/live/econ?indicator=&year=` | IMF DataMapper, all countries | 6 h | `{indicator, label, year, values: {ISO3: value}}` |
| `world_geojson()` | `/api/live/world.geojson` | Natural Earth 110m countries (GitHub raw) | forever | raw GeoJSON bytes |

Notes:
- `aircraft` snaps the bbox outward to a 5° grid, and shrinks very large boxes to 40°×60° around the
  centre. This keeps OpenSky's anonymous daily credits from being burnt by every pan.
- `satellites("military")` merges CelesTrak's `military` group with name queries (USA, YAOGAN, GAOFEN,
  RISAT, CARTOSAT, EMISAT, GSAT-7, OFEQ, SAR-LUPE, IGS, LACROSSE, BARS-M, LOTOS, TOPAZ), drops
  NAVSTAR/GPS names (they're navigation satellites with USA-nnn names), and de-duplicates by NORAD id.
  A name query that returns "No GP data found" (HTTP 404) is treated as empty, not as a failure.
- GNSS constellation tags come from `_constellation(name)`: IRNSS/NVS → NavIC, GPS/NAVSTAR, GSAT0/GALILEO,
  BEIDOU, COSMOS → GLONASS, QZS → QZSS, else SBAS/other.

## Map modes (terminal.js)

`setMode(mode)` clears timers and layer groups, resets `#map-ctl`/`#map-side`, then calls the mode's
`enter()`. The mode is remembered in `localStorage["imx-mode"]`. Shortcuts: Alt+1..6 and the commands
ECON/TRAFFIC/CLIMATE/GNSS/ASTRO/MIL (aliases: ECO, TRF, AIR, CLM, WX, NAV, GPS, NAVIC, AST, SKY, SPY, MILSAT).

| Mode | Layers | Side panel | Refresh |
|---|---|---|---|
| `econ` | GeoJSON choropleth (pane `choro`, SVG renderer) coloured by `ECON_IND` config; optional VIIRS night lights; chokepoints | Top/bottom 5 + India's rank; click → `CMP` | on change |
| `traffic` | Aircraft as rotated ➤ divIcons for the current view; chokepoint circles (size = transits, colour = vs 1y avg) | Aircraft count by registration country | aircraft every 30 s and on `moveend` (debounced 800 ms) |
| `climate` | NASA GIBS tile layer (selectable, dated yesterday), quakes (radius by magnitude, fading with age), EONET icons with storm tracks, city PM2.5 dots | Worst PM2.5 cities, largest quakes, hazard counts | feeds re-poll globally |
| `gnss` | Satellite markers (canvas), bigger when >10° elevation from the observer; observer ⌖ | Count in view per constellation | positions every 2 s |
| `astro` | Night/twilight polygons (always on here), ☀ sub-solar and ☾ sub-lunar points, space stations with ISS ground track | Sky state, Sun/Moon elevation, phase, station list | 30 s, stations 2 s |
| `mil` | Military/recon markers coloured by country | Overflight watch for a region in `REGIONS`, next 60 min | positions 2 s, watch list 60 s |

Clicking the map in gnss/astro/mil moves the observer (`S.observer`). Clicking a satellite
(`selectSat`) draws its ground track (±half an orbit, capped at 12 h) and its horizon footprint circle.

### Panes and renderers (important)

The map uses `preferCanvas: true`. A vector layer with `pane: "x"` but no matching renderer is drawn
on the default canvas in the overlay pane, ignoring the pane. So:
- night shading uses `S.nightRenderer = L.canvas({pane: "night"})` (zIndex 430);
- the choropleth uses `S.choroRenderer = L.svg({pane: "choro"})` (zIndex 380, under night);
- labels tile layer is in pane `labels` (zIndex 450, pointer-events none).

### Astronomy and satellite maths

- `sunMoon(date)`: low-precision solar and lunar positions (about 1°), GMST, illumination, waxing.
- `nightPolygon(sun, h0)`: for each longitude, solves sin h0 = A sin φ + B cos φ for the latitude where the
  Sun's elevation equals h0, closes the polygon at the dark pole; drawn for 0, −6, −12, −18° and copied at
  ±360° longitude. The h0 = 0 line is also drawn as a dashed amber terminator (navy fill alone is
  invisible on the dark basemap).
- Satellites: `satellite.twoline2satrec` + `propagate` + `eciToGeodetic`; look angles with
  `ecfToLookAngles`. Simulated satellites use circular Kepler orbits (`satPos` handles both).
- Overflight watch: for each satellite, step 0..60 min by 1 min and record the first minute its
  sub-point is inside the region box (~30k propagations for ~500 objects; recomputed once a minute).

### Basemap

Esri `World_Dark_Gray_Base` + `World_Dark_Gray_Reference` (labels). CARTO's dark tiles now return an
"API KEY REQUIRED" watermark; don't switch back without a key. GIBS URL pattern:
`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/{layer}/default/{date}/GoogleMapsCompatible_Level{n}/{z}/{y}/{x}.{ext}`
(`maxNativeZoom` must equal the level `n`).

## Front-end state and flow

- Global `S`: `mode, map, layers{night, mode, overlay, sats}, timers, feeds{quotes, quakes, events,
  weather, choke, air}, quotes{symbol→last}, wire(Map), observer, sats[], satGroup, satMarkers,
  selected, charts[], activeChart, history[]`.
- `boot()` → clocks, map, chat intro, LLM status, series list, `refreshAll()`, polling intervals:
  quotes 60 s, quakes 2 min, events/weather 15 min, chokepoints/india 1 h.
- `api(path)` uses **relative** paths (`api/live/...`) so the page works under `/indiamacro/`.
- Wire: `addWire(id, time, tag, text, latlon, onclick)`, de-duplicated by id, newest first, capped at 200.
  Tags and thresholds: QUAKE M≥5, HAZARD (all EONET), MKT |chg|≥1.5 %, SHIP |7d vs 1y|≥25 %,
  AIR PM2.5≥150.
- Charts: `addCharts(specs, origin)` appends (max 12), `renderChart()` draws the active tab with Plotly.
- `md()` is a tiny markdown renderer (bold, italics, code, fenced code, blockquote, mixed list/heading
  blocks). It escapes HTML first; keep it that way, since answers come from an LLM.

## Command bar (`runCommand`)

| Command | Does |
|---|---|
| mode names | `setMode` |
| `G <series...> [yoy\|pct\|diff\|log\|zscore\|index100] [since YYYY]` | `get_series` tool |
| `CORR <a> <b> [W\|M\|Q]` | `correlate` |
| `CMP <indicator> [group \| ISO3,ISO3]` | `compare_countries` |
| `WIN <series> <YYYY-MM-DD>` | `window` (30 days before, 60 after) |
| `LIST`, `HELP`/`?`, `REFRESH` | series list, hints, refresh all feeds |
| `GO <city \| lat,lon>`, `SAT <name>` | fly the map; select a satellite in the current group |
| anything else | `ask()` |

Hints (`showHints`) complete command names and, after a space, series keys.

## The analyst (`monitor/assistant.py`)

- **Config** (`.env` or environment; environment wins): `LLM_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`, with
  `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL` as fallbacks. Only an OpenAI key → api.openai.com.
  The endpoint may be a base (`.../v1`) or the full `.../chat/completions` URL. Default model
  `gpt-4o-mini`; the production proxy (t.aryan.cfd, LiteLLM-style) does **not** serve that name, which is
  why `.env` sets `OPENAI_MODEL=heavy-tool` (`light-tool` is faster). List models with `GET {base}/models`.
- **System prompt** (`SYSTEM`): use tools, every number from tool results, cite source and date, flag
  SIMULATED, correlation ≠ causation, IMF projections, answer → bullets → caveats → follow-ups. It also
  receives a `context` string from the page (mode, map centre, observer, selected satellite, chart on
  screen, three quotes).
- **Loop:** max 5 rounds (`MAX_ROUNDS`), temperature 0.2, last 8 history messages (each cut to 4,000
  characters), tool results cut to 6,000 characters.
- **Planner** (`plan()`), used by mock mode, grounded mode and `fake_llm`. Rules in order:
  list/help → compare (group names, 2+ countries, "peers") → date in text → window →
  2+ series with correlation words (or exactly 2 series without "show/plot") → correlate →
  1+ series → get_series (yoy/zscore/index100 by keywords; `since YYYY` → start) →
  live words → live_snapshot → fallback live_snapshot + list_series.

## Adding things

See RECIPES.md: add a series, a tool, a feed, a watchlist ticker, a map mode or map layer.
