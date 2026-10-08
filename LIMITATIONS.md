# Limitations

What this package and dashboard **can't** do, where the numbers are approximations,
and what could break. Written October 2026 from what was observed while building
and testing it. Read this before citing anything in coursework.

Each item says **what** the limitation is, **why it matters**, and **what to do**.

---

## 1. Data you don't get

| Missing | Why | What to use instead |
|---|---|---|
| **RBI DBIE** (money supply, bank credit, interest rates, the RBI *Handbook*) | The API needs a registered subscription, session tokens, encoded payloads and a captcha. Not worked around on purpose. | Download from data.rbi.org.in by hand. Policy rate comes from BIS, exchange rates from FRED/BIS, external-sector tables from MoSPI. |
| **EIA's own API** (inventories, refinery runs, weekly petroleum status) | `api.eia.gov` timed out from the test machine. Needs a free key too. | FRED carries EIA's spot prices. For US stocks and refinery runs, get a free EIA key and call the API directly. |
| **European diesel (ICE gasoil), Singapore products, Urals, Dubai daily** | Paid (ICE, Platts, Argus). | US diesel prices as a proxy (see 3.2). Monthly Dubai comes from the Pink Sheet. For Urals, use monthly averages published by Russia's finance ministry (not automated). |
| **Ship-by-ship tanker tracking** (Kpler, Vortexa) | Paid. | CREA covers Russia only. Everyone else is monthly (JODI, Comtrade). |
| **IEA Oil Market Report**, **CMIE** | Paid. | Free IEA highlights; check whether your library subscribes to CMIE. |
| **War-risk insurance premiums and freight rates** | Quoted by brokers, Lloyd's List, Platts and the Baltic Exchange; not published freely. | Route usage from IMF PortWatch (`energy.chokepoints`) and tanker share prices (`energy.shipping_equities`) as a market proxy. |
| **China's customs data (GACC) and recent China data in Comtrade** | GACC blocks automated access; Comtrade's free tier returned no China records for 2025-26. | JODI's China product exports (monthly, ~3-month lag), or GACC releases downloaded by hand. |
| **China's strategic reserve levels** | China doesn't publish them. | JODI total crude stocks (commercial + strategic) and stock changes, monthly. Releases have to be inferred. |
| **Exports from Russia, Iraq and Iran in JODI** | They stopped reporting. | CREA for Russia. Partner-country imports in Comtrade (mirror data) for the others. |
| **Indian basket history** | PPAC serves only the current fiscal year without a login. | A Brent/Dubai proxy (see 3.1), or download PPAC's historical file after registering. |

## 2. Freshness: the API isn't always the latest print

Last observation seen on 8 Oct 2026:

| Series | Last data | Note |
|---|---|---|
| CPI (MoSPI, base 2012) | Dec 2025 | The new **base-2024 CPI** (from Jan 2026) isn't in the API yet. CPI-based charts stop at Dec 2025. |
| WPI (MoSPI) | Apr 2026 | Possibly awaiting the new WPI base. |
| Forex reserves (RBI table via MoSPI) | Jun 2025 | MoSPI's copy lags RBI's weekly supplement by over a year. |
| USD/INR monthly (RBI table via MoSPI) | Aug 2025 | Use `india.usdinr()` (FRED, daily) for current values. |
| Indian basket (PPAC) | Jul 2026 monthly | PPAC's page states a later daily value in a text note, which isn't parsed. |
| India crude imports (Comtrade) | Jun-Jul 2026 | Customs data lag 1-4 months. |
| JODI | Jul 2026 | 1-2 months lag; countries report at different speeds. |
| Chokepoint transits (IMF PortWatch) | 4 Oct 2026 | Daily, a few days' lag. |
| Penn World Table 11.0 | 2023 | Released Oct 2025; updated every few years. |
| World Bank WDI | 2025 (annual) | Some indicators lag 2-3 years (poverty, Gini). |

**What to do:** for the latest headline number, check the MoSPI/RBI/PPAC press
release and say so in a footnote. Every chart shows its last date, and tiles show
the observation date.

