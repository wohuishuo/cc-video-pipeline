"""Browser-safe voice provider capabilities without loading model weights."""

from __future__ import annotations

from pathlib import Path


QWEN3_LOCALES = (
    "ru-RU", "en-US", "zh-CN", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "ja-JP", "ko-KR"
)
QWEN3_VOICES = (
    ("Vivian", "Vivian"), ("Serena", "Serena"), ("Uncle_Fu", "Uncle Fu"),
    ("Dylan", "Dylan"), ("Eric", "Eric"), ("Ryan", "Ryan"), ("Aiden", "Aiden"),
    ("Ono_Anna", "Ono Anna"), ("Sohee", "Sohee"),
)


def _qwen_ready(repository: Path | None) -> bool:
    if repository is None:
        return False
    root = Path(repository).resolve()
    roots = [root]
    if root.parent.name == ".worktrees":
        roots.append(root.parent.parent)
    return any(
        (candidate / "tools" / "qwen3tts-env" / "Scripts" / "python.exe").is_file()
        and (candidate / "tools" / "qwen3tts-env" / "Lib" / "site-packages" / "qwen_tts").is_dir()
        for candidate in roots
    )


def voice_provider_rows(repository: Path | None) -> list[dict]:
    return [
        {
            "id": "edge", "name": "Edge TTS", "ready": True,
            "supportedLocales": None, "voices": [],
            "description": "Fast named neural voices; requires network access while rendering.",
        },
        {
            "id": "qwen3", "name": "Qwen3-TTS", "ready": _qwen_ready(repository),
            "supportedLocales": list(QWEN3_LOCALES),
            "voices": [{"id": identity, "name": name} for identity, name in QWEN3_VOICES],
            "description": "Local preset synthesis with one resident model per video.",
        },
        {
            "id": "original", "name": "Original audio + subtitles", "ready": True,
            "supportedLocales": None,
            "voices": [{"id": "original-audio", "name": "Original audio"}],
            "description": "Keep source speech and burn translated subtitles without synthetic narration.",
        },
    ]
