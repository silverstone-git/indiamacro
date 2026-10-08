"""Pages: the oil market (prices, refining, the curve, trade flows)."""

from __future__ import annotations

import pandas as pd

from ..sources import energy
from . import charts as C, data as D, events as E
from .framework import Builder, story

OIL_EVENTS = ["refinery_strike", "reserve_release", "opec", "sanctions", "geopolitical", "demand"]


def _oil_events():
    ev = E.load()
    return ev[ev["category"].isin(OIL_EVENTS)]


@story("oil_prices", "Oil prices", "Energy",
       "What do crude and refined products cost, in dollars and in rupees, and how does today compare with history?",
       method="Daily spot prices are EIA assessments published on FRED (products converted from $/gallon to "
              "$/bbl: x42). Monthly history from the World Bank Pink Sheet; real prices deflated by US CPI.",
       caveats=["EIA's product prices are US (New York Harbor / Gulf Coast). European diesel (ICE gasoil) and "
                "Singapore prices matter more for Russia and India but aren't freely available as long series.",
                "The Indian basket before the current fiscal year is a Brent/Dubai proxy (see Sources)."])
def _(s: Builder):
    def daily():
        p = D.spot()["2019":]
        last = D.spot().dropna(subset=["brent"]).iloc[-1]
        s.insight(f"Dated Brent ${last['brent']:.2f}, WTI ${last['wti']:.2f}, NY Harbor diesel "
                  f"${last['diesel_nyh']:.2f}/bbl on {D.spot()['brent'].dropna().index[-1]:%d %b %Y}.", 10)
        return C.line(p, "Crude and product spot prices, daily", "US$/bbl", "EIA via FRED", events=_oil_events())
    s.chart(daily)

    def long_run():
        ps = D.pink()[["Crude oil, Brent", "Crude oil, Dubai", "Crude oil, WTI"]].dropna(how="all")
        cpi = D.us_cpi().resample("MS").mean()
        deflator = cpi.iloc[-1] / cpi.reindex(ps.index).ffill()
        real = (ps["Crude oil, Brent"] * deflator).rename("Brent, today's dollars")
        peak = real.idxmax()
        s.insight(f"In today's dollars, the monthly Brent peak was ${real.max():.0f} ({peak:%b %Y}); the latest "
                  f"month is ${real.dropna().iloc[-1]:.0f}.", 20)
        return C.line({**{c: ps[c] for c in ps}, "Brent, in today's US$": real}, "Crude oil since 1960, monthly",
                      "US$/bbl", "World Bank Pink Sheet; US CPI (FRED)", events=_oil_events(), log_y=True)
    s.chart(long_run)

    def rupees():
        brent_m = D.spot()["brent"].resample("MS").mean()
        inr = (brent_m * D.usdinr_monthly()).dropna()["2005":]
        return C.line({"Brent in rupees": inr}, "Brent in rupees", "Rs per barrel", "EIA, FRED",
                      note="What Indian refiners pay depends on the dollar price and the exchange rate.")
    s.chart(rupees, "half")

    def basket():
        b = D.basket()
        both = b.dropna()
        if len(both):
            gap = (both["official"] - both["proxy"]).abs().mean()
            s.insight(f"Indian basket (PPAC): ${b['official'].dropna().iloc[-1]:.2f}/bbl in "
                      f"{b['official'].dropna().index[-1]:%b %Y}. The Brent/Dubai proxy is within ${gap:.1f} on "
                      f"average where both exist.", 30)
        return C.line({"Official (PPAC)": b["official"].dropna(), "Proxy (75% Brent / 25% Dubai)": b["proxy"]["2010":]},
                      "Indian crude basket", "US$/bbl", "PPAC; World Bank Pink Sheet")
    s.chart(basket, "half")


@story("refining", "Refining margins and product cracks", "Energy",
       "Is the shock in crude oil, or in the refineries that turn it into diesel, petrol and jet fuel?",
       method="Crack spread = product price minus crude price, both in US$/bbl. The 3-2-1 crack approximates a "
              "US refinery's margin (3 bbl crude -> 2 gasoline + 1 diesel).",
       caveats=["Crack spreads are seasonal (gasoline in summer, diesel in winter); compare with the same month in "
                "past years.",
                "US prices are a proxy for the global product market; regional cracks can diverge."])
