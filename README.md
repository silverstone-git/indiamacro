# indiamacro

India-first access to **free** macroeconomic data, with international data for comparison.
One `pip install`, tidy pandas output, consistent dates, and an on-disk cache.

```python
import indiamacro as im

im.india.snapshot()                         # latest headline numbers, with sources
im.india.cpi_inflation()                    # official MoSPI CPI inflation, monthly
im.compare("gdp_growth", "BRICS")           # India vs peers, incl. IMF projections
im.mospi.nas(9, freq="Q")                   # any MoSPI table - here quarterly GFCF
im.bis.credit_gap(["IND", "CHN"])           # BIS credit-to-GDP gap
im.pwt.get(["hc", "rtfpna"], "IND")         # Penn World Table: human capital, TFP
```

## Sources

| Module | Source | What you get | Key needed |
|---|---|---|---|
| `mospi` | MoSPI eSankhyiki API | GDP/GVA and components (annual + quarterly), CPI, WPI, IIP, PLFS jobs data | no |
| `mospi.rbi` | RBI tables via MoSPI | Balance of payments, trade, exchange rates, forex reserves, external debt (39 tables) | no |
| `budget` | indiabudget.gov.in | Budget at a Glance, Annual Financial Statement, expenditure workbooks (raw sheets) | no |
| `fred` | St. Louis Fed FRED | 800k+ series; daily USD/INR, OECD MEI data for India | no (key enables `search`) |
| `worldbank` | World Bank WDI | ~1,500 annual development indicators, ~217 countries | no |
| `imf` | IMF WEO + SDMX API | Headline macro + **5-year projections**; any IMF dataset via `imf.sdmx` | no |
| `oecd` | OECD Data Explorer | Composite leading indicators, any OECD dataset via `oecd.get` | no |
| `bis` | Bank for International Settlements | Policy rates, REER/NEER, credit gaps, private credit, house prices | no |
| `pwt` | Penn World Table 11.0 | PPP GDP, capital, human capital, TFP, 185 countries since 1950 | no |
| `owid` | Our World in Data | Any OWID chart's data (Maddison GDP back to 1 CE, poverty, inequality...) | no |

Run `uv run indiamacro-ping` to test every source live; the last run is in
[docs/SOURCE_STATUS.md](docs/SOURCE_STATUS.md). [docs/SOURCES.md](docs/SOURCES.md)
lists codes, coverage and quirks for each source.

**Not automated:** RBI's own DBIE portal (its API needs registration, session tokens
and a captcha; the main RBI tables come via MoSPI and BIS instead) and CMIE (paid).

## Install

```bash
cd indiamacro
uv sync                    # or: pip install -e .
uv run pytest              # offline unit tests
uv run pytest -m live      # live tests against every source
uv run --extra plot python examples/india_vs_peers.py   # charts -> examples/output/
```

## Conventions

- **Long format.** Source functions return `date, country, series, value` (plus
  source-specific columns). `im.wide(df)` pivots to a date x country table.
- **Dates mark the start of the period.** 2024 -> 2024-01-01, Q2 -> 04-01, and
  Indian fiscal year 2024-25 -> 2024-04-01. The original label is kept in `period`.
- **Countries** can be names, ISO2 or ISO3 codes, or groups: `BRICS`, `BRICS+`, `G7`,
  `G20`, `SOUTH_ASIA`, `ASEAN`, `EM_ASIA`, `QUAD`. India always comes first.
- **`india.*` functions** return a `pandas.Series` whose `.attrs` hold the source,
  unit and notes, which is everything you need for a chart caption or citation.
- **Caching.** Responses are cached in `~/.cache/indiamacro` for a day (Penn World
  Table forever). `im.settings.cache = False` or `im.clear_cache()` to refresh.

## Things that will trip you up (and impress your professor if you handle them)

1. **Base-year changes.** India rebased GDP and IIP to 2022-23 and CPI to 2024 in
   2025-26. Old- and new-base series are different series; every MoSPI function
   returns a `base_year` column. Compare growth rates across bases, not levels.
2. **Revisions.** GDP goes through advance, provisional, revised and final estimates.
   `mospi.nas()` returns all vintages in `revision`; `india.gdp()` keeps the latest.
3. **Fiscal vs calendar years.** MoSPI and the IMF report India by fiscal year
   (IMF "2024" = FY 2024-25). World Bank data for India are fiscal-year based too.
4. **Projections.** IMF WEO mixes actuals and forecasts; `imf.weo()` flags them in a
   `projection` column (from the IMF's own "latest actual" metadata).
5. **Freshness.** The MoSPI API can lag the official press releases (as of Oct 2026
   the base-2024 CPI and post-April-2026 WPI weren't loaded yet). For the very
   latest print, check the MoSPI/RBI press release and say so in your footnote.

## Citing

Cite the original producer, not this package: e.g. *National Statistics Office,
MoSPI, CPI (base 2012=100), accessed via the eSankhyiki API on 8 Oct 2026*. Each
`india.*` series carries its source in `s.attrs["source"]`; PWT and OWID modules
document their required citations.
