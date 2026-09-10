#!/usr/bin/env bash
# Task 63 — ONE-SHOT fleet resume. Run the moment EITHER arrives:
#   bash scripts/fleet_resume_63.sh "<vault passphrase>"     # master key (restores everything)
#   bash scripts/fleet_resume_63.sh --lightning "<key>"      # single-plane key (studio + worker only)
#
# Chain: unseal vault (if passphrase given) -> brain boot -> start deyoung-h3
# studio -> doctor recovery (restart worker, verified by heartbeat) -> prod
# queue probe. Idempotent; every step prints honest PASS/FAIL. No secret is
# ever echoed.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"
PASS="${2:-}"

say() { echo "[resume63] $*"; }

if [ "$MODE" = "--lightning" ]; then
  if [ -z "$PASS" ]; then say "FATAL: --lightning needs the key as arg 2"; exit 1; fi
  say "single-plane mode: writing lightning_tokens.json shape used by Task 55/61 scripts"
  mkdir -p "$ROOT/workers/secrets"
  python3 - "$PASS" <<'PY'
import json, sys, pathlib
p = pathlib.Path("/home/z/my-project/workers/secrets/lightning_tokens.json")
key = sys.argv[1]
data = json.loads(p.read_text()) if p.exists() else {}
if "keys" not in data or not isinstance(data.get("keys"), list):
    data["keys"] = []
if data["keys"]:
    data["keys"][0]["key"] = key
else:
    data["keys"] = [{"key": key}]
p.chmod(0o600) if p.exists() else p.touch(mode=0o600)
p.write_text(json.dumps(data, indent=1))
print("lightning_tokens.json ready (key not printed)")
PY
elif [ -n "$MODE" ] && [ "$MODE" != "--lightning" ]; then
  PASS="$MODE"
fi

if [ -f "$ROOT/workers/secrets/lightning_tokens.json" ]; then
  say "PASS vault/plane credentials present"
else
  if [ -n "$PASS" ]; then
    bash "$ROOT/scripts/selfheal.sh" "$PASS" || { say "FAIL selfheal (wrong passphrase?)"; exit 2; }
  else
    say "FATAL: no credentials and no passphrase — nothing to do"; exit 1
  fi
fi

[ -f "$ROOT/workers/secrets/lightning_tokens.json" ] \
  && say "PASS lightning_tokens.json present" \
  || { say "FAIL lightning key still missing — studio cannot be started from here"; exit 3; }

say "step: brain boot (idempotent)"
bash "$ROOT/scripts/brain_boot.sh" start || true

say "step: start deyoung-h3 studio (T4) — takes up to ~10 min to reach Running"
python3 "$ROOT/scripts/lightning_start_61.py" 2>&1 | tail -8

say "step: doctor — layered truth + bounded worker recovery"
python3 "$ROOT/scripts/h3_doctor_61.py" --recover --json 2>&1 | tail -25

say "step: prod worker-status probe (uses restored WORKER_TOKEN if present)"
if [ -f "$ROOT/.env.local" ]; then
  T="$(grep -E '^WORKER_TOKEN=' "$ROOT/.env.local" | head -1 | cut -d= -f2- | tr -d '\"'"'"'')"
  if [ -n "$T" ]; then
    curl -s --max-time 20 -H "Authorization: Bearer $T" https://deyoungltd.site/api/worker/status | head -c 300
    echo ""
  else
    say "skip: WORKER_TOKEN not found in .env.local"
  fi
else
  say "skip: .env.local absent (passphrase mode only)"
fi

say "done — if doctor reported IDLE/BUSY, the queued customer video will be claimed within ~30s"
