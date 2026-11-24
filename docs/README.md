# indiamacro docs: start here

These docs are written for whoever works on this code next, human or AI agent. They explain how the
pieces fit, how to change them safely, and the mistakes that have already been made once.

`CLAUDE.md` (repo root) is the short version that is loaded into every agent session. These files are
the long version. When they disagree, the code wins; fix the doc in the same change.

## Reading order

| If you want to... | Read |
|---|---|
| Understand the system in 10 minutes | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Know the shapes of data moving around (DataFrames, envelopes, chart specs, tool results) | [DATA_MODEL.md](DATA_MODEL.md) |
| Work on the live terminal (`/terminal`: feeds, maps, satellites, AI analyst) | [TERMINAL.md](TERMINAL.md) |
| Call or change the HTTP API | [API.md](API.md) |
| Add something (a source, a page, a series, a tool, a feed, a map mode) | [RECIPES.md](RECIPES.md) |
| Find out why something is broken | [DEBUGGING.md](DEBUGGING.md) |
| Avoid repeating known mistakes | [PITFALLS.md](PITFALLS.md) (read this before your first change) |
| Write or run tests, or check the UI with screenshots | [TESTING.md](TESTING.md) |
| Ship to https://t.aryan.cfd/indiamacro | [DEPLOYMENT.md](DEPLOYMENT.md) |

## Reference material (already here, for users and researchers)

| File | What it is |
|---|---|
| [SOURCES.md](SOURCES.md) | Per-source catalogue: endpoints, codes worth knowing, quirks. Update it when you touch a source. |
| [SOURCE_STATUS.md](SOURCE_STATUS.md) | Output of the last `indiamacro-ping --markdown` run. Generated; don't hand-edit. |
| [../LIMITATIONS.md](../LIMITATIONS.md) | What the data can't tell you, lags, proxies, fragile connections. User-facing. |
| [../README.md](../README.md) | User-facing overview of the library, dashboard and terminal. |
| RESEARCH_OUTCOME_ANGLE.md | A plan (not implemented) for R&D/education outcome data. |
| eastern_seaboard_report.md, econ_ai_report_slop.md | The owner's research notes. Not documentation of the code; don't edit. |

## The project in five sentences

`indiamacro` is a Python library that fetches free macroeconomic data (India first, with international
comparators) into tidy pandas objects with provenance attached. On top of it sit two web front ends
served by one stdlib HTTP server: a **dashboard** of explained "story" pages, and a Bloomberg-style
**terminal** with live feeds, six map modes and an LLM analyst that answers questions by calling
data tools. The audience (students, journalists, analysts, investors) will quote the numbers, so
correctness, dates, sources and honest caveats matter more than features. Everything uses free,
keyless sources; paid or login-gated data is out of scope on purpose. The hosted copy runs on this
machine behind nginx and a password.

## Ground rules that apply to every change

1. **Never invent or hard-code a number** that is shown as data. Insights and AI answers are computed
   from fetched data; simulated data is always labelled SIM/SIMULATED.
2. **Cite the original producer** (MoSPI, RBI, IMF...), with dates, not this package.
3. **Never splice series across base years** or mix projections into actuals silently.
4. **All network access goes through `_http`** (or, for Yahoo, `yfinance` wrapped with a cache).
5. **Run `uv run pytest`** (offline, ~2 s) before and after; check UI changes with
   `scripts/screenshots.py` at phone and desktop sizes.
6. **Update docs in the same change**: README/SOURCES/LIMITATIONS for users, these files for developers.
