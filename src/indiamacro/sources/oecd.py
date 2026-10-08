"""OECD Data Explorer (SDMX). India is a key partner, so many OECD datasets include it.

Find dataflow ids and keys at https://data-explorer.oecd.org - open a table,
then "Developer API" shows the exact ``flow`` and ``key`` to pass to :func:`get`.
The OECD rate-limits anonymous use, so results are cached for a day.
"""

from __future__ import annotations

import io

import pandas as pd

from .. import _http, countries as _countries
from ..utils import parse_period

SOURCE = "oecd"
BASE = "https://sdmx.oecd.org/public/rest/data"

CLI_FLOW = "OECD.SDD.STES,DSD_STES@DF_CLI,4.1"


def get(flow: str, key: str = "all", start=None, end=None) -> pd.DataFrame:
    """Raw query; returns the labelled CSV plus ``date`` and ``value`` columns."""
    body = _http.get(f"{BASE}/{flow}/{key}",
                     {"startPeriod": start, "endPeriod": end, "format": "csvfilewithlabels"}, source=SOURCE)
    df = pd.read_csv(io.BytesIO(body), low_memory=False)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no data for {flow}/{key}")
    df["date"] = df["TIME_PERIOD"].map(parse_period)
    df["value"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df.attrs["source"] = SOURCE
    return df


def cli(countries="IND", start=None) -> pd.DataFrame:
    """Composite Leading Indicator (amplitude adjusted, long-term average = 100).

    Above 100 and rising = expansion ahead; it tends to turn 6-9 months before activity.
    Returns long format: ``date, country, series, value``.
    """
    codes = "+".join(_countries.expand(countries))
    df = get(CLI_FLOW, f"{codes}.M.LI...AA...H", start=start)
    out = df.rename(columns={"REF_AREA": "country"}).assign(series="CLI")
    out = out[["date", "country", "series", "value"]].sort_values(["country", "date"], ignore_index=True)
    out.attrs["source"] = SOURCE
    return out
