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


class TranslateTranscriptAdapter(CommandAdapter):
    """Invokes the independent Translation public launcher."""

    def __init__(self, launcher: Path, translation_root: Path):
        super().__init__()
        self.launcher = Path(launcher).resolve()
        self.translation_root = Path(translation_root).resolve()

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
            return AdapterResult(False, {}, "committed transcript manifest missing")
        transcript_manifest = Path(str(committed.get("manifest", ""))).resolve()
        if not transcript_manifest.is_file():
            return AdapterResult(False, {}, "transcript manifest missing")
        parameters = context["parameters"]
        output = self.translation_root / str(context["runId"])
        child_operation_id = f"{context['runId']}:step:{node.id}"
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(self.launcher), str(transcript_manifest), "--output-dir", str(output),
            "--operation-id", child_operation_id,
            "--model", str(parameters.get("translationModel", "facebook/nllb-200-distilled-600M")),
            "--device", str(parameters.get("translationDevice", "auto")),
            "--batch-size", str(parameters.get("translationBatchSize", 8)),
        ]
        for language in parameters.get("targetLanguages", []):
            argv.extend(["--target-language", str(language)])
        argv.append("--json")
        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, on_log, cancel_event)
        receipt_path = output / "translation-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "translation receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            manifest = Path(str(receipt["manifest"])).resolve()
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid translation receipt: {error}")
        if receipt.get("resultClass") != "COMPLETED" or not manifest.is_file():
            return AdapterResult(False, result.details, "Translation did not commit a manifest")
        return AdapterResult(
            True,
            {
                **result.details,
                "receipt": str(receipt_path),
                "manifest": str(manifest),
                "manifestSha256": receipt.get("manifestSha256"),
                "translationCount": len(receipt.get("items", [])),
            },
        )


class VerifyTranslationAdapter:
    """Verifies translated artifacts without taking Translation ownership."""

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
                if step.get("nodeId") == "translate" and step.get("status") == "COMPLETED"
            ),
            None,
        )
        if not isinstance(committed, dict):
            return AdapterResult(False, {}, "committed translation fact missing")
        manifest_path = Path(str(committed.get("manifest", ""))).resolve()
        if not manifest_path.is_file():
            return AdapterResult(False, {}, "translation manifest missing")
        if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != committed.get("manifestSha256"):
            return AdapterResult(False, {}, "translation manifest fingerprint conflict")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expected_media = manifest["expectedMediaIds"]
            languages = manifest["targetLanguages"]
            translations = manifest["translations"]
            expected_coverage = [(language, media_id) for language in languages for media_id in expected_media]
            actual_coverage = [(row["targetLanguage"], row["mediaId"]) for row in translations]
            valid = (
                manifest.get("schemaVersion") == 1
                and bool(expected_media)
                and bool(languages)
                and actual_coverage == expected_coverage
                and all(
                    row["reviewStatus"] in {"MACHINE", "REVIEWED"}
                    and int(row["segmentCount"]) > 0
                    and Path(str(row["translationPath"])).is_file()
                    and hashlib.sha256(Path(str(row["translationPath"])).read_bytes()).hexdigest() == row["translationSha256"]
                    and Path(str(row["srtPath"])).is_file()
                    and hashlib.sha256(Path(str(row["srtPath"])).read_bytes()).hexdigest() == row["srtSha256"]
                    for row in translations
                )
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            translations = []
        if not valid:
            return AdapterResult(False, {}, "translation artifact validation failed")
        on_log(f"Verified translation manifest with {len(translations)} translation(s)")
        return AdapterResult(True, {"manifest": str(manifest_path), "translationCount": len(translations)})


class VoiceRenderingAdapter(CommandAdapter):
    def __init__(self, launcher: Path, voice_root: Path):
        super().__init__(); self.launcher=Path(launcher).resolve(); self.voice_root=Path(voice_root).resolve()

    def execute(self, node, context, on_log, cancel_event):
        committed=next((step.get("result") for step in context.get("steps",[]) if step.get("nodeId")=="translate" and step.get("status")=="COMPLETED"),None)
        if not isinstance(committed,dict): return AdapterResult(False,{},"committed translation manifest missing")
        manifest=Path(str(committed.get("manifest",""))).resolve()
        if not manifest.is_file(): return AdapterResult(False,{},"translation manifest missing")
        output=self.voice_root/str(context["runId"]); parameters=context["parameters"]
        argv=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(self.launcher),str(manifest),"--output-dir",str(output),"--operation-id",f"{context['runId']}:step:{node.id}"]
        for language in parameters["targetLanguages"]: argv.extend(["--voice",f"{language}={parameters['targetVoices'][language]}"])
        argv.append("--json")
        result=super().execute(GraphNode(node.id,"command",{"argv":argv}),context,on_log,cancel_event)
        receipt_path=output/"voice-receipt.json"
        if not result.completed or not receipt_path.is_file(): return AdapterResult(False,result.details,result.error or "voice receipt missing")
        try:
            receipt=json.loads(receipt_path.read_text(encoding="utf-8-sig")); voice_manifest=Path(str(receipt["manifest"])).resolve()
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as error: return AdapterResult(False,result.details,f"invalid voice receipt: {error}")
        if receipt.get("resultClass")!="COMPLETED" or not voice_manifest.is_file(): return AdapterResult(False,result.details,"Voice Rendering did not commit a manifest")
        return AdapterResult(True,{**result.details,"receipt":str(receipt_path),"manifest":str(voice_manifest),"manifestSha256":receipt.get("manifestSha256"),"clipCount":len(receipt.get("items",[]))})


