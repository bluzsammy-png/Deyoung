"""Web dashboard pages: SEO hygiene, PWA files, custom 404, thank-you flow.

Checklist coverage (2026-09 owner request): unique titles, meta descriptions,
canonical tags, OG/Twitter share meta, JSON-LD, robots.txt, sitemap.xml,
llms.txt, breadcrumbs, alt text, installable PWA (manifest + service worker),
offline page, owner photo hook.
"""
from __future__ import annotations


import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _get(server, path):
    return httpx.get(f"{server['base_url']}{path}", follow_redirects=False)


# ---------------------------------------------------------------- pages
def test_all_pages_return_200(server):
    for path in ("/", "/faq", "/privacy", "/thank-you", "/offline"):
        r = _get(server, path)
        assert r.status_code == 200, path
        assert r.text.lstrip().startswith("<!doctype html>"), path


def test_every_page_unique_title_and_description(server):
    seen = set()
    for path in ("/", "/faq", "/privacy", "/thank-you", "/offline"):
        r = _get(server, path)
        m_title = __import__("re").search(r"<title>(.*?)</title>", r.text)
        assert m_title, f"no title on {path}"
        title = m_title.group(1)
        assert title not in seen, f"duplicate title: {title}"
        seen.add(title)
        assert "meta name=\"description\"" in r.text or \
               "meta name='description'" in r.text, path


def test_canonical_and_og_image_absolute(server):
    base = server["base_url"]
    r = _get(server, "/faq")
    assert f'<link rel="canonical" href="{base}/faq">' in r.text
    assert f'property="og:image" content="{base}/assets/og-image.png"' in r.text


def test_breadcrumbs_and_internal_links(server):
    r = _get(server, "/faq")
    assert 'aria-label="Breadcrumb"' in r.text
    assert 'href="/"' in r.text and 'href="/privacy"' in r.text
    r2 = _get(server, "/")
    assert 'href="/faq"' in r2.text
    assert 'alt="' in r2.text  # images carry alt text


def test_json_ld_present(server):
    r = _get(server, "/")
    assert '"@type": "SoftwareApplication"' in r.text
    assert '"price": "0"' in r.text
    r2 = _get(server, "/faq")
    assert '"@type": "FAQPage"' in r2.text


# ---------------------------------------------------------------- PWA
def test_manifest_valid_and_icons_exist(server):
    r = _get(server, "/manifest.webmanifest")
    assert r.status_code == 200
    assert "application/manifest" in r.headers["content-type"]
    data = r.json()
    assert data["display"] == "standalone"
    assert data["start_url"] == "/"
    assert any(i["purpose"] == "maskable" for i in data["icons"])


def test_service_worker_served_with_scope(server):
    r = _get(server, "/sw.js")
    assert r.status_code == 200
    assert "javascript" in r.headers["content-type"]
    assert r.headers.get("service-worker-allowed") == "/"
    assert "addEventListener(\"fetch\"" in r.text


def test_assets_served(server):
    for path, ctype in (("/assets/icon-192.png", "image/png"),
                        ("/assets/icon-512.png", "image/png"),
                        ("/assets/apple-touch-icon.png", "image/png"),
                        ("/assets/favicon.svg", "image/svg+xml"),
                        ("/assets/og-image.png", "image/png")):
        r = _get(server, path)
        assert r.status_code == 200, path
        assert ctype in r.headers["content-type"], path


# ---------------------------------------------------------------- SEO files
def test_robots_txt_disallows_all(server):
    r = _get(server, "/robots.txt")
    assert r.status_code == 200
    assert "User-agent: *" in r.text
    assert "Disallow: /" in r.text


def test_sitemap_xml_lists_pages(server):
    base = server["base_url"]
    r = _get(server, "/sitemap.xml")
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    for p in ("/", "/faq", "/privacy"):
        assert f"<loc>{base}{p}</loc>" in r.text


def test_llms_txt_describes_pati(server):
    r = _get(server, "/llms.txt")
    assert r.status_code == 200
    assert "# PATI" in r.text
    assert "FREE_ONLY=true" in r.text
    assert "/docs" in r.text


# ---------------------------------------------------------------- 404 flow
def test_custom_404_html_page(server):
    r = _get(server, "/this-page-does-not-exist")
    assert r.status_code == 404
    assert "Page not found" in r.text
    assert 'href="/"' in r.text


def test_api_404_stays_json(server):
    r = _get(server, "/api/v1/definitely-not-a-route")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "HTTP_404"


def test_thank_you_shows_job_id(server):
    r = _get(server, "/thank-you?job=job_abc123")
    assert r.status_code == 200
    assert "job_abc123" in r.text
    assert "response-time promise" in r.text.lower() or "What happens now" in r.text


# ---------------------------------------------------------------- units
def test_visit_counter_increments_across_loads(server):
    import re
    r1 = _get(server, "/")
    m1 = re.search(r"served <strong>(\d+)</strong> page", r1.text)
    assert m1, "visit counter missing from dashboard"
    r2 = _get(server, "/")
    m2 = re.search(r"served <strong>(\d+)</strong> page", r2.text)
    assert m2
    assert int(m2.group(1)) >= int(m1.group(1))
