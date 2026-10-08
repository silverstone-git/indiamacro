"""Pages: overview and the India sections."""

from __future__ import annotations

import pandas as pd

from .. import india
from ..compare import INDICATORS, compare
from ..sources import bis, mospi, oecd, worldbank
from . import charts as C, data as D, events as E
from .framework import Builder, Param, story

FIT_START = "2016-08-05"   # flexible inflation targeting notified


def _weo_split(code: str, country: str = "IND") -> tuple[pd.Series, pd.Series]:
    """IMF WEO series split into actuals and projections (the projection line starts at the last actual)."""
    df = D.weo(code, (country,)).set_index("date")
    is_proj = df["projection"].map(lambda v: v is True)   # NA (unknown) counts as actual
    act, proj = df.loc[~is_proj, "value"], df.loc[is_proj, "value"]
    if len(act) and len(proj):
        proj = pd.concat([act.iloc[-1:], proj])
    return act, proj


# ---------------------------------------------------------------- overview

@story("overview", "India at a glance", "Overview",
       "Where is the Indian economy right now, and what is the oil market doing to it?")
def _(s: Builder):
    def tiles():
        t = []
        def add(label, fn, unit, source, decimals=2, hint=""):
            try:
                t.append(C.kpi(label, fn(), unit, source, decimals, hint=hint))
            except Exception as e:
                t.append({"label": label, "error": str(e)[:120]})
        add("Real GDP growth", lambda: _weo_split("NGDP_RPCH")[0], "% y/y", "IMF WEO", 1,
            "latest actual fiscal year")
        add("CPI inflation", india.cpi_inflation, "% y/y", "MoSPI", 2)
        add("WPI inflation", D.wpi_infl, "% y/y", "MoSPI/OEA", 2)
        add("Industrial production", india.iip_growth, "% y/y", "MoSPI IIP", 1)
        add("Unemployment", india.unemployment, "%", "MoSPI PLFS", 1, "monthly, 15+, CWS")
        add("Repo rate", D.repo_monthly, "%", "RBI via BIS", 2)
        add("Rupees per US$", D.usdinr_daily, "INR", "FRED", 2)
        add("Forex reserves", lambda: india.forex_reserves() / 1000, "US$ bn", "RBI via MoSPI", 0)
        add("Brent (dated)", lambda: D.spot()["brent"], "US$/bbl", "EIA via FRED", 2)
        add("Indian crude basket", lambda: D.basket()["official"].dropna(), "US$/bbl", "PPAC", 2, "monthly average")
        add("Diesel crack", lambda: D.cracks()["diesel_crack"], "US$/bbl", "EIA via FRED", 1,
            "NY Harbor ULSD minus Brent")
        add("Dated-to-frontline", D.dfl, "US$/bbl", "EIA, NYMEX", 1, "physical tightness")
        return C.kpis(t)
    s.chart(tiles)

    def cpi_repo():
        cpi, repo = india.cpi_inflation(), D.repo_monthly()["2013":]
        return C.line({"CPI inflation": cpi, "Repo rate": repo}, "Inflation and the policy rate", "%",
                      "MoSPI; RBI via BIS", hbands=[{"y0": 2, "y1": 6, "label": "target band"}],
                      events=E.select("india_policy"))
    s.chart(cpi_repo, "half")

    def growth():
        act, proj = _weo_split("NGDP_RPCH")
        spec = C.line({"India (actual)": act["2000":]}, "Real GDP growth", "% y/y", "IMF World Economic Outlook",
                      note="Dashed = IMF projection. Years are Indian fiscal years (2024 = FY 2024-25).")
        spec["traces"].append(C.trace(proj, "India (IMF projection)", dash=True))
        return spec
    s.chart(growth, "half")

    def oil():
        b = D.basket()
        brent_m = D.spot()["brent"].resample("MS").mean()
        return C.line({"Indian basket (official)": b["official"].dropna(), "Indian basket (proxy)": b["proxy"]["2015":],
                       "Brent (monthly avg)": brent_m["2015":]}, "Crude oil India pays", "US$/bbl",
                      "PPAC; World Bank Pink Sheet; EIA via FRED")
    s.chart(oil, "half")

    def rupee():
        return C.line({"INR per USD": D.usdinr_daily()["2010":]}, "The rupee", "INR per US$", "FRED (Fed H.10)",
                      events=E.select("geopolitical"))
    s.chart(rupee, "half")


# ---------------------------------------------------------------- growth

@story("india_growth", "Growth and the business cycle", "India",
       "How fast is India growing, how does it compare, and which way is the cycle turning?",
       method="Annual growth from IMF WEO (with projections) and MoSPI national accounts; "
              "high-frequency momentum from industrial production and the OECD composite leading indicator.",
       caveats=["GDP was rebased to 2022-23 in 2026; the quarterly MoSPI series below are shown separately by base "
                "year because levels are not comparable across bases.",
                "IMF years for India are fiscal years (2024 = April 2024-March 2025)."])
