#!/usr/bin/env python3
"""Resolve the Kaggle username for each KGAT token (uses the CLI's own introspection)."""
import json
import os
import pathlib

from kaggle.api.kaggle_api_extended import KaggleApi


def main():
    tokens = [t.strip() for t in (os.environ.get("KAGGLE_TOKENS", "")).split(",") if t.strip()]
    api = KaggleApi()
    api.authenticate()  # no-op when no classic creds; we only need build_kaggle_client
    out = []
    for tok in tokens:
        try:
            username = api._introspect_token(tok)
            status = "OK" if username else "INACTIVE"
            print(f"{status} {tok[:12]}... -> username: {username}")
            out.append({"token": tok, "username": username})
        except Exception as exc:
            print(f"FAIL {tok[:12]}... -> {exc.__class__.__name__}: {str(exc)[:150]}")
            out.append({"token": tok, "username": None, "error": str(exc)[:200]})
    pathlib.Path(__file__).parent.joinpath("kaggle_accounts.json").write_text(json.dumps(out, indent=2))
    print("saved -> scripts/kaggle_accounts.json")


if __name__ == "__main__":
    main()
