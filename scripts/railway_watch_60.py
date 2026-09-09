#!/usr/bin/env python3
"""Task 60: probe Railway GraphQL for latest deployments (prints raw error bodies)."""
import json
import sys
import urllib.request
from pathlib import Path

VAULT = Path("/home/z/my-project/workers/secrets/railway.json")
PROJECT_ID = "99f9348d-fb56-4411-b48b-fde2ed9f0e14"
SERVICE_ID = "1a50a560-4211-4309-b195-aa2b569afc8f"
ENDPOINT = "https://backboard.railway.app/graphql/v2"
UA = "Mozilla/5.0 (X11; Linux x86_64) deyoung-ops/1.0"


def gql(query, variables=None, timeout=30):
    tok = json.loads(VAULT.read_text())["project_token"]
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "User-Agent": UA},
    )
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        raise
    if d.get("errors"):
        raise RuntimeError(f"GraphQL errors: {d['errors']}")
    return d["data"]


def prod_env():
    d = gql('{project(id:"%s"){environments{edges{node{id name}}}}}' % PROJECT_ID)
    envs = [e["node"] for e in d["project"]["environments"]["edges"]]
    return next((e["id"] for e in envs if e["name"] == "production"), envs[0]["id"])


q = """query Deployments($input: DeploymentListInput!) {
  deployments(first: 5, input: $input) {
    edges { node { id status createdAt staticUrl url meta } }
  }
}"""

env = prod_env()
print("prod env:", env)
d = gql(q, {"input": {"serviceId": SERVICE_ID, "projectId": PROJECT_ID, "environmentId": env}})
edges = list(d["deployments"]["edges"])
edges.sort(key=lambda e: e["node"]["createdAt"] or "", reverse=True)
for n in edges[:5]:
    meta = n.get("meta")
    src = meta.get("source") if isinstance(meta, dict) else meta
    msg = meta.get("commitMessage") if isinstance(meta, dict) else ""
    print(n.get("createdAt"), n.get("status"), n.get("id"), src, "|", (msg or "")[:60], "|", n.get("staticUrl"))
