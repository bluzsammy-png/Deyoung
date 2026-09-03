"""Core API: health, registries, FREE_ONLY enforcement, quotas, status."""
from __future__ import annotations

import httpx


def test_health(server):
    r = httpx.get(f"{server['base_url']}/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["free_only"] is True
    assert body["max_spend"] == 0


def test_version_header(server):
    r = httpx.get(f"{server['base_url']}/health")
    assert "X-PATI-Version" in r.headers


def test_registries(admin):
    caps = admin.get_capabilities()
    assert len(caps) >= 80
    ids = {c["capability_id"] for c in caps}
    # master-prompt capability coverage across every category
    for required in ["text_generation", "coding", "web_research", "image_generation",
                     "text_to_video", "text_to_speech", "filesystem_operations",
                     "app_generation", "container_execution", "filesystem_organize",
                     "artifact_save_local", "music_generation", "OCR"]:
        assert required in ids, required

    models = admin.list_models()
    assert models, "model registry must not be empty"
    for m in models:
        assert m["cost"] == 0, "every model must be $0"
        assert m["free_status"] in ("FREE_FOREVER", "FREE_WITH_LIMITS",
                                    "OPEN_SOURCE_SELF_HOSTED")
    providers = {m["provider"] for m in models}
    assert "kaggle-hosted" in providers, "free GPU path must exist"

    tools = admin.list_tools()
    tool_ids = {t["tool_id"] for t in tools}
    assert {"fs.organize", "artifact.save", "report.markdown"} <= tool_ids


def test_system_status(admin):
    st = admin.get_system_status()
    assert st["policy"]["FREE_ONLY"] is True
    assert st["policy"]["MAX_SPEND"] == 0
    assert st["policy"]["PAID_FALLBACKS"] is False


def test_quotas(admin):
    q = admin.get_quotas()
    assert q["quotas"]["max_concurrent_tasks"] >= 1
    assert q["quotas"]["gpu_minutes_per_day"] > 0


def test_dashboard_public(server):
    r = httpx.get(f"{server['base_url']}/")
    assert r.status_code == 200
    assert "PATI Dashboard" in r.text
    assert "FREE_ONLY = true" in r.text
    # PWA wiring + social meta present
    assert 'rel="manifest"' in r.text
    assert 'property="og:image"' in r.text
    assert 'rel="canonical"' in r.text


def test_tool_discovery(admin):
    hits = admin.discover_tool("organize")
    assert any(t["tool_id"] == "fs.organize" for t in hits)