def _(s: Builder):
    def daily():
        c = D.cracks()
        d = c["diesel_crack"].dropna()
        base = d["2010":"2019"]
        pct = (base < d.iloc[-1]).mean() * 100
        s.insight(f"The diesel crack is ${d.iloc[-1]:.1f}/bbl ({d.index[-1]:%d %b %Y}), higher than "
                  f"{pct:.0f}% of trading days in 2010-2019 (median ${base.median():.1f}). "
                  + ("That points to a refining/product shortage, not just expensive crude." if pct > 90 else ""), 10)
        return C.line(c["2018":], "Crack spreads, daily", "US$/bbl", "EIA via FRED", events=_oil_events())
    s.chart(daily)

    def by_year():
        c = D.cracks()[["diesel_crack", "gasoline_crack", "jet_crack"]]
        yearly = c.groupby(c.index.year).mean().loc[2006:]
        yearly.index = yearly.index.astype(str)
        return {**C.bar({k: yearly[k] for k in yearly}, "Average crack by year", "US$/bbl", "EIA via FRED"),
                "grouped": True}
    s.chart(by_year, "half")

    def seasonal():
        d = D.cracks()["diesel_crack"].dropna()
        m = d.groupby([d.index.year, d.index.month]).mean().unstack(0)
        hist = m.loc[:, 2010:2019]
        cur = pd.Timestamp.today().year
        out = {"2010-19 range low": hist.min(axis=1), "2010-19 range high": hist.max(axis=1),
               "2010-19 average": hist.mean(axis=1)}
        for y in (cur - 1, cur):
            if y in m:
                out[str(y)] = m[y]
        spec = C.line({k: v.set_axis([f"{i:02d}" for i in v.index]) for k, v in out.items()},
                      "Diesel crack seasonality", "US$/bbl", "EIA via FRED", range_buttons=False,
                      note="Monthly averages; x axis is the calendar month.")
        return spec
    s.chart(seasonal, "half")


@story("curve", "Futures curve and market tightness", "Energy",
       "How scarce are barrels for prompt delivery right now?",
       method="The forward curve is the latest settlement of each listed NYMEX contract. Dated-to-frontline (DFL) "
              "compares the physical Dated Brent assessment with the front-month futures contract.",
       caveats=["NYMEX Brent (BZ) tracks ICE Brent closely but is a different contract.",
                "Contract months that have expired or aren't yet trading are skipped."])
def _(s: Builder):
    def curves():
        out = {}
        for root, name in (("BZ", "Brent"), ("CL", "WTI")):
            c = energy.curve(root, months=24)
            out[name] = pd.Series(c["price"].to_numpy(), index=c["delivery"].dt.strftime("%Y-%m"))
            if root == "BZ" and len(c) > 6:
                m1, m6 = c["price"].iloc[0], c["price"].iloc[min(6, len(c) - 1)]
                shape = "backwardation" if m1 > m6 else "contango"
                s.insight(f"Brent curve: front contract ${m1:.2f}, six months out ${m6:.2f} - "
                          f"{shape} of ${abs(m1 - m6):.2f} ({abs(m1 / m6 - 1) * 100:.1f}%). "
                          + ("Steep backwardation means the market wants oil now: inventories are being drawn."
                             if m1 - m6 > 3 else ""), 10)
        return C.line(out, "Forward curves (latest settlements)", "US$/bbl", "NYMEX via Yahoo Finance",
                      range_buttons=False, note="x axis = delivery month")
    s.chart(curves)

    def dfl():
        d = D.dfl()
        s.insight(f"Dated Brent is ${d.iloc[-1]:+.2f}/bbl vs front-month futures ({d.index[-1]:%d %b %Y}); "
                  f"its 2010-2019 range was ${d['2010':'2019'].quantile(.05):.1f} to "
                  f"${d['2010':'2019'].quantile(.95):.1f} (5th-95th pct).", 20)
        return C.line({"Dated-to-frontline": d["2015":]}, "Physical premium: Dated Brent minus front-month futures",
                      "US$/bbl", "EIA via FRED; NYMEX via Yahoo", events=_oil_events())
    s.chart(dfl)

    s.chart(lambda: C.line(D.futures()[["BZ", "CL"]]["2019":].rename(columns={"BZ": "Brent", "CL": "WTI"}),
                           "Front-month futures", "US$/bbl", "NYMEX via Yahoo Finance"), "half")
    s.chart(lambda: C.line({"Brent - WTI": (D.spot()["brent"] - D.spot()["wti"]).dropna()["2015":]},
                           "Brent-WTI spread", "US$/bbl", "EIA via FRED",
                           note="Widens when the shock is outside the US (seaborne crude) or US supply is plentiful."),
            "half")


