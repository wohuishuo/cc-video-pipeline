from pathlib import Path
import sys


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.store import RunStore
from studio.voice_provider_catalog import voice_provider_rows


def test_voice_provider_catalog_is_explicit_and_does_not_load_qwen_models(tmp_path):
    qwen = tmp_path / "tools" / "qwen3tts-env"
    (qwen / "Scripts").mkdir(parents=True)
    (qwen / "Scripts" / "python.exe").write_bytes(b"runtime")
    (qwen / "Lib" / "site-packages" / "qwen_tts").mkdir(parents=True)

    rows = voice_provider_rows(tmp_path)

    assert [row["id"] for row in rows] == ["edge", "qwen3", "original"]
    assert rows[0]["ready"] is True
    assert rows[1]["ready"] is True
    assert rows[1]["supportedLocales"] == [
        "ru-RU", "en-US", "zh-CN", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "ja-JP", "ko-KR"
    ]
    assert [voice["id"] for voice in rows[1]["voices"]] == [
        "Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden", "Ono_Anna", "Sohee"
    ]
    assert rows[2]["voices"] == [{"id": "original-audio", "name": "Original audio"}]


def test_api_exposes_voice_providers_without_accepting_credentials(tmp_path):
    app = StudioApplication(
        RunStore(tmp_path / "studio.db"), WorkflowEngine(RunStore(tmp_path / "other.db"), {}),
        allowed_roots=(tmp_path,), repository=tmp_path,
    )

    status, response = app.handle("GET", "/api/v1/voice-providers", {}, None)

    assert status == 200
    assert response["contractVersion"] == "1.0"
    assert [row["id"] for row in response["providers"]] == ["edge", "qwen3", "original"]
