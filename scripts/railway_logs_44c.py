#!/usr/bin/env python3
"""Task 44-c: fetch latest Railway deployment + its logs, grep for the
prisma db push / seed boot lines. Read-only."""
import json
import os
import sys
import time

import urllib.request

VAULT = os.path.join(os.path.dirname(__file__), "..", "workers", "secrets", "railway.json")
R = json.load(open(VAULT))
TOK = R["project_token"]
SERVICE = R["service_id"]
ENV_ID = "a3f81c18-8929-4a70-9ae6-06f9b9b78a26"  # production (from cutover note)
PROJECT = "99f9348d"  # prefix only; resolved via service query
API = "https://backboard.railway.app/graphql/v2"


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API, data=body, method="POST",
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def main():
    # 1. latest deployments for the service
    q1 = """query($service: String!) {
      service(id: $service) {
        name
        environments { edges { node { id name } } }
      }
    }"""
    d = gql(q1, {"service": SERVICE})
    svc = d.get("data", {}).get("service") or {}
    print("service:", svc.get("name"))
    for e in (svc.get("environments") or {}).get("edges", []):
        n = e["node"]
        print("  env:", n["id"], n["name"])

    q2 = """query($serviceId: String!, $environmentId: String!, $last: Int) {
      deployments(serviceId: $serviceId, environmentId: $environmentId, last: $last) {
        edges { node { id status createdAt url buildLogs } }
      }
    }"""
    d2 = gql(q2, {"serviceId": SERVICE, "environmentId": ENV_ID, "last": 3})
    deps = (d2.get("data", {}).get("deployments") or {}).get("edges", [])
    print(f"\nlatest {len(deps)} deployments:")
    latest = None
    for e in deps:
        n = e["node"]
        print(f"  {n['id']} {n['status']:<10} {n['createdAt']} url={n.get('url')}")
        if latest is None or n["createdAt"] > latest["createdAt"]:
            latest = n
    if not latest:
        print("no deployments found")
        return 1
    print("\n== LOGS of latest deployment:", latest["id"], "==")
    q3 = """query($id: String!, $limit: Int, $offset: Int) {
      deploymentLogs(deploymentId: $id, limit: $limit, offset: $offset)
    }"""
    # deploymentLogs may return {message} entries; paginate a few windows
    logs = []
    for off in range(0, 2000, 500):
        try:
            d3 = gql(q3, {"id": latest["id"], "limit": 500, "offset": off})
            batch = d3.get("data", {}).get("deploymentLogs") or []
            if isinstance(batch, list):
                logs.extend(batch)
            if len(batch) < 500:
                break
        except Exception as ex:
            print("log fetch error at offset", off, ":", ex)
            break
    print(f"fetched {len(logs)} log lines")
    hits = 0
    for ln in logs:
        m = ln.get("message", "") if isinstance(ln, dict) else str(ln)
        low = m.lower()
        if any(k in low for k in ("prisma", "db push", "seed", "[deyoung]", "error", "warning", "schema")):
            print("  |", m[:220])
            hits += 1
            if hits > 60:
                break
    if hits == 0:
        # show the tail anyway
        for ln in logs[-25:]:
            print("  |", (ln.get("message") if isinstance(ln, dict) else str(ln))[:220])
    return 0


if __name__ == "__main__":
    sys.exit(main())
