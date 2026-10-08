"""Pages: data explorer and source status."""

from __future__ import annotations

from .. import ping
from ..sources import bis, fred, imf, mospi, oecd, worldbank
from . import charts as C
from .framework import Builder, Param, story

EXPLORER_SOURCES = [
    ("fred", "FRED series id (e.g. DEXINUS, DCOILBRENTEU, CPIAUCSL)"),
    ("worldbank", "World Bank indicator (e.g. NY.GDP.PCAP.PP.KD)"),
    ("imf", "IMF WEO indicator (e.g. PCPIPCH, GGXWDG_NGDP)"),
    ("mospi_nas", "MoSPI national accounts indicator code (1-24)"),
    ("mospi_rbi", "MoSPI RBI table code (1-48)"),
    ("bis_policy", "BIS policy rates (countries)"),
    ("oecd_cli", "OECD leading indicator (countries)"),
]


@story("explorer", "Data explorer", "Tools",
       "Plot any series from any source.",
       params=[Param("source", "Source", "select", "fred", EXPLORER_SOURCES),
               Param("code", "Code", "text", "DCOILBRENTEU"),
               Param("countries", "Countries", "text", "IND, CHN, USA",
                     help="For World Bank / IMF / BIS / OECD. Names, ISO codes or groups (BRICS, G20, ...)"),
               Param("start", "From year", "number", 2000)])
def _(s: Builder):
    src, code, start = s.p["source"], s.p["code"].strip(), s.p["start"]
    ctry = [c.strip() for c in s.p["countries"].split(",") if c.strip()]

    def chart():
        if src == "fred":
            df = fred.get([c.strip() for c in code.split(",")], start=f"{start}-01-01")
            return C.line(df.pivot_table(index="date", columns="series", values="value"), code, "", "FRED")
        if src == "worldbank":
            df = worldbank.get(code, ctry, start=start)
            return C.line(df.pivot_table(index="date", columns="country", values="value"),
                          df["series_name"].iloc[0], "", "World Bank WDI")
        if src == "imf":
            df = imf.weo(code, ctry, start=start)
            return C.line(df.pivot_table(index="date", columns="country", values="value"), code, "",
                          "IMF WEO (includes projections)")
        if src == "mospi_nas":
            df = mospi.nas(int(code))
            df = df[df["date"].dt.year >= start]
            df["key"] = df["base_year"] + " " + df.get("revision", "").fillna("")
            latest = df.drop_duplicates(["date", "base_year"], keep="last")
            w = latest.pivot_table(index="date", columns="base_year", values="constant_price")
            return C.line(w, f"{mospi.NAS_INDICATORS.get(int(code), code)} (constant prices)",
                          df["unit"].iloc[0], "MoSPI National Accounts", note="Fiscal years; one line per base year.")
        if src == "mospi_rbi":
            df = mospi.rbi(int(code))
            dims = [c for c in df.columns if c not in ("indicator", "year", "month", "value", "unit", "date",
                                                        "quarter")]
            df["key"] = df[dims].astype(str).agg(" | ".join, axis=1) if dims else "value"
            top = df.groupby("key")["value"].apply(lambda v: v.abs().sum()).nlargest(8).index
            w = df[df["key"].isin(top)].pivot_table(index="date", columns="key", values="value")
            return C.line(w[w.index.year >= start], df["indicator"].iloc[0], str(df["unit"].dropna().iloc[0])
                          if df["unit"].notna().any() else "", "RBI via MoSPI",
                          note="Showing the 8 largest series in the table.")
        if src == "bis_policy":
            df = bis.policy_rate(ctry, start=str(start))
            return C.line(df.pivot_table(index="date", columns="country", values="value"), "Policy rates", "%", "BIS")
        if src == "oecd_cli":
            df = oecd.cli(ctry, start=f"{start}-01")
            return C.line(df.pivot_table(index="date", columns="country", values="value"),
                          "Composite leading indicators", "index", "OECD")
        raise ValueError(f"unknown source {src}")
    s.chart(chart)


@story("status", "Source status", "Tools", "Is every data source reachable right now?")
def _(s: Builder):
    def run():
        df = ping.run(verbose=False)
        ok = (df["status"] == "OK").sum()
        s.insight(f"{ok} of {len(df)} source checks passed.", 10)
        df = df.set_index("source")
        return C.table(df[["query", "status", "rows", "latest_date", "latest_value", "seconds"]],
                       "Live checks (cached responses count as passing)", fmt="{:,.1f}")
    s.chart(run)
    s.text("**Not automated:** " + " ".join(f"*{n}* - {w}" for n, w in ping.NOT_AUTOMATED))
