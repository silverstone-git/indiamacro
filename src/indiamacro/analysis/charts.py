"""Builders for the JSON chart specs the web UI renders (with Plotly).

A spec is a plain dict, e.g.::

    {"kind": "line", "title": ..., "unit": ..., "source": ...,
     "traces": [{"name": ..., "x": [...], "y": [...], "axis": "y" | "y2", "dash": bool}],
     "events": [{"x": "2022-02-24", "label": ...}], "bands": [...], "hbands": [...]}

Kinds: line, area (stacked), bar, hbar, scatter, table, kpis.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def _x(index) -> list:
    if isinstance(index, pd.DatetimeIndex):
        return [d.strftime("%Y-%m-%d") for d in index]
    return [str(v) if not isinstance(v, (int, float, np.integer, np.floating)) else _num(v) for v in index]


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else round(f, 6)


def _y(values) -> list:
    return [_num(v) for v in values]


def trace(s: pd.Series, name: str | None = None, axis: str = "y", dash: bool = False, **extra) -> dict:
    s = s.dropna()
    return {"name": name or str(s.name), "x": _x(s.index), "y": _y(s.to_numpy()), "axis": axis,
            "dash": dash, **extra}


def line(series: dict | pd.DataFrame | pd.Series, title: str, unit: str = "", source: str = "",
         note: str = "", y2: dict | None = None, y2_unit: str = "", events=None, bands=None,
         hbands=None, kind: str = "line", range_buttons: bool = True, **extra) -> dict:
    """Time-series chart from a Series, a DataFrame (one trace per column) or {name: Series}."""
    if isinstance(series, pd.Series):
        series = {series.name or title: series}
    elif isinstance(series, pd.DataFrame):
        series = {c: series[c] for c in series.columns}
    traces = [trace(s, n) for n, s in series.items()]
    traces += [trace(s, n, axis="y2", dash=True) for n, s in (y2 or {}).items()]
    return {"kind": kind, "title": title, "unit": unit, "y2_unit": y2_unit, "source": source, "note": note,
            "traces": traces, "events": event_marks(events), "bands": bands or [], "hbands": hbands or [],
            "range_buttons": range_buttons, **extra}


def bar(values: pd.Series | dict, title: str, unit: str = "", source: str = "", note: str = "",
        horizontal: bool = False, highlight: str | None = None, **extra) -> dict:
    """Categorical bar chart; ``highlight`` colours one category (e.g. India)."""
    if isinstance(values, pd.Series):
        values = {"": values}
    traces = []
    for name, s in values.items():
        t = {"name": name, "x": _x(s.index), "y": _y(s.to_numpy())}
        if highlight is not None:
            t["highlight"] = [str(k) == highlight for k in s.index]
        traces.append(t)
    return {"kind": "hbar" if horizontal else "bar", "title": title, "unit": unit, "source": source,
            "note": note, "traces": traces, **extra}


def stacked(df: pd.DataFrame, title: str, unit: str = "", source: str = "", note: str = "", bars: bool = False,
            **extra) -> dict:
    """Stacked area (or stacked bars) over time - for shares and compositions."""
    return line(df, title, unit, source, note, kind="stackbar" if bars else "area", **extra)


def scatter(x: pd.Series, y: pd.Series, title: str, x_label: str, y_label: str, source: str = "",
            note: str = "", labels: list | None = None, fit: bool = True) -> dict:
    df = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    spec = {"kind": "scatter", "title": title, "x_label": x_label, "unit": y_label, "source": source,
            "note": note, "traces": [{"name": "observations", "x": _y(df["x"]), "y": _y(df["y"]),
                                      "text": labels or [str(i.date()) if hasattr(i, "date") else str(i)
                                                         for i in df.index]}]}
    if fit and len(df) > 3:
        b, a = np.polyfit(df["x"], df["y"], 1)
        xs = np.linspace(df["x"].min(), df["x"].max(), 20)
        r = df["x"].corr(df["y"])
        spec["traces"].append({"name": f"fit: slope {b:.3g}, r = {r:.2f}", "x": _y(xs), "y": _y(a + b * xs),
                               "mode": "lines"})
    return spec


def table(df: pd.DataFrame, title: str, source: str = "", note: str = "", fmt: str = "{:,.2f}") -> dict:
    """HTML table spec. Columns holding only whole numbers (counts) are shown without decimals."""
    whole = {c for c in df.columns
             if pd.api.types.is_numeric_dtype(df[c]) and df[c].dropna().map(lambda v: float(v).is_integer()).all()}

    def cell(v, col=None):
        if isinstance(v, (float, int, np.floating, np.integer)) and not isinstance(v, bool):
            if pd.isna(v):
                return ""
            whole_number = col in whole or (col is None and float(v).is_integer())   # col None = row label
            return f"{int(v):,}" if whole_number else fmt.format(v)
        if isinstance(v, pd.Timestamp):
            return str(v.date())
        return str(v)
    return {"kind": "table", "title": title, "source": source, "note": note,
            "columns": [str(df.index.name or "")] + [str(c) for c in df.columns],
            "rows": [[cell(i)] + [cell(v, c) for v, c in zip(row, df.columns)] for i, row in zip(df.index, df.to_numpy())]}


def event_marks(events) -> list[dict]:
    if events is None or len(events) == 0:
        return []
    return [{"x": str(pd.Timestamp(e.date).date()), "label": e.label, "category": e.category}
            for e in events.itertuples()]


def kpi(label: str, s: pd.Series, unit: str = "", source: str = "", decimals: int = 2,
        spark_points: int = 60, change: str | None = None, hint: str = "") -> dict:
    """A headline tile: latest value, change vs a previous observation, and a sparkline."""
    s = s.dropna()
    last, prev = s.iloc[-1], (s.iloc[-2] if len(s) > 1 else np.nan)
    tile = {"label": label, "value": _num(round(float(last), decimals)), "unit": unit,
            "date": str(s.index[-1].date()) if hasattr(s.index[-1], "date") else str(s.index[-1]),
            "delta": _num(last - prev), "source": source, "hint": hint, "decimals": decimals,
            "spark": {"x": _x(s.index[-spark_points:]), "y": _y(s.iloc[-spark_points:])}}
    if change:
        tile["delta_label"] = change
    return tile


def kpis(tiles: list[dict], title: str = "") -> dict:
    return {"kind": "kpis", "title": title, "tiles": [t for t in tiles if t]}


def error(title: str, exc: Exception) -> dict:
    return {"kind": "error", "title": title, "message": f"{type(exc).__name__}: {exc}"}
