from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_FIELDS = (
    "schema_version", "name", "summary", "entrypoint", "install", "test",
    "inputs", "outputs", "dependencies", "delivery_level",
)
DELIVERY_LEVELS = {"DESIGNED", "IMPLEMENTED", "DOMAIN_VERIFIED", "PLATFORM_INTEGRATED", "PRODUCTION_VERIFIED"}


def validate_repository(root: Path) -> list[str]:
    root = Path(root).resolve()
    errors: list[str] = []
    names: dict[str, Path] = {}
    for path in sorted((root / "apps").glob("*/mvp.json")):
        relative = path.relative_to(root).as_posix()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f"{relative}: invalid JSON: {error}")
            continue
        for field in REQUIRED_FIELDS:
            if field not in data:
                errors.append(f"{relative}: missing field '{field}'")
        name = data.get("name")
        if isinstance(name, str):
            if name in names:
                errors.append(f"{relative}: duplicate application name '{name}'")
            names[name] = path
        for field in ("entrypoint", "install"):
            value = data.get(field)
            if isinstance(value, str) and not (path.parent / value).is_file():
                errors.append(f"{relative}: {field} path does not exist: {value}")
        level = data.get("delivery_level")
        if level is not None and level not in DELIVERY_LEVELS:
            errors.append(f"{relative}: invalid delivery_level '{level}'")
    return errors


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:])[0]) if (argv or sys.argv[1:]) else Path.cwd()
    errors = validate_repository(root)
    if errors:
        print("\n".join(errors))
        return 1
    print("All MVP manifests are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
