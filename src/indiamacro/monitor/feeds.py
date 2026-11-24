"""Live feeds for the terminal. Every function returns an *envelope*::

    {"feed": "quakes", "status": "live" | "sim", "source": "...", "asof": "...Z",
     "note": "...", "data": [...]}

``status`` is ``"sim"`` when the real source failed (the error is in ``note``) or when
``INDIAMACRO_DEMO=1``; the screen shows a SIM badge on those panels. All sources are free
and need no key (as of Nov 2026):

  quotes      Yahoo Finance via yfinance, 5-minute bars, delayed 0-20 min depending on exchange
  quakes      USGS earthquake feed, M4.5+ past 7 days (GeoJSON, updated every minute)
  events      NASA EONET v3 open natural events (wildfires, storms, volcanoes, ice, floods)
  aircraft    OpenSky Network state vectors (anonymous: ~10 s resolution, daily credit limit)
  weather     Open-Meteo forecast API (current conditions) + Open-Meteo air quality (CAMS)
  satellites  CelesTrak GP element sets (TLE). CelesTrak asks clients not to re-download a
              group more often than every 2 hours, hence the 2-6 h cache.
  chokepoints IMF PortWatch daily AIS transit counts (lags ~1 week)
  econ map    IMF World Economic Outlook via DataMapper (annual, includes projections)
"""

from __future__ import annotations

import math
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pandas as pd

from .. import _http
from . import env, sim

_mem: dict = {}
_mem_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _envelope(feed: str, source: str, ttl: float, live, fallback, note: str = "", key=()) -> dict:
    """Run ``live()`` (memoised for ``ttl`` seconds); on failure or in demo mode use ``fallback()``."""
    k = (feed, key)
    with _mem_lock:
        hit = _mem.get(k)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    status, err = "live", ""
    if env.demo():
        data, status, err = fallback(), "sim", "demo mode (INDIAMACRO_DEMO=1)"
    else:
        try:
            data = live()
        except Exception as e:  # any source failure -> labelled simulation, never a blank panel
            traceback.print_exc()
            data, status, err = fallback(), "sim", f"{type(e).__name__}: {str(e)[:160]}"
    out = {"feed": feed, "status": status, "source": source if status == "live" else "SIMULATED (source unavailable)",
           "asof": _now(), "note": err or note, "data": data}
    stamp = time.time() if status == "live" else time.time() - ttl + min(ttl, 60)   # retry failures sooner
    with _mem_lock:
        _mem[k] = (stamp, out)
    return out


def clear() -> None:
    with _mem_lock:
        _mem.clear()


# ---------------------------------------------------------------- markets

WATCHLIST = [
    # (yahoo ticker, short label, group, simulated base level)
    ("^NSEI", "NIFTY 50", "India", 25800), ("^BSESN", "SENSEX", "India", 84500),
    ("^NSEBANK", "BANK NIFTY", "India", 57500), ("^INDIAVIX", "INDIA VIX", "India", 12.5),
    ("INR=X", "USD/INR", "FX", 88.6), ("DX-Y.NYB", "DXY", "FX", 99.5), ("CNY=X", "USD/CNY", "FX", 7.1),
    ("BZ=F", "BRENT", "Cmdty", 88), ("CL=F", "WTI", "Cmdty", 84), ("NG=F", "NAT GAS", "Cmdty", 3.4),
    ("GC=F", "GOLD", "Cmdty", 3550), ("SI=F", "SILVER", "Cmdty", 41), ("HG=F", "COPPER", "Cmdty", 4.9),
    ("^TNX", "UST 10Y", "Rates", 4.2), ("^GSPC", "S&P 500", "World", 6700), ("^IXIC", "NASDAQ", "World", 22800),
    ("^N225", "NIKKEI", "World", 48000), ("^HSI", "HANG SENG", "World", 25500), ("^STOXX50E", "STOXX 50", "World", 5600),
    ("BTC-USD", "BITCOIN", "Crypto", 95000),
]


