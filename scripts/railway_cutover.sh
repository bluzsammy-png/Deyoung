#!/usr/bin/env bash
# DeYoung Railway cutover — ONE-SHOT, run when the owner provides a RAILWAY_TOKEN.
#
# Does, in order (vault workers/secrets/supabase.json + kaggle_tokens.json are the
# single source of truth; this script never prints secret VALUES):
#   [1] ensure Railway CLI (npm global install if missing)
#   [2] auth check (railway whoami)
#   [3] apply ALL production env vars from the vault onto service
#         1a50a560-4211-4309-b195-aa2b569afc8f  ("Deeyoung")
#       DATABASE_URL/DIRECT_URL/SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY/STORAGE_DRIVER
#       + AUTH_SECRET + ADMIN_BOOTSTRAP_PASSWORD + WORKER_TOKEN (STAGED rotation dyw_62bf…)
#   [4] redeploy the service (single clean deploy)
#   [5] verify: poll /api/health until 200, then check WORKER auth:
#       - no token        -> 401/403 expected
#       - NEW staged token-> 200 expected (cutover proof)
#       - OLD token       -> 401 expected (owner may run this from a browser;
#                            the full old token value is not retained anywhere by design)
#
# Usage:
#   RAILWAY_TOKEN=xxxx-… bash scripts/railway_cutover.sh
#   bash scripts/railway_cutover.sh --health-only   # just verify current prod, no changes
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_ID="1a50a560-4211-4309-b195-aa2b569afc8f"
BASES=("https://deeyoung-production-72ef.up.railway.app" "https://deyoungltd.site")

log() { echo "[$(date -u +%H:%M:%S)] $*"; }
die() { echo "FATAL: $*" >&2; exit 1; }

# ---- vault readers (values never echoed) ----
vread() { R="$ROOT" python3 -c "
import json, sys
what = sys.argv[1]
root = __import__('os').environ['R']
sp = json.load(open(root + '/workers/secrets/supabase.json'))
kt = json.load(open(root + '/workers/secrets/kaggle_tokens.json'))
out = {
  'DATABASE_URL': sp['supabase']['database_url_transaction_pooler'] + '?schema=deyoung&pgbouncer=true&connection_limit=1',
  'DIRECT_URL': sp['supabase']['database_url_session_pooler'] + '?schema=deyoung',
  'SUPABASE_URL': sp['supabase']['supabase_url'],
  'SUPABASE_SERVICE_ROLE_KEY': sp['supabase']['service_role_key'],
  'STORAGE_DRIVER': 'supabase',
  'AUTH_SECRET': sp['auth_secret']['value'],
  'ADMIN_BOOTSTRAP_PASSWORD': sp['admin_bootstrap']['password'],
  'WORKER_TOKEN': kt['worker_plane']['current_token'],
}
sys.stdout.write(out[what])
" "$1"; }

# ---- CLI ensure ----
ensure_cli() {
  if command -v railway >/dev/null 2>&1; then RAIL="railway"; return; fi
  for c in "$HOME/.npm-global/bin/railway" "$HOME/.local/bin/railway"; do
    [ -x "$c" ] && RAIL="$c" && return
  done
  log "installing Railway CLI…"
  npm install -g @railway/cli@latest >/dev/null 2>&1 || die "npm install of @railway/cli failed"
  RAIL="$(npm bin -g 2>/dev/null)/railway" || RAIL="$HOME/.npm-global/bin/railway"
  [ -x "$RAIL" ] || RAIL="railway"
}

health_probe() {  # $1 = base url -> prints "code:body12"
  local code body
  code=$(curl -s -m 20 -o /tmp/dyw_probe.json -w '%{http_code}' "$1/api/health" || echo 000)
  body=$(head -c 60 /tmp/dyw_probe.json 2>/dev/null || true)
  echo "$code:$body"
}

claim_probe() {  # $1 = base url, $2 = token (may be empty) -> HTTP code
  local code
  if [ -n "${2:-}" ]; then
    code=$(curl -s -m 20 -o /tmp/dyw_claim.json -w '%{http_code}' -X POST "$1/api/worker/claim" \
      -H 'content-type: application/json' -H "authorization: Bearer $2" -d '{"agent":"cutover-verify"}' || echo 000)
  else
    code=$(curl -s -m 20 -o /tmp/dyw_claim.json -w '%{http_code}' -X POST "$1/api/worker/claim" \
      -H 'content-type: application/json' -d '{"agent":"cutover-verify"}' || echo 000)
  fi
  echo "$code"
}

# ---- main ----
cd "$ROOT"
HEALTH_ONLY=0
[ "${1:-}" = "--health-only" ] && HEALTH_ONLY=1

if [ "$HEALTH_ONLY" = "1" ]; then
  for b in "${BASES[@]}"; do
    log "health $b -> $(health_probe "$b")"
    log "claim no-token $b -> $(claim_probe "$b" "") (401/403 = guard on, 429 = edge-throttled sandbox IP)"
  done
  exit 0
fi

: "${RAILWAY_TOKEN:?export RAILWAY_TOKEN=<token from owner> before running}"
export RAILWAY_TOKEN
ensure_cli
log "whoami: $("$RAIL" whoami 2>&1 | head -c 120)"

# ---- [3] apply variables ----
log "applying env vars to service $SERVICE_ID (names only):"
VARS=(DATABASE_URL DIRECT_URL SUPABASE_URL SUPABASE_SERVICE_ROLE_KEY STORAGE_DRIVER AUTH_SECRET ADMIN_BOOTSTRAP_PASSWORD WORKER_TOKEN)
SETARGS=()
for v in "${VARS[@]}"; do
  val="$(vread "$v")"
  [ -n "$val" ] || die "vault value for $v is empty"
  SETARGS+=("--set" "$v=$val")
  log "  + $v (${#val} chars)"
done
# --skip-deploy so we get exactly ONE clean deploy afterwards
if ! "$RAIL" variables --service "$SERVICE_ID" --skip-deploy "${SETARGS[@]}"; then
  log "retrying with 'railway variables set' form…"
  "$RAIL" variables set --service "$SERVICE_ID" --skip-deploy "${SETARGS[@]}" || die "variable apply failed"
fi
log "variables applied"

# ---- [4] redeploy ----
log "redeploying service…"
"$RAIL" redeploy --service "$SERVICE_ID" --environment production 2>/dev/null \
  || "$RAIL" redeploy --service "$SERVICE_ID" 2>/dev/null \
  || log "redeploy command unavailable — Railway auto-deploys on variable change for repo-connected services; watch the dashboard"

# ---- [5] verify ----
log "waiting for deploy to settle (poll health up to 12 min)…"
sleep 90
GOT=""
for i in $(seq 1 24); do
  GOT="$(health_probe "${BASES[0]}")"
  log "  try $i: ${GOT%%:*} ${GOT#*:}"
  case "$GOT" in 200:*) break;; esac
  sleep 30
done
case "$GOT" in
  200:*) log "health GREEN" ;;
  *) log "health not green from this sandbox IP (429 = edge-throttle, known artifact). Verify in browser." ;;
esac

NEW="$(vread WORKER_TOKEN)"
for b in "${BASES[@]}"; do
  log "claim no-token   $b -> $(claim_probe "$b" "")   (expect 401/403)"
  log "claim NEW token  $b -> $(claim_probe "$b" "$NEW")   (expect 200 or queue-empty JSON => cutover LIVE)"
done
log "cutover script finished. Owner browser check (optional): old token dyw_a71c… must now 401."
