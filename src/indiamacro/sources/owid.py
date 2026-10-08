"""Our World in Data - cleaned, long-run datasets behind every OWID chart.

Any chart at ``ourworldindata.org/grapher/<slug>`` can be fetched with ``get("<slug>")``.
OWID compiles from primary sources (Maddison, World Bank, UN...), so cite the
original source listed in :func:`metadata` as well.
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http, countries as _countries

SOURCE = "owid"
BASE = "https://ourworldindata.org/grapher"

SLUGS = {
    "gdp-per-capita-maddison-project-database": "GDP per capita since 1 CE (Maddison)",
    "gdp-per-capita-worldbank": "GDP per capita, PPP (World Bank)",
    "share-of-population-in-extreme-poverty": "Extreme poverty headcount",
    "economic-inequality-gini-index": "Gini index",
    "life-expectancy": "Life expectancy",
    "co-emissions-per-capita": "CO2 emissions per capita",
}


def get(slug: str, countries=None) -> pd.DataFrame:
    """Chart data in long format: ``date, country, series, value`` (one series per data column).

    ``countries=None`` returns every entity, including regions like "World" (country = NaN).
    """
    body = _http.get(f"{BASE}/{slug}.csv", {"useColumnShortNames": "false"}, source=SOURCE)
    if body.lstrip().startswith(b"<"):
        raise _http.SourceError(SOURCE, f"unknown chart slug {slug!r}")
    df = pd.read_csv(io.BytesIO(body))
    time_col = "Year" if "Year" in df.columns else "Day"
    skip = {"Entity", "Code", time_col, "World region according to OWID", "World regions according to OWID"}
    value_cols = [c for c in df.columns if c not in skip]
    if countries is not None:
        df = df[df["Code"].isin(_countries.expand(countries))]
    long = df.melt(id_vars=["Entity", "Code", time_col], value_vars=value_cols, var_name="series")
    if time_col == "Year":
        long["date"] = pd.to_datetime(long["Year"].astype(int).astype(str) + "-01-01", errors="coerce")
    else:
        long["date"] = pd.to_datetime(long["Day"])
    out = long.rename(columns={"Code": "country", "Entity": "entity"})
    out = out[["date", "country", "series", "value", "entity"]].dropna(subset=["value"])
    out = out.sort_values(["series", "entity", "date"], ignore_index=True)
    out.attrs["source"] = SOURCE
    return out


def metadata(slug: str) -> dict:
    """Chart metadata, including the original sources and citation text."""
    return _http.get_json(f"{BASE}/{slug}.metadata.json", source=SOURCE)