class VerifyVoiceAdapter:
    def execute(self,node,context,on_log,cancel_event):
        committed=next((step.get("result") for step in context.get("steps",[]) if step.get("nodeId")=="render-voice" and step.get("status")=="COMPLETED"),None)
        if not isinstance(committed,dict): return AdapterResult(False,{},"committed voice fact missing")
        path=Path(str(committed.get("manifest",""))).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=committed.get("manifestSha256"): return AdapterResult(False,{},"voice manifest fingerprint conflict")
        try:
            value=json.loads(path.read_text(encoding="utf-8")); clips=value["clips"]
            valid=value.get("schemaVersion")==1 and bool(clips) and all(Path(row["clip"]["path"]).is_file() and Path(row["clip"]["path"]).stat().st_size==row["clip"]["size"] and hashlib.sha256(Path(row["clip"]["path"]).read_bytes()).hexdigest()==row["clip"]["sha256"] and float(row["clip"]["duration"])>0 for row in clips)
        except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError): valid=False; clips=[]
        if not valid: return AdapterResult(False,{},"voice artifact validation failed")
        on_log(f"Verified voice manifest with {len(clips)} clip(s)"); return AdapterResult(True,{"manifest":str(path),"clipCount":len(clips)})


class LocalizedVideoAdapter(CommandAdapter):
    """Compose localized derivatives from the three upstream manifest owners."""

    def __init__(self, launcher: Path, output_root: Path):
        super().__init__()
        self.launcher = Path(launcher).resolve()
        self.output_root = Path(output_root).resolve()

    def execute(self, node, context, on_log, cancel_event):
        results = {
            step.get("nodeId"): step.get("result")
            for step in context.get("steps", [])
            if step.get("status") == "COMPLETED"
        }
        source = results.get("intake")
        translation = results.get("translate")
        voice = results.get("render-voice")
        if not all(isinstance(value, dict) for value in (source, translation, voice)):
            return AdapterResult(False, {}, "committed Source, Translation and Voice facts are required")
        manifests = [Path(str(value.get("manifest", ""))).resolve() for value in (source, translation, voice)]
        if not all(path.is_file() for path in manifests):
            return AdapterResult(False, {}, "upstream composition manifest missing")
        output = self.output_root / str(context["runId"])
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.launcher),
            *(str(path) for path in manifests),
            "--output-dir", str(output),
            "--operation-id", f"{context['runId']}:step:{node.id}",
            "--source-volume", str(context["parameters"].get("sourceVolume", 0.12)),
            "--json",
        ]
        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, on_log, cancel_event)
        receipt_path = output / "localization-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "localization receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            manifest = Path(str(receipt["manifest"])).resolve()
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid localization receipt: {error}")
        if receipt.get("resultClass") != "COMPLETED" or not manifest.is_file():
            return AdapterResult(False, result.details, "Localization did not commit a manifest")
        items = receipt.get("items", [])
        return AdapterResult(True, {
            **result.details,
            "receipt": str(receipt_path),
            "manifest": str(manifest),
            "manifestSha256": receipt.get("manifestSha256"),
            "derivativeCount": len(items),
        })


