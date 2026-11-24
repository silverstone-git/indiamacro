/* indiamacro terminal: live panels, six map modes, satellite propagation, chart workspace and the analyst. */
"use strict";

/* ================================================================== utilities */
const $ = (s, el = document) => el.querySelector(s);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined) el.append(kid.nodeType ? kid : String(kid));
  return el;
};
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (v, d = 2) => v === null || v === undefined || !isFinite(v) ? "–"
  : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
const smart = (v) => v === null || v === undefined ? "–" : Math.abs(v) >= 1000 ? num(v, 0) : Math.abs(v) >= 10 ? num(v, 2) : num(v, 3);
const D2R = Math.PI / 180, R2D = 180 / Math.PI, RE = 6371;
// Categorical palette (dark-surface steps), fixed order; status colours reserved.
const CAT = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"];
const GRAY = "#7d828d";

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}
const post = (path, body) => api(path, { method: "POST", body: JSON.stringify(body) });
function toast(msg) { const t = h("div", { class: "toast" }, msg); document.body.append(t); setTimeout(() => t.remove(), 3500); }
function badge(el, env) {
  if (!el) return;
  if (!env) { el.className = "badge err"; el.textContent = "ERR"; el.title = "request failed"; return; }
  const sim = env.status === "sim";
  el.className = "badge " + (sim ? "sim" : "live");
  el.textContent = sim ? "SIM" : "LIVE";
  el.title = `${env.source}\nas of ${env.asof}${env.note ? "\n" + env.note : ""}`;
}
function sparkSvg(vals, w = 64, hgt = 16) {
  const v = (vals || []).filter((x) => x !== null && isFinite(x));
  if (v.length < 2) return h("svg", { class: "spark" });
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((y, i) => `${(i / (v.length - 1) * w).toFixed(1)},${(hgt - 1 - (y - lo) / span * (hgt - 2)).toFixed(1)}`).join(" ");
  const col = v[v.length - 1] >= v[0] ? "var(--up)" : "var(--down)";
  const svg = h("svg", { class: "spark", viewBox: `0 0 ${w} ${hgt}`, preserveAspectRatio: "none" });
  svg.innerHTML = `<polyline points="${pts}" fill="none" stroke="${col}" stroke-width="1.2"/>`;
  return svg;
}
const ago = (ms) => { const m = (Date.now() - ms) / 60000; return m < 60 ? `${Math.round(m)}m` : m < 1440 ? `${Math.round(m / 60)}h` : `${Math.round(m / 1440)}d`; };

/* ================================================================== state */
const S = {
  mode: null, map: null, layers: {}, timers: {}, feeds: {}, quotes: {}, wire: new Map(),
  observer: { name: "New Delhi", lat: 28.61, lon: 77.21 }, sats: [], satGroup: null, selected: null,
  charts: [], activeChart: -1, history: [], ctx: "",
};

/* ================================================================== clocks */
function clocks() {
  const zones = [["IST", "Asia/Kolkata"], ["UTC", "UTC"], ["LDN", "Europe/London"], ["NY", "America/New_York"], ["TYO", "Asia/Tokyo"]];
  const el = $("#clocks");
  const tick = () => {
    const now = new Date();
    el.innerHTML = zones.map(([l, z]) => `<span>${l} <b>${now.toLocaleTimeString("en-GB", { timeZone: z, hour: "2-digit", minute: "2-digit", second: l === "IST" ? "2-digit" : undefined })}</b></span>`).join("");
  };
  tick(); setInterval(tick, 1000);
}

/* ================================================================== markets */
async function loadQuotes() {
  let env;
  try { env = await api("api/live/quotes"); } catch { return badge($("#b-quotes"), null); }
  S.feeds.quotes = env; badge($("#b-quotes"), env);
  const box = $("#watch"); box.innerHTML = "";
  let group = null;
  const tape = [];
  for (const q of env.data) {
    if (q.group !== group) { group = q.group; box.append(h("div", { class: "wl-group" }, group.toUpperCase())); }
    const cls = q.chg_pct > 0.005 ? "up" : q.chg_pct < -0.005 ? "down" : "flat";
    const prev = S.quotes[q.symbol];
    const row = h("div", { class: "wl", title: `${q.symbol} · last ${q.time || ""} UTC · prev close ${smart(q.prev_close)}`,
      onclick: () => runCommand(`G ${symbolSeries(q.symbol) || q.label}`) },
      h("span", { class: "n" }, q.label), sparkSvg(q.spark), h("span", { class: "v" }, smart(q.last)),
      h("span", { class: "c " + cls }, q.chg_pct == null ? "–" : `${q.chg_pct >= 0 ? "+" : ""}${num(q.chg_pct)}%`));
    if (prev && q.last !== prev.last) row.classList.add(q.last > prev.last ? "flash-up" : "flash-down");
    box.append(row);
    S.quotes[q.symbol] = q;
    if (q.last != null) tape.push(`<span><b>${esc(q.label)}</b>${smart(q.last)} <i class="${cls}">${q.chg_pct >= 0 ? "▲" : "▼"} ${num(Math.abs(q.chg_pct))}%</i></span>`);
    if (q.chg_pct != null && Math.abs(q.chg_pct) >= 1.5)
      addWire(`mkt-${q.symbol}-${new Date().toISOString().slice(0, 10)}`, Date.parse(q.time) || Date.now(), "MKT",
        `${q.label} ${q.chg_pct >= 0 ? "+" : ""}${num(q.chg_pct)}% to ${smart(q.last)}`, null, () => runCommand(`G ${symbolSeries(q.symbol) || q.label}`));
  }
  if (env.status === "sim") tape.unshift(`<span class="sim"><b class="sim">SIMULATED QUOTES</b>source unavailable</span>`);
  $("#tape-inner").innerHTML = tape.join("") + tape.join("");
}
function symbolSeries(sym) {
  return { "^NSEI": "nifty", "^BSESN": "nifty", "INR=X": "usdinr", "BZ=F": "brent", "CL=F": "wti", "GC=F": "gold", "^GSPC": "sp500",
    "DX-Y.NYB": "dxy", "^TNX": "ust10y", "HG=F": "copper", "NG=F": "natgas", "BTC-USD": "bitcoin" }[sym];
}

const INDIA_LABELS = { gdp_growth: ["Real GDP growth", "%"], cpi_inflation: ["CPI inflation", "%"], wpi_inflation: ["WPI inflation", "%"],
  iip_growth: ["IIP growth", "%"], unemployment: ["Unemployment (PLFS)", "%"], repo_rate: ["RBI repo rate", "%"],
  usdinr: ["USD/INR (FRED)", ""], reer: ["REER (BIS)", ""], forex_reserves: ["FX reserves", "$bn"] };
const INDIA_SERIES = { gdp_growth: "india_gdp_growth", cpi_inflation: "india_cpi", wpi_inflation: "india_wpi", iip_growth: "india_iip",
  unemployment: "india_unemployment", repo_rate: "repo_rate", usdinr: "usdinr", reer: "reer", forex_reserves: "forex_reserves" };
async function loadIndia() {
  let env;
  try { env = await api("api/live/india"); } catch { return badge($("#b-india"), null); }
  badge($("#b-india"), env);
  const box = h("div", { class: "kv" });
  for (const r of env.data) {
    const [label, unit] = INDIA_LABELS[r.series] || [r.series, ""];
    let v = r.value;
    if (r.series === "forex_reserves" && v != null) v = v / 1000;
    const row = h("span", { class: "k", title: `${r.source || ""}${r.error ? "\n" + r.error : ""}`, style: "cursor:pointer",
      onclick: () => INDIA_SERIES[r.series] && runCommand(`G ${INDIA_SERIES[r.series]}`) }, label);
    box.append(row, h("span", { class: "val" }, r.error ? "n/a" : `${smart(v)}${unit === "%" ? "%" : unit ? " " + unit : ""}`),
      h("span", { class: "d" }, r.error ? String(r.error).slice(0, 60) : `${r.date || "simulated"} · ${(r.source || "").slice(0, 38)}`));
  }
  $("#india").replaceChildren(box);
}

/* ================================================================== wire */
function addWire(id, t, tag, text, latlon, onclick) {
  if (S.wire.has(id)) return;
  S.wire.set(id, { id, t, tag, text, latlon, onclick });
  renderWireSoon();
}
let wireTimer = null;
function renderWireSoon() { clearTimeout(wireTimer); wireTimer = setTimeout(renderWire, 150); }
function renderWire() {
  const items = [...S.wire.values()].sort((a, b) => b.t - a.t).slice(0, 200);
  $("#wire").replaceChildren(...items.map((w) => h("div", { class: "wi", title: w.text, onclick: () => {
    if (w.onclick) return w.onclick();
    if (w.latlon) S.map.flyTo(w.latlon, 6);
  } }, h("span", { class: "tm" }, ago(w.t)), h("span", { class: "tg " + w.tag }, w.tag), h("span", { class: "tx" }, w.text))));
}

