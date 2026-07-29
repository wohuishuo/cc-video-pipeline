import json
from pathlib import Path

from scripts.validate_mvp_manifests import validate_repository


REQUIRED = {
    "schema_version": 1,
    "name": "demo",
    "summary": "Demonstration application",
    "entrypoint": "run.ps1",
    "install": "install.ps1",
    "test": "python -m pytest tests -q",
    "inputs": ["input file"],
    "outputs": ["output file"],
    "dependencies": ["python>=3.12"],
    "delivery_level": "IMPLEMENTED",
}


def write_app(root: Path, name: str, manifest: dict) -> None:
    app = root / "apps" / name
    app.mkdir(parents=True)
    for filename in ("README.md", "run.ps1", "install.ps1"):
        (app / filename).write_text("# Demo\n", encoding="utf-8")
    (app / "mvp.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_reports_missing_required_manifest_fields(tmp_path):
    write_app(tmp_path, "demo", {"schema_version": 1, "name": "demo"})
    errors = validate_repository(tmp_path)
    assert "apps/demo/mvp.json: missing field 'entrypoint'" in errors
    assert "apps/demo/mvp.json: missing field 'delivery_level'" in errors


def test_accepts_complete_manifest_with_existing_paths(tmp_path):
    write_app(tmp_path, "demo", REQUIRED)
    assert validate_repository(tmp_path) == []


def test_rejects_duplicate_application_names(tmp_path):
    write_app(tmp_path, "one", REQUIRED)
    write_app(tmp_path, "two", REQUIRED)
    assert any("duplicate application name 'demo'" in error for error in validate_repository(tmp_path))
