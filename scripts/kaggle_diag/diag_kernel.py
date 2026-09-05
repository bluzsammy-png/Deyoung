print("[diag] starting")
import urllib.request, json

SITE = "https://deeyoung-production-72ef.up.railway.app"

def probe(url, method="GET", data=None, headers=None):
    try:
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        with urllib.request.urlopen(req, timeout=45) as r:
            return f"HTTP {r.status}: {r.read()[:250]}"
    except Exception as e:
        body = ""
        try:
            body = e.read()[:250]
        except Exception:
            pass
        return f"ERR {type(e).__name__}: {e} {body}"

try:
    import torch
    print("[diag] cuda:", torch.cuda.is_available(),
          torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no-gpu")
except Exception as e:
    print("[diag] torch ERR", e)

print("[diag] site /api/health ->", probe(f"{SITE}/api/health"))
print("[diag] site / ->", probe(SITE))
print("[diag] huggingface ->", probe("https://huggingface.co/api/models/Lightricks/LTX-Video-0.9.5"))
print("[diag] done")