async function loadQuakes() {
  try {
    const env = await api("api/live/quakes"); S.feeds.quakes = env;
    for (const q of env.data) if (q.mag >= 5)
      addWire("q" + q.id, q.time, "QUAKE", `M${q.mag} ${q.place || ""}${q.tsunami ? " · tsunami flag" : ""}`, [q.lat, q.lon],
        () => { setMode("climate"); S.map.flyTo([q.lat, q.lon], 6); });
    if (S.mode === "climate") drawClimate();
  } catch {}
}
async function loadEvents() {
  try {
    const env = await api("api/live/events"); S.feeds.events = env;
    for (const e of env.data) addWire("e" + e.id, Date.parse(e.date) || Date.now(), "HAZARD", `${e.category}: ${e.title}`, [e.lat, e.lon],
      () => { setMode("climate"); S.map.flyTo([e.lat, e.lon], 6); });
    if (S.mode === "climate") drawClimate();
  } catch {}
}
async function loadWeather() {
  try {
    const env = await api("api/live/weather"); S.feeds.weather = env;
    for (const w of env.data) if (w.pm25 >= 150)
      addWire(`aq-${w.city}-${(w.time || "").slice(0, 13)}`, Date.parse((w.time || "") + "Z") || Date.now(), "AIR",
        `${w.city} PM2.5 ${num(w.pm25, 0)} µg/m³ (hazardous; WHO 24h guideline 15)`, [w.lat, w.lon], () => { setMode("climate"); S.map.flyTo([w.lat, w.lon], 7); });
    if (S.mode === "climate") drawClimate();
  } catch {}
}
async function loadChoke() {
  try {
    const env = await api("api/live/chokepoints"); S.feeds.choke = env;
    for (const c of env.data) {
      const dev = c.avg365 ? (c.last7 / c.avg365 - 1) * 100 : 0;
      if (Math.abs(dev) >= 25) addWire(`ch-${c.name}-${c.date}`, Date.parse(c.date), "SHIP",
        `${c.name}: ${num(c.last7, 0)} transits/day (7d) vs ${num(c.avg365, 0)} 1y avg (${dev >= 0 ? "+" : ""}${num(dev, 0)}%)`, [c.lat, c.lon],
        () => { setMode("traffic"); S.map.flyTo([c.lat, c.lon], 6); });
    }
    if (S.mode === "traffic" || S.mode === "econ") S.mode === "traffic" ? drawTraffic() : drawEconOverlays();
  } catch {}
}

/* ================================================================== map */
// Esri dark-gray canvas: free to use with attribution, no key (CARTO's basemaps now need one).
const BASE = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/{style}/MapServer/tile/{z}/{y}/{x}";
const ATTR = 'Basemap © Esri, HERE, Garmin, © OpenStreetMap contributors';
function initMap() {
  const map = L.map("map", { worldCopyJump: true, zoomControl: true, minZoom: 2, preferCanvas: true, attributionControl: true })
    .setView([22, 78], 4);
  map.createPane("labels"); map.getPane("labels").style.zIndex = 450; map.getPane("labels").style.pointerEvents = "none";
  map.createPane("night"); map.getPane("night").style.zIndex = 430; map.getPane("night").style.pointerEvents = "none";
  map.createPane("choro"); map.getPane("choro").style.zIndex = 380;
  S.nightRenderer = L.canvas({ pane: "night", padding: 0.5 });
  S.choroRenderer = L.svg({ pane: "choro" });
  L.tileLayer(BASE, { style: "World_Dark_Gray_Base", attribution: ATTR, maxNativeZoom: 16, maxZoom: 18 }).addTo(map);
  L.tileLayer(BASE, { style: "World_Dark_Gray_Reference", pane: "labels", maxNativeZoom: 16, maxZoom: 18, opacity: 0.8 }).addTo(map);
  S.map = map;
  S.layers.night = L.layerGroup().addTo(map);
  S.layers.mode = L.layerGroup().addTo(map);
  S.layers.overlay = L.layerGroup().addTo(map);
  S.layers.sats = L.layerGroup().addTo(map);
  S.canvas = L.canvas({ padding: 0.3 });
  map.on("click", (e) => {
    if (["gnss", "astro", "mil"].includes(S.mode)) {
      S.observer = { name: `${num(e.latlng.lat, 2)}, ${num(e.latlng.lng, 2)}`, lat: e.latlng.lat, lon: wrapLon(e.latlng.lng) };
      toast(`Observer set to ${S.observer.name}`); satTick(true);
    }
  });
  map.on("moveend", () => { if (S.mode === "traffic") scheduleAircraft(800); });
  drawNight(); setInterval(drawNight, 60000);
  $("#opt-night").addEventListener("change", drawNight);
}
const wrapLon = (lon) => ((lon + 540) % 360) - 180;

/* --------------------------------------------- astronomy (low-precision, ~0.5-1°: fine for a world map) */
function sunMoon(date = new Date()) {
  const n = date.getTime() / 86400000 + 2440587.5 - 2451545.0;
  const gmst = ((280.46061837 + 360.98564736629 * n) % 360 + 360) % 360;
  const eps = (23.439 - 0.0000004 * n) * D2R;
  const L = (280.460 + 0.9856474 * n) % 360, g = ((357.528 + 0.9856003 * n) % 360) * D2R;
  const lamS = (L + 1.915 * Math.sin(g) + 0.020 * Math.sin(2 * g)) * D2R;
  const toEq = (lam, bet) => ({
    ra: Math.atan2(Math.sin(lam) * Math.cos(eps) - Math.tan(bet) * Math.sin(eps), Math.cos(lam)) * R2D,
    dec: Math.asin(Math.sin(bet) * Math.cos(eps) + Math.cos(bet) * Math.sin(eps) * Math.sin(lam)) * R2D });
  const sun = toEq(lamS, 0);
  const Lm = (218.316 + 13.176396 * n) * D2R, Mm = (134.963 + 13.064993 * n) * D2R, F = (93.272 + 13.229350 * n) * D2R;
  const D = (297.850 + 12.190749 * n) * D2R;
  const lamM = Lm + (6.289 * Math.sin(Mm) - 1.274 * Math.sin(Mm - 2 * D) + 0.658 * Math.sin(2 * D)) * D2R, betM = 5.128 * Math.sin(F) * D2R;
  const moon = toEq(lamM, betM);
  const elong = Math.acos(Math.cos(lamM - lamS) * Math.cos(betM));
  const waxing = (((lamM - lamS) * R2D) % 360 + 360) % 360 < 180;
  return { gmst, sun: { lat: sun.dec, lon: wrapLon(sun.ra - gmst) }, moon: { lat: moon.dec, lon: wrapLon(moon.ra - gmst) },
    illum: (1 - Math.cos(elong)) / 2, waxing, age: elong * R2D };
}
function elevation(body, lat, lon) {   // altitude of a body with sub-point `body` seen from (lat, lon), degrees
  const H = (lon - body.lon) * D2R, p = lat * D2R, d = body.lat * D2R;
  return Math.asin(Math.sin(p) * Math.sin(d) + Math.cos(p) * Math.cos(d) * Math.cos(H)) * R2D;
}
function nightPolygon(sun, h0) {   // region where the sun is below h0 degrees
  const d = sun.lat * D2R, s = Math.sin(h0 * D2R), A = Math.sin(d);
  const southNight = -A < s, pole = southNight ? -85 : 85, opp = -pole;
  const pts = [];
  for (let lon = -180; lon <= 180; lon += 2) {
    const B = Math.cos(d) * Math.cos((lon - sun.lon) * D2R), R = Math.hypot(A, B), psi = Math.atan2(B, A);
    let lat;
    if (s / R > 1) lat = opp; else if (s / R < -1) lat = pole;
    else {
      const a = Math.asin(s / R);
      const cands = [a - psi, Math.PI - a - psi].map((x) => Math.atan2(Math.sin(x), Math.cos(x)));
      const c = cands.find((x) => Math.abs(x) <= Math.PI / 2);
      lat = c === undefined ? pole : Math.max(-85, Math.min(85, c * R2D));
    }
    pts.push([lat, lon]);
  }
  return [[pole, -180], ...pts, [pole, 180]];
}
function drawNight() {
  S.layers.night.clearLayers();
  if (!$("#opt-night").checked) return;
  const sm = sunMoon();
  for (const h0 of [0, -6, -12, -18]) {
    const poly = nightPolygon(sm.sun, h0);
    for (const off of [-360, 0, 360])
      L.polygon(poly.map(([a, b]) => [a, b + off]), { pane: "night", renderer: S.nightRenderer, stroke: false,
        fillColor: "#0d2350", fillOpacity: 0.16, interactive: false }).addTo(S.layers.night);
    if (h0 === 0)   // the terminator itself: navy fill alone barely shows on a dark basemap
      for (const off of [-360, 0, 360])
        L.polyline(poly.slice(1, -1).map(([a, b]) => [a, b + off]), { pane: "night", renderer: S.nightRenderer, color: "#ffa028",
          weight: 1, opacity: 0.55, dashArray: "4 4", interactive: false }).addTo(S.layers.night);
  }
  if (S.mode === "astro") drawAstro();
}

