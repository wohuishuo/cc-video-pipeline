"""Production translation adapters."""

from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .contracts import TranslationError


SOURCE_CODES = {
    "zh": "zho_Hans", "zh-cn": "zho_Hans", "zho": "zho_Hans", "zho_hans": "zho_Hans",
    "en": "eng_Latn", "en-us": "eng_Latn", "eng": "eng_Latn", "eng_latn": "eng_Latn",
    "ru": "rus_Cyrl", "ru-ru": "rus_Cyrl", "rus": "rus_Cyrl", "rus_cyrl": "rus_Cyrl",
    "kk": "kaz_Cyrl", "kk-kz": "kaz_Cyrl", "kaz": "kaz_Cyrl", "kaz_cyrl": "kaz_Cyrl",
    "es": "spa_Latn", "es-es": "spa_Latn", "spa": "spa_Latn", "spa_latn": "spa_Latn",
    "fr": "fra_Latn", "fr-fr": "fra_Latn", "fra": "fra_Latn", "fra_latn": "fra_Latn",
    "de": "deu_Latn", "de-de": "deu_Latn", "deu": "deu_Latn", "deu_latn": "deu_Latn",
    "it": "ita_Latn", "it-it": "ita_Latn", "ita": "ita_Latn", "ita_latn": "ita_Latn",
    "pt": "por_Latn", "pt-br": "por_Latn", "por": "por_Latn", "por_latn": "por_Latn",
    "ja": "jpn_Jpan", "ja-jp": "jpn_Jpan", "jpn": "jpn_Jpan", "jpn_jpan": "jpn_Jpan",
    "ko": "kor_Hang", "ko-kr": "kor_Hang", "kor": "kor_Hang", "kor_hang": "kor_Hang",
    "ar": "arb_Arab", "ar-sa": "arb_Arab", "arb": "arb_Arab", "arb_arab": "arb_Arab",
    "hi": "hin_Deva", "hi-in": "hin_Deva", "hin": "hin_Deva", "hin_deva": "hin_Deva",
    "tr": "tur_Latn", "tr-tr": "tur_Latn", "tur": "tur_Latn", "tur_latn": "tur_Latn",
    "uk": "ukr_Cyrl", "uk-ua": "ukr_Cyrl", "ukr": "ukr_Cyrl", "ukr_cyrl": "ukr_Cyrl",
    "pl": "pol_Latn", "pl-pl": "pol_Latn", "pol": "pol_Latn", "pol_latn": "pol_Latn",
    "nl": "nld_Latn", "nl-nl": "nld_Latn", "nld": "nld_Latn", "nld_latn": "nld_Latn",
    "id": "ind_Latn", "id-id": "ind_Latn", "ind": "ind_Latn", "ind_latn": "ind_Latn",
    "vi": "vie_Latn", "vi-vn": "vie_Latn", "vie": "vie_Latn", "vie_latn": "vie_Latn",
    "th": "tha_Thai", "th-th": "tha_Thai", "tha": "tha_Thai", "tha_thai": "tha_Thai",
}

TARGET_CODES = {
    "ru-RU": "rus_Cyrl", "en-US": "eng_Latn", "kk-KZ": "kaz_Cyrl", "zh-CN": "zho_Hans",
    "es-ES": "spa_Latn", "fr-FR": "fra_Latn", "de-DE": "deu_Latn", "it-IT": "ita_Latn",
    "pt-BR": "por_Latn", "ja-JP": "jpn_Jpan", "ko-KR": "kor_Hang", "ar-SA": "arb_Arab",
    "hi-IN": "hin_Deva", "tr-TR": "tur_Latn", "uk-UA": "ukr_Cyrl", "pl-PL": "pol_Latn",
    "nl-NL": "nld_Latn", "id-ID": "ind_Latn", "vi-VN": "vie_Latn", "th-TH": "tha_Thai",
}


