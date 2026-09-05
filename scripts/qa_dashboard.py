"""Full QA crawl of the PATI dashboard.

- Boots the control plane with an isolated data dir.
- Crawls every page + SEO/PWA file, asserting HTTP 200.
- Captures browser console on every page; FAILS on any console error.
- Live flow: reads bootstrap token, connects via the real UI, submits a job,
  verifies the thank-you redirect + live jobs list.
- Saves desktop + phone screenshots.
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import async_playwright

PATI = Path("/home/z/my-project/pati")
DATA = Path("/tmp/pati_qa_data")
SHOTS = Path("/home/z/my-project/download")
PORT = 8021
BASE = f"http://127.0.0.1:{PORT}"

errors: list[str] = []
console_msgs: list[tuple[str, str]] = []


async def track_console(page, label):
    page.on("console", lambda m: console_msgs.append((label, m.type, m.text))
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(f"{label}: PAGEERROR {e}"))
    page.on("requestfailed", lambda r:
            errors.append(f"{label}: REQFAIL {r.url} {r.failure}")
            if not r.url.startswith("http://127.0.0.1") or "/owner-photo" not in r.url
            and "favicon" not in r.url else None)


async def main():
    # fresh data dir -> server bootstraps a fresh admin token
    shutil.rmtree(DATA, ignore_errors=True)
    DATA.mkdir(parents=True)
    env = dict(os.environ, PATI_DATA_DIR=str(DATA))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "pati_api.app:app", "--port", str(PORT)],
        cwd=str(PATI), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for boot + grab the bootstrap token
        token = ""
        for _ in range(40):
            time.sleep(0.5)
            tf = DATA / "bootstrap_admin_token.txt"
            if tf.exists():
                token = tf.read_text().strip()
                break
        assert token, "bootstrap token never appeared"

        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # ---------------- plain HTTP crawl of everything
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            await track_console(page, "crawl")
            crawl = ["/", "/faq", "/privacy", "/thank-you?job=job_qa1", "/offline",
                     "/robots.txt", "/sitemap.xml", "/llms.txt", "/manifest.webmanifest",
                     "/sw.js", "/assets/icon-192.png", "/assets/icon-512.png",
                     "/assets/icon-maskable-512.png", "/assets/apple-touch-icon.png",
                     "/assets/favicon-64.png", "/assets/favicon.svg",
                     "/assets/og-image.png", "/docs"]
            for path in crawl:
                r = await page.goto(BASE + path, wait_until="domcontentloaded")
                status = r.status if r else 0
                print(f"  {status}  {path}")
                assert status == 200, f"{path} -> {status}"
            # custom 404 (separate page: its own 404 status is expected,
            # not a dashboard bug)
            p404 = await browser.new_page()
            r = await p404.goto(BASE + "/no-such-page", wait_until="domcontentloaded")
            assert r.status == 404 and "Page not found" in await p404.content()
            await p404.close()
            print("  404  /no-such-page (custom HTML page)")

            # ---------------- dashboard: no console errors at load
            await page.goto(BASE + "/", wait_until="networkidle")
            await page.wait_for_timeout(600)

            # manifest/sw sanity inside the browser
            sw_ok = await page.evaluate(
                "!!document.querySelector('link[rel=manifest]')")
            assert sw_ok

            # ---------------- live flow: connect with real token
            await page.fill("#tokenInput", token)
            await page.click("#connectBtn")
            await page.wait_for_timeout(2500)
            label = await page.text_content("#connLabel")
            print(f"  connect -> {label}")
            assert "Connected" in (label or ""), "token connect failed"

            # submit a real job through the UI
            await page.fill("#objective", "Generate an image of a mountain lake at sunrise")
            await page.click("#runBtn")
            # wait for redirect to /thank-you
            for _ in range(40):
                await page.wait_for_timeout(250)
                if "/thank-you" in page.url:
                    break
            assert "/thank-you" in page.url, f"no thank-you redirect (at {page.url})"
            content = await page.content()
            assert "Job submitted" in content
            print(f"  submit -> redirected to {page.url.split('/')[-1]}")

            # back to dashboard: job should appear live
            await page.goto(BASE + "/", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            jobs = await page.text_content("#jobsList")
            assert "mountain lake" in (jobs or ""), "job not visible in live list"
            print("  live jobs list shows the submitted job")

            # ---------------- screenshots
            await page.screenshot(path=str(SHOTS / "pati_dashboard_desktop.png"),
                                  full_page=True)
            phone = await browser.new_page(
                viewport={"width": 390, "height": 844},
                is_mobile=True, has_touch=True,
                user_agent=("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"))
            await track_console(phone, "phone")
            await phone.goto(BASE + "/", wait_until="networkidle")
            await phone.wait_for_timeout(800)
            await phone.screenshot(path=str(SHOTS / "pati_dashboard_phone.png"),
                                   full_page=True)
            await phone.goto(BASE + "/faq", wait_until="networkidle")
            await phone.screenshot(path=str(SHOTS / "pati_faq_phone.png"),
                                   full_page=True)
            await browser.close()

        # ---------------- console verdict
        errs = [m for m in console_msgs if m[1] == "error"]
        print("\nconsole errors:", len(errs))
        for e in errs:
            print("  ERR", e)
        warn_count = len([m for m in console_msgs if m[1] == "warning"])
        print("console warnings:", warn_count)
        for w in console_msgs:
            if w[1] == "warning":
                print("  WARN", w)
        if errors:
            print("page/request errors:", errors)
        assert not errs and not errors, "console/network errors detected"
        print("\nQA PASS: every page 200, zero console errors, live flow works")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

asyncio.run(main())
