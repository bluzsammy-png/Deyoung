#!/usr/bin/env python3
"""Task 67c — ModelScope chat/completions 401 body capture + model from live list."""
import json
import urllib.request
import urllib.error

with open("/home/z/my-project/workers/secrets/modelscope_tokens.json") as f:
    tok = json.load(f)["tokens"][0]["token"]
BASE = "https://api-inference.modelscope.cn/v1"


def post(url, payload, timeout=60):
    r = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    r.add_header("Authorization", f"Bearer {tok}")
    r.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:
        return None, f"{type(e).__name__}: {str(e)[:120]}"


# 1. pull a live model id from the public list
r = urllib.request.Request(BASE + "/models")
with urllib.request.urlopen(r, timeout=30) as resp:
    ids = [m["id"] for m in json.loads(resp.read().decode()).get("data", [])]
print(f"[models] {len(ids)} available; first 5: {ids[:5]}")

# prefer a small qwen if present, else first id
pref = [i for i in ids if "Qwen2.5-1.5B" in i] or [i for i in ids if "Qwen" in i and "1.5B" in i] or ids[:1]
for mid in pref[:2]:
    st, body = post(BASE + "/chat/completions", {
        "model": mid,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 16,
    })
    ok = st == 200
    preview = ""
    if ok:
        ch = (body.get("choices") or [{}])[0]
        preview = ((ch.get("message") or {}).get("content") or "")[:60]
    print(f"[chat] model={mid} -> HTTP {st} {'PASS' if ok else 'FAIL'} body={preview or str(body)[:200]}")
    if ok:
        break
