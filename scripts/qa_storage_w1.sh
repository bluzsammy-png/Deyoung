#!/bin/bash
# W1 storage_v2 QA (spec §D.1/§E.6) — runs against the LIVE :3000 dev server.
# Creates a scoped QA admin row in the sandbox dev DB, then removes everything.
# (Isolated-server QA proved impossible here: next dev ignores env swaps and the
#  shared .next cache corrupts under parallel boots — documented in worklog.)
set -u
cd /home/z/my-project
[ -f .env ] && set -a && . ./.env && set +a
PASS=0; FAIL=0
check() {
  if [ "$2" = "$3" ]; then echo "    PASS $1 ($3)"; PASS=$((PASS+1)); else echo "    FAIL $1 (expected $2, got $3)"; FAIL=$((FAIL+1)); fi
}
BASE=http://localhost:3000
JAR=/tmp/w1-qa-cookies.txt
QA_ADMIN="qa-storage-admin@test.deyoung"
QA_PW="w1-qa-passphrase-0123456789"
EMAIL="storage-qa-$(date +%s)@test.deyoung"

echo "[0] create scoped QA admin row (removed in cleanup)…"
node -e "
const { PrismaClient } = require('@prisma/client');
const crypto = require('crypto');
const db = new PrismaClient();
const salt = crypto.randomBytes(16).toString('hex');
const hash = crypto.scryptSync('$QA_PW', salt, 64).toString('hex');
db.admin.upsert({
  where: { email: '$QA_ADMIN' },
  update: { passwordHash: 'scrypt\$' + salt + '\$' + hash },
  create: { email: '$QA_ADMIN', passwordHash: 'scrypt\$' + salt + '\$' + hash },
}).then(() => { console.log('qa admin ready'); return db.\$disconnect(); });
" 2>&1 | grep -v prisma:query

echo "[1] admin login…"
CODE=$(curl -s --max-time 15 -o /tmp/w1-login.json -w "%{http_code}" -c $JAR -X POST $BASE/api/auth/login \
  -H 'content-type: application/json' -d "{\"email\":\"$QA_ADMIN\",\"password\":\"$QA_PW\"}")
check "qa admin login" 200 "$CODE"

PNG_B64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
echo "$PNG_B64" | base64 -d > /tmp/w1-test.png

echo "[2] POST /api/upload (PNG sent with a lying content-type: image/jpeg)…"
UP=$(curl -s --max-time 30 -b $JAR -X POST $BASE/api/upload -F "file=@/tmp/w1-test.png;type=image/jpeg" -o /tmp/w1-up.json -w "%{http_code}")
check "upload status" 200 "$UP"
ASSET=$(python3 -c "import json;print(json.load(open('/tmp/w1-up.json')).get('assetId',''))" 2>/dev/null)
URL=$(python3 -c "import json;print(json.load(open('/tmp/w1-up.json')).get('url',''))" 2>/dev/null)
echo "    assetId=$ASSET url=$URL"

echo "[3] delivery + magic-byte sniffing…"
check "public asset GET" 200 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' $BASE$URL)"
check "served as image/png (sniffed, not the lie)" "image/png" "$(curl -s --max-time 15 -o /dev/null -w '%{content_type}' $BASE$URL)"
check "HEAD probe" 200 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -I $BASE$URL)"
MIME_DB=$(node scripts/qa_worker_data.mjs asset "$ASSET" 2>/dev/null)
check "db row mime|kind|driver" "image/png|image|local" "$MIME_DB"

echo "[4] upload abuse control…"
echo "this is definitely not an image" > /tmp/w1-bad.txt
check "text file rejected (magic bytes)" 400 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -b $JAR -X POST $BASE/api/upload -F 'file=@/tmp/w1-bad.txt')"
NOSESSION=$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -X POST $BASE/api/upload -F 'file=@/tmp/w1-test.png')
if [ "$NOSESSION" = "401" ] || [ "$NOSESSION" = "403" ]; then PASS=$((PASS+1)); echo "    PASS unauthenticated blocked ($NOSESSION)"; else FAIL=$((FAIL+1)); echo "    FAIL unauthenticated upload returned $NOSESSION"; fi

echo "[5] worker deliver → object storage → private authz…"
SEED=$(node scripts/qa_worker_data.mjs seed "$EMAIL")
JOB1=$(echo "$SEED" | python3 -c "import json,sys; print(json.load(sys.stdin)['jobIds'][0])")
python3 -c "
data = b'\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2avc1' + b'\x00' * 4096
open('/tmp/w1-fake.mp4','wb').write(data)"
DELIVER=$(curl -s --max-time 30 -X PATCH "$BASE/api/worker/jobs/$JOB1" -H "authorization: Bearer $WORKER_TOKEN" \
  -F "action=deliver" -F "file=@/tmp/w1-fake.mp4;type=video/mp4" -F "gpuMinutes=1.5" -F "renderer=qa-w1")
echo "    deliver: $(echo $DELIVER | head -c 170)"
RURL=$(node scripts/qa_worker_data.mjs resulturl "$EMAIL" "$JOB1")
STATUS=$(node scripts/qa_worker_data.mjs verify "$EMAIL" "$JOB1" | python3 -c "import json,sys; print(json.load(sys.stdin)['status'])")
check "job status done" "done" "$STATUS"
check "resultUrl is /api/files" "yes" "$(echo "$RURL" | grep -q '^/api/files/' && echo yes || echo no)"
ASSET2=$(echo "$RURL" | sed -E 's#^/api/files/([^?]+).*#\1#')
check "private asset without params → 404" 404 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' $BASE/api/files/$ASSET2)"
check "customer with id+email → 200" 200 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' "$BASE$RURL")"
check "served as video/mp4" "video/mp4" "$(curl -s --max-time 15 -o /dev/null -w '%{content_type}' "$BASE$RURL")"
check "range request → 206" 206 "$(curl -s --max-time 15 -o /dev/null -w '%{http_code}' -H 'Range: bytes=0-1023' "$BASE$RURL")"
check "admin session also allowed" 200 "$(curl -s --max-time 15 -b $JAR -o /dev/null -w '%{http_code}' $BASE/api/files/$ASSET2)"

echo "[6] cleanup (QA admin, request rows, assets, media)…"
node scripts/qa_worker_data.mjs cleanup "$EMAIL" "$JOB1" >/dev/null && echo "    request rows + media removed"
node -e "
const { PrismaClient } = require('@prisma/client');
const db = new PrismaClient();
db.admin.delete({ where: { email: '$QA_ADMIN' } })
  .then(() => { console.log('qa admin removed'); return db.\$disconnect(); })
  .catch(() => { console.log('qa admin already gone'); return db.\$disconnect(); });
" 2>&1 | grep -v prisma:query
rm -f $JAR /tmp/w1-test.png /tmp/w1-fake.mp4 /tmp/w1-bad.txt /tmp/w1-login.json /tmp/w1-up.json

echo ""
echo "RESULT: $PASS passed, $FAIL failed"
[ $FAIL -eq 0 ]
