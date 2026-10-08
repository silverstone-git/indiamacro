"""Oil and refined-product markets: prices, spreads, the futures curve, and trade flows.

Prices
  * :func:`prices` - daily spot prices from EIA via FRED: Brent, WTI, diesel (ULSD),
    jet fuel and gasoline, all converted to US$/bbl.
  * :func:`cracks` - refining margins (product minus crude), the cleanest signal of a
    *refining* shock as opposed to a *crude* shock.
  * :func:`futures` / :func:`curve` / :func:`dated_to_frontline` - NYMEX futures via Yahoo:
    the forward curve and how tight the prompt market is.
  * :func:`pink_sheet` - World Bank monthly commodity prices (Brent, Dubai, WTI, gas, coal...).
  * :func:`indian_basket` - PPAC's official Indian crude basket (current fiscal year) and a
    Brent/Dubai proxy for history.

Flows
  * :func:`jodi` - JODI Oil World Database: production, exports, imports, refinery
    runs and stocks by country, monthly. (Russia and Iraq stopped reporting exports.)
  * :func:`comtrade` - UN Comtrade monthly imports/exports by partner (e.g. India's crude
    suppliers). Free preview tier: one month per request.
  * :func:`russia_exports` - CREA Russia Fossil Tracker: daily seaborne/pipeline export
    volumes by commodity and destination, from ship tracking.

Routes
  * :func:`chokepoints` - IMF PortWatch: daily vessel transits (tankers, all ships) through
    28 maritime chokepoints, from AIS ship tracking. The best free gauge of whether a
    route is being used; war-risk insurance premiums themselves are not published freely.
  * :func:`shipping_equities` - tanker and container shipping share prices, a market
    proxy for freight and insurance costs.
"""

from __future__ import annotations

import io
import json
import re
import time

import pandas as pd

from .. import _http, countries as _countries
from ..utils import fy_label, month_start

SOURCE = "energy"
BBL_PER_GAL = 42

# ---------------------------------------------------------------- daily spot prices (FRED / EIA)

SPOT = {
    "brent":       ("DCOILBRENTEU", 1, "Brent (Europe), dated"),
    "wti":         ("DCOILWTICO", 1, "WTI (Cushing)"),
    "diesel_nyh":  ("DDFUELNYH", BBL_PER_GAL, "Ultra-low-sulphur diesel, NY Harbor"),
    "diesel_gulf": ("DDFUELUSGULF", BBL_PER_GAL, "Ultra-low-sulphur diesel, US Gulf Coast"),
    "jet_gulf":    ("DJFUELUSGULF", BBL_PER_GAL, "Jet fuel (kerosene), US Gulf Coast"),
    "gasoline_nyh": ("DGASNYH", BBL_PER_GAL, "Conventional gasoline, NY Harbor"),
}


def prices(names: list[str] | None = None, start=None) -> pd.DataFrame:
    """Daily spot prices in **US$/bbl**, one column per product (see :data:`SPOT`)."""
    from . import fred

    names = names or list(SPOT)
    cols = {}
    for n in names:
        sid, factor, _ = SPOT[n]
        cols[n] = fred.series(sid, start=start) * factor
    df = pd.DataFrame(cols).dropna(how="all")
    df.attrs.update(source="EIA spot prices via FRED", unit="US$/bbl")
    return df


def cracks(start=None) -> pd.DataFrame:
    """Daily crack spreads vs Brent, US$/bbl, plus the US 3-2-1 crack vs WTI.

    A refinery outage (e.g. strikes on Russian refineries) shows up as *wider product
    cracks* with crude flat or even weaker; a crude-supply shock lifts crude and
    products together, leaving cracks roughly unchanged.
    """
    p = prices(start=start)
    out = pd.DataFrame({
        "diesel_crack": p["diesel_nyh"] - p["brent"],
        "gasoline_crack": p["gasoline_nyh"] - p["brent"],
        "jet_crack": p["jet_gulf"] - p["brent"],
        "crack_321": (2 * p["gasoline_nyh"] + p["diesel_nyh"]) / 3 - p["wti"],
    }).dropna(how="all")
    out.attrs.update(source="EIA spot prices via FRED", unit="US$/bbl")
    return out


# ---------------------------------------------------------------- futures (Yahoo)

