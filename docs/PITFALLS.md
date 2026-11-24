# Pitfalls: mistakes already made (or narrowly avoided)

Each entry has the **symptom** you'll see, the **cause**, and the **fix or rule**. Read this before your
first change. Add an entry when you lose more than a few minutes to something.

## Data and correctness

1. **Splicing across base years.** *Symptom:* a level series with a jump in 2022-23 or 2024. *Cause:* MoSPI
   rebased GDP/IIP (2011-12 → 2022-23) and CPI (2012 → 2024). *Rule:* compute growth within a base; never
   join levels; keep `base_year` in output.
2. **India CPI stops at Dec 2025.** *Cause:* the base-2024 CPI isn't in the eSankhyiki API yet
   (`mospi.cpi(base_year="2024")` raises `SourceError`). *Rule:* say so wherever CPI appears; don't fill the
   gap with another series. Re-check `mospi.cpi(base_year="2024")` from time to time and update
   LIMITATIONS.md when it lands.
3. **IMF projections shown as actuals.** WEO values after a country's latest actual year are projections.
   `imf.weo` has a `projection` column; the terminal shades them (`shade_from`) and the tool text says so.
4. **Dates as end of period.** Everything here is *start* of period (FY 2024-25 = 2024-04-01). A
   month-end date silently shifts joins by one period.
5. **Hard-coded "insights".** Insight and answer text must be computed from the fetched numbers. In the
   terminal, the LLM only explains tool `text`; never put numbers in prompts or templates.
6. **Simulated data leaking.** Every fallback path must carry `status: "sim"` / `sim: True` and the word
   SIMULATED in tool text. Tests use `INDIAMACRO_DEMO=1`, so a missing label is caught by
   `test_feeds_fall_back_to_labelled_simulation` and `test_get_series_never_uses_two_axes`.
7. **Lead/lag over-interpretation.** `correlate` searches ±12 lags, so its best lag is optimistic. The text
   says so and gives the rolling-correlation range. Don't remove those caveats.
8. **"BRICS" is the original five** in `countries.GROUPS` (no Egypt, Ethiopia, Iran, UAE, Indonesia).
   Say so if a user asks about the expanded group.

## Front end

9. **Leaflet pane ignored with `preferCanvas`.** *Symptom:* the night shading was "drawn" (layers
   existed, the canvas existed) but invisible or in the wrong z-order. *Cause:* with `preferCanvas: true`,
   vector layers use the map's default canvas in the overlay pane; their `pane` option is ignored without
   a renderer for that pane. *Fix:* `L.canvas({pane})` / `L.svg({pane})` and pass `renderer:`.
10. **Black on a dark basemap is invisible.** Night shading at 0.17 black over a near-black basemap showed
    nothing. Use a tint (navy `#0d2350`) and draw the terminator line.
11. **CARTO tiles need an API key now.** They render "API KEY REQUIRED" watermarks. The basemap is Esri dark
    gray (keyless, attribution required).
12. **Absolute URLs break the hosted copy.** The site lives under `/indiamacro/`. `fetch("/api/...")` or
    `href="/static/..."` hits the domain root (a different app). Always use relative URLs (`api/...`,
    `static/...`, `terminal.html`, `./`). The local server also routes `/terminal.html` for this reason.
    Don't add a `/terminal/` (trailing slash) route: relative `static/...` would resolve to `/terminal/static/`.
