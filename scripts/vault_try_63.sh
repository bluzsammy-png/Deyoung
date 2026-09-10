#!/usr/bin/env bash
# Task 63 — bounded vault-passphrase recovery attempt (owner-authorized).
# Tries a SHORT list of high-probability candidates against vault/vault.enc
# using the exact selfheal pipeline (openssl AES-256-CBC/PBKDF2-600k + tar).
#
# SAFETY:
#   * candidates live ONLY in a 0600 file inside the gitignored vault dir
#   * the winning candidate is NEVER echoed, logged, or stored — it is passed
#     straight to selfheal.sh as argv on this single-user sandbox
#   * the candidates file is SHREDDED unconditionally on exit
#   * on success the script continues into the full fleet-resume chain
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOB="$ROOT/vault/vault.enc"
CAND="$ROOT/workers/secrets/.cand_63.txt"
umask 077

shred_candidates() { [ -f "$CAND" ] && shred -u "$CAND" 2>/dev/null || rm -f "$CAND"; }
trap shred_candidates EXIT

[ -f "$BLOB" ] || { echo "FATAL: $BLOB missing"; exit 1; }

# Bounded, honest candidate list (site/project-derived guesses only).
cat > "$CAND" <<'CANDS'
deyoung
deyoungltd
deyoungltd.site
DeYoung
deyoung2026
deyoungltd2026
Deyoung2026
deyoung-vault
deyoung vault
deyoungsltd
youngwilly
deyoung-w2
deyoungfleet
deyoung-master
Deyoung!2026
deyoungltd.site:2026
CANDS

N=0
WIN=""
while IFS= read -r c; do
  [ -n "$c" ] || continue
  N=$((N+1))
  TMP=$(mktemp -d)
  if openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$BLOB" -pass pass:"$c" 2>/dev/null \
       | tar xzf - -C "$TMP" 2>/dev/null; then
    if [ -d "$TMP/workers/secrets" ]; then
      WIN="$c"
      rm -rf "$TMP"
      break
    fi
  fi
  rm -rf "$TMP"
done < "$CAND"

if [ -z "$WIN" ]; then
  echo "NO_CANDIDATE_MATCHED (tried=$N)"
  exit 2
fi

echo "VAULT_UNSEALED — candidate accepted (value not shown). Restoring fleet..."
bash "$ROOT/scripts/selfheal.sh" "$WIN" || { echo "SELFHEAL_FAILED"; exit 3; }

echo "--- vault contents check (names only) ---"
ls "$ROOT/workers/secrets/" | head -12
[ -f "$ROOT/workers/secrets/lightning_tokens.json" ] && echo "lightning_tokens.json: PRESENT" || echo "lightning_tokens.json: MISSING"

echo "--- fleet resume: start deyoung-h3 studio (Task 61 starter) ---"
python3 "$ROOT/scripts/lightning_start_61.py" 2>&1 | tail -15 || echo "START61_NONZERO_EXIT"

echo "--- doctor: layered truth + bounded recovery ---"
python3 "$ROOT/scripts/h3_doctor_61.py" --recover --json 2>&1 | tail -30 || echo "DOCTOR_NONZERO_EXIT"