def _quotes_live() -> list[dict]:
    import logging

    import yfinance as yf

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
    tickers = [t for t, *_ in WATCHLIST]
    raw = yf.download(tickers, period="5d", interval="5m", progress=False, auto_adjust=False, threads=True)
    if raw is None or raw.empty:
        raise _http.SourceError("yahoo", "empty intraday download")
    close = raw["Close"]
    out = []
    for t, label, group, _ in WATCHLIST:
        s = close[t].dropna() if t in close else pd.Series(dtype=float)
        if s.empty:
            out.append({"symbol": t, "label": label, "group": group, "last": None})
            continue
        day = s.index[-1].date()
        today, before = s[s.index.date == day], s[s.index.date < day]
        prev = float(before.iloc[-1]) if len(before) else float(today.iloc[0])
        out.append({"symbol": t, "label": label, "group": group, "last": float(s.iloc[-1]), "prev_close": prev,
                    "chg_pct": (float(s.iloc[-1]) / prev - 1) * 100 if prev else None,
                    "time": s.index[-1].strftime("%Y-%m-%dT%H:%MZ") if s.index.tz is None
                    else s.index[-1].tz_convert("UTC").strftime("%Y-%m-%dT%H:%MZ"),
                    "spark": [round(float(v), 4) for v in today.tolist()[-120:]]})
    if all(q["last"] is None for q in out):
        raise _http.SourceError("yahoo", "no quotes")
    return out


def _quotes_sim() -> list[dict]:
    out = []
    for t, label, group, base in WATCHLIST:
        q = sim.quote(t, base, vol=0.02 if group in ("Crypto", "Cmdty") else 0.008)
        out.append({"symbol": t, "label": label, "group": group, "last": q["last"], "prev_close": q["prev_close"],
                    "chg_pct": (q["last"] / q["prev_close"] - 1) * 100, "time": _now(), "spark": q["spark"]})
    return out


def quotes() -> dict:
    return _envelope("quotes", "Yahoo Finance (delayed; exchange data, 5-min bars)", 60, _quotes_live, _quotes_sim)


# ---------------------------------------------------------------- earth: quakes, natural events

USGS = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
EONET = "https://eonet.gsfc.nasa.gov/api/v3/events"


def _quakes_live() -> list[dict]:
    js = _http.get_json(USGS, ttl=120, source="usgs")
    out = []
    for f in js["features"]:
        p, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"][:3]
        out.append({"id": f["id"], "lat": lat, "lon": lon, "depth": depth, "mag": p.get("mag"),
                    "place": p.get("place"), "time": p.get("time"), "url": p.get("url"),
                    "tsunami": p.get("tsunami"), "alert": p.get("alert")})
    return sorted(out, key=lambda q: -(q["time"] or 0))


def quakes() -> dict:
    return _envelope("quakes", "USGS Earthquake Hazards Program, M4.5+ past 7 days", 120, _quakes_live, sim.quakes)


def _centroid(geom: dict) -> tuple[float, float] | None:
    c = geom.get("coordinates")
    if geom.get("type") == "Point":
        return c[1], c[0]
    if geom.get("type") == "Polygon" and c:
        ring = c[0]
        return sum(p[1] for p in ring) / len(ring), sum(p[0] for p in ring) / len(ring)
    return None


def _events_live() -> list[dict]:
    js = _http.get_json(EONET, {"status": "open", "days": 30, "limit": 400}, ttl=900, source="eonet")
    out = []
    for e in js.get("events", []):
        if not e.get("geometry"):
            continue
        g = e["geometry"][-1]                # latest position (storms move)
        ll = _centroid(g)
        if not ll:
            continue
        out.append({"id": e["id"], "title": e["title"], "category": e["categories"][0]["title"],
                    "lat": ll[0], "lon": ll[1], "date": g.get("date"),
                    "link": (e.get("sources") or [{}])[0].get("url") or e.get("link"),
                    "track": [_centroid(x) for x in e["geometry"][-40:]] if len(e["geometry"]) > 1 else None})
    return out


def natural_events() -> dict:
    return _envelope("events", "NASA EONET v3 (open events, past 30 days)", 900, _events_live, sim.natural_events)


# ---------------------------------------------------------------- traffic: aircraft, chokepoints

OPENSKY = "https://opensky-network.org/api/states/all"
INDIA_BBOX = (5.0, 66.0, 37.5, 98.0)   # lamin, lomin, lamax, lomax


