"""Connector catalog: everything declared, planned items marked honestly.

Kaggle is intentionally NOT a connector: it is a compute worker (see
pati_workers/kaggle_worker.py). Colab would be the same if ever supported.
"""
from .base import ConnectorSpec

PLANNED = [
    ConnectorSpec(
        name="browser", version="0.0.0",
        description="Local browser automation (Playwright, free) - planned",
        capabilities=["browser_automation", "browser_testing"],
        auth="none", scopes=["profile: none - never touch stored passwords/cookies"],
        rate_limits="local", security=["isolated profile", "no credential store access"],
        free_status="FREE_FOREVER", license="Apache-2.0 (playwright)",
        supported_operations=["navigate", "extract", "screenshot"],
        default_status="planned"),
    ConnectorSpec(
        name="email", version="0.0.0",
        description="IMAP/SMTP with app passwords - planned",
        capabilities=["API_operations"], auth="app_password",
        scopes=["mailbox: selected folders"], rate_limits="provider",
        security=["app password only", "never the account password"],
        free_status="FREE_FOREVER", license="n/a",
        supported_operations=["list", "read", "send"], default_status="planned"),
    ConnectorSpec(
        name="calendar", version="0.0.0",
        description="Google Calendar read/write - planned",
        capabilities=["API_operations"], auth="oauth2",
        scopes=["calendar.events"], rate_limits="google",
        security=["revocable OAuth", "least privilege"],
        free_status="FREE_WITH_LIMITS", license="Google APIs ToS",
        supported_operations=["list_events", "create_event"], default_status="planned"),
    ConnectorSpec(
        name="cloud_storage", version="0.0.0",
        description="rclone-backed free storage targets - planned",
        capabilities=["artifact_storage"], auth="varies",
        scopes=["chosen remotes only"], rate_limits="provider",
        security=["config file 0600"], free_status="FREE_WITH_LIMITS",
        license="MIT (rclone)", supported_operations=["put", "get", "list"],
        default_status="planned"),
]

INSTALLED = []


def catalog() -> list[dict]:
    from .github_connector import GitHubConnector
    from .gdrive_connector import DriveConnector
    specs = [GitHubConnector.spec, DriveConnector.spec] + PLANNED
    return [s.declare() for s in specs]


def adapter_for(name: str):
    from .github_connector import GitHubConnector
    from .gdrive_connector import DriveConnector
    adapters = {"github": GitHubConnector, "gdrive": DriveConnector}
    return adapters.get(name)
