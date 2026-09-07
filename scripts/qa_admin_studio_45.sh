#!/bin/bash
# Task 45 QA: admin-panel session must open the AI Studio fully free.
# Dev sqlite only. Never prints the password.
B=http://localhost:3000
J=/tmp/qa45_cookies.txt
PASS="$ADMIN_BOOTSTRAP_PASSWORD"
[ -z "$PASS" ] && PASS=$(python3 -c "import json;print(json.load(open('workers/secrets/supabase.json'))['admin_bootstrap']['password'])")
p() { echo "[$1] $2"; }

rm -f "$J"
# 1. admin login (panel session)
C=$(curl -s -c "$J" -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}")
p 1 "login: $(echo "$C" | head -c 120)"

# 2. /api/me with admin cookie -> unlimited owner shape
M=$(curl -s -b "$J" $B/api/me)
p 2 "me: $(echo "$M" | python3 -c "import json,sys;d=json.load(sys.stdin);print('email=',d['user']['email'],'role=',d['user']['role'],'unlimited=',d['unlimited'],'plan=',d['plan'])")"

# 3. studio projects list (was 401 before fix)
P=$(curl -s -b "$J" $B/api/studio/projects)
p 3 "projects list: $(echo "$P" | head -c 60)"

# 4. save a project (StudioProject FK via shadow user)
S=$(curl -s -b "$J" -X POST $B/api/studio/projects -H 'Content-Type: application/json' -d '{"title":"QA Admin Studio","niche":"kids cartoon","brief":"A tiny robot learns to paint sunsets for his village.","status":"draft"}')
PID=$(echo "$S" | python3 -c "import json,sys;print(json.load(sys.stdin)['project']['id'])")
p 4 "project saved: $PID"

# 5. enhance (LLM, admin session)
E=$(curl -s -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d '{"prompt":"A tiny robot learns to paint glowing sunsets over his village","niche":"kids cartoon"}')
p 5 "enhance: $(echo "$E" | head -c 100)"

# 6. render submit -> owner tier (priority 100, no watermark, 1080p+audio)
R=$(curl -s -b "$J" -X POST $B/api/studio/render -H 'Content-Type: application/json' -d "{\"prompt\":\"The little robot paints a glowing sunset over the hills\",\"seconds\":5,\"resolution\":\"1080p\",\"withAudio\":true,\"projectId\":\"$PID\",\"sceneId\":\"s01\"}")
RID=$(echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['request']['id'])")
p 6 "render: $(echo "$R" | python3 -c "import json,sys;d=json.load(sys.stdin);r=d['request'];print('status=',r['status'],'prio=',r['queuePriority'],'watermark=',r['watermark'],'res=',r['resolution'],'audio=',r['withAudio'],'qp=',d.get('queuePosition'))")"

# 7. SSE stream with admin cookie (owner-or-admin live console)
T=$(timeout 6 curl -s -N -b "$J" "$B/api/studio/stream?requestId=$RID" 2>/dev/null | head -c 400)
p 7 "stream first bytes: $(echo "$T" | tr '\n' ' ' | head -c 160)"

# 8. anon guards still honest
A1=$(curl -s -o /dev/null -w "%{http_code}" $B/api/me)
A2=$(curl -s -o /dev/null -w "%{http_code}" $B/api/studio/render -X POST)
p 8 "anon /api/me=$A1 (expect 401), anon render=$A2 (expect 401)"

# 9. regular user session unaffected (mint user via signup+login)
QAEMAIL="qa45user-$(date +%s)@example.com"
U=$(curl -s -c /tmp/qa45_user.txt -X POST $B/api/auth/signup -H 'Content-Type: application/json' -d "{\"email\":\"$QAEMAIL\",\"password\":\"Qa45!Passw0rd\",\"name\":\"QA45\"}")
UM=$(curl -s -b /tmp/qa45_user.txt $B/api/me)
p 9 "user me: $(echo "$UM" | python3 -c "import json,sys;d=json.load(sys.stdin);print('email=',d['user']['email'],'role=',d['user']['role'],'unlimited=',d['unlimited'])") 2>/dev/null || echo "$UM" | head -c 80)"
UR=$(curl -s -b /tmp/qa45_user.txt -X POST $B/api/studio/render -H 'Content-Type: application/json' -d '{"prompt":"A cat chases a butterfly through a meadow","seconds":5,"resolution":"720p"}' -o /dev/null -w "%{http_code}")
p 9b "user render without plan -> $UR (expect 403 subscribe-gate intact)"

p DONE "RID=$RID PID=$PID (cleanup next)"