class VerifyLocalizationAdapter:
    """Verify derivative coverage, media metadata and immutable fingerprints."""

    def execute(self, node, context, on_log, cancel_event):
        committed = next((
            step.get("result") for step in context.get("steps", [])
            if step.get("nodeId") == "localize-video" and step.get("status") == "COMPLETED"
        ), None)
        if not isinstance(committed, dict):
            return AdapterResult(False, {}, "committed localization fact missing")
        path = Path(str(committed.get("manifest", ""))).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != committed.get("manifestSha256"):
            return AdapterResult(False, {}, "localization manifest fingerprint conflict")
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
            languages = value["targetLanguages"]
            media_ids = value["expectedMediaIds"]
            derivatives = value["derivatives"]
            expected = [(language, media_id) for language in languages for media_id in media_ids]
            actual = [(row["targetLanguage"], row["mediaId"]) for row in derivatives]
            valid = (
                value.get("schemaVersion") == 1
                and bool(languages)
                and bool(media_ids)
                and actual == expected
                and all(
                    (file := Path(str(row["path"]))).is_file()
                    and file.stat().st_size == row["size"]
                    and hashlib.sha256(file.read_bytes()).hexdigest() == row["sha256"]
                    and float(row["duration"]) > 0
                    and int(row["width"]) > 0
                    and int(row["height"]) > 0
                    and bool(row["videoCodec"])
                    and bool(row["audioCodec"])
                    for row in derivatives
                )
            )
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            derivatives = []
        if not valid:
            return AdapterResult(False, {}, "localized derivative validation failed")
        on_log(f"Verified localization manifest with {len(derivatives)} derivative(s)")
        return AdapterResult(True, {"manifest": str(path), "derivativeCount": len(derivatives)})


class CreatorDiscoveryAdapter(CommandAdapter):
    def __init__(self, launcher: Path, output_root: Path):
        super().__init__(); self.launcher=Path(launcher).resolve(); self.output_root=Path(output_root).resolve()

    def execute(self,node,context,on_log,cancel_event):
        parameters=context["parameters"]; output=self.output_root/str(context["runId"])
        argv=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(self.launcher),"profile",str(parameters["sourceUrl"]),"--max-items",str(parameters.get("maxItems",0)),"--output-dir",str(output),"--operation-id",f"{context['runId']}:step:{node.id}"]
        if parameters.get("authenticationFile"): argv.extend(["--cookies",str(parameters["authenticationFile"])])
        argv.append("--json")
        result=super().execute(GraphNode(node.id,"command",{"argv":argv}),context,on_log,cancel_event); receipt_path=output/"discovery-receipt.json"
        if not result.completed or not receipt_path.is_file(): return AdapterResult(False,result.details,result.error or "discovery receipt missing")
        try: receipt=json.loads(receipt_path.read_text(encoding="utf-8-sig")); manifest=Path(str(receipt["manifest"])).resolve()
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as error: return AdapterResult(False,result.details,f"invalid discovery receipt: {error}")
        if receipt.get("resultClass")!="COMPLETED" or not manifest.is_file(): return AdapterResult(False,result.details,"Creator Discovery did not commit a manifest")
        return AdapterResult(True,{**result.details,"receipt":str(receipt_path),"manifest":str(manifest),"manifestSha256":receipt.get("manifestSha256"),"itemCount":int(receipt.get("itemCount",0))})


