/* indiamacro dashboard: hash router + generic renderer for the server's chart specs. */
"use strict";

const PALETTE = ["#e8590c", "#2563eb", "#059669", "#7c3aed", "#db2777", "#0891b2", "#ca8a04", "#64748b",
                 "#dc2626", "#4f46e5", "#65a30d", "#0d9488"];
const EVENT_COLORS = { refinery_strike: "#dc2626", reserve_release: "#059669", opec: "#ca8a04",
                       sanctions: "#7c3aed", geopolitical: "#475569", demand: "#0891b2",
                       india_policy: "#e8590c", custom: "#db2777" };
const $ = (sel, el = document) => el.querySelector(sel);
const h = (tag, attrs = {}, ...kids) => {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (v !== undefined && v !== null && v !== false) el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined) el.append(kid.nodeType ? kid : String(kid));
  return el;
};
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const isDate = (x) => typeof x === "string" && /^\d{4}-\d{2}-\d{2}$/.test(x);
const fmt = (v, d = 2) => v === null || v === undefined ? "–"
  : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });

let CATALOG = null;
let current = null;            // { id, params } of the page on screen
let charts = [];               // plotly divs, for re-theming

/* ------------------------------------------------------------------ theme */
function applyTheme(t) {
  if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme;
  try { t ? localStorage.setItem("theme", t) : localStorage.removeItem("theme"); } catch {}
  charts.forEach((div) => window.Plotly && Plotly.relayout(div, themeLayout()));
}
function currentTheme() {
  return document.documentElement.dataset.theme ||
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function themeLayout() {
  return {
    paper_bgcolor: "rgba(0,0,0,0)", plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: "Inter, system-ui, sans-serif", size: 12, color: css("--ink-2") },
    "xaxis.gridcolor": css("--grid"), "yaxis.gridcolor": css("--grid"),
    "xaxis.linecolor": css("--line"), "yaxis.zerolinecolor": css("--line"),
    "legend.font.color": css("--ink-2"), "hoverlabel.bgcolor": css("--panel"),
    "hoverlabel.font.color": css("--ink"), "hoverlabel.bordercolor": css("--line"),
  };
}

/* ------------------------------------------------------------------ api */
async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const body = await r.json().catch(() => ({ error: `HTTP ${r.status}` }));
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  return body;
}
function toast(msg) {
  const t = h("div", { class: "toast" }, msg);
  document.body.append(t);
  setTimeout(() => t.remove(), 3500);
}

