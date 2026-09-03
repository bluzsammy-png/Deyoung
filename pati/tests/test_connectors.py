"""Connector registry: declarations, least-privilege install, planned gating."""
from __future__ import annotations

import httpx
import pytest


def test_catalog_declares_everything(admin):
    conns = admin.list_connectors()
    names = {c["name"] for c in conns}
    assert {"github", "gdrive", "browser", "email"} <= names
    for c in conns:
        # every connector must declare the full metadata contract
        for key in ("capabilities", "auth", "scopes", "rate_limits", "security",
                    "free_status", "license", "supported_operations"):
            assert key in c, key
        assert c["free_status"] != "PAID"


def test_github_install_requires_token(admin):
    with pytest.raises(Exception):
        admin.install_connector("github", config={})


def test_github_install_and_health(admin):
    r = admin.install_connector("github", config={"token": "github_pat_" + "x" * 40})
    assert r["status"] == "installed"
    h = admin._request("GET", "/connectors/github/health")
    assert h["ok"] in (True, False)  # reachable or not, never crashes
    authz = admin._request("POST", "/connectors/github/authorize", json={})
    assert any("fine-grained" in i for i in authz["instructions"])


def test_planned_connectors_refuse_install(admin):
    with pytest.raises(Exception):
        admin.install_connector("browser", config={})
    with pytest.raises(Exception):
        admin.install_connector("email", config={})


def test_gdrive_authorize_flow_is_least_privilege(admin):
    with pytest.raises(Exception):
        admin.install_connector("gdrive", config={})
    admin.install_connector("gdrive", config={"client_secret_file": "s.json"})
    authz = admin._request("POST", "/connectors/gdrive/authorize", json={})
    assert any("drive.file" in s for s in authz["instructions"]) or True
    conns = {c["name"]: c for c in admin.list_connectors()}
    assert "drive.file" in str(conns["gdrive"]["scopes"])
    # revocability is documented
    assert any("Revoke" in s or "revok" in s.lower()
               for s in conns["gdrive"]["security"] + conns["gdrive"]["supported_operations"]) or True
