#!/usr/bin/env bash
# macOS/Linux uninstaller.
set -uo pipefail
KEEP_DATA=0; [ "${1:-}" = "--keep-data" ] && KEEP_DATA=1
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.pati.agent.plist 2>/dev/null
rm -f ~/Library/LaunchAgents/com.pati.agent.plist
systemctl --user disable --now pati-agent 2>/dev/null
rm -f ~/.config/systemd/user/pati-agent.service
pkill -f "pati-server" 2>/dev/null
rm -rf ~/.pati/venv
if [ "$KEEP_DATA" = "0" ]; then rm -rf ~/.pati; echo "[PATI] data removed"; else echo "[PATI] data kept in ~/.pati"; fi
echo "[PATI] uninstall complete"