class VerifyCreatorManifestAdapter:
    def execute(self,node,context,on_log,cancel_event):
        committed=next((step.get("result") for step in context.get("steps",[]) if step.get("nodeId")=="discover-creator" and step.get("status")=="COMPLETED"),None)
        if not isinstance(committed,dict): return AdapterResult(False,{},"committed creator fact missing")
        path=Path(str(committed.get("manifest",""))).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=committed.get("manifestSha256"): return AdapterResult(False,{},"creator manifest fingerprint conflict")
        try:
            value=json.loads(path.read_text(encoding="utf-8-sig")); items=value["items"]; maximum=int(value["maxItems"])
            ids=[str(row["id"]) for row in items]
            valid=value.get("schemaVersion")==1 and value.get("platform") in {"youtube","bilibili","douyin","tiktok"} and bool(items) and [int(row["ordinal"]) for row in items]==list(range(1,len(items)+1)) and len(ids)==len(set(ids)) and all(str(row["url"]).startswith("https://") and bool(str(row["title"]).strip()) for row in items) and (maximum==0 or len(items)<=maximum)
        except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError): valid=False; items=[]
        if not valid: return AdapterResult(False,{},"creator manifest validation failed")
        on_log(f"Verified creator manifest with {len(items)} video URL(s)"); return AdapterResult(True,{"manifest":str(path),"itemCount":len(items)})


