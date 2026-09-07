#!/usr/bin/env python3
"""DeYoung Railway cutover via GraphQL backboard API (the v4 CLI rejects project
tokens, but the API accepts them fine — verified 2026-09-07).

Steps:
  1. locate project (QuantEdge Terminal) -> production environment
  2. upsert ALL production env vars from the vault (skipDeploys=true each)
  3. redeploy the latest deployment of service 1a50a560… (single clean deploy)
  4. watch the new deployment until CR_SUCCESS / failure / 12-min timeout

Prints variable NAMES and lengths only — never values.
Env: RAILWAY_TOKEN must be set (owner-provided project token).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
API = "https://backboard.railway.app/graphql/v2"
PROJECT_ID = "99f9348d-fb56-4411-b48b-fde2ed9f0e14"
SERVICE_ID = "1a50a560-4211-4309-b195-aa2b569afc8f"
UA = "deyoung-cutover/1.0"
TIMEOUT_SECS = 12 * 60

TOKEN = os.environ.get("RAILWAY_TOKEN", "").strip()
if not TOKEN:
    sys.exit("FATAL: export RAILWAY_TOKEN first")


def gql(query, variables=None, timeout=30):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(API, data=payload, headers={
        "Authorization": f"Bearer {TOKEN}", "content-type": "application/json", "User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (502, 503, 504) and attempt < 2:
                time.sleep(3)
                continue
            raise
    if out.get("errors"):
        raise RuntimeError(f"GraphQL errors: {json.dumps(out['errors'])[:300]}")
    return out["data"]


def vault_vars():
    sp = json.load(open(f"{ROOT}/workers/secrets/supabase.json"))
    kt = json.load(open(f"{ROOT}/workers/secrets/kaggle_tokens.json"))
    return {
        # deploy/start.sh contract: DATABASE_URL = SESSION pooler :5432 (+schema);
        # start.sh rewrites the app runtime to :6543+pgbouncer itself. NEVER hand it :6543.
        "DATABASE_URL": sp["supabase"]["database_url_session_pooler"] + "?schema=deyoung",
        "DIRECT_URL": sp["supabase"]["database_url_session_pooler"] + "?schema=deyoung",
        "SUPABASE_URL": sp["supabase"]["supabase_url"],
        "SUPABASE_SERVICE_ROLE_KEY": sp["supabase"]["service_role_key"],
        "STORAGE_DRIVER": "supabase",
        "AUTH_SECRET": sp["auth_secret"]["value"],
        "ADMIN_BOOTSTRAP_PASSWORD": sp["admin_bootstrap"]["password"],
        "WORKER_TOKEN": kt["worker_plane"]["current_token"],
    }


def latest_deployment(env_id):
    q = """query Deployments($input: DeploymentListInput!) {
      deployments(first: 5, input: $input) {
        edges { node { id status createdAt staticUrl } }
      }
    }"""
    d = gql(q, {"input": {"serviceId": SERVICE_ID, "projectId": PROJECT_ID, "environmentId": env_id}})
    edges = d["deployments"]["edges"]
    if not edges:
        return None, None
    edges.sort(key=lambda e: e["node"]["createdAt"] or "", reverse=True)
    n = edges[0]["node"]
    return n["id"], n


def main():
    # 1. production environment
    d = gql('{project(id:"%s"){environments{edges{node{id name}}}}}' % PROJECT_ID)
    envs = [e["node"] for e in d["project"]["environments"]["edges"]]
    prod = next((e for e in envs if e["name"] == "production"), None) or (envs[0] if len(envs) == 1 else None)
    if not prod:
        sys.exit(f"FATAL: no production environment found; envs={[e['name'] for e in envs]}")
    env_id = prod["id"]
    print(f"[1] project OK, environment: {prod['name']} ({env_id})")

    # 2. upsert variables (skipDeploys=true -> one clean redeploy afterwards)
    vvars = vault_vars()
    print(f"[2] upserting {len(vvars)} variables (skipDeploys=true):")
    for name, value in vvars.items():
        if not value:
            sys.exit(f"FATAL: vault value for {name} is empty")
        m = """mutation Upsert($input: VariableUpsertInput!) {
          variableUpsert(input: $input)
        }"""
        gql(m, {"input": {"projectId": PROJECT_ID, "environmentId": env_id,
                          "serviceId": SERVICE_ID, "name": name, "value": value,
                          "skipDeploys": True}})
        print(f"    + {name} ({len(value)} chars)")
    print("    all variables applied")

    # 3. redeploy latest deployment
    dep_id, dep = latest_deployment(env_id)
    if not dep_id:
        sys.exit("FATAL: no existing deployment found to redeploy (service never deployed?)")
    print(f"[3] redeploying latest deployment {dep_id} (was {dep['status']}, {dep['createdAt']})")
    m = """mutation RD($id: String!) { deploymentRedeploy(id: $id) { id status createdAt } }"""
    r = gql(m, {"id": dep_id})
    new_dep = r["deploymentRedeploy"]
    new_id = new_dep["id"]
    print(f"    new deployment: {new_id} status={new_dep['status']}")

    # 4. watch until settled
    print(f"[4] watching deployment {new_id} (max {TIMEOUT_SECS // 60} min)…")
    t0 = time.time()
    q = """query D($id: String!) { deployment(id: $id) { id status createdAt } }"""
    final = None
    while time.time() - t0 < TIMEOUT_SECS:
        time.sleep(20)
        dep = gql(q, {"id": new_id})["deployment"]
        st = dep["status"]
        print(f"    {int(time.time() - t0):>4}s  {st}")
        if st in ("CR_SUCCESS", "SUCCESS", "DEPLOY_LIVE"):
            final = st
            break
        if st in ("CR_FAILED", "FAILED", "CR_CRASHED", "CRASHED", "CR_CANCELLED", "CANCELLED"):
            final = st
            break
    if final in ("CR_SUCCESS", "SUCCESS", "DEPLOY_LIVE"):
        print("DEPLOY GREEN — cutover applied. Verify externally: /api/health 200; worker claim with NEW token = 200; old token = 401.")
    elif final:
        print(f"DEPLOY FAILED ({final}) — check Railway dashboard logs immediately.")
        sys.exit(2)
    else:
        print("TIMEOUT waiting for deploy (still building?) — check dashboard; build can take >12 min on cold cache.")
        sys.exit(3)


if __name__ == "__main__":
    main()
