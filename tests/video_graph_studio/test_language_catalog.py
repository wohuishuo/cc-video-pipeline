from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "apps" / "video-graph-studio"
TRANSLATION = ROOT / "apps" / "translation"
CREATOR_BATCH = ROOT / "apps" / "creator-batch"
for app in (STUDIO, TRANSLATION, CREATOR_BATCH):
    sys.path.insert(0, str(app))

from creator_batch.contracts import SUPPORTED_LANGUAGES
from studio.api import StudioApplication
from studio.engine import WorkflowEngine
from studio.store import RunStore
from translation_app.adapters import TARGET_CODES
from translation_app.contracts import normalize_target_languages


EXPECTED = {
    "ru-RU": "rus_Cyrl",
    "en-US": "eng_Latn",
    "kk-KZ": "kaz_Cyrl",
    "zh-CN": "zho_Hans",
    "es-ES": "spa_Latn",
    "fr-FR": "fra_Latn",
    "de-DE": "deu_Latn",
    "it-IT": "ita_Latn",
    "pt-BR": "por_Latn",
    "ja-JP": "jpn_Jpan",
    "ko-KR": "kor_Hang",
    "ar-SA": "arb_Arab",
    "hi-IN": "hin_Deva",
    "tr-TR": "tur_Latn",
    "uk-UA": "ukr_Cyrl",
    "pl-PL": "pol_Latn",
    "nl-NL": "nld_Latn",
    "id-ID": "ind_Latn",
    "vi-VN": "vie_Latn",
    "th-TH": "tha_Thai",
}


def test_all_locales_normalize_and_match_translation_and_batch_contracts():
    assert normalize_target_languages(EXPECTED) == tuple(EXPECTED)
    assert TARGET_CODES == EXPECTED
    assert tuple(SUPPORTED_LANGUAGES) == tuple(EXPECTED)


def test_language_api_exposes_searchable_rows_with_voice_defaults(tmp_path):
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("GET", "/api/v1/languages", {}, None)

    assert status == 200
    assert response["contractVersion"] == "1.0"
    assert len(response["languages"]) == 20
    assert {row["locale"]: row["nllbCode"] for row in response["languages"]} == EXPECTED
    assert all(row["name"] and row["defaultVoice"] for row in response["languages"])


def test_translation_provider_api_reports_local_and_deepseek_readiness(tmp_path, monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    store = RunStore(tmp_path / "studio.db")
    app = StudioApplication(store, WorkflowEngine(store, {}), allowed_roots=(tmp_path,))

    status, response = app.handle("GET", "/api/v1/translation-providers", {}, None)

    assert status == 200
    assert response["providers"] == [
        {"id": "nllb", "name": "NLLB (local)", "ready": True, "defaultModel": "facebook/nllb-200-distilled-600M"},
        {"id": "deepseek", "name": "DeepSeek (cloud)", "ready": False, "defaultModel": "deepseek-v4-flash", "setupAvailable": False},
    ]