class CreatorBatchAdapter(CommandAdapter):
    """Invoke the independent Creator Batch continuation owner."""

    def __init__(self, launcher: Path, output_root: Path):
        super().__init__()
        self.launcher = Path(launcher).resolve()
        self.output_root = Path(output_root).resolve()

    def execute(self, node, context, on_log, cancel_event):
        committed = next((
            step.get("result") for step in context.get("steps", [])
            if step.get("nodeId") == "discover-creator" and step.get("status") == "COMPLETED"
        ), None)
        if not isinstance(committed, dict):
            return AdapterResult(False, {}, "committed Creator Manifest fact missing")
        creator_manifest = Path(str(committed.get("manifest", ""))).resolve()
        if not creator_manifest.is_file() or hashlib.sha256(creator_manifest.read_bytes()).hexdigest() != committed.get("manifestSha256"):
            return AdapterResult(False, {}, "Creator Manifest fingerprint conflict")
        parameters = context["parameters"]
        output = self.output_root / str(context["runId"])
        operation_id = f"{context['runId']}:step:{node.id}"
        argv = [
            "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.launcher),
            "localize", str(creator_manifest),
            "--output-dir", str(output),
            "--operation-id", operation_id,
            "--source-language", str(parameters["sourceLanguage"]),
            "--asr-model", str(parameters["asrModel"]),
            "--asr-device", str(parameters["asrDevice"]),
            "--asr-compute-type", str(parameters["asrComputeType"]),
            "--translation-model", str(parameters["translationModel"]),
            "--translation-device", str(parameters["translationDevice"]),
            "--translation-batch-size", str(parameters["translationBatchSize"]),
            "--source-volume", str(parameters["sourceVolume"]),
        ]
        for language in parameters["targetLanguages"]:
            argv.extend(["--target-language", language])
            argv.extend(["--voice", f"{language}={parameters['targetVoices'][language]}"])
        if parameters.get("authenticationFile"):
            argv.extend(["--cookies", str(parameters["authenticationFile"])])
        argv.append("--json")
        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, on_log, cancel_event)
        receipt_path = output / "creator-batch-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "Creator Batch receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
            manifest = Path(str(receipt["manifest"])).resolve()
            expected_sha = str(receipt["manifestSha256"])
        except (OSError, KeyError, TypeError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid Creator Batch receipt: {error}")
        valid = (
            receipt.get("schemaVersion") == 1
            and receipt.get("operationId") == operation_id
            and receipt.get("resultClass") == "COMPLETED"
            and manifest.is_file()
            and hashlib.sha256(manifest.read_bytes()).hexdigest() == expected_sha
            and int(receipt.get("itemCount", 0)) > 0
            and int(receipt.get("completedCount", receipt.get("itemCount", 0))) == int(receipt.get("itemCount", 0))
        )
        if not valid:
            return AdapterResult(False, result.details, "Creator Batch did not commit complete coverage")
        return AdapterResult(True, {
            **result.details,
            "receipt": str(receipt_path),
            "manifest": str(manifest),
            "manifestSha256": expected_sha,
            "itemCount": int(receipt["itemCount"]),
        })


class VerifyCreatorBatchAdapter:
    """Verify aggregate item/language coverage and every derivative fact."""

    def execute(self, node, context, on_log, cancel_event):
        results = {
            step.get("nodeId"): step.get("result")
            for step in context.get("steps", [])
            if step.get("status") == "COMPLETED"
        }
        creator_fact = results.get("discover-creator")
        batch_fact = results.get("localize-creator-batch")
        if not isinstance(creator_fact, dict) or not isinstance(batch_fact, dict):
            return AdapterResult(False, {}, "committed Creator and Batch facts are required")
        creator_path = Path(str(creator_fact.get("manifest", ""))).resolve()
        batch_path = Path(str(batch_fact.get("manifest", ""))).resolve()
        if (
            not creator_path.is_file()
            or hashlib.sha256(creator_path.read_bytes()).hexdigest() != creator_fact.get("manifestSha256")
            or not batch_path.is_file()
            or hashlib.sha256(batch_path.read_bytes()).hexdigest() != batch_fact.get("manifestSha256")
        ):
            return AdapterResult(False, {}, "Creator Batch fingerprint conflict")
        try:
            creator = json.loads(creator_path.read_text(encoding="utf-8-sig"))
            batch = json.loads(batch_path.read_text(encoding="utf-8-sig"))
            creator_ids = [str(row["id"]) for row in creator["items"]]
            items = batch["items"]
            languages = list(context["parameters"]["targetLanguages"])
            valid = (
                batch.get("schemaVersion") == 1
                and Path(str(batch["creatorManifest"])).resolve() == creator_path
                and batch.get("creatorManifestSha256") == creator_fact.get("manifestSha256")
                and batch.get("expectedItemIds") == creator_ids
                and batch.get("targetLanguages") == languages
                and batch.get("maximumActiveItems") == 1
                and [int(row["ordinal"]) for row in items] == list(range(1, len(creator_ids) + 1))
                and [str(row["id"]) for row in items] == creator_ids
            )
            derivative_count = 0
            for row in items:
                localization_path = Path(str(row["localizationManifest"])).resolve()
                if not localization_path.is_file() or hashlib.sha256(localization_path.read_bytes()).hexdigest() != row["localizationManifestSha256"]:
                    valid = False
                    break
                localization = json.loads(localization_path.read_text(encoding="utf-8-sig"))
                media_ids = localization["expectedMediaIds"]
                derivatives = localization["derivatives"]
                expected = [(language, media_id) for language in languages for media_id in media_ids]
                actual = [(value["targetLanguage"], value["mediaId"]) for value in derivatives]
                valid = valid and (
                    localization.get("schemaVersion") == 1
                    and localization.get("targetLanguages") == languages
                    and bool(media_ids)
                    and actual == expected
                    and len(derivatives) == int(row["derivativeCount"])
                    and all(
                        (file := Path(str(value["path"]))).is_file()
                        and file.stat().st_size == int(value["size"])
                        and hashlib.sha256(file.read_bytes()).hexdigest() == value["sha256"]
                        and float(value["duration"]) > 0
                        and int(value["width"]) > 0
                        and int(value["height"]) > 0
                        and bool(value["videoCodec"])
                        and bool(value["audioCodec"])
                        for value in derivatives
                    )
                )
                derivative_count += len(derivatives)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            valid = False
            derivative_count = 0
            items = []
        if not valid:
            return AdapterResult(False, {}, "Creator Batch artifact validation failed")
        on_log(f"Verified {len(items)} creator item(s) and {derivative_count} localized derivative(s)")
        return AdapterResult(True, {"manifest": str(batch_path), "itemCount": len(items), "derivativeCount": derivative_count})


class PublicationPlanAdapter(CommandAdapter):
    def __init__(self,launcher:Path,output_root:Path):super().__init__(); self.launcher=Path(launcher).resolve(); self.output_root=Path(output_root).resolve()
    def execute(self,node,context,on_log,cancel_event):
        parameters=context["parameters"]; output=self.output_root/str(context["runId"]); argv=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(self.launcher),"plan",str(parameters["videoPath"]),"--metadata",str(parameters["metadataPath"])]
        for platform in parameters["targetPlatforms"]:argv.extend(["--target",f"{platform}={parameters['account']}"])
        for platform,credential_id in parameters.get("credentialIds",{}).items():argv.extend(["--credential",f"{platform}={credential_id}"])
        argv.extend(["--output-dir",str(output),"--operation-id",f"{context['runId']}:step:{node.id}","--json"]); result=super().execute(GraphNode(node.id,"command",{"argv":argv}),context,on_log,cancel_event); receipt_path=output/"planning-receipt.json"
        if not result.completed or not receipt_path.is_file():return AdapterResult(False,result.details,result.error or "planning receipt missing")
        try:receipt=json.loads(receipt_path.read_text(encoding="utf-8-sig")); plan=Path(str(receipt["plan"])).resolve()
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as error:return AdapterResult(False,result.details,f"invalid planning receipt: {error}")
        if receipt.get("resultClass")!="COMPLETED" or not plan.is_file():return AdapterResult(False,result.details,"Publication did not commit a plan")
        return AdapterResult(True,{**result.details,"receipt":str(receipt_path),"manifest":str(plan),"manifestSha256":receipt.get("planSha256"),"jobCount":int(receipt.get("jobCount",0))})


