"""Cross-country comparisons with India as the reference column."""

from __future__ import annotations

import pandas as pd

from . import countries as _countries
from .sources import imf, worldbank
from .utils import wide

# Friendly names -> source codes. IMF WEO includes projections; World Bank has more breadth.
INDICATORS = {
    "gdp_growth":         {"imf": "NGDP_RPCH",   "worldbank": "NY.GDP.MKTP.KD.ZG"},
    "inflation":          {"imf": "PCPIPCH",     "worldbank": "FP.CPI.TOTL.ZG"},
    "gdp_usd":            {"imf": "NGDPD",       "worldbank": "NY.GDP.MKTP.CD"},
    "gdp_per_capita_ppp": {"imf": "PPPPC",       "worldbank": "NY.GDP.PCAP.PP.KD"},
    "share_world_gdp_ppp": {"imf": "PPPSH"},
    "unemployment":       {"imf": "LUR",         "worldbank": "SL.UEM.TOTL.ZS"},
    "govt_debt":          {"imf": "GGXWDG_NGDP", "worldbank": "GC.DOD.TOTL.GD.ZS"},
    "fiscal_balance":     {"imf": "GGXCNL_NGDP"},
    "current_account":    {"imf": "BCA_NGDPD",   "worldbank": "BN.CAB.XOKA.GD.ZS"},
    "exports_gdp":        {"worldbank": "NE.EXP.GNFS.ZS"},
    "investment_gdp":     {"worldbank": "NE.GDI.TOTL.ZS"},
    "savings_gdp":        {"worldbank": "NY.GNS.ICTR.ZS"},
    "fdi_gdp":            {"worldbank": "BX.KLT.DINV.WD.GD.ZS"},
    "manufacturing_gdp":  {"worldbank": "NV.IND.MANF.ZS"},
    "female_lfpr":        {"worldbank": "SL.TLF.CACT.FE.ZS"},
    "population":         {"worldbank": "SP.POP.TOTL"},
}


def compare(indicator: str, countries="BRICS", source: str | None = None,
            start: int | None = None, end: int | None = None) -> pd.DataFrame:
    """Date x country table for one indicator, India first.

    ``indicator`` is a key of :data:`INDICATORS` or a raw IMF/World Bank code.
    ``countries`` accepts groups ("BRICS", "G20", "SOUTH_ASIA", "ASEAN", "EM_ASIA",
    "QUAD", "G7"), lists, names or codes. ``source`` defaults to IMF when it has the
    indicator (it adds projections), else the World Bank.
    """
    codes = _countries.expand(countries)
    mapping = INDICATORS.get(indicator)
    if mapping is None:
        source = source or ("worldbank" if "." in indicator else "imf")
        code = indicator
    else:
        source = source or ("imf" if "imf" in mapping else "worldbank")
        if source not in mapping:
            raise ValueError(f"{indicator!r} is not available from {source}; try {list(mapping)}")
        code = mapping[source]
    fetch = imf.weo if source == "imf" else worldbank.get
    df = fetch(code, codes, start=start, end=end)
    table = wide(df).reindex(columns=[c for c in codes if c in set(df["country"])])
    table.attrs.update(source=source, code=code)
    return table
