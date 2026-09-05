"""`pati-agent` CLI entry point.

Commands:
  setup              12-step installation wizard (pairing, folders, permissions)
  run                run the agent loop (foreground)
  doctor             diagnostics with actionable fixes
  status             show agent config summary
  update             check/apply free-channel updates
  authorize-folder   add | remove | list  authorized folders
  permissions        grant | revoke | list  permissions
  allow-command      add | remove | list  command allowlist (EXECUTE_COMMANDS)
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
from pathlib import Path

from .config import AgentConfig
from .policy import ALL_PERMISSIONS


def _cfg_path() -> Path:
    return Path.home() / ("PATI/agent/config.json" if os.name == "nt"
                          else ".pati/agent/config.json")


def _load() -> AgentConfig:
    p = _cfg_path()
    if not p.exists():
        print("no config found. Run the wizard first:  pati-agent setup", file=sys.stderr)
        sys.exit(1)
    return AgentConfig.load(p)


def _save(cfg: AgentConfig) -> None:
    cfg.save(_cfg_path())


def cmd_setup(args):
    from .wizard import run_wizard
    roots = args.root or None
    run_wizard(server=args.server or "", code=args.code or "",
               non_interactive_roots=roots, assume_yes=args.yes)


def cmd_run(args):
    from .agent import PatiAgent
    cfg = _load()
    agent = PatiAgent.from_config(cfg)
    print(f"PATI Local Agent running -> {cfg.server_url} (worker {cfg.worker_name})")
    print(f"authorized folders: {cfg.allowed_roots}")
    print(f"permissions: {cfg.permissions}")
    print("Ctrl+C to stop")
    agent.start()
    try:
        agent.wait()
    except KeyboardInterrupt:
        pass
    finally:
        agent.stop()
        print("agent stopped")


def cmd_doctor(args):
    from .doctor import run_doctor
    sys.exit(run_doctor())


def cmd_status(args):
    cfg = _load()
    print(json.dumps({
        "server": cfg.server_url, "worker_id": cfg.worker_id, "name": cfg.worker_name,
        "authorized_roots": cfg.allowed_roots, "permissions": cfg.permissions,
        "allowed_commands": cfg.allowed_commands, "autostart": cfg.autostart,
    }, indent=2))


def cmd_update(args):
    from .updater import check_updates
    sys.exit(check_updates(apply=args.yes))


def cmd_authorize_folder(args):
    cfg = _load()
    if args.action == "list":
        print("\n".join(cfg.allowed_roots) or "(none)")
        return
    if args.action == "add":
        p = pathlib.Path(args.path).expanduser().resolve()
        if not p.exists():
            print(f"creating {p}")
            p.mkdir(parents=True, exist_ok=True)
        if str(p) not in cfg.allowed_roots:
            cfg.allowed_roots.append(str(p))
        _save(cfg)
        print(f"authorized: {p}")
        _resync_capabilities(cfg)
        return
    if args.action == "remove":
        p = str(pathlib.Path(args.path).expanduser().resolve())
        cfg.allowed_roots = [r for r in cfg.allowed_roots if r != p]
        _save(cfg)
        print(f"removed: {p}")
        return


def cmd_permissions(args):
    cfg = _load()
    if args.action == "list":
        for perm in ALL_PERMISSIONS:
            mark = "*" if perm in cfg.permissions else " "
            print(f"{mark} {perm}")
        print("\n(* = granted; dangerous permissions should stay off unless needed)")
        return
    if args.action == "grant":
        if args.perm not in ALL_PERMISSIONS:
            print(f"unknown permission: {args.perm}", file=sys.stderr)
            sys.exit(2)
        if args.perm not in cfg.permissions:
            cfg.permissions.append(args.perm)
        _save(cfg)
        print(f"granted: {args.perm}")
        _resync_capabilities(cfg)
        return
    if args.action == "revoke":
        cfg.permissions = [p for p in cfg.permissions if p != args.perm]
        _save(cfg)
        print(f"revoked: {args.perm}")
        _resync_capabilities(cfg)
        return


def cmd_allow_command(args):
    cfg = _load()
    if args.action == "list":
        print("\n".join(cfg.allowed_commands) or "(none)")
        return
    if args.action == "add":
        if args.name not in cfg.allowed_commands:
            cfg.allowed_commands.append(args.name)
        _save(cfg)
        print(f"allowlisted: {args.name} (EXECUTE_COMMANDS still required)")
        return
    if args.action == "remove":
        cfg.allowed_commands = [c for c in cfg.allowed_commands if c != args.name]
        _save(cfg)
        print(f"removed: {args.name}")


def _resync_capabilities(cfg: AgentConfig) -> None:
    """Push updated capabilities to the control plane after policy changes."""
    try:
        from .api_client import AgentAPI
        from .sysinfo import resource_report
        api = AgentAPI(cfg.server_url, cfg.token)
        engine = cfg.policy_engine()
        # capability sync happens via heartbeat -> resources; registration is
        # immutable, so we simply heartbeat and note the new capability set.
        api.heartbeat(cfg.worker_id, resource_report(cfg.allowed_roots))
        print(f"capabilities now: {engine.capabilities()}")
    except Exception as e:
        print(f"warning: could not resync with server ({e})")


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="pati-agent",
                                 description="PATI Local Agent - secure bridge to this computer")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup", help="run the installation wizard")
    p.add_argument("--server", default="")
    p.add_argument("--code", default="", help="one-time pairing code from 'pati admin-pair'")
    p.add_argument("--root", action="append", help="authorized folder (repeatable)")
    p.add_argument("--yes", action="store_true", help="accept defaults (non-interactive)")
    p.set_defaults(fn=cmd_setup)

    sub.add_parser("run", help="run the agent").set_defaults(fn=cmd_run)
    sub.add_parser("doctor", help="run diagnostics").set_defaults(fn=cmd_doctor)
    sub.add_parser("status", help="show config summary").set_defaults(fn=cmd_status)
    p = sub.add_parser("update"); p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_update)

    p = sub.add_parser("authorize-folder"); p.add_argument("action", choices=["add", "remove", "list"])
    p.add_argument("path", nargs="?", default=""); p.set_defaults(fn=cmd_authorize_folder)
    p = sub.add_parser("permissions"); p.add_argument("action", choices=["grant", "revoke", "list"])
    p.add_argument("perm", nargs="?", default=""); p.set_defaults(fn=cmd_permissions)
    p = sub.add_parser("allow-command"); p.add_argument("action", choices=["add", "remove", "list"])
    p.add_argument("name", nargs="?", default=""); p.set_defaults(fn=cmd_allow_command)

    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