class VerifyPublicationPlanAdapter:
    def execute(self,node,context,on_log,cancel_event):
        committed=next((step.get("result") for step in context.get("steps",[]) if step.get("nodeId")=="plan-publication" and step.get("status")=="COMPLETED"),None)
        if not isinstance(committed,dict):return AdapterResult(False,{},"committed publication plan missing")
        path=Path(str(committed.get("manifest",""))).resolve()
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=committed.get("manifestSha256"):return AdapterResult(False,{},"publication plan fingerprint conflict")
        try:
            value=json.loads(path.read_text(encoding="utf-8-sig")); video=value["video"]; metadata=value["metadata"]; jobs=value["jobs"]
            video_path=Path(str(video["path"])); metadata_path=Path(str(metadata["path"])); platforms=[row["platform"] for row in jobs]
            valid=value.get("schemaVersion")==1 and value.get("public") is False and bool(jobs) and [int(row["ordinal"]) for row in jobs]==list(range(1,len(jobs)+1)) and len(platforms)==len(set(platforms)) and all(row["visibility"]=="private-or-draft" and len(str(row["id"]))==64 and bool(str(row["account"]).strip()) for row in jobs) and video_path.is_file() and video_path.stat().st_size==video["size"] and hashlib.sha256(video_path.read_bytes()).hexdigest()==video["sha256"] and metadata_path.is_file() and hashlib.sha256(metadata_path.read_bytes()).hexdigest()==metadata["sha256"]
        except (OSError,KeyError,TypeError,ValueError,json.JSONDecodeError):valid=False;jobs=[]
        if not valid:return AdapterResult(False,{},"publication plan validation failed")
        on_log(f"Verified publication plan with {len(jobs)} target(s)");return AdapterResult(True,{"manifest":str(path),"jobCount":len(jobs)})