/* ================================================================== modes */
const MODES = {
  econ: { enter: enterEcon, label: "ECON" }, traffic: { enter: enterTraffic, label: "TRAFFIC" },
  climate: { enter: enterClimate, label: "CLIMATE" }, gnss: { enter: () => enterSats("gnss"), label: "GNSS" },
  astro: { enter: enterAstro, label: "ASTRO" }, mil: { enter: () => enterSats("military"), label: "MIL-SAT" },
};
function setMode(mode) {
  if (!MODES[mode] || S.mode === mode) return;
  Object.values(S.timers).forEach(clearInterval); S.timers = {};
  S.layers.mode.clearLayers(); S.layers.overlay.clearLayers(); S.layers.sats.clearLayers();
  if (S.obsMarker) { S.obsMarker.remove(); S.obsMarker = null; }
  if (S.gibs) { S.map.removeLayer(S.gibs); S.gibs = null; }
  if (S.lights) { S.map.removeLayer(S.lights); S.lights = null; }
  S.mode = mode; S.selected = null; S.sats = []; S.satGroup = null;
  $("#map-ctl").innerHTML = ""; $("#map-side").innerHTML = ""; $("#b-map").className = "badge"; $("#b-map").textContent = "…";
  document.querySelectorAll("#modes button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  try { localStorage.setItem("imx-mode", mode); } catch {}
  MODES[mode].enter();
}

/* --------------------------------------------- ECON: IMF WEO choropleth */
const ECON_IND = {
  NGDP_RPCH: { label: "Real GDP growth, %", div: true, mid: 0, lo: -4, hi: 8, highGood: true },
  PCPIPCH: { label: "Inflation, %", div: true, mid: 3, lo: -1, hi: 12, highGood: false },
  BCA_NGDPD: { label: "Current account, % of GDP", div: true, mid: 0, lo: -10, hi: 10, highGood: true },
  GGXCNL_NGDP: { label: "Govt net lending, % of GDP", div: true, mid: 0, lo: -10, hi: 5, highGood: true },
  GGXWDG_NGDP: { label: "Govt gross debt, % of GDP", div: false, lo: 0, hi: 150 },
  LUR: { label: "Unemployment, %", div: false, lo: 0, hi: 20 },
  PPPPC: { label: "GDP per capita, PPP int'l $", div: false, lo: 1000, hi: 100000, log: true },
  PPPSH: { label: "Share of world GDP (PPP), %", div: false, lo: 0, hi: 10 },
};
const hex2rgb = (x) => [1, 3, 5].map((i) => parseInt(x.slice(i, i + 2), 16));
const mix = (a, b, t) => { const A = hex2rgb(a), B = hex2rgb(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(",")})`; };
const SEQ = ["#16202c", "#184f95", "#3987e5", "#9ec5f4"];
const DIV_GOOD = "#3987e5", DIV_BAD = "#e66767", DIV_MID = "#383835";
function econColor(cfg, v) {
  if (v === null || v === undefined) return null;
  if (cfg.div) {
    const t = v >= cfg.mid ? Math.min(1, (v - cfg.mid) / (cfg.hi - cfg.mid)) : -Math.min(1, (cfg.mid - v) / (cfg.mid - cfg.lo));
    const good = (t >= 0) === cfg.highGood;
    return mix(DIV_MID, good ? DIV_GOOD : DIV_BAD, Math.abs(t));
  }
  let t = cfg.log ? (Math.log(Math.max(v, cfg.lo)) - Math.log(cfg.lo)) / (Math.log(cfg.hi) - Math.log(cfg.lo)) : (v - cfg.lo) / (cfg.hi - cfg.lo);
  t = Math.max(0, Math.min(1, t)) * (SEQ.length - 1);
  const i = Math.min(SEQ.length - 2, Math.floor(t));
  return mix(SEQ[i], SEQ[i + 1], t - i);
}
function rampCss(cfg) {
  if (cfg.div) {
    const lo = cfg.highGood ? DIV_BAD : DIV_GOOD, hi = cfg.highGood ? DIV_GOOD : DIV_BAD;
    const m = (cfg.mid - cfg.lo) / (cfg.hi - cfg.lo) * 100;
    return `linear-gradient(90deg, ${lo}, ${DIV_MID} ${m}%, ${hi})`;
  }
  return `linear-gradient(90deg, ${SEQ.join(",")})`;
}
async function enterEcon() {
  const yr = new Date().getFullYear();
  const ctl = $("#map-ctl");
  ctl.append(h("span", { class: "t" }, "IMF WORLD ECONOMIC OUTLOOK"),
    h("label", {}, "Indicator", h("select", { id: "econ-ind", onchange: drawEcon },
      ...Object.entries(ECON_IND).map(([k, c]) => h("option", { value: k }, c.label)))),
    h("label", {}, "Year", h("input", { id: "econ-year", type: "number", min: 1980, max: yr + 5, value: yr, onchange: drawEcon })),
    h("div", { id: "econ-ramp" }),
    h("label", {}, h("input", { type: "checkbox", id: "econ-lights", onchange: drawEconOverlays }), "Night lights (VIIRS 2016)"),
    h("label", {}, h("input", { type: "checkbox", id: "econ-choke", checked: true, onchange: drawEconOverlays }), "Shipping chokepoints"),
    h("div", { class: "note" }, "Years after a country's latest actual data are IMF projections. Night lights are a rough activity proxy (NASA Black Marble)."));
  if (!S.world) S.world = await api("api/live/world.geojson").catch(() => null);
  drawEcon(); drawEconOverlays();
}
async function drawEcon() {
  if (S.mode !== "econ") return;
  const ind = $("#econ-ind").value, year = $("#econ-year").value, cfg = ECON_IND[ind];
  let env;
  try { env = await api(`api/live/econ?indicator=${ind}&year=${year}`); } catch (e) { return badge($("#b-map"), null); }
  badge($("#b-map"), env);
  const vals = env.data.values || {};
  S.layers.mode.clearLayers();
  if (S.world) {
    L.geoJSON(S.world, {
      renderer: S.choroRenderer, pane: "choro",
      style: (f) => {
        const iso = f.properties.ISO_A3 !== "-99" ? f.properties.ISO_A3 : f.properties.ADM0_A3;
        const c = econColor(cfg, vals[iso]);
        return { pane: "choro", color: iso === "IND" ? "#ffa028" : "#000", weight: iso === "IND" ? 1.6 : 0.4, fillColor: c || "#15171b", fillOpacity: c ? 0.85 : 0.6 };
      },
      onEachFeature: (f, layer) => {
        const iso = f.properties.ISO_A3 !== "-99" ? f.properties.ISO_A3 : f.properties.ADM0_A3;
        const v = vals[iso];
        layer.bindTooltip(`<b>${esc(f.properties.NAME)}</b> ${v == null ? "no data" : smart(v)} <span style="color:#6c717b">${year}</span>`, { sticky: true });
        layer.on("click", () => runCommand(`CMP ${econKey(ind)} ${iso === "IND" ? "BRICS" : "IND," + iso}`));
      },
    }).addTo(S.layers.mode);
  }
  $("#econ-ramp").innerHTML = `<div class="ramp" style="background:${rampCss(cfg)}"></div><div class="ramp-l"><span>${cfg.lo}${cfg.log ? "" : ""}</span>${cfg.div ? `<span>${cfg.mid}</span>` : ""}<span>${cfg.hi}+</span></div>`;
  const ranked = Object.entries(vals).filter(([c]) => c.length === 3).sort((a, b) => b[1] - a[1]);
  const india = ranked.findIndex(([c]) => c === "IND");
  const nm = (iso) => (S.world?.features.find((f) => f.properties.ISO_A3 === iso || f.properties.ADM0_A3 === iso)?.properties.NAME) || iso;
  const row = ([c, v], i) => `<tr class="click" data-iso="${c}"><td>${i}</td><td>${esc(nm(c))}</td><td style="text-align:right">${smart(v)}</td></tr>`;
  $("#map-side").innerHTML = `<div class="t">${esc(cfg.label.toUpperCase())} · ${year}</div>
    <div class="note">India: <b style="color:var(--amber)">${india >= 0 ? smart(ranked[india][1]) : "n/a"}</b> — rank ${india + 1} of ${ranked.length} economies</div>
    <table><tr><th>#</th><th>Top 5</th><th></th></tr>${ranked.slice(0, 5).map((r, i) => row(r, i + 1)).join("")}
    <tr><th>#</th><th>Bottom 5</th><th></th></tr>${ranked.slice(-5).map((r, i) => row(r, ranked.length - 4 + i)).join("")}</table>
    <div class="note">Click a country to compare it with India over time.</div>`;
  $("#map-side").querySelectorAll("tr.click").forEach((tr) => tr.onclick = () => runCommand(`CMP ${econKey(ind)} IND,${tr.dataset.iso}`));
}
const econKey = (ind) => ({ NGDP_RPCH: "gdp_growth", PCPIPCH: "inflation", BCA_NGDPD: "current_account", GGXCNL_NGDP: "fiscal_balance",
  GGXWDG_NGDP: "govt_debt", LUR: "unemployment", PPPPC: "gdp_per_capita_ppp", PPPSH: "share_world_gdp_ppp" }[ind] || ind);
function drawEconOverlays() {
  if (S.mode !== "econ") return;
  S.layers.overlay.clearLayers();
  if (S.lights) { S.map.removeLayer(S.lights); S.lights = null; }
  if ($("#econ-lights")?.checked) S.lights = gibsLayer("VIIRS_Black_Marble", "2016-01-01", 8, "png", 0.9).addTo(S.map);
  if ($("#econ-choke")?.checked) drawChokepoints(S.layers.overlay);
}

/* --------------------------------------------- shipping chokepoints (shared by ECON and TRAFFIC) */
function drawChokepoints(layer) {
  const env = S.feeds.choke;
  if (!env) return;
  for (const c of env.data) {
    if (c.lat == null) continue;
    const dev = c.avg365 ? (c.last7 / c.avg365 - 1) * 100 : 0;
    const col = dev <= -15 ? "#e66767" : dev >= 15 ? "#3987e5" : "#a9adb5";
    L.circleMarker([c.lat, c.lon], { radius: 5 + Math.sqrt(c.last7 || 1) * 0.9, color: "#000", weight: 1, fillColor: col, fillOpacity: 0.85, renderer: S.canvas })
      .bindPopup(`<b>${esc(c.name)}</b><br>${num(c.last7, 0)} vessels/day (7-day avg to ${c.date})<br>1-year avg ${num(c.avg365, 0)} (${dev >= 0 ? "+" : ""}${num(dev, 0)}%)<br>tankers ${num(c.tanker7, 0)}/day${c.tanker365 ? ` vs ${num(c.tanker365, 0)}` : ""}<br><span style="color:#6c717b">${esc(env.source)}</span>`)
      .bindTooltip(`${c.name} ${dev >= 0 ? "+" : ""}${num(dev, 0)}%`)
      .addTo(layer);
  }
}

/* --------------------------------------------- TRAFFIC: aircraft + ships */
function enterTraffic() {
  $("#map-ctl").append(h("span", { class: "t" }, "LIVE AIR TRAFFIC + SEA LANES"),
    h("label", {}, h("input", { type: "checkbox", id: "tr-air", checked: true, onchange: () => scheduleAircraft(0) }), "Aircraft (OpenSky ADS-B, current view)"),
    h("label", {}, h("input", { type: "checkbox", id: "tr-ship", checked: true, onchange: drawTraffic }), "Chokepoint transits (PortWatch)"),
    h("div", { class: "note" }, "Aircraft refresh every 30 s for the visible area (large views are trimmed to save the free API quota). Ship counts are daily AIS transits, about a week behind."));
  if (S.map.getZoom() < 4) S.map.setView([22, 78], 5);
  scheduleAircraft(0);
  S.timers.air = setInterval(() => scheduleAircraft(0), 30000);
  drawTraffic();
}
let airTimeout = null;
function scheduleAircraft(ms) { clearTimeout(airTimeout); airTimeout = setTimeout(loadAircraft, ms); }
async function loadAircraft() {
  if (S.mode !== "traffic") return;
  if (!$("#tr-air").checked) { S.feeds.air = null; return drawTraffic(); }
  const b = S.map.getBounds();
  const bbox = [Math.max(-85, b.getSouth()), wrapLon(b.getWest()), Math.min(85, b.getNorth()), wrapLon(b.getEast())];
  if (bbox[3] < bbox[1] || b.getEast() - b.getWest() >= 360) { bbox[1] = -180; bbox[3] = 180; }
  try { S.feeds.air = await api(`api/live/aircraft?bbox=${bbox.map((x) => x.toFixed(1)).join(",")}`); } catch { S.feeds.air = null; }
  drawTraffic();
}
function drawTraffic() {
  if (S.mode !== "traffic") return;
  S.layers.mode.clearLayers();
  const env = S.feeds.air;
  if (env) {
    badge($("#b-map"), env);
    const icon = (trk, ground) => L.divIcon({ className: "", iconSize: [12, 12],
      html: `<div class="plane" style="transform:rotate(${(trk || 0) - 90}deg);opacity:${ground ? .45 : 1}">➤</div>` });
    for (const a of env.data)
      L.marker([a.lat, a.lon], { icon: icon(a.track, a.ground), keyboard: false })
        .bindTooltip(`<b>${esc(a.callsign || a.icao24)}</b> ${esc(a.country)}<br>${a.alt != null ? num(a.alt, 0) + " m" : "–"} · ${a.vel != null ? num(a.vel * 3.6, 0) + " km/h" : "–"}`)
        .addTo(S.layers.mode);
    const byCountry = {};
    env.data.forEach((a) => byCountry[a.country] = (byCountry[a.country] || 0) + 1);
    const top = Object.entries(byCountry).sort((a, b) => b[1] - a[1]).slice(0, 10);
    $("#map-side").innerHTML = `<div class="t">AIRCRAFT IN VIEW: ${env.data.length}${env.status === "sim" ? ' <span class="sim">SIM</span>' : ""}</div>
      <table><tr><th>Registration country</th><th>n</th></tr>${top.map(([c, n]) => `<tr><td>${esc(c)}</td><td>${n}</td></tr>`).join("")}</table>
      <div class="note">${esc(env.source)} · ${env.asof}. ADS-B coverage is volunteer-run and thin over oceans and parts of Asia/Africa, so counts are a floor.</div>`;
  }
  if ($("#tr-ship")?.checked) drawChokepoints(S.layers.mode);
}

/* --------------------------------------------- CLIMATE: NASA GIBS imagery, quakes, hazards, air quality */
const GIBS = {
  none: null,
  truecolor: ["MODIS_Terra_CorrectedReflectance_TrueColor", 9, "jpg", "MODIS Terra true colour (clouds, smoke, dust)"],
  lst: ["MODIS_Terra_Land_Surface_Temp_Day", 7, "png", "Land surface temperature, day (MODIS Terra)"],
  rain: ["IMERG_Precipitation_Rate", 6, "png", "Precipitation rate (GPM IMERG)"],
  aod: ["MODIS_Combined_Value_Added_AOD", 6, "png", "Aerosol optical depth (haze, smoke, dust)"],
  lights: ["VIIRS_Black_Marble", 8, "png", "Night lights 2016 (VIIRS Black Marble)"],
};
function gibsLayer(layer, date, lvl, ext, opacity = 0.75) {
  return L.tileLayer(`https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/${date}/GoogleMapsCompatible_Level${lvl}/{z}/{y}/{x}.${ext}`,
    { maxNativeZoom: lvl, maxZoom: 18, opacity, attribution: "Imagery: NASA GIBS / EOSDIS" });
}
function enterClimate() {
  const yday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
  $("#map-ctl").append(h("span", { class: "t" }, "EARTH OBSERVATION"),
    h("label", {}, "Imagery", h("select", { id: "cl-gibs", onchange: setGibs },
      ...Object.entries(GIBS).map(([k, v]) => h("option", { value: k, selected: k === "aod" ? "" : null }, v ? v[3] : "None")))),
    h("label", {}, "Date", h("input", { id: "cl-date", type: "date", value: yday, max: yday, onchange: setGibs })),
    h("label", {}, h("input", { type: "checkbox", id: "cl-q", checked: true, onchange: drawClimate }), "Earthquakes M4.5+ (7 days, USGS)"),
    h("label", {}, h("input", { type: "checkbox", id: "cl-e", checked: true, onchange: drawClimate }), "Natural hazards (NASA EONET)"),
    h("label", {}, h("input", { type: "checkbox", id: "cl-w", checked: true, onchange: drawClimate }), "City weather + PM2.5 (Open-Meteo/CAMS)"),
    h("div", { class: "note" }, "Satellite imagery is daily with gaps (swaths, clouds); try the previous day if tiles look empty. PM2.5 is a model estimate, not a station reading."));
  setGibs(); drawClimate();
}
function setGibs() {
  if (S.gibs) { S.map.removeLayer(S.gibs); S.gibs = null; }
  const g = GIBS[$("#cl-gibs").value];
  if (g) S.gibs = gibsLayer(g[0], g[0] === "VIIRS_Black_Marble" ? "2016-01-01" : $("#cl-date").value, g[1], g[2]).addTo(S.map);
}
const EV_ICON = { Wildfires: "🔥", "Severe Storms": "🌀", Volcanoes: "🌋", "Sea and Lake Ice": "🧊", Floods: "🌊", Earthquakes: "⚠", Landslides: "⛰", Drought: "☀", "Dust and Haze": "🌫", Snow: "❄", "Temperature Extremes": "🌡", Manmade: "🏭", "Water Color": "💧" };
const pmColor = (v) => v == null ? GRAY : v <= 15 ? "#0ca30c" : v <= 35 ? "#fab219" : v <= 75 ? "#ec835a" : "#d03b3b";
const pmLabel = (v) => v == null ? "n/a" : v <= 15 ? "good" : v <= 35 ? "moderate" : v <= 75 ? "unhealthy" : "hazardous";
function drawClimate() {
  if (S.mode !== "climate") return;
  S.layers.mode.clearLayers();
  const envs = [];
  if ($("#cl-q").checked && S.feeds.quakes) {
    envs.push(S.feeds.quakes);
    for (const q of S.feeds.quakes.data)
      L.circleMarker([q.lat, q.lon], { radius: Math.max(3, (q.mag - 3.5) * 3.2), color: "#e66767", weight: 1, fillColor: "#e66767",
        fillOpacity: Math.max(0.15, 0.7 - (Date.now() - q.time) / 6.048e8 * 0.55), renderer: S.canvas })
        .bindPopup(`<b>M${q.mag}</b> ${esc(q.place)}<br>depth ${num(q.depth, 0)} km · ${new Date(q.time).toUTCString()}${q.url ? `<br><a href="${esc(q.url)}" target="_blank" rel="noopener">USGS event page</a>` : ""}`)
        .addTo(S.layers.mode);
  }
  if ($("#cl-e").checked && S.feeds.events) {
    envs.push(S.feeds.events);
    for (const e of S.feeds.events.data) {
      if (e.track && e.track.length > 1) L.polyline(e.track.filter(Boolean), { color: "#c98500", weight: 1.5, dashArray: "3 3", interactive: false }).addTo(S.layers.mode);
      L.marker([e.lat, e.lon], { icon: L.divIcon({ className: "", iconSize: [14, 14], html: `<div class="ev-ico">${EV_ICON[e.category] || "●"}</div>` }) })
        .bindPopup(`<b>${esc(e.title)}</b><br>${esc(e.category)} · ${esc((e.date || "").slice(0, 16))}${e.link ? `<br><a href="${esc(e.link)}" target="_blank" rel="noopener">source</a>` : ""}`)
        .addTo(S.layers.mode);
    }
  }
  if ($("#cl-w").checked && S.feeds.weather) {
    envs.push(S.feeds.weather);
    for (const w of S.feeds.weather.data)
      L.circleMarker([w.lat, w.lon], { radius: 6, color: "#000", weight: 1, fillColor: pmColor(w.pm25), fillOpacity: 0.95, renderer: S.canvas })
        .bindTooltip(`<b>${esc(w.city)}</b> ${num(w.temp, 1)}°C · RH ${w.humidity ?? "–"}% · wind ${num(w.wind, 0)} km/h<br>PM2.5 ${num(w.pm25, 0)} µg/m³ (${pmLabel(w.pm25)})${w.aqi != null ? ` · US AQI ${w.aqi}` : ""}`)
        .addTo(S.layers.mode);
  }
  const sim = envs.find((e) => e.status === "sim");
  badge($("#b-map"), sim || envs[0]);
  const worst = (S.feeds.weather?.data || []).filter((w) => w.pm25 != null).sort((a, b) => b.pm25 - a.pm25).slice(0, 6);
  const quakes = (S.feeds.quakes?.data || []).slice().sort((a, b) => b.mag - a.mag).slice(0, 4);
  const cats = {}; (S.feeds.events?.data || []).forEach((e) => cats[e.category] = (cats[e.category] || 0) + 1);
  $("#map-side").innerHTML = `<div class="t">AIR QUALITY — WORST TRACKED CITIES</div>
    <table>${worst.map((w) => `<tr><td><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${pmColor(w.pm25)}"></i> ${esc(w.city)}</td><td>${num(w.pm25, 0)} µg/m³</td><td>${pmLabel(w.pm25)}</td></tr>`).join("")}</table>
    <div class="t" style="margin-top:6px">LARGEST QUAKES · 7 DAYS</div>
    <table>${quakes.map((q) => `<tr class="click" data-ll="${q.lat},${q.lon}"><td>M${q.mag}</td><td>${esc((q.place || "").slice(0, 38))}</td><td>${ago(q.time)}</td></tr>`).join("")}</table>
    <div class="t" style="margin-top:6px">OPEN HAZARDS</div><div class="legend">${Object.entries(cats).map(([c, n]) => `<span>${EV_ICON[c] || "●"} ${esc(c)} ${n}</span>`).join("")}</div>`;
  $("#map-side").querySelectorAll("tr.click").forEach((tr) => tr.onclick = () => S.map.flyTo(tr.dataset.ll.split(",").map(Number), 6));
}

/* --------------------------------------------- satellites (GNSS, MIL, stations) */
const GNSS_COL = { GPS: CAT[0], BeiDou: CAT[1], NavIC: CAT[2], Galileo: CAT[3], QZSS: CAT[6], GLONASS: CAT[7], "SBAS/other": GRAY, Simulated: CAT[4] };
const MIL_COUNTRY = (tag) => /^US|^USA/.test(tag) ? "United States" : /^China/.test(tag) ? "China" : /^India/.test(tag) ? "India"
  : /^Russia/.test(tag) ? "Russia" : /^Israel/.test(tag) ? "Israel" : /^Japan/.test(tag) ? "Japan" : /^Germany/.test(tag) ? "Germany" : "Other / mixed";
const MIL_COL = { "United States": CAT[0], China: CAT[7], India: CAT[2], Russia: CAT[1], Israel: CAT[3], Japan: CAT[4], Germany: CAT[6], "Other / mixed": GRAY, Simulated: CAT[4] };
const REGIONS = {
  India: [6, 68, 36, 98], "Taiwan Strait": [21, 115, 27, 124], "Persian Gulf / Hormuz": [23, 47, 31, 58], Ukraine: [44, 22, 53, 41],
  "Korean Peninsula": [33, 124, 43, 131], "Red Sea": [12, 32, 30, 44], "South China Sea": [4, 105, 23, 121], "Kashmir / LoC": [32, 72, 37, 80],
};
function satColor(s) {
  if (S.satGroup === "gnss") return GNSS_COL[s.tag] || GRAY;
  if (S.satGroup === "military") return MIL_COL[s.tag === "Simulated" ? "Simulated" : MIL_COUNTRY(s.tag)];
  return CAT[0];
}
function satPos(s, date) {
  if (s.rec) {
    const pv = satellite.propagate(s.rec, date);
    if (!pv || !pv.position) return null;
    const gmst = satellite.gstime(date);
    const gd = satellite.eciToGeodetic(pv.position, gmst);
    return { lat: satellite.degreesLat(gd.latitude), lon: satellite.degreesLong(gd.longitude), alt: gd.height, ecf: satellite.eciToEcf(pv.position, gmst) };
  }
  const o = s.sim, a = RE + o.alt_km, T = 2 * Math.PI * Math.sqrt(a ** 3 / 398600.4418);
  const u = (o.ma * D2R + 2 * Math.PI * (date / 1000 % 1e7) / T), i = o.inc * D2R;
  const lat = Math.asin(Math.sin(i) * Math.sin(u)) * R2D;
  const lon = wrapLon((Math.atan2(Math.cos(i) * Math.sin(u), Math.cos(u)) * R2D + o.raan - 360 * (date / 1000 % 86164) / 86164));
  const la = lat * D2R, lo = lon * D2R;
  return { lat, lon, alt: o.alt_km, ecf: { x: a * Math.cos(la) * Math.cos(lo), y: a * Math.cos(la) * Math.sin(lo), z: a * Math.sin(la) } };
}
function lookElev(p) {
  const o = S.observer;
  return satellite.ecfToLookAngles({ latitude: o.lat * D2R, longitude: o.lon * D2R, height: 0.2 }, p.ecf).elevation * R2D;
}
async function loadSats(group) {
  const env = await api(`api/live/satellites?group=${group}`);
  S.satGroup = group;
  S.sats = env.data.map((s) => {
    let rec = null;
    try { if (s.l1) rec = satellite.twoline2satrec(s.l1, s.l2); } catch {}
    return { ...s, rec };
  }).filter((s) => s.rec || s.sim);
  S.satEnv = env;
  badge($("#b-map"), env);
  S.satMarkers = new Map();
  for (const s of S.sats) {
    const m = L.circleMarker([0, 0], { radius: 3.5, color: "#000", weight: 0.6, fillColor: satColor(s), fillOpacity: 0.95, renderer: S.canvas })
      .bindTooltip(() => satTip(s)).on("click", (e) => { L.DomEvent.stopPropagation(e); selectSat(s); });
    S.satMarkers.set(s.norad, m);
  }
}
function satTip(s) {
  const p = s.pos;
  return `<b>${esc(s.name)}</b> #${s.norad}<br>${esc(s.tag)}<br>${p ? `${num(p.lat, 2)}°, ${num(p.lon, 2)}° · ${num(p.alt, 0)} km` : ""}${s.elev != null ? `<br>elev from ${esc(S.observer.name)}: ${num(s.elev, 1)}°` : ""}`;
}
function selectSat(s) {
  S.selected = s;
  S.layers.overlay.clearLayers();
  const now = Date.now();
  const period = s.rec ? 2 * Math.PI / s.rec.no : 100;          // minutes
  const span = Math.min(period, 720), step = Math.max(0.5, span / 240);
  let seg = [], prev = null;
  const segs = [];
  for (let m = -span / 2; m <= span; m += step) {
    const p = satPos(s, new Date(now + m * 60000));
    if (!p) continue;
    if (prev !== null && Math.abs(p.lon - prev) > 180) { segs.push(seg); seg = []; }
    seg.push([p.lat, p.lon]); prev = p.lon;
  }
  segs.push(seg);
  segs.forEach((g) => L.polyline(g, { color: satColor(s), weight: 1.5, opacity: 0.8, interactive: false }).addTo(S.layers.overlay));
  const p = satPos(s, new Date());
  if (p) {
    const radius = RE * Math.acos(RE / (RE + p.alt)) * 1000;
    L.circle([p.lat, p.lon], { radius, color: satColor(s), weight: 1, fillOpacity: 0.06, interactive: false }).addTo(S.layers.overlay);
  }
  toast(`${s.name}: ground track ±${Math.round(span / 2)} min, circle = horizon footprint`);
}
function addObserver() {
  if (S.obsMarker) S.obsMarker.remove();
  S.obsMarker = L.marker([S.observer.lat, S.observer.lon], { icon: L.divIcon({ className: "", iconSize: [12, 12], html: '<div style="color:#ffa028;font-size:14px;line-height:12px">⌖</div>' }) })
    .bindTooltip(`Observer: ${esc(S.observer.name)} (click map to move)`).addTo(S.map);
}
async function enterSats(group) {
  const ctl = $("#map-ctl");
  if (group === "gnss") ctl.append(h("span", { class: "t" }, "GNSS CONSTELLATIONS"),
    h("div", { class: "legend" }, ...Object.entries(GNSS_COL).filter(([k]) => k !== "Simulated").map(([k, c]) => h("span", {}, h("i", { style: `background:${c}` }), k))),
    h("div", { class: "note" }, "Positions propagated in your browser with SGP4 from CelesTrak elements (refreshed every 2 h). Click a satellite for its ground track; click the map to move the observer."));
  else ctl.append(h("span", { class: "t" }, "MILITARY & RECONNAISSANCE SATELLITES"),
    h("div", { class: "legend" }, ...Object.entries(MIL_COL).filter(([k]) => k !== "Simulated").map(([k, c]) => h("span", {}, h("i", { style: `background:${c}` }), k))),
    h("label", {}, "Overflight watch", h("select", { id: "mil-region", onchange: () => satTick(true) }, ...Object.keys(REGIONS).map((r) => h("option", {}, r)))),
    h("div", { class: "note" }, "Only objects in the public catalogue (CelesTrak name/group queries). Classified payloads are absent and some elements are deliberately stale, so treat passes as indicative."));
  try { await loadSats(group); } catch (e) { badge($("#b-map"), null); return toast("satellite elements unavailable: " + e.message); }
  if (S.mode !== (group === "gnss" ? "gnss" : "mil")) return;
  S.satMarkers.forEach((m) => m.addTo(S.layers.sats));
  addObserver();
  satTick(true);
  S.timers.sat = setInterval(() => satTick(false), 2000);
}
let lastSide = 0;
function satTick(forceSide) {
  if (!S.sats.length) return;
  const now = new Date();
  for (const s of S.sats) {
    const p = satPos(s, now);
    s.pos = p;
    if (!p) continue;
    s.elev = lookElev(p);
    const m = S.satMarkers.get(s.norad);
    if (m) {
      m.setLatLng([p.lat, p.lon]);
      if (S.satGroup === "gnss") m.setStyle({ radius: s.elev > 10 ? 5 : 3, fillOpacity: s.elev > 10 ? 1 : 0.45 });
    }
  }
  if (!forceSide && Date.now() - lastSide < (S.satGroup === "military" ? 60000 : 5000)) return;
  lastSide = Date.now();
  if (forceSide) addObserver();
  if (S.satGroup === "gnss") gnssSide(); else if (S.satGroup === "military") milSide(now);
  else if (S.satGroup === "stations") astroSide();
}
function gnssSide() {
  const by = {};
  for (const s of S.sats) {
    const b = by[s.tag] ||= { total: 0, vis: 0, best: [] };
    b.total++;
    if (s.elev > 10) { b.vis++; b.best.push(s.elev); }
  }
  const order = ["GPS", "GLONASS", "Galileo", "BeiDou", "NavIC", "QZSS", "SBAS/other", "Simulated"].filter((k) => by[k]);
  const vis = order.reduce((a, k) => a + by[k].vis, 0);
  $("#map-side").innerHTML = `<div class="t">SKY OVER ${esc(S.observer.name.toUpperCase())} · ELEVATION &gt; 10°</div>
    <table><tr><th>System</th><th>in view</th><th>tracked</th></tr>${order.map((k) => `<tr><td><i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${GNSS_COL[k] || GRAY}"></i> ${k}</td><td>${by[k].vis}</td><td>${by[k].total}</td></tr>`).join("")}
    <tr><td><b>All</b></td><td><b>${vis}</b></td><td>${S.sats.length}</td></tr></table>
    <div class="note">A receiver needs 4+ satellites for a fix; more systems in view = better geometry. NavIC (India's IRNSS) is regional: its geosynchronous satellites only serve ~1,500 km around India. "Tracked" includes spares and satellites not currently healthy.</div>`;
}
function milSide(now) {
  const box = REGIONS[$("#mil-region")?.value || "India"];
  const inBox = (p) => p && p.lat >= box[0] && p.lat <= box[2] && p.lon >= box[1] && p.lon <= box[3];
  const passes = [];
  for (const s of S.sats) {
    for (let m = 0; m <= 60; m += 1) {
      const p = m === 0 ? s.pos : satPos(s, new Date(now.getTime() + m * 60000));
      if (inBox(p)) { passes.push({ s, m, alt: p.alt }); break; }
    }
  }
  passes.sort((a, b) => a.m - b.m);
  const over = passes.filter((p) => p.m === 0).length;
  $("#map-side").innerHTML = `<div class="t">OVERFLIGHT WATCH · ${esc($("#mil-region")?.value || "India")} · NEXT 60 MIN</div>
    <div class="note">${over} catalogued military/recon objects over the box now; ${passes.length} enter it within an hour (subpoint inside the box; sensor reach is wider).</div>
    <table><tr><th>T+min</th><th>Object</th><th>Programme</th><th>alt km</th></tr>${passes.slice(0, 40).map((p) =>
      `<tr class="click" data-n="${p.s.norad}"><td>${p.m === 0 ? "NOW" : "+" + p.m}</td><td>${esc(p.s.name)}</td><td style="color:${satColor(p.s)}" title="${esc(p.s.tag)}">${esc(p.s.tag.replace(/\s*\(.*$/, "").slice(0, 24))}</td><td>${num(p.alt, 0)}</td></tr>`).join("")}</table>`;
  $("#map-side").querySelectorAll("tr.click").forEach((tr) => tr.onclick = () => {
    const s = S.sats.find((x) => x.norad === +tr.dataset.n); if (s) { selectSat(s); if (s.pos) S.map.panTo([s.pos.lat, s.pos.lon]); }
  });
}

/* --------------------------------------------- ASTRO: sun, moon, twilight, space stations */
async function enterAstro() {
  $("#map-ctl").append(h("span", { class: "t" }, "SKY & SPACE STATIONS"),
    h("div", { class: "note" }, "Shaded bands: night and civil / nautical / astronomical twilight. ☀ and ☾ mark where the Sun and Moon are overhead. Stations (ISS, Tiangong and visiting craft) from CelesTrak, propagated live. Click the map to move the observer."));
  if (!$("#opt-night").checked) { $("#opt-night").checked = true; drawNight(); }
  drawAstro();
  try {
    await loadSats("stations");
    if (S.mode !== "astro") return;
    S.satMarkers.forEach((m) => m.setRadius(5).addTo(S.layers.sats));
    const iss = S.sats.find((s) => /ISS \(ZARYA\)/.test(s.name));
    if (iss) selectSat(iss);
    satTick(true);
    S.timers.sat = setInterval(() => satTick(false), 2000);
  } catch (e) { toast("station elements unavailable"); }
  S.timers.astro = setInterval(drawAstro, 30000);
}
function drawAstro() {
  if (S.mode !== "astro") return;
  S.layers.mode.clearLayers();
  const sm = sunMoon();
  const mk = (p, sym, tip) => L.marker([p.lat, p.lon], { icon: L.divIcon({ className: "", iconSize: [18, 18], html: `<div class="sunmoon">${sym}</div>` }) }).bindTooltip(tip).addTo(S.layers.mode);
  mk(sm.sun, "☀", `Sub-solar point ${num(sm.sun.lat, 1)}°, ${num(sm.sun.lon, 1)}°`);
  mk(sm.moon, "☾", `Sub-lunar point ${num(sm.moon.lat, 1)}°, ${num(sm.moon.lon, 1)}° · ${num(sm.illum * 100, 0)}% lit`);
  addObserver();
  if (!S.satEnv) $("#b-map").className = "badge live", $("#b-map").textContent = "CALC";
  astroSide();
}
function astroSide() {
  if (S.mode !== "astro") return;
  const sm = sunMoon(), o = S.observer;
  const sunEl = elevation(sm.sun, o.lat, o.lon), moonEl = elevation(sm.moon, o.lat, o.lon);
  const phase = sm.illum < 0.03 ? "New moon" : sm.illum > 0.97 ? "Full moon" : `${sm.waxing ? "Waxing" : "Waning"} ${sm.illum < 0.5 ? "crescent" : "gibbous"}`;
  const sky = sunEl > 0 ? "Day" : sunEl > -6 ? "Civil twilight" : sunEl > -12 ? "Nautical twilight" : sunEl > -18 ? "Astronomical twilight" : "Night (dark sky)";
  const stations = S.sats.filter((s) => s.pos).map((s) => `<tr class="click" data-n="${s.norad}"><td>${esc(s.name)}</td><td>${num(s.pos.alt, 0)} km</td><td>${num(s.elev, 0)}°${s.elev > 10 ? " ▲" : ""}</td></tr>`).join("");
  $("#map-side").innerHTML = `<div class="t">SKY AT ${esc(o.name.toUpperCase())}</div>
    <table><tr><td>Sky</td><td>${sky}</td></tr><tr><td>Sun elevation</td><td>${num(sunEl, 1)}°</td></tr>
    <tr><td>Moon elevation</td><td>${num(moonEl, 1)}°</td></tr><tr><td>Moon phase</td><td>${phase}, ${num(sm.illum * 100, 0)}% lit</td></tr>
    <tr><td>Sub-solar latitude</td><td>${num(sm.sun.lat, 2)}° (declination)</td></tr></table>
    ${stations ? `<div class="t" style="margin-top:6px">CREWED STATIONS & VISITORS</div><table><tr><th>Object</th><th>alt</th><th>elev</th></tr>${stations}</table>` : ""}
    <div class="note">Low-precision formulas (~1° accuracy): good for the map, not for observing or navigation.</div>`;
  $("#map-side").querySelectorAll("tr.click").forEach((tr) => tr.onclick = () => {
    const s = S.sats.find((x) => x.norad === +tr.dataset.n); if (s) { selectSat(s); S.map.panTo([s.pos.lat, s.pos.lon]); }
  });
}

/* ================================================================== chart workspace */
function addCharts(specs, origin = "") {
  if (!specs || !specs.length) return;
  for (const sp of specs) S.charts.push({ ...sp, origin });
  while (S.charts.length > 12) S.charts.shift();
  S.activeChart = S.charts.length - specs.length;
  renderTabs(); renderChart();
}
function renderTabs() {
  const bar = $("#work-tabs");
  bar.querySelectorAll(".ctab").forEach((b) => b.remove());
  const spacer = bar.querySelector(".spacer");
  S.charts.forEach((c, i) => bar.insertBefore(h("button", { class: "ctab" + (i === S.activeChart ? " on" : ""), title: c.title,
    onclick: () => { S.activeChart = i; renderTabs(); renderChart(); } }, (c.title || "chart").slice(0, 34)), spacer));
}
function renderChart() {
  const box = $("#work");
  const c = S.charts[S.activeChart];
  if (!c) return;
  box.innerHTML = "";
  const div = h("div", { class: "chart" });
  box.append(div, h("div", { class: "src" }, `Source: ${(c.sources || []).join("; ") || "see answer"}${c.origin ? " · from: " + c.origin : ""}`));
  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)", margin: { l: 52, r: 16, t: 30, b: 30 },
    font: { family: "JetBrains Mono, monospace", size: 10.5, color: "#a9adb5" },
    title: { text: c.title, font: { size: 12, color: "#ffa028" }, x: 0.01, xanchor: "left" },
    xaxis: { gridcolor: "#1b1e23", linecolor: "#23262d", zeroline: false },
    yaxis: { gridcolor: "#1b1e23", zerolinecolor: "#3a3e46", title: { text: c.yaxis || "", font: { size: 10 } } },
    legend: { orientation: "h", y: -0.1, yanchor: "top", x: 0, xanchor: "left", font: { size: 10 } },
    hovermode: c.type === "bar" ? "closest" : "x unified", hoverlabel: { bgcolor: "#121418", bordercolor: "#23262d", font: { color: "#e6e6e6" } },
    shapes: [],
  };
  let data;
  if (c.type === "bar") {
    data = [{ type: "bar", x: c.x, y: c.y, marker: { color: c.y.map((v) => v == null ? GRAY : v >= 0 ? CAT[0] : CAT[7]) }, hovertemplate: "lag %{x}: r=%{y:.3f}<extra></extra>" }];
    if (c.band) for (const y of [c.band, -c.band]) layout.shapes.push({ type: "line", xref: "paper", x0: 0, x1: 1, y0: y, y1: y, line: { color: "#6c717b", dash: "dot", width: 1 } });
    layout.xaxis.title = { text: "lag (periods)", font: { size: 10 } };
  } else {
    data = (c.traces || []).map((t, i) => ({ type: "scatter", mode: "lines", name: t.name, x: t.x, y: t.y, line: { width: 1.8, color: CAT[i % CAT.length] } }));
    layout.showlegend = data.length > 1;
    if (layout.showlegend) layout.margin.b = 56;
    const xmax = data.flatMap((d) => d.x || []).reduce((m, x) => x > m ? x : m, "");
    if (c.shade_from && xmax > c.shade_from) layout.shapes.push({ type: "rect", xref: "x", yref: "paper", x0: c.shade_from, x1: xmax, y0: 0, y1: 1, fillcolor: "rgba(255,160,40,.06)", line: { width: 0 } });
    if (c.vline) layout.shapes.push({ type: "line", xref: "x", yref: "paper", x0: c.vline, x1: c.vline, y0: 0, y1: 1, line: { color: "#ffa028", dash: "dot", width: 1 } });
  }
  Plotly.newPlot(div, data, layout, { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] });
}

