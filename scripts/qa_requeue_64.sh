#!/usr/bin/env bash
# Task 64 QA — live API E2E for worker-plane list + requeue on a SCRATCH dev
# server (port 3111, local sqlite, throwaway token). Cleans up after itself.
set -u
cd /home/z/my-project
TOK="qa-local-token-0123456789abcdef"
BASE="http://127.0.0.1:3111"
PASS=0; FAIL=0
ck() { # ck <name> <expected> <actual>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); echo "PASS: $1"; else FAIL=$((FAIL+1)); echo "FAIL: $1 (want $2 got $3)"; fi
}

echo "[qa] starting scratch dev server on 3111..."
PORT=3111 WORKER_TOKEN="$TOK" DATABASE_URL="file:/home/z/my-project/db/custom.db" npx next dev -p 3111 >/tmp/dev64.log 2>&1 &
DEVPID=$!
for i in $(seq 1 40); do sleep 2; curl -s -o /dev/null "$BASE" && break; done
curl -s -o /dev/null -w "dev server: %{http_code}\n" "$BASE" --max-time 20

echo "[qa] seeding 3 rows (failed+orphaned / failed+genuine / queued)..."
node - <<'EOF'
const { PrismaClient } = require("@prisma/client");
const p = new PrismaClient({ datasources: { db: { url: "file:/home/z/my-project/db/custom.db" } } });
(async () => {
  await p.videoRequest.deleteMany({ where: { prompt: { startsWith: "QA64:" } } });
  await p.videoRequest.createMany({ data: [
    { subscriptionId: "qa64-sub", email: "qa64@test.local", prompt: "QA64: orphaned row", seconds: 5, resolution: "1080p", status: "failed",
      notes: "orphaned: no worker reported back for 45+ minutes (worker died mid-render) — safe to re-submit" },
    { subscriptionId: "qa64-sub", email: "qa64@test.local", prompt: "QA64: genuine fail", seconds: 5, resolution: "1080p", status: "failed",
      notes: "ComfyUI graph error — reported by qa at 2026-01-01T00:00:00Z" },
    { subscriptionId: "qa64-sub", email: "qa64@test.local", prompt: "QA64: queued row", seconds: 5, resolution: "1080p", status: "queued", notes: "" },
    { subscriptionId: "qa64-sub", email: "qa64@test.local", prompt: "QA64: watchdog row", seconds: 5, resolution: "1080p", status: "failed",
      notes: "render watchdog fired after 35 min — reported by lightning-h3-x" },
    { subscriptionId: "qa64-sub", email: "qa64@test.local", prompt: "QA64: attempt2 row", seconds: 5, resolution: "1080p", status: "failed",
      notes: "orphaned: worker died — prior: requeued by qa attempt=1 after infra-failure" },
  ]});
  const rows = await p.videoRequest.findMany({ where: { prompt: { startsWith: "QA64:" } } });
  for (const r of rows) console.log(r.prompt.split(" ")[1] + "=" + r.id);
  await p.$disconnect();
})();
EOF

ORPH="$(node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient({datasources:{db:{url:'file:/home/z/my-project/db/custom.db'}}});p.videoRequest.findFirst({where:{prompt:'QA64: orphaned row'}}).then(r=>{console.log(r.id);return p.\$disconnect()})")"
GENU="$(node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient({datasources:{db:{url:'file:/home/z/my-project/db/custom.db'}}});p.videoRequest.findFirst({where:{prompt:'QA64: genuine fail'}}).then(r=>{console.log(r.id);return p.\$disconnect()})")"
echo "[qa] orphaned=$ORPH genuine=$GENU"

H="Authorization: Bearer $TOK"
echo "[qa] T1 list failed (auth)";        R=$(curl -s -o /tmp/r.json -w "%{http_code}" -H "$H" "$BASE/api/worker/jobs?status=failed");     ck "list-failed 200" 200 "$R"; grep -q "orphaned" /tmp/r.json && echo "  -> contains orphaned row" 
echo "[qa] T2 list bad status";           R=$(curl -s -o /dev/null -w "%{http_code}" -H "$H" "$BASE/api/worker/jobs?status=done");        ck "list-bad 400" 400 "$R"
echo "[qa] T3 list wrong token";          R=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer nope-nope-nope-nope" "$BASE/api/worker/jobs?status=failed"); ck "wrong-token 401" 401 "$R"
echo "[qa] T4 requeue orphaned row";      R=$(curl -s -o /tmp/r.json -w "%{http_code}" -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"action":"requeue","agent":"qa-64"}' "$BASE/api/worker/jobs/$ORPH"); ck "requeue-orphaned 200" 200 "$R"; grep -q '"status":"queued"' /tmp/r.json && echo "  -> now queued"
echo "[qa] T5 requeue genuine fail";      R=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"action":"requeue"}' "$BASE/api/worker/jobs/$GENU"); ck "requeue-genuine 409" 409 "$R"
echo "[qa] T6 requeue already queued";    R=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"action":"requeue"}' "$BASE/api/worker/jobs/$ORPH"); ck "requeue-again 409" 409 "$R"
echo "[qa] T7 claim returns requeued row"; curl -s -X POST -H "$H" -H "Content-Type: application/json" -d '{"agent":"qa-64"}' "$BASE/api/worker/claim" > /tmp/r.json; grep -q "QA64: orphaned row" /tmp/r.json && { PASS=$((PASS+1)); echo "PASS: claim got requeued job"; } || { FAIL=$((FAIL+1)); echo "FAIL: claim did not return requeued job"; }

WATCH="$(node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient({datasources:{db:{url:'file:/home/z/my-project/db/custom.db'}}});p.videoRequest.findFirst({where:{prompt:'QA64: watchdog row'}}).then(r=>{console.log(r.id);return p.\$disconnect()})")"
ATT2="$(node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient({datasources:{db:{url:'file:/home/z/my-project/db/custom.db'}}});p.videoRequest.findFirst({where:{prompt:'QA64: attempt2 row'}}).then(r=>{console.log(r.id);return p.\$disconnect()})")"
echo "[qa] T8 requeue watchdog-class row";   R=$(curl -s -o /tmp/r.json -w "%{http_code}" -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"action":"requeue","agent":"qa-64"}' "$BASE/api/worker/jobs/$WATCH"); ck "requeue-watchdog 200" 200 "$R"
echo "[qa] T9 attempt counter increments";   R=$(curl -s -X PATCH -H "$H" -H "Content-Type: application/json" -d '{"action":"requeue","agent":"qa-64"}' "$BASE/api/worker/jobs/$ATT2"); echo "$R" | grep -q '"attempt":2' && { PASS=$((PASS+1)); echo "PASS: attempt=2"; } || { FAIL=$((FAIL+1)); echo "FAIL: attempt counter got: $(cat /tmp/r.json 2>/dev/null | head -c 120)"; }

echo "[qa] cleanup..."
node -e "const {PrismaClient}=require('@prisma/client');const p=new PrismaClient({datasources:{db:{url:'file:/home/z/my-project/db/custom.db'}}});p.videoRequest.deleteMany({where:{prompt:{startsWith:'QA64:'}}}).then(n=>{console.log('deleted',n.count);return p.\$disconnect()})"
kill $DEVPID 2>/dev/null; sleep 1; pkill -f "next dev -p 3111" 2>/dev/null
echo "[qa] RESULT: PASS=$PASS FAIL=$FAIL"
[ "$FAIL" = "0" ]
