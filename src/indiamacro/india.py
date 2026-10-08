"""One-line access to India's headline macro series, each from its best free source.

Every function returns a date-indexed :class:`pandas.Series` whose ``attrs`` record
the source and units, so you can cite it. Use the modules in
:mod:`indiamacro.sources` when you need the full detail behind a series.
"""

from __future__ import annotations

import pandas as pd

from .sources import bis, fred, imf, mospi

_REVISION_ORDER = [
    "First Advance Estimates", "Second Advance Estimates", "Provisional Estimates",
    "First Revised Estimates", "Second Revised Estimates", "Third Revised Estimates", "Final Estimates",
]


def _series(values: pd.Series, name: str, source: str, unit: str, note: str = "") -> pd.Series:
    s = values.sort_index().rename(name)
    s.index.name = "date"
    s.attrs.update(source=source, unit=unit, note=note)
    return s


def _latest_revision(df: pd.DataFrame) -> pd.DataFrame:
    rank = df["revision"].map({r: i for i, r in enumerate(_REVISION_ORDER)}).fillna(-1)
    return df.assign(_rank=rank).sort_values(["date", "_rank"]).groupby("date").tail(1).drop(columns="_rank")


# ---------------------------------------------------------------- output

def gdp(real: bool = True, freq: str = "A", base_year: str = "2022-23") -> pd.Series:
    """GDP in Rs crore from MoSPI national accounts, latest available estimate per period.

    Annual dates are fiscal-year starts (2024-04-01 = FY 2024-25); quarterly dates are
    fiscal-quarter starts. ``base_year="2022-23"`` is the current official series;
    use ``"2011-12"`` for the longer pre-2026 series. Don't mix the two.
    """
    df = mospi.nas(5, freq=freq)
    df = df[df["base_year"] == base_year]
    if df.empty:
        raise ValueError(f"no GDP data for base year {base_year}")
    df = _latest_revision(df) if "revision" in df else df
    col = "constant_price" if real else "current_price"
    kind = "real" if real else "nominal"
    return _series(df.set_index("date")[col], f"gdp_{kind}", "MoSPI National Accounts",
                   f"Rs crore, {'constant ' + base_year if real else 'current'} prices",
                   f"base {base_year}; fiscal-year dates")


def gdp_growth(source: str = "imf", projections: bool = True) -> pd.Series:
    """Real GDP growth, % per year.

    ``source="imf"``: IMF WEO, from 1980, with projections ~5 years ahead unless
    ``projections=False`` (IMF reports India by fiscal year: 2024 = FY 2024-25).
    ``source="mospi"``: computed from official real GDP (current base year only).
    """
    if source == "imf":
        df = imf.weo("NGDP_RPCH", "IND")
        if not projections:
            df = df[~df["projection"].map(lambda v: v is True)]   # keeps rows where it's unknown (NA)
        return _series(df.set_index("date")["value"], "gdp_growth", "IMF World Economic Outlook", "% y/y",
                       "fiscal-year basis" + ("; includes IMF projections" if projections else ""))
    g = gdp(real=True).pct_change(fill_method=None) * 100
    return _series(g.dropna(), "gdp_growth", "MoSPI National Accounts", "% y/y", "fiscal years")


def iip_growth(base_year: str = "2022-23") -> pd.Series:
    """Index of Industrial Production, general index, % y/y, monthly."""
    df = mospi.iip(base_year=base_year, type="General")
    return _series(df.set_index("date")["growth_rate"], "iip_growth", "MoSPI IIP", "% y/y", f"base {base_year}")


# ---------------------------------------------------------------- prices

def cpi_inflation(base_year: str = "2012") -> pd.Series:
    """Headline CPI inflation (all-India, rural+urban, general index), % y/y, monthly."""
    df = mospi.cpi(base_year=base_year, group_code=None)
    df = df[df["group"] == "General"]
    return _series(df.set_index("date")["inflation"], "cpi_inflation", "MoSPI CPI", "% y/y",
                   f"base {base_year}=100")


