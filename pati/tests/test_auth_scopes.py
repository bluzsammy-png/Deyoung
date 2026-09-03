"""AuthN/AuthZ: scopes, token kinds, revocation, rate limiting, pairing."""
from __future__ import annotations

import httpx

from pati.errors import APIError


def test_missing_token_rejected(server):
    r = httpx.get(f"{server['base_url']}/api/v1/tasks")
    # TestClient base_url is virtual; use direct client instead
    assert r.status_code in (401,)


def test_scopes_enforced(server, admin):
    # create a limited client token without admin scope
    tok = admin.issue_token("limited", kind="client")
    assert tok["kind"] == "client"
    r = httpx.get(f"{server['base_url']}/api/v1/admin/tokens",
                  headers={"Authorization": f"Bearer {tok['token']}"})
    assert r.status_code == 403


def test_worker_token_bound_to_own_worker(server, admin):
    a = admin.register_worker(name="w1", wtype="LOCAL_WORKER", capabilities=["system_inspection"])
    b = admin.register_worker(name="w2", wtype="LOCAL_WORKER", capabilities=["system_inspection"])
    h = {"Authorization": f"Bearer {a['token']}"}
    r = httpx.post(f"{server['base_url']}/api/v1/workers/{b['worker_id']}/heartbeat",
                   json={"resources": {}}, headers=h)
    assert r.status_code == 403, "worker A must not act as worker B"
    r = httpx.post(f"{server['base_url']}/api/v1/workers/{a['worker_id']}/heartbeat",
                   json={"resources": {}}, headers=h)
    assert r.status_code == 200


def test_revocation(server, admin, client_factory):
    tok = admin.issue_token("revoked-soon", kind="client")
    c = client_factory(tok["token"])
    assert c.list_workers() == c.list_workers()  # works
    token_id = tok["id"]
    r = httpx.post(f"{server['base_url']}/api/v1/admin/tokens/{token_id}/revoke",
                   headers={"Authorization": f"Bearer {server['admin_token']}"}, json={})
    assert r.status_code == 200
    import pytest
    from pati.errors import APIError
    with pytest.raises(APIError) as e:
        c.list_workers()
    assert e.value.status == 401


def test_pairing_code_flow(server, admin, client_factory):
    code = admin.create_pairing_code()
    assert len(code["code"]) == 6
    # register an agent with the pairing code and NO admin token
    r = httpx.post(f"{server['base_url']}/api/v1/workers/register", json={
        "name": "wizard-pc", "type": "LOCAL_WORKER",
        "capabilities": ["system_inspection"], "pairing_code": code["code"]})
    assert r.status_code == 200
    body = r.json()
    assert body["worker_id"].startswith("wrk_")
    assert body["token"].startswith("pati_worker_")
    # pairing codes are single-use
    r2 = httpx.post(f"{server['base_url']}/api/v1/workers/register", json={
        "name": "wizard-pc-2", "type": "LOCAL_WORKER",
        "capabilities": [], "pairing_code": code["code"]})
    assert r2.status_code == 401


def test_rate_limit(server, admin, monkeypatch):
    from pati_api import config, security
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 60, raising=True)
    security._rate_buckets.clear()
    tok = admin.issue_token("ratelimited", kind="client")
    h = {"Authorization": f"Bearer {tok['token']}"}
    codes = []
    for _ in range(90):
        r = httpx.get(f"{server['base_url']}/api/v1/tasks", headers=h)
        codes.append(r.status_code)
        if r.status_code == 429:
            break
    assert 429 in codes, "sliding-window rate limiter must engage"
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 100000, raising=True)
    security._rate_buckets.clear()