def _(s: Builder):
    def imf_growth():
        act, proj = _weo_split("NGDP_RPCH")
        avg = {f"{d}s": act[str(d):str(d + 9)].mean() for d in (1980, 1990, 2000, 2010, 2020)}
        s.insight("Average real growth by decade (IMF): " + ", ".join(f"{k} {v:.1f}%" for k, v in avg.items()
                                                                     if pd.notna(v)) + ".", 10)
        spec = C.line({"Actual": act}, "India real GDP growth, 1980-", "% y/y", "IMF World Economic Outlook",
                      note="Dashed = IMF projection", kind="bar")
        spec["traces"].append(C.trace(proj.iloc[1:], "IMF projection", dash=True))
        return spec
    s.chart(imf_growth)

    s.chart(lambda: C.line(compare("gdp_growth", "BRICS", start=2000), "India vs BRICS",
                           "% y/y", "IMF WEO", note="Includes IMF projections for recent/future years."), "half")
    s.chart(lambda: C.line(compare("gdp_growth", "EM_ASIA", start=2000), "India vs emerging Asia",
                           "% y/y", "IMF WEO"), "half")

    def quarterly():
        df = mospi.nas(5, freq="Q")
        out = {}
        for base, g in df.groupby("base_year"):
            q = g.drop_duplicates("date", keep="last").set_index("date")["constant_price"].sort_index()
            out[f"base {base}"] = (q.pct_change(4, fill_method=None) * 100).dropna()
        last_key = max(out)
        if len(out[last_key]):
            s.insight(f"Latest quarterly real GDP growth ({out[last_key].index[-1]:%b %Y} quarter, {last_key}): "
                      f"{out[last_key].iloc[-1]:.1f}% y/y.", 20)
        return C.line(out, "Quarterly real GDP growth (MoSPI)", "% y/y", "MoSPI National Accounts",
                      note="Dates are the start of each fiscal quarter (Q1 = Apr-Jun).")
    s.chart(quarterly, "half")

    s.chart(lambda: C.line({"IIP growth": india.iip_growth()}, "Industrial production (IIP)", "% y/y",
                           "MoSPI", hbands=[{"y0": 0, "y1": 0, "label": ""}]), "half")

    def cli():
        df = oecd.cli(["IND", "CHN", "USA"], start="2010-01")
        w = df.pivot_table(index="date", columns="country", values="value")
        ind = w["IND"].dropna()
        direction = "rising" if ind.iloc[-1] > ind.iloc[-4] else "falling"
        s.insight(f"OECD leading indicator for India: {ind.iloc[-1]:.1f} ({ind.index[-1]:%b %Y}), {direction} over 3 "
                  f"months - {'above' if ind.iloc[-1] > 100 else 'below'} its long-run trend (100).", 30)
        return C.line(w, "Composite leading indicators (100 = trend)", "index", "OECD",
                      hbands=[{"y0": 100, "y1": 100, "label": "trend"}])
    s.chart(cli)


# ---------------------------------------------------------------- inflation and policy

@story("india_inflation", "Inflation and monetary policy", "India",
       "Has inflation targeting worked, and how tight is monetary policy?",
       method="CPI (base 2012) from MoSPI; repo rate from the BIS policy-rate database. The real policy rate is "
              "the repo rate minus current CPI inflation (an ex-post measure; forward-looking studies use expected "
              "inflation).",
       caveats=["CPI base 2024 was introduced in 2026 and is not yet in the MoSPI API; the 2012-base series ends "
                "where the API stops.",
                "Food has a ~46% weight in CPI (2012 base), so supply shocks to vegetables and pulses dominate "
                "headline swings; core inflation is a better gauge of demand pressure."])