def aircraft(bbox: tuple[float, float, float, float] = INDIA_BBOX) -> dict:
    # snap outward to a 5-degree grid so nearby views share one cached request (OpenSky's anonymous quota is small)
    lamin, lomin, lamax, lomax = (float(x) for x in bbox)
    snap = lambda v, up: (math.ceil if up else math.floor)(v / 5) * 5   # noqa: E731
    bbox = (max(-90, snap(lamin, False)), max(-180, snap(lomin, False)), min(90, snap(lamax, True)), min(180, snap(lomax, True)))
    lamin, lomin, lamax, lomax = bbox
    if (lamax - lamin) * (lomax - lomin) > 2500:          # keep anonymous credit use low
        clat, clon = (lamin + lamax) / 2, (lomin + lomax) / 2
        bbox = (clat - 20, clon - 30, clat + 20, clon + 30)
        lamin, lomin, lamax, lomax = bbox

    def live():
        js = _http.get_json(OPENSKY, {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
                            ttl=20, source="opensky")
        out = []
        for s in (js.get("states") or [])[:3000]:
            if s[5] is None or s[6] is None:
                continue
            out.append({"icao24": s[0], "callsign": (s[1] or "").strip(), "country": s[2], "lon": s[5], "lat": s[6],
                        "alt": s[13] if s[13] is not None else s[7], "ground": s[8], "vel": s[9], "track": s[10]})
        return out

    return _envelope("aircraft", "OpenSky Network (ADS-B, anonymous access)", 20, live,
                     lambda: sim.aircraft(bbox), note=f"bbox {bbox}", key=bbox)


CHOKEPOINT_COORDS = {
    "Strait of Hormuz": (26.57, 56.25), "Bab el-Mandeb Strait": (12.58, 43.33), "Suez Canal": (30.6, 32.33),
    "Cape of Good Hope": (-34.36, 18.47), "Malacca Strait": (2.5, 101.3), "Bosporus Strait": (41.12, 29.07),
    "Panama Canal": (9.08, -79.68), "Gibraltar Strait": (35.96, -5.5), "Dover Strait": (51.0, 1.45),
    "Taiwan Strait": (24.4, 119.6), "Lombok Strait": (-8.77, 115.73), "Sunda Strait": (-5.92, 105.88),
}


def _choke_live() -> list[dict]:
    from ..sources import energy

    df = energy.chokepoints(start=(pd.Timestamp.today() - pd.Timedelta(days=400)).date())
    out = []
    for name, g in df.groupby("chokepoint"):
        g = g.set_index("date").sort_index()
        last = g.index.max()
        w = g.loc[last - pd.Timedelta(days=6):]
        y = g.loc[last - pd.Timedelta(days=365):]
        lat, lon = CHOKEPOINT_COORDS.get(name, (None, None))
        out.append({"name": name, "lat": lat, "lon": lon, "date": str(last.date()),
                    "last7": round(float(w["n_total"].mean()), 1), "avg365": round(float(y["n_total"].mean()), 1),
                    "tanker7": round(float(w["n_tanker"].mean()), 1),
                    "tanker365": round(float(y["n_tanker"].mean()), 1),
                    "spark": [int(v) for v in g["n_total"].iloc[-60:].tolist()]})
    return out


def _choke_sim() -> list[dict]:
    rows = sim.chokepoints(list(CHOKEPOINT_COORDS))
    for r in rows:
        r["lat"], r["lon"] = CHOKEPOINT_COORDS[r["name"]]
    return rows


def chokepoints() -> dict:
    return _envelope("chokepoints", "IMF PortWatch (AIS transits; ~1 week lag)", 3600, _choke_live, _choke_sim)


# ---------------------------------------------------------------- weather and air quality

CITIES = [
    ("New Delhi", 28.61, 77.21), ("Mumbai", 19.08, 72.88), ("Kolkata", 22.57, 88.36), ("Chennai", 13.08, 80.27),
    ("Bengaluru", 12.97, 77.59), ("Hyderabad", 17.39, 78.49), ("Ahmedabad", 23.02, 72.57), ("Lucknow", 26.85, 80.95),
    ("Patna", 25.59, 85.14), ("Jaipur", 26.91, 75.79), ("Guwahati", 26.14, 91.74), ("Kochi", 9.93, 76.27),
    ("Dhaka", 23.81, 90.41), ("Karachi", 24.86, 67.0), ("Colombo", 6.93, 79.86), ("Dubai", 25.2, 55.27),
    ("Singapore", 1.35, 103.82), ("Beijing", 39.9, 116.4), ("Shanghai", 31.23, 121.47), ("Tokyo", 35.68, 139.69),
    ("London", 51.51, -0.13), ("Frankfurt", 50.11, 8.68), ("New York", 40.71, -74.01), ("São Paulo", -23.55, -46.63),
    ("Lagos", 6.52, 3.38), ("Jakarta", -6.21, 106.85),
]
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_AQ = "https://air-quality-api.open-meteo.com/v1/air-quality"


def _weather_live() -> list[dict]:
    lats = ",".join(str(c[1]) for c in CITIES)
    lons = ",".join(str(c[2]) for c in CITIES)
    wx = _http.get_json(OPEN_METEO, {"latitude": lats, "longitude": lons, "timezone": "UTC",
                                     "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation,weather_code"},
                        ttl=900, source="open-meteo")
    try:
        aq = _http.get_json(OPEN_METEO_AQ, {"latitude": lats, "longitude": lons, "current": "pm2_5,us_aqi"},
                            ttl=900, source="open-meteo")
    except Exception:
        aq = [{} for _ in CITIES]
    wx = wx if isinstance(wx, list) else [wx]
    aq = aq if isinstance(aq, list) else [aq]
    out = []
    for (city, lat, lon), w, a in zip(CITIES, wx, aq):
        c, ac = w.get("current", {}), (a or {}).get("current", {})
        out.append({"city": city, "lat": lat, "lon": lon, "temp": c.get("temperature_2m"),
                    "humidity": c.get("relative_humidity_2m"), "wind": c.get("wind_speed_10m"),
                    "precip": c.get("precipitation"), "code": c.get("weather_code"),
                    "pm25": ac.get("pm2_5"), "aqi": ac.get("us_aqi"), "time": c.get("time")})
    return out


def weather() -> dict:
    return _envelope("weather", "Open-Meteo (forecast model current conditions; CAMS air quality)", 900,
                     _weather_live, lambda: sim.weather(CITIES))


# ---------------------------------------------------------------- satellites (CelesTrak)

CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php"
SAT_GROUPS: dict[str, list[tuple[str, str, str]]] = {
    # group -> [(query kind, value, tag)]
    "gnss": [("GROUP", "gnss", "")],
    "stations": [("GROUP", "stations", "Space stations")],
    "military": [
        ("GROUP", "military", "CelesTrak 'military' group"),
        ("NAME", "USA ", "US government (USA-nnn designation)"),
        ("NAME", "YAOGAN", "China Yaogan (reconnaissance)"),
        ("NAME", "GAOFEN", "China Gaofen (high-res EO, dual-use)"),
        ("NAME", "RISAT", "India RISAT (radar imaging)"),
        ("NAME", "CARTOSAT", "India Cartosat (high-res EO, dual-use)"),
        ("NAME", "EMISAT", "India EMISAT (electronic intelligence)"),
        ("NAME", "GSAT-7", "India GSAT-7 (naval/air force comms)"),
        ("NAME", "OFEQ", "Israel Ofeq (reconnaissance)"),
        ("NAME", "SAR-LUPE", "Germany SAR-Lupe (radar reconnaissance)"),
        ("NAME", "IGS", "Japan IGS (information gathering)"),
        ("NAME", "LACROSSE", "US Lacrosse (radar imaging)"),
        ("NAME", "BARS-M", "Russia Bars-M (mapping)"),
        ("NAME", "LOTOS", "Russia Lotos-S (signals intelligence)"),
        ("NAME", "TOPAZ", "Russia (radar reconnaissance)"),
    ],
}


def _constellation(name: str) -> str:
    n = name.upper()
    for key, tag in (("IRNSS", "NavIC"), ("NVS-", "NavIC"), ("GPS", "GPS"), ("NAVSTAR", "GPS"),
                     ("GSAT0", "Galileo"), ("GALILEO", "Galileo"), ("BEIDOU", "BeiDou"), ("COSMOS", "GLONASS"),
                     ("GLONASS", "GLONASS"), ("QZS", "QZSS")):
        if key in n:
            return tag
    return "SBAS/other"


def _parse_tle(text: str, tag: str) -> list[dict]:
    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    out = []
    for i in range(0, len(lines) - 2, 3):
        name, l1, l2 = lines[i].strip(), lines[i + 1], lines[i + 2]
        if not (l1.startswith("1 ") and l2.startswith("2 ")):
            continue
        out.append({"name": name, "norad": int(l1[2:7]), "l1": l1, "l2": l2,
                    "tag": tag or _constellation(name)})
    return out


def _sats_live(group: str) -> list[dict]:
    def one(q):
        kind, value, tag = q
        try:
            body = _http.get(CELESTRAK, {kind: value, "FORMAT": "tle"}, ttl=6 * 3600, source="celestrak")
        except _http.SourceError as e:
            if "No GP data" in str(e) and kind == "NAME":   # a programme with no public elements right now
                return []
            raise
        txt = body.decode("utf-8", "replace")
        if "No GP data found" in txt:
            return []
        return _parse_tle(txt, tag)

    with ThreadPoolExecutor(6) as ex:
        parts = list(ex.map(one, SAT_GROUPS[group]))
    seen, out = set(), []
    for part in parts:
        for s in part:
            if group == "military" and any(k in s["name"] for k in ("NAVSTAR", "GPS ")):
                continue      # US navigation satellites carry USA-nnn names too; they belong to GNSS
            if s["norad"] not in seen:
                seen.add(s["norad"])
                out.append(s)
    if not out:
        raise _http.SourceError("celestrak", f"no elements for {group}")
    return out


def _sats_sim(group: str) -> list[dict]:
    r = sim._rng("sats", group)
    n, alt = {"gnss": (90, 20200), "stations": (6, 420), "military": (60, 500)}.get(group, (30, 600))
    return [{"name": f"SIM-{group.upper()}-{i}", "norad": 90000 + i, "tag": "Simulated",
             "sim": {"inc": r.choice([55, 64.8, 97.5, 98.2, 51.6]), "raan": r.uniform(0, 360),
                     "ma": r.uniform(0, 360), "alt_km": alt * r.uniform(.95, 1.05)}} for i in range(n)]


def satellites(group: str) -> dict:
    if group not in SAT_GROUPS:
        raise ValueError(f"unknown satellite group {group!r}; choose from {list(SAT_GROUPS)}")
    return _envelope("satellites", "CelesTrak GP element sets (public catalogue, TLE)", 2 * 3600,
                     lambda: _sats_live(group), lambda: _sats_sim(group), key=group,
                     note="Only publicly catalogued objects; classified payloads are absent." if group == "military" else "")


# ---------------------------------------------------------------- economics map

NE_COUNTRIES = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
                "ne_110m_admin_0_countries.geojson")


