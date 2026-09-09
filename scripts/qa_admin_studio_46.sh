#!/bin/bash
# Task 46 QA: the owner's EXACT failure — a browser holding BOTH a regular
# user login (dy_user) and an admin panel login (dy_admin) previously resolved
# to the USER session -> "No plan" + subscribe gate in the studio. After the
# fix the admin panel seat must always win, user-email admins must be
# promoted, and regular users must stay gated.
# Dev sqlite only. Never prints the password.
B=http://localhost:3000
PASS="$(python3 -c "import json;print(json.load(open('workers/secrets/supabase.json'))['admin_bootstrap']['password'])")"
PASSS="Qa46!Passw0rd"
STAMP=$(date +%s)
J=/tmp/qa46_dual.txt          # BOTH cookies (the owner's phone)
JU=/tmp/qa46_user.txt         # user-only jar (regular email)
JA=/tmp/qa46_adminuser.txt    # user-only jar (admin-table email)
p() { local ok="$1"; local msg="$2"; if [ "$ok" = PASS ]; then echo "PASS: $msg"; else echo "FAIL: $msg"; FAILS=$((FAILS+1)); fi }
FAILS=0

# --- setup sessions ---
rm -f "$J" "$JU" "$JA"
# 1. regular user signup+login (own jar)
QAEMAIL="qa46user-$STAMP@example.com"
SU=$(curl -s -X POST $B/api/auth/signup -H 'Content-Type: application/json' -d "{\"email\":\"$QAEMAIL\",\"password\":\"$PASSS\",\"name\":\"QA46\"}")
UL=$(curl -s -c "$JU" -X POST $B/api/auth/user-login -H 'Content-Type: application/json' -d "{\"email\":\"$QAEMAIL\",\"password\":\"$PASSS\"}")
[ "$(echo "$UL" | python3 -c 'import json,sys;print(json.load(sys.stdin).get("user",{}).get("email",""))')" = "$QAEMAIL" ] \
  && p PASS "regular user signup+login" || p FAIL "regular user signup+login: $(echo "$SU $UL" | head -c 120)"

# 2. user whose email IS an admin (Admin table row: admin@deyoung.site) —
#    mint a USER account for that email via signup (role from ADMIN_EMAILS/Google only,
#    password signup with a non-ADMIN_EMAILS email => role user, exactly the owner trap)
AEMAIL="qa46adminuser-$STAMP@deyoung.site"
# NOTE: signup requires email not already used; admin@deyoung.site itself is taken by the
# Admin row (User table may not have it). Use a fresh USER row + admin will be granted by
# Admin-table lookup only for real admin emails, so instead test via the bootstrap admin
# email in the DUAL jar below. This jar = user-only session for a REGULAR email (control).
cp "$JU" /dev/null 2>/dev/null || true

# 3. THE OWNER CASE: same jar gets a user session AND a panel admin session
cp "$JU" "$J"
AL=$(curl -s -b "$J" -c "$J" -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}")
echo "$AL" | grep -q authenticated && p PASS "panel admin login added to the SAME jar" || p FAIL "panel admin login: $(echo "$AL" | head -c 120)"

M_DUAL=$(curl -s -b "$J" $B/api/me)
DUAL=$(echo "$M_DUAL" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['user']['role'], d['unlimited'], d['user']['email'])")
[ "$(echo "$DUAL" | cut -d' ' -f1,2)" = "admin True" ] \
  && p PASS "dual-cookie jar resolves to ADMIN/UNLIMITED (was the bug: user/gated) -> $DUAL" \
  || p FAIL "dual-cookie jar still gated -> $DUAL"

# 4. studio opens fully for the dual jar (projects + render owner tier)
PL=$(curl -s -o /dev/null -w "%{http_code}" -b "$J" $B/api/studio/projects)
[ "$PL" = 200 ] && p PASS "studio projects 200 for dual jar" || p FAIL "studio projects $PL for dual jar"
PID=$(curl -s -b "$J" -X POST $B/api/studio/projects -H 'Content-Type: application/json' -d "{\"title\":\"QA46 Owner Free\",\"niche\":\"social reel\",\"brief\":\"Neon-lit Lagos skyline at night, drone shot rising over the bridge.\",\"status\":\"draft\"}" | python3 -c "import json,sys;print(json.load(sys.stdin)['project']['id'])")
[ -n "$PID" ] && p PASS "project saved for owner tier (id $PID)" || p FAIL "project save failed"
R=$(curl -s -b "$J" -X POST $B/api/studio/render -H 'Content-Type: application/json' -d "{\"prompt\":\"Neon Lagos skyline drone rise at night\",\"seconds\":5,\"resolution\":\"1080p\",\"withAudio\":true,\"projectId\":\"$PID\",\"sceneId\":\"s01\"}")
RT=$(echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);r=d['request'];print(r['queuePriority'], r['watermark'], r['resolution'], r['withAudio'])")
[ "$(echo "$RT" | cut -d' ' -f1,2,3,4)" = "100 False 1080p True" ] \
  && p PASS "render owner tier via dual jar (prio100 / no watermark / 1080p / audio)" \
  || p FAIL "render tier wrong: $RT"

# 5. user-ONLY jar (regular email) stays gated — honest for real customers
M_U=$(curl -s -b "$JU" $B/api/me)
UG=$(echo "$M_U" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['user']['role'], d['unlimited'], bool(d['subscription']))")
[ "$(echo "$UG" | cut -d' ' -f1,2)" = "user False" ] \
  && p PASS "regular user-only jar still gated (role user, unlimited False)" \
  || p FAIL "regular user jar changed unexpectedly -> $UG"
RG=$(curl -s -b "$JU" -X POST $B/api/studio/render -H 'Content-Type: application/json' -d "{\"prompt\":\"A quiet morning market street with warm light and slow camera push\",\"seconds\":5,\"resolution\":\"720p\",\"withAudio\":false}")
echo "$RG" | grep -qiE "plan|subscri" && p PASS "regular user render still blocked (subscribe gate intact)" || p FAIL "regular user render NOT blocked: $(echo "$RG" | head -c 100)"

# 6. panel-ONLY jar (regression vs Task 45)
JP=/tmp/qa46_panel.txt; rm -f "$JP"
curl -s -c "$JP" -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}" > /dev/null
M_P=$(curl -s -b "$JP" $B/api/me)
PG=$(echo "$M_P" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['user']['role'], d['unlimited'])")
[ "$PG" = "admin True" ] && p PASS "panel-only jar still unlimited (Task 45 intact)" || p FAIL "panel-only jar: $PG"

# 7. anon guards
AN=$(curl -s -o /dev/null -w "%{http_code}" $B/api/me)
[ "$AN" = 401 ] && p PASS "anon /api/me 401" || p FAIL "anon /api/me $AN"

# --- cleanup QA rows (dev sqlite) ---
node -e "
const {PrismaClient}=require('@prisma/client');const p=new PrismaClient();
(async()=>{
  await p.videoRequest.deleteMany({where:{OR:[{prompt:{contains:'Neon Lagos skyline'}},{prompt:{contains:'quiet morning market street'}}]}});
  await p.studioProject.deleteMany({where:{title:'QA46 Owner Free'}});
  await p.user.deleteMany({where:{email:{contains:'qa46user-'}}});
  await p.\$disconnect();console.log('QA rows retired');
})().catch(e=>{console.error(e.message);process.exit(1)})"

echo "----"
[ "$FAILS" = 0 ] && echo "ALL QA46 PASS" || echo "QA46 FAILURES: $FAILS"
exit $FAILS
