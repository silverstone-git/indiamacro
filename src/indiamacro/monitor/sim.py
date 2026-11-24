"""Simulated stand-ins for every live feed, used when a source is unreachable or when
``INDIAMACRO_DEMO=1``. Everything here is fake and is labelled ``status: "sim"`` all the
way to the screen, so nobody can mistake it for data. Values are plausible in scale only.
"""

from __future__ import annotations

import math
import random
import time
import zlib

import numpy as np
import pandas as pd


def _rng(*key) -> random.Random:
    return random.Random(zlib.crc32("|".join(map(str, key)).encode()))


def quote(symbol: str, base: float, vol: float = 0.01, points: int = 78) -> dict:
    """A random walk that advances once a minute, so the screen ticks."""
    minute = int(time.time() // 60)
    r = _rng(symbol, minute // points)
    path = [base]
    for _ in range(points + minute % points):
        path.append(path[-1] * (1 + r.gauss(0, vol / math.sqrt(points))))
    spark = path[-points:]
    prev = path[0]
    return {"last": spark[-1], "prev_close": prev, "spark": spark}


def series(name: str, freq: str = "MS", periods: int = 180, level: float = 100.0, vol: float = 0.02,
           mean_revert: float | None = None) -> pd.Series:
    """A reproducible fake history (random walk, or AR(1) around ``mean_revert``)."""
    r = np.random.default_rng(zlib.crc32(name.encode()))
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=periods, freq=freq)
    x = np.empty(periods)
    x[0] = level
    for i in range(1, periods):
        if mean_revert is None:
            x[i] = x[i - 1] * (1 + r.normal(0, vol))
        else:
            x[i] = mean_revert + 0.9 * (x[i - 1] - mean_revert) + r.normal(0, vol * max(abs(mean_revert), 1))
    s = pd.Series(x, index=idx, name=name)
    s.attrs.update(source="SIMULATED (not real data)", unit="", sim=True)
    return s


def quakes(n: int = 60) -> list[dict]:
    r = _rng("quakes", int(time.time() // 3600))
    belts = [(36, 70), (28, 85), (-6, 105), (35, 140), (13, 122), (-20, -70), (38, -120), (40, 25), (-40, 175)]
    now = time.time() * 1000
    out = []
    for i in range(n):
        lat0, lon0 = r.choice(belts)
        out.append({"id": f"sim{i}", "lat": lat0 + r.gauss(0, 4), "lon": lon0 + r.gauss(0, 6),
                    "mag": round(4.5 + r.expovariate(2.2), 1), "depth": round(r.uniform(5, 300)),
                    "place": "simulated event", "time": now - r.uniform(0, 7 * 86400e3), "url": None})
    return out


def natural_events() -> list[dict]:
    r = _rng("eonet", int(time.time() // 3600))
    cats = ["Wildfires", "Severe Storms", "Volcanoes", "Sea and Lake Ice", "Floods"]
    return [{"id": f"sim{i}", "title": f"Simulated {c.lower()} event", "category": c,
             "lat": r.uniform(-40, 60), "lon": r.uniform(-170, 170),
             "date": pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%MZ"), "link": None}
            for i, c in enumerate(r.choice(cats) for _ in range(25))]


def aircraft(bbox: tuple[float, float, float, float], n: int = 250) -> list[dict]:
    lamin, lomin, lamax, lomax = bbox
    t = time.time()
    r = _rng("ac", bbox)
    out = []
    for i in range(n):
        lat, lon, trk, v = r.uniform(lamin, lamax), r.uniform(lomin, lomax), r.uniform(0, 360), r.uniform(180, 260)
        d = v * (t % 3600) / 111_000      # move along track so the map animates
        out.append({"icao24": f"sim{i:03d}", "callsign": f"SIM{i:03d}", "country": "Simulated",
                    "lat": lamin + (lat - lamin + d * math.cos(math.radians(trk))) % (lamax - lamin),
                    "lon": lomin + (lon - lomin + d * math.sin(math.radians(trk))) % (lomax - lomin),
                    "alt": r.uniform(3000, 12000), "vel": v, "track": trk, "ground": False})
    return out


def weather(cities: list[tuple[str, float, float]]) -> list[dict]:
    r = _rng("wx", int(time.time() // 900))
    return [{"city": c, "lat": la, "lon": lo, "temp": round(30 - abs(la) * 0.5 + r.gauss(0, 3), 1),
             "humidity": r.randint(20, 95), "wind": round(r.uniform(2, 30), 1), "precip": 0.0,
             "code": 0, "pm25": round(r.uniform(5, 250 if 15 < la < 32 and 70 < lo < 90 else 60)),
             "aqi": None} for c, la, lo in cities]


def chokepoints(names: list[str]) -> list[dict]:
    r = _rng("choke", pd.Timestamp.today().date())
    out = []
    for n in names:
        base = r.uniform(10, 120)
        out.append({"name": n, "last7": round(base * r.uniform(.6, 1.2), 1), "avg365": round(base, 1),
                    "tanker7": round(base * .3, 1), "date": str(pd.Timestamp.today().date())})
    return out