@story("flows", "Who exports oil, and to whom", "Energy",
       "Where does the world's oil come from, where does Russia's go, and who supplies India?",
       method="JODI Oil (official monthly submissions), CREA's ship-tracking-based Russia tracker, and UN Comtrade "
              "customs data for India's imports by supplier.",
       caveats=["Russia, Iraq and Iran don't report exports to JODI; use CREA for Russia.",
                "Comtrade free tier: one request per month of data, so the India chart takes ~30 s the first time.",
                "Customs values are reported with a 1-4 month lag."])
def _(s: Builder):
    def exporters():
        df = energy.jodi("TOTEXPSB", "CRUDEOIL", start_year=pd.Timestamp.today().year - 1)
        recent = df[df["date"] >= df["date"].max() - pd.DateOffset(months=2)]
        avg = recent.groupby("country")["value"].mean().sort_values().tail(15)
        return C.bar(avg, "Largest crude exporters reporting to JODI (avg of last 3 months)", "thousand bbl/day",
                     "JODI Oil World Database", horizontal=True,
                     note="Russia, Iraq and Iran are missing because they don't report exports to JODI.")
    s.chart(exporters, "half")

    def trend():
        df = energy.jodi("TOTEXPSB", "CRUDEOIL", countries=["SAU", "USA", "CAN", "ARE", "NOR", "BRA", "KAZ", "KWT"],
                         start_year=2015)
        w = df.pivot_table(index="date", columns="country", values="value")
        return C.line(w, "Crude exports by country", "thousand bbl/day", "JODI Oil World Database",
                      events=_oil_events())
    s.chart(trend, "half")

    def russia():
        df = D.russia_daily()
        w = df.pivot_table(index="date", columns="commodity", values="value_tonne")
        oil = w[[c for c in ("crude_oil", "oil_products", "pipeline_oil") if c in w]].rolling(7).mean() / 1e3
        if "oil_products" in oil:
            r = oil["oil_products"].dropna()
            chg = (r.iloc[-1] / r[: r.index[-1] - pd.DateOffset(days=90)].iloc[-1] - 1) * 100
            s.insight(f"Russian refined-product exports (7-day avg): {r.iloc[-1]:,.0f} kt/day, {chg:+.0f}% vs 90 "
                      f"days earlier. Refinery strikes show up as falling product exports.", 20)
        oil = oil.rename(columns={"crude_oil": "Crude (seaborne)", "oil_products": "Refined products",
                                  "pipeline_oil": "Crude (pipeline)"})
        return C.line(oil, "Russian oil exports by type, 7-day average", "thousand tonnes/day",
                      "CREA Russia Fossil Tracker", events=E.select("refinery_strike"))
    s.chart(russia)

    def destinations():
        df = D.russia_destinations("crude_oil")
        w = df.pivot_table(index="date", columns="destination_country", values="value_tonne").fillna(0) / 1e6
        top = w.sum().sort_values(ascending=False).index[:6]
        w = pd.concat([w[top], w.drop(columns=top).sum(axis=1).rename("Others")], axis=1)
        w = w.iloc[:-1] if w.index[-1].month == pd.Timestamp.today().month else w   # drop partial month
        share = (w.get("India", 0) / w.sum(axis=1)).iloc[-1] * 100
        s.insight(f"India took {share:.0f}% of Russia's seaborne crude exports in {w.index[-1]:%b %Y} (CREA).", 30)
        return C.stacked(w, "Russian crude exports by destination, monthly", "million tonnes",
                         "CREA Russia Fossil Tracker")
    s.chart(destinations, "half")

    def china():
        out = {}
        for prod, name in (("GASDIES", "Diesel/gasoil"), ("GASOLINE", "Gasoline"), ("RESFUEL", "Fuel oil"),
                           ("TOTPRODS", "All products")):
            df = energy.jodi("TOTEXPSB", prod, countries="CHN", start_year=2022)
            out[name] = df.set_index("date")["value"]
        d = out["Diesel/gasoil"]
        zero = d[d.index >= "2025-01-01"]
        if len(zero) and (zero.iloc[-3:] == 0).all():
            s.insight(f"China reported zero diesel exports in the last {int((zero[::-1].cumsum() == 0).sum())} "
                      f"months to {d.index[-1]:%b %Y} (JODI).", 35)
        return C.line(out, "China's refined product exports", "thousand bbl/day", "JODI Oil World Database",
                      note="China sets export quotas; jet fuel is not reported separately.")
    s.chart(china, "half")

    def india_imports():
        df = energy.comtrade("IND", "crude", "M", months=12)
        w = df.pivot_table(index="date", columns="partner", values="value_usd").fillna(0) / 1e9
        top = w.sum().sort_values(ascending=False).index[:7]
        w = pd.concat([w[top], w.drop(columns=top).sum(axis=1).rename("Others")], axis=1)
        if "Russian Federation" in w:
            sh = w["Russian Federation"] / w.sum(axis=1) * 100
            s.insight(f"Russia supplied {sh.iloc[-1]:.0f}% of India's crude import bill in "
                      f"{w.index[-1]:%b %Y} (Comtrade).", 40)
        return C.stacked(w, "India's crude imports by supplier", "US$ bn", "UN Comtrade (HS 2709)", bars=True)
    s.chart(india_imports, "half")


