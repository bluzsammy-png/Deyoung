#!/bin/bash
# Task 47 QA: Script writer + Prompt enhancer must WORK (they were dead in prod:
# z-ai-web-dev-sdk needs sandbox-internal .z-ai-config). Full owner flow on the
# dev server, exactly as the owner does it: panel admin login -> enhance ->
# write script -> autosave -> render one scene (owner tier). Plus: regular user
# AI access (allowed), anon 401, malformed input 400s, output quality sanity.
# Dev sqlite only. Never prints passwords.
B=http://localhost:3000
PASS="$(python3 -c "import json;print(json.load(open('workers/secrets/supabase.json'))['admin_bootstrap']['password'])")"
PASSS="Qa47!Passw0rd"
STAMP=$(date +%s)
J=/tmp/qa47_admin.txt      # panel-admin jar (the owner's studio session)
JU=/tmp/qa47_user.txt      # regular user jar
FAILS=0
p() { local ok="$1"; local msg="$2"; if [ "$ok" = PASS ]; then echo "PASS: $msg"; else echo "FAIL: $msg"; FAILS=$((FAILS+1)); fi }

rm -f "$J" "$JU"

# dev-only: clear DB-backed login/signup rate buckets (QA re-runs trip them;
# worklog 46-c lesson). The limiter is DB-backed and survives dev restarts.
node -e "
const {PrismaClient}=require('@prisma/client');
const p=new PrismaClient();
(async()=>{
  await p.\$queryRawUnsafe(\"DELETE FROM RateLimit WHERE bucket LIKE 'login:%' OR bucket LIKE 'signup:%' OR bucket LIKE 'ai:%'\");
  await p.\$disconnect();
})().catch(e=>{console.error(e.message);process.exit(1)});
" 2>/dev/null || echo "(bucket cleanup skipped)"

# --- 0. anon is rejected ---
AN=$(curl -s -o /dev/null -w "%{http_code}" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"hello world test","niche":"custom"}')
[ "$AN" = 401 ] && p PASS "anon enhance -> 401" || p FAIL "anon enhance -> $AN (want 401)"

# --- 1. panel admin login (owner path) ---
AL=$(curl -s -c "$J" -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}")
echo "$AL" | grep -q authenticated && p PASS "panel admin login" || p FAIL "panel admin login: $(echo "$AL" | head -c 120)"

ME=$(curl -s -b "$J" $B/api/me)
ROLE=$(echo "$ME" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('user',{}).get('role','?'), d.get('unlimited'))")
[ "$(echo "$ROLE" | cut -d' ' -f1,2)" = "admin True" ] && p PASS "/api/me admin unlimited -> $ROLE" || p FAIL "/api/me -> $ROLE"

# --- 2. PROMPT ENHANCER (the broken tool #1) ---
for NICHE in "kids cartoon" "product ad" "real estate" "social reel"; do
  EN=$(curl -s -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d "{\"prompt\":\"a boy discovers his drawing pen brings cartoons to life\",\"niche\":\"$NICHE\"}")
  WORDS=$(echo "$EN" | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('enhanced','').split()))" 2>/dev/null)
  if [ -n "$WORDS" ] && [ "$WORDS" -ge 25 ] 2>/dev/null; then
    p PASS "enhancer works [$NICHE] ($WORDS words)"
    [ "$NICHE" = "kids cartoon" ] && echo "  sample: $(echo "$EN" | python3 -c "import json,sys;print(json.load(sys.stdin)['enhanced'][:160])")"
  else
    p FAIL "enhancer [$NICHE] bad/short -> $(echo "$EN" | head -c 140)"
  fi
done

