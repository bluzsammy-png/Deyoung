#!/usr/bin/env python3
"""Task 65 — verify every Kaggle token LIVE and identify its username.

For each token in workers/secrets/kaggle_tokens.json:
  1. GET https://www.kaggle.com/api/v1/kernels/list?mine=true&pageSize=20
     with `Authorization: Bearer <KGAT_…>`.
  2. 401/403 -> token invalid. 200 -> valid; username = ref prefix of the
     first kernel that has one (falls back to the CLI `kernels list --mine`
     when the REST shape yields nothing).
  3. Also report the account's deyoung-* fleet kernels and their run status.

Updates kaggle_tokens.json in place (account + label_note) when a username is
learned, writes evidence to brain/kaggle_fleet_check_65.json (token values are
NEVER written anywhere). Re-run any time; idempotent.
"""
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
SECRETS = ROOT / "workers" / "secrets" / "kaggle_tokens.json"
EVIDENCE = ROOT / "brain" / "kaggle_fleet_check_65.json"
API = "https://www.kaggle.com/api/v1"


def rest_list(token):
    req = urllib.request.Request(
        f"{API}/kernels/list?mine=true&pageSize=20",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def cli_mine(token):
    env = {**os.environ, "KAGGLE_API_TOKEN": token}
    r = subprocess.run(
        [sys.executable, "-m", "kaggle", "kernels", "list", "--mine", "--page-size", "20"],
        capture_output=True, text=True, timeout=120, env=env,
    )
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def cli_status(token, ref):
    env = {**os.environ, "KAGGLE_API_TOKEN": token}
    r = subprocess.run(
        [sys.executable, "-m", "kaggle", "kernels", "status", ref],
        capture_output=True, text=True, timeout=120, env=env,
    )
    return ((r.stdout or "") + (r.stderr or "")).strip()


def main():
    vault = json.loads(SECRETS.read_text())
    evidence = {"checked": [], "summary": {}}
    for t in vault["tokens"]:
        tok, tid = t["token"], t["id"]
        entry = {"id": tid, "known_account": t.get("account")}
        code, body = rest_list(tok)
        entry["rest_probe"] = code
        username = None
        kernels = []
        if code == 200 and isinstance(body, list):
            for k in body:
                ref = k.get("ref") or ""
                if "/" in ref:
                    u, slug = ref.split("/", 1)
                    username = username or u
                    if slug.startswith("deyoung-"):
                        kernels.append(ref)
        elif code in (401, 403):
            entry["valid"] = False
            entry["error"] = f"HTTP {code}"
            evidence["checked"].append(entry)
            print(f"{tid}: INVALID (HTTP {code})")
            continue
        else:
            # fall back to the CLI, which also proves token validity
            rc, out = cli_mine(tok)
            entry["cli_probe_rc"] = rc
            if rc != 0 and ("401" in out or "403" in out or "Unauthorized" in out):
                entry["valid"] = False
                entry["error"] = "Unauthorized via CLI"
                evidence["checked"].append(entry)
                print(f"{tid}: INVALID (CLI unauthorized)")
                continue
            for line in out.splitlines():
                if "/" in line:
                    cand = line.strip().split()[0]
                    if "/" in cand and not cand.startswith("-"):
                        u, slug = cand.split("/", 1)
                        username = username or u
                        if slug.startswith("deyoung-"):
                            kernels.append(cand)

        entry["valid"] = True
        entry["username"] = username
        entry["fleet_kernels"] = sorted(set(kernels))
        statuses = {}
        for ref in entry["fleet_kernels"][:6]:
            statuses[ref] = cli_status(tok, ref)[:120]
        entry["kernel_statuses"] = statuses
        evidence["checked"].append(entry)
        print(f"{tid}: VALID user={username} fleet_kernels={entry['fleet_kernels']}")

    valid = [e for e in evidence["checked"] if e.get("valid")]
    evidence["summary"] = {
        "valid": len(valid),
        "invalid": len(evidence["checked"]) - len(valid),
        "usernames": {e["id"]: e.get("username") for e in evidence["checked"]},
    }
    EVIDENCE.write_text(json.dumps(evidence, indent=1))
    print("SUMMARY:", json.dumps(evidence["summary"]))

    # update accounts in the vault (never touches token values)
    changed = False
    for t in vault["tokens"]:
        for e in evidence["checked"]:
            if e["id"] == t["id"] and e.get("valid") and e.get("username"):
                if t.get("account") != e["username"]:
                    t["account"] = e["username"]
                    t["label_note"] = f"username identified live 2026-09-11 (task 65 fleet check)"
                    changed = True
    if changed:
        SECRETS.write_text(json.dumps(vault, indent=2))
        SECRETS.chmod(0o600)
        print("kaggle_tokens.json updated with identified usernames")
    else:
        print("kaggle_tokens.json already fully labeled")


if __name__ == "__main__":
    main()
