"""indiamacro - India-first access to free macroeconomic data.

    import indiamacro as im

    im.india.cpi_inflation()                     # official MoSPI series
    im.india.snapshot()                          # latest headline numbers
    im.compare("gdp_growth", "BRICS")            # India vs peers (IMF WEO)
    im.mospi.nas(9)                              # any MoSPI table (here: GFCF)
    im.worldbank.get("SI.POV.GINI", "SOUTH_ASIA")

Sources: MoSPI (incl. RBI tables), Union Budget, FRED, World Bank, IMF, OECD,
BIS, Penn World Table, Our World in Data.
"""

from . import countries, india, utils
from ._http import SourceError, clear_cache, settings
from .compare import INDICATORS, compare
from .sources import bis, budget, fred, imf, mospi, oecd, owid, pwt, worldbank
from .utils import wide, yoy

__version__ = "0.1.0"

__all__ = [
    "india", "compare", "INDICATORS", "countries", "utils", "wide", "yoy",
    "mospi", "budget", "fred", "worldbank", "imf", "oecd", "bis", "pwt", "owid",
    "SourceError", "settings", "clear_cache",
]
