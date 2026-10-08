"""MoSPI eSankhyiki API (Ministry of Statistics and Programme Implementation).

India's official statistics, straight from the producer: national accounts (GDP/GVA),
CPI, WPI, IIP, PLFS labour data, and RBI external-sector tables (BoP, trade,
exchange rates, forex reserves) republished through the same API.

API docs (Swagger): https://api.mospi.gov.in . No key needed. Pages are capped at
200 rows, so large unfiltered queries take many requests - filter where you can.

Base years matter. Several series were rebased in 2025-26 (GDP and IIP to 2022-23,
CPI to 2024). Old and new bases are *different series*; never splice them without
a linking factor. Every function returns a ``base_year`` column so you can tell.
"""

from __future__ import annotations

import pandas as pd

from .. import _http
from ..utils import fy_quarter_start, fy_start, month_start, to_number

SOURCE = "mospi"
BASE = "https://api.mospi.gov.in/api"
PAGE = 200

NAS_INDICATORS = {
    1: "Gross Value Added", 2: "Net Taxes on Products", 3: "Taxes on Products",
    4: "Subsidies on Products", 5: "Gross Domestic Product", 6: "Consumption of Fixed Capital",
    7: "Net Domestic Product", 8: "Gross Capital Formation by Industry of Use",
    9: "Gross Fixed Capital Formation", 10: "Private Final Consumption Expenditure",
    11: "Government Final Consumption Expenditure", 12: "Change in Stock", 13: "Valuables",
    14: "Export of Goods and Services", 15: "Import of Goods and Services",
    16: "Primary Income Receivable Net From RoW", 17: "Gross National Income",
    18: "Other Current Transfers Net From RoW", 19: "Gross National Disposable Income",
    20: "Gross Saving", 21: "GVA Growth Rate", 22: "GDP Growth Rate",
    23: "Gross State Domestic Product", 24: "Net State Domestic Product",
}

PLFS_INDICATORS = {
    1: "Labour Force Participation Rate (%)", 2: "Worker Population Ratio (%)",
    3: "Unemployment Rate (%)", 4: "Distribution of workers (%)",
    5: "Regular wage employees by employment conditions (%)",
    6: "Average monthly earnings, regular wage/salaried (Rs)",
    7: "Average daily wage, casual labour (Rs)", 8: "Average 30-day earnings, self-employed (Rs)",
}

# Codes that select the all-India headline aggregates.
ALL_INDIA = 99          # CPI state_code
COMBINED = 3            # CPI sector_code (1 rural, 2 urban, 3 combined)
PLFS_ALL_INDIA = 99
PLFS_PERSON = 3         # gender_code (1 male, 2 female, 3 person)
PLFS_RURAL_URBAN = 3    # sector_code (1 rural, 2 urban, 3 rural+urban)
PLFS_AGE_15_PLUS = 1


def query(path: str, max_pages: int | None = 50, **params) -> pd.DataFrame:
    """Call any eSankhyiki endpoint (e.g. ``"cpi/getCPIIndex"``) and fetch every page.

    Parameter names are as in the Swagger docs. Raises if more than ``max_pages``
    pages would be needed - add filters, or pass ``max_pages=None``.
    """
    params = {k: v for k, v in params.items() if v is not None}
    params = {k: (",".join(map(str, v)) if isinstance(v, (list, tuple)) else v) for k, v in params.items()}
    params.setdefault("Format", "JSON")
    rows, page, pages = [], 1, 1
    while page <= pages:
        data = _http.get_json(f"{BASE}/{path}", {**params, "limit": PAGE, "page": page}, source=SOURCE)
        if not isinstance(data, dict) or data.get("success") is False or "data" not in data:
            if isinstance(data, dict) and data.get("msg") == "No Data Found":
                break
            raise _http.SourceError(SOURCE, f"{path}: {data.get('message') or data.get('msg') or data}")
        meta = data.get("meta_data") or {}
        pages = meta.get("totalPages", 1)
        if page == 1 and max_pages is not None and pages > max_pages:
            raise _http.SourceError(
                SOURCE, f"{path} would need {pages} pages ({meta.get('totalRecords')} rows); "
                        f"add filters or pass max_pages=None")
        rows.extend(data["data"])
        page += 1
    df = pd.DataFrame(rows)
    df.attrs["source"] = SOURCE
    return df


