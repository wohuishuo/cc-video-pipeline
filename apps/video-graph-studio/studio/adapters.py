"""Replaceable worker adapters used by the workflow engine."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Queue
import subprocess
import threading
from typing import Any, Callable

from .contracts import GraphNode


@dataclass(frozen=True)
class AdapterResult:
    completed: bool
    details: dict[str, Any]
    error: str | None = None


class CommandAdapter:
    """Runs one argv-only child process and streams its merged output."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self.active_processes = 0
        self.maximum_active_processes = 0

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        argv = node.config.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            return AdapterResult(False, {}, "command node requires a non-empty argv list")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        with self._lock:
            self._process = process
            self.active_processes += 1
            self.maximum_active_processes = max(self.maximum_active_processes, self.active_processes)

        output: Queue[str | None] = Queue()

        def read_output() -> None:
            assert process.stdout is not None
            for line in process.stdout:
                output.put(line.rstrip("\r\n"))
            output.put(None)

        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        closed = False
        try:
            while process.poll() is None or not closed:
                if cancel_event.is_set() and process.poll() is None:
                    self.stop()
                try:
                    item = output.get(timeout=0.05)
                    if item is None:
                        closed = True
                    elif item:
                        on_log(item)
                except Empty:
                    pass
            exit_code = process.wait()
            if cancel_event.is_set():
                return AdapterResult(False, {"exitCode": exit_code, "cancelled": True}, "cancelled")
            if exit_code != 0:
                return AdapterResult(False, {"exitCode": exit_code}, f"process exited {exit_code}")
            return AdapterResult(True, {"exitCode": exit_code})
        finally:
            reader.join(timeout=1)
            with self._lock:
                self.active_processes -= 1
                if self._process is process:
                    self._process = None

    def stop(self) -> None:
        with self._lock:
            process = self._process
        if process is not None and process.poll() is None:
            process.terminate()


class PreparedFolderAdapter:
    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        source = Path(str(context["parameters"].get("sourceRoot", ""))).resolve()
        manifest = source / "russian" / "batch-manifest.json"
        if not source.is_dir() or not manifest.is_file():
            return AdapterResult(False, {"sourceRoot": str(source)}, "localization manifest not found")
        on_log(f"Prepared localization manifest: {manifest}")
        return AdapterResult(True, {"manifest": str(manifest)})


class PreparedFolderEdgeAdapter(CommandAdapter):
    def __init__(self, launcher: Path):
        super().__init__()
        self.launcher = Path(launcher)

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        source = str(Path(str(context["parameters"]["sourceRoot"])).resolve())
        voice = str(context["parameters"].get("voice", "ru-RU-DmitryNeural"))
        command_node = GraphNode(
            node.id,
            "command",
            {
                "argv": [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(self.launcher),
                    "-SourceRoot",
                    source,
                    "-Voice",
                    voice,
                ]
            },
        )
        result = super().execute(command_node, context, on_log, cancel_event)
        if not result.completed:
            return result
        failures = Path(source) / "russian" / "edge-final" / "edge-failures.json"
        if not failures.is_file():
            return AdapterResult(False, result.details, "Edge failure receipt not found")
        import json

        failure_rows = json.loads(failures.read_text(encoding="utf-8")).get("failures", [])
        outputs = list((failures.parent).glob("*.mp4"))
        if failure_rows or not outputs:
            return AdapterResult(
                False,
                {**result.details, "failureCount": len(failure_rows), "outputCount": len(outputs)},
                "Edge localization did not produce verified outputs",
            )
        return AdapterResult(
            True,
            {**result.details, "failureReceipt": str(failures), "outputCount": len(outputs)},
        )


class VerifyOutputAdapter:
    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        output = Path(str(context["parameters"]["sourceRoot"])) / "russian" / "edge-final"
        videos = [path for path in output.glob("*.mp4") if path.stat().st_size > 0]
        if not videos:
            return AdapterResult(False, {"outputRoot": str(output)}, "no localized videos found")
        on_log(f"Verified {len(videos)} localized video(s)")
        return AdapterResult(True, {"outputRoot": str(output), "videoCount": len(videos)})


class SourceIntakeAdapter(CommandAdapter):
    """Invokes the independent Source Intake public launcher."""

    def __init__(self, launcher: Path, intake_root: Path):
        super().__init__()
        self.launcher = Path(launcher).resolve()
        self.intake_root = Path(intake_root).resolve()

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        parameters = context["parameters"]
        mode = str(parameters.get("sourceKind", ""))
        source = parameters.get("sourceRoot") if mode == "folder" else parameters.get("sourceUrl")
        if mode not in {"folder", "url"} or not isinstance(source, str):
            return AdapterResult(False, {}, "invalid Source Intake parameters")
        output = self.intake_root / str(context["runId"])
        child_operation_id = f"{context['runId']}:step:{node.id}"
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(self.launcher), mode, source, "--output-dir", str(output),
            "--operation-id", child_operation_id, "--json",
        ]
        if mode == "url":
            argv.extend(["--max-height", str(parameters.get("maxHeight", 1080))])
        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, on_log, cancel_event)
        receipt_path = output / "intake-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "intake receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            manifest = Path(str(receipt["manifest"])).resolve()
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid intake receipt: {error}")
        if receipt.get("resultClass") != "COMPLETED" or not manifest.is_file():
            return AdapterResult(False, result.details, "Source Intake did not commit a manifest")
        return AdapterResult(
            True,
            {
                **result.details,
                "receipt": str(receipt_path),
                "manifest": str(manifest),
                "manifestSha256": receipt.get("manifestSha256"),
                "mediaCount": receipt.get("mediaCount"),
            },
        )


