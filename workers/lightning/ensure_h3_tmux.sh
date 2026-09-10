#!/usr/bin/env bash
# DeYoung H3 worker — tmux session layer (runs INSIDE the Lightning studio).
#
# Role (owner brief, Task 61): tmux is ONLY the persistent-session layer that
# keeps the H3 queue worker alive across SSH/exec disconnection. It is NOT
# orchestration: health truth lives in the worker's heartbeat file, and the
# brain-side doctor (scripts/h3_doctor_61.py) decides ONLINE/UNHEALTHY/etc.
#
# Idempotent. Re-running never double-starts the worker.
# Secrets: read from the 0600 env file INSIDE the tmux pane — never argv,
# never exported into this script's own environment output.
#
# Usage (inside the studio):
#   bash ensure_h3_tmux.sh              # start/ensure the worker session
#   tmux attach -t h3-queue             # (human) attach to the session
#   tmux ls                             # list sessions
set -u

SESSION="h3-queue"
STUDIO_HOME="/teamspace/studios/this_studio"
WORK="$STUDIO_HOME/h3work"
ENV_FILE="$WORK/h3q.env"
LOG="$WORK/h3q.log"
STARTER="$WORK/start_worker.sh"
HEARTBEAT="$WORK/status_h3q.json"

say() { echo "[ensure-h3-tmux] $*"; }

# tmux needs a terminfo name; Jupyter/exec environments ship TERM empty and
# the tmux server then dies with "server exited unexpectedly" (proven live
# in the studio 2026-09-10). Force a sane default BEFORE any tmux call.
export TERM="${TERM:-xterm}"
[ -n "$TERM" ] || export TERM=xterm

# ---- 1. prerequisites -------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
  say "FATAL: $ENV_FILE missing (deploy it first via the doctor/deploy script)"
  exit 10
fi
if [ ! -f "$WORK/h3_queue_worker.py" ]; then
  say "FATAL: $WORK/h3_queue_worker.py missing"
  exit 11
fi

if ! command -v tmux >/dev/null 2>&1; then
  say "tmux not installed — attempting install (needs sudo)…"
  if sudo -n true 2>/dev/null; then
    sudo -n apt-get update -qq 2>/dev/null || sudo -n apt-get update 2>&1 | tail -1
    sudo -n apt-get install -y tmux 2>&1 | tail -2
  else
    sudo apt-get install -y tmux 2>&1 | tail -2   # some images ask nothing
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    say "FATAL: tmux unavailable and install not permitted"
    say "FALLBACK: start with nohup instead (doctor still supervises via heartbeat):"
    say "  bash $STARTER nohup"
    exit 12
  fi
fi
say "tmux: $(tmux -V)"

# ---- 2. starter script (the ONLY thing tmux executes) -----------------------
# The env file is sourced INSIDE the pane so secrets never appear in tmux
# argv, `ps` output of the parent, or this script's logs. Every byte of the
# pane (boot errors included) lands in h3q.log from the first line — a silent
# death is a diagnosable death.
cat > "$STARTER" << 'EOF'
#!/usr/bin/env bash
set -u
WORK="/teamspace/studios/this_studio/h3work"
exec >> "$WORK/h3q.log" 2>&1
echo "[start_worker] launched $(date -u +%FT%TZ) TERM=$TERM"
cd "$WORK" || { echo "[start_worker] CD_FAIL"; exit 1; }
set -a; source "$WORK/h3q.env"; set +a
chmod 600 "$WORK/h3q.env" 2>/dev/null || true
echo "[start_worker] env ok (token len ${#DEYOUNG_WORKER_TOKEN}), exec python"
exec python3 "$WORK/h3_queue_worker.py"
EOF
chmod +x "$STARTER"

# ---- 3. idempotency: already alive? -----------------------------------------
hb_pid() {
  python3 - << 'PYEOF' 2>/dev/null || true
import json
print(json.load(open("/teamspace/studios/this_studio/h3work/status_h3q.json")).get("pid", ""))
PYEOF
}
if tmux has-session -t "$SESSION" 2>/dev/null; then
  PID="$(hb_pid)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    say "already running (session=$SESSION pid=$PID) — nothing to do"
    say "attach:  tmux attach -t $SESSION"
    exit 0
  fi
  say "session exists but worker pid is NOT alive — replacing stale session"
  tmux kill-session -t "$SESSION" 2>/dev/null || true
fi

# ---- 4. start ---------------------------------------------------------------
tmux new-session -d -s "$SESSION" -n worker "$STARTER tmux"
# diagnostics window (only if a monitor exists; never fatal)
if command -v btop >/dev/null 2>&1; then
  tmux new-window -d -t "$SESSION" -n diag "btop"
elif command -v htop >/dev/null 2>&1; then
  tmux new-window -d -t "$SESSION" -n diag "htop"
else
  tmux new-window -d -t "$SESSION" -n diag "watch -n 5 nvidia-smi"
fi
tmux select-window -t "$SESSION:worker"

# ---- 5. verify: heartbeat must appear (session alone proves NOTHING) -------
say "waiting for first heartbeat (up to 90s)…"
for i in $(seq 1 18); do
  sleep 5
  if [ -f "$HEARTBEAT" ]; then
    PID="$(hb_pid)"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      say "OK: worker alive (pid=$PID), heartbeat present"
      say "  attach:   tmux attach -t $SESSION"
      say "  windows:  tmux list-windows -t $SESSION"
      say "  logs:     tail -f $LOG"
      say "  status:   cat $HEARTBEAT"
      exit 0
    fi
  fi
  if ! tmux has-session -t "$SESSION" 2>/dev/null; then
    say "FATAL: session died during startup — last log lines:"
    tail -5 "$LOG" 2>/dev/null || true
    exit 13
  fi
done
say "FATAL: no heartbeat after 90s — worker is NOT verified healthy"
tail -8 "$LOG" 2>/dev/null || true
exit 14
