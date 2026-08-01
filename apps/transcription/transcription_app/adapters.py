"""Replaceable ASR adapters."""

from __future__ import annotations

from typing import Any, Callable

from .contracts import Segment, SourceMedia, TranscriptionError
from .operation import AdapterTranscript


class FasterWhisperAdapter:
    def __init__(
        self,
        model: str = "small",
        *,
        device: str = "auto",
        compute_type: str = "default",
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self._model_factory = model_factory
        self._model: Any | None = None
        self.identity = (
            f"faster-whisper@1:model={model}:device={device}:compute={compute_type}"
        )

    def _load(self) -> Any:
        if self._model is None:
            factory = self._model_factory
            if factory is None:
                try:
                    from faster_whisper import WhisperModel
                except ImportError as error:
                    raise TranscriptionError(
                        "ADAPTER_UNAVAILABLE", "faster-whisper is not installed"
                    ) from error
                factory = WhisperModel
            self._model = factory(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self, media: SourceMedia, language: str, on_log: Callable[[str], None]
    ) -> AdapterTranscript:
        on_log(f"Loading {self.identity}")
        rows, info = self._load().transcribe(
            media.path,
            language=None if language == "auto" else language,
            vad_filter=True,
            word_timestamps=False,
            beam_size=5,
        )
        segments: list[Segment] = []
        for row in rows:
            text = str(row.text).strip()
            if not text or float(row.end) <= float(row.start):
                continue
            segments.append(
                Segment(len(segments) + 1, float(row.start), float(row.end), text)
            )
        if not segments:
            raise TranscriptionError("EMPTY_TRANSCRIPT", f"no speech detected in {media.id}")
        detected = str(getattr(info, "language", None) or language or "und")
        on_log(f"Detected {detected}; committed {len(segments)} segment(s)")
        return AdapterTranscript(detected, tuple(segments))

