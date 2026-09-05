"""PATI control plane configuration.

Windows-first paths (per owner decision): %USERPROFILE%\\PATI\\data
All settings are env-overridable. FREE_ONLY policy is enforced here and surfaced
through /system/status. Cost of every dependency used by PATI is $0.
"""
from __future__ import annotations

import os
import pathlib

VERSION = "1.0.0"
API_PREFIX = "/api/v1"
API_VERSION_TAG = "v1"


def default_data_dir() -> pathlib.Path:
    home = pathlib.Path.home()
    if os.name == "nt":
        return home / "PATI" / "data"
    return home / ".pati" / "data"


DATA_DIR = pathlib.Path(os.environ.get("PATI_DATA_DIR", str(default_data_dir())))
DB_PATH = DATA_DIR / "pati.db"
ARTIFACT_DIR = DATA_DIR / "artifacts"
LOG_DIR = DATA_DIR / "logs"
BOOTSTRAP_TOKEN_FILE = DATA_DIR / "bootstrap_admin_token.txt"
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent  # pati_api/ (holds static/)

# ---- Absolute $0 policy (hard architectural requirement) ----
POLICY = {
    "FREE_ONLY": True,
    "PAID_SERVICES": False,
    "PAID_APIS": False,
    "PAID_MODELS": False,
    "PAID_COMPUTE": False,
    "PAID_HOSTING": False,
    "PAID_STORAGE": False,
    "PAID_DATABASES": False,
    "PAID_FALLBACKS": False,
    "AUTO_BILLING": False,
    "CREDIT_CARD_REQUIRED": False,
    "MAX_SPEND": 0,
    "MAX_AUTOMATIC_SPEND": 0,
}

# ---- Operational limits (all zero-cost, local machine friendly) ----
RATE_LIMIT_PER_MIN = int(os.environ.get("PATI_RATE_LIMIT_PER_MIN", "240"))
MAX_UPLOAD_MB = int(os.environ.get("PATI_MAX_UPLOAD_MB", "200"))
STAGE_DEADLINE_S = int(os.environ.get("PATI_STAGE_DEADLINE_S", "1800"))
LONGPOLL_MAX_S = int(os.environ.get("PATI_LONGPOLL_MAX_S", "30"))
MAX_STAGE_RETRIES = int(os.environ.get("PATI_MAX_STAGE_RETRIES", "2"))
WORKER_OFFLINE_AFTER_S = int(os.environ.get("PATI_WORKER_OFFLINE_AFTER_S", "60"))
HEARTBEAT_INTERVAL_S = int(os.environ.get("PATI_HEARTBEAT_INTERVAL_S", "15"))
CIRCUIT_BREAKER_FAILURES = int(os.environ.get("PATI_CIRCUIT_FAILURES", "3"))
DEFAULT_TENANT = "tenant_local"

# Quota manager defaults (safety margins inside Kaggle's ~30 GPU-h/week free quota)
QUOTA_DEFAULTS = {
    "max_concurrent_tasks": 4,
    "max_tasks_per_day": 200,
    "max_artifact_mb_total": 2048,
    "gpu_minutes_per_day": 240,      # conservative daily GPU budget on free tier
    "api_requests_per_min": RATE_LIMIT_PER_MIN,
}

DEFAULT_ADMIN_USER = "owner"


def ensure_dirs() -> None:
    for p in (DATA_DIR, ARTIFACT_DIR, LOG_DIR):
        p.mkdir(parents=True, exist_ok=True)
