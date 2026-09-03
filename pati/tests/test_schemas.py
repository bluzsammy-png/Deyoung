"""Schema validation: catalogs validate against schemas/*.schema.json."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def test_all_schema_files_valid_json():
    files = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert len(files) >= 15
    for f in files:
        data = json.loads(f.read_text())
        assert data["$schema"].startswith("https://json-schema.org")


def test_free_only_hardcoded_in_model_and_health_schemas():
    model = json.loads((SCHEMA_DIR / "model.schema.json").read_text())
    assert model["properties"]["cost"]["maximum"] == 0
    health = json.loads((SCHEMA_DIR / "health.schema.json").read_text())
    assert health["properties"]["max_spend"]["const"] == 0


@pytest.mark.skipif(importlib.util.find_spec("jsonschema") is None,
                    reason="jsonschema not installed")
def test_registry_entries_validate_against_schemas(server, admin):
    import jsonschema
    model_schema = json.loads((SCHEMA_DIR / "model.schema.json").read_text())
    for m in admin.list_models():
        jsonschema.validate(m, model_schema)
    tool_schema = json.loads((SCHEMA_DIR / "tool.schema.json").read_text())
    for t in admin.list_tools():
        jsonschema.validate(t, tool_schema)
    cap_schema = json.loads((SCHEMA_DIR / "capability.schema.json").read_text())
    for c in admin.get_capabilities()[:30]:
        jsonschema.validate(c, cap_schema)
