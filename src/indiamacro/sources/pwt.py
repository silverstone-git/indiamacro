"""Penn World Table (Groningen Growth and Development Centre).

The standard dataset for long-run growth accounting: PPP-adjusted output, capital
stocks, human capital, TFP, for 185 countries from 1950. Version 11.0 covers to 2023.

Cite as: Feenstra, Inklaar and Timmer (2015), "The Next Generation of the Penn World
Table", American Economic Review 105(10), www.ggdc.net/pwt.
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http, countries as _countries

SOURCE = "pwt"

# Dataverse file ids for the main Stata file of each release.
FILES = {"11.0": 554030, "10.01": 354098}
LATEST = "11.0"

VARIABLES = {
    "rgdpe": "Expenditure-side real GDP at chained PPPs (mn 2021 US$)",
    "rgdpo": "Output-side real GDP at chained PPPs (mn 2021 US$)",
    "rgdpna": "Real GDP at constant national prices (mn 2021 US$) - use for growth rates",
    "pop": "Population (millions)",
    "emp": "Persons engaged (millions)",
    "avh": "Average annual hours worked",
    "hc": "Human capital index (years of schooling and returns to education)",
    "cn": "Capital stock at current PPPs",
    "rnna": "Capital stock at constant national prices",
    "ctfp": "TFP level at current PPPs (USA = 1)",
    "rtfpna": "TFP at constant national prices (2021 = 1)",
    "labsh": "Share of labour compensation in GDP",
    "csh_c": "Share of household consumption in CGDPo",
    "csh_i": "Share of gross capital formation in CGDPo",
    "csh_g": "Share of government consumption in CGDPo",
    "csh_x": "Share of merchandise exports in CGDPo",
    "xr": "Exchange rate (national currency per US$)",
    "pl_gdpo": "Price level of CGDPo (USA 2021 = 1)",
}


def load(version: str = LATEST) -> pd.DataFrame:
    """The full table (one row per country-year). Downloaded once, then cached on disk."""
    body = _http.get(f"https://dataverse.nl/api/access/datafile/{FILES[version]}",
                     ttl=_http.FOREVER, source=SOURCE)
    if not body.startswith(b"<stata_dta>"):
        raise _http.SourceError(SOURCE, "download was not a Stata file (bot check?) - try again later")
    df = pd.read_stata(io.BytesIO(body))
    df.attrs["source"] = SOURCE
    return df


def get(variables: str | list[str] = "rgdpna", countries="IND", version: str = LATEST) -> pd.DataFrame:
    """Selected variables in long format: ``date, country, series, value``."""
    vars_ = [variables] if isinstance(variables, str) else list(variables)
    df = load(version)
    df = df[df["countrycode"].isin(_countries.expand(countries))]
    long = df.melt(id_vars=["countrycode", "year"], value_vars=vars_, var_name="series")
    long["date"] = pd.to_datetime(long["year"].astype(int).astype(str) + "-01-01")
    out = long.rename(columns={"countrycode": "country"})[["date", "country", "series", "value"]]
    out = out.sort_values(["series", "country", "date"], ignore_index=True)
    out.attrs["source"] = SOURCE
    return out
