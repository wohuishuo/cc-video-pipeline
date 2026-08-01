"""Replaceable worker adapters used by the workflow engine."""

from __future__ import annotations

from dataclasses import dataclass
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

