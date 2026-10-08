# Source catalogue

What each source offers, the codes worth knowing, and the quirks found while
building this package (probed October 2026).

## India

### MoSPI eSankhyiki - `im.mospi`
- **API:** `https://api.mospi.gov.in/api/...` - Swagger docs at https://api.mospi.gov.in . No key.
- **Quirks:** the server needs TLS *legacy renegotiation*, which OpenSSL 3 refuses by
  default (`curl` fails with `unsafe legacy renegotiation disabled`); the package
  enables it for this host only. Pages are capped at `limit=200`. The WPI endpoint
  ignores its documented commodity filters and capitalised `Year`/`Month_code` - use
  lowercase `year`/`month_code`.
- **NAS indicator codes** (`mospi.nas(code)`): 1 GVA, 5 GDP, 9 GFCF, 10 PFCE, 11 GFCE,
  14 exports, 15 imports, 17 GNI, 20 gross saving, 21 GVA growth, 22 GDP growth,
  23 GSDP (states). Full list: `mospi.NAS_INDICATORS`.
- **PLFS indicator codes** (`mospi.plfs(code)`): 1 LFPR, 2 WPR, 3 unemployment,
  6-8 earnings. Frequencies: annual (2017-18+), quarterly (urban), monthly (2025+).
- **CPI:** `state_code=99` all-India; `sector_code` 1 rural / 2 urban / 3 combined.
  Headline is `group == "General"`; food is `subgroup == "Consumer Food Price-Overall"`.
- **Base years:** GDP 2011-12 and 2022-23; IIP 2011-12 and 2022-23; CPI 2012 (2024 pending in API).

### RBI tables via MoSPI - `im.mospi.rbi(code)`
`mospi.rbi_indicators()` lists all 39. Useful ones: 4 quarterly BoP (US$),
5 annual BoP (US$), 12 foreign trade (US$), 25 external debt (US$),
33 monthly INR exchange rates, 37 rates for 155 currencies, 40 NRI deposits,
47 monthly forex reserves, 28 RBI USD purchases/sales.

### RBI DBIE - not automated
https://data.rbi.org.in - money supply, credit, interest rates, the *Handbook of
Statistics on the Indian Economy*. Its API needs a registered subscription, session
tokens, encoded payloads and a captcha, so download from the site by hand. Policy
rates (BIS), exchange rates (FRED, BIS, MoSPI) and external-sector tables (MoSPI)
are covered elsewhere.

### Union Budget - `im.budget.workbook(name)`
Excel files from https://www.indiabudget.gov.in : `budget_at_a_glance` (deficits,
receipts, expenditure, transfers to states), `annual_financial_statement`,
`expenditure_summary`, `expenditure_by_ministry`. Returned raw (`header=None`)
because they are formatted reports. Past years: the budget archive.

## International

### FRED - `im.fred`
- Keyless CSV endpoint `fred.stlouisfed.org/graph/fredgraph.csv?id=...`.
- **Quirk:** the server resets connections for browser-like *and* custom User-Agents;
  the default `python-requests` one works.
- India series: `DEXINUS` (daily INR/USD), `INDCPIALLMINMEI` (CPI), `IRLTLT01INM156N`
  (10y yield), `MKTGDPINA646NWDB` (GDP US$). Search needs a free `FRED_API_KEY`.

### World Bank WDI - `im.worldbank`
- `api.worldbank.org/v2`, no key. `worldbank.search("gini")` searches indicator names.
- Codes: see `worldbank.INDICATORS` (growth, inflation, poverty, Gini, trade, FDI,
  sector shares, female labour participation...).

### IMF - `im.imf`
- `imf.weo(code)`: DataMapper API (`imf.org/external/datamapper/api/v1`). **Quirk:**
  returns 403 to browser User-Agents; ignores the country in the URL (we filter).
- `imf.sdmx(flow, key)`: SDMX 2.1 at `api.imf.org/external/sdmx/2.1`, CSV output,
  carries rich metadata (`LATEST_ACTUAL_ANNUAL_DATA`, methodology notes, citation).
- WEO codes: `imf.WEO`; all ~130: `imf.indicators()`.

