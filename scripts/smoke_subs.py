#!/usr/bin/env python3
"""E2E smoke test for DeYoung subscription tiers + video request queue (Task 18)."""
import json
import urllib.request
import urllib.error
import uuid

BASE = "http://localhost:3000"
ADMIN = ("admin@deyoung.site", "deyoung123")

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(f"  {'PASS' if cond else 'FAIL'} — {name}" + (f"  [{detail}]" if detail and not cond else ""))


def req(method, path, body=None, headers=None, raw_body=None, content_type=None):
    data = None
    hdrs = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
        if content_type:
            hdrs["Content-Type"] = content_type
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(r) as res:
            return res.status, json.loads(res.read().decode() or "{}"), res.headers
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}"), e.headers
        except Exception:
            return e.code, {}, e.headers


def multipart(field, filename, mime, payload: bytes):
    boundary = uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'.encode(),
        f"Content-Type: {mime}\r\n\r\n".encode(),
        payload,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


email = f"smoke.{uuid.uuid4().hex[:8]}@example.com"
UNIQUE = uuid.uuid4().hex[:8]  # makes prompts unique per run → deterministic fresh-queue behavior


def cleanup_previous():
    """Remove leftovers from earlier smoke runs so re-runs start clean."""
    st, body, hdrs = req("POST", "/api/auth/login", {"email": ADMIN[0], "password": ADMIN[1]})
    if st != 200:
        return
    cookie = (hdrs.get("Set-Cookie") or "").split(";")[0]
    auth = {"Cookie": cookie}
    st, body, _ = req("GET", "/api/subscriptions", headers=auth)
    for s in body.get("subscriptions", []):
        if s["email"].startswith("smoke."):
            req("DELETE", f"/api/subscriptions/{s['id']}", headers=auth)


cleanup_previous()

print("== 1. public: create pending subscription ==")
st, body, _ = req("POST", "/api/subscriptions", {"name": "Smoke Tester", "email": email, "planCode": "beginner"})
check("subscription created (201)", st == 201, str(body))
sub_id = body["subscription"]["id"]
check("status pending", body["subscription"]["status"] == "pending")

print("== 2. request with pending sub is rejected ==")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": "a red bird flying over the city at dusk", "seconds": 15, "resolution": "720p"})
check("rejected 403 while pending", st == 403, f"{st} {body}")

print("== 3. admin login + activate ==")
st, body, hdrs = req("POST", "/api/auth/login", {"email": ADMIN[0], "password": ADMIN[1]})
check("admin login", st == 200, str(body))
cookie = (hdrs.get("Set-Cookie") or "").split(";")[0]
AUTH = {"Cookie": cookie}

st, body, _ = req("PATCH", f"/api/subscriptions/{sub_id}", {"action": "activate", "months": 1}, headers=AUTH)
check("subscription activated", st == 200 and body["subscription"]["status"] == "active", str(body))
check("period end set ~1 month", bool(body["subscription"]["periodEnd"]))

print("== 4. tier enforcement (beginner) ==")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": "long cinematic take over the skyline", "seconds": 60, "resolution": "720p"}, headers=AUTH)
check("60s rejected on beginner", st == 403, f"{st} {body}")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": "crisp hd shot of a red drum set", "seconds": 15, "resolution": "1080p"}, headers=AUTH)
check("1080p rejected on beginner", st == 403, f"{st} {body}")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": "drumming clip with sound", "seconds": 10, "resolution": "720p", "withAudio": True}, headers=AUTH)
check("audio rejected on beginner", st == 403, f"{st} {body}")

print("== 5. valid request queues ==")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": f"a red bird flying over the city at dusk {UNIQUE}", "seconds": 15, "resolution": "720p"}, headers=AUTH)
check("valid request queued (201)", st == 201, f"{st} {body}")
r1 = body["request"]
check("queue position 1", body["queuePosition"] == 1, str(body.get("queuePosition")))
check("eta days >= 1", body["etaDays"] >= 1)
check("usage 1/4", body["usage"] == {"used": 1, "quota": 4}, str(body.get("usage")))

print("== 6. concurrent limit (beginner = 1) ==")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": f"a totally different clip of ocean waves {UNIQUE}", "seconds": 10, "resolution": "720p"}, headers=AUTH)
check("2nd concurrent rejected 429", st == 429, f"{st} {body}")