FUTURES = {
    "BZ": ("BZ=F", "Brent crude (NYMEX)", 1),
    "CL": ("CL=F", "WTI crude (NYMEX)", 1),
    "HO": ("HO=F", "ULSD / heating oil (NYMEX)", BBL_PER_GAL),
    "RB": ("RB=F", "RBOB gasoline (NYMEX)", BBL_PER_GAL),
    "NG": ("NG=F", "Henry Hub natural gas (NYMEX), $/MMBtu", 1),
}
_MONTH_CODES = "FGHJKMNQUVXZ"


def _yahoo_close(tickers: list[str], start=None, period: str | None = None, ttl: float = 6 * 3600) -> pd.DataFrame:
    """Daily closes for Yahoo tickers, cached on disk like every other source."""
    import logging

    import yfinance as yf

    logging.getLogger("yfinance").setLevel(logging.CRITICAL)   # unlisted contract months are expected
    key = f"yahoo:{','.join(sorted(tickers))}:{start}:{period}"
    path = _http._cache_path("https://query1.finance.yahoo.com/" + key, None)
    if _http.settings.cache and path.exists() and time.time() - path.stat().st_mtime < ttl:
        return pd.read_csv(path, index_col=0, parse_dates=True)
    kw = {"period": period} if period else {"start": str(pd.Timestamp(start or "2000-01-01").date())}
    raw = yf.download(tickers, progress=False, auto_adjust=False, threads=True, **kw)
    if raw is None or raw.empty:
        raise _http.SourceError("yahoo", f"no data for {tickers}")
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]].set_axis(tickers, axis=1)
    close.index = pd.to_datetime(close.index).tz_localize(None).normalize()
    close = close.dropna(how="all")
    if _http.settings.cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        close.to_csv(path)
    return close


def futures(roots: list[str] | None = None, start="2007-01-01") -> pd.DataFrame:
    """Front-month (continuous) futures settlements. Products converted to US$/bbl."""
    roots = roots or ["BZ", "CL", "HO", "RB"]
    close = _yahoo_close([FUTURES[r][0] for r in roots], start=start)
    out = pd.DataFrame({r: close[FUTURES[r][0]] * FUTURES[r][2] for r in roots if FUTURES[r][0] in close})
    out.attrs.update(source="NYMEX futures via Yahoo Finance", unit="US$/bbl (NG in $/MMBtu)")
    return out


def curve(root: str = "BZ", months: int = 18) -> pd.DataFrame:
    """Today's forward curve: one row per listed contract month with its latest settlement.

    Steep *backwardation* (near > far) means the market is short of prompt barrels -
    the signature of a supply shock. *Contango* (near < far) means a glut, and pays
    holders to store oil.
    """
    today = pd.Timestamp.today().normalize()
    tickers, delivery = [], {}
    for i in range(months + 2):
        d = (today + pd.DateOffset(months=i)).replace(day=1)
        t = f"{root}{_MONTH_CODES[d.month - 1]}{str(d.year)[-2:]}.NYM"
        tickers.append(t)
        delivery[t] = d
    close = _yahoo_close(tickers, period="1mo", ttl=3600)
    rows = []
    for t in tickers:
        if t in close and close[t].notna().any():
            s = close[t].dropna()
            rows.append({"contract": t.split(".")[0], "delivery": delivery[t],
                         "price": float(s.iloc[-1]) * FUTURES[root][2], "as_of": s.index[-1]})
    if not rows:
        raise _http.SourceError("yahoo", f"no {root} contracts found")
    df = pd.DataFrame(rows).sort_values("delivery", ignore_index=True)
    df.attrs.update(source="NYMEX futures via Yahoo Finance", unit="US$/bbl")
    return df


def dated_to_frontline(start="2007-01-01") -> pd.Series:
    """Dated Brent (physical, EIA) minus front-month Brent futures, US$/bbl, daily.

    Positive and rising = physical barrels for prompt loading are scarce relative to
    paper barrels; it spikes during supply shocks and falls when reserves are released.
    """
    spot = prices(["brent"], start=start)["brent"]
    fut = futures(["BZ"], start=start)["BZ"]
    s = (spot - fut).dropna().rename("dated_to_frontline")
    s.attrs.update(source="EIA (dated Brent) via FRED; NYMEX Brent via Yahoo", unit="US$/bbl")
    return s


# ---------------------------------------------------------------- World Bank Pink Sheet