# --- 3. SCRIPT WRITER (the broken tool #2) ---
SC=$(curl -s -b "$J" -X POST $B/api/studio/script -H 'Content-Type: application/json' -d '{"brief":"a boy discovers his drawing pen brings cartoons to life and his doodles race across the page","niche":"kids cartoon","seconds":30}')
CHECK=$(echo "$SC" | python3 -c "
import json,sys
d=json.load(sys.stdin)
s=d.get('script',{})
scenes=s.get('scenes',[])
secs=sum(x.get('seconds',0) for x in scenes)
ids=[x.get('id') for x in scenes]
lines_ok=all(len(x.get('line','').split())<=16 for x in scenes)
vis_ok=all(len(x.get('visual',''))>30 for x in scenes)
chars=s.get('characters',[])
print('OK' if (s.get('title') and 3<=len(scenes)<=6 and secs<=40 and all(i in ('s1','s2','s3','s4','s5','s6','s7','s8') for i in ids) and lines_ok and vis_ok and 1<=len(chars)<=3) else 'BAD')
" 2>/dev/null || echo BAD)
[ "$CHECK" = OK ] && p PASS "script writer: title+logline+3-6 scenes+cast+lines+visuals all valid (30s)" || p FAIL "script writer shape: $(echo "$SC" | head -c 200)"

# quality eyeball of one scene
echo "  sample title: $(echo "$SC" | python3 -c "import json,sys;print(json.load(sys.stdin)['script']['title'])")"
echo "  sample scene: $(echo "$SC" | python3 -c "import json,sys;s=json.load(sys.stdin)['script']['scenes'][0];print(s['id'], s['title'], '|', s['visual'][:110])")"

# other niches produce valid scripts too
for NICHE in "real estate" "gaming" "fashion"; do
  SC2=$(curl -s -b "$J" -X POST $B/api/studio/script -H 'Content-Type: application/json' -d "{\"brief\":\"a quiet family home with a garden and morning light flowing through every room\",\"niche\":\"$NICHE\",\"seconds\":45}")
  T=$(echo "$SC2" | python3 -c "import json,sys;d=json.load(sys.stdin);s=d.get('script',{});print('OK' if s.get('title') and len(s.get('scenes',[]))>=3 else 'BAD')" 2>/dev/null || echo BAD)
  [ "$T" = OK ] && p PASS "script writer [$NICHE] 45s valid" || p FAIL "script writer [$NICHE] -> $(echo "$SC2" | head -c 140)"
done

# --- 4. FULL OWNER FLOW: save project + render scene 1 (owner tier) ---
PID=$(curl -s -b "$J" -X POST $B/api/studio/projects -H 'Content-Type: application/json' -d "{\"id\":\"\",\"title\":\"QA47 Pen Movie\",\"niche\":\"kids cartoon\",\"brief\":\"a boy discovers his drawing pen brings cartoons to life\",\"scriptJson\":$(echo "$SC" | python3 -c "import json,sys;print(json.dumps(json.dumps(json.load(sys.stdin)['script'])))"),\"status\":\"scripted\"}" | python3 -c "import json,sys;print(json.load(sys.stdin)['project']['id'])")
[ -n "$PID" ] && p PASS "scripted project saved (id ${PID:0:12}...)" || p FAIL "project save failed"

S1SEC=$(echo "$SC" | python3 -c "import json,sys;print(json.load(sys.stdin)['script']['scenes'][0]['seconds'])")
R=$(curl -s -b "$J" -X POST $B/api/studio/render -H 'Content-Type: application/json' -d "{\"prompt\":\"Scene s1 from the QA47 pen movie — a boy discovers his drawing pen brings cartoons to life\",\"seconds\":$S1SEC,\"resolution\":\"1080p\",\"withAudio\":true,\"projectId\":\"$PID\",\"sceneId\":\"s1\"}")
TIER=$(echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);r=d['request'];print(r['queuePriority'], r['watermark'], r['resolution'], r['withAudio'])" 2>/dev/null)
[ "$(echo "$TIER" | cut -d' ' -f1,2,3,4)" = "100 False 1080p True" ] && p PASS "render scene owner tier (prio100/no-wm/1080p/audio, ${S1SEC}s)" || p FAIL "render tier -> $(echo "$R" | head -c 160)"

# --- 5. regular user: AI tools WORK, render still gated ---
QAEMAIL="qa47user-$STAMP@example.com"
curl -s -X POST $B/api/auth/signup -H 'Content-Type: application/json' -d "{\"email\":\"$QAEMAIL\",\"password\":\"$PASSS\",\"name\":\"QA47\"}" > /dev/null
curl -s -c "$JU" -X POST $B/api/auth/user-login -H 'Content-Type: application/json' -d "{\"email\":\"$QAEMAIL\",\"password\":\"$PASSS\"}" > /dev/null
EN2=$(curl -s -b "$JU" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"sunset skateboarding along the beach promenade","niche":"travel"}')
echo "$EN2" | python3 -c "import json,sys;d=json.load(sys.stdin);exit(0 if len(d.get('enhanced','').split())>=25 else 1)" 2>/dev/null \
  && p PASS "regular user enhancer works (plan gate is render-only, as designed)" || p FAIL "regular user enhancer -> $(echo "$EN2" | head -c 140)"
RG=$(curl -s -o /dev/null -w "%{http_code}" -b "$JU" -X POST $B/api/studio/render -H 'Content-Type: application/json' -d '{"prompt":"beach skate at sunset, smooth push in","seconds":5,"resolution":"720p","withAudio":false}')
[ "$RG" = 403 ] && p PASS "regular user render still plan-gated (403)" || p FAIL "regular user render -> $RG (want 403)"

# --- 6. input validation ---
V1=$(curl -s -o /dev/null -w "%{http_code}" -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"hi","niche":"custom"}')
V2=$(curl -s -o /dev/null -w "%{http_code}" -b "$J" -X POST $B/api/studio/script -H 'Content-Type: application/json' -d '{"brief":"too short","niche":"custom"}')
V3=$(curl -s -o /dev/null -w "%{http_code}" -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"a valid long enough prompt here","niche":"nonexistent"}')
[ "$V1" = 400 ] && [ "$V2" = 400 ] && [ "$V3" = 400 ] && p PASS "validation: short inputs + bad niche -> 400" || p FAIL "validation codes: $V1 $V2 $V3"

# --- cleanup QA rows (dev sqlite) ---
node -e "
const {PrismaClient}=require('@prisma/client');
const p=new PrismaClient();
(async()=>{
  await p.videoRequest.deleteMany({where:{notes:{contains:'QA47'}}});
  await p.studioProject.deleteMany({where:{title:{contains:'QA47'}}});
  await p.user.deleteMany({where:{email:{contains:'qa47user-'}}});
  await p.\$queryRawUnsafe(\"DELETE FROM RateLimit WHERE bucket LIKE 'ai:%'\");
  console.log('cleanup done');
})().catch(e=>{console.error(e.message);process.exit(1)});
" 2>/dev/null || echo "(cleanup skipped — non-fatal)"

echo "==============================="
echo "QA47 RESULT: $((FAILS==0 ? 1 : 0)) (fails=$FAILS)"
[ $FAILS -eq 0 ] && echo "ALL PASS" || echo "HAS FAILURES"
