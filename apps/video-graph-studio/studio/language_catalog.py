"""Studio projection of the currently verified localization language catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageDefinition:
    locale: str
    name: str
    nllb_code: str
    default_voice: str

    def to_public_dict(self) -> dict[str, str]:
        return {
            "locale": self.locale,
            "name": self.name,
            "nllbCode": self.nllb_code,
            "defaultVoice": self.default_voice,
        }


LANGUAGES = (
    LanguageDefinition("ru-RU", "Russian", "rus_Cyrl", "ru-RU-DmitryNeural"),
    LanguageDefinition("en-US", "English", "eng_Latn", "en-US-GuyNeural"),
    LanguageDefinition("kk-KZ", "Kazakh", "kaz_Cyrl", "kk-KZ-DauletNeural"),
    LanguageDefinition("zh-CN", "Chinese (Simplified)", "zho_Hans", "zh-CN-YunxiNeural"),
    LanguageDefinition("es-ES", "Spanish", "spa_Latn", "es-ES-AlvaroNeural"),
    LanguageDefinition("fr-FR", "French", "fra_Latn", "fr-FR-HenriNeural"),
    LanguageDefinition("de-DE", "German", "deu_Latn", "de-DE-ConradNeural"),
    LanguageDefinition("it-IT", "Italian", "ita_Latn", "it-IT-DiegoNeural"),
    LanguageDefinition("pt-BR", "Portuguese (Brazil)", "por_Latn", "pt-BR-AntonioNeural"),
    LanguageDefinition("ja-JP", "Japanese", "jpn_Jpan", "ja-JP-KeitaNeural"),
    LanguageDefinition("ko-KR", "Korean", "kor_Hang", "ko-KR-InJoonNeural"),
    LanguageDefinition("ar-SA", "Arabic", "arb_Arab", "ar-SA-HamedNeural"),
    LanguageDefinition("hi-IN", "Hindi", "hin_Deva", "hi-IN-MadhurNeural"),
    LanguageDefinition("tr-TR", "Turkish", "tur_Latn", "tr-TR-AhmetNeural"),
    LanguageDefinition("uk-UA", "Ukrainian", "ukr_Cyrl", "uk-UA-OstapNeural"),
    LanguageDefinition("pl-PL", "Polish", "pol_Latn", "pl-PL-MarekNeural"),
    LanguageDefinition("nl-NL", "Dutch", "nld_Latn", "nl-NL-MaartenNeural"),
    LanguageDefinition("id-ID", "Indonesian", "ind_Latn", "id-ID-ArdiNeural"),
    LanguageDefinition("vi-VN", "Vietnamese", "vie_Latn", "vi-VN-NamMinhNeural"),
    LanguageDefinition("th-TH", "Thai", "tha_Thai", "th-TH-NiwatNeural"),
)

SUPPORTED_LANGUAGE_LOCALES = tuple(row.locale for row in LANGUAGES)


def language_rows() -> list[dict[str, str]]:
    return [row.to_public_dict() for row in LANGUAGES]