def _(s: Builder):
    def main():
        cpi, food, repo = india.cpi_inflation(), india.cpi_food_inflation(), D.repo_monthly()["2013":]
        pre, post = cpi[:FIT_START], cpi[FIT_START:]
        inband = lambda x: ((x >= 2) & (x <= 6)).mean() * 100
        s.insight(f"Average CPI inflation: {pre.mean():.1f}% before inflation targeting (2013 to Jul 2016) vs "
                  f"{post.mean():.1f}% since; inside the 2-6% band {inband(pre):.0f}% vs {inband(post):.0f}% of months.", 10)
        return C.line({"CPI headline": cpi, "CPI food": food, "Repo rate": repo},
                      "CPI inflation, food inflation and the repo rate", "%", "MoSPI; RBI via BIS",
                      hbands=[{"y0": 2, "y1": 6, "label": "2-6% band"}],
                      events=E.select("india_policy"))
    s.chart(main)

    def real_rate():
        cpi, repo = india.cpi_inflation(), D.repo_monthly()
        real = (repo.reindex(cpi.index) - cpi).dropna()
        s.insight(f"Real repo rate (repo minus CPI): {real.iloc[-1]:.1f}% in {real.index[-1]:%b %Y}; "
                  f"average since 2013 {real.mean():.1f}%.", 20)
        return C.line({"Real repo rate": real}, "Real policy rate (repo - CPI inflation)", "%", "MoSPI; BIS",
                      hbands=[{"y0": 0, "y1": 0, "label": ""}], kind="bar")
    s.chart(real_rate, "half")

    s.chart(lambda: C.line({"WPI": D.wpi_infl(), "CPI": india.cpi_inflation()}, "Wholesale vs consumer inflation",
                           "% y/y", "MoSPI/Office of Economic Adviser",
                           note="WPI is heavy in fuel and manufactured goods; it moves first when oil moves."), "half")

    def groups():
        df = D.cpi_all()
        latest = df["date"].max()
        g = df[(df["date"] == latest) & df["subgroup"].str.endswith("-Overall")]
        ser = g.set_index("subgroup")["inflation"].sort_values()
        ser.index = ser.index.str.replace("-Overall", "")
        return C.bar(ser, f"Inflation by CPI group, {latest:%b %Y}", "% y/y", "MoSPI", horizontal=True,
                     highlight="General")
    s.chart(groups)


# ---------------------------------------------------------------- labour

@story("india_labour", "Jobs and labour force", "India",
       "How many Indians are working or looking for work?",
       method="Periodic Labour Force Survey (PLFS) by MoSPI. Monthly estimates exist from 2025; annual estimates "
              "from 2017-18. CWS = current weekly status (activity in the past week).",
       caveats=["Unemployment in India is low partly because most workers are self-employed or casual; "
                "under-employment and labour-force participation tell more of the story.",
                "World Bank figures are ILO modelled estimates and can differ from PLFS."])
def _(s: Builder):
    def monthly():
        u = india.unemployment()
        s.insight(f"Unemployment (persons 15+, CWS): {u.iloc[-1]:.1f}% in {u.index[-1]:%b %Y}.", 10)
        return C.line({"Unemployment rate": u}, "Unemployment rate, monthly (PLFS)", "%", "MoSPI PLFS")
    s.chart(monthly, "half")

    def annual():
        out = {}
        for code, name in ((1, "Labour force participation"), (2, "Worker population ratio")):
            df = mospi.plfs(code, freq="A")
            if "weekly_status" in df:
                cws = df[df["weekly_status"].astype(str).str.upper() == "CWS"]
                df = cws if not cws.empty else df
            out[name] = df.drop_duplicates("date", keep="last").set_index("date")["value"]
        return C.line(out, "Participation and employment, annual (PLFS)", "% of population 15+", "MoSPI PLFS",
                      note="Fiscal years (date = start of year).")
    s.chart(annual, "half")

    def female():
        t = compare("female_lfpr", "SOUTH_ASIA", start=1995)
        latest = t.ffill().iloc[-1].sort_values()
        s.insight(f"Female labour force participation in India: {latest['IND']:.1f}% (World Bank/ILO), "
                  f"vs {latest.drop('IND').median():.1f}% median in South Asia.", 20)
        return C.line(t, "Female labour force participation, South Asia", "% of females 15+", "World Bank (ILO estimates)")
    s.chart(female)


# ---------------------------------------------------------------- external sector

@story("india_external", "External sector and the rupee", "India",
       "How exposed is India to external shocks, and how big is the buffer?",
       method="Reserves from RBI tables (via MoSPI), exchange rates from the Fed (FRED) and BIS, current account "
              "from IMF WEO.",
       caveats=["A falling REER means the rupee is getting more competitive (cheaper), not necessarily weaker "
                "against the dollar.",
                "MoSPI's copy of the RBI reserves table can lag RBI's weekly statistical supplement."])