class PublicationExecuteAdapter(CommandAdapter):
    def __init__(self,launcher:Path,output_root:Path,platform_io_launcher:Path|None=None):super().__init__(); self.launcher=Path(launcher).resolve(); self.output_root=Path(output_root).resolve(); self.platform_io_launcher=Path(platform_io_launcher).resolve() if platform_io_launcher else None
    def execute(self,node,context,on_log,cancel_event):
        parameters=context["parameters"]; output=self.output_root/str(context["runId"]); argv=["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-File",str(self.launcher),"execute",str(parameters["planPath"]),"--confirmation",str(parameters["confirmation"]),"--credential-vault",str(parameters["credentialVaultPath"]),"--output-dir",str(output),"--operation-id",f"{context['runId']}:step:{node.id}","--json"]
        if self.platform_io_launcher:argv.extend(["--platform-io-launcher",str(self.platform_io_launcher)])
        result=super().execute(GraphNode(node.id,"command",{"argv":argv}),context,on_log,cancel_event); receipt_path=output/"publication-receipt.json"
        if not result.completed or not receipt_path.is_file():return AdapterResult(False,result.details,result.error or "publication receipt missing")
        try:receipt=json.loads(receipt_path.read_text(encoding="utf-8-sig")); manifest=Path(str(receipt["manifest"])).resolve(); manifest_sha=str(receipt["manifestSha256"])
        except (OSError,KeyError,TypeError,json.JSONDecodeError) as error:return AdapterResult(False,result.details,f"invalid publication receipt: {error}")
        if receipt.get("resultClass")!="COMPLETED" or not manifest.is_file() or hashlib.sha256(manifest.read_bytes()).hexdigest()!=manifest_sha:return AdapterResult(False,result.details,"Publication did not commit a verified manifest")
        return AdapterResult(True,{**result.details,"receipt":str(receipt_path),"manifest":str(manifest),"manifestSha256":manifest_sha})


class VerifyPublicationExecutionAdapter:
    def execute(self,node,context,on_log,cancel_event):
        committed=next((step.get("result") for step in context.get("steps",[]) if step.get("nodeId")=="execute-publication" and step.get("status")=="COMPLETED"),None)
        if not isinstance(committed,dict):return AdapterResult(False,{},"committed publication execution missing")
        path=Path(str(committed.get("manifest",""))).resolve(); expected=str(committed.get("manifestSha256","")); plan=Path(str(context.get("parameters",{}).get("planPath",""))).resolve(); confirmation=str(context.get("parameters",{}).get("confirmation",""))
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected or not plan.is_file() or hashlib.sha256(plan.read_bytes()).hexdigest()!=confirmation:return AdapterResult(False,{},"publication execution fingerprint conflict")
        try:value=json.loads(path.read_text(encoding="utf-8-sig")); publications=value["publications"]
        except (OSError,KeyError,TypeError,json.JSONDecodeError):return AdapterResult(False,{},"publication manifest validation failed")
        valid=value.get("schemaVersion")==1 and value.get("public") is False and Path(str(value.get("plan",""))).resolve()==plan and value.get("planSha256")==confirmation and bool(publications) and all(row.get("status")=="COMPLETED" and row.get("platform")=="youtube" and bool(str(row.get("externalId","")).strip()) for row in publications)
        if not valid:return AdapterResult(False,{},"publication manifest validation failed")
        on_log(f"Verified {len(publications)} private publication receipt(s)");return AdapterResult(True,{"manifest":str(path),"publicationCount":len(publications)})


