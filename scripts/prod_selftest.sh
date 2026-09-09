#!/usr/bin/env bash
# Task 47 — reusable production self-test. Run from GitHub Actions (fresh IP)
# or anywhere. Browser-like header fingerprint on EVERY request (Railway hikari
# edge 429s non-browser fingerprints). Env: BASE, ADMIN_PASS.
set -uo pipefail
BASE="${BASE:-https://deyoungltd.site}"
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
FAILS=0
req() { # method path [data] [cookiejar]
  local m="$1" p="$2" d="${3:-}" cj="${4:-}"
  local args=(-A "$UA"
    -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    -H 'Accept-Language: en-US,en;q=0.9'
    -H 'sec-fetch-site: same-origin'
    -H 'sec-fetch-mode: cors'
    -H 'sec-fetch-dest: empty'
    -H 'Connection: keep-alive'
    -H 'Accept-Encoding: gzip, deflate, br'
    --compressed
    -o "/tmp/out_${m}_${p//\//_}.body" -w '%{http_code}' --max-time 25)
  [ -n "$cj" ] && args+=(-b "$cj" -c "$cj")
  if [ "$m" = POST ]; then args+=(-X POST -H 'Content-Type: application/json' -d "$d"); fi
  curl -s "${args[@]}" "$BASE$p"
}
p(){ if [ "$1" = PASS ]; then echo "PASS: $2"; else echo "FAIL: $2"; FAILS=$((FAILS+1)); fi }
body(){ cat "/tmp/out_$1.body" 2>/dev/null; }

echo "== 1. health =="
HC=$(req GET /api/health); HB=$(body GET__api_health)
p $([ "$HC" = 200 ] && echo PASS || echo FAIL) "health 200 (got $HC: $(echo "$HB" | head -c 60))"

echo "== 2. admin login =="
LC=$(req POST /api/auth/login "{\"email\":\"admin@deyoung.site\",\"password\":\"$ADMIN_PASS\"}" /tmp/jar.txt)
p $([ "$LC" = 200 ] && echo PASS || echo FAIL) "panel admin login 200 (got $LC: $(body POST__api_auth_login | head -c 80))"

echo "== 3. /api/me =="
MC=$(req GET /api/me "" /tmp/jar.txt)
MR=$(body GET__api_me | python3 -c "import json,sys;d=json.load(sys.stdin);print(d.get('user',{}).get('role'), d.get('unlimited'))" 2>/dev/null || echo "?")
p $([ "$MC" = 200 ] && [ "$MR" = "admin True" ] && echo PASS || echo FAIL) "/api/me admin unlimited (code $MC: $MR)"

echo "== 4. PROMPT ENHANCER =="
EC=$(req POST /api/studio/enhance '{"prompt":"a boy discovers his drawing pen brings cartoons to life","niche":"kids cartoon"}' /tmp/jar.txt)
EW=$(body POST__api_studio_enhance | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d.get('enhanced','').split()))" 2>/dev/null || echo 0)
p $([ "$EC" = 200 ] && [ "${EW:-0}" -ge 25 ] 2>/dev/null && echo PASS || echo FAIL) "enhancer 200 + $EW words (code $EC)"
echo "  ENHANCED: $(body POST__api_studio_enhance | python3 -c "import json,sys;print(json.load(sys.stdin).get('enhanced','')[:180])" 2>/dev/null)"

echo "== 5. SCRIPT WRITER =="
SC=$(req POST /api/studio/script '{"brief":"a boy discovers his drawing pen brings cartoons to life and his doodles race across the page","niche":"kids cartoon","seconds":30}' /tmp/jar.txt)
SOK=$(body POST__api_studio_script | python3 -c "
import json
s=json.load(sys.stdin).get('script',{})
secs=sum(x.get('seconds',0) for x in s.get('scenes',[]))
print('OK' if s.get('title') and 3<=len(s.get('scenes',[]))<=6 and secs<=40 and 1<=len(s.get('characters',[]))<=3 else 'BAD')
" 2>/dev/null || echo BAD)
p $([ "$SC" = 200 ] && [ "$SOK" = OK ] && echo PASS || echo FAIL) "script writer 200 + valid shape (code $SC)"
body POST__api_studio_script | python3 -c "
import json
s=json.load(sys.stdin)['script']
print('  TITLE:', s['title'])
print('  CAST:', [c['name'] for c in s['characters']])
print('  S1:', s['scenes'][0]['visual'][:160])
" 2>/dev/null

echo "== 6. owner-tier render =="
RC=$(req POST /api/studio/render '{"prompt":"prod selftest task47 - boy discovers his drawing pen brings cartoons to life","seconds":5,"resolution":"1080p","withAudio":true}' /tmp/jar.txt)
RT=$(body POST__api_studio_render | python3 -c "import json;r=json.load(sys.stdin)['request'];print(r['queuePriority'], r['watermark'], r['resolution'], r['withAudio'])" 2>/dev/null || echo "?")
p $([ "$RC" = 201 ] && [ "$RT" = "100 False 1080p True" ] && echo PASS || echo FAIL) "render 201 owner tier (code $RC: $RT)"

echo "==============================="
if [ $FAILS -eq 0 ]; then echo "PROD SELFTEST: ALL PASS"; else echo "PROD SELFTEST: $FAILS FAILURES"; fi
exit $FAILS
