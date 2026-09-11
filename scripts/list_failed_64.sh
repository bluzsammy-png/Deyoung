#!/usr/bin/env bash
# Task 64 prod ops — list reaper-orphaned failed rows, requeue the OWNER's
# video (identified interactively by createdAt/prompt), verify claim pickup.
# Token stays in env; never printed.
set -u
cd /home/z/my-project
TOK="$(python3 -c "import json;print(json.load(open('workers/secrets/worker_token.json'))['token'])")"
H="Authorization: Bearer $TOK"
BASE="https://deyoungltd.site"

echo "=== failed rows (latest first) ==="
curl -s -H "$H" "$BASE/api/worker/jobs?status=failed" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for j in d.get('jobs', []):
    print(f\"{j['id']} | created {j['createdAt'][:16]} | {j['seconds']}s {j['resolution']} | notes: {j['notes'][:80]}\")
    print(f\"   prompt: {j['prompt'][:110]}\")
print('count:', d.get('count'))"