@story("shipping", "Shipping routes and chokepoints", "Energy",
       "Which sea routes are ships still using, and what is the market charging to move oil?",
       method="Daily vessel transits through maritime chokepoints from IMF PortWatch (AIS ship tracking), "
              "compared with each chokepoint's 2025 average. Tanker share prices stand in for freight and "
              "insurance costs, which are not published freely.",
       caveats=["AIS counts miss ships that switch their transponders off, which is common in conflict zones; "
                "counts understate traffic during a crisis, but not by the size of the drops shown here.",
                "War-risk insurance premiums (a % of hull value per transit) appear only in trade press and broker "
                "notes; the Lloyd's Joint War Committee lists high-risk areas but publishes no prices.",
                "Share prices reflect earnings expectations, fleet supply and the stock market as a whole, not "
                "only freight rates."])
def _(s: Builder):
    def change():
        df = D.chokepoints()
        base = df[df["date"].dt.year == 2025].groupby("chokepoint")["n_total"].mean()
        recent = df[df["date"] > df["date"].max() - pd.Timedelta(days=30)].groupby("chokepoint")["n_total"].mean()
        chg = ((recent / base - 1) * 100).dropna().sort_values()
        worst = chg.index[0]
        s.insight(f"{worst}: {recent[worst]:.1f} vessels/day over the last 30 days vs {base[worst]:.1f} in 2025 "
                  f"({chg[worst]:+.0f}%). Data to {df['date'].max():%d %b %Y}.", 10)
        return C.bar(chg, "Transits, last 30 days vs 2025 average", "% change", "IMF PortWatch",
                     horizontal=True, highlight=worst)
    s.chart(change, "half")

    def tankers_now():
        df = D.chokepoints()
        base = df[df["date"].dt.year == 2025].groupby("chokepoint")["n_tanker"].mean()
        recent = df[df["date"] > df["date"].max() - pd.Timedelta(days=30)].groupby("chokepoint")["n_tanker"].mean()
        t = pd.DataFrame({"2025 avg": base, "last 30 days": recent}).dropna().sort_values("2025 avg")
        return {**C.bar({k: t[k] for k in t}, "Tanker transits per day", "tankers/day", "IMF PortWatch",
                        horizontal=True), "grouped": True}
    s.chart(tankers_now, "half")

    def hormuz():
        df = D.chokepoints()
        w = df[df["chokepoint"].isin(["Strait of Hormuz", "Bab el-Mandeb Strait", "Bosporus Strait"])]
        w = w.pivot_table(index="date", columns="chokepoint", values="n_tanker").rolling(7).mean()
        return C.line(w["2024":], "Tanker transits, 7-day average", "tankers/day", "IMF PortWatch",
                      events=E.select("geopolitical"))
    s.chart(hormuz)

    def indexed():
        df = D.chokepoints()
        m = df.pivot_table(index="date", columns="chokepoint", values="n_total").resample("MS").mean()
        idx = (m / m.loc["2025"].mean() * 100)
        keep = ["Strait of Hormuz", "Bab el-Mandeb Strait", "Suez Canal", "Cape of Good Hope", "Bosporus Strait",
                "Malacca Strait", "Panama Canal"]
        return C.line(idx[[k for k in keep if k in idx]]["2023":], "All-vessel transits, monthly (2025 average = 100)",
                      "index", "IMF PortWatch", hbands=[{"y0": 100, "y1": 100, "label": "2025 average"}])
    s.chart(indexed)

    def equities():
        px = D.shipping_equities()
        idx = px / px.loc["2025-01"].mean() * 100
        last = idx.ffill().iloc[-1].sort_values()
        s.insight("Tanker shares vs January 2025: " + ", ".join(f"{k} {v - 100:+.0f}%" for k, v in last.items()
                                                                 if k != "ZIM") + ".", 20)
        return C.line(idx, "Shipping company shares (Jan 2025 = 100)", "index", "Yahoo Finance",
                      note="Tanker owners: INSW, FRO, DHT (crude), STNG, TRMD (products). ZIM = containers.",
                      events=E.select("geopolitical"))
    s.chart(equities)
