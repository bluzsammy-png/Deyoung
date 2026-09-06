#!/usr/bin/env bash
# DeYoung brain boot — idempotent launcher for the always-on fleet brain loop.
# Safe to run every session; never starts a second loop.
#   bash scripts/brain_boot.sh          # ensure loop is running (60s cadence)
#   bash scripts/brain_boot.sh status   # just report
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDF="$ROOT/brain/loop.pid"
OUT="$ROOT/brain/loop.out"
SECS=60

alive() {
  [ -f "$PIDF" ] || return 1
  local p
  p="$(cat "$PIDF" 2>/dev/null)"
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null
}

case "${1:-start}" in
  status)
    if alive; then
      echo "brain loop RUNNING (pid $(cat "$PIDF"), since $(ps -o lstart= -p "$(cat "$PIDF")" 2>/dev/null))"
      echo "last pass: $(python3 -c "import json;print(json.load(open('$ROOT/brain/state.json')).get('fleet',{}).get('last_pass','?'))" 2>/dev/null)"
    else
      echo "brain loop NOT running"
    fi
    ;;
  stop)
    if alive; then kill "$(cat "$PIDF")" && rm -f "$PIDF" && echo "stopped"; else echo "not running"; fi
    ;;
  start|*)
    if alive; then
      echo "brain loop already RUNNING (pid $(cat "$PIDF"))"
    else
      mkdir -p "$ROOT/brain"
      nohup python3 "$ROOT/scripts/fleet_brain.py" --loop "$SECS" >> "$OUT" 2>&1 &
      echo $! > "$PIDF"
      sleep 1
      if alive; then
        echo "brain loop STARTED (pid $(cat "$PIDF"), every ${SECS}s) -> $OUT"
      else
        echo "FAILED to start; check $OUT" >&2
        exit 1
      fi
    fi
    ;;
esac