print("== 7. admin renders + delivers ==")
st, body, _ = req("PATCH", f"/api/requests/{r1['id']}", {"action": "start"}, headers=AUTH)
check("start render", st == 200 and body["request"]["status"] == "rendering", str(body))

payload, ctype = multipart("file", "result.mp4", "video/mp4", b"\x00\x00\x00\x18ftypmp42" + b"0" * 256)
st, body, _ = req("POST", "/api/upload", raw_body=payload, content_type=ctype, headers=AUTH)
check("video upload accepted", st == 200 and body.get("url", "").endswith(".mp4"), f"{st} {body}")
video_url = body["url"]

st, body, _ = req("PATCH", f"/api/requests/{r1['id']}", {"action": "deliver", "resultUrl": video_url, "gpuMinutes": 7.5}, headers=AUTH)
check("deliver marks done", st == 200 and body["request"]["status"] == "done", str(body))

print("== 8. public status check ==")
st, body, _ = req("GET", f"/api/requests/{r1['id']}?email={email}")
check("status endpoint works", st == 200 and body["request"]["status"] == "done", f"{st} {body}")
check("result url present", body["request"]["resultUrl"] == video_url)

print("== 9. dedup cache hit ==")
st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": f"a red bird flying over the city at dusk {UNIQUE}", "seconds": 15, "resolution": "720p"}, headers=AUTH)
check("identical request = cache hit", st == 201 and body.get("fromCache") is True, f"{st} {body}")
check("cache hit has result", st == 201 and body.get("request", {}).get("resultUrl", "").endswith(".mp4"), str(body.get("request", {}).get("resultUrl")))

print("== 10. quota exhaustion (4/month) ==")
# usage now: 2 (1 real + 1 cache). Submit 2 more distinct, delivering each (concurrent=1).
for i in range(2):
    st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": f"unique clip number {i} of a red market {UNIQUE}", "seconds": 5, "resolution": "720p"}, headers=AUTH)
    if st != 201:
        check(f"extra request {i} created", False, f"{st} {body}")
        break
    rid = body["request"]["id"]
    req("PATCH", f"/api/requests/{rid}", {"action": "start"}, headers=AUTH)
    req("PATCH", f"/api/requests/{rid}", {"action": "deliver", "resultUrl": video_url, "gpuMinutes": 1}, headers=AUTH)
else:
    st, body, _ = req("POST", "/api/requests", {"email": email, "prompt": f"one video beyond the quota of four {UNIQUE}", "seconds": 5, "resolution": "720p"}, headers=AUTH)
    check("5th video rejected 429", st == 429, f"{st} {body}")

print("== 11. plans editable by owner ==")
st, body, _ = req("PUT", "/api/plans", {"plans": [{"code": "beginner", "priceMonthly": 12}]}, headers=AUTH)
check("admin PUT plans", st == 200, str(body))
st, body, _ = req("GET", "/api/plans")
beg = [p for p in body["plans"] if p["code"] == "beginner"][0]
check("price change is live", beg["priceMonthly"] == 12, str(beg["priceMonthly"]))
st, body, _ = req("PUT", "/api/plans", {"plans": [{"code": "beginner", "priceMonthly": 9}]}, headers=AUTH)
check("price reverted", st == 200, str(body))

print("== 12. guards ==")
st, body, _ = req("GET", "/api/subscriptions")
check("subs list requires owner", st == 401, str(st))
st, body, _ = req("GET", "/api/requests")
check("queue list requires owner", st == 401, str(st))
st, body, _ = req("PUT", "/api/plans", {"plans": [{"code": "beginner", "priceMonthly": 1}]})
check("plans PUT requires owner", st == 401, str(st))

print("== 13. overview stats ==")
st, body, _ = req("GET", "/api/overview", headers=AUTH)
check("overview has sub stats", st == 200 and "subscribersActive" in body["stats"], str(body)[:120])
check("capacity fields present", "gpuMinutesToday" in body["stats"] and "gpuMinutesBudget" in body["stats"])
check("subs MRR counted", body["stats"]["subsMrr"] >= 9, str(body["stats"].get("subsMrr")))

print("== 14. cleanup ==")
st, body, _ = req("DELETE", f"/api/subscriptions/{sub_id}", headers=AUTH)
check("test data cleaned up", st == 200, f"{st} {body}")

print(f"\n===== {len(passed)} passed, {len(failed)} failed =====")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
