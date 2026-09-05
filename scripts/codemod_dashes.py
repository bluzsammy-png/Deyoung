#!/usr/bin/env python3
"""Codemod: remove em/en dashes from src/** (site copy rule: no em dashes).

- " — " / " – " -> " - "   (sentence/title gaps keep a hyphen with spaces)
- "—" / "–"      -> "-"    (glued forms, comments, ranges)
Idempotent. Prints a per-file replacement count.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path("/home/z/my-project/src")
total = 0
files = 0
for path in sorted(ROOT.rglob("*")):
    if path.suffix not in {".ts", ".tsx", ".css", ".json", ".mjs"}:
        continue
    text = path.read_text()
    before = text
    text = text.replace(" \u2014 ", " - ").replace(" \u2013 ", " - ")
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    if text != before:
        n = sum(1 for a, b in zip(before, text) if a != b)
        count = before.count("\u2014") + before.count("\u2013")
        print(f"{path.relative_to(ROOT)}: {count} dash(es)")
        path.write_text(text)
        total += count
        files += 1
print(f"TOTAL: {total} dash(es) in {files} file(s)")
if total == 0:
    print("clean already")
