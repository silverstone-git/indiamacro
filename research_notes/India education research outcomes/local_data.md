# Local `indiamacro` audit and verified World Bank extract (education / R&D outcomes)

Scope: audit only. No package source, tests or docs were changed. All new files are in this folder:
[extract_wb.py](./extract_wb.py), [wb_extract.csv](./wb_extract.csv),
[wb_diagnostics.json](./wb_diagnostics.json), [extract_wb_hlos.py](./extract_wb_hlos.py),
[wb_hlos_supplement.csv](./wb_hlos_supplement.csv).

**Access date for all live numbers: 20 Nov 2026.** Every number in the CSVs below came from the live
World Bank API on that date (cache disabled); the repo contained **no static values** for any of these
indicators — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md)
lists codes only, and the only World Bank entry in
[docs/SOURCE_STATUS.md](/home/ubuntu/cyto/indiamacro/docs/SOURCE_STATUS.md) is an unrelated GDP-growth
health check (India 2025 = 7.57).

## Q1. What the library already delivers: functions, output shape, `compare.py`, plan indicators

### Takeaway
`indiamacro` is a thin, consistent wrapper around free sources: source functions return tidy long-format
DataFrames, `india.*` returns attributed Series, and `compare()` pivots to a date × country table that
defaults to IMF WEO for named macro indicators but **already supports World Bank codes and a
`source="worldbank"` argument** — so the plan's "A1" needs no new comparison function.

