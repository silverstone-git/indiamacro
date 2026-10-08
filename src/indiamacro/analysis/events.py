"""Dated events (shocks, policy moves) and a simple event-study engine.

The built-in list holds well-documented events only. Add your own (e.g. a strike on
a refinery last week) from the web UI or with :func:`add`; they are saved to
``~/.local/share/indiamacro/events.json`` and never overwrite the built-ins.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

USER_FILE = Path(os.environ.get("INDIAMACRO_EVENTS",
                                Path.home() / ".local" / "share" / "indiamacro" / "events.json"))

CATEGORIES = {
    "refinery_strike": "Strikes on refineries / energy infrastructure",
    "reserve_release": "Strategic petroleum reserve releases",
    "opec": "OPEC / OPEC+ decisions",
    "sanctions": "Sanctions, embargoes and price caps",
    "geopolitical": "Wars and geopolitical shocks",
    "demand": "Demand shocks",
    "india_policy": "Indian economic policy",
}

BUILTIN = [
    # refinery / infrastructure strikes
    ("2019-09-14", "Drone and missile attack on Saudi Aramco's Abqaiq and Khurais facilities", "refinery_strike", "Saudi Arabia"),
    ("2024-01-21", "Drone strike on Novatek's Ust-Luga fuel export terminal", "refinery_strike", "Russia"),
    ("2024-03-12", "Drone strike on Lukoil's NORSI refinery (Kstovo)", "refinery_strike", "Russia"),
    ("2024-03-13", "Drone strike on Rosneft's Ryazan refinery", "refinery_strike", "Russia"),
    ("2024-03-16", "Drone strikes on Rosneft refineries in Samara region (Syzran, Novokuibyshevsk)", "refinery_strike", "Russia"),
    # strategic reserves
    ("2021-09-24", "China holds its first public auction of crude from state reserves", "reserve_release", "China"),
    ("2021-11-23", "US-led coordinated SPR release (US, China, India, Japan, Korea, UK)", "reserve_release", "Global"),
    ("2022-03-01", "IEA members agree 60 mb emergency stock release", "reserve_release", "Global"),
    ("2022-03-31", "US announces 180 mb SPR release over six months", "reserve_release", "USA"),
    # OPEC
    ("2014-11-27", "OPEC declines to cut output; price war on shale begins", "opec", "OPEC"),
    ("2016-11-30", "OPEC agrees first production cut since 2008", "opec", "OPEC"),
    ("2020-03-06", "OPEC+ talks collapse; Saudi-Russia price war", "opec", "OPEC+"),
    ("2020-04-12", "OPEC+ agrees record 9.7 mb/d cut", "opec", "OPEC+"),
    ("2023-04-02", "Surprise voluntary OPEC+ cuts of ~1.16 mb/d", "opec", "OPEC+"),
    # sanctions
    ("2022-12-05", "EU embargo on Russian seaborne crude; G7 $60 price cap", "sanctions", "Russia"),
    ("2023-02-05", "EU embargo and price caps on Russian refined products", "sanctions", "Russia"),
    # geopolitics / demand
    ("2022-02-24", "Russia invades Ukraine", "geopolitical", "Russia/Ukraine"),
    ("2020-03-11", "WHO declares COVID-19 a pandemic", "demand", "Global"),
    ("2020-04-20", "WTI May futures settle below zero", "demand", "USA"),
    # India
    ("2016-08-05", "Flexible inflation targeting (4% +/-2%) notified", "india_policy", "India"),
    ("2016-11-08", "Demonetisation of Rs 500 and Rs 1000 notes", "india_policy", "India"),
    ("2019-09-20", "Corporate tax rate cut", "india_policy", "India"),
    ("2020-03-25", "National COVID-19 lockdown", "india_policy", "India"),
    ("2022-05-04", "RBI off-cycle repo rate hike", "india_policy", "India"),
]


def load() -> pd.DataFrame:
    """All events: built-ins plus your own, sorted by date."""
    rows = [{"id": f"b{i}", "date": d, "label": l, "category": c, "region": r, "builtin": True}
            for i, (d, l, c, r) in enumerate(BUILTIN)]
    rows += [{**e, "builtin": False} for e in _read_user()]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date", ignore_index=True)


def _read_user() -> list[dict]:
    try:
        return json.loads(USER_FILE.read_text())
    except (FileNotFoundError, ValueError):
        return []


def add(date, label: str, category: str, region: str = "") -> dict:
    if category not in CATEGORIES:
        raise ValueError(f"category must be one of {list(CATEGORIES)}")
    event = {"id": uuid.uuid4().hex[:8], "date": str(pd.Timestamp(date).date()), "label": label.strip(),
             "category": category, "region": region.strip()}
    events = _read_user() + [event]
    USER_FILE.parent.mkdir(parents=True, exist_ok=True)
    USER_FILE.write_text(json.dumps(events, indent=2))
    return event


def remove(event_id: str) -> bool:
    events = _read_user()
    kept = [e for e in events if e["id"] != event_id]
    USER_FILE.write_text(json.dumps(kept, indent=2))
    return len(kept) < len(events)


def select(category: str | None = None, dates: list | None = None) -> pd.DataFrame:
    """Events in a category (or all), optionally plus ad-hoc ``dates``."""
    df = load()
    if category and category != "all":
        df = df[df["category"] == category]
    if dates:
        extra = pd.DataFrame({"date": pd.to_datetime(dates), "label": [f"custom {d}" for d in dates],
                              "category": "custom", "region": "", "id": "", "builtin": False})
        df = pd.concat([df, extra], ignore_index=True)
    return df.sort_values("date", ignore_index=True)


# ---------------------------------------------------------------- event study

def event_study(series: pd.Series, events: pd.DataFrame, pre: int = 10, post: int = 20,
                estimation: tuple[int, int] = (-120, -21), log: bool = True) -> dict:
    """Constant-mean-model event study.

    Windows are in *observations* (trading days for daily data, months for monthly).
    ``log=True`` measures % changes (prices); ``log=False`` measures level changes
    (spreads, rates). The abnormal change is the change minus its average over the
    estimation window, cumulated from day -``pre`` and re-centred so day -1 = 0.

    Returns ``paths`` (relative day x event), ``mean``, ``ci`` (95% band across events)
    and ``table`` (cumulative abnormal change at selected horizons, per event and mean).
    """
    s = series.dropna().sort_index()
    ch = (np.log(s).diff() * 100) if log else s.diff()
    idx = s.index
    paths, labels = {}, {}
    for e in events.itertuples():
        pos = idx.searchsorted(pd.Timestamp(e.date))
        lo, hi = pos + estimation[0], pos + estimation[1]
        if lo < 1 or pos + post >= len(idx) or pos - pre < 1:
            continue
        mu = ch.iloc[lo:hi + 1].mean()
        window = ch.iloc[pos - pre: pos + post + 1] - mu
        cum = window.cumsum()
        cum = cum - cum.iloc[pre - 1]       # day -1 = 0
        key = f"{pd.Timestamp(e.date).date()} {e.label}"
        paths[key] = cum.to_numpy()
        labels[key] = idx[pos]
    rel = np.arange(-pre, post + 1)
    paths_df = pd.DataFrame(paths, index=rel)
    n = paths_df.shape[1]
    mean = paths_df.mean(axis=1)
    se = paths_df.std(axis=1, ddof=1) / np.sqrt(n) if n > 1 else pd.Series(np.nan, index=rel)
    horizons = [h for h in (0, 1, 5, 10, post) if h <= post]
    table = paths_df.loc[horizons].T
    table.columns = [f"t+{h}" for h in horizons]
    summary = pd.DataFrame({"mean": table.mean(), "t_stat": table.mean() / (table.std(ddof=1) / np.sqrt(n))
                            if n > 1 else np.nan, "share_positive": (table > 0).mean()})
    return {"paths": paths_df, "mean": mean, "ci": (mean - 1.96 * se, mean + 1.96 * se),
            "table": table, "summary": summary, "n": n, "unit": "%" if log else "level",
            "dates": labels}
