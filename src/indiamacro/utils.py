"""Helpers for Indian date conventions and common transformations.

Date convention used across the package: every row has a ``date`` that marks the
*start* of its period (2024 -> 2024-01-01, 2024-Q2 -> 2024-04-01, Indian fiscal year
2024-25 -> 2024-04-01). Where the source labels periods differently, the original
label is kept in a ``period`` column.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})

_FY = re.compile(r"^\s*(\d{4})\s*-\s*(\d{2}|\d{4})\s*$")


def fy_start(label: str) -> pd.Timestamp:
    """Indian fiscal-year label ('2024-25' or '2024-2025') -> 2024-04-01."""
    m = _FY.match(str(label))
    if not m:
        raise ValueError(f"not a fiscal-year label: {label!r}")
    return pd.Timestamp(int(m.group(1)), 4, 1)


def fy_label(date) -> str:
    """Date -> the Indian fiscal year it falls in, e.g. 2025-02-10 -> '2024-25'."""
    d = pd.Timestamp(date)
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def fy_quarter_start(fy: str, quarter: str | int) -> pd.Timestamp:
    """Fiscal year + quarter ('2024-25', 'Q1') -> calendar start date (2024-04-01).

    India's Q1 is Apr-Jun, Q2 Jul-Sep, Q3 Oct-Dec, Q4 Jan-Mar.
    """
    q = int(str(quarter).upper().lstrip("Q"))
    return fy_start(fy) + pd.DateOffset(months=3 * (q - 1))


def month_number(month) -> int:
    if isinstance(month, (int, np.integer)):
        return int(month)
    return MONTHS[str(month).strip().lower()]


def month_start(year, month) -> pd.Timestamp:
    return pd.Timestamp(int(year), month_number(month), 1)


def to_number(s: pd.Series) -> pd.Series:
    """Clean numeric strings from government sources: '1,234.5', '-', '', 'NA' -> float."""
    if s.dtype.kind in "if":
        return s.astype(float)
    cleaned = s.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(cleaned.replace({"-": None, "": None, "NA": None, "None": None, "nan": None}),
                         errors="coerce")



def parse_period(label: str) -> pd.Timestamp:
    """Parse SDMX period strings: 2024, 2024-06, 2024-Q2, 2024-S1, 2024-06-30.

    'YYYY-NN' always means a month here; use :func:`fy_start` for Indian fiscal years.
    """
    label = str(label).strip()
    if re.fullmatch(r"\d{4}", label):
        return pd.Timestamp(int(label), 1, 1)
    m = re.fullmatch(r"(\d{4})-?Q([1-4])", label)
    if m:
        return pd.Timestamp(int(m.group(1)), 3 * int(m.group(2)) - 2, 1)
    m = re.fullmatch(r"(\d{4})-?S([12])", label)
    if m:
        return pd.Timestamp(int(m.group(1)), 6 * int(m.group(2)) - 5, 1)
    m = re.fullmatch(r"(\d{4})-M?(\d{1,2})", label)
    if m:
        return pd.Timestamp(int(m.group(1)), int(m.group(2)), 1)
    return pd.Timestamp(label)


# ---------------------------------------------------------------- transformations

def wide(df: pd.DataFrame, columns: str = "country", values: str = "value", index: str = "date") -> pd.DataFrame:
    """Pivot a long frame (date, <columns>, value) into a date x <columns> table."""
    return df.pivot_table(index=index, columns=columns, values=values, aggfunc="last").sort_index()


def yoy(s: pd.Series | pd.DataFrame, periods: int | None = None) -> pd.Series | pd.DataFrame:
    """Year-on-year % change. ``periods`` defaults from the index frequency (12 monthly, 4 quarterly, 1 annual)."""
    if periods is None:
        periods = periods_per_year(s.index)
    return s.pct_change(periods, fill_method=None) * 100


def periods_per_year(index: pd.DatetimeIndex) -> int:
    """12 for monthly, 4 for quarterly, 1 for annual (from the median gap); daily is not supported."""
    gap = pd.Series(index).diff().dt.days.median()
    if gap < 20:
        raise ValueError("daily/weekly data: resample to monthly before computing year-on-year changes")
    return 12 if gap < 40 else 4 if gap < 120 else 1


def rebase(s: pd.Series | pd.DataFrame, base) -> pd.Series | pd.DataFrame:
    """Rescale so the value at ``base`` (a date, or a year for annual-average) is 100."""
    if isinstance(base, int):
        ref = s[s.index.year == base].mean()
    else:
        ref = s.loc[pd.Timestamp(base)]
    return s / ref * 100


def deflate(nominal: pd.Series, price_index: pd.Series, base=None) -> pd.Series:
    """Nominal -> real, using ``price_index`` (rebased to ``base`` if given)."""
    p = rebase(price_index, base) if base is not None else price_index
    p = p.reindex(nominal.index).interpolate(limit_area="inside")
    return nominal / p * 100


def cagr(s: pd.Series) -> float:
    """Compound annual growth rate (%) between the first and last non-missing values."""
    s = s.dropna()
    years = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