**Caching:** responses are cached for a day (Penn World Table forever). A number can
be up to 24 h staler than the source. Use "Re-download data" in the dashboard or
`im.clear_cache()` to refresh.

## 3. Proxies and approximations

1. **Indian basket proxy** = 75% Brent + 25% Dubai (Pink Sheet, monthly). PPAC's actual
   sweet/sour ratio changes month to month (61:39 to 79:21 in FY 2026-27). Where both
   exist, the proxy is within about $1/bbl on average, but individual months can differ
   by more. Label it as a proxy.
2. **Product prices are US prices** (New York Harbor and US Gulf Coast, from EIA).
   Russian refinery outages hit the European and Mediterranean diesel markets first.
   US cracks capture the global effect only partly, so event-study effects on diesel
   are probably *understated*.
3. **Crack spreads mix markets:** US product prices minus European Brent. That's the
   standard free approximation, but it includes transatlantic freight and regional
   factors, not just refining margins.
4. **Dated-to-frontline uses NYMEX Brent (BZ) and EIA's dated Brent assessment.** The
   real DFL is quoted against ICE Brent. The two assessments are also taken at
   different times of day, so small daily values are noise; only large moves (like
   today's +$25) are meaningful.
5. **Brent in rupees** uses the Fed's New York noon buying rate (FRED `DEXINUS`), not
   RBI's reference rate. They differ by a few paise.
6. **"Real" oil prices** are deflated by **US** CPI. An India-relevant real price would
   use Indian prices and the rupee.
7. **Chokepoint transits are AIS counts.** PortWatch counts ships by their AIS transponders.
   Ships that switch AIS off (common in conflict zones and for sanctioned trades) aren't
   counted, so transits are understated during a crisis. A drop from ~90 to ~3 vessels/day
   is far beyond what dark transits could explain; small changes are not.
8. **Tanker share prices are not freight rates.** They also move with the stock market,
   fleet supply and company news.
9. **IMF years for India are fiscal years** (IMF "2024" = April 2024-March 2025). The
   `projection` flag comes from the IMF's own "latest actual" metadata. If that call
   fails, the flag is NA and the rows count as actual.
10. **Comparisons mix IMF and World Bank** depending on the indicator (see
   `compare.INDICATORS`). Definitions differ slightly, e.g. general vs central
   government debt.

## 4. Method limitations of the analysis templates

These are teaching templates, not publishable estimates.

**Event studies** (refinery strikes, reserve releases, event lab)
- **Constant-mean model:** the "abnormal" change is the change minus its average over
  trading days -120 to -21. Nothing controls for what the rest of the market did
  (no market model, no other regressors).
- **Small samples:** the built-in list has 5 refinery-strike and 4 reserve-release
  events. With N = 4-5, t-statistics are fragile and one outlier can drive the mean.
  The t-stat assumes events are independent; March 2024's strikes three days apart
  are not.
- **Overlapping events:** events close together contaminate each other's windows,
  including the estimation window. The Abqaiq attack (2019) is crude-processing
  infrastructure, not a refinery, yet it sits in the same category.
- **Timing:** day 0 is the first trading day on or after the event date. News that
  broke after the market closed shows up on day +1. Leaks (common before reserve
  releases) show up before day 0.
- **Built-in events end in 2024** and include only well-documented dates, plus one dated
  from the data itself: the collapse in Strait of Hormuz transits on 2 March 2026
  (PortWatch). Other 2025-26 shocks are **not** in the list; add them, with sources,
  on the Events page.

**Oil pass-through to India**
- Lagged **correlations**, not causal pass-through. A defensible estimate needs a
  distributed-lag regression or a VAR with controls.
- CPI "Fuel and light" covers cooking gas, kerosene and electricity, **not
  petrol/diesel** (those sit in transport). Retail fuel prices are partly
  administered, so CPI pass-through can be near zero for long stretches.

**Inflation regimes**
- A before/after comparison around August 2016. It can't separate inflation
  targeting from oil prices, food supply or COVID. The "before" period is short (CPI
  2012-base data start in 2013).

**Growth accounting**
- The capital share is fixed at 1 - (average labour share), and TFP is the residual,
  so it absorbs every measurement error.
- **India's employment in PWT 11.0 jumps 36% over 2018-2023** (493M to 670M, following
  PLFS). Output per worker and TFP for the 2020s turn negative because of this. The
  page warns about it, but any per-worker conclusion for recent years is unreliable.

