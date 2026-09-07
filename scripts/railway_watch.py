#!/usr/bin/env python3
"""Watch Railway deployments for the Deeyoung service (Task 41).

Lists the latest deployments; if one is GitHub-triggered (meta.source = github)
and still in flight, polls it to a terminal state. Also dumps boot-log tail on
request via --logs <deploymentId>.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

VAULT = Path("/home/z/my-project/workers/secrets/railway.json")
PROJECT_ID = "99f9348d-fb56-4411-b48b-fde2ed9f0e14"
SERVICE_ID = "1a50a560-4211-4309-b195-aa2b569afc8f"
ENDPOINT = "https://backboard.railway.app/graphql/v2"
UA = "Mozilla/5.0 (X11; Linux x86_64) deyoung-ops/1.0"
TERMINAL = {"SUCCESS", "CRASHED", "ERROR", "REMOVED", "DEPLOY_ERROR", "TIMEOUT", "CANCELED"}


def gql(query, variables=None, timeout=30):
    tok = json.loads(VAULT.read_text())["project_token"]
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json", "User-Agent": UA},
    )
    d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    if d.get("errors"):
        raise RuntimeError(f"GraphQL errors: {d['errors']}")
    return d["data"]


def prod_env():
    d = gql('{project(id:"%s"){environments{edges{node{id name}}}}}' % PROJECT_ID)
    envs = [e["node"] for e in d["project"]["environments"]["edges"]]
    return next((e["id"] for e in envs if e["name"] == "production"), envs[0]["id"])


def list_deployments(env_id, n=5):
    q = """query Deployments($input: DeploymentListInput!) {
      deployments(first: %d, input: $input) {
        edges { node { id status createdAt staticUrl meta { source commitMessage } } }
      }
    }""" % n
    d = gql(q, {"input": {"serviceId": SERVICE_ID, "projectId": PROJECT_ID, "environmentId": env_id}})
    edges = list(d["deployments"]["edges"])
    edges.sort(key=lambda e: e["node"]["createdAt"] or "", reverse=True)
    return [e["node"] for e in edges]


def deployment_logs(dep_id, limit=60):
    q = 'query($id: String!){deployment(id:$id){id status buildLogs}}'
    d = gql(q, {"id": dep_id})
    dep = d["deployment"]
    lines = (dep.get("buildLogs") or "").strip().splitlines()
    return dep["status"], lines[-limit:]


def main():
    env = prod_env()
    deps = list_deployments(env)
    for n in deps:
        m = n.get("meta") or {}
        print(f"DEP {n['id'][:12]} | {n['status']:<10} | {n['createdAt']} | src={m.get('source')} | {(m.get('commitMessage') or '')[:55]}")

    gh = [n for n in deps if (n.get("meta") or {}).get("source") == "github"]
    if not gh:
        print("\nNO github-triggered deployment yet (service not repo-connected, or webhook not fired).")
        return
    gh.sort(key=lambda n: n["createdAt"] or "", reverse=True)
    dep = gh[0]
    print(f"\nWatching github deployment {dep['id'][:12]} (status {dep['status']})...")
    waited = 0
    while dep["status"] not in TERMINAL and waited < 540:
        time.sleep(20)
        waited += 20
        d = gql('query($id: String!){deployment(id:$id){id status}}', {"id": dep["id"]})
        dep["status"] = d["deployment"]["status"]
        print(f"  [{waited:>3}s] {dep['status']}")
    print("FINAL:", dep["status"])
    if dep["status"] not in ("SUCCESS",):
        st, logs = deployment_logs(dep["id"])
        print(f"\n--- build log tail ({st}) ---")
        for ln in logs[-30:]:
            print(" ", ln[:200])


if __name__ == "__main__":
    main()
