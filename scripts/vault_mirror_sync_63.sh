#!/usr/bin/env bash
# Task 63 — push the CURRENT plaintext secrets to the PRIVATE mirror repo
# (bluzsammy-png/deyoung-vault-mirror). Run ONCE after any unseal / secret
# change. After this succeeds, future sandbox rebuilds self-restore with NO
# passphrase and NO owner action (selfheal -> vault_mirror_pull).
#
# Safety:
#   * refuses to push unless the target repo is verified PRIVATE via API
#   * never echoes secret contents; commit messages carry no values
#   * PAT source: env GH_PAT, else workers/secrets/github.json (token/key)
#
#   bash scripts/vault_mirror_sync_63.sh
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIRROR_REPO="bluzsammy-png/deyoung-vault-mirror"

pat() {
  if [ -n "${GH_PAT:-}" ]; then echo "$GH_PAT"; return; fi
  for f in "$ROOT/workers/secrets/github.json"; do
    [ -f "$f" ] && python3 -c "
import json,sys
d=json.load(open('$f'))
t=d.get('token') or d.get('pat') or d.get('key') or (d.get('keys') or [{}])[0].get('token') or (d.get('keys') or [{}])[0].get('key','')
print(t if len(str(t))>20 else '')" 2>/dev/null && return
  done
  return 1
}

PAT="$(pat)" || { echo "FATAL: no PAT (set GH_PAT or unseal vault so workers/secrets/github.json exists)"; exit 1; }
[ -n "$PAT" ] || { echo "FATAL: empty PAT"; exit 1; }

# HARD GUARD: mirror must be private, abort otherwise
PRIV="$(curl -s -H "Authorization: token $PAT" "https://api.github.com/repos/$MIRROR_REPO" | python3 -c "import json,sys;print(json.load(sys.stdin).get('private'))" 2>/dev/null || echo False)"
[ "$PRIV" = "True" ] || { echo "FATAL: $MIRROR_REPO is not private (got: $PRIV) — refusing to push secrets"; exit 2; }

[ -f "$ROOT/workers/secrets/kaggle_tokens.json" ] || [ -f "$ROOT/.env.local" ] \
  || { echo "FATAL: nothing to mirror (vault sealed?)"; exit 3; }

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
git clone -q "https://x-access-token:$PAT@github.com/$MIRROR_REPO.git" "$TMP/m" 2>/dev/null
mkdir -p "$TMP/m/workers"
cp -r "$ROOT/workers/secrets" "$TMP/m/workers/"
[ -f "$ROOT/.env.local" ] && cp "$ROOT/.env.local" "$TMP/m/.env.local"
find "$TMP/m/workers/secrets" -type f -exec chmod 600 {} \; 2>/dev/null
chmod 700 "$TMP/m/workers/secrets" 2>/dev/null || true
cd "$TMP/m"
git config user.email "agent@deyoungltd.site"; git config user.name "deyoung-agent"
git add -A >/dev/null
if git diff --cached --quiet; then echo "mirror already up to date"; exit 0; fi
git commit -qm "vault mirror sync $(date -u +%FT%TZ) (values never in messages)"
git push -q origin main 2>/dev/null || git push -q origin HEAD:main
echo "MIRROR SYNCED (private-verified): workers/secrets + .env.local -> $MIRROR_REPO"
