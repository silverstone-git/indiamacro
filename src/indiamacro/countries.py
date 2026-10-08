"""Country codes and peer groups.

Sources disagree on codes (BIS wants ISO2 'IN', IMF/OECD/PWT/OWID want ISO3 'IND',
the World Bank takes either), so every function in the package accepts names,
ISO2 or ISO3 and converts with :func:`iso3` / :func:`iso2`.
"""

from __future__ import annotations

from . import _http

# (iso3, iso2, name) for the economies used most often; anything else is looked up
# from the World Bank country list (cached).
_BUILTIN = [
    ("IND", "IN", "India"), ("CHN", "CN", "China"), ("USA", "US", "United States"),
    ("JPN", "JP", "Japan"), ("DEU", "DE", "Germany"), ("GBR", "GB", "United Kingdom"),
    ("FRA", "FR", "France"), ("ITA", "IT", "Italy"), ("CAN", "CA", "Canada"),
    ("AUS", "AU", "Australia"), ("KOR", "KR", "Korea, Rep."), ("BRA", "BR", "Brazil"),
    ("RUS", "RU", "Russian Federation"), ("ZAF", "ZA", "South Africa"), ("MEX", "MX", "Mexico"),
    ("IDN", "ID", "Indonesia"), ("TUR", "TR", "Turkiye"), ("SAU", "SA", "Saudi Arabia"),
    ("ARG", "AR", "Argentina"), ("PAK", "PK", "Pakistan"), ("BGD", "BD", "Bangladesh"),
    ("LKA", "LK", "Sri Lanka"), ("NPL", "NP", "Nepal"), ("BTN", "BT", "Bhutan"),
    ("MDV", "MV", "Maldives"), ("AFG", "AF", "Afghanistan"), ("MYS", "MY", "Malaysia"),
    ("THA", "TH", "Thailand"), ("VNM", "VN", "Viet Nam"), ("PHL", "PH", "Philippines"),
    ("SGP", "SG", "Singapore"), ("MMR", "MM", "Myanmar"), ("KHM", "KH", "Cambodia"),
    ("LAO", "LA", "Lao PDR"), ("BRN", "BN", "Brunei Darussalam"), ("EGY", "EG", "Egypt"),
    ("ETH", "ET", "Ethiopia"), ("IRN", "IR", "Iran"), ("ARE", "AE", "United Arab Emirates"),
    ("NGA", "NG", "Nigeria"), ("CHE", "CH", "Switzerland"), ("ESP", "ES", "Spain"),
    ("NLD", "NL", "Netherlands"), ("HKG", "HK", "Hong Kong SAR, China"), ("TWN", "TW", "Taiwan"),
    ("ISR", "IL", "Israel"), ("POL", "PL", "Poland"), ("CHL", "CL", "Chile"),
    ("COL", "CO", "Colombia"), ("PER", "PE", "Peru"), ("NZL", "NZ", "New Zealand"),
]

ALIASES = {
    "bharat": "IND", "us": "USA", "usa": "USA", "america": "USA", "uk": "GBR",
    "britain": "GBR", "korea": "KOR", "south korea": "KOR", "russia": "RUS",
    "vietnam": "VNM", "turkey": "TUR", "uae": "ARE", "taiwan": "TWN", "iran": "IRN",
    "egypt": "EGY", "laos": "LAO", "hong kong": "HKG",
}

GROUPS = {
    "BRICS": ["IND", "BRA", "RUS", "CHN", "ZAF"],
    "BRICS+": ["IND", "BRA", "RUS", "CHN", "ZAF", "EGY", "ETH", "IRN", "ARE", "IDN"],
    "G7": ["USA", "JPN", "DEU", "GBR", "FRA", "ITA", "CAN"],
    "G20": ["IND", "ARG", "AUS", "BRA", "CAN", "CHN", "FRA", "DEU", "IDN", "ITA", "JPN",
            "KOR", "MEX", "RUS", "SAU", "ZAF", "TUR", "GBR", "USA"],
    "SOUTH_ASIA": ["IND", "PAK", "BGD", "LKA", "NPL", "BTN", "MDV", "AFG"],
    "ASEAN": ["IDN", "MYS", "PHL", "SGP", "THA", "VNM", "MMR", "KHM", "LAO", "BRN"],
    # Large emerging Asian economies India is usually benchmarked against.
    "EM_ASIA": ["IND", "CHN", "IDN", "MYS", "PHL", "THA", "VNM"],
    "QUAD": ["IND", "USA", "JPN", "AUS"],
}

_by_iso3 = {i3: (i3, i2, n) for i3, i2, n in _BUILTIN}
_by_iso2 = {i2: (i3, i2, n) for i3, i2, n in _BUILTIN}
_by_name = {n.lower(): (i3, i2, n) for i3, i2, n in _BUILTIN}
_wb_loaded = False


def _load_worldbank() -> None:
    global _wb_loaded
    if _wb_loaded:
        return
    data = _http.get_json("https://api.worldbank.org/v2/country", {"format": "json", "per_page": 400},
                          ttl=30 * _http.DAY, source="worldbank")
    for c in data[1]:
        if c["region"]["value"] == "Aggregates":
            continue
        row = (c["id"], c["iso2Code"], c["name"])
        _by_iso3.setdefault(row[0], row)
        _by_iso2.setdefault(row[1], row)
        _by_name.setdefault(row[2].lower(), row)
    _wb_loaded = True


def lookup(country: str) -> tuple[str, str, str]:
    """Name / ISO2 / ISO3 -> (iso3, iso2, name)."""
    key = str(country).strip()
    low = key.lower()
    if low in ALIASES:
        return _by_iso3[ALIASES[low]]
    for table, k in ((_by_iso3, key.upper()), (_by_iso2, key.upper()), (_by_name, low)):
        if k in table:
            return table[k]
    _load_worldbank()
    for table, k in ((_by_iso3, key.upper()), (_by_iso2, key.upper()), (_by_name, low)):
        if k in table:
            return table[k]
    raise KeyError(f"unknown country: {country!r}")


def iso3(country: str) -> str:
    return lookup(country)[0]


def iso2(country: str) -> str:
    return lookup(country)[1]


def name(country: str) -> str:
    return lookup(country)[2]


def expand(countries) -> list[str]:
    """Normalise a country argument to a list of ISO3 codes.

    Accepts a single country, a list, a group name from :data:`GROUPS`, or a mix
    (``["BRICS", "USA"]``). India is moved to the front when present.
    """
    if countries is None:
        return ["IND"]
    if isinstance(countries, str):
        countries = [countries]
    out: list[str] = []
    for c in countries:
        codes = GROUPS.get(str(c).upper().replace(" ", "_"))
        for code in codes or [iso3(c)]:
            if code not in out:
                out.append(code)
    if "IND" in out:
        out.remove("IND")
        out.insert(0, "IND")
    return out
