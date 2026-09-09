#!/usr/bin/env python3
"""HF token capability probe v2 — hard timeouts, raw HTTP (no hanging SDK calls).

For each of the 4 owner tokens:
  1. model-repo write probe  (create private model repo -> delete)   = write scope test
  2. space-repo write probe  (create private gradio Space -> delete) = Space hosting test
Results appended to brain/hf_probe_results.json
"""
import json, pathlib, time, urllib.request, urllib.error

SECRETS = pathlib.Path("/home/z/my-project/workers/secrets/hf_tokens.json")
TOKS = json.loads(SECRETS.read_text())["tokens"]
OUT = pathlib.Path("/home/z/my-project/brain/hf_probe_results.json")
res = json.loads(OUT.read_text()) if OUT.exists() else {"write_probe": {}, "zerogpu_probe": {}}
res.setdefault("space_probe_v2", {})

def req(method: str, url: str, tok: str, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": "deyoung-fleet/1.0",
    })
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, resp.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:
        return None, str(e)[:200]

for t in TOKS:
    tid, tok, user = t["id"], t["token"], t.get("user", "?")
    rec = {}
    # 1. model repo (pure write-scope test)
    st, body = req("POST", "https://huggingface.co/api/repos/create", tok,
                   {"type": "model", "name": "deyoung-probe", "private": True})
    rec["model_create"] = f"{st} {body[:80]}"
    if st == 200 or st == 201:
        time.sleep(1)
        dst, _ = req("DELETE", f"https://huggingface.co/api/repos/delete?type=model&name=deyoung-probe", tok)
        rec["model_cleanup"] = dst
        rec["model_write"] = True
    else:
        rec["model_write"] = False
    # 2. space repo (Space hosting test)
    st2, body2 = req("POST", "https://huggingface.co/api/repos/create", tok,
                     {"type": "space", "name": "deyoung-probe", "private": True, "sdk": "gradio"})
    rec["space_create"] = f"{st2} {body2[:80]}"
    if st2 == 200 or st2 == 201:
        time.sleep(1)
        dst2, _ = req("DELETE", "https://huggingface.co/api/repos/delete?type=space&name=deyoung-probe", tok)
        rec["space_cleanup"] = dst2
        rec["space_write"] = True
    else:
        rec["space_write"] = False
    res["space_probe_v2"][f"{tid}:{user}"] = rec
    print(f"{tid}:{user} model_write={rec['model_write']} space_write={rec['space_write']} | model:{rec['model_create'][:60]} | space:{rec['space_create'][:60]}", flush=True)

OUT.write_text(json.dumps(res, indent=2))
print("saved", OUT)