def pink_sheet() -> pd.DataFrame:
    """World Bank Commodity Price Data ("Pink Sheet"), monthly, nominal US$, from 1960.

    Columns include 'Crude oil, Brent', 'Crude oil, Dubai', 'Crude oil, WTI',
    'Natural gas, Europe', 'Liquefied natural gas, Japan', 'Coal, Australian', metals,
    food and fertilisers.
    """
    page = _http.get("https://www.worldbank.org/en/research/commodity-markets", ttl=7 * _http.DAY,
                     source="worldbank").decode("utf-8", "replace")
    links = re.findall(r'https://thedocs\.worldbank\.org[^"]+CMO-Historical-Data-Monthly\.xlsx', page)
    if not links:
        raise _http.SourceError("worldbank", "Pink Sheet link not found on the commodity-markets page")
    body = _http.get(links[0], ttl=7 * _http.DAY, source="worldbank")
    raw = pd.read_excel(io.BytesIO(body), sheet_name="Monthly Prices", header=4)
    raw = raw.rename(columns={raw.columns[0]: "period"})
    raw = raw[raw["period"].astype(str).str.fullmatch(r"\d{4}M\d{2}")]
    raw.index = pd.to_datetime(raw["period"].str.replace("M", "-") + "-01")
    df = raw.drop(columns="period").apply(pd.to_numeric, errors="coerce")
    df.index.name = "date"
    df.attrs.update(source="World Bank Commodity Price Data (Pink Sheet)", unit="nominal US$ (see column)")
    return df


# ---------------------------------------------------------------- Indian crude basket (PPAC)

_PPAC_MONTHS = ["april", "may", "june", "july", "aug", "sep", "oct", "nov", "dec", "jan", "feb", "mar"]
# Sweet (Brent) share of the basket; PPAC revises this each year. Recent years: ~0.75.
BASKET_SWEET_SHARE = 0.75


def indian_basket() -> pd.DataFrame:
    """Indian crude basket, US$/bbl, monthly.

    ``official``: PPAC's published figure for the current fiscal year (PPAC only serves
    older years to registered users). ``proxy``: Brent/Dubai weighted by
    :data:`BASKET_SWEET_SHARE`, from the Pink Sheet, for long history. The proxy
    tracks the official series within a few dollars; cite it as an approximation.
    """
    fy = fy_label(pd.Timestamp.today()).replace("-", "-20")
    body = _http.get("https://ppac.gov.in/AjaxController/getInternationalPricesCrudeOil",
                     data={"financialYear": fy, "reportBy": 4, "pageId": 30},
                     headers={"X-Requested-With": "XMLHttpRequest"}, ttl=_http.DAY, source="ppac")
    result = json.loads(body).get("result") or {}
    rows = result.values() if isinstance(result, dict) else result
    official = {}
    for r in rows:
        if re.fullmatch(r"\d{4}-\d{2}", str(r.get("title", ""))):
            start = int(r["title"][:4])
            for i, m in enumerate(_PPAC_MONTHS):
                v = r.get(m)
                if v not in (None, ""):
                    official[month_start(start + (1 if i >= 9 else 0), 4 + i if i < 9 else i - 8)] = float(v)
    ps = pink_sheet()
    proxy = BASKET_SWEET_SHARE * ps["Crude oil, Brent"] + (1 - BASKET_SWEET_SHARE) * ps["Crude oil, Dubai"]
    df = pd.DataFrame({"proxy": proxy, "official": pd.Series(official, dtype=float)})
    df.index.name = "date"
    df.attrs.update(source="PPAC (official); World Bank Pink Sheet (proxy)", unit="US$/bbl")
    return df


# ---------------------------------------------------------------- JODI

JODI_FLOWS = {
    "INDPROD": "Production", "TOTEXPSB": "Exports", "TOTIMPSB": "Imports",
    "REFINOBS": "Refinery intake", "STOCKCH": "Stock change", "CLOSTLV": "Closing stocks",
    "TOTDEMO": "Demand",
}


def _jodi_links(kind: str) -> dict[int, str]:
    page = _http.get("https://www.jodidata.org/oil/database/data-downloads.aspx", ttl=7 * _http.DAY,
                     source="jodi").decode("utf-8", "replace")
    out = {}
    for href in re.findall(rf'href="(/_resources/files/downloads/oil-data/annual-csv/{kind}/[^"]+\.csv)"', page):
        year = re.search(r"(\d{4})\.csv$", href)
        if year:
            out[int(year.group(1))] = "https://www.jodidata.org" + href
    return out


