#!/usr/bin/env bash
# Task 65 — launch one DeYoung render worker on the Kaggle free GPU plane.
# Usage: bash scripts/launch_kaggle_worker_65.sh <k1..k8> [--exit-idle] [--max-minutes 480]
# Reads the KGAT + WORKER_TOKEN from the vault; values are never printed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TOK_ID="${1:?usage: launch_kaggle_worker_65.sh <k1..k8> [extra kaggle_launch args...]}"

eval "$(python3 - "$TOK_ID" <<'PYEOF'
import json, sys, shlex
tok_id = sys.argv[1]
d = json.load(open("workers/secrets/kaggle_tokens.json"))
t = next((t for t in d["tokens"] if t["id"] == tok_id), None)
if not t:
    raise SystemExit(f"token id {tok_id} not in vault")
wt = json.load(open("workers/secrets/worker_token.json"))["token"]
print("export KAGGLE_API_TOKEN=" + shlex.quote(t["token"]))
print("export KAGGLE_USER=" + shlex.quote(t.get("account") or ""))
print("export DEYOUNG_WT=" + shlex.quote(wt))
PYEOF
)"

shift
python3 "$ROOT/scripts/kaggle_launch.py" \
  --site https://deyoungltd.site \
  --token "$DEYOUNG_WT" \
  --renderer ltx \
  --max-minutes 480 \
  "$@"
