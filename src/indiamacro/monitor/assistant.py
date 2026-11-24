"""The terminal's analyst: answers questions by calling the tools in :mod:`query`.

Two modes, chosen automatically:

* **LLM** when ``LLM_ENDPOINT`` and ``LLM_API_KEY`` are set (``.env`` or environment). Any
  OpenAI-compatible ``/chat/completions`` server works (OpenAI, Azure-style proxies, vLLM,
  Ollama, LM Studio, OpenRouter, ...). The model gets the tools as functions; if the server
  rejects function calling, we fall back to *grounded* mode: the rule-based planner picks
  the tools, and the model only writes the answer from their output.
* **Mock** otherwise: the same planner, plus a templated write-up built from the computed
  numbers. Clearly labelled; useful offline and for testing the screen.

Either way every number shown comes from a tool result, and the tools flag SIMULATED data.
"""

from __future__ import annotations

import json
import re
import time
import traceback

import requests

from .. import countries as _countries
from . import env, query

SYSTEM = """You are the analyst inside indiamacro, an India-first macro, markets and geospatial terminal used \
by journalists, analysts and investors. Answer by calling tools, then explain what the numbers show.
Rules:
- Every number you state must come from a tool result in this conversation. Never invent data.
- Name the source and the date of the latest observation for key numbers.
- If a tool result says SIMULATED, say plainly that the figures are simulated, not real.
- Correlation is not causation; mention sample size, lag choice and instability when relevant.
- IMF values after the latest actual year are projections; say so.
- Be concise: a 1-2 sentence answer first, then 3-6 bullets of evidence, then caveats. Use markdown.
- Suggest one or two follow-up angles the user could query next (other series, lags, peers, windows).
Today is {today}. Terminal context: {context}"""

MAX_ROUNDS = 5


def _endpoint() -> str:
    """LLM_ENDPOINT, else OPENAI_BASE_URL, else api.openai.com when only an OpenAI key is set."""
    return env.get("LLM_ENDPOINT") or env.get("OPENAI_BASE_URL") or ("https://api.openai.com/v1" if env.get("OPENAI_API_KEY") else "")


def _key() -> str:
    return env.get("LLM_API_KEY") or env.get("OPENAI_API_KEY")


def _model() -> str:
    return env.get("LLM_MODEL") or env.get("OPENAI_MODEL") or "gpt-4o-mini"


def configured() -> bool:
    return bool(_endpoint() and _key())


def status() -> dict:
    return {"mode": "llm" if configured() else "mock", "model": _model() if configured() else None,
            "endpoint_host": re.sub(r"^https?://([^/]+).*", r"\1", _endpoint()) if configured() else None}


def _url() -> str:
    u = _endpoint().rstrip("/")
    return u if u.endswith("/chat/completions") else u + "/chat/completions"


