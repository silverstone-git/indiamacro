"""Supplementary live probe: corrected code for the plan's invalid HD.HCI.HLO.

The World Bank indicator catalogue (queried 2026-11-20) lists no HD.HCI.HLO, but does
list HD.HCI.HLOS = "Harmonized Test Scores" (source 63, Human Capital Index). This
script pulls that indicator with the same six countries and writes a tidy CSV.

    INDIAMACRO_NO_CACHE=1 uv run python \
        "research_notes/India education research outcomes/extract_wb_hlos.py"
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from indiamacro.sources import worldbank

HERE = Path(__file__).resolve().parent
COUNTRIES = ["IND", "CHN", "KOR", "USA", "DEU", "BRA"]
CODE = "HD.HCI.HLOS"

df = worldbank.get(CODE, COUNTRIES)
print(f"call: worldbank.get({CODE!r}, {COUNTRIES!r})")
print(f"rows={len(df)} name={df['series_name'].iloc[0]!r}")
nonnull = df.dropna(subset=["value"])
rows = []
for c in COUNTRIES:
    sub = nonnull[nonnull["country"] == c].sort_values("date")
    if sub.empty:
        print(f"  {c}: NO NON-NULL VALUES")
        continue
    last = sub.iloc[-1]
    print(f"  {c}: n={len(sub)} first={sub.iloc[0]['date'].date()} "
          f"latest={last['date'].date()} value={last['value']:.6f}")
    rows.append({"indicator": CODE, "country": c,
                 "date": str(last["date"].date()), "value": float(last["value"])})
out = pd.DataFrame(rows, columns=["indicator", "country", "date", "value"])
out.to_csv(HERE / "wb_hlos_supplement.csv", index=False, float_format="%.10g")
print(f"Wrote {HERE / 'wb_hlos_supplement.csv'}")
