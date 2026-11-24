"""Screenshot the dashboard and terminal at phone / tablet / laptop / desktop sizes, and report problems.

    uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py                  # local :8765
    uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py --url http://localhost:8773
    uv run --no-project --with playwright==1.57.0 python scripts/screenshots.py --prod           # t.aryan.cfd, password from .env
    ... --modes econ,gnss,mil --sizes phone,desktop --ask "how does oil relate to the rupee?" --out /tmp/shots

Runs with ``--no-project`` so Playwright never becomes a project dependency. It finds an already
downloaded Chromium in ~/.cache/ms-playwright (set PLAYWRIGHT_CHROMIUM to override); if none matches
your Playwright version, run ``uv run --no-project --with playwright==1.57.0 playwright install chromium``.

For each size it prints: JS errors, HTTP responses >= 400, panel badges (LIVE/SIM/ERR) and elements
that stick out past the right edge of the viewport (horizontal overflow; the ticker tape is expected).
Exit code 1 if any JS error or failed request was seen.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import os
import sys
from pathlib import Path

SIZES = {
    "phone": dict(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, device_scale_factor=2),
    "tablet": dict(viewport={"width": 820, "height": 1180}, is_mobile=True, has_touch=True, device_scale_factor=2),
    "laptop": dict(viewport={"width": 1366, "height": 768}),
    "desktop": dict(viewport={"width": 1680, "height": 980}),
}
MODES = ["econ", "traffic", "climate", "gnss", "astro", "mil"]
PROD = "https://t.aryan.cfd/indiamacro"


def chromium() -> str | None:
    if os.environ.get("PLAYWRIGHT_CHROMIUM"):
        return os.environ["PLAYWRIGHT_CHROMIUM"]
    pats = ["~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell",
            "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux/headless_shell",
            "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"]
    for pat in pats:
        hits = sorted(glob.glob(os.path.expanduser(pat)))
        if hits:
            return hits[-1]
    return None


def credentials() -> dict | None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from indiamacro.monitor import env   # loads .env

    user, pw = env.get("INDIAMACRO_USERNAME"), env.get("INDIAMACRO_KEY")
    return {"username": user, "password": pw} if user and pw else None


async def main(a) -> int:
    from playwright.async_api import async_playwright

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    base = a.url.rstrip("/")
    creds = credentials() if (a.prod or a.auth) else None
    bad_total = 0
    async with async_playwright() as p:
        exe = chromium()
        browser = await p.chromium.launch(**({"executable_path": exe} if exe else {}))
        for size in a.sizes.split(","):
            ctx = await browser.new_context(**SIZES[size], **({"http_credentials": creds} if creds else {}))
            page = await ctx.new_page()
            errors, bad = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("response", lambda r: bad.append(f"{r.status} {r.url}") if r.status >= 400 else None)
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

            await page.goto(f"{base}/terminal.html")
            await page.wait_for_timeout(a.wait)
            for mode in a.modes.split(","):
                await page.evaluate(f"setMode('{mode}')")
                await page.wait_for_timeout(a.wait // 2)
                await page.screenshot(path=out / f"{size}_{mode}.png", full_page=size in ("phone", "tablet"))
            if a.ask:
                await page.evaluate(f"ask({a.ask!r})")
                await page.wait_for_selector(".msg.bot:last-child .meta", timeout=180_000)
                await page.screenshot(path=out / f"{size}_ask.png", full_page=size in ("phone", "tablet"))
            badges = await page.evaluate("[...document.querySelectorAll('.badge')].map(b => b.id + '=' + b.textContent)")
            # elements past the right edge that are NOT inside a container that clips or scrolls them
            overflow = await page.evaluate("""() => [...document.querySelectorAll('body *')]
                .filter(e => e.getBoundingClientRect().right > innerWidth + 1)
                .filter(e => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) {
                    const s = getComputedStyle(a);
                    if (s.overflowX !== 'visible' && a.getBoundingClientRect().right <= innerWidth + 1) return false; }
                  return true; })
                .slice(0, 8).map(e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.split(' ')[0] : ''))""")
            await page.goto(f"{base}/")
            await page.wait_for_timeout(a.wait // 2)
            await page.screenshot(path=out / f"{size}_dashboard.png")
            print(f"[{size}] badges {badges}\n  overflow {overflow or 'none'}\n  js errors {errors or 'none'}\n  failed requests {bad or 'none'}")
            bad_total += len(errors) + len(bad)
            await ctx.close()
        await browser.close()
    print(f"screenshots in {out}")
    return 1 if bad_total else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://localhost:8765")
    ap.add_argument("--prod", action="store_true", help=f"use {PROD} with the password from .env")
    ap.add_argument("--auth", action="store_true", help="send INDIAMACRO_USERNAME/KEY from .env as basic auth")
    ap.add_argument("--sizes", default="phone,tablet,laptop,desktop")
    ap.add_argument("--modes", default=",".join(MODES))
    ap.add_argument("--ask", default="", help="also ask the analyst this question and screenshot the answer")
    ap.add_argument("--wait", type=int, default=8000, help="ms to wait for live feeds after loading")
    ap.add_argument("--out", default=os.environ.get("TMPDIR", "/tmp") + "/indiamacro-shots")
    args = ap.parse_args()
    if args.prod:
        args.url = PROD
    sys.exit(asyncio.run(main(args)))
