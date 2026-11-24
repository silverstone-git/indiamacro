"""Analyst tools: a registry of queryable series plus functions that slice them.

Each tool returns ``{"text": <plain summary with numbers>, "charts": [...], "sources": [...],
"sim": bool}``. The text is what an LLM (or the mock analyst) reasons over; charts are
simple JSON specs the terminal draws with Plotly. Every number in the text is computed
here, so the assistant never has to invent one.

If a series cannot be loaded, a simulated stand-in is used and ``sim`` is True; the text
then says SIMULATED in capitals so neither the model nor the reader can miss it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from .. import countries as _countries
from .. import india
from ..analysis import data as D
from ..analysis.framework import memo
from . import env, sim


@memo(3600)
def _yahoo(ticker: str) -> pd.Series:
    from ..sources import energy

    return energy._yahoo_close([ticker], start="2005-01-01")[ticker].dropna()


def _choke(name: str) -> pd.Series:
    df = D.chokepoints()
    return df[df["chokepoint"] == name].set_index("date")["n_total"].astype(float)


@dataclass
class Spec:
    label: str
    unit: str
    source: str
    loader: Callable[[], pd.Series]
    aliases: list[str] = field(default_factory=list)
    sim: dict = field(default_factory=dict)   # kwargs for sim.series when the real loader fails


SERIES: dict[str, Spec] = {
    "india_cpi": Spec("India CPI inflation", "% y/y", "MoSPI CPI, base 2012 (base-2024 releases are not in this series; never splice)", india.cpi_inflation,
                      ["inflation", "cpi", "consumer prices"], dict(mean_revert=5, vol=.15)),
    "india_food_cpi": Spec("India CPI food inflation", "% y/y", "MoSPI CPI, base 2012 (base-2024 releases are not in this series; never splice)", india.cpi_food_inflation,
                           ["food inflation", "food prices", "food"], dict(mean_revert=6, vol=.3)),
    "india_wpi": Spec("India WPI inflation", "% y/y", "Office of the Economic Adviser, DPIIT", D.wpi_infl,
                      ["wpi", "wholesale"], dict(mean_revert=3, vol=.4)),
    "india_iip": Spec("India industrial production (IIP) growth", "% y/y", "MoSPI IIP", india.iip_growth,
                      ["iip", "industrial production", "industry", "factory"], dict(mean_revert=4, vol=.5)),
    "india_gdp_growth": Spec("India real GDP growth", "% y/y", "MoSPI National Accounts",
                             lambda: india.gdp_growth(projections=False), ["gdp", "growth", "economy"],
                             dict(freq="YS", periods=30, mean_revert=6.5, vol=.3)),
    "india_unemployment": Spec("India unemployment rate (PLFS)", "%", "MoSPI PLFS", india.unemployment,
                               ["unemployment", "jobs", "labour", "labor"], dict(periods=36, mean_revert=5, vol=.05)),
    "repo_rate": Spec("RBI policy repo rate", "%", "BIS (Reserve Bank of India)", D.repo_monthly,
                      ["repo", "rbi", "policy rate", "interest rate", "rates"], dict(mean_revert=6, vol=.05)),
    "usdinr": Spec("Rupees per US dollar", "INR per USD", "FRED DEXINUS (Federal Reserve H.10)", D.usdinr_daily,
                   ["rupee", "inr", "usdinr", "usd/inr", "exchange rate", "currency"],
                   dict(freq="B", periods=2500, level=60, vol=.003)),
    "forex_reserves": Spec("India forex reserves", "US$ million", "RBI (via MoSPI eSankhyiki)", india.forex_reserves,
                           ["reserves", "forex", "fx reserves"], dict(level=400000, vol=.01)),
    "reer": Spec("Rupee real effective exchange rate", "index, 2020=100", "BIS", india.reer,
                 ["reer", "real exchange rate", "competitiveness"], dict(level=100, vol=.01)),
    "brent": Spec("Brent crude, spot", "US$/bbl", "EIA via FRED (DCOILBRENTEU)", lambda: D.spot()["brent"],
                  ["brent", "oil", "crude"], dict(freq="B", periods=2500, level=70, vol=.02)),
    "wti": Spec("WTI crude, spot", "US$/bbl", "EIA via FRED (DCOILWTICO)", lambda: D.spot()["wti"],
                ["wti"], dict(freq="B", periods=2500, level=65, vol=.02)),
    "diesel_crack": Spec("Diesel crack vs Brent", "US$/bbl", "EIA via FRED", lambda: D.cracks()["diesel_crack"],
                         ["diesel", "crack", "refining margin"], dict(freq="B", periods=2500, mean_revert=25, vol=.1)),
    "us_cpi": Spec("US CPI inflation", "% y/y", "BLS via FRED (CPIAUCSL)",
                   lambda: (D.us_cpi().pct_change(12, fill_method=None) * 100).dropna(),
                   ["us inflation", "us cpi", "american inflation"], dict(mean_revert=3, vol=.15)),
    "nifty": Spec("NIFTY 50", "index", "NSE via Yahoo Finance", lambda: _yahoo("^NSEI"),
                  ["nifty", "stocks", "equities", "stock market", "sensex", "market"],
                  dict(freq="B", periods=2500, level=8000, vol=.012)),
    "gold": Spec("Gold futures", "US$/oz", "COMEX via Yahoo Finance", lambda: _yahoo("GC=F"),
                 ["gold"], dict(freq="B", periods=2500, level=1200, vol=.01)),
    "sp500": Spec("S&P 500", "index", "Yahoo Finance", lambda: _yahoo("^GSPC"),
                  ["s&p", "sp500", "us stocks", "wall street"], dict(freq="B", periods=2500, level=2000, vol=.011)),
    "dxy": Spec("US dollar index (DXY)", "index", "ICE via Yahoo Finance", lambda: _yahoo("DX-Y.NYB"),
                ["dxy", "dollar index", "dollar"], dict(freq="B", periods=2500, level=95, vol=.004)),
    "ust10y": Spec("US 10-year Treasury yield", "%", "CBOE via Yahoo Finance", lambda: _yahoo("^TNX"),
                   ["treasury", "10y", "us yield", "bond yield", "yields"], dict(freq="B", periods=2500, mean_revert=3, vol=.02)),
    "copper": Spec("Copper futures", "US$/lb", "COMEX via Yahoo Finance", lambda: _yahoo("HG=F"),
                   ["copper"], dict(freq="B", periods=2500, level=3, vol=.015)),
    "natgas": Spec("Henry Hub natural gas futures", "US$/MMBtu", "NYMEX via Yahoo Finance", lambda: _yahoo("NG=F"),
                   ["natural gas", "gas", "lng", "henry hub"], dict(freq="B", periods=2500, level=3, vol=.03)),
    "bitcoin": Spec("Bitcoin", "US$", "Yahoo Finance", lambda: _yahoo("BTC-USD"),
                    ["bitcoin", "btc", "crypto"], dict(freq="D", periods=2500, level=10000, vol=.03)),
    "hormuz_transits": Spec("Strait of Hormuz transits", "vessels/day", "IMF PortWatch (AIS)",
                            lambda: _choke("Strait of Hormuz"), ["hormuz", "persian gulf"],
                            dict(freq="D", periods=700, mean_revert=110, vol=.1)),
    "red_sea_transits": Spec("Bab el-Mandeb transits", "vessels/day", "IMF PortWatch (AIS)",
                             lambda: _choke("Bab el-Mandeb Strait"), ["red sea", "bab el-mandeb", "houthi"],
                             dict(freq="D", periods=700, mean_revert=40, vol=.15)),
    "suez_transits": Spec("Suez Canal transits", "vessels/day", "IMF PortWatch (AIS)",
                          lambda: _choke("Suez Canal"), ["suez"], dict(freq="D", periods=700, mean_revert=40, vol=.15)),
    "malacca_transits": Spec("Malacca Strait transits", "vessels/day", "IMF PortWatch (AIS)",
                             lambda: _choke("Malacca Strait"), ["malacca"], dict(freq="D", periods=700, mean_revert=230, vol=.08)),
}


def resolve(name: str) -> str:
    """Map a key, label or alias ("rupee", "oil") to a SERIES key."""
    n = name.strip().lower().replace("-", "_")
    if n in SERIES:
        return n
    for k, sp in SERIES.items():
        if n == sp.label.lower() or n.replace("_", " ") in sp.aliases:
            return k
    for k, sp in SERIES.items():
        if any(a in n.replace("_", " ") for a in sp.aliases):
            return k
    raise KeyError(f"unknown series {name!r}; known: {', '.join(SERIES)}")


def mentions(text: str) -> list[str]:
    """Series keys mentioned in free text, in order of appearance (longest alias wins)."""
    t = text.lower()
    hits = []
    for k, sp in SERIES.items():
        best = None
        for a in [k.replace("_", " "), k, *sp.aliases]:
            m = re.search(rf"(?<![\w]){re.escape(a)}(?![\w])", t)
            i = m.start() if m else -1
            if i >= 0 and (best is None or i < best[0] or (i == best[0] and len(a) > best[1])):
                best = (i, len(a))
        if best:
            hits.append((best[0], -best[1], k))
    out = []
    used: list[tuple[int, int]] = []
    for i, neg_len, k in sorted(hits):
        span = (i, i - neg_len)
        if any(a <= span[0] < b for a, b in used):      # "food inflation" shadows "inflation"
            continue
        used.append(span)
        out.append(k)
    return out


def load(key: str) -> pd.Series:
    sp = SERIES[key]
    s = None
    if not env.demo():
        try:
            s = sp.loader().dropna().astype(float)
            s.index = pd.to_datetime(s.index)
            s = s.sort_index()
            s.attrs.update(source=sp.source, unit=sp.unit, sim=False)
        except Exception:
            s = None
    if s is None or s.empty:
        s = sim.series(key, **sp.sim)
        s.attrs.update(unit=sp.unit)
    s.name = key
    return s


# ---------------------------------------------------------------- helpers

def _freq(s: pd.Series) -> str:
    if len(s) < 3:
        return "A"
    d = pd.Series(s.index).diff().dt.days.median()
    return "D" if d <= 4 else "W" if d <= 10 else "M" if d <= 45 else "Q" if d <= 120 else "A"


_PER_YEAR = {"D": 252, "W": 52, "M": 12, "Q": 4, "A": 1}
TRANSFORMS = ["level", "yoy", "pct", "diff", "log", "zscore", "index100"]


def transform(s: pd.Series, how: str = "level") -> pd.Series:
    if how == "level":
        return s
    if how == "yoy":
        return (s / s.shift(_PER_YEAR[_freq(s)]) - 1).dropna() * 100
    if how == "pct":
        return s.pct_change(fill_method=None).dropna() * 100
    if how == "diff":
        return s.diff().dropna()
    if how == "log":
        return np.log(s.where(s > 0)).dropna()
    if how == "zscore":
        return (s - s.mean()) / s.std()
    if how == "index100":
        return s / s.iloc[0] * 100
    raise ValueError(f"transform must be one of {TRANSFORMS}")


def resample(s: pd.Series, freq: str | None) -> pd.Series:
    if not freq:
        return s
    rule = {"W": "W-FRI", "M": "MS", "Q": "QS", "A": "YS"}.get(freq.upper())
    return s.resample(rule).mean().dropna() if rule else s


def _thin(s: pd.Series, n: int = 1500) -> pd.Series:
    return s if len(s) <= n else s.iloc[:: math.ceil(len(s) / n)]


def _trace(s: pd.Series, name: str, axis: str = "y") -> dict:
    s = _thin(s.dropna())
    return {"name": name, "x": [d.strftime("%Y-%m-%d") for d in s.index], "y": [round(float(v), 4) for v in s], "axis": axis}


def _label(key: str, how: str = "level") -> str:
    sp = SERIES[key]
    return sp.label if how == "level" else f"{sp.label} [{how}]"


def _fmt(v, d: int = 2) -> str:
    return "n/a" if v is None or (isinstance(v, float) and not math.isfinite(v)) else f"{v:,.{d}f}"


def _src(s: pd.Series, key: str) -> str:
    return "SIMULATED (source unavailable)" if s.attrs.get("sim") else SERIES[key].source


def _start(s: pd.Series, start) -> pd.Series:
    return s[s.index >= pd.Timestamp(start)] if start else s


# ---------------------------------------------------------------- tools

def list_series() -> dict:
    rows = [f"{k}: {sp.label} ({sp.unit}; {sp.source})" for k, sp in SERIES.items()]
    return {"text": "Available series:\n" + "\n".join(rows), "charts": [], "sources": [], "sim": False}


def describe(s: pd.Series, key: str, how: str = "level", is_sim: bool = False) -> str:
    s = s.dropna()
    if s.empty:
        return f"{_label(key, how)}: no observations."
    last, d = float(s.iloc[-1]), s.index[-1].date()
    f = _freq(s)
    yr = s.iloc[-1 - _PER_YEAR[f]] if len(s) > _PER_YEAR[f] else None
    pct = float((s < last).mean() * 100)
    recent = s.iloc[-min(len(s), max(6, _PER_YEAR[f] // 4)):]
    slope = np.polyfit(np.arange(len(recent)), recent.values, 1)[0] if len(recent) > 2 else 0
    unit = "" if how in ("zscore", "index100") else f" {SERIES[key].unit}" if how == "level" else (" pp" if how == "diff" else " %")
    lines = [
        f"{_label(key, how)} — source: {'SIMULATED (source unavailable)' if is_sim else SERIES[key].source}; frequency {f}; {len(s)} obs from {s.index[0].date()} to {d}.",
        f"  latest {_fmt(last)}{unit} on {d}; higher than {pct:.0f}% of observations in the sample.",
        f"  sample mean {_fmt(s.mean())}, std {_fmt(s.std())}; min {_fmt(s.min())} on {s.idxmin().date()}, "
        f"max {_fmt(s.max())} on {s.idxmax().date()}.",
    ]
    if yr is not None:
        ch = last - float(yr)
        rel = f" ({(last / float(yr) - 1) * 100:+.1f}%)" if how == "level" and float(yr) > 0 else ""
        lines.append(f"  change over the past year: {ch:+,.2f}{rel}.")
    lines.append(f"  recent direction ({len(recent)} obs): {'rising' if slope > 0 else 'falling' if slope < 0 else 'flat'}.")
    if is_sim:
        lines.append("  WARNING: SIMULATED stand-in, not real data.")
    return "\n".join(lines)


def get_series(names: list[str] | str, start: str | None = None, transform_: str = "level",
               freq: str | None = None) -> dict:
    names = [names] if isinstance(names, str) else list(names)
    keys = [resolve(n) for n in names][:6]
    texts, traces, sources, any_sim = [], [], [], False
    for k in keys:
        s = _start(resample(load(k), freq), start)
        t = transform(s, transform_)
        any_sim |= bool(s.attrs.get("sim"))
        texts.append(describe(t, k, transform_, bool(s.attrs.get("sim"))))
        traces.append((k, _trace(t, _label(k, transform_) + (" [SIM]" if s.attrs.get("sim") else ""))))
        sources.append(_src(s, k))
    ylab = SERIES[keys[0]].unit if transform_ == "level" else transform_
    if transform_ == "level" and len({SERIES[k].unit for k in keys}) > 1:
        # different units: small multiples, never a second y-axis
        charts = [{"type": "line", "title": SERIES[k].label, "traces": [tr], "yaxis": SERIES[k].unit,
                   "sources": [src]} for (k, tr), src in zip(traces, sources)]
    else:
        title = " vs ".join(SERIES[k].label for k in keys) + ("" if transform_ == "level" else f" — {transform_}")
        charts = [{"type": "line", "title": title, "traces": [tr for _, tr in traces], "yaxis": ylab, "sources": sources}]
    return {"text": "\n\n".join(texts), "charts": charts, "sources": sources, "sim": any_sim}


def correlate(a: str, b: str, freq: str = "M", transform_: str = "auto", max_lag: int = 12,
              start: str | None = None) -> dict:
    """Correlation of a and b at lags -max_lag..+max_lag. Positive best lag = ``a`` leads ``b``."""
    ka, kb = resolve(a), resolve(b)
    sa, sb = load(ka), load(kb)
    sim_any = bool(sa.attrs.get("sim") or sb.attrs.get("sim"))
    ra, rb = _start(resample(sa, freq), start), _start(resample(sb, freq), start)

    def auto(k, s):
        if transform_ != "auto":
            return transform_
        return "diff" if SERIES[k].unit.startswith("%") else "yoy" if freq.upper() in ("M", "Q") else "pct"

    ha, hb = auto(ka, ra), auto(kb, rb)
    ta, tb = transform(ra, ha), transform(rb, hb)
    df = pd.concat([ta.rename("a"), tb.rename("b")], axis=1).dropna()
    if len(df) < 12:
        return {"text": f"Not enough overlapping observations between {ka} and {kb} ({len(df)}).",
                "charts": [], "sources": [_src(sa, ka), _src(sb, kb)], "sim": sim_any}
    lags = list(range(-max_lag, max_lag + 1))
    cors = []
    for L in lags:   # L>0: a at t-L vs b at t  => a leads b by L periods
        c = df["a"].shift(L).corr(df["b"])
        cors.append(None if pd.isna(c) else round(float(c), 3))
    valid = [(abs(c), L, c) for L, c in zip(lags, cors) if c is not None]
    _, best_lag, best_c = max(valid)
    c0 = cors[lags.index(0)]
    n = len(df)
    se = 1 / math.sqrt(n)
    win = {"M": 36, "Q": 12, "W": 104, "A": 10}.get(freq.upper(), 60)
    roll = df["a"].rolling(win).corr(df["b"]).dropna()
    level = pd.concat([ra.rename("a"), rb.rename("b")], axis=1).dropna()
    z = (level - level.mean()) / level.std()

    def strength(c):
        c = abs(c)
        return "negligible" if c < .1 else "weak" if c < .3 else "moderate" if c < .5 else "strong"

    unit = freq.upper()
    lead = (f"{SERIES[ka].label} leads by {best_lag} {unit}" if best_lag > 0 else
            f"{SERIES[kb].label} leads by {-best_lag} {unit}" if best_lag < 0 else "contemporaneous")
    text = "\n".join([
        f"Correlation of {SERIES[ka].label} [{ha}] with {SERIES[kb].label} [{hb}], {unit} data, n={n} "
        f"({df.index[0].date()} to {df.index[-1].date()}).",
        f"  same-period correlation r={_fmt(c0, 3)} ({strength(c0 or 0)}); ~95% noise band ±{2 * se:.2f}.",
        f"  strongest at lag {best_lag:+d} ({lead}): r={best_c:.3f}.",
        f"  rolling {win}-period correlation: latest {_fmt(roll.iloc[-1] if len(roll) else None, 2)}, "
        f"range {_fmt(roll.min() if len(roll) else None, 2)} to {_fmt(roll.max() if len(roll) else None, 2)} "
        "(unstable correlations are common; treat a single number with care).",
        "  Correlation is not causation, and lags picked by searching many lags overstate significance.",
        *(["  WARNING: at least one series is SIMULATED, not real data."] if sim_any else []),
    ])
    srcs = [_src(sa, ka), _src(sb, kb)]
    charts = [
        {"type": "line", "title": f"{SERIES[ka].label} vs {SERIES[kb].label} (standardised levels)",
         "traces": [_trace(z["a"], SERIES[ka].label), _trace(z["b"], SERIES[kb].label)], "yaxis": "z-score", "sources": srcs},
        {"type": "bar", "title": f"Cross-correlation by lag (+ = {SERIES[ka].label} leads)",
         "x": lags, "y": cors, "yaxis": "r", "band": 2 * se, "sources": srcs},
        {"type": "line", "title": f"Rolling {win}-period correlation", "traces": [_trace(roll, "rolling r")], "yaxis": "r", "sources": srcs},
    ]
    return {"text": text, "charts": charts, "sources": [_src(sa, ka), _src(sb, kb)], "sim": sim_any,
            "stats": {"r0": c0, "best_lag": best_lag, "best_r": best_c, "n": n}}


def compare_countries(indicator: str = "gdp_growth", countries="BRICS", start: int = 2000) -> dict:
    from ..compare import INDICATORS, compare

    try:
        if env.demo():
            raise RuntimeError("demo mode")
        t = compare(indicator, countries, start=start)
        src, is_sim = f"{t.attrs.get('source', '').upper()} {t.attrs.get('code', '')}".strip(), False
    except Exception as e:
        codes = _countries.expand(countries)
        t = pd.DataFrame({c: sim.series(f"{indicator}{c}", freq="YS", periods=30, mean_revert=4, vol=.4).values
                          for c in codes}, index=pd.date_range(end=pd.Timestamp.today(), periods=30, freq="YS"))
        src, is_sim = f"SIMULATED ({type(e).__name__})", True
    this_year = pd.Timestamp.today().year
    actual = t[t.index.year < this_year]
    last = actual.ffill().iloc[-1].dropna().sort_values(ascending=False)
    avg10 = actual.iloc[-10:].mean().reindex(last.index)
    lines = [f"{indicator} for {', '.join(t.columns)} — source {src}. Latest full year {actual.index[-1].year}"
             f" (values from {this_year} on are IMF projections when the source is IMF):"]
    for c, v in last.items():
        lines.append(f"  {_countries.name(c) if not is_sim else c}: {v:.2f} (10-yr avg {avg10[c]:.2f})")
    if "IND" in last.index:
        lines.append(f"  India ranks {list(last.index).index('IND') + 1} of {len(last)}.")
    if is_sim:
        lines.append("  WARNING: SIMULATED values.")
    traces = [_trace(t[c].dropna(), c) for c in t.columns]
    chart = {"type": "line", "title": f"{indicator} — {', '.join(t.columns)}", "traces": traces, "yaxis": indicator,
             "shade_from": f"{this_year}-01-01", "sources": [src]}
    return {"text": "\n".join(lines), "charts": [chart], "sources": [src], "sim": is_sim,
            "indicators": list(INDICATORS)}


def window(series: str, date: str, before: int = 30, after: int = 60) -> dict:
    """What a series did around a date: levels and % change before vs after (calendar days)."""
    k = resolve(series)
    s = load(k)
    d = pd.Timestamp(date)
    w = s[(s.index >= d - pd.Timedelta(days=before)) & (s.index <= d + pd.Timedelta(days=after))]
    if w.empty or w.index.min() > d:
        return {"text": f"No {k} data around {d.date()}.", "charts": [], "sources": [_src(s, k)], "sim": bool(s.attrs.get("sim"))}
    pre = s[s.index < d]
    v0 = float(pre.iloc[-1]) if len(pre) else float(w.iloc[0])
    v1 = float(w.iloc[-1])
    hi, lo = w.max(), w.min()
    text = (f"{SERIES[k].label} around {d.date()} ({before} days before to {after} after); source {_src(s, k)}.\n"
            f"  last value before the date {_fmt(v0)}; at end of window {_fmt(v1)} ({v1 - v0:+.2f}"
            f"{f', {(v1 / v0 - 1) * 100:+.1f}%' if v0 else ''}); window high {_fmt(hi)} on {w.idxmax().date()}, "
            f"low {_fmt(lo)} on {w.idxmin().date()}.")
    chart = {"type": "line", "title": f"{SERIES[k].label} around {d.date()}", "traces": [_trace(w, SERIES[k].label)],
             "yaxis": SERIES[k].unit, "vline": str(d.date()), "sources": [_src(s, k)]}
    return {"text": text, "charts": [chart], "sources": [_src(s, k)], "sim": bool(s.attrs.get("sim"))}


def live_snapshot() -> dict:
    """What the live feeds show right now (markets, quakes, natural events, air quality, shipping)."""
    from . import feeds

    parts, sims = [], []
    q = feeds.quotes()
    sims.append(q["status"] == "sim")
    movers = sorted([x for x in q["data"] if x.get("chg_pct") is not None], key=lambda x: -abs(x["chg_pct"]))
    parts.append(f"Markets ({q['status'].upper()}, {q['source']}): " + "; ".join(
        f"{m['label']} {m['last']:,.2f} ({m['chg_pct']:+.2f}%)" for m in movers[:8]))
    qk = feeds.quakes()
    sims.append(qk["status"] == "sim")
    big = sorted(qk["data"], key=lambda x: -(x["mag"] or 0))[:3]
    parts.append(f"Earthquakes M4.5+ past 7 days ({qk['status'].upper()}): {len(qk['data'])}; largest: " +
                 "; ".join(f"M{x['mag']} {x['place']}" for x in big))
    ev = feeds.natural_events()
    sims.append(ev["status"] == "sim")
    cats = pd.Series([e["category"] for e in ev["data"]]).value_counts()
    parts.append(f"Open natural events ({ev['status'].upper()}, NASA EONET): " + ", ".join(f"{c} {n}" for c, n in cats.items()))
    wx = feeds.weather()
    sims.append(wx["status"] == "sim")
    worst = sorted([w for w in wx["data"] if w.get("pm25") is not None], key=lambda w: -w["pm25"])[:5]
    parts.append(f"Worst PM2.5 among tracked cities ({wx['status'].upper()}, Open-Meteo/CAMS model): " +
                 ", ".join(f"{w['city']} {w['pm25']:.0f} µg/m³" for w in worst))
    ch = feeds.chokepoints()
    sims.append(ch["status"] == "sim")
    dev = sorted(ch["data"], key=lambda c: (c["last7"] / c["avg365"] - 1) if c["avg365"] else 0)
    parts.append(f"Chokepoint transits, 7-day avg vs 1-year avg ({ch['status'].upper()}, IMF PortWatch, data to "
                 f"{ch['data'][0].get('date') if ch['data'] else '?'}): " +
                 ", ".join(f"{c['name']} {c['last7']:.0f} vs {c['avg365']:.0f} ({(c['last7'] / c['avg365'] - 1) * 100:+.0f}%)"
                           for c in dev if c["avg365"]))
    return {"text": "\n".join(parts), "charts": [], "sources": [q["source"], qk["source"], ev["source"], wx["source"], ch["source"]],
            "sim": any(sims)}


# OpenAI-style tool definitions (also used by the mock planner) --------------------

TOOLS = {
    "list_series": (list_series, {"type": "object", "properties": {}},
                    "List every series the terminal can query, with units and sources."),
    "get_series": (lambda names, start=None, transform="level", freq=None: get_series(names, start, transform, freq), {
        "type": "object", "properties": {
            "names": {"type": "array", "items": {"type": "string"}, "description": "series keys or aliases, max 6"},
            "start": {"type": "string", "description": "ISO start date, optional"},
            "transform": {"type": "string", "enum": TRANSFORMS},
            "freq": {"type": "string", "enum": ["D", "W", "M", "Q", "A"], "description": "resample (mean)"}},
        "required": ["names"]}, "Fetch series, return summary statistics and a chart."),
    "correlate": (lambda a, b, freq="M", transform="auto", max_lag=12, start=None:
                  correlate(a, b, freq, transform, max_lag, start), {
        "type": "object", "properties": {
            "a": {"type": "string"}, "b": {"type": "string"},
            "freq": {"type": "string", "enum": ["W", "M", "Q", "A"]},
            "transform": {"type": "string", "enum": ["auto", *TRANSFORMS]},
            "max_lag": {"type": "integer"}, "start": {"type": "string"}},
        "required": ["a", "b"]}, "Lead/lag cross-correlation between two series, with rolling correlation."),
    "compare_countries": (compare_countries, {
        "type": "object", "properties": {
            "indicator": {"type": "string", "description": "gdp_growth, inflation, gdp_usd, gdp_per_capita_ppp, "
                          "unemployment, govt_debt, fiscal_balance, current_account, exports_gdp, fdi_gdp, ..."},
            "countries": {"type": "string", "description": "group (BRICS, G7, G20, SOUTH_ASIA, ASEAN, EM_ASIA, QUAD) "
                          "or comma-separated ISO3 codes"},
            "start": {"type": "integer"}},
        "required": ["indicator"]}, "Cross-country comparison (IMF WEO / World Bank), India first."),
    "window": (window, {
        "type": "object", "properties": {
            "series": {"type": "string"}, "date": {"type": "string"},
            "before": {"type": "integer"}, "after": {"type": "integer"}},
        "required": ["series", "date"]}, "What a series did around a date (event window, calendar days)."),
    "live_snapshot": (live_snapshot, {"type": "object", "properties": {}},
                      "Current state of live feeds: markets, quakes, natural events, air quality, shipping chokepoints."),
}


def call(name: str, args: dict) -> dict:
    fn = TOOLS[name][0]
    if name == "compare_countries" and isinstance(args.get("countries"), str) and "," in args["countries"]:
        args = {**args, "countries": [c.strip() for c in args["countries"].split(",")]}
    return fn(**args)
