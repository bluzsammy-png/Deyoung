"""Kaggle worker credential detection (both official token styles).

Covers the 2026-09 setup flow where Kaggle hands out new-style KGAT_*
tokens (env var or ~/.kaggle/access_token) in addition to the classic
kaggle.json. Secrets themselves are never asserted, only presence/style.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
kw = importlib.import_module("pati_workers.kaggle_worker")


@pytest.fixture()
def isolated_home(tmp_path, monkeypatch):
    """Point Path.home() at a temp dir and clear token env vars."""
    monkeypatch.setattr(kw.Path, "home", staticmethod(lambda: tmp_path))
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    monkeypatch.delenv("KAGGLE_USERNAME", raising=False)
    return tmp_path


def test_no_credentials_reports_reason(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    creds = kw.kaggle_credentials()
    assert creds["ok"] is False
    assert "no Kaggle token" in creds["reason"]
    assert kw.kaggle_available() is False
    w = kw.KaggleWorker()
    reg = w.register()
    assert reg["status"] == "unavailable"
    assert "access_token" in reg["remedy"]


def test_no_cli_reports_reason(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: None)
    creds = kw.kaggle_credentials()
    assert creds["ok"] is False
    assert "CLI" in creds["reason"]


def test_env_var_token_detected(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_test_dummy_not_real")
    creds = kw.kaggle_credentials()
    assert creds["ok"] is True
    assert creds["style"] == "access_token"
    assert creds["source"] == "env"
    # cli_env must forward the token to subprocesses
    assert kw.cli_env()["KAGGLE_API_TOKEN"] == "KGAT_test_dummy_not_real"
    assert kw.kaggle_available() is True


def test_access_token_file_detected(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    kdir = isolated_home / ".kaggle"
    kdir.mkdir()
    (kdir / "access_token").write_text("KGAT_file_dummy_not_real\n", encoding="utf-8")
    creds = kw.kaggle_credentials()
    assert creds["ok"] is True
    assert creds["style"] == "access_token"
    assert "access_token" in creds["source"]
    assert kw.cli_env()["KAGGLE_API_TOKEN"] == "KGAT_file_dummy_not_real"


def test_classic_kaggle_json_detected(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    kdir = isolated_home / ".kaggle"
    kdir.mkdir()
    (kdir / "kaggle.json").write_text(json.dumps({"username": "tester", "key": "dummy"}))
    creds = kw.kaggle_credentials()
    assert creds["ok"] is True
    assert creds["style"] == "kaggle.json"
    # username resolves locally without any subprocess call
    kw.KaggleWorker._username_cache = None
    assert kw.KaggleWorker._kaggle_user() == "tester"


def test_env_var_precedence_over_file(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    kdir = isolated_home / ".kaggle"
    kdir.mkdir()
    (kdir / "access_token").write_text("KGAT_from_file", encoding="utf-8")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_from_env")
    creds = kw.kaggle_credentials()
    assert creds["source"] == "env"
    assert kw.cli_env()["KAGGLE_API_TOKEN"] == "KGAT_from_env"


def test_username_fallback_without_kaggle_json(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    monkeypatch.setenv("KAGGLE_USERNAME", "envuser")
    kw.KaggleWorker._username_cache = None
    assert kw.KaggleWorker._kaggle_user() == "envuser"
    kw.KaggleWorker._username_cache = None
    monkeypatch.delenv("KAGGLE_USERNAME")
    monkeypatch.setattr(kw.subprocess, "run",
                        lambda *a, **k: type("P", (), {"stdout": "", "stderr": ""})())
    assert kw.KaggleWorker._kaggle_user() == "pati-user"


def test_register_reports_style_when_available(isolated_home, monkeypatch):
    monkeypatch.setattr(kw.shutil, "which", lambda _: "/usr/bin/kaggle")
    kdir = isolated_home / ".kaggle"
    kdir.mkdir()
    (kdir / "access_token").write_text("KGAT_ok", encoding="utf-8")
    reg = kw.KaggleWorker().register()
    assert reg["status"] == "available"
    assert reg["credential_style"] == "access_token"
