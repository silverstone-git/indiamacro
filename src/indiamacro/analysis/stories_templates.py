"""Analysis templates: reusable, parameterised studies of causes (shocks) and trends.

Each template states the question, runs the analysis on live data, reports what it
found in plain language, and lists the method and its caveats - the structure of a
good empirical homework answer.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .. import india
from ..compare import INDICATORS, compare
from ..countries import GROUPS
from ..sources import energy, pwt
from . import charts as C, data as D, events as E
from .framework import Builder, Param, story

CATEGORY_OPTIONS = [("all", "All events")] + list(E.CATEGORIES.items())
WINDOW_PARAMS = [
    Param("pre", "Days before", "number", 10, help="Trading days shown before each event"),
    Param("post", "Days after", "number", 20, help="Trading days tracked after each event"),
    Param("dates", "Extra event dates", "text", "", help="Comma-separated YYYY-MM-DD, e.g. 2025-08-14, 2025-09-12"),
]


def _events(p: dict, default_cat: str):
    dates = [d.strip() for d in str(p.get("dates") or "").split(",") if d.strip()]
    return E.select(p.get("category") or default_cat, dates)


def _study_charts(s: Builder, key: str, ev, pre: int, post: int, order: int, width: str = "half"):
    """Mean path with 95% band + individual paths for one series."""
    label, loader, log, unit = D.LAB_SERIES[key]

    def run():
        return E.event_study(loader(), ev, pre, post, log=log)

    def mean_chart():
        r = run()
        if r["n"] == 0:
            raise ValueError("no events with enough data around them")
        lo, hi = r["ci"]
        m = r["mean"]
        at5 = r["summary"].loc["t+5"] if "t+5" in r["summary"].index else r["summary"].iloc[-1]
        end = r["summary"].iloc[-1]
        u = "%" if log else " $/bbl" if "US$" in unit else ""
        sig = (f"t = {end['t_stat']:.1f}; positive in {end['share_positive'] * 100:.0f}% of events"
               if r["n"] > 1 else "a single event, so no significance test")
        s.insight(f"{label}: average move of {at5['mean']:+.2f}{u} by day +5 and {end['mean']:+.2f}{u} by day "
                  f"+{post} across {r['n']} event{'s' if r['n'] != 1 else ''} ({sig}).", order)
        spec = C.line({"95% band (low)": lo, "95% band (high)": hi, "Average": m},
                      f"{label}: average around events", f"cumulative abnormal change ({'%' if log else unit})",
                      "event study on " + label, range_buttons=False,
                      note=f"Day 0 = event (or next trading day). N = {r['n']}. Constant-mean model, "
                           f"estimation window days -120 to -21.")
        spec["band_pair"] = True        # UI: shade between the first two traces
        spec["vline0"] = True
        return spec

    def paths_chart():
        r = run()
        spec = C.line(r["paths"], f"{label}: each event", f"cumulative abnormal change ({'%' if log else unit})",
                      "event study on " + label, range_buttons=False)
        spec["vline0"] = True
        spec["legend"] = "compact"
        return spec

    s.chart(mean_chart, width)
    s.chart(paths_chart, width)
    return run


# ---------------------------------------------------------------- causes: shocks

@story("tpl_refinery", "Refinery strikes and the product shock", "Shocks",
       "When drones hit refineries (e.g. Ukraine's strikes on Russian plants), do product prices react more than "
       "crude - and does Russia export less fuel?",
       params=[Param("category", "Events", "select", "refinery_strike", CATEGORY_OPTIONS)] + WINDOW_PARAMS,
       method="Event study. For each event, daily changes are compared with their average over days -120 to -21 "
              "(constant-mean model) and cumulated. Prices use % changes; crack spreads use $/bbl changes. If the "
              "diesel crack rises while crude barely moves, the shock is to refining capacity, not to crude supply. "
              "CREA ship-tracking data then shows whether Russian product exports actually fell.",
       caveats=["Small samples: a handful of events means wide confidence bands - report them.",
                "Other news lands on the same days (OPEC meetings, US inventory reports, sanctions); check each "
                "event's path in the 'each event' chart, and consider dropping contaminated ones.",
                "US diesel prices proxy for the European market where Russian diesel used to go; the effect on "
                "ICE gasoil is likely larger.",
                "Strikes often cause outages of days to weeks; markets may also anticipate a campaign of strikes, "
                "so later events in a wave can show smaller surprises.",
                "Add recent strikes in the Events page or the 'Extra event dates' box - the built-in list covers "
                "only well-documented 2019-2024 events."], kind="template")
def _(s: Builder):
    ev = _events(s.p, "refinery_strike")
    pre, post = s.p["pre"], s.p["post"]
    s.text(f"**{len(ev)} events selected.** " + "; ".join(f"{d:%d %b %Y}: {l}" for d, l in
                                                         zip(ev["date"], ev["label"])))
    _study_charts(s, "diesel_crack", ev, pre, post, 10)
    _study_charts(s, "brent", ev, pre, post, 20)
    _study_charts(s, "gasoline_crack", ev, pre, post, 30)

    def table():
        rows = {}
        for key in ("brent", "diesel_nyh", "diesel_crack", "gasoline_crack", "jet_crack", "dfl"):
            label, loader, log, unit = D.LAB_SERIES[key]
            r = E.event_study(loader(), ev, pre, post, log=log)
            if r["n"]:
                summ = r["summary"]
                rows[label] = {f"{h} mean": summ.loc[h, "mean"] for h in summ.index} | \
                              {"t-stat (end)": summ.iloc[-1]["t_stat"], "N": r["n"]}
        df = pd.DataFrame(rows).T
        df.index.name = "series"
        return C.table(df, "Cumulative abnormal change by horizon",
                       note="% for prices; US$/bbl for cracks and spreads.", source="event study")
    s.chart(table)

    def russia():
        df = D.russia_daily()
        w = df.pivot_table(index="date", columns="commodity", values="value_tonne")
        cols = [c for c in ("crude_oil", "oil_products") if c in w]
        nice = {"crude_oil": "Crude (seaborne)", "oil_products": "Refined products"}
        return C.line((w[cols].rolling(7).mean() / 1e3).rename(columns=nice), "Russian seaborne exports, 7-day average",
                      "thousand tonnes/day", "CREA Russia Fossil Tracker", events=ev)
    s.chart(russia, "half")
    s.chart(lambda: C.line(D.cracks()[["diesel_crack", "gasoline_crack"]]["2022":], "Crack spreads with events",
                           "US$/bbl", "EIA via FRED", events=ev), "half")


@story("tpl_reserves", "Strategic reserve releases", "Shocks",
       "Do coordinated reserve releases (US SPR, IEA, China's state reserves) actually lower prices - and for how long?",
       params=[Param("category", "Events", "select", "reserve_release", CATEGORY_OPTIONS),
               Param("pre", "Days before", "number", 10), Param("post", "Days after", "number", 30),
               Param("dates", "Extra event dates", "text", "")],
       method="Event study on Brent (%), the physical premium (Dated Brent minus front-month futures) and the "
              "Brent-WTI spread. A release that eases physical scarcity should narrow the physical premium; a US "
              "release should weaken WTI relative to Brent. China's stock changes come from JODI (total crude "
              "stocks; China does not publish its strategic reserve separately).",
       caveats=["Releases are usually leaked or discussed for days before the announcement, so part of the effect "
                "happens before day 0 - look at the pre-event path.",
                "Announced volumes are often bigger than what is actually delivered.",
                "Releases happen *because* prices are rising; a smaller-than-expected release can be followed by "
                "higher prices. This is a correlation, not a clean causal estimate.",
                "China's announcements are rare; its stock draws show up only in monthly data."], kind="template")
def _(s: Builder):
    ev = _events(s.p, "reserve_release")
    pre, post = s.p["pre"], s.p["post"]
    s.text(f"**{len(ev)} events selected.** " + "; ".join(f"{d:%d %b %Y}: {l}" for d, l in
                                                         zip(ev["date"], ev["label"])))
    _study_charts(s, "brent", ev, pre, post, 10)
    _study_charts(s, "dfl", ev, pre, post, 20)
    _study_charts(s, "brent_wti", ev, pre, post, 30)

    def china():
        out = {}
        for flow, name in (("STOCKCH", "Stock change"), ("TOTIMPSB", "Imports")):
            df = energy.jodi(flow, "CRUDEOIL", countries="CHN", start_year=2018)
            out[name] = df.set_index("date")["value"]
        return C.line(out, "China: crude imports and stock change", "thousand bbl/day", "JODI Oil World Database",
                      note="Negative stock change = draw on inventories (commercial + strategic).", events=ev)
    s.chart(china)


@story("tpl_oil_india", "Oil shock pass-through to India", "Shocks",
       "When oil prices jump, how much and how quickly does it reach Indian inflation and the rupee?",
       params=[Param("start", "From year", "number", 2014), Param("max_lag", "Max lag (months)", "number", 12)],
       method="Monthly Brent in rupees (dollar price x exchange rate), year-on-year change, correlated with "
              "CPI fuel & light inflation, WPI inflation and headline CPI at lags of 0 to N months. The lag with "
              "the highest correlation is a rough guide to the pass-through delay. The scatter shows how the rupee "
              "moves with oil month to month.",
       caveats=["Correlation is not pass-through: a proper estimate regresses inflation on lagged oil changes with "
                "controls (e.g. a distributed-lag model or VAR).",
                "India's retail petrol and diesel prices are partly administered (excise changes, oil-company "
                "pricing), which can hold pass-through to CPI near zero for long stretches; WPI reacts faster.",
                "CPI fuel & light covers cooking gas, kerosene and electricity - not petrol/diesel, which sit in "
                "transport. Base 2024 CPI changes weights."], kind="template")
def _(s: Builder):
    start, max_lag = str(s.p["start"]), s.p["max_lag"]

    def build():
        brent_inr = (D.spot()["brent"].resample("MS").mean() * D.usdinr_monthly()).dropna()
        oil_yoy = (brent_inr.pct_change(12, fill_method=None) * 100).dropna()
        targets = {"WPI inflation": D.wpi_infl(), "CPI fuel & light": D.cpi_subgroup("Fuel and Light-Overall"),
                   "CPI headline": india.cpi_inflation()}
        return oil_yoy, targets

    def levels():
        oil_yoy, targets = build()
        return C.line({"Brent in rupees (% y/y)": oil_yoy[start:]}, "Oil in rupees vs Indian inflation",
                      "% y/y (Brent)", "EIA, FRED, MoSPI", y2={k: v[start:] for k, v in targets.items()},
                      y2_unit="% y/y (inflation)")
    s.chart(levels)

    def lags():
        oil_yoy, targets = build()
        out = {}
        for name, t in targets.items():
            corr = pd.Series({k: oil_yoy.shift(k).corr(t[start:]) for k in range(0, max_lag + 1)})
            out[name] = corr
            k = int(corr.idxmax())
            s.insight(f"{name}: correlation with Brent-in-rupees peaks at a lag of {k} month(s) "
                      f"(r = {corr.max():.2f}).", 10 + len(out))
        df = pd.DataFrame(out)
        df.index = [f"{i}" for i in df.index]
        return {**C.bar({k: df[k] for k in df}, "Correlation with oil price change, by lag",
                        "correlation coefficient", "own calculation", note="x axis = months that oil leads by"),
                "grouped": True}
    s.chart(lags, "half")

    def rupee():
        brent = D.spot()["brent"].resample("MS").mean()
        x = (np.log(brent).diff() * 100)[start:]
        y = (np.log(D.usdinr_monthly()).diff() * 100)[start:]
        return C.scatter(x, y, "Oil and the rupee, monthly % changes", "Brent, % change",
                         "INR per US$, % change (up = weaker rupee)", "EIA, FRED")
    s.chart(rupee, "half")


@story("tpl_event_lab", "Event study lab", "Shocks",
       "Pick any market series and any set of events: what happened on average around them?",
       params=[Param("series", "Series", "select", "brent", [(k, v[0]) for k, v in D.LAB_SERIES.items()]),
               Param("category", "Events", "select", "geopolitical", CATEGORY_OPTIONS)] + WINDOW_PARAMS,
       method="Constant-mean-model event study: abnormal change = daily change minus its average over days -120 "
              "to -21, cumulated from the start of the window and set to zero on day -1. The t-statistic is the "
              "mean across events divided by its standard error.",
       caveats=["With few events, a single outlier can drive the average - check the per-event chart.",
                "Event dates are announcement or news dates; if news broke after market close, the reaction "
                "appears on day +1."], kind="template")
def _(s: Builder):
    ev = _events(s.p, "geopolitical")
    s.text(f"**{len(ev)} events.** " + "; ".join(f"{d:%d %b %Y}: {l}" for d, l in zip(ev["date"], ev["label"])))
    _study_charts(s, s.p["series"], ev, s.p["pre"], s.p["post"], 10)

    def table():
        label, loader, log, unit = D.LAB_SERIES[s.p["series"]]
        r = E.event_study(loader(), ev, s.p["pre"], s.p["post"], log=log)
        t = r["table"].copy()
        t.index.name = "event"
        return C.table(t, f"{label}: cumulative abnormal change per event", source="event study")
    s.chart(table)


# ---------------------------------------------------------------- trends

@story("tpl_growth_accounting", "Catch-up growth and growth accounting", "Trends",
       "Is a country catching up with the US, and is its growth coming from capital, education or productivity?",
       params=[Param("country", "Country", "select", "IND",
                     [(c, c) for c in ["IND", "CHN", "IDN", "VNM", "KOR", "BRA", "BGD", "THA", "MYS", "PHL", "ZAF"]]),
               Param("peers", "Compare with", "text", "CHN, IDN, KOR, VNM")],
       method="Penn World Table 11.0. Output per worker growth is split as "
              "g(Y/L) = a*g(K/L) + (1-a)*g(h) + g(TFP), where a = 1 - labour share, K = capital stock and h = human "
              "capital (schooling-based index). TFP is the residual. Real series at constant national prices "
              "(rgdpna, rnna) for growth; PPP output (rgdpo) for levels across countries.",
       caveats=["TFP is a residual: it absorbs measurement error in capital, labour quality and utilisation.",
                "Labour share (labsh) in countries with many self-employed workers depends on imputation choices.",
                "Employment counts matter: PWT's India employment rises sharply after 2018 with the PLFS, so "
                "per-worker measures fall even while GDP per person rises.",
                "PWT 11.0 ends in 2023."], kind="template")
def _(s: Builder):
    c = s.p["country"]
    peers = [p.strip().upper() for p in s.p["peers"].split(",") if p.strip()]

    def relative():
        df = pwt.get(["rgdpo", "pop"], list(dict.fromkeys([c, *peers, "USA"])))
        w = df.pivot_table(index="date", columns=["series", "country"], values="value")
        pc = w["rgdpo"] / w["pop"]
        rel = pc.div(pc["USA"], axis=0).drop(columns="USA") * 100
        r = rel[c].dropna()
        s.insight(f"{c}'s GDP per person was {r.iloc[-1]:.1f}% of the US level in {r.index[-1].year} "
                  f"(PPP), up from {r['1990'].iloc[0]:.1f}% in 1990.", 10)
        return C.line(rel["1960":], "GDP per person relative to the US (PPP)", "US = 100", "Penn World Table 11.0")
    s.chart(relative)

    def decomposition():
        df = pwt.get(["rgdpna", "rnna", "emp", "hc", "labsh"], c)
        w = df.pivot_table(index="date", columns="series", values="value").dropna()
        a = 1 - w["labsh"].mean()
        g = np.log(w[["rgdpna", "rnna", "hc"]].div(w["emp"], axis=0).assign(hc=w["hc"])).diff() * 100
        comp = pd.DataFrame({"Capital deepening": a * g["rnna"], "Human capital": (1 - a) * g["hc"]})
        comp["TFP"] = g["rgdpna"] - comp.sum(axis=1)
        comp["Output per worker"] = g["rgdpna"]
        comp = comp.dropna()
        decade = comp.groupby((comp.index.year // 10) * 10).mean()
        decade.index = [f"{d}s" for d in decade.index]
        last = decade.iloc[-1]
        emp_growth = (w["emp"].iloc[-1] / w["emp"].iloc[-6]) ** (1 / 5) * 100 - 100
        if emp_growth > 3:
            s.insight(f"Warning: measured employment grew {emp_growth:.1f}%/yr over the last five years in PWT, far "
                      f"faster than population, which drags down output per worker and the TFP residual. For "
                      f"India this reflects PLFS counting many more (largely self-employed and unpaid family) "
                      f"workers; compare with output per person before drawing conclusions.", 15)
        s.insight(f"{c}, {decade.index[-1]}: output per worker grew {last['Output per worker']:.1f}%/yr - capital "
                  f"{last['Capital deepening']:.1f}pp, human capital {last['Human capital']:.1f}pp, TFP "
                  f"{last['TFP']:.1f}pp (capital share a = {a:.2f}).", 20)
        spec = C.bar({k: decade[k] for k in ("Capital deepening", "Human capital", "TFP")},
                     f"{c}: sources of growth in output per worker, by decade", "% per year (contribution)",
                     "Penn World Table 11.0; own calculation")
        spec["stacked"] = True
        spec["overlay_line"] = {"name": "Output per worker", "x": list(decade.index),
                                "y": [round(v, 3) for v in decade["Output per worker"]]}
        return spec
    s.chart(decomposition, "half")

    def hc_tfp():
        df = pwt.get(["hc"], list(dict.fromkeys([c, *peers])))
        return C.line(df.pivot_table(index="date", columns="country", values="value"), "Human capital index",
                      "index (years of schooling + returns)", "Penn World Table 11.0")
    s.chart(hc_tfp, "half")


@story("tpl_inflation_regime", "Inflation regimes and policy credibility", "Trends",
       "Did adopting inflation targeting change the level and volatility of inflation?",
       params=[Param("break_date", "Regime change", "text", "2016-08-05",
                     help="Date the new regime started (default: India's inflation-targeting framework)"),
               Param("window", "Rolling window (months)", "number", 24)],
       method="Compares mean, volatility and persistence (first-order autocorrelation) of monthly CPI inflation "
              "before and after a break date, with rolling statistics to show how gradual the change was.",
       caveats=["Before-after comparisons can't separate the policy from everything else that changed (oil prices, "
                "food supply, COVID). A stronger design compares with similar countries (difference-in-differences) "
                "or tests for a structural break.",
                "MoSPI's CPI series starts in 2013 (2012 base), so the 'before' period is short."], kind="template")
def _(s: Builder):
    brk, win = pd.Timestamp(s.p["break_date"]), s.p["window"]

    def stats():
        cpi = india.cpi_inflation()
        pre, post = cpi[:brk - pd.Timedelta(days=1)], cpi[brk:]
        def st(x):
            return {"mean": x.mean(), "std dev": x.std(), "persistence (AR1)": x.autocorr(1),
                    "share in 2-6% band": ((x >= 2) & (x <= 6)).mean() * 100, "months": len(x)}
        df = pd.DataFrame({"before": st(pre), "after": st(post)})
        df.index.name = "statistic"
        s.insight(f"Inflation averaged {pre.mean():.1f}% (sd {pre.std():.1f}) before {brk:%b %Y} and "
                  f"{post.mean():.1f}% (sd {post.std():.1f}) after.", 10)
        return C.table(df, "CPI inflation before and after", source="MoSPI CPI; own calculation")
    s.chart(stats, "half")

    def rolling():
        cpi = india.cpi_inflation()
        return C.line({"Rolling mean": cpi.rolling(win).mean(), "Rolling std dev": cpi.rolling(win).std()},
                      f"{win}-month rolling mean and volatility of CPI inflation", "%", "MoSPI CPI",
                      bands=[{"x0": str(brk.date()), "x1": str(pd.Timestamp.today().date()), "label": "new regime"}])
    s.chart(rolling, "half")

    def peers():
        t = compare("inflation", "EM_ASIA", start=2005)
        return C.line(t, "Inflation in emerging Asia (IMF WEO)", "% y/y", "IMF WEO",
                      bands=[{"x0": str(brk.date()), "x1": str(pd.Timestamp.today().date()), "label": "India's new regime"}])
    s.chart(peers)


@story("tpl_convergence_compare", "Compare countries", "Trends",
       "How does India compare with any group of countries on any headline indicator?",
       params=[Param("indicator", "Indicator", "select", "gdp_growth",
                     [(k, k.replace("_", " ")) for k in INDICATORS]),
               Param("group", "Countries", "select", "BRICS", [(g, g.replace("_", " ")) for g in GROUPS]),
               Param("start", "From year", "number", 2000)],
       method="IMF World Economic Outlook where available (includes projections), otherwise World Bank WDI.",
       caveats=["IMF and World Bank definitions differ slightly; don't mix sources within a comparison."],
       kind="template")
def _(s: Builder):
    def chart():
        t = compare(s.p["indicator"], s.p["group"], start=s.p["start"])
        return C.line(t, f"{s.p['indicator'].replace('_', ' ')}: {s.p['group']}", "", t.attrs.get("source", "").upper()
                      + f" ({t.attrs.get('code')})")
    s.chart(chart)

    def latest():
        t = compare(s.p["indicator"], s.p["group"], start=s.p["start"])
        year = min(pd.Timestamp.today().year - 1, t.index.max().year)
        row = t.loc[:str(year)].ffill().iloc[-1].dropna().sort_values()
        rank = list(row.index[::-1]).index("IND") + 1 if "IND" in row else None
        if rank:
            s.insight(f"India ranks {rank} of {len(row)} in {s.p['group']} on {s.p['indicator'].replace('_', ' ')} "
                      f"({year}): {row['IND']:.2f}.", 10)
        return C.bar(row, f"Latest ({year})", "", t.attrs.get("source", "").upper(), horizontal=True, highlight="IND")
    s.chart(latest, "half")

    def avg():
        t = compare(s.p["indicator"], s.p["group"], start=s.p["start"])
        t = t.loc[:str(pd.Timestamp.today().year - 1)]
        return C.bar(t.mean().sort_values(), f"Average since {s.p['start']}", "",
                     t.attrs.get("source", "").upper(), horizontal=True, highlight="IND")
    s.chart(avg, "half")