def jodi(flow: str = "TOTEXPSB", product: str = "CRUDEOIL", countries=None, start_year: int = 2015,
         unit: str = "KBD") -> pd.DataFrame:
    """JODI Oil, monthly, long format ``date, country, series, value``.

    ``product``: CRUDEOIL (primary file) or a product such as GASDIES (diesel/gasoil),
    GASOLINE, JETKERO, TOTPRODS (secondary file). ``unit``: KBD (thousand bbl/day),
    KBBL or KTONS. ``countries=None`` returns every reporter.
    """
    kind = "primary" if product in ("CRUDEOIL", "NGL", "OTHERCRUDE", "TOTCRUDE") else "secondary"
    links = _jodi_links(kind)
    frames = []
    for year in sorted(y for y in links if y >= start_year):
        ttl = _http.DAY if year >= pd.Timestamp.today().year - 1 else 90 * _http.DAY
        df = pd.read_csv(io.BytesIO(_http.get(links[year], ttl=ttl, source="jodi")), dtype=str)
        frames.append(df[(df["ENERGY_PRODUCT"] == product) & (df["FLOW_BREAKDOWN"] == flow)
                         & (df["UNIT_MEASURE"] == unit)])
    if not frames:
        raise _http.SourceError("jodi", "no JODI files found")
    df = pd.concat(frames)
    df["value"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df = df.dropna(subset=["value"])
    df["country"] = [_safe_iso3(c) for c in df["REF_AREA"]]
    if countries is not None:
        df = df[df["country"].isin(_countries.expand(countries))]
    out = pd.DataFrame({"date": pd.to_datetime(df["TIME_PERIOD"] + "-01"), "country": df["country"],
                        "series": f"{product}.{flow}", "value": df["value"]})
    out = out.sort_values(["country", "date"], ignore_index=True)
    out.attrs.update(source="JODI Oil World Database", unit=unit)
    return out


def _safe_iso3(iso2: str) -> str:
    try:
        return _countries.iso3(iso2)
    except KeyError:
        return iso2


# ---------------------------------------------------------------- UN Comtrade

HS = {"crude": "2709", "products": "2710", "lng_gas": "2711", "coal": "2701"}


def _m49_names() -> dict[int, str]:
    data = _http.get_json("https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json",
                          ttl=30 * _http.DAY, source="comtrade")
    return {int(r["id"]): r["text"] for r in data["results"]}


def _m49(country: str) -> int:
    data = _http.get_json("https://comtradeapi.un.org/files/v1/app/reference/Reporters.json",
                          ttl=30 * _http.DAY, source="comtrade")
    iso3 = _countries.iso3(country)
    for r in data["results"]:
        if r.get("reporterCodeIsoAlpha3") == iso3 and not r.get("isGroup"):
            return int(r["id"])
    raise KeyError(f"no Comtrade reporter code for {country}")


def comtrade(reporter="IND", commodity: str = "crude", flow: str = "M", months: int = 12,
             end=None) -> pd.DataFrame:
    """Monthly trade by partner: ``date, partner, value_usd, net_weight_kg``.

    ``commodity`` is a key of :data:`HS` or an HS code. ``flow`` M imports / X exports.
    Reporters publish with a 1-4 month lag; months with no data yet are skipped.
    """
    code, names = _m49(reporter), _m49_names()
    end = pd.Timestamp(end or pd.Timestamp.today()).replace(day=1)
    rows = []
    for i in range(months):
        period = (end - pd.DateOffset(months=i)).strftime("%Y%m")
        data = _http.get_json("https://comtradeapi.un.org/public/v1/preview/C/M/HS",
                              {"reporterCode": code, "period": period, "cmdCode": HS.get(commodity, commodity),
                               "flowCode": flow}, ttl=7 * _http.DAY, source="comtrade")
        for r in data.get("data") or []:
            if r["partnerCode"] == 0 or r.get("motCode") not in (0, None) or r.get("partner2Code") not in (0, None):
                continue
            rows.append({"date": pd.Timestamp(r["refYear"], r["refMonth"], 1),
                         "partner": names.get(r["partnerCode"], str(r["partnerCode"])),
                         "value_usd": r["primaryValue"], "net_weight_kg": r.get("netWgt")})
        time.sleep(0.3)   # be polite to the free tier
    df = pd.DataFrame(rows)
    if df.empty:
        raise _http.SourceError("comtrade", f"no data for {reporter} {commodity} in the last {months} months")
    df = df.groupby(["date", "partner"], as_index=False).sum().sort_values(["date", "value_usd"],
                                                                           ascending=[True, False])
    df.attrs.update(source="UN Comtrade", unit="US$")
    return df.reset_index(drop=True)


# ---------------------------------------------------------------- CREA Russia Fossil Tracker

CREA = "https://api.russiafossiltracker.com/v0/counter"


def russia_exports(by: str = "commodity", start="2022-01-01", end=None, commodity: str | None = None) -> pd.DataFrame:
    """Russian fossil-fuel exports from CREA's tracker.

    ``by="commodity"``: daily tonnes and EUR by commodity (crude_oil, oil_products,
    pipeline_oil, lng, natural_gas, coal). ``by="destination"``: monthly by destination
    country (optionally for one ``commodity``).
    """
    agg = "date,commodity" if by == "commodity" else "month,destination_country"
    params = {"format": "json", "aggregate_by": agg, "date_from": str(pd.Timestamp(start).date()),
              "date_to": str(pd.Timestamp(end or pd.Timestamp.today()).date()), "commodity": commodity}
    data = _http.get_json(CREA, params, ttl=_http.DAY, source="crea")["data"]
    df = pd.DataFrame(data)
    if df.empty:
        raise _http.SourceError("crea", "no data")
    df["date"] = pd.to_datetime(df["date" if by == "commodity" else "month"])
    keep = ["date", "commodity" if by == "commodity" else "destination_country", "value_tonne", "value_eur", "value_usd"]
    df = df[[c for c in keep if c in df]].sort_values("date", ignore_index=True)
    df.attrs.update(source="CREA Russia Fossil Tracker", unit="tonnes / EUR / USD")
    return df


# ---------------------------------------------------------------- shipping routes

PORTWATCH = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
             "Daily_Chokepoints_Data/FeatureServer/0/query")