def _chat(messages: list[dict], tools: bool = True) -> dict:
    body = {"model": _model(), "messages": messages, "temperature": 0.2}
    if tools:
        body["tools"] = [{"type": "function", "function": {"name": n, "description": d, "parameters": p}}
                         for n, (_, p, d) in query.TOOLS.items()]
        body["tool_choice"] = "auto"
    r = requests.post(_url(), json=body, timeout=120,
                      headers={"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"})
    if r.status_code >= 400:
        raise RuntimeError(f"LLM HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


# ---------------------------------------------------------------- planner (mock + grounded mode)

_CMP_IND = [("current account", "current_account"), ("per capita", "gdp_per_capita_ppp"), ("debt", "govt_debt"),
            ("fiscal", "fiscal_balance"), ("deficit", "fiscal_balance"), ("unemployment", "unemployment"),
            ("inflation", "inflation"), ("fdi", "fdi_gdp"), ("export", "exports_gdp"), ("investment", "investment_gdp"),
            ("manufacturing", "manufacturing_gdp"), ("size", "gdp_usd"), ("share of world", "share_world_gdp_ppp"),
            ("gdp", "gdp_growth"), ("growth", "gdp_growth")]
_GROUPS = {"brics": "BRICS", "g7": "G7", "g20": "G20", "south asia": "SOUTH_ASIA", "asean": "ASEAN",
           "emerging asia": "EM_ASIA", "em asia": "EM_ASIA", "quad": "QUAD"}
_COUNTRY_WORDS = ["china", "united states", "us", "usa", "japan", "germany", "uk", "united kingdom", "brazil", "russia",
                  "indonesia", "pakistan", "bangladesh", "vietnam", "south africa", "mexico", "korea", "france",
                  "sri lanka", "nepal", "turkey", "saudi arabia", "philippines", "thailand", "malaysia", "australia"]
_LIVE = ["right now", "today", "live", "happening", "earthquake", "quake", "wildfire", "storm", "volcano",
         "air quality", "aqi", "pollution", "pm2.5", "smog", "shipping", "chokepoint", "markets now", "movers"]


def _countries_in(q: str) -> list[str]:
    out = ["IND"]
    for w in _COUNTRY_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", q):
            try:
                c = _countries.iso3({"us": "USA", "usa": "USA", "uk": "GBR", "korea": "KOR"}.get(w, w))
                if c not in out:
                    out.append(c)
            except Exception:
                pass
    return out


def plan(question: str) -> list[tuple[str, dict]]:
    """Pick tool calls for a question with keyword rules. Deliberately simple and predictable."""
    q = question.lower()
    keys = query.mentions(q)
    since = re.search(r"\b(?:since|from|after)\s+((?:19|20)\d{2})\b", q)
    start = f"{since.group(1)}-01-01" if since else None
    date = re.search(r"\b((?:19|20)\d{2}-\d{2}-\d{2})\b", q)
    group = next((g for w, g in _GROUPS.items() if re.search(rf"\b{w}\b", q)), None)
    named = _countries_in(q)
    cmp_intent = group or len(named) > 1 or re.search(r"\b(peers?|countries|other economies|rank|vs china|compared? to)\b", q)

    if re.search(r"\b(what can|help|which series|list)\b", q) and not keys:
        return [("list_series", {})]
    if cmp_intent and not (len(keys) >= 2 and re.search(r"correlat|relationship|lead|lag|move together", q)):
        ind = next((i for w, i in _CMP_IND if w in q), "gdp_growth")
        return [("compare_countries", {"indicator": ind, "countries": group or named, "start": int(since.group(1)) if since else 2000})]
    if date and keys:
        return [("window", {"series": keys[0], "date": date.group(1), "before": 30, "after": 90})]
    corr_words = re.search(r"correlat|relationship|relate|lead|lag|drive|affect|impact|pattern|move together|link", q)
    just_show = re.search(r"\b(show|plot|chart|graph|draw)\b", q)
    if len(keys) >= 2 and (corr_words or (len(keys) == 2 and not just_show)):
        freq = "W" if re.search(r"\bweekly|days?\b", q) else "M"
        calls = [("correlate", {"a": keys[0], "b": keys[1], "freq": freq, **({"start": start} if start else {})})]
        if len(keys) > 2:
            calls.append(("correlate", {"a": keys[0], "b": keys[2], "freq": freq}))
        return calls
    if keys:
        how = "yoy" if re.search(r"year[- ]on[- ]year|y/y|yoy|annual change", q) else \
              "zscore" if re.search(r"unusual|extreme|z-?score|abnormal", q) else \
              "index100" if re.search(r"rebase|indexed|performance", q) else "level"
        calls = [("get_series", {"names": keys[:4], "transform": how, **({"start": start} if start else {})})]
        if any(w in q for w in _LIVE):
            calls.append(("live_snapshot", {}))
        return calls
    if any(w in q for w in _LIVE) or not q.strip():
        return [("live_snapshot", {})]
    return [("live_snapshot", {}), ("list_series", {})]


def _run(calls: list[tuple[str, dict]]) -> list[tuple[str, dict, dict]]:
    out = []
    for name, args in calls:
        try:
            res = query.call(name, dict(args))
        except Exception as e:
            traceback.print_exc()
            res = {"text": f"Tool {name} failed: {type(e).__name__}: {e}", "charts": [], "sources": [], "sim": False}
        out.append((name, args, res))
    return out


def _mock_writeup(question: str, results: list[tuple[str, dict, dict]]) -> str:
    head = ("> **Mock analyst** — no LLM is configured, so this answer is assembled by rules from the tool output "
            "below. Put `LLM_ENDPOINT` and `LLM_API_KEY` in `.env` for a real model.\n")
    parts = [head]
    for name, args, res in results:
        st = res.get("stats") or {}
        if name == "correlate" and st:
            a, b = query.SERIES[query.resolve(args["a"])].label, query.SERIES[query.resolve(args["b"])].label
            r0, L, rb = st["r0"] or 0, st["best_lag"], st["best_r"]
            dirn = "in the same direction" if rb > 0 else "in opposite directions"
            lead = f"**{a}** tends to lead by {L} periods" if L > 0 else f"**{b}** tends to lead by {-L} periods" if L < 0 else "the link is strongest in the same period"
            parts.append(f"**{a} vs {b}:** changes move {dirn}; {lead} (r = {rb:.2f}, same-period r = {r0:.2f}, n = {st['n']}).")
        elif name == "get_series":
            first = res["text"].split("\n")[:2]
            parts.append("**" + first[0].split(" — ")[0] + ":** " + first[1].strip() if len(first) > 1 else res["text"])
        elif name == "compare_countries":
            lines = res["text"].split("\n")
            rank = next((ln.strip() for ln in lines if "ranks" in ln), "")
            parts.append(f"**Peer comparison:** {lines[1].strip() if len(lines) > 1 else ''} leads the group. {rank}")
        elif name == "live_snapshot":
            parts.append("**Live picture:** " + res["text"].split("\n")[0])
        elif name == "window":
            parts.append("**Event window:** " + res["text"].split("\n")[-1].strip())
    parts.append("\n**Evidence (computed):**\n```\n" + "\n\n".join(r["text"] for _, _, r in results) + "\n```")
    if any(r.get("sim") for _, _, r in results):
        parts.append("⚠ Some inputs are **SIMULATED** because a source was unreachable or demo mode is on.")
    parts.append("_Try next:_ add a lag (`CORR brent usdinr`), compare peers (`inflation vs BRICS`), "
                 "or zoom into a date (`rupee around 2025-04-02`).")
    return "\n\n".join(parts)


def _pack(answer: str, results, mode: str, error: str = "") -> dict:
    charts = [c for _, _, r in results for c in r.get("charts", [])]
    srcs = list(dict.fromkeys(s for _, _, r in results for s in r.get("sources", [])))
    return {"answer": answer, "charts": charts[:6], "mode": mode, "error": error,
            "tools": [{"name": n, "args": a} for n, a, _ in results], "sources": srcs,
            "sim": any(r.get("sim") for _, _, r in results), **status()}


def ask(question: str, history: list[dict] | None = None, context: str = "") -> dict:
    t0 = time.time()
    if not configured():
        results = _run(plan(question))
        out = _pack(_mock_writeup(question, results), results, "mock")
        out["elapsed"] = round(time.time() - t0, 2)
        return out

    sys_msg = {"role": "system", "content": SYSTEM.format(today=time.strftime("%Y-%m-%d"), context=context or "none")}
    msgs = [sys_msg, *[{"role": m["role"], "content": str(m["content"])[:4000]} for m in (history or [])[-8:]
                       if m.get("role") in ("user", "assistant")], {"role": "user", "content": question}]
    results: list[tuple[str, dict, dict]] = []
    try:
        for _ in range(MAX_ROUNDS):
            resp = _chat(msgs)
            msg = resp["choices"][0]["message"]
            calls = msg.get("tool_calls") or []
            if not calls:
                out = _pack(msg.get("content") or "", results, "llm")
                out["elapsed"] = round(time.time() - t0, 2)
                return out
            msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
            for c in calls:
                fn = c["function"]["name"]
                try:
                    args = json.loads(c["function"].get("arguments") or "{}")
                except ValueError:
                    args = {}
                (_, _, res), = _run([(fn, args)]) if fn in query.TOOLS else [(fn, args, {"text": f"unknown tool {fn}"})]
                results.append((fn, args, res))
                msgs.append({"role": "tool", "tool_call_id": c.get("id", fn), "content": res["text"][:6000]})
        msgs.append({"role": "user", "content": "Write the final answer now from the tool results."})
        final = _chat(msgs, tools=False)["choices"][0]["message"].get("content") or ""
        out = _pack(final, results, "llm")
    except Exception as e:
        traceback.print_exc()
        # grounded fallback: our planner runs the tools; the model (if reachable) only writes
        results = results or _run(plan(question))
        evidence = "\n\n".join(f"[{n}]\n{r['text']}" for n, _, r in results)
        try:
            final = _chat([sys_msg, {"role": "user", "content": f"Question: {question}\n\nTool results:\n{evidence}"}],
                          tools=False)["choices"][0]["message"].get("content") or ""
            out = _pack(final, results, "llm-grounded", error=str(e)[:300])
        except Exception as e2:
            out = _pack(_mock_writeup(question, results), results, "mock", error=f"LLM unavailable: {str(e2)[:300]}")
    out["elapsed"] = round(time.time() - t0, 2)
    return out
