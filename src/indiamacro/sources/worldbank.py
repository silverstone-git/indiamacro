"""World Bank World Development Indicators (WDI) - annual, ~1,500 indicators, ~217 economies."""

from __future__ import annotations

import pandas as pd

from .. import _http, countries as _countries

SOURCE = "worldbank"
BASE = "https://api.worldbank.org/v2"

# Common indicator codes.
INDICATORS = {
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant 2021 international $)",
    "NY.GDP.PCAP.KD": "GDP per capita (constant 2015 US$)",
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labour force, ILO estimate)",
    "SL.TLF.CACT.FE.ZS": "Female labour force participation rate (%)",
    "NE.EXP.GNFS.ZS": "Exports of goods and services (% of GDP)",
    "NE.IMP.GNFS.ZS": "Imports of goods and services (% of GDP)",
    "NE.GDI.TOTL.ZS": "Gross capital formation (% of GDP)",
    "NY.GNS.ICTR.ZS": "Gross savings (% of GDP)",
    "BN.CAB.XOKA.GD.ZS": "Current account balance (% of GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "FDI, net inflows (% of GDP)",
    "GC.DOD.TOTL.GD.ZS": "Central government debt (% of GDP)",
    "FI.RES.TOTL.CD": "Total reserves incl. gold (current US$)",
    "SI.POV.DDAY": "Poverty headcount at $3.00/day (2021 PPP, % of population)",
    "SI.POV.GINI": "Gini index",
    "SP.POP.TOTL": "Population, total",
    "SP.URB.TOTL.IN.ZS": "Urban population (% of total)",
    "NV.AGR.TOTL.ZS": "Agriculture value added (% of GDP)",
    "NV.IND.MANF.ZS": "Manufacturing value added (% of GDP)",
    "NV.SRV.TOTL.ZS": "Services value added (% of GDP)",
}


def get(indicator: str | list[str], countries="IND", start: int | None = None, end: int | None = None) -> pd.DataFrame:
    """Annual WDI data. ``countries`` takes names, ISO codes or a group like ``"BRICS"``.

    Returns long format: ``date, country, series, value, country_name, series_name``.
    """
    codes = _countries.expand(countries)
    inds = [indicator] if isinstance(indicator, str) else list(indicator)
    date = f"{start or 1960}:{end or 2100}" if (start or end) else None
    frames = []
    for ind in inds:
        rows = _paged(f"{BASE}/country/{';'.join(codes)}/indicator/{ind}", {"date": date})
        if not rows:
            raise _http.SourceError(SOURCE, f"no data for {ind} / {codes}")
        df = pd.DataFrame({
            "date": pd.to_datetime([f"{r['date']}-01-01" for r in rows]),
            "country": [r["countryiso3code"] for r in rows],
            "series": ind,
            "value": [r["value"] for r in rows],
            "country_name": [r["country"]["value"] for r in rows],
            "series_name": [r["indicator"]["value"] for r in rows],
        })
        frames.append(df)
    out = pd.concat(frames, ignore_index=True).sort_values(["series", "country", "date"], ignore_index=True)
    out["value"] = out["value"].astype(float)
    out.attrs["source"] = SOURCE
    return out


def _paged(url: str, params: dict) -> list[dict]:
    rows, page, pages = [], 1, 1
    while page <= pages:
        data = _http.get_json(url, {**params, "format": "json", "per_page": 20000, "page": page}, source=SOURCE)
        if isinstance(data, list) and data and "message" in data[0]:
            raise _http.SourceError(SOURCE, str(data[0]["message"]))
        if len(data) < 2 or data[1] is None:
            return rows
        pages = data[0]["pages"]
        rows.extend(data[1])
        page += 1
    return rows


def search(text: str) -> pd.DataFrame:
    """Search WDI indicator names (case-insensitive substring)."""
    rows = _paged(f"{BASE}/source/2/indicators", {})
    df = pd.DataFrame({"id": [r["id"] for r in rows], "name": [r["name"] for r in rows],
                       "unit": [r.get("unit", "") for r in rows]})
    return df[df["name"].str.contains(text, case=False, regex=False)].reset_index(drop=True)
