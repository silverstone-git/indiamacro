"""FRED (Federal Reserve Bank of St. Louis) - 800k+ series, including many for India.

Works without an API key through the public CSV download. Set ``FRED_API_KEY``
(free from https://fred.stlouisfed.org/docs/api/api_key.html) to enable
:func:`search` and :func:`info`.
"""

from __future__ import annotations

import io
import os

import pandas as pd

from .. import _http

SOURCE = "fred"

# Handy India-related series (all verified to exist).
INDIA = {
    "DEXINUS": "INR per USD, daily (Fed H.10)",
    "INDCPIALLMINMEI": "CPI all items, India (OECD MEI), monthly index",
    "MKTGDPINA646NWDB": "GDP, current USD (World Bank), annual",
    "INTDSRINM193N": "RBI discount rate (IMF IFS), monthly",
    "IRLTLT01INM156N": "10-year government bond yield, India, monthly",
}


def get(series: str | list[str], start=None, end=None) -> pd.DataFrame:
    """Observations for one or more FRED series ids.

    Returns long format: ``date, series, value``.
    """
    ids = [series] if isinstance(series, str) else list(series)
    frames = []
    for sid in ids:
        body = _http.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                         {"id": sid, "cosd": _iso(start), "coed": _iso(end)}, source=SOURCE)
        text = body.decode()
        if not text.startswith("observation_date"):
            raise _http.SourceError(SOURCE, f"unknown series {sid!r}")
        df = pd.read_csv(io.StringIO(text), na_values=["."])
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["series"] = sid
        frames.append(df[["date", "series", "value"]])
    out = pd.concat(frames, ignore_index=True)
    out.attrs["source"] = SOURCE
    return out


def series(series_id: str, start=None, end=None) -> pd.Series:
    """One FRED series as a date-indexed :class:`pandas.Series`."""
    df = get(series_id, start, end)
    return df.set_index("date")["value"].rename(series_id)


def _key() -> str:
    key = os.environ.get("FRED_API_KEY")
    if not key:
        raise _http.SourceError(SOURCE, "set FRED_API_KEY (free) to use search/info")
    return key


def search(text: str, limit: int = 50) -> pd.DataFrame:
    """Full-text search of FRED series (needs ``FRED_API_KEY``)."""
    data = _http.get_json("https://api.stlouisfed.org/fred/series/search",
                          {"search_text": text, "api_key": _key(), "file_type": "json", "limit": limit},
                          source=SOURCE)
    cols = ["id", "title", "frequency_short", "units_short", "observation_start", "observation_end", "popularity"]
    return pd.DataFrame(data["seriess"])[cols]


def info(series_id: str) -> dict:
    """Metadata for a series (needs ``FRED_API_KEY``)."""
    data = _http.get_json("https://api.stlouisfed.org/fred/series",
                          {"series_id": series_id, "api_key": _key(), "file_type": "json"}, source=SOURCE)
    return data["seriess"][0]


def _iso(d) -> str | None:
    return None if d is None else pd.Timestamp(str(d)).strftime("%Y-%m-%d")