/* ================================================================== ask */
function md(text) {
  const blocks = [];
  let t = esc(text).replace(/```(?:\w+)?\n?([\s\S]*?)```/g, (_, code) => { blocks.push(`<pre>${code}</pre>`); return `\u0000${blocks.length - 1}\u0000`; });
  const inline = (s) => s.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])_([^_]+)_(?=[\s.,;:)]|$)/g, "$1<em>$2</em>").replace(/(^|[\s(])\*([^*]+)\*(?=[\s.,;:)]|$)/g, "$1<em>$2</em>");
  return t.split(/\n{2,}/).map((para) => {
    if (/^\u0000\d+\u0000$/.test(para.trim())) return para.trim();
    const lines = para.split("\n");
    if (lines.every((l) => /^\s*(&gt;)/.test(l))) return `<blockquote>${inline(lines.map((l) => l.replace(/^\s*&gt;\s?/, "")).join(" "))}</blockquote>`;
    // mixed blocks: headings, runs of list items and plain lines, in order
    let out = "", list = null, text = [];
    const flushText = () => { if (text.length) out += `<p>${inline(text.join("<br>"))}</p>`; text = []; };
    const flushList = () => { if (list) out += `<${list.tag}>${list.items.map((x) => `<li>${inline(x)}</li>`).join("")}</${list.tag}>`; list = null; };
    for (const l of lines) {
      const m = l.match(/^\s*([-*•]|\d+\.)\s+(.*)$/);
      if (m) {
        flushText();
        const tag = /\d/.test(m[1]) ? "ol" : "ul";
        if (!list || list.tag !== tag) { flushList(); list = { tag, items: [] }; }
        list.items.push(m[2]);
      } else if (/^#{1,4}\s/.test(l)) { flushText(); flushList(); out += `<p><strong>${inline(l.replace(/^#+\s/, ""))}</strong></p>`; }
      else { flushList(); text.push(l); }
    }
    flushText(); flushList();
    return out;
  }).join("").replace(/\u0000(\d+)\u0000/g, (_, i) => blocks[+i]);
}
const SUGGEST = [
  "How does the oil price relate to the rupee?", "Is food inflation leading the RBI repo rate?",
  "Compare India's GDP growth with BRICS since 2010", "What is happening right now?",
  "Show nifty and gold since 2020", "Did Red Sea transits move diesel cracks?",
];
function chatIntro() {
  $("#chat").replaceChildren(h("div", { class: "msg bot" },
    h("p", { html: "Ask the data anything: relationships, leads and lags, peers, event windows, what is moving now. Every number comes from a computed tool result; charts land in the workspace." }),
    h("div", { class: "suggest" }, ...SUGGEST.map((q) => h("button", { onclick: () => ask(q) }, q)))));
}
function context() {
  const c = S.map.getCenter();
  const q = (sym) => S.quotes[sym] ? `${S.quotes[sym].label} ${smart(S.quotes[sym].last)} (${num(S.quotes[sym].chg_pct)}%)` : "";
  return [`map mode ${MODES[S.mode]?.label}`, `center ${num(c.lat, 1)},${num(c.lng, 1)} zoom ${S.map.getZoom()}`,
    `observer ${S.observer.name}`, S.selected ? `selected satellite ${S.selected.name} (${S.selected.tag})` : "",
    S.charts[S.activeChart] ? `chart on screen: ${S.charts[S.activeChart].title}` : "",
    ["^NSEI", "INR=X", "BZ=F"].map(q).filter(Boolean).join(", ")].filter(Boolean).join("; ");
}
async function ask(question) {
  question = question.trim();
  if (!question) return;
  const chat = $("#chat");
  chat.append(h("div", { class: "msg user" }, "> " + question));
  const wait = h("div", { class: "msg thinking" }, "querying data ");
  chat.append(wait); chat.scrollTop = chat.scrollHeight;
  try {
    const r = await post("api/ask", { question, history: S.history.slice(-8), context: context() });
    wait.remove();
    S.history.push({ role: "user", content: question }, { role: "assistant", content: r.answer });
    const meta = h("div", { class: "meta" },
      h("span", {}, r.mode === "mock" ? "MOCK" : `${r.model}@${r.endpoint_host}${r.mode === "llm-grounded" ? " (grounded)" : ""}`),
      h("span", {}, `${r.elapsed}s`), ...(r.tools || []).map((t) => h("span", { title: JSON.stringify(t.args) }, "ƒ " + t.name)),
      r.sim ? h("span", { class: "sim" }, "contains SIMULATED data") : null,
      r.charts?.length ? h("a", { onclick: () => addCharts(r.charts, question) }, `▸ ${r.charts.length} chart${r.charts.length > 1 ? "s" : ""}`) : null);
    chat.append(h("div", { class: "msg bot" }, h("div", { html: md(r.answer || "(empty answer)") }),
      r.error ? h("div", { class: "meta sim" }, r.error) : null, meta));
    addCharts(r.charts, question);
  } catch (e) {
    wait.remove();
    chat.append(h("div", { class: "msg bot" }, h("p", { class: "sim" }, "Error: " + e.message)));
  }
  chat.scrollTop = chat.scrollHeight;
}
async function llmStatus() {
  try {
    const s = await api("api/ask/status");
    const el = $("#llm-status");
    el.className = "pill " + (s.mode === "mock" ? "mock" : "llm");
    el.textContent = s.mode === "mock" ? "AI: MOCK" : `AI: ${s.model}`;
    el.title = s.mode === "mock" ? "No LLM configured. Set LLM_ENDPOINT and LLM_API_KEY (and optionally LLM_MODEL) in .env, then restart." : `OpenAI-compatible endpoint at ${s.endpoint_host}`;
    $("#ask-mode").textContent = s.mode === "mock" ? "mock analyst (rules) — configure .env for an LLM" : `${s.model} @ ${s.endpoint_host}`;
  } catch {}
}