### OECD - `im.oecd`
- SDMX at `sdmx.oecd.org/public/rest/data/{flow}/{key}`. Get `flow`/`key` from the
  "Developer API" button on https://data-explorer.oecd.org . Rate-limited; cached daily.
- `oecd.cli()` = composite leading indicator (India included).

### BIS - `im.bis`
- `stats.bis.org/api/v1/data/{flow}/{key}?format=csv`. Countries are ISO2 (`IN`).
- Helpers: `policy_rate`, `reer`, `usd_fx`, `credit_gap`, `total_credit`, `property_prices`.
  Credit datasets label the country `BORROWERS_CTY`, not `REF_AREA`.

### Penn World Table - `im.pwt`
- Stata files on dataverse.nl (`/api/access/datafile/554030` for 11.0). Browser
  User-Agents get a bot-check page; the API path works. Downloaded once, cached forever.
- Variables: `pwt.VARIABLES`. Use `rgdpna` for growth over time, `rgdpo`/`rgdpe` for
  cross-country level comparisons.
- Cite: Feenstra, Inklaar & Timmer (2015), *AER* 105(10).

### Our World in Data - `im.owid`
- `ourworldindata.org/grapher/{slug}.csv` - the slug is in any chart's URL.
- `owid.metadata(slug)` gives the underlying sources to cite.

## Energy - `im.energy`

| Function | Source | Notes |
|---|---|---|
| `prices()`, `cracks()` | EIA spot prices via FRED (`DCOILBRENTEU`, `DCOILWTICO`, `DDFUELNYH`, `DDFUELUSGULF`, `DJFUELUSGULF`, `DGASNYH`) | Daily; products converted from $/gal to $/bbl (x42). Cracks = product minus Brent. |
| `futures()`, `curve()` | NYMEX via Yahoo (`BZ=F`, `CL=F`, `HO=F`, `RB=F`; contracts like `BZZ26.NYM`) | Unlisted/expired contract months are skipped. |
| `dated_to_frontline()` | EIA dated Brent minus NYMEX front month | Physical tightness; normally within +/-$2. |
| `pink_sheet()` | World Bank Commodity Price Data | Monthly since 1960. The file URL changes each month; found from the commodity-markets page. |
| `indian_basket()` | PPAC (`AjaxController/getInternationalPricesCrudeOil`, form POST) | PPAC serves only the current fiscal year without a login; history is a 75/25 Brent/Dubai proxy. |
| `jodi()` | JODI Oil World Database annual CSVs (primary = crude, secondary = products) | Russia, Iraq, Iran don't report exports. Files are 5-10 MB per year (cached). |
| `comtrade()` | UN Comtrade public preview API | One month per request, max 500 rows; partner names from the reference JSON. |
| `russia_exports()` | CREA Russia Fossil Tracker API (`/v0/counter`) | Daily by commodity, monthly by destination; based on ship tracking. |
| `chokepoints()` | IMF PortWatch, ArcGIS feature service `Daily_Chokepoints_Data` | Daily transits (all vessels, tankers, tanker capacity) for 28 chokepoints from 2019; AIS-based; paged 2,000 rows per request. |
| `shipping_equities()` | Yahoo Finance (INSW, FRO, DHT, STNG, TRMD, ZIM) | Proxy for freight and insurance costs, not an index of either. |
| `jodi(..., countries="CHN")` | JODI secondary file | China's product exports: GASDIES, GASOLINE, RESFUEL, TOTPRODS (no separate jet fuel). China customs (GACC) blocks automated access; Comtrade's free tier has no recent China data. |

Not reachable from the test machine: EIA's own API (`api.eia.gov`, timed out; most EIA prices are on FRED).
Not free: ICE gasoil (European diesel), Platts/Argus assessments (Urals, Singapore products), Kpler/Vortexa tanker data, Baltic Exchange freight rates, and war-risk insurance premiums (trade press and brokers only; the Lloyd's Joint War Committee publishes listed areas, not prices).

## Not free
- **CMIE Economic Outlook / ProwessIQ** - paid; many college libraries subscribe.
