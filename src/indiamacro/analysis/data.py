"""Memoised data loaders shared by the stories (many pages reuse the same series)."""

from __future__ import annotations

import pandas as pd

from .. import india
from ..sources import energy, fred, imf, mospi
from .framework import memo


@memo()
def spot() -> pd.DataFrame:
    return energy.prices(start="2000-01-01")


@memo()
def cracks() -> pd.DataFrame:
    return energy.cracks(start="2000-01-01")


@memo()
def futures() -> pd.DataFrame:
    return energy.futures(start="2007-01-01")


@memo()
def dfl() -> pd.Series:
    return energy.dated_to_frontline(start="2007-01-01")


@memo(3600)
def pink() -> pd.DataFrame:
    return energy.pink_sheet()


@memo(3600)
def basket() -> pd.DataFrame:
    return energy.indian_basket()


@memo()
def usdinr_daily() -> pd.Series:
    return india.usdinr()


@memo()
def usdinr_monthly() -> pd.Series:
    return usdinr_daily().resample("MS").mean()


@memo()
def cpi_all() -> pd.DataFrame:
    return mospi.cpi()


def cpi_subgroup(name: str) -> pd.Series:
    df = cpi_all()
    return df[df["subgroup"] == name].set_index("date")["inflation"].sort_index()


@memo()
def repo_monthly() -> pd.Series:
    return india.repo_rate(freq="M")


@memo()
def wpi_infl() -> pd.Series:
    return india.wpi_inflation()


@memo()
def weo(code: str, countries: tuple) -> pd.DataFrame:
    return imf.weo(code, list(countries))


@memo(3600)
def us_cpi() -> pd.Series:
    return fred.series("CPIAUCSL")


@memo(3600)
def russia_daily() -> pd.DataFrame:
    return energy.russia_exports(start="2022-01-01")


@memo(3600)
def russia_destinations(commodity: str = "crude_oil") -> pd.DataFrame:
    return energy.russia_exports(by="destination", start="2022-01-01", commodity=commodity)


# ---------------------------------------------------------------- event-lab series catalogue

def _brent_wti() -> pd.Series:
    p = spot()
    return (p["brent"] - p["wti"]).dropna()


LAB_SERIES = {
    # key: (label, loader, log-changes?, unit)
    "brent": ("Brent spot (US$/bbl)", lambda: spot()["brent"], True, "%"),
    "wti": ("WTI spot (US$/bbl)", lambda: spot()["wti"], True, "%"),
    "diesel_nyh": ("Diesel, NY Harbor (US$/bbl)", lambda: spot()["diesel_nyh"], True, "%"),
    "gasoline_nyh": ("Gasoline, NY Harbor (US$/bbl)", lambda: spot()["gasoline_nyh"], True, "%"),
    "jet_gulf": ("Jet fuel, US Gulf (US$/bbl)", lambda: spot()["jet_gulf"], True, "%"),
    "diesel_crack": ("Diesel crack vs Brent (US$/bbl)", lambda: cracks()["diesel_crack"], False, "US$/bbl"),
    "gasoline_crack": ("Gasoline crack vs Brent (US$/bbl)", lambda: cracks()["gasoline_crack"], False, "US$/bbl"),
    "jet_crack": ("Jet crack vs Brent (US$/bbl)", lambda: cracks()["jet_crack"], False, "US$/bbl"),
    "dfl": ("Dated Brent minus front-month futures (US$/bbl)", dfl, False, "US$/bbl"),
    "brent_wti": ("Brent-WTI spread (US$/bbl)", _brent_wti, False, "US$/bbl"),
    "bz_front": ("Brent front-month futures (US$/bbl)", lambda: futures()["BZ"], True, "%"),
    "usdinr": ("Rupees per US dollar", usdinr_daily, True, "%"),
}