/* ================================================================== command line */
const COMMANDS = [
  ["ECON", "World economy map (IMF WEO)"], ["TRAFFIC", "Live aircraft + shipping chokepoints"], ["CLIMATE", "Satellite imagery, quakes, hazards, air quality"],
  ["GNSS", "GPS / GLONASS / Galileo / BeiDou / NavIC sky"], ["ASTRO", "Day-night, twilight, Sun, Moon, space stations"], ["MIL", "Military & recon satellites, overflight watch"],
  ["G <series…> [yoy|pct|diff|zscore|index100] [since YYYY]", "Chart and describe series"], ["CORR <a> <b> [W|M|Q]", "Lead/lag correlation"],
  ["CMP <indicator> [BRICS|G20|IND,CHN,…]", "Cross-country comparison"], ["WIN <series> <YYYY-MM-DD>", "Event window around a date"],
  ["SAT <name>", "Find a satellite in the current satellite mode"], ["GO <city | lat,lon>", "Fly the map"],
  ["LIST", "List queryable series"], ["REFRESH", "Re-fetch every feed"], ["<anything else>", "Ask the analyst"],
];
let SERIES = [];
async function tool(name, args, origin) {
  try {
    const r = await post("api/tool", { name, args });
    addCharts(r.charts, origin);
    const chat = $("#chat");
    chat.append(h("div", { class: "msg user" }, "> " + origin),
      h("div", { class: "msg bot" }, h("pre", {}, r.text), r.sim ? h("div", { class: "meta sim" }, "contains SIMULATED data") : null));
    chat.scrollTop = chat.scrollHeight;
  } catch (e) { toast(e.message); }
}
async function runCommand(raw) {
  const line = raw.trim();
  if (!line) return;
  const [head, ...rest] = line.split(/\s+/);
  const cmd = head.toUpperCase();
  const modes = { ECON: "econ", ECO: "econ", TRAFFIC: "traffic", TRF: "traffic", AIR: "traffic", CLIMATE: "climate", CLM: "climate", WX: "climate",
    GNSS: "gnss", NAV: "gnss", GPS: "gnss", NAVIC: "gnss", ASTRO: "astro", AST: "astro", SKY: "astro", MIL: "mil", SPY: "mil", MILSAT: "mil" };
  if (modes[cmd] && !rest.length) return setMode(modes[cmd]);
  if (cmd === "HELP" || cmd === "?") return showHints(true);
  if (cmd === "REFRESH") { await post("api/refresh", {}); refreshAll(); return toast("Refreshing every feed"); }
  if (cmd === "LIST") return tool("list_series", {}, line);
  if (cmd === "G" && rest.length) {
    const tr = rest.find((w) => ["yoy", "pct", "diff", "log", "zscore", "index100", "level"].includes(w.toLowerCase()));
    const si = rest.findIndex((w) => w.toLowerCase() === "since");
    const start = si >= 0 && rest[si + 1] ? `${rest[si + 1]}-01-01` : undefined;
    const names = rest.filter((w, i) => w !== tr && i !== si && i !== si + 1);
    return tool("get_series", { names, transform: (tr || "level").toLowerCase(), ...(start ? { start } : {}) }, line);
  }
  if (cmd === "CORR" && rest.length >= 2) return tool("correlate", { a: rest[0], b: rest[1], freq: (rest[2] || "M").toUpperCase() }, line);
  if (cmd === "CMP" && rest.length) return tool("compare_countries", { indicator: rest[0], countries: rest[1] || "BRICS" }, line);
  if (cmd === "WIN" && rest.length >= 2) return tool("window", { series: rest[0], date: rest[1] }, line);
  if (cmd === "GO" && rest.length) {
    const ll = rest.join(" ").split(",").map(Number);
    if (ll.length === 2 && ll.every(isFinite)) return S.map.flyTo(ll, 7);
    const c = (S.feeds.weather?.data || []).find((w) => w.city.toLowerCase().startsWith(rest.join(" ").toLowerCase()));
    if (c) return S.map.flyTo([c.lat, c.lon], 8);
    return toast("Unknown place; use GO lat,lon");
  }
  if (cmd === "SAT" && rest.length) {
    const q = rest.join(" ").toLowerCase();
    const s = S.sats.find((x) => x.name.toLowerCase().includes(q));
    if (!s) return toast(S.sats.length ? "No satellite matches" : "Open GNSS, ASTRO or MIL first");
    selectSat(s); if (s.pos) S.map.flyTo([s.pos.lat, s.pos.lon], 4);
    return;
  }
  return ask(line);
}
function showHints(force) {
  const box = $("#cmd-hints"), v = $("#cmd").value.trim().toUpperCase();
  const items = COMMANDS.filter(([c]) => !v || c.startsWith(v.split(" ")[0]) || force);
  const seriesHits = v.length >= 2 ? SERIES.filter((s) => s.key.toUpperCase().includes(v.split(" ").pop()) && v.includes(" ")).slice(0, 8) : [];
  if (!items.length && !seriesHits.length) { box.hidden = true; return; }
  box.replaceChildren(...items.map(([c, d]) => h("div", { onmousedown: (e) => { e.preventDefault(); $("#cmd").value = c.replace(/\s.*$/, "") + (c.includes(" ") ? " " : ""); $("#cmd").focus(); showHints(); } }, h("b", {}, c), h("span", {}, d))),
    ...seriesHits.map((s) => h("div", { onmousedown: (e) => { e.preventDefault(); const parts = $("#cmd").value.trim().split(/\s+/); parts[parts.length - 1] = s.key; $("#cmd").value = parts.join(" ") + " "; $("#cmd").focus(); } },
      h("b", {}, s.key), h("span", {}, `${s.label} · ${s.unit}`))));
  box.hidden = false;
}