def _monthly_date(df: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.to_datetime([month_start(y, m) for y, m in zip(df["year"], df["month"])])


# ---------------------------------------------------------------- prices

def cpi(base_year: str = "2012", series: str = "Current", year=None, month=None,
        state_code=ALL_INDIA, sector_code=COMBINED, group_code=None, subgroup_code=None) -> pd.DataFrame:
    """Consumer Price Index (all groups and sub-groups), monthly.

    Defaults to all-India, rural+urban combined. The headline is group == "General".
    ``inflation`` is MoSPI's published year-on-year % change.
    Base 2024 (launched 2026) appears here once MoSPI loads it into the API.
    """
    df = query("cpi/getCPIIndex", base_year=base_year, series=series, year=year, month_code=month,
               state_code=state_code, sector_code=sector_code, group_code=group_code,
               subgroup_code=subgroup_code, max_pages=None)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no CPI data for base_year={base_year}")
    df["date"] = _monthly_date(df)
    df["index"] = to_number(df["index"])
    df["inflation"] = to_number(df["inflation"])
    df = df.rename(columns={"baseyear": "base_year"})
    cols = ["date", "base_year", "state", "sector", "group", "subgroup", "index", "inflation", "status"]
    return df[cols].sort_values(["group", "subgroup", "date"], ignore_index=True)


WPI_HEADLINE = "Wholesale price index"


def wpi(year=None, month=None) -> pd.DataFrame:
    """Wholesale Price Index (base 2011-12), monthly, full commodity hierarchy (~870 rows a month).

    The API ignores the commodity-code filters in its docs (and its capitalised
    ``Year``/``Month_code``), so filter by ``year``/``month`` here and by the
    ``majorgroup``/``group``/``item`` columns afterwards. For the headline index use
    :func:`wpi_headline`, which is much faster.
    """
    df = query("wpi/getWpiRecords", year=year, month_code=month, max_pages=None)
    return _tidy_wpi(df)


def wpi_headline(start_year: int = 2012, end_year: int | None = None) -> pd.DataFrame:
    """The all-commodities WPI, one row per month (one small request per month, cached)."""
    end_year = end_year or pd.Timestamp.today().year
    rows = []
    for y in range(start_year, end_year + 1):
        for m in range(1, 13):
            if pd.Timestamp(y, m, 1) > pd.Timestamp.today():
                break
            data = _http.get_json(f"{BASE}/wpi/getWpiRecords",
                                  {"year": y, "month_code": m, "limit": 5, "Format": "JSON"}, source=SOURCE)
            head = [r for r in data.get("data") or [] if r["majorgroup"] == WPI_HEADLINE and r["group"] is None]
            if not head and data.get("data"):   # ordering changed: scan the whole month
                full = query("wpi/getWpiRecords", year=y, month_code=m, max_pages=None).to_dict("records")
                head = [r for r in full if r["majorgroup"] == WPI_HEADLINE and r["group"] is None]
            rows.extend(head[:1])
    if not rows:
        raise _http.SourceError(SOURCE, "no WPI data")
    return _tidy_wpi(pd.DataFrame(rows))


def _tidy_wpi(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = _monthly_date(df)
    df["index"] = to_number(df["index_value"])
    cols = ["date", "base_year", "majorgroup", "group", "subgroup", "sub_subgroup", "item", "index"]
    return df[cols].sort_values(["majorgroup", "date"], ignore_index=True)


# ---------------------------------------------------------------- activity

def iip(base_year: str = "2022-23", freq: str = "M", type: str = "General", year=None,
        category_code=None) -> pd.DataFrame:
    """Index of Industrial Production. ``type``: General, Sectoral, Use-based or All.

    ``freq="M"`` monthly (by calendar year) or ``"A"`` annual (by fiscal year).
    """
    if freq.upper().startswith("M"):
        df = query("iip/getIIPMonthly", base_year=base_year, type=type, year=year,
                   category_code=category_code, max_pages=None)
        if df.empty:
            raise _http.SourceError(SOURCE, f"no IIP data for base_year={base_year}")
        df["date"] = _monthly_date(df)
    else:
        df = query("iip/getIIPAnnual", base_year=base_year, type=type, financial_year=year,
                   category_code=category_code, max_pages=None)
        if df.empty:
            raise _http.SourceError(SOURCE, f"no IIP data for base_year={base_year}")
        df["period"] = df["year"]
        df["date"] = df["year"].map(fy_start)
    df["index"] = to_number(df["index"])
    df["growth_rate"] = to_number(df["growth_rate"])
    cols = ["date", "base_year", "type", "category", "sub_category", "index", "growth_rate"]
    return df[[c for c in cols + ["period"] if c in df.columns]].sort_values(["category", "date"], ignore_index=True)


def nas(indicator_code: int = 5, freq: str = "A", series: str = "Current", **filters) -> pd.DataFrame:
    """National Accounts Statistics. ``indicator_code`` from :data:`NAS_INDICATORS` (5 = GDP).

    Annual rows are Indian fiscal years (``period`` '2024-25', ``date`` 2024-04-01);
    quarterly rows are fiscal quarters (Q1 = Apr-Jun). ``revision`` tells you which
    estimate a figure is (advance, provisional, revised...). Values in Rs crore
    unless ``unit`` says otherwise; ``current_price`` is nominal, ``constant_price`` real.
    ``series="Back"`` gives the back-series (older years on the current base).
    """
    frequency = "Quarterly" if freq.upper().startswith("Q") else "Annually"
    df = query("nas/getNASData", series=series, frequency_code=frequency, indicator_code=indicator_code,
               max_pages=None, **filters)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no NAS data for indicator {indicator_code}")
    df["period"] = df["year"] if frequency == "Annually" else df["year"] + " " + df["quarter"].astype(str)
    df["date"] = (df["year"].map(fy_start) if frequency == "Annually"
                  else [fy_quarter_start(y, q) for y, q in zip(df["year"], df["quarter"])])
    for col in ("current_price", "constant_price"):
        if col in df:
            df[col] = to_number(df[col])
    lead = ["date", "period", "base_year", "indicator", "revision"]
    rest = [c for c in df.columns if c not in lead + ["year", "frequency", "series"]]
    return df[lead + rest].sort_values(["base_year", "date"], ignore_index=True)


def plfs(indicator_code: int = 3, freq: str = "A", state_code=PLFS_ALL_INDIA, gender_code=PLFS_PERSON,
         sector_code=PLFS_RURAL_URBAN, age_code=PLFS_AGE_15_PLUS, **filters) -> pd.DataFrame:
    """Periodic Labour Force Survey. ``indicator_code`` from :data:`PLFS_INDICATORS` (3 = unemployment).

    ``freq``: "A" annual, "Q" quarterly (urban), "M" monthly (from 2025). Defaults to all-India,
    all persons aged 15+, rural+urban.
    """
    fcode = {"A": 1, "Q": 2, "M": 3}[freq.upper()[0]]
    df = query("plfs/getData", indicator_code=indicator_code, frequency_code=fcode, state_code=state_code,
               gender_code=gender_code, sector_code=sector_code, age_code=age_code, max_pages=None, **filters)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no PLFS data for indicator {indicator_code}, freq {freq}")
    df["value"] = to_number(df["value"])
    if fcode == 3:
        df["date"] = _monthly_date(df)
    elif fcode == 2:
        df["date"] = pd.to_datetime(df["year"].astype(str).str[:4] + "-01-01")
    else:
        df["date"] = [fy_start(y) if "-" in str(y) else pd.Timestamp(int(y), 1, 1) for y in df["year"]]
    df["period"] = df["year"].astype(str) + (" " + df["quarter"].astype(str) if "quarter" in df and fcode == 2 else "")
    lead = ["date", "period", "indicator", "value", "unit"]
    rest = [c for c in df.columns if c not in lead + ["year", "frequency", "month", "quarter"]]
    return df[lead + rest].sort_values("date", ignore_index=True)


# ---------------------------------------------------------------- RBI tables

def rbi_indicators() -> pd.DataFrame:
    """The 39 RBI external-sector tables available (code, label)."""
    data = _http.get_json(f"{BASE}/rbi/getRbiIndicatorList", ttl=7 * _http.DAY, source=SOURCE)
    return pd.DataFrame(data["data"])[["indicator_code", "label"]].rename(columns={"indicator_code": "code"})


def rbi(code: int, **filters) -> pd.DataFrame:
    """One RBI table by code (see :func:`rbi_indicators`), e.g. 47 = monthly forex reserves,
    33 = monthly INR exchange rates, 4 = quarterly balance of payments (US$).

    Tables have different shapes, so columns vary; ``value`` is numeric and ``date``
    is added where the table has a year (and month/quarter).
    """
    df = query("rbi/getRbiRecords", sub_indicator_code=code, max_pages=None, **filters)
    if df.empty:
        raise _http.SourceError(SOURCE, f"no RBI data for code {code}")
    df["value"] = to_number(df["value"])
    if "year" in df:
        months = df["month"] if "month" in df else pd.Series([None] * len(df))
        df["date"] = [_rbi_date(str(y), m) for y, m in zip(df["year"], months)]
    return df


def _rbi_date(year: str, month) -> pd.Timestamp:
    """RBI tables mix calendar years ('2025') and fiscal years ('2024-25'), with or without months."""
    fiscal = "-" in year
    if month is None or pd.isna(month):
        return fy_start(year) if fiscal else pd.Timestamp(int(year), 1, 1)
    start = int(year[:4])
    if fiscal and month_start(start, month).month < 4:   # Jan-Mar fall in the second calendar year
        start += 1
    return month_start(start, month)
