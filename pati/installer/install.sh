#!/usr/bin/env bash
# PATI installer for macOS / Linux (free stack only).
set -euo pipefail
say()  { echo -e "[PATI] $*"; }
ok()   { echo -e "[ OK ] $*"; }
fail() { echo -e "[FAIL] $*" >&2; exit 1; }

PATI_HOME="${HOME}/.pati"
VENV="${PATI_HOME}/venv"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

say "PATI installer (COST=\$0, FREE_ONLY=true)"

# 1. prerequisites ----------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 not found. Install Python 3.10+ (free): https://www.python.org/downloads/"
fi
PYVER=$(python3 -c 'import sys; print(f"{sys.version_info.major}{sys.version_info.minor}")')
[ "${PYVER}" -ge 310 ] || fail "Python 3.10+ required, found ${PYVER}"
ok "python3 ${PYVER}"

# 2. venv -------------------------------------------------------------------
[ -d "${VENV}" ] || python3 -m venv "${VENV}"
PIP="${VENV}/bin/pip"
PY="${VENV}/bin/python"

# 3. install ----------------------------------------------------------------
say "Installing PATI (free/open-source deps only)..."
"${PIP}" install -e "${REPO_DIR}" >/dev/null
ok "installed into ${VENV}"

# 4. workspace --------------------------------------------------------------
mkdir -p "${PATI_HOME}/workspace" "${HOME}/Projects/AI" "${HOME}/Projects/Video" "${HOME}/Projects/Research"
ok "workspace: ${PATI_HOME}/workspace"

# 5. control plane ----------------------------------------------------------
say "Starting PATI control plane on http://127.0.0.1:8000 ..."
nohup "${VENV}/bin/pati-server" > "${PATI_HOME}/server.log" 2>&1 &
sleep 3
if curl -fsS http://127.0.0.1:8000/health >/dev/null; then ok "control plane healthy"; else
  say "WARN: control plane not answering yet (see ${PATI_HOME}/server.log)"; fi

# 6. pairing code + wizard --------------------------------------------------
export PATI_SERVER="http://127.0.0.1:8000"
if [ -f "${PATI_HOME}/data/bootstrap_admin_token.txt" ]; then
  export PATI_TOKEN="$(cat "${PATI_HOME}/data/bootstrap_admin_token.txt")"
  "${VENV}/bin/pati" admin-pair || true
fi
"${VENV}/bin/pati-agent" setup --server "${PATI_SERVER}"
"${VENV}/bin/pati-agent" doctor || true

say "Optional autostart: copy installer/pati-agent.service to ~/.config/systemd/user/ (Linux)"
say "or installer/com.pati.agent.plist to ~/Library/LaunchAgents/ (macOS)"
say "Done. Try: ${VENV}/bin/pati submit 'Create a folder called Test 01 in my workspace' --wait"
