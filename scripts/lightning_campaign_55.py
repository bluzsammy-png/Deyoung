#!/usr/bin/env python3
"""Task 55: Lightning campaign controller — renders the 20s UGC launch cut on
the owner's deyoung-h3 studio (T4) while the Kaggle fleet is quota-grounded.

Credit-burn guard (owner order):
  - studio starts ONLY when there is work
  - the moment campaign finishes (or fatals), the studio is STOPPED
  - hard wall-clock cap + minimum-balance kill switch
  - balance sampled every cycle; every delta logged

  python3 scripts/lightning_campaign_55.py        # env LIGHTNING_API_KEY auto-loaded
"""
import json
import os
import pathlib
import sys
import time

ROOT = pathlib.Path("/home/z/my-project")
SEV = ROOT / "workers/secrets/lightning_tokens.json"
SUPA = ROOT / "workers/secrets/supabase.json"
WORKER_LOCAL = ROOT / "campaign/site-worker/deyoung-lightning-c20.py"
EVID = ROOT / "brain/lightning_c20_evidence.json"
STATE = ROOT / "brain/state.json"

_key = json.loads(SEV.read_text())["keys"][0]
KEY = os.environ.get("LIGHTNING_API_KEY") or _key["key"]
os.environ["LIGHTNING_API_KEY"] = KEY  # SDK reads env at import/auth time
SUPA_URL = json.loads(SUPA.read_text())["supabase"]["supabase_url"]
SUPA_KEY = json.loads(SUPA.read_text())["supabase"]["service_role_key"]

import requests
from lightning_sdk import Studio

BASE = "https://lightning.ai"
PROJECT_ID = _key["teamspace_id"]
HDR = {"Authorization": f"Bearer {KEY}"}
MIN_BALANCE = 3.0           # kill switch: keep credits in reserve
HARD_CAP_MIN = 20 * 60      # absolute wall-clock cap for this controller
POLL_SEC = 120


def balance():
    try:
        r = requests.get(f"{BASE}/v1/memberships", headers=HDR, timeout=25)
        for m in r.json().get("memberships", []):
            if m.get("projectId") == PROJECT_ID:
                return m.get("balance")
    except Exception as e:
        print("[ctl] balance err", repr(e)[:120], flush=True)
    return None


