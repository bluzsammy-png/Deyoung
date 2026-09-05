#!/bin/bash
# One-shot QA for the DeYoung worker plane (server must live inside this call).
set -u
cd /home/z/my-project
export WORKER_TOKEN=dyw_a71c94597566e4a6274020de99e412b5
PORT=3311
BASE=http://localhost:$PORT

echo "[1] boot dev server…"
rm -f .next/dev/lock
PORT=$PORT npx next dev -p $PORT > /tmp/dev-qa.log 2>&1 &
DEVPID=$!
for i in $(seq 1 120); do
  sleep 2
  curl -s -o /dev/null -w "%{http_code}" $BASE/api/health | grep -q 200 && break
done
echo "    health: $(curl -s $BASE/api/health)"

echo "[2] seed queue…"
EMAIL="worker-qa-$(date +%s)@test.deyoung"
SEED=$(node scripts/qa_worker_data.mjs seed "$EMAIL")
echo "    $SEED"
JOB1=$(echo "$SEED" | python3 -c "import json,sys; print(json.load(sys.stdin)['jobIds'][0])")
JOB2=$(echo "$SEED" | python3 -c "import json,sys; print(json.load(sys.stdin)['jobIds'][1])")

echo "[3] auth guards…"
echo -n "    no token   → "; curl -s -X POST $BASE/api/worker/claim -H 'content-type: application/json' -d '{"agent":"anon"}' | head -c 120; echo
echo -n "    wrong token → "; curl -s -X POST $BASE/api/worker/claim -H 'content-type: application/json' -H 'authorization: Bearer dyw_totallywrong12345' -d '{"agent":"anon"}' | head -c 120; echo
echo -n "    good token  → "; curl -s $BASE/api/worker/status -H "authorization: Bearer $WORKER_TOKEN" | head -c 160; echo

echo "[4] run worker (stub, single cycle)…"
python3 workers/deyoung_worker.py --site $BASE --token $WORKER_TOKEN --renderer stub --once --agent qa-burst

echo "[5] verify job1 in DB + download…"
node scripts/qa_worker_data.mjs verify "$EMAIL" "$JOB1"
curl -s -o /tmp/qa-delivered.mp4 -w "    file GET: %{http_code} (%{size_download} bytes)\n" "$BASE/api/worker/file/req-$JOB1.mp4"
curl -s -o /dev/null -w "    range GET: %{http_code}\n" -H "Range: bytes=0-1023" "$BASE/api/worker/file/req-$JOB1.mp4"
ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 /tmp/qa-delivered.mp4 | sed 's/^/    stream: /'

echo "[6] second cycle picks job2…"
python3 workers/deyoung_worker.py --site $BASE --token $WORKER_TOKEN --renderer stub --once --agent qa-burst
node scripts/qa_worker_data.mjs verify "$EMAIL" "$JOB2"

echo "[7] empty queue behavior…"
curl -s -X POST $BASE/api/worker/claim -H 'content-type: application/json' -H "authorization: Bearer $WORKER_TOKEN" -d '{"agent":"qa"}' | head -c 160; echo

echo "[8] cleanup…"
node scripts/qa_worker_data.mjs cleanup "$EMAIL" "$JOB1"
node scripts/qa_worker_data.mjs cleanup "$EMAIL" "$JOB2"
kill $DEVPID 2>/dev/null
echo "QA DONE"
