"""Local Agent policy engine: permissions + filesystem allowlist + path guard.

Security invariants (see docs/SECURITY.md):
- PATI never receives unrestricted hard-drive access. Only explicitly
  authorized folders are reachable, enforced HERE on the owner's machine.
- Dangerous permissions (DELETE_FILES, EXECUTE_COMMANDS, RUN_SCRIPTS,
  RUN_LOCAL_MODELS) are disabled by default.
- Path traversal, absolute escapes, UNC/device paths, symlink escapes and
  null-byte tricks are rejected before any syscall happens.
- Every operation is audit-logged (hash-chained, tamper-evident).
"""
from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------
READ_FILES = "READ_FILES"
CREATE_FILES = "CREATE_FILES"
MODIFY_FILES = "MODIFY_FILES"
COPY_FILES = "COPY_FILES"
MOVE_FILES = "MOVE_FILES"
DELETE_FILES = "DELETE_FILES"
EXECUTE_COMMANDS = "EXECUTE_COMMANDS"
RUN_SCRIPTS = "RUN_SCRIPTS"
RUN_LOCAL_MODELS = "RUN_LOCAL_MODELS"
SAVE_ARTIFACTS = "SAVE_ARTIFACTS"

ALL_PERMISSIONS = [READ_FILES, CREATE_FILES, MODIFY_FILES, COPY_FILES, MOVE_FILES,
                   DELETE_FILES, EXECUTE_COMMANDS, RUN_SCRIPTS, RUN_LOCAL_MODELS,
                   SAVE_ARTIFACTS]

DANGEROUS = {DELETE_FILES, EXECUTE_COMMANDS, RUN_SCRIPTS, RUN_LOCAL_MODELS}

# Disabled by default per master spec; the wizard must explicitly enable them.
DEFAULT_PERMISSIONS = [READ_FILES, CREATE_FILES, MODIFY_FILES, COPY_FILES, MOVE_FILES,
                       SAVE_ARTIFACTS]

CAPABILITY_FOR_PERMISSION = {
    READ_FILES: "filesystem_read",
    CREATE_FILES: "filesystem_create",
    MODIFY_FILES: "filesystem_modify",
    COPY_FILES: "filesystem_copy",
    MOVE_FILES: "filesystem_move",
    DELETE_FILES: "filesystem_delete",
    EXECUTE_COMMANDS: "run_commands",
    RUN_SCRIPTS: "run_scripts",
    RUN_LOCAL_MODELS: "run_local_models",
    SAVE_ARTIFACTS: "artifact_save_local",
}


class PolicyViolation(Exception):
    """Raised when an operation is not authorized. error_code=SECURITY_VIOLATION."""
    def __init__(self, message: str):
        self.error_code = "SECURITY_VIOLATION"
        super().__init__(message)


@dataclass
class PolicyEngine:
    allowed_roots: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=lambda: list(DEFAULT_PERMISSIONS))
    allowed_commands: list[str] = field(default_factory=list)  # basenames, exact match

    # ------------------------------------------------------------------ perms
    def can(self, permission: str) -> bool:
        return permission in self.permissions

    def require(self, permission: str | list[str]) -> None:
        needed = [permission] if isinstance(permission, str) else permission
        missing = [p for p in needed if not self.can(p)]
        if missing:
            raise PolicyViolation(
                f"permission not granted: {', '.join(missing)}. "
                f"Grant it via: pati-agent permissions grant {missing[0]}")

    def capabilities(self) -> list[str]:
        caps = ["system_inspection", "filesystem_list"]
        for perm in self.permissions:
            caps.append(CAPABILITY_FOR_PERMISSION[perm])
        if self.can(READ_FILES):
            caps.append("filesystem_organize" if (self.can(CREATE_FILES) and self.can(MOVE_FILES))
                        else "filesystem_read")
            caps.append("report_generation" if self.can(CREATE_FILES) else "filesystem_read")
            caps.append("document_research")
        if self.can(RUN_SCRIPTS):
            caps.append("run_scripts")
        return sorted(set(caps))

    # ------------------------------------------------------------ path guard
    def roots(self) -> list[pathlib.Path]:
        return [pathlib.Path(r) for r in self.allowed_roots]

    def resolve_root(self, root_hint: str | None) -> pathlib.Path:
        if root_hint:
            for r in self.roots():
                if os.path.normcase(str(r.resolve())) == os.path.normcase(str(pathlib.Path(root_hint).resolve())):
                    return r
            raise PolicyViolation(f"root not authorized: {root_hint}")
        if not self.allowed_roots:
            raise PolicyViolation("no authorized folders configured; run: pati-agent authorize-folder add <dir>")
        return self.roots()[0]

    def validate_path(self, raw: str, root_hint: str | None = None,
                      must_exist: bool | None = None) -> pathlib.Path:
        """Validate and resolve a path against the allowlist. Raises PolicyViolation."""
        if raw is None:
            raise PolicyViolation("missing path")
        p = str(raw)
        if "\x00" in p:
            raise PolicyViolation("illegal null byte in path")
        if any(ch in p for ch in "*?"):
            raise PolicyViolation("wildcards are not allowed in paths")
        base = self.resolve_root(root_hint)
        candidate = pathlib.Path(p)
        if not candidate.is_absolute():
            candidate = base / candidate
        # normalize (handles .., duplicate separators, forward/back slashes)
        try:
            candidate = candidate.resolve(strict=False)
        except OSError as e:
            raise PolicyViolation(f"cannot resolve path: {e}")
        base_res = base.resolve(strict=False)
        if os.path.normcase(str(candidate)) == os.path.normcase(str(base_res)) :
            inside = True
        else:
            try:
                candidate.relative_to(base_res)
                inside = True
            except ValueError:
                inside = False
        if not inside:
            raise PolicyViolation(
                f"path outside authorized folders: {candidate}. "
                f"Authorized roots: {self.allowed_roots}")
        # symlink escape check: resolve() already follows links; if any final
        # component is a symlink pointing outside the root it would now resolve
        # outside, so the containment test above catches it. Double-check the
        # deepest existing component for defense in depth:
        probe = candidate
        while probe != probe.parent:
            if probe.is_symlink():
                target = probe.resolve(strict=False)
                try:
                    target.relative_to(base_res)
                except ValueError:
                    raise PolicyViolation(f"symlink escapes authorized folder: {probe} -> {target}")
            if not probe.exists():
                break
            probe = probe.parent
        if must_exist is True and not candidate.exists():
            raise PolicyViolation(f"file not found: {candidate}")
        return candidate

    def validate_command(self, argv: list[str]) -> None:
        if not argv:
            raise PolicyViolation("empty command")
        exe = os.path.basename(argv[0]).lower()
        if exe.endswith((".exe", ".cmd", ".bat", ".ps1")):
            exe = exe.rsplit(".", 1)[0]
        if exe not in [c.lower() for c in self.allowed_commands]:
            raise PolicyViolation(
                f"command not allowlisted: {argv[0]}. Allowlist: {self.allowed_commands}. "
                f"Add via: pati-agent allow-command add <name>")