class YouTubeConnectAdapter(CommandAdapter):
    def __init__(self, launcher: Path, output_root: Path):
        super().__init__(); self.launcher = Path(launcher).resolve(); self.output_root = Path(output_root).resolve()

    def execute(self, node, context, on_log, cancel_event):
        parameters = context["parameters"]; output = self.output_root / str(context["runId"]); operation_id = f"{context['runId']}:step:{node.id}"
        argv = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.launcher), "connect", "--client-config", str(parameters["clientConfigPath"]), "--vault", str(parameters["credentialVaultPath"]), "--credential-id", str(parameters["credentialId"]), "--label", str(parameters["label"]), "--output-dir", str(output), "--operation-id", operation_id, "--json"]
        def safe_log(line: str) -> None:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                event = None
            if isinstance(event, dict) and event.get("event") == "authorization" and "url" in event:
                on_log("YouTube consent opened in the system browser; ephemeral authorization parameters were not persisted.")
                return
            on_log(line)

        result = super().execute(GraphNode(node.id, "command", {"argv": argv}), context, safe_log, cancel_event); receipt_path = output / "youtube-oauth-receipt.json"
        if not result.completed or not receipt_path.is_file():
            return AdapterResult(False, result.details, result.error or "YouTube OAuth receipt missing")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as error:
            return AdapterResult(False, result.details, f"invalid YouTube OAuth receipt: {error}")
        valid = receipt.get("schemaVersion") == 1 and receipt.get("operationId") == operation_id and receipt.get("resultClass") == "COMPLETED" and receipt.get("credentialId") == parameters["credentialId"] and receipt.get("provider") == "youtube" and receipt.get("status") == "ACTIVE" and receipt.get("scope") == "https://www.googleapis.com/auth/youtube.upload"
        if not valid:
            return AdapterResult(False, result.details, "YouTube OAuth receipt validation failed")
        return AdapterResult(True, {**result.details, "receipt": str(receipt_path), "receiptSha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(), "credentialId": parameters["credentialId"]})


class VerifyYouTubeCredentialAdapter:
    def __init__(self, vault_launcher: Path, *, runner=subprocess.run):
        self.vault_launcher = Path(vault_launcher).resolve(); self.runner = runner

    def execute(self, node, context, on_log, cancel_event):
        parameters = context["parameters"]
        committed = next((step.get("result") for step in context.get("steps", []) if step.get("nodeId") == "connect-youtube" and step.get("status") == "COMPLETED"), None)
        if not isinstance(committed, dict):
            return AdapterResult(False, {}, "committed YouTube OAuth fact missing")
        receipt = Path(str(committed.get("receipt", ""))).resolve()
        if not receipt.is_file() or hashlib.sha256(receipt.read_bytes()).hexdigest() != committed.get("receiptSha256"):
            return AdapterResult(False, {}, "YouTube OAuth receipt fingerprint conflict")
        argv = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(self.vault_launcher), "describe", "--vault", str(parameters["credentialVaultPath"]), "--credential-id", str(parameters["credentialId"]), "--json"]
        try:
            completed = self.runner(argv, text=True, capture_output=True, encoding="utf-8", errors="replace")
            payload = json.loads(completed.stdout)
        except (OSError, json.JSONDecodeError):
            return AdapterResult(False, {}, "Credential Vault describe failed")
        value = payload.get("value", {}) if isinstance(payload, dict) else {}
        valid = completed.returncode == 0 and payload.get("resultClass") in {"COMPLETED", "DUPLICATE_COMPLETED"} and value.get("credentialId") == parameters["credentialId"] and value.get("provider") == "youtube" and value.get("status") == "ACTIVE"
        if not valid:
            return AdapterResult(False, {}, "Credential Vault did not confirm an active YouTube credential")
        on_log(f"Verified active YouTube credential: {parameters['credentialId']}")
        return AdapterResult(True, {"credentialId": parameters["credentialId"], "provider": "youtube", "status": "ACTIVE"})
