#!/usr/bin/env bash
# DeYoung self-heal — ONE command after any sandbox rebuild. Idempotent.
#
#   bash scripts/selfheal.sh "<vault passphrase>"
#
# What it does (in order, safe to re-run any time):
#   1. Restores workers/secrets/ + .env.local from the tracked encrypted blob
#      vault/vault.enc (AES-256-CBC, PBKDF2 600k) if they are missing.
#   2. Ensures the Kaggle CLI is installed.
#   3. Boots the fleet brain loop (brain_boot.sh, idempotent).
#   4. Prints one-line status: brain + canary.
#
# Passphrase custody: held by the OWNER (saved out-of-band) and repeated in the
# agent chat history. NEVER stored in any tracked file, never logged here.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PASS="${1:-}"
BLOB="$ROOT/vault/vault.enc"

# --- 1. vault restore (only when missing) ---
if [ ! -f "$ROOT/workers/secrets/kaggle_tokens.json" ]; then
  if [ ! -f "$BLOB" ]; then
    echo "FATAL: vault missing and $BLOB not found (repo checkout incomplete?)"
    exit 1
  fi
  if [ -z "$PASS" ]; then
    # Task 63: try the PRIVATE vault mirror before demanding the passphrase
    # (post-bootstrap this makes rebuilds fully owner-independent).
    if bash "$ROOT/scripts/vault_mirror_pull_63.sh" 2>>"$ROOT/brain/selfheal_mirror.log"; then
      echo "[selfheal] VAULT RESTORED from private mirror (no passphrase needed)"
      bash "$ROOT/scripts/brain_boot.sh" start
      bash "$ROOT/scripts/brain_boot.sh" status
      exit 0
    else
      echo "VAULT MISSING -> passphrase required:"
      echo "  bash scripts/selfheal.sh '<vault passphrase>'   (owner has it; also in agent chat history)"
      exit 1
    fi
  fi
  TMP=$(mktemp -d)
  if openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -in "$BLOB" -pass pass:"$PASS" \
       2>/dev/null | tar xzf - -C "$TMP" 2>/dev/null; then
    mkdir -p "$ROOT/workers/secrets"
    cp -r "$TMP/workers/secrets/." "$ROOT/workers/secrets/" 2>/dev/null
    [ -f "$TMP/.env.local" ] && cp "$TMP/.env.local" "$ROOT/.env.local"
    chmod 600 "$ROOT"/workers/secrets/* "$ROOT/.env.local" 2>/dev/null
    rm -rf "$TMP"
    echo "[selfheal] VAULT RESTORED from repo blob (workers/secrets + .env.local)"
  else
    rm -rf "$TMP"
    echo "FATAL: decrypt failed — wrong passphrase? (owner holds it; also in agent chat history)"
    exit 1
  fi
else
  echo "[selfheal] vault intact — no restore needed"
fi

# --- 2. kaggle CLI ---
if ! command -v kaggle >/dev/null 2>&1 && [ ! -x "$HOME/.venv/bin/kaggle" ]; then
  echo "[selfheal] installing kaggle CLI ..."
  pip3 install -q kaggle 2>&1 | tail -1 || "$HOME/.venv/bin/pip3" install -q kaggle 2>&1 | tail -1
fi
echo "[selfheal] kaggle CLI: $(command -v kaggle || echo "$HOME/.venv/bin/kaggle")"

# --- 3. brain loop ---
bash "$ROOT/scripts/brain_boot.sh" start

# --- 4. status ---
bash "$ROOT/scripts/brain_boot.sh" status
echo "[selfheal] done. Check canary: kaggle kernels status youngwilly/deyoung-v2-c01"
