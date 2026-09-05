print("[probe] starting")
import urllib.request

SITE = "https://deeyoung-production-72ef.up.railway.app"

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception as e:
        return f"ERR {type(e).__name__}: {e}"

html = get(SITE)
if html.startswith("ERR"):
    print("[probe] site:", html)
else:
    checks = {
        "4K removed": ("4K" not in html and "HD" in html),
        "no em dash": ("\u2014" not in html),
        "colon See Plans": ("See Plans" in html),
        "no Made with DeYoung": ("Made with DeYoung" not in html),
        "no star glyphs": ("\u2605" not in html),
    }
    for k, v in checks.items():
        print(f"[probe] {k}: {'PASS' if v else 'FAIL'}")
print("[probe] done")