def ev_write(**kw):
    ev = {}
    if EVID.exists():
        try:
            ev = json.loads(EVID.read_text())
        except Exception:
            ev = {}
    ev.update(kw)
    ev["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    EVID.write_text(json.dumps(ev, indent=1))


def stop_studio(st, why):
    try:
        st.stop()
        ev_write(stop_reason=why, stopped_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        print(f"[ctl] studio STOPPED ({why}) - credits safe", flush=True)
    except Exception as e:
        ev_write(stop_error=repr(e)[:300])
        print("[ctl] stop err", repr(e)[:200], flush=True)


def main():
    b0 = balance()
    ev_write(started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
             balance_before=b0)
    print(f"[ctl] balance before: {b0}", flush=True)

    st = Studio(name="deyoung-h3", teamspace="default-project", user=_key["account"])

    # poll-only mode: studio already Running on T4 (prepared in a foreground step)
    if os.environ.get("CTL_SKIP_BOOT") == "1":
        s = str(st.status)
        m = str(getattr(st, "machine", "?"))
        print(f"[ctl] poll-only boot skip: status={s} machine={m}", flush=True)
        if "Running" not in s:
            ev_write(fatal=f"CTL_SKIP_BOOT but studio {s}")
            sys.exit(8)
        gpu = st.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | head -1").strip()
        ev_write(machine=m, gpu=gpu)
        print(f"[ctl] gpu={gpu}", flush=True)
        if "T4" not in gpu and "Tesla" not in gpu:
            stop_studio(st, "no_gpu_poll_only")
            sys.exit(3)
        # fall through to push+launch
    else:
        # settle-loop start
        for i in range(40):
            s = str(st.status)
            if "Running" in s:
                break
            if "Stopped" in s:
                t0 = time.time()
                st.start()
                print(f"[ctl] started in {time.time()-t0:.0f}s", flush=True)
                break
            print(f"[ctl] status {s}, waiting...", flush=True)
            time.sleep(15)
        else:
            print("[ctl] FATAL: studio never settled", flush=True)
            sys.exit(2)

    time.sleep(20)
    machine = str(getattr(st, "machine", "?"))
    print(f"[ctl] machine after start: {machine}", flush=True)

    # T4 does NOT persist across stop/start: re-attach every session
    if "T4" not in machine:
        try:
            from lightning_sdk.machine import Machine
            print("[ctl] re-attaching T4 machine ...", flush=True)
            st.switch_machine(Machine.T4)
            ev_write(machine_switch="T4 re-attached")
            time.sleep(30)
            for i in range(40):
                s = str(st.status)
                if "Running" in s:
                    break
                print(f"[ctl] switch settle: {s}", flush=True)
                time.sleep(15)
        except Exception as e:
            ev_write(fatal=f"machine switch failed: {e!r}"[:300])
            print("[ctl] FATAL switch:", repr(e)[:200], flush=True)
            stop_studio(st, "switch_failed")
            sys.exit(7)

    for i in range(20):
        gpu = st.run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>&1 | head -1")
        if "Tesla" in gpu or "T4" in gpu:
            break
        print(f"[ctl] gpu not ready ({gpu.strip()[:60]}), retrying...", flush=True)
        time.sleep(20)
    machine = str(getattr(st, "machine", "?"))
    gpu = gpu.strip()
    ev_write(machine=machine, gpu=gpu)
    print(f"[ctl] machine={machine} gpu={gpu}", flush=True)
    if "T4" not in gpu and "Tesla" not in gpu:
        ev_write(fatal="no GPU visible inside studio", gpu_raw=gpu)
        stop_studio(st, "no_gpu")
        sys.exit(3)

    # push worker + launch with secrets as env
    st.upload_file(str(WORKER_LOCAL), "h3work/c20_worker.py")
    ev_write(worker_uploaded=True)
    launch = (f"cd /teamspace/studios/this_studio/h3work && "
              f"SUPA_URL='{SUPA_URL}' SUPA_KEY='{SUPA_KEY}' "
              f"nohup python3 c20_worker.py > c20.log 2>&1 & echo LAUNCHED_PID=$!")
    out = st.run(launch)
    ev_write(launched=out.strip()[:80],
             launched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print("[ctl] worker launched:", out.strip()[:60], flush=True)

    # poll loop
    t_start = time.time()
    last_bal = b0
    while True:
        time.sleep(POLL_SEC)
        el = (time.time() - t_start) / 60
        status = ""
        summary = {}
        try:
            status = st.run("tail -c 700 /teamspace/studios/this_studio/h3work/c20.log 2>/dev/null || echo NOLOG")
            raw = st.run("python3 -c \"import json;d=json.load(open('/teamspace/studios/this_studio/h3work/status_c20.json'));print(json.dumps({'phase':d.get('phase'),'ok':d.get('ok'),'total':d.get('total'),'done':d.get('done'),'failed':d.get('failed'),'fix':d.get('fix'),'elapsed_min':d.get('elapsed_min')}))\" 2>/dev/null || echo NOFILE")
            if "NOFILE" not in raw and raw.strip().startswith("{"):
                summary = json.loads(raw.strip())
        except Exception as e:
            status = f"RUN_ERR {e!r}"[:300]
            print("[ctl] poll err", repr(e)[:150], flush=True)
        bal = balance()
        delta = None if (bal is None or last_bal is None) else round(bal - last_bal, 4)
        print(f"[ctl] t+{el:.0f}min bal={bal} (d={delta}) phase={summary.get('phase')} :: {status[-200:]}", flush=True)
        ev_write(last_poll=f"t+{el:.0f}min", balance=bal, burn_since_last=delta,
                 summary=summary, log_tail=status[-600:])

        if isinstance(bal, (int, float)) and bal < MIN_BALANCE:
            ev_write(fatal=f"balance {bal} below floor {MIN_BALANCE}")
            stop_studio(st, "min_balance")
            sys.exit(4)
        if el > HARD_CAP_MIN:
            ev_write(fatal="hard wall-clock cap")
            stop_studio(st, "hard_cap")
            sys.exit(5)
        if summary.get("phase") == "finished":
            ev_write(campaign_result={"ok": summary.get("ok"), "total": summary.get("total"),
                                      "fix": summary.get("fix")},
                     finished_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            stop_studio(st, f"campaign_finished ok={summary.get('ok')}/{summary.get('total')}")
            print("[ctl] CAMPAIGN FINISHED ok=", summary.get("ok"), "/", summary.get("total"), flush=True)
            sys.exit(0)
        if summary.get("phase") == "fatal":
            ev_write(fatal=str(summary.get("failed"))[:300] + " | log: " + status[-400:])
            stop_studio(st, "worker_fatal")
            sys.exit(6)


if __name__ == "__main__":
    main()