/* ------------------------------------------------------------------ nav + routing */
function buildNav() {
  const nav = $("#nav");
  nav.innerHTML = "";
  for (const section of CATALOG.sections) {
    const items = CATALOG.stories.filter((s) => s.section === section);
    if (section === "Tools") items.splice(0, 0, { id: "__events", title: "Events", section });
    if (!items.length) continue;
    nav.append(h("h4", {}, section === "Shocks" ? "Analysis: shocks" : section === "Trends" ? "Analysis: trends" : section));
    for (const s of items) {
      const href = s.id === "__events" ? "#/events" : `#/story/${s.id}`;
      nav.append(h("a", { href, "data-id": s.id, title: s.question || "" }, s.title));
    }
  }
}
function markActive(id) {
  document.querySelectorAll("nav a").forEach((a) => a.classList.toggle("active", a.dataset.id === id));
}
function parseHash() {
  const [path, qs] = location.hash.replace(/^#/, "").split("?");
  const parts = path.split("/").filter(Boolean);
  return { parts, params: Object.fromEntries(new URLSearchParams(qs || "")) };
}
async function route() {
  $("#sidebar").classList.remove("open");
  const { parts, params } = parseHash();
  if (parts[0] === "events") { markActive("__events"); return renderEvents(); }
  const id = parts[0] === "story" && parts[1] ? parts[1] : "overview";
  markActive(id);
  return renderStory(id, params);
}

/* ------------------------------------------------------------------ story page */
async function renderStory(id, params) {
  current = { id, params };
  const page = $("#page");
  const meta = CATALOG.stories.find((s) => s.id === id) || { title: id, section: "", question: "" };
  page.innerHTML = "";
  page.append(head(meta.section, meta.title, meta.question));
  const loader = $("#loading").content.cloneNode(true).firstElementChild;
  page.append(loader);
  const t0 = performance.now();
  const timer = setInterval(() => { const t = $(".timer", loader); if (t) t.textContent = `${((performance.now() - t0) / 1000).toFixed(0)}s`; }, 500);
  let story;
  try {
    story = await api(`api/story/${id}?` + new URLSearchParams(params));
  } catch (e) {
    clearInterval(timer);
    loader.replaceWith(h("div", { class: "card error" }, h("h2", {}, "Couldn't load this page"), h("pre", {}, e.message)));
    return;
  } finally { clearInterval(timer); }
  if (current.id !== id) return;   // user navigated away meanwhile
  charts = [];
  page.innerHTML = "";
  const hd = head(story.section, story.title, story.question);
  hd.append(h("div", { class: "meta" }, `Computed in ${story.seconds}s · data cached locally`));
  page.append(hd);
  if (story.params.length) page.append(paramForm(story));
  if (story.insights.length) {
    page.append(h("section", { class: "insights" }, h("h3", {}, "What the data says"),
      h("ul", {}, story.insights.map((t) => h("li", {}, t)))));
  }
  const grid = h("div", { class: "grid" });
  page.append(grid);
  for (const b of story.blocks) grid.append(block(b));
  if (story.method || story.caveats.length) {
    page.append(h("details", { class: "method", open: story.id.startsWith("tpl_") ? "" : null },
      h("summary", {}, "Method and caveats"),
      story.method ? h("p", {}, h("b", {}, "Method. "), story.method) : null,
      story.caveats.length ? h("ul", {}, story.caveats.map((c) => h("li", {}, c))) : null));
  }
}
function head(section, title, question) {
  return h("header", { class: "page-head" }, h("div", { class: "crumb" }, section),
    h("h1", {}, title), question ? h("p", {}, question) : null);
}
function paramForm(story) {
  const form = h("form", { class: "params", onsubmit: (e) => {
    e.preventDefault();
    const values = {};
    for (const p of story.params) values[p.name] = form.elements[p.name].value;
    const next = `#/story/${story.id}?` + new URLSearchParams(values);
    if (location.hash === next) route(); else location.hash = next;   // re-run even if unchanged
  } });
  for (const p of story.params) {
    const val = story.values[p.name] ?? p.default ?? "";
    let input;
    if (p.type === "select") {
      input = h("select", { name: p.name }, p.options.map((o) => h("option", { value: o.value, selected: String(o.value) === String(val) ? "" : null }, o.label)));
    } else {
      input = h("input", { name: p.name, type: p.type === "number" ? "number" : "text", value: val, placeholder: p.help || "" });
    }
    form.append(h("label", { class: p.type === "text" ? "wide" : "", title: p.help || "" }, p.label, input));
  }
  form.append(h("button", { class: "primary", type: "submit" }, "Run"));
  return form;
}

/* ------------------------------------------------------------------ blocks */
function block(spec) {
  const width = spec.width || "full";
  if (spec.kind === "text") return h("div", { class: `card text ${width}`, html: null }, md(spec.markdown));
  if (spec.kind === "error") {
    return h("div", { class: `card error ${width}` }, h("h2", {}, spec.title || "Chart unavailable"),
      h("pre", {}, spec.message), h("div", { class: "unit" }, "The source may be down or slow; other charts are unaffected."));
  }
  if (spec.kind === "kpis") return h("div", { class: `card ${width}` }, spec.title ? h("h2", {}, spec.title) : null, kpis(spec.tiles));
  const card = h("div", { class: `card ${width}` });
  card.append(h("h2", {}, spec.title));
  if (spec.unit) card.append(h("div", { class: "unit" }, spec.unit));
  if (spec.kind === "table") {
    card.append(h("div", { class: "tablewrap" }, h("table", {},
      h("thead", {}, h("tr", {}, spec.columns.map((c) => h("th", {}, c)))),
      h("tbody", {}, spec.rows.map((r) => h("tr", {}, r.map((c) => h("td", {}, c))))))));
  } else {
    const div = h("div", { class: "chart" });
    card.append(div);
    requestAnimationFrame(() => plot(div, spec));
  }
  const tools = h("div", { class: "tools" });
  if (spec.traces || spec.rows) tools.append(h("button", { type: "button", title: "Download the data behind this chart", onclick: () => downloadCSV(spec) }, "CSV"));
  card.append(h("div", { class: "card-foot" },
    h("div", { class: "src" }, spec.source ? h("em", {}, "Source: " + spec.source) : null, spec.note ? h("div", {}, spec.note) : null),
    tools));
  return card;
}
function md(text) {
  // tiny markdown: **bold**, *italic*, `code`
  const span = h("div");
  const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
  span.innerHTML = esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/`(.+?)`/g, "<code>$1</code>");
  return span;
}
function kpis(tiles) {
  return h("div", { class: "kpis" }, tiles.map((t) => {
    if (t.error) return h("div", { class: "tile err", title: t.error }, h("div", { class: "lbl" }, t.label), h("div", { class: "val" }, "unavailable"));
    const d = t.delta;
    const dir = d > 0 ? "up" : d < 0 ? "down" : "";
    return h("div", { class: "tile", title: [t.hint, t.source].filter(Boolean).join(" · ") },
      h("div", { class: "lbl" }, h("span", {}, t.label), h("span", {}, tileDate(t.date))),
      h("div", { class: "val" }, fmt(t.value, t.decimals), h("small", {}, t.unit)),
      sparkline(t.spark),
      h("div", { class: "sub" }, h("span", { class: dir }, d === null || d === undefined ? "" : `${d > 0 ? "▲" : d < 0 ? "▼" : "•"} ${fmt(Math.abs(d), t.decimals)} vs prev.`),
        h("span", {}, t.source)));
  }));
}
function tileDate(d) {
  if (!isDate(d)) return d || "";
  const dt = new Date(d + "T00:00:00");
  if (d.endsWith("-01-01")) return d.slice(0, 4);                       // annual
  if (d.endsWith("-01")) return dt.toLocaleDateString("en-GB", { month: "short", year: "numeric" });   // monthly
  return dt.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
function sparkline(spark) {
  const ys = (spark?.y || []).filter((v) => v !== null);
  if (ys.length < 2) return h("div");
  const min = Math.min(...ys), max = Math.max(...ys), span = max - min || 1;
  const pts = ys.map((v, i) => `${(i / (ys.length - 1)) * 100},${30 - ((v - min) / span) * 26 - 2}`);
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 100 32"); svg.setAttribute("preserveAspectRatio", "none");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", "M" + pts.join(" L")); path.setAttribute("vector-effect", "non-scaling-stroke");
  svg.append(path);
  return svg;
}

