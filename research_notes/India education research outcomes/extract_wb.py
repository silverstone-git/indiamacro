"""Live World Bank WDI extract for the education / R&D research-outcome report.

Run from the repo root with the cache disabled so every call hits the live API:

    INDIAMACRO_NO_CACHE=1 uv run python \
        "research_notes/India education research outcomes/extract_wb.py"

Writes wb_extract.csv (latest non-null observation per indicator/country) and
wb_diagnostics.json (exact calls, row counts, errors, search results) next to this file.
No package source, tests or docs are modified.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

import indiamacro as im
from indiamacro import _http
from indiamacro.sources import worldbank

HERE = Path(__file__).resolve().parent
ACCESS_DATE = "2026-11-20"
COUNTRIES = ["IND", "CHN", "KOR", "USA", "DEU", "BRA"]
INDICATORS = [
    "GB.XPD.RSDV.GD.ZS",
    "SP.POP.SCIE.RD.P6",
    "SP.POP.TECH.RD.P6",
    "IP.PAT.RESD",
    "IP.PAT.NRES",
    "IP.JRN.ARTC.SC",
    "SE.XPD.TOTL.GD.ZS",
    "HD.HCI.LAYS",
    "HD.HCI.HLO",
    "SE.LPV.PRIM",
]
SEARCH_TERMS = [
    "research and development",
    "researchers in r&d",
    "patent applications",
    "scientific and technical journal",
    "government expenditure on education",
    "learning-adjusted",
    "learning poverty",
    "harmonized learning outcomes",
]

diagnostics: dict = {
    "access_date": ACCESS_DATE,
    "cache_enabled": _http.settings.cache,
    "countries": COUNTRIES,
    "indicators": INDICATORS,
    "calls": {},
    "search": {},
    "errors": [],
}
latest_rows: list[dict] = []
full_frames: list[pd.DataFrame] = []

for ind in INDICATORS:
    call = f"worldbank.get({ind!r}, {COUNTRIES!r})"
    t0 = time.monotonic()
    try:
        df = worldbank.get(ind, COUNTRIES)
        elapsed = round(time.monotonic() - t0, 2)
        nonnull = df.dropna(subset=["value"])
        per_country = {}
        for c in COUNTRIES:
            sub = nonnull[nonnull["country"] == c].sort_values("date")
            if sub.empty:
                per_country[c] = {"n_nonnull": 0, "latest_date": None, "latest_value": None,
                                  "first_date": None, "first_value": None}
                continue
            last = sub.iloc[-1]
            first = sub.iloc[0]
            per_country[c] = {
                "n_nonnull": int(len(sub)),
                "latest_date": str(last["date"].date()),
                "latest_value": float(last["value"]),
                "first_date": str(first["date"].date()),
                "first_value": float(first["value"]),
            }
            latest_rows.append({
                "indicator": ind,
                "country": c,
                "date": str(last["date"].date()),
                "value": float(last["value"]),
            })
        diagnostics["calls"][ind] = {
            "call": call,
            "ok": True,
            "seconds": elapsed,
            "rows_total": int(len(df)),
            "countries_returned": sorted(set(df["country"])),
            "series_name": str(df["series_name"].iloc[0]) if len(df) else None,
            "per_country": per_country,
        }
        full_frames.append(df.assign(indicator=ind)[
            ["indicator", "country", "date", "value", "series_name", "country_name"]
        ])
        print(f"OK   {ind:20s} rows={len(df):5d} nonnull={len(nonnull):5d} "
              f"name={diagnostics['calls'][ind]['series_name']!r} ({elapsed}s)")
    except Exception as e:
        elapsed = round(time.monotonic() - t0, 2)
        msg = f"{type(e).__name__}: {e}"
        diagnostics["calls"][ind] = {"call": call, "ok": False, "seconds": elapsed, "error": msg}
        diagnostics["errors"].append({"indicator": ind, "error": msg})
        print(f"FAIL {ind:20s} {msg} ({elapsed}s)")

for term in SEARCH_TERMS:
    t0 = time.monotonic()
    try:
        res = worldbank.search(term)
        diagnostics["search"][term] = {
            "ok": True,
            "seconds": round(time.monotonic() - t0, 2),
            "n_matches": int(len(res)),
            "matches": res.to_dict("records"),
        }
        print(f"SEARCH {term!r}: {len(res)} matches "
              f"({diagnostics['search'][term]['seconds']}s)")
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        diagnostics["search"][term] = {"ok": False, "error": msg}
        diagnostics["errors"].append({"search": term, "error": msg})
        print(f"SEARCH {term!r}: FAILED {msg}")

# Extra check: is the named helper exported on the package/module, and is energy exported?
diagnostics["api_checks"] = {
    "worldbank_get": callable(getattr(worldbank, "get", None)),
    "worldbank_search": callable(getattr(worldbank, "search", None)),
    "im_worldbank": hasattr(im, "worldbank"),
    "im_energy": hasattr(im, "energy"),
    "im_compare": callable(getattr(im, "compare", None)),
    "package_version": im.__version__,
    "compare_indicators": list(im.INDICATORS),
    "wb_indicator_dict_codes": list(worldbank.INDICATORS),
}

out = pd.DataFrame(latest_rows, columns=["indicator", "country", "date", "value"])
out.to_csv(HERE / "wb_extract.csv", index=False, float_format="%.10g")
(HERE / "wb_diagnostics.json").write_text(json.dumps(diagnostics, indent=2, ensure_ascii=False))
print(f"\nWrote {HERE / 'wb_extract.csv'} ({len(out)} rows) and wb_diagnostics.json")
