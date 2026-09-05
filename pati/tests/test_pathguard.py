"""Security unit tests: path guard vs traversal, symlinks, escapes; permissions."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from pati_agent.policy import (DEFAULT_PERMISSIONS, PolicyEngine, PolicyViolation,
                               DELETE_FILES, EXECUTE_COMMANDS)


@pytest.fixture()
def engine(tmp_path):
    root = tmp_path / "PATI_workspace"
    (root / "sub").mkdir(parents=True)
    return PolicyEngine(allowed_roots=[str(root)], permissions=list(DEFAULT_PERMISSIONS),
                        allowed_commands=[]), root


def test_inside_root_ok(engine):
    e, root = engine
    p = e.validate_path(str(root / "sub" / "file.txt"))
    assert str(p).startswith(str(root.resolve()))


def test_traversal_blocked(engine):
    e, root = engine
    with pytest.raises(PolicyViolation):
        e.validate_path(str(root / "sub" / ".." / ".." / "etc" / "passwd"))


def test_absolute_escape_blocked(engine):
    e, root = engine
    with pytest.raises(PolicyViolation):
        e.validate_path("/etc/passwd" if os.name != "nt" else "C:/Windows/system32/config")


def test_null_byte_and_wildcards(engine):
    e, root = engine
    with pytest.raises(PolicyViolation):
        e.validate_path(str(root / "a\x00b"))
    with pytest.raises(PolicyViolation):
        e.validate_path(str(root / "*.txt"))


def test_symlink_escape_blocked(engine, tmp_path):
    e, root = engine
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "leak"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(PolicyViolation):
        e.validate_path(str(root / "leak" / "secret.txt"))
    # symlinked file
    (outside / "f.txt").write_text("secret")
    link2 = root / "leakfile"
    link2.symlink_to(outside / "f.txt")
    with pytest.raises(PolicyViolation):
        e.validate_path(str(link2))


def test_relative_path_resolves_inside_default_root(engine):
    e, root = engine
    p = e.validate_path("sub/file.txt")
    assert str(p).startswith(str(root.resolve()))


def test_dangerous_permissions_off_by_default(engine):
    e, root = engine
    assert DELETE_FILES not in e.permissions
    assert EXECUTE_COMMANDS not in e.permissions
    with pytest.raises(PolicyViolation):
        e.require(DELETE_FILES)


def test_delete_root_itself_refuses(tmp_path):
    from pati_agent.fsops import FSOperations
    from pati_agent.audit import AuditLog
    root = tmp_path / "ws"
    root.mkdir()
    e = PolicyEngine(allowed_roots=[str(root)], permissions=list(DEFAULT_PERMISSIONS) + [DELETE_FILES])
    fs = FSOperations(e, AuditLog(tmp_path / "audit.jsonl"))
    with pytest.raises(PolicyViolation):
        fs.delete_path({"path": str(root), "root": str(root)})


def test_command_allowlist(tmp_path):
    e = PolicyEngine(allowed_roots=[str(tmp_path)], permissions=[EXECUTE_COMMANDS],
                     allowed_commands=["python3"])
    e.validate_command(["python3", "-c", "print(1)"])
    with pytest.raises(PolicyViolation):
        e.validate_command(["rm", "-rf", "/"])


def test_audit_chain_tamper_evident(tmp_path):
    from pati_agent.audit import AuditLog
    path = tmp_path / "audit.jsonl"
    a = AuditLog(path)
    for i in range(5):
        a.append("test.action", f"res-{i}", {"i": i})
    ok, n = a.verify()
    assert ok and n == 5
    # tamper
    lines = path.read_text().splitlines()
    rec = lines[2].replace("res-2", "res-HACKED")
    lines[2] = rec
    path.write_text("\n".join(lines) + "\n")
    ok, n = AuditLog(path).verify()
    assert not ok, "tampering must be detected"
