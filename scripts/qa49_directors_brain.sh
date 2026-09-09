#!/bin/bash
# Task 49 QA: The Director's Brain must reach EVERY script scene and the enhancer.
# Runs against the dev server exactly as the owner would (panel admin session).
# Never prints passwords.
B=http://localhost:3000
PASS="$(python3 -c "import json;print(json.load(open('workers/secrets/supabase.json'))['admin_bootstrap']['password'])")"
J=/tmp/qa49_admin.txt
FAILS=0
p() { local ok="$1"; local msg="$2"; if [ "$ok" = PASS ]; then echo "PASS: $msg"; else echo "FAIL: $msg"; FAILS=$((FAILS+1)); fi }

rm -f "$J"
node -e "
const {PrismaClient}=require('@prisma/client');
const p=new PrismaClient();
(async()=>{await p.\$queryRawUnsafe(\"DELETE FROM RateLimit WHERE bucket LIKE 'login:%' OR bucket LIKE 'ai:%'\");await p.\$disconnect();})().catch(()=>process.exit(0));
" 2>/dev/null

AL=$(curl -s -c "$J" -X POST $B/api/auth/login -H 'Content-Type: application/json' -d "{\"email\":\"admin@deyoung.site\",\"password\":\"$PASS\"}")
echo "$AL" | grep -q authenticated && p PASS "panel admin login" || p FAIL "panel admin login: $(echo "$AL" | head -c 100)"

# --- script writer: direction + bible on every scene, for several shapes ---
for TOT in 15 30 60 120; do
  SC=$(curl -s -b "$J" -X POST $B/api/studio/script -H 'Content-Type: application/json' \
    -d "{\"brief\":\"a brave tiny robot and a shy firefly light up a sleeping city at night\",\"niche\":\"kids cartoon\",\"seconds\":$TOT}")
  RES=$(echo "$SC" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin); s=d.get('script',{})
    scenes=s.get('scenes',[]); bible=s.get('bible')
    n=len(scenes)
    directed=sum(1 for sc in scenes if sc.get('direction',{}).get('shot') and sc.get('direction',{}).get('note'))
    total=sum(sc.get('seconds',0) for sc in scenes)
    shot_in_visual=sum(1 for sc in scenes if sc.get('direction',{}).get('shot','')[:18].lower() in sc.get('visual','').lower())
    bible_ok = bool(bible and bible.get('bibleLine') and bible.get('styleAnchor') and bible.get('kidPromise'))
    print(f'{n}|{directed}|{total}|$TOT|{shot_in_visual}|{bible_ok}')
except Exception as e:
    print(f'ERR|{e}')
" 2>/dev/null)
  N=$(echo "$RES" | cut -d'|' -f1); DIR=$(echo "$RES" | cut -d'|' -f2); SUM=$(echo "$RES" | cut -d'|' -f3); SHOTV=$(echo "$RES" | cut -d'|' -f5); BOK=$(echo "$RES" | cut -d'|' -f6)
  if [ "$DIR" = "$N" ] && [ "$N" -ge 3 ] 2>/dev/null; then p PASS "script ${TOT}s: $N/$N scenes directed"; else p FAIL "script ${TOT}s direction: $RES"; fi
  if [ "$SUM" = "$TOT" ]; then p PASS "script ${TOT}s: seconds sum === $TOT"; else p FAIL "script ${TOT}s: sum=$SUM want $TOT"; fi
  if [ "$BOK" = "True" ]; then p PASS "script ${TOT}s: visual bible present"; else p FAIL "script ${TOT}s: bible missing ($BOK)"; fi
  if [ "$SHOTV" -ge $((N*2/3)) ] 2>/dev/null; then p PASS "script ${TOT}s: shot language woven into visuals ($SHOTV/$N)"; else p FAIL "script ${TOT}s: shots not woven ($SHOTV/$N) -> $RES"; fi
done

# --- enhancer: craft language present ---
EN=$(curl -s -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' \
  -d '{"prompt":"a boy discovers his drawing pen brings cartoons to life","niche":"kids cartoon"}')
WORDS=$(echo "$EN" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('enhanced','').split()))" 2>/dev/null)
[ -n "$WORDS" ] && [ "$WORDS" -ge 25 ] 2>/dev/null && p PASS "enhancer works ($WORDS words)" || p FAIL "enhancer weak: $WORDS"
CRAFT=$(echo "$EN" | python3 -c "import json,sys;t=json.load(sys.stdin).get('enhanced','').lower();print(sum(k in t for k in ['palette','light','shot','framed','composition','lens']))" 2>/dev/null)
[ "$CRAFT" -ge 2 ] 2>/dev/null && p PASS "enhancer carries craft language ($CRAFT craft terms)" || p FAIL "enhancer craft language ($CRAFT): $(echo "$EN" | head -c 200)"

# --- other niches smoke (director voices for all) ---
for NICHE in "product ad" "music video" "gaming" "custom"; do
  EN2=$(curl -s -b "$J" -X POST $B/api/studio/enhance -H 'Content-Type: application/json' -d "{\"prompt\":\"a champion runner crosses the finish line at dawn\",\"niche\":\"$NICHE\"}")
  W2=$(echo "$EN2" | python3 -c "import json,sys;print(len(json.load(sys.stdin).get('enhanced','').split()))" 2>/dev/null)
  [ -n "$W2" ] && [ "$W2" -ge 25 ] 2>/dev/null && p PASS "enhancer [$NICHE] ($W2 words)" || p FAIL "enhancer [$NICHE] weak: $W2"
done

echo "---"
if [ "$FAILS" = 0 ]; then echo "qa49: ALL PASS"; else echo "qa49: $FAILS FAILURES"; exit 1; fi
