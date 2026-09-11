#!/usr/bin/env python3
"""Task 65 — HF plane hygiene: delete the leftover deyoung-probe model repos
that Task 53's probe created and failed to clean up (cleanup returned 400).
Also serves as the live per-account verification evidence."""
import json
import urllib.error
import urllib.request

toks = [(t["id"], t["token"]) for t in json.load(open("workers/secrets/hf_tokens.json"))["tokens"]]


def req(method, url, tok):
    r = urllib.request.Request(url, method=method, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


for tid, tok in toks:
    st, body = req("GET", "https://huggingface.co/api/whoami-v2", tok)
    if st != 200:
        print(f"{tid}: whoami HTTP {st} — token invalid?")
        continue
    user = json.loads(body).get("name")
    st2, body2 = req("DELETE", f"https://huggingface.co/api/models/{user}/deyoung-probe", tok)
    print(f"{tid} ({user}): delete deyoung-probe -> HTTP {st2} {body2[:100]}")
