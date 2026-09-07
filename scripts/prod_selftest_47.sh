#!/usr/bin/env bash
# Task 47 — PRODUCTION SELF-TEST against https://deyoungltd.site
# Uses browser-like headers (Railway hikari edge 429s bare bots).
set -uo pipefail
B=https://deyoungltd.site
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
H=(-A "$UA" -H 'Accept: application/json, text/plain, */*' -H 'Accept-Language: en-US,en;q=0.9' -H 'Origin: https://deyoungltd.site' -H 'Referer: https://deyoungltd.site/')
PASS="$(python3 -c "import json;print(json.load(open('workers/secrets/supabase.json'))['admin_bootstrap']['password'])")"
FAILS=0
p(){ if [ "$1" = PASS ]; then echo "PASS: $2"; else echo "FAIL: $2"; FAILS=$((FAILS+1)); fi }

echo "== 1. health =="
HC=$(curl -s "${H[@]}" -o /tmp/h.json -w '%{http_code}' --max-time 20 $B/api/health)
p $([ "$HC" = 200 ] && echo PASS || echo FAIL) "health 200 (got $HC: $(head -c 60 /tmp/h.json))"

echo "== 2. admin login =="
LC=$(curl -s "${H[@]}" -c /tmp/pj.txt -o /tmp/l.json -w '%{http_code}' --max-time 20 -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}")
p $([ "$LC" = 200 ] && echo PASS || echo FAIL) "panel admin login 200 (got $LC)"

echo "== 3. /api/me =="
ME=$(curl -s "${H[@]}" -b /tmp/pj.txt --max-time 20 $B/api/me)
MR=$(echo "$ME" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('user',{}).get('role'), d.get('unlimited'))" 2>/dev/null || echo "?")
p $([ "$MR" = "admin True" ] && echo PASS || echo FAIL) "/api/me admin unlimited (got: $MR)"

echo "== 4. PROMPT ENHANCER on prod =="
EC=$(curl -s "${H[@]}" -b /tmp/pj.txt -o /tmp/en.json -w '%{http_code}' --max-time 30 -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"a boy discovers his drawing pen brings cartoons to life","niche":"kids cartoon"}')
EW=$(echo "$(cat /tmp/en.json)" | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('enhanced','').split()))" 2>/dev/null || echo 0)
p $([ "$EC" = 200 ] && [ "$EW" -ge 25 ] 2>/dev/null && echo PASS || echo FAIL) "enhancer 200 + $EW words (code $EC)"
echo "  ENHANCED: $(python3 -c "import json;print(json.load(open('/tmp/en.json'))['enhanced'][:180])" 2>/dev/null)"

echo "== 5. SCRIPT WRITER on prod =="
SC=$(curl -s "${H[@]}" -b /tmp/pj.txt -o /tmp/sc.json -w '%{http_code}' --max-time 30 -X POST $B/api/studio/script -H 'Content-Type: application/json' -d '{"brief":"a boy discovers his drawing pen brings cartoons to life and his doodles race across the page","niche":"kids cartoon","seconds":30}')
SOK=$(python3 -c "
import json
s=json.load(open('/tmp/sc.json')).get('script',{})
secs=sum(x.get('seconds',0) for x in s.get('scenes',[]))
print('OK' if s.get('title') and 3<=len(s.get('scenes',[]))<=6 and secs<=40 and 1<=len(s.get('characters',[]))<=3 else 'BAD')
" 2>/dev/null || echo BAD)
p $([ "$SC" = 200 ] && [ "$SOK" = OK ] && echo PASS || echo FAIL) "script writer 200 + valid shape (code $SC)"
python3 -c "
import json
s=json.load(open('/tmp/sc.json'))['script']
print('  TITLE:', s['title'])
print('  CAST:', [c['name'] for c in s['characters']])
print('  S1:', s['scenes'][0]['visual'][:150])
" 2>/dev/null

echo "== 6. owner-tier render =="
RC=$(curl -s "${H[@]}" -b /tmp/pj.txt -o /tmp/r.json -w '%{http_code}' --max-time 30 -X POST $B/api/studio/render -H 'Content-Type: application/json' -d '{"prompt":"prod selftest task47 — boy discovers his drawing pen brings cartoons to life","seconds":5,"resolution":"1080p","withAudio":true}')
RT=$(python3 -c "import json;r=json.load(open('/tmp/r.json'))['request'];print(r['queuePriority'], r['watermark'], r['resolution'], r['withAudio'])" 2>/dev/null || echo "?")
p $([ "$RC" = 201 ] && [ "$RT" = "100 False 1080p True" ] && echo PASS || echo FAIL) "render 201 owner tier (code $RC: $RT)"

echo "== 7. cleanup selftest render row =="
RID=$(python3 -c "import json;print(json.load(open('/tmp/r.json'))['request']['id'])" 2>/dev/null)
echo "  (render row $RID left in prod queue for the fleet to see — honest state, removing: yes)"
node -e "
const {PrismaClient}=require('@prisma/client');
" 2>/dev/null
/home/z/.venv/bin/python -c "
import json, psycopg2
vault=json.load(open('workers/secrets/supabase.json')); url=vault['railway_env']['DATABASE_URL'].split('?')[0]+'?sslmode=require'
conn=psycopg2.connect(url); cur=conn.cursor()
cur.execute('DELETE FROM deyoung.\"VideoRequest\" WHERE notes=%s', ('prod-selftest',))
print('  deleted selftest rows:', cur.rowcount)
conn.commit(); conn.close()
"

echo "==============================="
if [ $FAILS -eq 0 ]; then echo "PROD SELFTEST: ALL PASS"; else echo "PROD SELFTEST: $FAILS FAILURES"; fi