/* ================================================================== boot */
function refreshAll() { loadQuotes(); loadIndia(); loadQuakes(); loadEvents(); loadWeather(); loadChoke(); }
function boot() {
  clocks(); initMap(); chatIntro(); llmStatus();
  api("api/series").then((r) => SERIES = r.series).catch(() => {});
  refreshAll();
  setInterval(loadQuotes, 60000); setInterval(loadQuakes, 120000); setInterval(loadEvents, 900000);
  setInterval(loadWeather, 900000); setInterval(loadChoke, 3600000); setInterval(loadIndia, 3600000);
  setInterval(renderWire, 60000);
  document.querySelectorAll("#modes button").forEach((b) => b.onclick = () => setMode(b.dataset.mode));
  let start = "econ";
  try { start = localStorage.getItem("imx-mode") || "econ"; } catch {}
  setMode(MODES[start] ? start : "econ");

  const cmd = $("#cmd");
  if (matchMedia("(max-width: 760px)").matches) cmd.placeholder = "Command or question  (try: MIL, CORR brent usdinr)";
  $("#cmd-form").addEventListener("submit", (e) => { e.preventDefault(); const v = cmd.value; cmd.value = ""; $("#cmd-hints").hidden = true; runCommand(v); });
  cmd.addEventListener("input", () => showHints());
  cmd.addEventListener("focus", () => showHints());
  cmd.addEventListener("blur", () => setTimeout(() => $("#cmd-hints").hidden = true, 100));
  const askEl = $("#ask");
  $("#ask-form").addEventListener("submit", (e) => { e.preventDefault(); const v = askEl.value; askEl.value = ""; ask(v); });
  askEl.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ask-form").requestSubmit(); } });
  $("#ask-clear").onclick = () => { S.history = []; chatIntro(); };
  $("#work-clear").onclick = () => { S.charts = []; S.activeChart = -1; renderTabs(); $("#work").innerHTML = '<div class="empty">Charts cleared.</div>'; };
  document.addEventListener("keydown", (e) => {
    const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
    if (e.key === "/" && !typing) { e.preventDefault(); cmd.focus(); }
    if (e.key === "Escape") { document.activeElement?.blur(); $("#cmd-hints").hidden = true; }
    if (e.altKey && /^[1-6]$/.test(e.key)) { e.preventDefault(); setMode(Object.keys(MODES)[+e.key - 1]); }
  });
}
window.addEventListener("load", boot);