class DeepSeekAdapter:
    """DeepSeek Chat Completions adapter with exact segment coverage."""

    endpoint = "https://api.deepseek.com/chat/completions"

    def __init__(
        self,
        api_key: str,
        *,
        model: str = "deepseek-v4-flash",
        timeout_seconds: float = 90,
        maximum_attempts: int = 3,
        requester: Callable[[str, dict[str, str], dict[str, Any], float], dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise TranslationError("CREDENTIAL_REQUIRED", "DEEPSEEK_API_KEY is required for DeepSeek translation")
        if not isinstance(model, str) or not model.strip() or timeout_seconds <= 0 or maximum_attempts < 1:
            raise TranslationError("INVALID_ADAPTER", "DeepSeek model, timeout or retry policy is invalid")
        self._api_key = api_key.strip()
        self.model_id = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.maximum_attempts = int(maximum_attempts)
        self.requester = requester or self._request_json
        self.sleep = sleep

    @property
    def identity(self) -> str:
        return f"deepseek@1:model={self.model_id}:attempts={self.maximum_attempts}"

    def translate(self, texts, source_language, target_language, on_log):
        if not texts:
            return ()
        payload = {
            "model": self.model_id,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a professional audiovisual subtitle translator. Translate every input segment "
                        "faithfully and naturally, preserve names, tone, meaning and segment order. Return JSON "
                        "only in this exact shape: {\"translations\":[\"...\"]}. The array must contain exactly "
                        "one non-empty string for every input segment. Do not add explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "sourceLanguage": str(source_language),
                            "targetLanguage": str(target_language),
                            "segments": [
                                {"id": index, "text": text}
                                for index, text in enumerate(texts, 1)
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        last_error: Exception | None = None
        for attempt in range(1, self.maximum_attempts + 1):
            try:
                response = self.requester(self.endpoint, headers, payload, self.timeout_seconds)
                content = response["choices"][0]["message"]["content"]
                document = json.loads(content)
                translations = document.get("translations")
                if (
                    not isinstance(translations, list)
                    or len(translations) != len(texts)
                    or any(not isinstance(value, str) or not value.strip() for value in translations)
                ):
                    raise TranslationError(
                        "INVALID_ADAPTER_OUTPUT",
                        "DeepSeek must return exactly one translation for every source segment",
                    )
                on_log(f"DeepSeek translated {len(texts)} segment(s) to {target_language}")
                return tuple(value.strip() for value in translations)
            except HTTPError as error:
                if error.code in {401, 403}:
                    raise TranslationError("CREDENTIAL_REJECTED", "DeepSeek rejected the configured API credential") from error
                last_error = error
            except (KeyError, IndexError, TypeError, json.JSONDecodeError, URLError, OSError, TranslationError) as error:
                last_error = error
            if attempt < self.maximum_attempts:
                on_log(f"DeepSeek response attempt {attempt} failed; retrying")
                self.sleep(min(2 ** (attempt - 1), 4))
        if isinstance(last_error, TranslationError):
            raise last_error
        raise TranslationError("ADAPTER_UNAVAILABLE", f"DeepSeek translation failed after {self.maximum_attempts} attempts") from last_error

    @staticmethod
    def _request_json(
        url: str, headers: dict[str, str], payload: dict[str, Any], timeout: float
    ) -> dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict):
            raise TranslationError("INVALID_ADAPTER_OUTPUT", "DeepSeek returned a non-object response")
        return value


class NllbAdapter:
    def __init__(
        self,
        model: str = "facebook/nllb-200-distilled-600M",
        *,
        device: str = "auto",
        batch_size: int = 8,
        runtime_factory: Callable[[str, str, str], tuple[Any, Any]] | None = None,
    ) -> None:
        if device not in {"auto", "cpu", "cuda"} or batch_size <= 0:
            raise TranslationError("INVALID_ADAPTER", "device or batch size is invalid")
        self.model_id = model
        self.requested_device = device
        self.batch_size = batch_size
        self.runtime_factory = runtime_factory or self._load_runtime
        self._runtime_by_source: dict[str, tuple[Any, Any]] = {}
        self._resolved_device: str | None = None

    @property
    def identity(self) -> str:
        return f"nllb@1:model={self.model_id}:device={self.requested_device}:batch={self.batch_size}"

    def translate(self, texts, source_language, target_language, on_log):
        source_code = SOURCE_CODES.get(str(source_language).strip().lower())
        target_code = TARGET_CODES.get(target_language)
        if source_code is None:
            raise TranslationError("UNSUPPORTED_SOURCE_LANGUAGE", f"unsupported source language: {source_language}")
        if target_code is None:
            raise TranslationError("UNSUPPORTED_LANGUAGE", f"unsupported target language: {target_language}")
        device = self._device()
        if source_code not in self._runtime_by_source:
            on_log(f"Loading NLLB model for {source_code} on {device}")
            self._runtime_by_source[source_code] = self.runtime_factory(self.model_id, source_code, device)
        tokenizer, model = self._runtime_by_source[source_code]
        translated: list[str] = []
        forced_id = tokenizer.convert_tokens_to_ids(target_code)
        for offset in range(0, len(texts), self.batch_size):
            batch = tuple(texts[offset : offset + self.batch_size])
            encoded = tokenizer(batch, return_tensors="pt", padding=True, truncation=True, max_length=512).to(device)
            output = self._generate(model, encoded, forced_id)
            translated.extend(tokenizer.batch_decode(output, skip_special_tokens=True))
            on_log(f"Translated {min(offset + len(batch), len(texts))}/{len(texts)} segments to {target_language}")
        return tuple(text.strip() for text in translated)

    @staticmethod
    def _generate(model, encoded, forced_id):
        try:
            import torch
        except ImportError:
            return model.generate(**encoded, forced_bos_token_id=forced_id, max_new_tokens=256, num_beams=4)
        with torch.inference_mode():
            return model.generate(**encoded, forced_bos_token_id=forced_id, max_new_tokens=256, num_beams=4)

    def _device(self) -> str:
        if self._resolved_device is None:
            if self.requested_device != "auto":
                self._resolved_device = self.requested_device
            else:
                try:
                    import torch
                    self._resolved_device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    self._resolved_device = "cpu"
        return self._resolved_device

    @staticmethod
    def _load_runtime(model_id: str, source_code: str, device: str):
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise TranslationError("ADAPTER_UNAVAILABLE", "install transformers, torch and sentencepiece") from error
        tokenizer = AutoTokenizer.from_pretrained(model_id, src_lang=source_code)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id).to(device)
        model.eval()
        return tokenizer, model
