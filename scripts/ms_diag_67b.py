#!/usr/bin/env python3
"""Task 67b — focused ModelScope 401 diagnostics (body detail, header variants)."""
import json
import urllib.request
import urllib.error

with open("/home/z/my-project/workers/secrets/modelscope_tokens.json") as f:
    tok = json.load(f)["tokens"][0]["token"]

URL = "https://api-inference.modelscope.cn/v1/models"


def probe(label, headers):
    r = urllib.request.Request(URL, method="GET")
    for k, v in headers.items():
        r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            body = resp.read().decode()[:300]
            print(f"[{label}] HTTP {resp.status}: {body}")
    except urllib.error.HTTPError as e:
        print(f"[{label}] HTTP {e.code}: {e.read().decode()[:300]}")
    except Exception as e:
        print(f"[{label}] {type(e).__name__}: {str(e)[:120]}")


probe("bearer", {"Authorization": f"Bearer {tok}"})
probe("raw", {"Authorization": tok})
probe("no-auth", {})