### Cited Findings
- Source modules shipped: `mospi` (incl. RBI tables), `budget`, `fred`, `worldbank`, `imf`, `oecd`, `bis`, `pwt`, `owid`, `energy`; plus `analysis/` dashboard pages and `compare()` — [CLAUDE.md](/home/ubuntu/cyto/indiamacro/CLAUDE.md#L21-L43), [src/indiamacro/__init__.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/__init__.py#L15-L19).
- `worldbank.get(indicator, countries="IND", start=None, end=None)` exists and accepts a code or list of codes, names, ISO codes or groups; `worldbank.search(text)` also exists — [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L39-L64), [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L81-L86).
- Long-format contract: columns `date` (pandas datetime, **1 Jan of the period year**), `country` (ISO3), `series` (source code), `value` (float, NaN when missing), plus `country_name` and `series_name`; `df.attrs["source"] = "worldbank"`. Example live row: `date=2020-01-01, country=IND, series=GB.XPD.RSDV.GD.ZS, value=0.64558, country_name=India, series_name='Research and development expenditure (% of GDP)'` — [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L39-L64), [wb_extract.csv](./wb_extract.csv), [World Bank API, R&D % GDP (accessed 2026-11-20)](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/GB.XPD.RSDV.GD.ZS?format=json&per_page=20000).
- `compare(indicator, countries="BRICS", source=None, start=None, end=None)` returns a wide date × country DataFrame with India first and `attrs = {"source": ..., "code": ...}` — [src/indiamacro/compare.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/compare.py#L32-L55).
- What it actually runs on: of the 16 named `INDICATORS`, 9 have an IMF mapping and therefore default to `imf.weo()` (GDP growth, inflation, GDP USD, PPP GDP per capita, world-GDP share, unemployment, government debt, fiscal balance, current account); 7 are World-Bank-only (exports, investment, savings, FDI, manufacturing, female LFPR, population). A raw code containing "." defaults to World Bank, other raw codes default to IMF — [src/indiamacro/compare.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/compare.py#L11-L55).
- **Live check:** `im.compare("GB.XPD.RSDV.GD.ZS", ["IND", "CHN", "KOR"])` returned a wide table with columns `['IND','CHN','KOR']`, 2023 values `2.57729 / 4.94352` for CHN/KOR and NaN for IND (India's last value is 2020), with `attrs={'source': 'worldbank', 'code': 'GB.XPD.RSDV.GD.ZS'}` — [World Bank API, same indicator (accessed 2026-11-20)](https://api.worldbank.org/v2/country/IND;CHN;KOR/indicator/GB.XPD.RSDV.GD.ZS?format=json&per_page=20000), [wb_diagnostics.json](./wb_diagnostics.json).
- `budget.py` delivers only **raw, unheaded** workbook sheets (`workbook(name)` keys: `budget_at_a_glance`, `annual_financial_statement`, `expenditure_summary`, `expenditure_by_ministry`); there is no `rd_lines()`, `education_lines()` or BE-vs-actuals utilisation helper — [src/indiamacro/sources/budget.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/budget.py#L1-L40).
- `india.py` has headline macro helpers (`gdp`, `gdp_growth`, `cpi_inflation`, `wpi_inflation`, `iip_growth`, `unemployment`, `repo_rate`, `usdinr`, `reer`, `forex_reserves`, `snapshot`) returning date-indexed Series with `attrs["source"]`, `attrs["unit"]`, `attrs["note"]` — none are education/R&D series — [src/indiamacro/india.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/india.py#L1-L160).

### Inferences
- For the report, the shortest no-new-code path is `worldbank.get(code, [countries])` for raw numbers and `im.compare(code, countries, source="worldbank")` for wide peer tables; the plan's claim that `compare.py` is IMF-only is only true for the named macro keys.
- Because `get()` returns NaN rows for missing years and fills `value` with float, the report writer must drop NaNs before taking "latest" — that is what the extract script does.

### Gaps
- No `RD_INDICATORS`/`EDUCATION_INDICATORS` dict, `india.rd_snapshot()`, research dashboard page, or BE-vs-actuals calculation exists yet; these are plan items, not current capabilities — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L19-L38).
- `budget.workbook()` returns formatted reports, so any ministry-line extraction still needs manual row mapping (and the archive for older years) — [src/indiamacro/sources/budget.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/budget.py#L4-L10).

## Q2. Live World Bank extract: exact calls, latest values, coverage

### Takeaway
Nine of the ten planned codes returned live data; `HD.HCI.HLO` is an invalid World Bank code (the correct
one is `HD.HCI.HLOS`). India's coverage is strong for patents, papers and education spending, but sparse
or stale for R&D spending, researchers, technicians, learning-adjusted years and learning poverty.

### Cited Findings
- Exact calls, all run from the repo root with `INDIAMACRO_NO_CACHE=1 uv run python ...` on 20 Nov 2026: `worldbank.get('<CODE>', ['IND', 'CHN', 'KOR', 'USA', 'DEU', 'BRA'])` for each of the ten planned codes; reproduction script and per-call diagnostics (row counts, timings, names, errors) are saved — [extract_wb.py](./extract_wb.py), [wb_diagnostics.json](./wb_diagnostics.json).
- Latest non-null observation per indicator/country (all values below are live API values, not repo statics; `date` is 1 Jan of the reported year; full tidy file: [wb_extract.csv](./wb_extract.csv)):

| Indicator | IND | CHN | KOR | USA | DEU | BRA |
|---|---|---|---|---|---|---|
| `GB.XPD.RSDV.GD.ZS` — R&D, % GDP | 2020: **0.64558** | 2023: 2.57729 | 2023: 4.94352 | 2023: 3.44716 | 2023: 3.1539 | 2023: 1.1938 |
| `SP.POP.SCIE.RD.P6` — researchers/m | 2020: **259.26325** | 2023: 2107.27003 | 2023: 9471.82543 | 2022: 4937.49441 | 2023: 5926.07432 | 2014: 903.20079 |
| `SP.POP.TECH.RD.P6` — technicians/m | 2018: **73.05997** | no non-null values | no non-null values | no non-null values | 2017: 2006.65327 | 2014: 969.90222 |
| `IP.PAT.RESD` — resident patent applications | 2024: **63217** | 2024: 1672001 | 2024: 195786 | 2024: 270295 | 2024: 40085 | 2024: 5752 |
| `IP.PAT.NRES` — nonresident patent applications | 2024: **41940** | 2024: 156053 | 2024: 50459 | 2024: 332899 | 2024: 19177 | 2024: 19845 |
| `IP.JRN.ARTC.SC` — scientific/technical articles | 2023: **228174.31** | 2023: 932711.93 | 2023: 71724.33 | 2023: 430843.27 | 2023: 108782.34 | 2023: 58292.04 |
| `SE.XPD.TOTL.GD.ZS` — government education spend, % GDP | 2022: **4.098658142** | 2023: 3.897140026 | 2022: 5.409100056 | 2021: 5.420380116 | 2022: 5.239160061 | 2022: 5.619209766 |
| `HD.HCI.LAYS` — learning-adjusted years of school | 2020: **7.102170467** | 2020: 9.270027161 | 2020: 11.68402767 | 2020: 10.55677032 | 2020: 11.03308964 | 2020: 7.872839451 |
| `HD.HCI.HLO` — planned code | **invalid code — no data** (see below) | — | — | — | — | — |
| `SE.LPV.PRIM` — learning poverty, % | 2017: **56.07056046** | 2016: 18.20000076 | 2019: 3.230080605 | 2021: 9.691570282 | 2021: 15.43990231 | 2019: 46.89786148 |

Sources for the table: live World Bank API per indicator — [R&D % GDP](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/GB.XPD.RSDV.GD.ZS?format=json&per_page=20000), [researchers](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/SP.POP.SCIE.RD.P6?format=json&per_page=20000), [technicians](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/SP.POP.TECH.RD.P6?format=json&per_page=20000), [resident patents](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/IP.PAT.RESD?format=json&per_page=20000), [nonresident patents](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/IP.PAT.NRES?format=json&per_page=20000), [articles](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/IP.JRN.ARTC.SC?format=json&per_page=20000), [education spend](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/SE.XPD.TOTL.GD.ZS?format=json&per_page=20000), [LAYS](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/HD.HCI.LAYS?format=json&per_page=20000), [learning poverty](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/SE.LPV.PRIM?format=json&per_page=20000), all accessed 2026-11-20; compiled in [wb_extract.csv](./wb_extract.csv).
- `HD.HCI.HLO` failed immediately with `SourceError: [worldbank] [{'id': '120', 'key': 'Invalid value', 'value': 'The provided parameter value is not valid'}]`; the World Bank's own indicator endpoint returns the same error, and its catalogue contains no `HD.HCI.HLO` — [wb_diagnostics.json](./wb_diagnostics.json), [World Bank indicator endpoint](https://api.worldbank.org/v2/indicator/HD.HCI.HLO?format=json).
- The catalogue instead lists `HD.HCI.HLOS` = "Harmonized Test Scores" (source 63, Human Capital Index). Live call `worldbank.get('HD.HCI.HLOS', ['IND','CHN','KOR','USA','DEU','BRA'])` (cache disabled, 20 Nov 2026) returned 66 rows with latest values: IND 2020: **399**, CHN 2020: 441, KOR 2020: 537.209717, USA 2020: 511.798676, DEU 2020: 517.281433, BRA 2020: 413.244751 — [extract_wb_hlos.py](./extract_wb_hlos.py), [wb_hlos_supplement.csv](./wb_hlos_supplement.csv), [World Bank API](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/HD.HCI.HLOS?format=json&per_page=20000).
- Non-null observation counts explain the sparse series: R&D % GDP India 25 points (1996–2020); researchers India 8 points (1996–2020) vs CHN/KOR/DEU 28 each; technicians India 7 points (1996–2018), CHN/USA zero, KOR 23, DEU 18; LAYS India 3 points (2017–2020); learning poverty India **1 point (2017)** vs USA/DEU 5 — [wb_diagnostics.json](./wb_diagnostics.json).
- By contrast, resident/nonresident patents have 44 Indian observations (1980–2024), scientific articles 28 (1996–2023), government education spending 22 (1997–2022) — [wb_diagnostics.json](./wb_diagnostics.json).
- Indicator names returned by the API confirm the code meanings: e.g. `SE.LPV.PRIM` = "Learning poverty: Share of Children at the End-of-Primary age below minimum reading proficiency adjusted by Out-of-School Children (%)" — [wb_diagnostics.json](./wb_diagnostics.json), [World Bank API](https://api.worldbank.org/v2/country/IND;CHN;KOR;USA;DEU;BRA/indicator/SE.LPV.PRIM?format=json&per_page=20000).

### Inferences
- The plan's qualitative claims are confirmed by live data: India's R&D spending and researcher series stop in 2020; its technician and learning-poverty series are too thin for trend claims — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L27-L34), [wb_diagnostics.json](./wb_diagnostics.json).
- Patent *counts* and article counts are available and comparable across all six peers at recent dates, but they are output volumes, not quality or "usefulness"; the report must not treat them as quality proxies without the caveats in the plan — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L84-L86), [wb_extract.csv](./wb_extract.csv).
- Comparison years differ by indicator (patents 2024, papers/R&D 2023, education spend 2022, learning 2020 or older); do not present them as a same-year snapshot — [wb_extract.csv](./wb_extract.csv).
- README warns World Bank data for India are fiscal-year based; treat the 1-Jan dates as period labels and cite the original producer, not this package — [README.md](/home/ubuntu/cyto/indiamacro/README.md#L100-L105), [README.md](/home/ubuntu/cyto/indiamacro/README.md#L113-L117).

### Gaps
- No Indian value after 2020 for R&D % GDP or researchers/million; after 2018 for technicians; after 2017 for learning poverty; after 2020 for LAYS/HLOS — [wb_extract.csv](./wb_extract.csv).
- `GB.XPD.RSDV.GD.ZS` has no funder/performer breakdown (central, state, business), so it cannot settle whether government or firms drive India's low R&D intensity — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L140-L154), [wb_extract.csv](./wb_extract.csv).
- Patent counts carry no citations, grants, lapses or applicant type; WDI cannot answer the patent-quality question — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L72-L86).

## Q3. `worldbank.search`, `energy` export, and other plan items

### Takeaway
`worldbank.search` works but searches only the WDI source list (source 2), so it confirms most planned
codes but not the Human Capital Index indicators; `im.energy` is indeed not exported; none of the plan's
new R&D/education/ASER/patent/startup/openalex modules exist.

### Cited Findings
- `worldbank.search(text)` exists and ran successfully: "research and development" → 1 match (`GB.XPD.RSDV.GD.ZS`); "researchers in r&d" → 1 (`SP.POP.SCIE.RD.P6`); "patent applications" → 2 (`IP.PAT.RESD`, `IP.PAT.NRES`); "scientific and technical journal" → 1 (`IP.JRN.ARTC.SC`); "government expenditure on education" → 5 (incl. `SE.XPD.TOTL.GD.ZS`); "learning poverty" → 3 (incl. `SE.LPV.PRIM`) — [wb_diagnostics.json](./wb_diagnostics.json), [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L81-L86).
- However, "learning-adjusted" and "harmonized learning outcomes" returned **0 matches** even though `HD.HCI.LAYS`/`HD.HCI.HLOS` fetch fine: `search()` queries `source/2/indicators` (WDI) while those codes belong to World Bank source 63, "Human Capital Index" — [wb_diagnostics.json](./wb_diagnostics.json), [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L81-L86), [World Bank indicator metadata](https://api.worldbank.org/v2/indicator/HD.HCI.LAYS?format=json).
- Live API check: `hasattr(im, 'energy')` is **False**, matching the documented known issue; use `from indiamacro.sources import energy`. `hasattr(im, 'worldbank')` and `im.compare` are True; package version 0.1.0 — [wb_diagnostics.json](./wb_diagnostics.json), [CLAUDE.md](/home/ubuntu/cyto/indiamacro/CLAUDE.md#L108-L111), [src/indiamacro/__init__.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/__init__.py#L15-L19).
- The file list contains no `aser.py`, `udise_nas.py`, `patents.py`, `startups.py`, `openalex.py` or `stories_research.py`; existing story modules are `stories_india.py`, `stories_energy.py`, `stories_templates.py`, `stories_tools.py` — [src/indiamacro/sources/](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources), [src/indiamacro/analysis/](/home/ubuntu/cyto/indiamacro/src/indiamacro/analysis).
- Adjacent capability already present: `pwt.get(['hc'], countries)` returns the Penn World Table human-capital index (years of schooling and returns to education) in the standard long format, cached forever; `oecd.get(flow, key)` is a generic SDMX query that could reach OECD patent datasets only if the right flow/key is supplied — [src/indiamacro/sources/pwt.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/pwt.py#L24-L67), [src/indiamacro/sources/oecd.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/oecd.py#L1-L33).

### Inferences
- For a first report table, `worldbank.get` plus `search` and `compare(source="worldbank")` are sufficient; everything else in the plan (ASER, budget line items, patents, startups, OpenAlex, dashboards) is unimplemented work.
- `search()` is a name-matching convenience, not a complete indicator catalogue: verify any code with `get()` or the World Bank indicator endpoint.

### Gaps
- No patent-quality, startup-count, ASER/UDISE learning-level or budget-utilisation numbers are available from this repo; the report writer must source them elsewhere or flag them as missing — [docs/RESEARCH_OUTCOME_ANGLE.md](/home/ubuntu/cyto/indiamacro/docs/RESEARCH_OUTCOME_ANGLE.md#L19-L132).

## Q4. Network, cache and provenance behaviour

### Takeaway
All live WDI calls succeeded except the invalid `HD.HCI.HLO`; no timeouts or retries were observed. The
default path caches responses on disk for one day, so this extract was deliberately run with caching off.

### Cited Findings
- Extract run with `INDIAMACRO_NO_CACHE=1` (sets `settings.cache = False`) so every call hit `api.worldbank.org` live; `wb_diagnostics.json` records `cache_enabled: false` and access date 2026-11-20 — [extract_wb.py](./extract_wb.py), [wb_diagnostics.json](./wb_diagnostics.json), [src/indiamacro/_http.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/_http.py#L40-L45).
- All eight search calls succeeded (first 1.94 s, rest 0.06–0.10 s); nine of ten indicator calls succeeded with elapsed times 6.13 s (LAYS), 8.93 s (learning poverty), 14.69 s (education spend), 21.64 s (articles), 22.68 s (resident patents), 27.51 s (nonresident patents), 40.9 s (technicians), 68.56 s (R&D), 83.93 s (researchers); total ~5 minutes — [wb_diagnostics.json](./wb_diagnostics.json).
- The only error was the immediate (0.3 s) invalid-value response for `HD.HCI.HLO` from the World Bank, reproduced directly against the API; there were no HTTP 429/5xx retries, connection resets or 90-second timeouts in this run — [wb_diagnostics.json](./wb_diagnostics.json), [World Bank indicator endpoint](https://api.worldbank.org/v2/indicator/HD.HCI.HLO?format=json).
- Default behaviour (not used for the numbered extract): one shared `requests.Session`, 3 retries with 1.5× backoff on 429/5xx, 90 s timeout, atomic on-disk cache at `~/.cache/indiamacro` with a 1-day TTL (`ttl=None` forever, e.g. PWT); `INDIAMACRO_CACHE` overrides the directory, `INDIAMACRO_NO_CACHE` or `im.settings.cache = False` disables it — [src/indiamacro/_http.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/_http.py#L25-L121), [README.md](/home/ubuntu/cyto/indiamacro/README.md#L92-L93).
- World Bank API limitation: requests return all years including null-valued rows (66 rows for LAYS, 396 for the others across six countries), so "latest" must be computed after dropping nulls — [wb_diagnostics.json](./wb_diagnostics.json), [src/indiamacro/sources/worldbank.py](/home/ubuntu/cyto/indiamacro/src/indiamacro/sources/worldbank.py#L49-L64).
- Provenance: **all numeric values in `wb_extract.csv` and `wb_hlos_supplement.csv` are live World Bank API values retrieved on 20 Nov 2026**; the only pre-existing repo number related to this source was the unrelated WDI GDP-growth health-check value in `docs/SOURCE_STATUS.md` (India 2025 = 7.57), which was not copied into the extract — [wb_extract.csv](./wb_extract.csv), [wb_hlos_supplement.csv](./wb_hlos_supplement.csv), [docs/SOURCE_STATUS.md](/home/ubuntu/cyto/indiamacro/docs/SOURCE_STATUS.md#L15).
- Suggested citation wording: "World Bank World Development Indicators / Human Capital Index, indicators [codes], accessed via the World Bank API on 20 Nov 2026" — not a citation of this package — [README.md](/home/ubuntu/cyto/indiamacro/README.md#L113-L117).

### Inferences
- Results are reproducible with the two scripts in this folder; re-running with the default cache may serve up to one-day-old responses, so pass `INDIAMACRO_NO_CACHE=1` for a fresh date stamp.
- Slow calls (researchers 84 s, R&D 69 s) are within the 90 s per-request timeout but close to it; a flaky connection could raise `SourceError` on those two, which would be an environment issue, not missing data.

### Gaps
- No systematic probe of all ~217 countries or all years was made; coverage statements apply only to IND, CHN, KOR, USA, DEU, BRA.
- Whether the World Bank will backfill post-2020 Indian R&D/researcher data, or revise historical values, cannot be determined from this snapshot.