CHOKEPOINTS = ["Strait of Hormuz", "Bab el-Mandeb Strait", "Suez Canal", "Cape of Good Hope",
               "Malacca Strait", "Bosporus Strait", "Panama Canal", "Gibraltar Strait", "Dover Strait",
               "Taiwan Strait", "Lombok Strait", "Sunda Strait"]


def chokepoints(names: list[str] | str | None = None, start="2023-01-01") -> pd.DataFrame:
    """Daily transits through maritime chokepoints (IMF PortWatch), long format:
    ``date, chokepoint, n_tanker, n_total, capacity_tanker``.

    Counts come from AIS transponders: ships that switch AIS off are not counted, so
    during conflicts the counts understate traffic (but not by a 95% collapse).
    ``names=None`` returns :data:`CHOKEPOINTS`.
    """
    names = [names] if isinstance(names, str) else (names or CHOKEPOINTS)
    quoted = ",".join("'" + n.replace("'", "''") + "'" for n in names)
    rows, offset = [], 0
    while True:
        data = _http.get_json(PORTWATCH, {
            "where": f"portname IN ({quoted}) AND date >= DATE '{pd.Timestamp(start).date()}'",
            "outFields": "date,portname,n_tanker,n_total,capacity_tanker", "orderByFields": "date,portname",
            "resultOffset": offset, "resultRecordCount": 2000, "f": "json"}, ttl=12 * 3600, source="portwatch")
        if "error" in data:
            raise _http.SourceError("portwatch", str(data["error"]))
        feats = data.get("features", [])
        rows += [f["attributes"] for f in feats]
        if len(feats) < 2000 and not data.get("exceededTransferLimit"):
            break
        offset += len(feats)
    if not rows:
        raise _http.SourceError("portwatch", f"no data for {names}")
    df = pd.DataFrame(rows).rename(columns={"portname": "chokepoint"})
    df["date"] = pd.to_datetime(df["date"], unit="ms")
    df = df.sort_values(["chokepoint", "date"], ignore_index=True)
    df.attrs.update(source="IMF PortWatch (AIS-based)", unit="vessels per day")
    return df[["date", "chokepoint", "n_tanker", "n_total", "capacity_tanker"]]


SHIPPING_EQUITIES = {
    "INSW": "International Seaways (crude and product tankers)",
    "FRO": "Frontline (crude tankers)",
    "DHT": "DHT Holdings (VLCCs)",
    "STNG": "Scorpio Tankers (product tankers)",
    "TRMD": "TORM (product tankers)",
    "ZIM": "ZIM (container shipping)",
}


def shipping_equities(tickers: list[str] | None = None, start="2023-01-01") -> pd.DataFrame:
    """Daily closing prices of shipping companies (Yahoo). Tanker shares rise with freight
    rates, which in turn rise with longer routes, war-risk insurance and vessel scarcity.
    A market proxy only - not a freight or insurance index."""
    tickers = tickers or list(SHIPPING_EQUITIES)
    out = _yahoo_close(tickers, start=start)
    out.attrs.update(source="Yahoo Finance", unit="share price, local currency")
    return out
