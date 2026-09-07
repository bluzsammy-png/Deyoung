#!/usr/bin/env python3
"""Build + push the site-render drain kernel to a fleet Kaggle account.

Reads secrets ONLY from the vault (gitignored). The kernel source template is
tracked (campaign/site-worker/deyoung-site-w.py) with {{PLACEHOLDER}} slots;
the pushed kernel file is private on Kaggle.

Usage: python3 scripts/site_worker_make.py <account-slug> [kernel-slug]
  account-slug: deyoungsltd | jimcreat | bittrexminingltd | teslaprime |
                youngwilly | wikeyoung5   (must exist in the vault tokens)
"""
import base64, json, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path("/home/z/my-project")
TEMPLATE = ROOT / "campaign/site-worker/deyoung-site-w.py"

def kaggle_env(token: str):
    home = pathlib.Path("/home/z/.kaggle")
    home.mkdir(exist_ok=True)
    (home / "access_token").write_text(token)
    return {"KAGGLE_CONFIG_DIR": str(home), "HOME": "/home/z"}

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: site_worker_make.py <account-slug> [kernel-slug]")
    account = sys.argv[1]
    kernel = sys.argv[2] if len(sys.argv) > 2 else "deyoung-site-w01"

    fleet = json.loads((ROOT / "workers/secrets/fleet_db.json").read_text())
    supa = json.loads((ROOT / "workers/secrets/supabase.json").read_text())
    tokens = json.loads((ROOT / "workers/secrets/kaggle_tokens.json").read_text())
    tok = next((t for t in tokens["tokens"] if t["account"] == account), None)
    if not tok:
        sys.exit(f"no token for account {account}")

    # session pooler DSN for the scoped role:
    # app DSN = postgresql://postgres.<ref>:pw@aws-1-eu-west-1.pooler.supabase.com:5432/...
    app_url = supa["railway_env"]["DATABASE_URL"]
    import re
    m = re.match(r"postgresql://postgres\.([^.]+):[^@]+@([^:/]+):(\d+)/", app_url)
    if not m:
        sys.exit("unexpected DATABASE_URL shape")
    ref, pooler_host = m.group(1), m.group(2)
    dsn = f"postgresql://deyoung_fleet.{ref}:{fleet['password']}@{pooler_host}:5432/postgres?sslmode=require"

    src = TEMPLATE.read_text()
    src = src.replace("{{DSN}}", dsn)
    src = src.replace("{{SUPA_URL}}", supa["railway_env"]["SUPABASE_URL"].rstrip("/"))
    src = src.replace("{{SUPA_KEY}}", supa["railway_env"]["SUPABASE_SERVICE_ROLE_KEY"])
    src = src.replace("{{AGENT}}", f"kaggle-site-{account}")

    with tempfile.TemporaryDirectory() as td:
        tdp = pathlib.Path(td)
        (tdp / f"{kernel}.py").write_text(src)
        (tdp / "kernel-metadata.json").write_text(json.dumps({
            "id": f"{account}/{kernel}",
            "title": kernel,
            "code_file": f"{kernel}.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": "true",
            "enable_gpu": "true",
            "enable_internet": "true",
            "dataset_sources": [],
            "competition_sources": [],
            "kernel_sources": [],
        }, indent=1))
        env = kaggle_env(tok["token"])
        env_full = {**__import__("os").environ, **env}
        r = subprocess.run(["/home/z/.venv/bin/kaggle", "kernels", "push", "-p", td],
                           capture_output=True, text=True, env=env_full)
        print(r.stdout.strip() or r.stderr.strip())
        if "successfully" not in (r.stdout + r.stderr).lower():
            sys.exit(1)
    print(f"PUSHED {account}/{kernel} at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")

if __name__ == "__main__":
    main()
