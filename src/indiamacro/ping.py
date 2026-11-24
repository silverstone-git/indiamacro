"""Ping every source with a small real query and report what came back.

    uv run indiamacro-ping                      # table in the terminal
    uv run indiamacro-ping --markdown STATUS.md # also write a Markdown report
    uv run indiamacro-ping --fresh              # bypass the cache
"""

from __future__ import annotations

import argparse
import datetime as dt
import time
from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd

from . import _http
from .sources import bis, budget, energy, fred, imf, mospi, oecd, owid, pwt, worldbank


@dataclass
class Check:
    source: str
    what: str
    run: Callable[[], pd.DataFrame]  # returns a DataFrame with ``date`` and a value column


def _latest(df: pd.DataFrame, col: str = "value") -> tuple[str, str]:
    row = df.dropna(subset=[col]).sort_values("date").iloc[-1]
    return str(pd.Timestamp(row["date"]).date()), f"{row[col]:,.2f}"


CHECKS = [
    Check("MoSPI - National Accounts", "India real GDP, annual (Rs crore)",
          lambda: mospi.nas(5).rename(columns={"constant_price": "value"})),
    Check("MoSPI - CPI", "India CPI general index, all-India combined",
          lambda: mospi.cpi(year=2025).query("group == 'General'").rename(columns={"index": "value"})),
    Check("MoSPI - WPI", "India WPI, all commodities (latest year)",
          lambda: mospi.wpi_headline(start_year=pd.Timestamp.today().year - 1).rename(columns={"index": "value"})),
    Check("MoSPI - IIP", "India industrial production, general index",
          lambda: mospi.iip().rename(columns={"index": "value"})),
    Check("MoSPI - PLFS", "India unemployment rate, monthly (%)",
          lambda: mospi.plfs(3, freq="M")),
    Check("RBI (via MoSPI)", "USD/INR monthly reference rate",
          lambda: mospi.rbi(33).query("currency == 'US Dollar' and reference_rate == 'Average'")),
    Check("Union Budget", "Budget at a Glance workbook (sheets)",
          lambda: pd.DataFrame({"date": [pd.Timestamp.today()], "value": [float(len(budget.workbook()))]})),
    Check("FRED", "INR per USD, daily (DEXINUS)", lambda: fred.get("DEXINUS", start="2026-01-01")),
    Check("World Bank WDI", "India GDP growth, annual (%)",
          lambda: worldbank.get("NY.GDP.MKTP.KD.ZG", "IND", start=2015)),
    Check("IMF WEO", "India real GDP growth incl. projections (%)", lambda: imf.weo("NGDP_RPCH", "IND")),
    Check("IMF SDMX", "WEO via SDMX API, India inflation (%)",
          lambda: imf.sdmx("WEO", "IND.PCPIPCH.A", start=2015)),
    Check("OECD", "India composite leading indicator", lambda: oecd.cli("IND", start="2024-01")),
    Check("BIS", "RBI policy rate, monthly (%)", lambda: bis.policy_rate("IND", start="2024")),
    Check("BIS", "India real effective exchange rate", lambda: bis.reer("IND", start="2024")),
    Check("Penn World Table 11.0", "India human capital index", lambda: pwt.get("hc", "IND")),
    Check("Our World in Data", "India GDP per capita (Maddison)",
          lambda: owid.get("gdp-per-capita-maddison-project-database", "IND")),
    Check("EIA spot (via FRED)", "Diesel crack vs Brent, daily (US$/bbl)",
          lambda: energy.cracks(start="2026-01-01").reset_index().rename(columns={"diesel_crack": "value"})),
    Check("NYMEX futures (Yahoo)", "Brent front-month (US$/bbl)",
          lambda: energy.futures(["BZ"], start="2026-01-01").reset_index(names="date").rename(columns={"BZ": "value"})),
    Check("World Bank Pink Sheet", "Dubai crude, monthly (US$/bbl)",
          lambda: energy.pink_sheet().reset_index().rename(columns={"Crude oil, Dubai": "value"})),
    Check("PPAC", "Indian crude basket, current fiscal year (US$/bbl)",
          lambda: energy.indian_basket().reset_index().rename(columns={"official": "value"})),
    Check("JODI Oil", "Saudi crude exports (kb/d)",
          lambda: energy.jodi("TOTEXPSB", "CRUDEOIL", countries="SAU", start_year=pd.Timestamp.today().year - 1)),
    Check("CREA Russia tracker", "Russian crude exports to India (t/month)",
          lambda: energy.russia_exports("destination", start="2026-01-01", commodity="crude_oil")
          .query("destination_country == 'India'").rename(columns={"value_tonne": "value"})),
    Check("IMF PortWatch", "Strait of Hormuz vessel transits (per day)",
          lambda: energy.chokepoints("Strait of Hormuz", start="2026-01-01").rename(columns={"n_total": "value"})),
    Check("UN Comtrade", "India crude imports, one month (US$)",
          lambda: energy.comtrade("IND", "crude", months=1, end=pd.Timestamp.today() - pd.DateOffset(months=4))
          .groupby("date", as_index=False)["value_usd"].sum().rename(columns={"value_usd": "value"})),
    # terminal live feeds (monitor.feeds); a simulated fallback counts as a failure here
    Check("USGS earthquakes", "M4.5+ quakes, past 7 days (magnitude)",
          lambda: _feed(lambda f: f.quakes(), "time", "mag", unit="ms")),
    Check("NASA EONET", "Open natural events, past 30 days (count per day)",
          lambda: _feed(lambda f: f.natural_events(), "date", None)),
    Check("OpenSky Network", "Aircraft over India now (count)",
          lambda: _feed(lambda f: f.aircraft(), None, None)),
    Check("Open-Meteo", "PM2.5 in tracked cities now (µg/m³)",
          lambda: _feed(lambda f: f.weather(), "time", "pm25")),
    Check("CelesTrak", "GNSS satellites with current elements (count)",
          lambda: _feed(lambda f: f.satellites("gnss"), None, None)),
    Check("Yahoo Finance", "Terminal watchlist, 5-min bars (latest quote)",
          lambda: _feed(lambda f: f.quotes(), "time", "last")),
]


