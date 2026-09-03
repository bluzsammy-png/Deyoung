"""`pati` command line interface - a reference Personal-AI-independent client."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time


def _client(args):
    from .client import PatiClient
    base = args.server or os.environ.get("PATI_SERVER", "http://127.0.0.1:8000")
    token = args.token or os.environ.get("PATI_TOKEN", "")
    if not token:
        print("error: no PATI token. Set PATI_TOKEN or pass --token", file=sys.stderr)
        sys.exit(2)
    return PatiClient(base, token)


def _pp(obj):
    print(json.dumps(obj, indent=2, default=str))


def cmd_status(args):
    pati = _client(args)
    _pp(pati.get_system_status())


def cmd_tasks(args):
    pati = _client(args)
    _pp(pati.list_tasks(status=args.status or "", limit=args.limit))


def cmd_submit(args):
    pati = _client(args)
    params = json.loads(args.params) if args.params else {}
    task = pati.submit_task(args.objective, task_type=args.type or "auto", params=params)
    print(f"submitted {task['id']} ({len(task['stages'])} stages)")
    if args.wait:
        done = pati.wait_for_task(task["id"], timeout_s=args.timeout,
                                  on_log=lambda e: print(f"  [{e['level']}] {e['message']}"))
        _pp({k: done[k] for k in ("id", "status", "error")})
        for a in pati.list_task_artifacts(task["id"]):
            print(f"artifact: {a['id']} {a['name']} ({a['size']} bytes, {a['storage']})")
    else:
        _pp(task)


def cmd_get(args):
    _pp(_client(args).get_task(args.task_id))


def cmd_cancel(args):
    _pp(_client(args).cancel_task(args.task_id))


def cmd_workers(args):
    _pp(_client(args).list_workers())


def cmd_capabilities(args):
    caps = _client(args).get_capabilities()
    for c in caps:
        print(f"{c['capability_id']:<38} {c['category']:<14} {'RISKY' if c['risky'] else '     '} L{c['min_autonomy_level']}")


def cmd_models(args):
    for m in _client(args).list_models():
        print(f"{m['model_id']:<28} {m['provider']:<16} cost={m['cost']} {m['free_status']:<26} {m['status']}")


def cmd_tools(args):
    for t in _client(args).list_tools():
        print(f"{t['tool_id']:<24} {t['status']:<28} {t['description']}")


def cmd_artifacts(args):
    _pp(_client(args).list_task_artifacts(args.task_id) if args.task_id else
        _client(args)._request("GET", "/artifacts")["artifacts"])


def cmd_download(args):
    pati = _client(args)
    path = pati.download_artifact(args.artifact_id, args.out)
    print(f"saved -> {path}")


def cmd_admin_pair(args):
    pati = _client(args)
    code = pati.create_pairing_code()
    print(f"pairing code: {code['code']}  (expires in 15 min)")
    print("run on the target computer: pati-agent setup --server <PATI URL> --code " + code["code"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pati", description="PATI SDK CLI (zero-cost AI infrastructure client)")
    ap.add_argument("--server", default=os.environ.get("PATI_SERVER"))
    ap.add_argument("--token", default=os.environ.get("PATI_TOKEN"))
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="system status").set_defaults(fn=cmd_status)
    p = sub.add_parser("tasks"); p.add_argument("--status", default=""); p.add_argument("--limit", type=int, default=20)
    p.set_defaults(fn=cmd_tasks)
    p = sub.add_parser("submit", help="submit an objective")
    p.add_argument("objective"); p.add_argument("--type", default="auto")
    p.add_argument("--params", default=""); p.add_argument("--wait", action="store_true")
    p.add_argument("--timeout", type=float, default=600)
    p.set_defaults(fn=cmd_submit)
    p = sub.add_parser("get"); p.add_argument("task_id"); p.set_defaults(fn=cmd_get)
    p = sub.add_parser("cancel"); p.add_argument("task_id"); p.set_defaults(fn=cmd_cancel)
    sub.add_parser("workers").set_defaults(fn=cmd_workers)
    sub.add_parser("capabilities").set_defaults(fn=cmd_capabilities)
    sub.add_parser("models").set_defaults(fn=cmd_models)
    sub.add_parser("tools").set_defaults(fn=cmd_tools)
    p = sub.add_parser("artifacts"); p.add_argument("--task-id", default=""); p.set_defaults(fn=cmd_artifacts)
    p = sub.add_parser("download"); p.add_argument("artifact_id"); p.add_argument("out")
    p.set_defaults(fn=cmd_download)
    sub.add_parser("admin-pair", help="issue a one-time pairing code for a new computer").set_defaults(fn=cmd_admin_pair)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
