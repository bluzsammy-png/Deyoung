#!/usr/bin/env python3
"""Task 67 — live canary for the two NEW fleet planes:
  * Baidu AI Studio LLM API (OpenAI-compatible, base https://aistudio.baidu.com/llm/lmapi/v3)
  * ModelScope API-Inference   (OpenAI-compatible, base https://api-inference.modelscope.cn/v1)

Secrets: workers/secrets/{baidu,modelscope}_tokens.json (never argv, never printed).
Burn discipline: single call per plane, max_completion_tokens capped at 16.
Evidence: brain/new_planes_canary_67.json (key masked to 6-char prefix).
Exit 0 only if BOTH planes pass.
"""
import json
import time
import urllib.request
import urllib.error
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BAIDU_F = os.path.join(ROOT, "workers/secrets/baidu_tokens.json")
MS_F = os.path.join(ROOT, "workers/secrets/modelscope_tokens.json")
OUT = os.path.join(ROOT, "brain/new_planes_canary_67.json")


def mask(t):
    return (t[:6] + "…") if t else "missing"


def load(path, plane):
    with open(path) as f:
        d = json.load(f)
    t = d["tokens"][0]
    return t["token"], t["base_url"], t.get("default_model"), t.get("fallback_model")


def req(url, token, payload=None, timeout=90):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    r.add_header("Authorization", f"Bearer {token}")
    r.add_header("Content-Type", "application/json")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            return resp.status, body, round(time.time() - t0, 2), None
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {}
        return e.code, body, round(time.time() - t0, 2), f"HTTP {e.code}"
    except Exception as e:
        return None, {}, round(time.time() - t0, 2), f"{type(e).__name__}: {str(e)[:120]}"


def canary_baidu():
    tok, base, model, _ = load(BAIDU_F, "baidu")
    ev = {"plane": "baidu_aistudio", "key": mask(tok), "base_url": base}
    # doctor-safe probe candidate: does a plain GET /models exist?
    st, body, lat, err = req(base + "/models", tok)
    ev["models_list"] = {"status": st, "err": err}
    # real canary: 16-token completion (minimal burn)
    st, body, lat, err = req(base + "/chat/completions", tok, {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_completion_tokens": 16,
        "stream": False,
    })
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    ev["chat"] = {
        "status": st, "latency_s": lat, "err": err,
        "model": body.get("model"), "finish": choice.get("finish_reason"),
        "content_preview": (msg.get("content") or "")[:60],
        "reasoning_present": bool(msg.get("reasoning_content")),
    }
    ev["ok"] = st == 200 and bool(body.get("choices"))
    return ev


def canary_modelscope():
    tok, base, model, fallback = load(MS_F, "modelscope")
    ev = {"plane": "modelscope", "key": mask(tok), "base_url": base}
    st, body, lat, err = req(base + "/models", tok)
    n = len(body.get("data") or [])
    ev["models_list"] = {"status": st, "count": n, "err": err}
    used = model
    st, body, lat, err = req(base + "/chat/completions", tok, {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
        "max_tokens": 16,
        "stream": False,
    })
    if st == 404 and fallback:  # model unavailable -> try fallback, still one extra call max
        used = fallback
        st, body, lat, err = req(base + "/chat/completions", tok, {
            "model": fallback,
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "max_tokens": 16,
            "stream": False,
        })
    choice = (body.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    ev["chat"] = {
        "status": st, "latency_s": lat, "err": err, "model_requested": model,
        "model_used": body.get("model") or used,
        "finish": choice.get("finish_reason"),
        "content_preview": (msg.get("content") or "")[:60],
    }
    ev["ok"] = st == 200 and bool(body.get("choices"))
    return ev


def main():
    results = {"generated": time.strftime("%FT%TZ", time.gmtime()), "planes": []}
    rc = 0
    for name, fn in [("baidu", canary_baidu), ("modelscope", canary_modelscope)]:
        try:
            ev = fn()
        except Exception as e:
            ev = {"plane": name, "ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}
        results["planes"].append(ev)
        if not ev.get("ok"):
            rc = 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    for ev in results["planes"]:
        print(f"[canary] {ev['plane']}: {'PASS' if ev.get('ok') else 'FAIL'} "
              f"(key {ev.get('key', '?')}, chat status {ev.get('chat', {}).get('status')}, "
              f"{ev.get('chat', {}).get('latency_s')}s, err={ev.get('chat', {}).get('err') or ev.get('error')})")
    print(f"[canary] evidence -> {OUT}")
    raise SystemExit(rc)


if __name__ == "__main__":
    main()