def world_geojson() -> bytes:
    """Natural Earth 1:110m country outlines (public domain), cached forever on disk."""
    return _http.get(NE_COUNTRIES, ttl=None, source="naturalearth")


def econ_map(indicator: str = "NGDP_RPCH", year: int | None = None) -> dict:
    from ..sources import imf

    year = int(year or pd.Timestamp.today().year)

    def live():
        js = _http.get_json(f"{imf.DATAMAPPER}/{indicator}", source="imf")
        vals = js.get("values", {}).get(indicator) or {}
        if not vals:
            raise _http.SourceError("imf", f"no values for {indicator}")
        return {"indicator": indicator, "label": imf.WEO.get(indicator, indicator), "year": year,
                "values": {c: v.get(str(year)) for c, v in vals.items() if len(c) == 3 and v.get(str(year)) is not None}}

    def fallback():
        r = sim._rng("econ", indicator, year)
        return {"indicator": indicator, "label": imf.WEO.get(indicator, indicator) + " [SIMULATED]", "year": year,
                "values": {}, "random_seed": r.random()}

    note = "IMF WEO; values after a country's latest actual year are IMF projections."
    return _envelope("econ", "IMF World Economic Outlook (DataMapper)", 6 * 3600, live, fallback,
                     note=note, key=(indicator, year))


# ---------------------------------------------------------------- India macro snapshot

_SNAP_SIM = [("gdp_growth", 7.4, "% y/y"), ("cpi_inflation", 1.5, "% y/y"), ("wpi_inflation", 0.3, "% y/y"),
             ("iip_growth", 4.0, "% y/y"), ("unemployment", 5.2, "%"), ("repo_rate", 5.5, "%"),
             ("usdinr", 88.6, "INR per USD"), ("reer", 101.0, "index, 2020=100"),
             ("forex_reserves", 690000, "US$ million")]


def india_snapshot() -> dict:
    from .. import india

    def live():
        df = india.snapshot()
        if "error" in df and df["error"].notna().all():
            raise _http.SourceError("india", "every headline series failed")
        df = df.astype(object).where(df.notna(), None)
        return [{k: (str(v) if k == "date" and v is not None else v) for k, v in r.items()} for r in df.to_dict("records")]

    def fallback():
        return [{"series": s, "value": v, "unit": u, "date": None, "source": "SIMULATED"} for s, v, u in _SNAP_SIM]

    return _envelope("india", "MoSPI, RBI, BIS, FRED, IMF (see each row)", 3600, live, fallback)
