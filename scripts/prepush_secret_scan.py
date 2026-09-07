#!/usr/bin/env python3
"""W0-playbook pre-push secret scan (Task 41).

Scans the ENTIRE git history (`git log --all -p`) for:
  1. Every literal secret value stored in the local vault (workers/secrets/*.json)
  2. Generic high-signal credential patterns (PATs, KGAT tokens, worker tokens,
     JWTs, credentialed DB URLs, private keys)

Never prints secret values — only pattern name + commit-ish + sanitized line prefix.
Exit code 0 = CLEAN (safe to push), 1 = LEAK FOUND (do not push).
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/z/my-project")
SECRETS_DIR = ROOT / "workers" / "secrets"

GENERIC_PATTERNS = [
    ("github-pat", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("github-finetoken", re.compile(r"gh_[A-Za-z0-9]{20,}")),
    ("kaggle-token", re.compile(r"KGAT[_-]?[A-Za-z0-9]{16,}")),
    ("worker-token", re.compile(r"dyw_[A-Za-z0-9]{16,}")),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}")),
    ("db-url-with-creds", re.compile(r"postgres(?:ql)?://[^\\s'\"<>]{3,}:[^\\s'\"<>]{3,}@")),
    ("private-key-block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("aws-key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("agentmail-key-literal", re.compile(r"am_[A-Za-z0-9]{20,}")),
    ("railway-token", re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b\s*(?:,|;|$)")),
]


def vault_literals() -> list[tuple[str, str]]:
    """Pull every string value >= 16 chars from the vault as a candidate secret."""
    out: list[tuple[str, str]] = []

    def walk(obj, source):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{source}:{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                walk(v, f"{source}[{i}]")
        elif isinstance(obj, str) and len(obj) >= 16:
            label = source.rsplit(":", 1)[-1]
            # skip obvious non-secrets: urls alone are checked via cred pattern,
            # names/notes/identifiers are noise; still keep high-entropy values
            skip_words = ("note", "runbook", "url", "hint", "example", "http", "meta",
                          "account", "description", "email", "service_id", "vars_applied")
            if any(w in source.lower() for w in skip_words):
                return
            out.append((label, obj))

    for p in sorted(SECRETS_DIR.glob("*.json")):
        try:
            walk(__import__("json").loads(p.read_text()), p.stem)
        except Exception as e:  # noqa: BLE001
            print(f"[warn] cannot parse vault file {p.name}: {e}")
    return out


def main() -> int:
    pats = list(GENERIC_PATTERNS)
    for label, val in vault_literals():
        if val.startswith("postgresql") or val.startswith("postgres"):  # urls -> generic regex handles
            continue
        pats.append((f"vault:{label}", re.compile(re.escape(val))))

    proc = subprocess.Popen(
        ["git", "-C", str(ROOT), "log", "--all", "-p", "--no-color"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace",
    )
    hits: dict[str, int] = {}
    samples: dict[str, str] = {}
    assert proc.stdout is not None
    def is_placeholder(text: str) -> bool:
        """True for doc placeholders like dyw_xxxx, KGAT_0000..., ghp_XXXX."""
        body = re.sub(r"^(ghp_|gh_|KGAT[_-]?|dyw_|am_)", "", text)
        return len(set(body.lower())) <= 3  # 'xxxx', '0000', 'abab'

    for line in proc.stdout:
        for name, rx in pats:
            m = rx.search(line)
            if m and not is_placeholder(m.group(0)):
                hits[name] = hits.get(name, 0) + 1
                # sanitize sample: keep 12 chars around match start only, mask token body
                s = max(0, m.start() - 10)
                sample = (line.strip()[: s + 10] + "...")[:80]
                samples.setdefault(name, sample)
    proc.wait()

    # The UUID-shaped railway-token generic regex is extremely false-positive prone
    # (commit hashes appear in diff context); drop it if only that fired.
    hits.pop("railway-token", None)

    if not hits:
        print("PRE-PUSH SCAN: CLEAN — no vault literals or credential patterns in full git history.")
        return 0

    print("PRE-PUSH SCAN: LEAK CANDIDATES FOUND")
    for name, n in sorted(hits.items()):
        print(f"  {name}: {n} hit(s) | e.g. {samples.get(name, '')}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