class VerifySourceAdapter:
    """Verifies the committed Source Intake fact without owning the manifest."""

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        intake = next(
            (
                step.get("result")
                for step in context.get("steps", [])
                if step.get("nodeId") == "intake" and step.get("status") == "COMPLETED"
            ),
            None,
        )
        if not isinstance(intake, dict):
            return AdapterResult(False, {}, "committed intake fact missing")
        manifest_path = Path(str(intake.get("manifest", ""))).resolve()
        if not manifest_path.is_file():
            return AdapterResult(False, {}, "source manifest missing")
        digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
        if digest != intake.get("manifestSha256"):
            return AdapterResult(False, {}, "source manifest fingerprint conflict")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            media = manifest["media"]
            valid = bool(media) and all(
                Path(str(row["path"])).is_file()
                and Path(str(row["path"])).stat().st_size == int(row["size"])
                for row in media
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            media = []
        if not valid:
            return AdapterResult(False, {}, "source manifest media validation failed")
        on_log(f"Verified source manifest with {len(media)} media file(s)")
        return AdapterResult(True, {"manifest": str(manifest_path), "mediaCount": len(media)})


class TranscriptSourceAdapter(CommandAdapter):
    """Invokes the independent Transcription public launcher."""

    def __init__(self, launcher: Path, transcript_root: Path):
        super().__init__()
        self.launcher = Path(launcher).resolve()
        self.transcript_root = Path(transcript_root).resolve()

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        intake = next(
            (
                step.get("result")
                for step in context.get("steps", [])
                if step.get("nodeId") == "intake" and step.get("status") == "COMPLETED"
            ),
            None,
        )
        if not isinstance(intake, dict):
            return AdapterResult(False, {}, "committed source manifest missing")
        source_manifest = Path(str(intake.get("manifest", ""))).resolve()
        if not source_manifest.is_file():
            return AdapterResult(False, {}, "source manifest missing")
        parameters = context["parameters"]
        output = self.transcript_root / str(context["runId"])
        child_operation_id = f"{context['runId']}:step:{node.id}"
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(self.launcher), str(source_manifest), "--output-dir", str(output),
            "--operation-id", child_operation_id,
            "--language", str(parameters.get("sourceLanguage", "auto")),
            "--model", str(parameters.get("asrModel", "small")),
            "--device", str(parameters.get("asrDevice", "auto")),
            "--compute-type", str(parameters.get("asrComputeType", "default")),
            "--json",
        ]
        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, on_log, cancel_event)
        receipt_path = output / "transcription-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "transcription receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            manifest = Path(str(receipt["manifest"])).resolve()
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid transcription receipt: {error}")
        if receipt.get("resultClass") != "COMPLETED" or not manifest.is_file():
            return AdapterResult(False, result.details, "Transcription did not commit a manifest")
        return AdapterResult(
            True,
            {
                **result.details,
                "receipt": str(receipt_path),
                "manifest": str(manifest),
                "manifestSha256": receipt.get("manifestSha256"),
                "transcriptCount": len(receipt.get("items", [])),
            },
        )


class VerifyTranscriptAdapter:
    """Verifies transcript artifacts without taking Transcription ownership."""

    def execute(
        self,
        node: GraphNode,
        context: dict[str, Any],
        on_log: Callable[[str], None],
        cancel_event: threading.Event,
    ) -> AdapterResult:
        committed = next(
            (
                step.get("result")
                for step in context.get("steps", [])
                if step.get("nodeId") == "transcribe" and step.get("status") == "COMPLETED"
            ),
            None,
        )
        if not isinstance(committed, dict):
            return AdapterResult(False, {}, "committed transcript fact missing")
        manifest_path = Path(str(committed.get("manifest", ""))).resolve()
        if not manifest_path.is_file():
            return AdapterResult(False, {}, "transcript manifest missing")
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != committed.get("manifestSha256"):
            return AdapterResult(False, {}, "transcript manifest fingerprint conflict")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected = manifest["expectedMediaIds"]
            transcripts = manifest["transcripts"]
            valid = (
                manifest.get("schemaVersion") == 1
                and bool(expected)
                and [row["mediaId"] for row in transcripts] == expected
                and all(
                    Path(str(row["sourcePath"])).is_file()
                    and hashlib.sha256(Path(str(row["sourcePath"])).read_bytes()).hexdigest() == row["sourceSha256"]
                    and Path(str(row["transcriptPath"])).is_file()
                    and hashlib.sha256(Path(str(row["transcriptPath"])).read_bytes()).hexdigest() == row["transcriptSha256"]
                    and Path(str(row["srtPath"])).is_file()
                    and hashlib.sha256(Path(str(row["srtPath"])).read_bytes()).hexdigest() == row["srtSha256"]
                    and int(row["segmentCount"]) > 0
                    for row in transcripts
                )
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            transcripts = []
        if not valid:
            return AdapterResult(False, {}, "transcript artifact validation failed")
        on_log(f"Verified transcript manifest with {len(transcripts)} transcript(s)")
        return AdapterResult(True, {"manifest": str(manifest_path), "transcriptCount": len(transcripts)})
