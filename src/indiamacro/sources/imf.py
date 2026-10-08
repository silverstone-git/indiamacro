"""IMF data.

* :func:`weo` - World Economic Outlook via the DataMapper API: ~130 headline
  indicators, all countries, annual, **including IMF projections ~5 years ahead**.
* :func:`sdmx` - any dataset on the IMF SDMX 2.1 API (api.imf.org), e.g. WEO,
  CPI, IFS-successor datasets. Browse at https://data.imf.org.
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http, countries as _countries
from ..utils import parse_period

SOURCE = "imf"
DATAMAPPER = "https://www.imf.org/external/datamapper/api/v1"
SDMX = "https://api.imf.org/external/sdmx/2.1"

WEO = {
    "NGDP_RPCH": "Real GDP growth (%)",
    "NGDPD": "GDP, current prices (billions of US$)",
    "PPPGDP": "GDP, PPP (billions of international $)",
    "NGDPDPC": "GDP per capita, current prices (US$)",
    "PPPPC": "GDP per capita, PPP (international $)",
    "PPPSH": "Share of world GDP at PPP (%)",
    "PCPIPCH": "Inflation, average consumer prices (%)",
    "LUR": "Unemployment rate (%)",
    "GGXWDG_NGDP": "General government gross debt (% of GDP)",
    "GGXCNL_NGDP": "General government net lending/borrowing (% of GDP)",
    "BCA_NGDPD": "Current account balance (% of GDP)",
}


def weo(indicator: str | list[str], countries="IND", start: int | None = None, end: int | None = None) -> pd.DataFrame:
    """World Economic Outlook series, including IMF projections.

    Returns long format: ``date, country, series, value, projection`` where
    ``projection`` is True for years after the latest actual data.
    """
    codes = _countries.expand(countries)
    inds = [indicator] if isinstance(indicator, str) else list(indicator)
    frames = []
    for ind in inds:
        # The country segment in the URL is ignored by the server; filter client-side.
        data = _http.get_json(f"{DATAMAPPER}/{ind}", source=SOURCE)
        by_country = data.get("values", {}).get(ind)
        if not by_country:
            raise _http.SourceError(SOURCE, f"unknown WEO indicator {ind!r} (see imf.indicators())")
        rows = [(int(y), c, v) for c in codes for y, v in by_country.get(c, {}).items()]
        frames.append(pd.DataFrame(rows, columns=["year", "country", "value"]).assign(series=ind))
    df = pd.concat(frames, ignore_index=True)
    if start:
        df = df[df["year"] >= start]
    if end:
        df = df[df["year"] <= end]
    df["date"] = pd.to_datetime(df["year"].astype(str) + "-01-01")
    last = latest_actual(inds, codes)
    df["projection"] = [
        (y > last[(c, i)]) if (c, i) in last else pd.NA
        for y, c, i in zip(df["year"], df["country"], df["series"])
    ]
    out = df[["date", "country", "series", "value", "projection"]]
    out = out.sort_values(["series", "country", "date"], ignore_index=True)
    out.attrs["source"] = SOURCE
    return out


def latest_actual(indicators: list[str], countries: list[str]) -> dict[tuple[str, str], int]:
    """{(country, indicator): last year that is data rather than projection}, from WEO metadata.

    India reports by fiscal year and the IMF maps FY t/t+1 to year t, so 'FY2024/25' -> 2024.
    Returns an empty dict if the metadata can't be fetched (``projection`` is then NA).
    """
    try:
        df = sdmx("WEO", f"{'+'.join(countries)}.{'+'.join(indicators)}.A", start=2015)
    except _http.SourceError:
        return {}
    meta = df[["COUNTRY", "INDICATOR", "LATEST_ACTUAL_ANNUAL_DATA"]].dropna().drop_duplicates()
    years = meta["LATEST_ACTUAL_ANNUAL_DATA"].astype(str).str.extract(r"(\d{4})")[0]
    return {(c, i): int(y) for c, i, y in zip(meta["COUNTRY"], meta["INDICATOR"], years) if pd.notna(y)}


def indicators() -> pd.DataFrame:
    """All DataMapper indicators (code, label, unit, dataset)."""
    data = _http.get_json(f"{DATAMAPPER}/indicators", ttl=7 * _http.DAY, source=SOURCE)
    rows = [{"code": k, "label": v.get("label"), "unit": v.get("unit"), "dataset": v.get("dataset"),
             "description": v.get("description")} for k, v in data["indicators"].items() if k]
    return pd.DataFrame(rows)


def sdmx(dataflow: str, key: str, start=None, end=None) -> pd.DataFrame:
    """Raw SDMX query, e.g. ``sdmx("WEO", "IND.NGDP_RPCH.A")``.

    Keys are dot-separated dimension values; ``+`` joins alternatives and an empty
    slot is a wildcard. Returns the CSV with ``date`` and ``value`` columns added.
    """
    body = _http.get(f"{SDMX}/data/{dataflow}/{key}",
                     {"startPeriod": start, "endPeriod": end},
                     headers={"Accept": "text/csv"}, source=SOURCE)
    df = pd.read_csv(io.BytesIO(body), low_memory=False)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no data for {dataflow}/{key}")
    df["date"] = df["TIME_PERIOD"].map(parse_period)
    df["value"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df.attrs["source"] = SOURCE
    return df
