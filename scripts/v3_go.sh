#!/bin/bash
# DeYoung v3 gate: probe z-ai quota with ONE tiny chat call every 3 min.
# When the limiter opens: finish c8 frame -> submit all scenes -> poll downloads.
cd /home/z/my-project
MAX_WAIT="${1:-3300}"   # seconds to keep probing before giving up this run
START=$(date +%s)

probe_ok() {
  node -e "
import('z-ai-web-dev-sdk').then(async ({default: ZAI}) => {
  try {
    const z = await ZAI.create();
    await z.chat.completions.create({messages:[{role:'user',content:'ok'}], max_tokens: 1});
    console.log('PROBE_OK'); process.exit(0);
  } catch(e) { process.exit(1); }
});" 2>/dev/null
}

while true; do
  NOW=$(date +%s)
  [ $((NOW - START)) -ge "$MAX_WAIT" ] && { echo "GATE_TIMEOUT_STILL_LIMITED"; exit 3; }
  if probe_ok; then
    echo "== quota open at $(date -u +%H:%M:%S) =="
    node scripts/v3_chars.mjs 2>&1 | grep -E "CHARS_DONE"
    node scripts/v3_submit.mjs 2>&1 | grep -vE "^\s+at |Failed to make" | tail -10
    node scripts/v3_poll.mjs "${2:-480}" 2>&1 | grep -vE "^\s+at |Failed" | tail -12
    exit 0
  fi
  echo "$(date -u +%H:%M:%S) still limited, sleeping 180s"
  sleep 180
done