13. **One y-axis only in the terminal.** Different units → small multiples or z-score/index. (The older
    dashboard has a `y2` option; don't copy that pattern into the terminal.)
14. **Late async draws.** A feed can return after the user switched mode. Every `draw*()` starts with
    `if (S.mode !== "x") return;`, and timers live in `S.timers` so `setMode` can clear them.
15. **Markdown from the LLM is untrusted.** `md()` escapes HTML first; keep it that way, and never put an
    answer in `innerHTML` unescaped.
16. **Mobile overflow.** The header used to push the AI pill and DASHBOARD link off-screen, and mode tabs
    wrapped to two lines. The phone CSS wraps the header and makes the tabs scroll. After layout changes
    run `scripts/screenshots.py --sizes phone`; it reports overflowing elements (ignoring clipped/scrolling
    containers).
17. **iOS zoom on focus.** Inputs under 16 px make iOS zoom the page. Phone CSS sets 16 px on the command
    bar and ask box.

## Sources and networking

18. **User-Agent quirks.** FRED resets connections and IMF DataMapper returns 403 for browser-like UAs.
    Keep the default python-requests UA; don't add a "friendly" UA to the shared session.
19. **MoSPI TLS.** `api.mospi.gov.in` needs OpenSSL legacy renegotiation, enabled for that host only
    (`_LEGACY_TLS_HOSTS`). Don't enable it globally. MoSPI pages cap at 200 rows; filter queries.
20. **CelesTrak "No GP data found" is HTTP 404.** A name query with no matches raises `SourceError`; the
    military group treats that as empty. CelesTrak asks for at most one download per group per 2 hours;
    the disk ttl is 6 h. Don't lower it.
21. **"USA" catches GPS satellites.** NAVSTAR GPS satellites have USA-nnn names; they're filtered out of
    the military group. Expect other non-reconnaissance US government payloads to remain (documented).
22. **OpenSky anonymous quota.** Each pan used to make a new request. The bbox is now snapped to a 5° grid
    and capped in size; keep the 30 s refresh. If you add authenticated OpenSky access, keep the snapping.
23. **Yahoo rate limits and NaNs.** Raw `query1.finance.yahoo.com` calls 429; go through `yfinance`.
    Intraday frames are NaN outside trading hours, so `dropna()` per ticker and take the previous date's last
    bar as the previous close.
24. **Natural Earth ISO codes.** France, Norway and a few others have `ISO_A3 = "-99"`; use `ADM0_A3` then.
    Small states (Bahrain...) aren't in the 1:110m file, so they appear in rankings with a code instead of a name.
25. **PortWatch lag.** Chokepoint data are about a week behind; wire items and popups show the data date.

## Python and the server

26. **Shadowing a module with a local.** In `Handler.do_GET`, `query` is the parsed query-string dict. The
    terminal module is imported as `mquery` for this reason. Watch for this in any handler.
27. **`@memo` keys on positional args only.** `framework.memo` builds its key from `*args`; keyword
    arguments aren't supported. Call memoised loaders positionally.
28. **Port fallback on restart.** `_free_port` used to probe without `SO_REUSEADDR`. A socket in TIME_WAIT
    from the just-stopped process made 8765 look busy, so `systemctl restart` moved the service to 8766
    and nginx returned 502. The probe now sets `SO_REUSEADDR`. If you see 502 after a deploy, check
    `ss -ltnp | grep indiamacro`.
29. **Quoting Python inside bash single quotes.** `python -c '... env.get(\"X\") ...'` fails: backslashes are
    literal inside single quotes, so Python sees `\"`. Use double quotes inside the Python code, or a
    heredoc.
30. **`.env` doesn't override the environment.** `env.load()` uses `setdefault`, so an exported variable
    wins over `.env`. Tests rely on this; it also means a stale exported key beats your edit.
31. **`energy` isn't exported from the package.** `im.energy` raises `AttributeError`; use
    `from indiamacro.sources import energy`. (Known issue, listed in CLAUDE.md.)
32. **Optional-package scripts.** Playwright must not become a project dependency: run it with
    `uv run --no-project --with playwright==1.57.0 ...`. The browser binary already in
    `~/.cache/ms-playwright` is for arm64 (`chrome-headless-shell-linux-arm64`); `scripts/screenshots.py`
    finds it.

## Security and operations

33. **Secrets.** `.env` holds the LLM key and the site password; it's gitignored. Never print values (mask
    with `sed -E 's/=.*/=<redacted>/' .env`), never put the password on a command line (`curl -u` shows in
    `ps`); use `--netrc-file <(...)` or stdin (`htpasswd -i`).
34. **The public site spends the owner's LLM credits.** `/api/ask` is rate-limited per IP
    (`INDIAMACRO_ASK_PER_HOUR`, default 30) and the whole site sits behind basic auth. Don't remove either.
35. **Shared nginx config.** `/etc/nginx/sites-available/t.aryan.cfd` also serves other apps (/p, /admin,
    /cytogame, /agentcyto). Back it up before editing (`sudo cp ... t.aryan.cfd.bak-$(date +%Y%m%d%H%M%S)`),
    then `sudo nginx -t` before `sudo systemctl reload nginx`. Never restart other apps' containers.
36. **The server runs from the working tree.** systemd uses the repo checkout, so `git checkout <branch>`
    changes production code at the next restart, and uncommitted edits ship too.