**Real repo rate** is ex-post (repo minus current CPI), not repo minus expected inflation.

## 5. India-specific data quirks

- **Base-year breaks:** GDP has a 2011-12 and a 2022-23 base. The new base has only four
  annual points so far. Quarterly growth is computed *within* each base and never
  spliced. IIP likewise (2011-12 / 2022-23). Don't join old and new levels.
- **GDP revisions:** annual GDP comes as advance, provisional, revised and final
  estimates. `india.gdp()` keeps the most final one available, so a recent year's
  number will change as later estimates arrive.
- **PLFS:** monthly estimates start in 2025; annual from 2017-18. Status definitions
  (current weekly status vs usual status) give different unemployment rates. The
  dashboard uses CWS where available.
- **2020 gaps:** CPI wasn't published for April-May 2020 (COVID lockdown).

## 6. Fragile connections: things that may break

Several sources are used through endpoints that are undocumented or scraped. They
work today but can change without notice:

| Source | How it's reached | Failure mode |
|---|---|---|
| MoSPI | Public API, but needs TLS legacy renegotiation; the RBI tables use an endpoint (`rbi/getRbiRecords`) that isn't in the Swagger docs | Server TLS update, endpoint removal |
| MoSPI WPI | Ignores its documented filters; the headline is fetched as the first row of each month, with a full-month scan as fallback | Slow (minutes) if the ordering changes |
| PPAC | Internal AJAX endpoint (`AjaxController/...`) | Site redesign |
| World Bank Pink Sheet | File link scraped from the commodity-markets page (the URL changes monthly) | Page redesign |
| JODI | CSV links scraped from the download page | Page redesign |
| Yahoo Finance | Unofficial, via `yfinance` | Rate limits, API changes (yfinance usually updates quickly) |
| FRED keyless CSV | Works only with the default python-requests User-Agent | UA policy change; fall back to a free API key |
| IMF DataMapper | Blocks browser User-Agents | UA policy change |
| CREA | `v0` API | Version change |
| UN Comtrade | Free preview: 1 month per request, max 500 rows | Rate limiting; tightened free tier |
| OECD | Anonymous rate limit | Errors after many uncached queries |

`uv run indiamacro-ping` checks all 23 connections in under a minute. When one fails,
the dashboard shows an error card in place of that chart and everything else still loads.

## 7. Dashboard limitations

- **Local and single-user.** No login and no access control. `--host 0.0.0.0` exposes
  it, *including the ability to add and delete events*, to anyone on your network.
- **Needs internet** for the charting library (Plotly, from jsdelivr) and fonts (Google
  Fonts), as well as for data.
- **Slow first loads:** pages that hit Comtrade (12 requests) or several World Bank
  indicators take 60-90 s the first time; later loads come from cache.
- **Caches:** results are kept in memory for 10 minutes, downloads on disk for a day.
  "Refresh pages" recomputes from the disk cache. "Re-download data" deletes the
  whole disk cache, including the Penn World Table file.
- Tested in Chromium on Linux (desktop and narrow widths). Other browsers should work
  but weren't tested.

## 8. Testing limitations

- **Offline tests** (43) cover date handling, pagination, the event-study maths, the
  events store, chart specs and server helpers. They don't contain recorded
  responses from each source, so a change in a source's format is caught only by the
  live tests.
- **Live tests** (49) check that every source returns data and every page renders
  without errors. They check that numbers *exist and are shaped right*, not that
  they are *correct*. Correctness was spot-checked by hand: PPAC vs proxy, IMF vs
  World Bank growth, Yahoo vs FRED prices, CREA vs Comtrade (India's Russian share
  ~53-54% in both).

## 9. Not advice

This is a study tool. Prices from free sources are delayed and unofficial; don't use
them for trading. Cite the original producer (MoSPI, RBI, IMF, EIA, ...), not this
package, and note the access date.