/* ------------------------------------------------------------------ plotly */
function plot(div, spec) {
  if (!window.Plotly) { div.replaceWith(h("pre", {}, "Charts need the Plotly library from cdn.jsdelivr.net - check your internet connection.")); return; }
  const traces = [];
  const kind = spec.kind;
  const n = (spec.traces || []).length;
  const dateX = spec.traces?.some((t) => isDate(t.x?.[0]));
  (spec.traces || []).forEach((t, i) => {
    const color = PALETTE[i % PALETTE.length];
    const big = (t.x || []).length > 4000;
    if (kind === "scatter") {
      traces.push(t.mode === "lines"
        ? { type: "scatter", mode: "lines", x: t.x, y: t.y, name: t.name, line: { color: PALETTE[1], width: 2 } }
        : { type: "scatter", mode: "markers", x: t.x, y: t.y, name: t.name, text: t.text,
            marker: { color: PALETTE[0], size: 6, opacity: .65 }, hovertemplate: "%{text}<br>x %{x:.2f}<br>y %{y:.2f}<extra></extra>" });
      return;
    }
    if (kind === "bar" || kind === "hbar" || kind === "stackbar") {
      const horiz = kind === "hbar";
      const colors = t.highlight ? t.highlight.map((on) => on ? PALETTE[0] : css("--ink-3")) : color;
      traces.push({ type: "bar", name: t.name, x: horiz ? t.y : t.x, y: horiz ? t.x : t.y, orientation: horiz ? "h" : "v",
        marker: { color: colors, opacity: t.dash ? .45 : .9 }, showlegend: n > 1 && !!t.name,
        hovertemplate: horiz ? "%{y}: %{x:,.2f}<extra></extra>" : `${t.name ? t.name + "<br>" : ""}%{x}: %{y:,.2f}<extra></extra>` });
      return;
    }
    const tr = { type: big ? "scattergl" : "scatter", mode: "lines", name: t.name, x: t.x, y: t.y,
      yaxis: t.axis === "y2" ? "y2" : "y",
      line: { color, width: t.name === "Average" ? 3 : n > 8 ? 1.2 : 1.8, dash: t.dash ? "dash" : "solid" },
      hovertemplate: `${t.name}: %{y:,.2f}<extra></extra>` };
    if (kind === "area") { tr.stackgroup = "one"; tr.line.width = .5; tr.fillcolor = color + "cc"; }
    if (spec.band_pair && i < 2) {
      tr.line = { width: 0, color }; tr.showlegend = false; tr.hoverinfo = "skip"; tr.hovertemplate = undefined;
      tr.type = "scatter";
      if (i === 1) { tr.fill = "tonexty"; tr.fillcolor = "rgba(232,89,12,0.15)"; }
    }
    if (spec.band_pair && t.name === "Average") tr.line.color = PALETTE[0];
    traces.push(tr);
  });
  if (spec.overlay_line) {
    traces.push({ type: "scatter", mode: "lines+markers", name: spec.overlay_line.name, x: spec.overlay_line.x,
      y: spec.overlay_line.y, line: { color: css("--ink"), width: 2 }, marker: { size: 7 } });
  }

  const shapes = [], annotations = [];
  for (const b of spec.hbands || []) {
    if (b.y0 === b.y1) shapes.push({ type: "line", xref: "paper", x0: 0, x1: 1, y0: b.y0, y1: b.y1, line: { color: css("--ink-3"), width: 1, dash: "dot" } });
    else shapes.push({ type: "rect", xref: "paper", x0: 0, x1: 1, y0: b.y0, y1: b.y1, fillcolor: "rgba(5,150,105,0.08)", line: { width: 0 }, layer: "below" });
    if (b.label) annotations.push({ xref: "paper", x: 1, y: b.y1, text: b.label, showarrow: false, xanchor: "right", yanchor: "bottom", font: { size: 10, color: css("--ink-3") } });
  }
  for (const b of spec.bands || []) {
    shapes.push({ type: "rect", yref: "paper", y0: 0, y1: 1, x0: b.x0, x1: b.x1, fillcolor: "rgba(232,89,12,0.06)", line: { width: 0 }, layer: "below" });
    if (b.label) annotations.push({ yref: "paper", y: 1, x: b.x0, text: b.label, showarrow: false, xanchor: "left", yanchor: "bottom", font: { size: 10, color: css("--ink-3") } });
  }
  if (spec.vline0) shapes.push({ type: "line", yref: "paper", y0: 0, y1: 1, x0: 0, x1: 0, line: { color: css("--ink-3"), width: 1, dash: "dot" } });
  const xs = (spec.traces || []).flatMap((t) => [t.x?.[0], t.x?.[t.x.length - 1]]).filter(isDate).sort();
  for (const e of spec.events || []) {
    if (xs.length && (e.x < xs[0] || e.x > xs[xs.length - 1])) continue;
    const c = EVENT_COLORS[e.category] || "#64748b";
    shapes.push({ type: "line", yref: "paper", y0: 0, y1: 1, x0: e.x, x1: e.x, line: { color: c, width: 1, dash: "dot" }, opacity: .55 });
    annotations.push({ yref: "paper", y: 1.0, x: e.x, text: "◆", showarrow: false, yanchor: "bottom", font: { size: 10, color: c },
      hovertext: `${e.x}<br>${e.label}`, hoverlabel: { bgcolor: css("--panel") } });
  }

  const layout = {
    margin: { l: 56, r: spec.y2_unit ? 56 : 16, t: (spec.events || []).length ? 22 : 10, b: 40 },
    hovermode: kind === "scatter" ? "closest" : (kind === "hbar" ? "y unified" : "x unified"),
    showlegend: kind === "scatter" ? true : n > 1 || !!spec.overlay_line,
    legend: { orientation: "h", y: -0.16, x: 0, font: { size: spec.legend === "compact" || n > 8 ? 10 : 12 } },
    xaxis: { gridcolor: css("--grid"), linecolor: css("--line"), automargin: true, title: spec.x_label ? { text: spec.x_label, font: { size: 11 } } : undefined },
    yaxis: { gridcolor: css("--grid"), zerolinecolor: css("--line"), automargin: true, type: spec.log_y ? "log" : undefined,
             title: spec.y2_unit ? { text: spec.unit, font: { size: 11 } } : undefined },
    barmode: kind === "stackbar" || spec.stacked ? "relative" : "group",
    shapes, annotations,
  };
  merge(layout, flatten(themeLayout()));
  if (kind === "hbar") { layout.yaxis.automargin = true; layout.margin.l = 10; layout.xaxis.title = { text: spec.unit, font: { size: 11 } }; }
  if (spec.y2_unit) layout.yaxis2 = { overlaying: "y", side: "right", showgrid: false, title: { text: spec.y2_unit, font: { size: 11 } } };
  if (dateX && spec.range_buttons !== false && kind !== "bar") {
    layout.xaxis.rangeselector = { x: 0, y: 1.02, yanchor: "bottom", bgcolor: css("--panel-2"), activecolor: css("--accent-soft"),
      font: { size: 11, color: css("--ink-2") },
      buttons: [{ count: 1, label: "1Y", step: "year", stepmode: "backward" }, { count: 5, label: "5Y", step: "year", stepmode: "backward" },
                { count: 10, label: "10Y", step: "year", stepmode: "backward" }, { step: "all", label: "All" }] };
    layout.margin.t = 36;
  }
  Plotly.newPlot(div, traces, layout, { responsive: true, displaylogo: false, displayModeBar: "hover",
    modeBarButtonsToRemove: ["lasso2d", "select2d", "autoScale2d"],
    toImageButtonOptions: { filename: (spec.title || "chart").replace(/[^\w]+/g, "_"), scale: 2 } });
  charts.push(div);
}
function merge(target, src) {
  // deep merge so theme colours don't wipe out per-chart axis/legend settings
  for (const [k, v] of Object.entries(src)) {
    if (v && typeof v === "object" && !Array.isArray(v)) merge(target[k] = target[k] || {}, v);
    else target[k] = v;
  }
  return target;
}
function flatten(o) {
  // themeLayout uses "a.b" keys for relayout; expand them for newPlot
  const out = {};
  for (const [k, v] of Object.entries(o)) {
    const parts = k.split(".");
    let cur = out;
    parts.slice(0, -1).forEach((p) => { cur[p] = cur[p] || {}; cur = cur[p]; });
    cur[parts[parts.length - 1]] = v;
  }
  return out;
}

