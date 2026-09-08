#!/usr/bin/env bash
# DeYoung orchestrator boot — idempotent launcher for recovery_orchestrator_51.
# Mirrors brain_boot.sh exactly (plain nohup from an exiting parent — the
# launch pattern proven to survive sandbox reaping; setsid variants died).
#   bash scripts/orch_boot.sh          # ensure orchestrator is running
#   bash scripts/orch_boot.sh status
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PIDF="$ROOT/brain/recovery51.pid"
OUT="$ROOT/brain/recovery51.out"

alive() {
  [ -f "$PIDF" ] || return 1
  local p
  p="$(cat "$PIDF" 2>/dev/null)"
  [ -n "$p" ] && kill -0 "$p" 2>/dev/null
}

case "${1:-start}" in
  status)
    if alive; then
      echo "orchestrator RUNNING (pid $(cat "$PIDF"), since $(ps -o lstart= -p "$(cat "$PIDF")" 2>/dev/null))"
    else
      echo "orchestrator NOT running"
    fi
    ;;
  stop)
    if alive; then kill "$(cat "$PIDF")" && rm -f "$PIDF" && echo "stopped"; else echo "not running"; fi
    ;;
  start|*)
    if alive; then
      echo "orchestrator already RUNNING (pid $(cat "$PIDF"))"
    else
      nohup python3 "$ROOT/scripts/recovery_orchestrator_51.py" >> "$OUT" 2>&1 &
      echo $! > "$PIDF"
      sleep 1
      if alive; then
        echo "orchestrator STARTED (pid $(cat "$PIDF")) -> $OUT"
      else
        echo "orchestrator FAILED to start (see $OUT)"
        exit 1
      fi
    fi
    ;;
esac
