#!/usr/bin/env bash
# Task 63 — restore the vault FROM the private mirror (rebuild self-heal).
# Called automatically by scripts/selfheal.sh when the vault is sealed; also
# runnable directly:
#   bash scripts/vault_mirror_pull_63.sh
#
# PAT source (first hit wins): env GH_PAT -> workers/secrets/github.json.
# Any failure exits non-zero SILENTLY (caller falls back to passphrase flow).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIRROR_REPO="bluzsammy-png/deyoung-vault-mirror"
err() { echo "[mirror-pull] $*" >&2; }

PAT="${GH_PAT:-}"
if [ -z "$PAT" ] && [ -f "$ROOT/workers/secrets/github.json" ]; then
  PAT="$(python3 -c "
import json
d=json.load(open('$ROOT/workers/secrets/github.json'))
t=d.get('token') or d.get('pat') or d.get('key') or (d.get('keys') or [{}])[0].get('token') or (d.get('keys') or [{}])[0].get('key','')
print(t if len(str(t))>20 else '')" 2>/dev/null || true)"
fi
[ -n "$PAT" ] || { err "no PAT available"; exit 1; }

PRIV="$(curl -s --max-time 15 -H "Authorization: token $PAT" "https://api.github.com/repos/$MIRROR_REPO" | python3 -c "import json,sys;print(json.load(sys.stdin).get('private'))" 2>/dev/null || echo False)"
[ "$PRIV" = "True" ] || { err "mirror not private/unreachable"; exit 2; }

TMP=$(mktemp -d) || exit 3
trap 'rm -rf "$TMP"' EXIT
git clone -q --depth 1 "https://x-access-token:$PAT@github.com/$MIRROR_REPO.git" "$TMP/m" 2>/dev/null || { err "clone failed"; exit 4; }
[ -d "$TMP/m/workers/secrets" ] || { err "mirror has no secrets yet (run sync after unseal)"; exit 5; }

mkdir -p "$ROOT/workers/secrets"
cp -r "$TMP/m/workers/secrets/." "$ROOT/workers/secrets/" 2>/dev/null
[ -f "$TMP/m/.env.local" ] && cp "$TMP/m/.env.local" "$ROOT/.env.local"
chmod 600 "$ROOT"/workers/secrets/* "$ROOT/.env.local" 2>/dev/null || true
err "restored $(ls "$ROOT/workers/secrets" | wc -l) secret files + .env.local from private mirror"
exit 0