def cpi_food_inflation(base_year: str = "2012") -> pd.Series:
    """Consumer Food Price Index inflation, % y/y, monthly."""
    df = mospi.cpi(base_year=base_year)
    df = df[df["subgroup"] == "Consumer Food Price-Overall"]
    return _series(df.set_index("date")["inflation"], "cpi_food_inflation", "MoSPI CPI", "% y/y",
                   f"base {base_year}=100")


def wpi_inflation() -> pd.Series:
    """Headline WPI inflation (all commodities), % y/y, monthly."""
    idx = mospi.wpi_headline().set_index("date")["index"].sort_index()
    return _series((idx.pct_change(12, fill_method=None) * 100).dropna(), "wpi_inflation",
                   "MoSPI/Office of Economic Adviser WPI", "% y/y", "base 2011-12")


# ---------------------------------------------------------------- labour

def unemployment(freq: str = "M") -> pd.Series:
    """Unemployment rate (%, persons 15+, rural+urban, current weekly status) from PLFS.

    Monthly data starts in 2025; use ``freq="A"`` for the annual series from 2017-18.
    """
    df = mospi.plfs(3, freq=freq)
    if "weekly_status" in df:
        cws = df[df["weekly_status"].astype(str).str.upper() == "CWS"]
        df = cws if not cws.empty else df
    df = df.drop_duplicates("date", keep="last")
    return _series(df.set_index("date")["value"], "unemployment", "MoSPI PLFS", "%")


# ---------------------------------------------------------------- money and external

def repo_rate(freq: str = "D") -> pd.Series:
    """RBI policy repo rate, % (via BIS central-bank policy rates)."""
    df = bis.policy_rate("IND", freq=freq)
    return _series(df.set_index("date")["value"], "repo_rate", "BIS (Reserve Bank of India)", "%")


def usdinr(start=None) -> pd.Series:
    """Rupees per US dollar, daily noon buying rate (Federal Reserve H.10, via FRED)."""
    s = fred.series("DEXINUS", start=start).dropna()
    return _series(s, "usdinr", "FRED DEXINUS", "INR per USD")


def reer() -> pd.Series:
    """Real effective exchange rate, broad basket, 2020=100 (BIS). Up = rupee appreciation."""
    df = bis.reer("IND")
    return _series(df.set_index("date")["value"], "reer", "BIS", "index, 2020=100")


def forex_reserves() -> pd.Series:
    """Total foreign exchange reserves, US$ million, monthly (RBI via MoSPI)."""
    df = mospi.rbi(47)
    typ = df["foreign_exchange_reserve_type"].astype(str).str.lower()
    cur = df["foreign_exchange_reserve_currency"].astype(str)
    df = df[typ.str.contains("total") & cur.str.contains("US", case=False)]
    df = df.dropna(subset=["value"]).drop_duplicates("date", keep="last")
    return _series(df.set_index("date")["value"], "forex_reserves", "RBI (via MoSPI eSankhyiki)", "US$ million")


# ---------------------------------------------------------------- summary

def snapshot() -> pd.DataFrame:
    """Latest reading of every headline series, with its date and source."""
    funcs = [gdp_growth, cpi_inflation, wpi_inflation, iip_growth, unemployment, repo_rate,
             usdinr, reer, forex_reserves]
    rows = []
    for f in funcs:
        try:
            s = (gdp_growth(projections=False) if f is gdp_growth else f()).dropna()
            rows.append({"series": s.name, "date": s.index[-1].date(), "value": round(float(s.iloc[-1]), 2),
                         "unit": s.attrs.get("unit"), "source": s.attrs.get("source")})
        except Exception as e:  # one broken source shouldn't hide the rest
            rows.append({"series": f.__name__, "error": str(e)[:120]})
    return pd.DataFrame(rows)
