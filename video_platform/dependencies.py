from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dependency:
    url: str
    revision: str
    license: str
    checkout: Path


@dataclass(frozen=True)
class DependencyManifest:
    dependencies: dict[str, Dependency]

    @classmethod
    def load(cls, path: Path) -> "DependencyManifest":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        dependencies = {
            name: Dependency(
                url=value["url"],
                revision=value["revision"],
                license=value["license"],
                checkout=Path(value["checkout"]),
            )
            for name, value in payload["dependencies"].items()
        }
        return cls(dependencies)


def resolve_uploader_checkout(project_root: Path) -> Path:
    manifest = DependencyManifest.load(project_root / "vendor" / "video-uploaders.lock.json")
    return (project_root / manifest.dependencies["social-auto-upload"].checkout).resolve()


def ensure_runtime_config(checkout: Path) -> Path:
    checkout = Path(checkout)
    target = checkout / "conf.py"
    if target.exists():
        return target
    example = checkout / "conf.example.py"
    if not example.is_file():
        raise FileNotFoundError(f"Missing upstream configuration example: {example}")
    target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return target