/* ------------------------------------------------------------------ csv */
function downloadCSV(spec) {
  let rows;
  if (spec.kind === "table") rows = [spec.columns, ...spec.rows];
  else {
    const xs = [...new Set(spec.traces.flatMap((t) => t.x))];
    if (xs.every(isDate)) xs.sort();
    const maps = spec.traces.map((t) => new Map(t.x.map((x, i) => [x, t.y[i]])));
    rows = [["x", ...spec.traces.map((t) => t.name)], ...xs.map((x) => [x, ...maps.map((m) => m.get(x) ?? "")])];
  }
  const csv = rows.map((r) => r.map((c) => /[",\n]/.test(String(c)) ? `"${String(c).replace(/"/g, '""')}"` : c).join(",")).join("\n");
  const a = h("a", { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })),
    download: (spec.title || "data").replace(/[^\w]+/g, "_") + ".csv" });
  document.body.append(a); a.click(); a.remove();
}

/* ------------------------------------------------------------------ events page */
async function renderEvents(filter = "all") {
  current = { id: "__events" };
  const page = $("#page");
  page.innerHTML = "";
  page.append(head("Tools", "Events", "The dated shocks and policy moves marked on charts and used by the event-study templates. Add your own - e.g. a refinery strike from last week."));
  let data;
  try { data = await api("api/events"); } catch (e) { page.append(h("div", { class: "card error" }, h("pre", {}, e.message))); return; }
  const cats = data.categories;
  const form = h("form", { class: "params events-form", onsubmit: async (e) => {
    e.preventDefault();
    const f = e.target.elements;
    try {
      await api("api/events", { method: "POST", body: JSON.stringify({ date: f.date.value, label: f.label.value, category: f.category.value, region: f.region.value }) });
      toast("Event added - event studies now include it");
      renderEvents(filter);
    } catch (err) { toast(err.message); }
  } },
    h("label", {}, "Date", h("input", { name: "date", type: "date", required: "" })),
    h("label", { class: "wide" }, "What happened", h("input", { name: "label", required: "", placeholder: "e.g. Drone strike on Volgograd refinery" })),
    h("label", {}, "Category", h("select", { name: "category" }, Object.entries(cats).map(([k, v]) => h("option", { value: k }, v)))),
    h("label", {}, "Region", h("input", { name: "region", placeholder: "Russia" })),
    h("button", { class: "primary", type: "submit" }, "Add event"));
  page.append(form);
  const filters = h("div", { class: "filters" }, [["all", "All"], ...Object.entries(cats)].map(([k, v]) =>
    h("button", { type: "button", class: filter === k ? "on" : "", onclick: () => renderEvents(k) }, v)));
  page.append(filters);
  const evs = data.events.filter((e) => filter === "all" || e.category === filter);
  page.append(h("div", { class: "card" }, h("div", { class: "tablewrap" }, h("table", { class: "text-table" },
    h("thead", {}, h("tr", {}, ["Date", "Event", "Category", "Region", ""].map((c) => h("th", {}, c)))),
    h("tbody", {}, evs.map((e) => h("tr", {},
      h("td", {}, e.date), h("td", {}, e.label),
      h("td", {}, h("span", { class: "tag" + (e.builtin ? "" : " mine") }, cats[e.category] || e.category)),
      h("td", {}, e.region || ""),
      h("td", {}, e.builtin ? h("span", { class: "unit" }, "built-in") : h("button", { class: "del", title: "Delete", onclick: async () => {
        await api(`api/events/${e.id}`, { method: "DELETE" }); toast("Event removed"); renderEvents(filter);
      } }, "✕"))))))),
    h("div", { class: "card-foot" }, h("div", { class: "src" }, `Your events are saved in ${data.file}`))));
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  try { const t = localStorage.getItem("theme"); if (t) document.documentElement.dataset.theme = t; } catch {}
  $("#theme").onclick = () => applyTheme(currentTheme() === "dark" ? "light" : "dark");
  $("#menu").onclick = () => $("#sidebar").classList.toggle("open");
  $("#refresh").onclick = async () => { await api("api/refresh", { method: "POST", body: "{}" }); toast("Pages will be recomputed"); route(); };
  $("#hard-refresh").onclick = async () => {
    if (!confirm("Delete the local download cache and fetch everything again? The next page loads will be slow.")) return;
    await api("api/refresh", { method: "POST", body: JSON.stringify({ hard: true }) }); toast("Cache cleared"); route();
  };
  try { CATALOG = await api("api/catalog"); }
  catch (e) { $("#page").append(h("div", { class: "card error" }, h("h2", {}, "Server not reachable"), h("pre", {}, e.message))); return; }
  buildNav();
  window.addEventListener("hashchange", route);
  route();
}
document.addEventListener("DOMContentLoaded", boot);
