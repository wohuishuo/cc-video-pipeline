"""Adapter that composes five independent MVP public launchers for one item."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import threading
from typing import Any, Callable

from .contracts import BatchPolicy, CreatorItem
from .operation import ItemProcessResult


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: str
    stderr: str


def _run(argv: list[str], on_log: Callable[[str], None]) -> ProcessResult:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    process = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=creationflags,
    )
    output: Queue[tuple[str, str] | None] = Queue()

    def read(stream, name):
        assert stream is not None
        for line in stream:
            output.put((name, line.rstrip("\r\n")))
        output.put(None)

    threads = [
        threading.Thread(target=read, args=(process.stdout, "stdout"), daemon=True),
        threading.Thread(target=read, args=(process.stderr, "stderr"), daemon=True),
    ]
    for thread in threads:
        thread.start()
    closed = 0
    stdout: list[str] = []
    stderr: list[str] = []
    while process.poll() is None or closed < len(threads):
        try:
            row = output.get(timeout=0.05)
        except Empty:
            continue
        if row is None:
            closed += 1
            continue
        name, line = row
        (stdout if name == "stdout" else stderr).append(line)
        if line:
            on_log(line)
    for thread in threads:
        thread.join(timeout=1)
    return ProcessResult(process.wait(), "\n".join(stdout), "\n".join(stderr))


class PublicMvpItemProcessor:
    def __init__(self, repository: Path, *, runner: Callable[[list[str], Callable[[str], None]], ProcessResult] = _run):
        self.repository = Path(repository).resolve()
        self.runner = runner

    def process(
        self,
        item: CreatorItem,
        item_root: Path,
        child_prefix: str,
        batch_policy: BatchPolicy,
        cookies: Path | None,
        on_log: Callable[[str], None],
    ) -> ItemProcessResult:
        root = Path(item_root).resolve()
        source = self._invoke(
            "Source Intake",
            self._base("source-intake")
            + [
                "url",
                item.url,
                "--output-dir",
                str(root / "intake"),
                "--operation-id",
                f"{child_prefix}:intake",
                "--json",
                "--max-height",
                str(batch_policy.max_height),
            ]
            + (["--cookies", str(Path(cookies).resolve())] if cookies is not None else []),
            on_log,
        )
        if isinstance(source, str):
            return ItemProcessResult(False, None, 0, source)

        transcript = self._invoke(
            "Transcription",
            self._base("transcription")
            + [
                str(source),
                "--output-dir",
                str(root / "transcription"),
                "--operation-id",
                f"{child_prefix}:transcription",
                "--language",
                batch_policy.source_language,
                "--model",
                batch_policy.asr_model,
                "--device",
                batch_policy.asr_device,
                "--compute-type",
                batch_policy.asr_compute_type,
                "--json",
            ],
            on_log,
        )
        if isinstance(transcript, str):
            return ItemProcessResult(False, None, 0, transcript)

        translation_argv = self._base("translation") + [
            str(transcript),
            "--output-dir",
            str(root / "translation"),
            "--operation-id",
            f"{child_prefix}:translation",
            "--provider",
            batch_policy.translation_provider,
            "--model",
            batch_policy.translation_model,
            "--device",
            batch_policy.translation_device,
            "--batch-size",
            str(batch_policy.translation_batch_size),
        ]
        for language in batch_policy.target_languages:
            translation_argv.extend(["--target-language", language])
        translation_argv.append("--json")
        translation = self._invoke("Translation", translation_argv, on_log)
        if isinstance(translation, str):
            return ItemProcessResult(False, None, 0, translation)

        voice_argv = self._base("voice-rendering") + [
            str(translation),
            "--output-dir",
            str(root / "voice"),
            "--operation-id",
            f"{child_prefix}:voice",
            "--provider",
            batch_policy.voice_provider,
        ]
        for language in batch_policy.target_languages:
            voice_argv.extend(["--voice", f"{language}={batch_policy.target_voices[language]}"])
        voice_argv.append("--json")
        voice = self._invoke("Voice Rendering", voice_argv, on_log)
        if isinstance(voice, str):
            return ItemProcessResult(False, None, 0, voice)

        localized = self._invoke(
            "Localization",
            self._base("localization")
            + [
                str(source),
                str(translation),
                str(voice),
                "--output-dir",
                str(root / "localized"),
                "--operation-id",
                f"{child_prefix}:localization",
                "--source-volume",
                str(batch_policy.source_volume),
                "--json",
            ],
            on_log,
        )
        if isinstance(localized, str):
            return ItemProcessResult(False, None, 0, localized)
        try:
            value = json.loads(localized.read_text(encoding="utf-8-sig"))
            derivatives = value["derivatives"]
            if not isinstance(derivatives, list) or not derivatives:
                raise ValueError
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            return ItemProcessResult(False, None, 0, "Localization Manifest did not contain derivatives")
        return ItemProcessResult(True, localized, len(derivatives))

    def _base(self, app: str) -> list[str]:
        return [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(self.repository / "apps" / app / "run.ps1"),
        ]

    def _invoke(self, owner: str, argv: list[str], on_log: Callable[[str], None]) -> Path | str:
        try:
            result = self.runner(argv, on_log)
        except OSError:
            return f"{owner} process could not be started"
        payload = self._last_json(result.stdout)
        if result.returncode != 0 or payload is None or payload.get("resultClass") not in {"COMPLETED", "DUPLICATE_COMPLETED"}:
            detail = payload.get("error") if isinstance(payload, dict) else None
            return str(detail or result.stderr[-4000:] or f"{owner} failed")
        manifest = Path(str(payload.get("manifest", ""))).resolve()
        if not manifest.is_file():
            return f"{owner} did not commit a readable manifest"
        return manifest

    @staticmethod
    def _last_json(text: str) -> dict[str, Any] | None:
        for line in reversed(text.splitlines()):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        return None
