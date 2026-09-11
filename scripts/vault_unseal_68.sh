#!/usr/bin/env bash
# Task 68 — owner delivered the real vault passphrase. Unseal -> merge new
# plane tokens -> re-seal -> round-trip verify -> restore fleet secrets.
#
# SAFETY (same discipline as vault_try_63.sh):
#   * passphrase arrives as $1 (argv), NEVER echoed, NEVER written to any
#     tracked file; script lives in tracked scripts/ so it holds no value
#   * decrypted tree lives only in a 0700 mktemp dir, shredded on exit
#   * only file NAMES and OK/FAIL verdicts are printed — no contents
#   * old blob is replaced ONLY after a clean unseal + structure check
#   * new blob is kept ONLY if a full round-trip hash verify passes
set -eu
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BLOB="$ROOT/vault/vault.enc"
PASS="${1:-}"
[ -n "$PASS" ] || { echo "FATAL: passphrase required as argv[1]"; exit 1; }
[ -f "$BLOB" ] || { echo "FATAL: $BLOB missing"; exit 1; }
umask 077
TMP=$(mktemp -d)
TMP2=$(mktemp -d)
trap 'rm -rf "$TMP" "$TMP2"' EXIT

# --- 1. UNSEAL (no writes to the blob yet) ---
if ! openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$BLOB" -pass pass:"$PASS" 2>/dev/null \
     | tar xzf - -C "$TMP" 2>/dev/null; then
  echo "FATAL: decrypt/untar failed — passphrase rejected, blob UNTOUCHED"
  exit 2
fi
[ -d "$TMP/workers/secrets" ] || { echo "FATAL: unsealed tree lacks workers/secrets — aborting"; exit 3; }
echo "UNSEAL: OK"
echo "--- unsealed inventory (names only) ---"
find "$TMP" -type f | sed "s|$TMP/||" | sort

# --- 2. MERGE the two new-plane token files (Task 67 ingest) ---
for f in baidu_tokens.json modelscope_tokens.json; do
  if [ -f "$ROOT/workers/secrets/$f" ]; then
    cp "$ROOT/workers/secrets/$f" "$TMP/workers/secrets/$f"
    echo "MERGE: $f added"
  else
    echo "MERGE: $f MISSING in sandbox (skipped!)"; fi
done
chmod 600 "$TMP"/workers/secrets/* 2>/dev/null || true

# --- 3. RE-SEAL from the tmp root, preserving original top-level entries ---
ENTRIES=$(cd "$TMP" && ls -A)
tar czf - -C "$TMP" $ENTRIES 2>/dev/null \
  | openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -out "$BLOB.new" -pass pass:"$PASS" 2>/dev/null
chmod 600 "$BLOB.new"
echo "RESEAL: wrote $BLOB.new ($(wc -c < "$BLOB.new") bytes)"

# --- 4. ROUND-TRIP VERIFY: decrypt the NEW blob, hash-compare vs tmp tree ---
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$BLOB.new" -pass pass:"$PASS" 2>/dev/null \
  | tar xzf - -C "$TMP2" 2>/dev/null
if diff <(cd "$TMP"  && find . -type f -exec sha256sum {} \; | sort -k2) \
        <(cd "$TMP2" && find . -type f -exec sha256sum {} \; | sort -k2) >/dev/null; then
  echo "ROUNDTRIP: hash-identical PASS"
else
  echo "ROUNDTRIP: MISMATCH — keeping old blob, aborting"; exit 4
fi

# --- 5. COMMIT: swap blobs, restore the full fleet into the sandbox ---
mv "$BLOB.new" "$BLOB"
cp -r "$TMP/workers/secrets/." "$ROOT/workers/secrets/"
[ -f "$TMP/.env.local" ] && { cp "$TMP/.env.local" "$ROOT/.env.local"; echo "RESTORE: .env.local"; }
chmod 600 "$ROOT"/workers/secrets/* "$ROOT/.env.local" 2>/dev/null || true
echo "RESTORE: workers/secrets/ now holds:"
ls "$ROOT/workers/secrets/"
echo "DONE"
