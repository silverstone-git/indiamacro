"""Bank for International Settlements - central-bank and financial-stability data.

Policy rates, effective exchange rates, credit-to-GDP gaps, property prices and
total credit for ~60 economies including India. Browse at https://data.bis.org.
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http, countries as _countries
from ..utils import parse_period

SOURCE = "bis"
BASE = "https://stats.bis.org/api/v1/data"


def get(flow: str, key: str, start=None, end=None) -> pd.DataFrame:
    """Raw query, e.g. ``get("WS_CBPOL", "M.IN")``; returns the CSV plus ``date`` and ``value``."""
    body = _http.get(f"{BASE}/{flow}/{key}", {"format": "csv", "startPeriod": start, "endPeriod": end},
                     source=SOURCE)
    df = pd.read_csv(io.BytesIO(body), low_memory=False)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no data for {flow}/{key}")
    df["date"] = df["TIME_PERIOD"].map(parse_period)
    df["value"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df.attrs["source"] = SOURCE
    return df


def _tidy(df: pd.DataFrame, series: str) -> pd.DataFrame:
    area = "REF_AREA" if "REF_AREA" in df else "BORROWERS_CTY"   # credit datasets name it differently
    out = df.assign(country=df[area].map(_countries.iso3), series=series)
    out = out[["date", "country", "series", "value"]].sort_values(["country", "date"], ignore_index=True)
    out.attrs["source"] = SOURCE
    return out


def _keys(countries) -> str:
    return "+".join(_countries.iso2(c) for c in _countries.expand(countries))


def policy_rate(countries="IND", freq: str = "M", start=None) -> pd.DataFrame:
    """Central-bank policy rate (RBI repo rate for India), end of period, %. ``freq`` is D or M."""
    return _tidy(get("WS_CBPOL", f"{freq}.{_keys(countries)}", start), "policy_rate")


def reer(countries="IND", real: bool = True, broad: bool = True, start=None) -> pd.DataFrame:
    """Effective exchange rate index (2020=100), monthly. Up = currency appreciation."""
    key = f"M.{'R' if real else 'N'}.{'B' if broad else 'N'}.{_keys(countries)}"
    return _tidy(get("WS_EER", key, start), "reer" if real else "neer")


def usd_fx(countries="IND", start=None) -> pd.DataFrame:
    """Local currency per US dollar, monthly average."""
    keys = "+".join(f"{_countries.iso2(c)}" for c in _countries.expand(countries))
    df = get("WS_XRU", f"M.{keys}..A", start)
    return _tidy(df, "usd_fx")


def credit_gap(countries="IND", start=None) -> pd.DataFrame:
    """Credit-to-GDP gap (percentage points), quarterly. Large positive gaps flag credit booms."""
    return _tidy(get("WS_CREDIT_GAP", f"Q.{_keys(countries)}.P.A.C", start), "credit_gap")


def total_credit(countries="IND", start=None) -> pd.DataFrame:
    """Credit to the private non-financial sector, % of GDP, quarterly."""
    return _tidy(get("WS_TC", f"Q.{_keys(countries)}.P.A.M.770.A", start), "private_credit_gdp")


def property_prices(countries="IND", start=None) -> pd.DataFrame:
    """Real residential property price index (2010=100), quarterly."""
    return _tidy(get("WS_SPP", f"Q.{_keys(countries)}.R.628", start), "real_house_prices")