def _(s: Builder):
    def reserves():
        r = india.forex_reserves() / 1000
        s.insight(f"Forex reserves: US${r.iloc[-1]:,.0f} bn ({r.index[-1]:%b %Y}).", 10)
        return C.line({"Forex reserves": r}, "Foreign exchange reserves", "US$ bn", "RBI via MoSPI eSankhyiki")
    s.chart(reserves, "half")

    s.chart(lambda: C.line({"REER (broad)": india.reer()}, "Real effective exchange rate", "index, 2020 = 100",
                           "BIS", note="Up = rupee appreciation against a trade-weighted basket, adjusted for inflation."),
            "half")

    def rupee():
        r = D.usdinr_daily()
        yoy = (r.iloc[-1] / r[: r.index[-1] - pd.DateOffset(years=1)].iloc[-1] - 1) * 100
        s.insight(f"Rupee: {r.iloc[-1]:.2f} per US$ on {r.index[-1]:%d %b %Y}, "
                  f"{'depreciated' if yoy > 0 else 'appreciated'} {abs(yoy):.1f}% over a year.", 20)
        return C.line({"INR per US$": r["2000":]}, "Rupee vs US dollar", "INR per US$", "FRED (Fed H.10)",
                      events=E.select().query("category in ['geopolitical','india_policy','sanctions']"))
    s.chart(rupee)

    def ca():
        act, proj = _weo_split("BCA_NGDPD")
        spec = C.line({"Actual": act["1990":]}, "Current account balance", "% of GDP", "IMF WEO", kind="bar",
                      note="Dashed = IMF projection")
        spec["traces"].append(C.trace(proj.iloc[1:], "IMF projection", dash=True))
        return spec
    s.chart(ca, "half")

    def credit():
        df = bis.credit_gap(["IND", "CHN", "USA"], start="2000")
        return C.line(df.pivot_table(index="date", columns="country", values="value"), "Credit-to-GDP gap",
                      "percentage points", "BIS", note="Above +2pp has historically flagged elevated banking-crisis risk "
                                                         "(Basel III countercyclical buffer guide).",
                      hbands=[{"y0": 2, "y1": 10, "label": "warning zone"}])
    s.chart(credit, "half")


# ---------------------------------------------------------------- fiscal and structure

@story("india_fiscal", "Public finances", "India",
       "How large are India's deficits and debt, and how do they compare?",
       method="General government (centre + states) figures from IMF WEO, comparable across countries.",
       caveats=["The Union Budget reports the central government only; general government adds the states, so "
                "deficits and debt are much larger than the headline 'fiscal deficit' in the Budget speech."])
def _(s: Builder):
    for code, title in (("GGXWDG_NGDP", "General government gross debt"),
                        ("GGXCNL_NGDP", "General government net lending (+) / borrowing (-)")):
        def chart(code=code, title=title):
            act, proj = _weo_split(code)
            s.insight(f"{title}: {act.iloc[-1]:.1f}% of GDP in {act.index[-1].year} (latest actual); IMF projects "
                      f"{proj.iloc[-1]:.1f}% by {proj.index[-1].year}.", 10 if code.startswith("GGXW") else 20)
            spec = C.line({"India": act["1995":]}, title, "% of GDP", "IMF WEO", note="Dashed = IMF projection")
            spec["traces"].append(C.trace(proj, "IMF projection", dash=True))
            return spec
        s.chart(chart, "half")

    for ind, title in (("govt_debt", "Government debt, G20, latest"), ("fiscal_balance", "Fiscal balance, G20, latest")):
        def chart(ind=ind, title=title):
            t = compare(ind, "G20", start=2020)
            year = pd.Timestamp.today().year - 1
            latest = t.loc[:str(year)].ffill().iloc[-1].dropna().sort_values()
            return C.bar(latest, f"{title} ({year})", "% of GDP", "IMF WEO", horizontal=True, highlight="IND")
        s.chart(chart, "half")


@story("india_structure", "Structural change", "India",
       "What does India produce, and how is that changing compared with China and its peers?",
       method="Value added by sector as a share of GDP (World Bank WDI).",
       caveats=["Sector shares don't sum to 100 (net taxes are excluded); 'industry' includes construction and "
                "utilities, of which manufacturing is a part."])
def _(s: Builder):
    def sectors():
        codes = {"NV.AGR.TOTL.ZS": "Agriculture", "NV.IND.MANF.ZS": "Manufacturing", "NV.SRV.TOTL.ZS": "Services"}
        df = worldbank.get(list(codes), ["IND", "CHN"], start=1970)
        df["name"] = df["country"] + " " + df["series"].map(codes)
        w = df.pivot_table(index="date", columns="name", values="value")
        return C.line(w, "Sector shares of GDP: India vs China", "% of GDP", "World Bank WDI")
    s.chart(sectors)

    def manuf():
        t = compare("manufacturing_gdp", "EM_ASIA", start=2015)
        latest = t.ffill().iloc[-1].sort_values()
        s.insight(f"Manufacturing is {latest['IND']:.1f}% of India's GDP vs {latest['CHN']:.1f}% in China "
                  f"(latest World Bank data).", 10)
        return C.bar(latest, "Manufacturing share of GDP, emerging Asia (latest)", "% of GDP", "World Bank WDI",
                     horizontal=True, highlight="IND")
    s.chart(manuf, "half")

    s.chart(lambda: C.line(compare("exports_gdp", "EM_ASIA", start=1990), "Exports of goods and services",
                           "% of GDP", "World Bank WDI"), "half")