def _feed(get, date_col: str | None, value_col: str | None, unit: str | None = None) -> pd.DataFrame:
    """Turn a terminal feed envelope into ``date, value`` rows (count per date if ``value_col`` is None)."""
    from .monitor import feeds

    feeds.clear()
    env = get(feeds)
    if env["status"] != "live":
        raise _http.SourceError(env["feed"], f"fell back to simulation: {env['note']}")
    df = pd.DataFrame(env["data"])
    if date_col is None:
        return pd.DataFrame({"date": [pd.Timestamp.now().normalize()], "value": [float(len(df))]})
    df["date"] = (pd.to_datetime(df[date_col], unit=unit) if unit else
                  pd.to_datetime(df[date_col], utc=True, errors="coerce").dt.tz_localize(None))
    if value_col is None:
        return df.groupby(df["date"].dt.normalize()).size().rename("value").reset_index()
    return df.rename(columns={value_col: "value"})[["date", "value"]].dropna()

NOT_AUTOMATED = [
    ("RBI DBIE (data.rbi.org.in)", "API needs registration, session tokens and a captcha; "
     "the main RBI tables are reachable via MoSPI (`mospi.rbi`) and BIS instead. "
     "For anything else, download from DBIE by hand."),
    ("CMIE Economic Outlook", "Paid - check if your college library subscribes."),
]


def run(fresh: bool = False, verbose: bool = True) -> pd.DataFrame:
    if fresh:
        _http.settings.cache = False
    rows = []
    for c in CHECKS:
        t = time.perf_counter()
        try:
            df = c.run()
            date, value = _latest(df)
            rows.append({"source": c.source, "query": c.what, "status": "OK", "rows": len(df),
                         "latest_date": date, "latest_value": value, "seconds": round(time.perf_counter() - t, 1)})
        except Exception as e:
            rows.append({"source": c.source, "query": c.what, "status": "FAIL", "rows": 0,
                         "latest_date": "", "latest_value": f"{type(e).__name__}: {str(e)[:100]}",
                         "seconds": round(time.perf_counter() - t, 1)})
        r = rows[-1]
        if verbose:
            print(f"{r['status']:4}  {r['source']:28} {r['query']:48} {r['latest_date']:>10}  {r['latest_value']}")
    return pd.DataFrame(rows)


def to_markdown(df: pd.DataFrame) -> str:
    lines = [f"# Source status - {dt.date.today()}", "",
             f"{(df.status == 'OK').sum()} of {len(df)} checks passed.", "",
             "| Source | Query | Status | Rows | Latest | Value | Time (s) |",
             "|---|---|---|---:|---|---:|---:|"]
    for r in df.itertuples():
        lines.append(f"| {r.source} | {r.query} | {r.status} | {r.rows} | {r.latest_date} | "
                     f"{r.latest_value} | {r.seconds} |")
    lines += ["", "## Not automated", ""]
    lines += [f"- **{name}** - {why}" for name, why in NOT_AUTOMATED]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--markdown", metavar="FILE", help="write a Markdown report to FILE")
    ap.add_argument("--fresh", action="store_true", help="ignore the on-disk cache")
    args = ap.parse_args(argv)
    df = run(fresh=args.fresh)
    print(f"\n{(df.status == 'OK').sum()}/{len(df)} OK")
    if args.markdown:
        with open(args.markdown, "w") as f:
            f.write(to_markdown(df))
        print(f"wrote {args.markdown}")
    return 0 if (df.status == "OK").all() else 1


if __name__ == "__main__":
    raise SystemExit(main())
