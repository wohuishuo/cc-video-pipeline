"""Loopback HTTP transport and static file server."""

from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import webbrowser
from urllib.parse import parse_qs, urlsplit

from .api import StudioApplication


MAX_BODY_BYTES = 1024 * 1024


def create_server(
    host: str,
    port: int,
    application: StudioApplication,
    *,
    web_root: Path,
) -> ThreadingHTTPServer:
    if host != "127.0.0.1":
        raise ValueError("Video Graph Studio may bind only to 127.0.0.1")
    root = Path(web_root).resolve()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self._dispatch()

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch()

        def _dispatch(self) -> None:
            parsed = urlsplit(self.path)
            if parsed.path.startswith("/api/"):
                body = self._read_json() if self.command == "POST" else None
                if body is _INVALID:
                    self._send_json(400, {"resultClass": "REJECTED_MALFORMED"})
                    return
                status, payload = application.handle(
                    self.command, parsed.path, parse_qs(parsed.query), body
                )
                self._send_json(status, payload)
                return
            self._serve_static(parsed.path)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return _INVALID
            if length <= 0 or length > MAX_BODY_BYTES:
                return _INVALID
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return _INVALID
            return value if isinstance(value, dict) else _INVALID

        def _send_json(self, status: int, payload: dict) -> None:
            content = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def _serve_static(self, request_path: str) -> None:
            relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
            candidate = (root / relative).resolve()
            if not (candidate == root or candidate.is_relative_to(root)) or not candidate.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args) -> None:
            return

    return ThreadingHTTPServer((host, port), Handler)


_INVALID = object()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Video Graph Studio control plane.")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--no-browser", action="store_true")
    return parser


def _allowed_roots(repository: Path) -> tuple[Path, ...]:
    home = Path.home()
    candidates = [repository, home / "Videos", home / "Documents", home / "Downloads", home / "Desktop"]
    result: list[Path] = []
    for candidate in candidates:
        if candidate.exists():
            resolved = candidate.resolve()
            if resolved not in result:
                result.append(resolved)
    return tuple(result)


def build_runtime(repository: Path, data_root: Path):
    from .adapters import (
        PreparedFolderAdapter,
        PreparedFolderEdgeAdapter,
        LocalizedVideoAdapter,
        CreatorDiscoveryAdapter,
        PublicationPlanAdapter,
        SourceIntakeAdapter,
        TranscriptSourceAdapter,
        TranslateTranscriptAdapter,
        VoiceRenderingAdapter,
        VerifyOutputAdapter,
        VerifySourceAdapter,
        VerifyTranscriptAdapter,
        VerifyTranslationAdapter,
        VerifyVoiceAdapter,
        VerifyLocalizationAdapter,
        VerifyCreatorManifestAdapter,
        VerifyPublicationPlanAdapter,
    )
    from .engine import WorkflowEngine
    from .store import RunStore

    repository = Path(repository).resolve()
    data_root = Path(data_root).resolve()
    data_root.mkdir(parents=True, exist_ok=True)
    store = RunStore(data_root / "studio.db")
    store.interrupt_active()
    edge_launcher = repository / "apps" / "localization" / "edge-russian.ps1"
    intake_launcher = repository / "apps" / "source-intake" / "run.ps1"
    transcription_launcher = repository / "apps" / "transcription" / "run.ps1"
    translation_launcher = repository / "apps" / "translation" / "run.ps1"
    voice_launcher = repository / "apps" / "voice-rendering" / "run.ps1"
    localization_launcher = repository / "apps" / "localization" / "run.ps1"
    creator_discovery_launcher = repository / "apps" / "creator-discovery" / "run.ps1"
    publication_launcher = repository / "apps" / "publication" / "run.ps1"
    engine = WorkflowEngine(
        store,
        {
            "prepared-folder": PreparedFolderAdapter(),
            "edge-localize": PreparedFolderEdgeAdapter(edge_launcher),
            "verify-output": VerifyOutputAdapter(),
            "source-intake": SourceIntakeAdapter(intake_launcher, data_root / "intakes"),
            "verify-source": VerifySourceAdapter(),
            "transcribe-source": TranscriptSourceAdapter(
                transcription_launcher, data_root / "transcripts"
            ),
            "verify-transcript": VerifyTranscriptAdapter(),
            "translate-transcript": TranslateTranscriptAdapter(
                translation_launcher, data_root / "translations"
            ),
            "verify-translation": VerifyTranslationAdapter(),
            "render-voice": VoiceRenderingAdapter(voice_launcher, data_root / "voices"),
            "verify-voice": VerifyVoiceAdapter(),
            "localize-video": LocalizedVideoAdapter(
                localization_launcher, data_root / "localized"
            ),
            "verify-localization": VerifyLocalizationAdapter(),
            "discover-creator": CreatorDiscoveryAdapter(
                creator_discovery_launcher, data_root / "creators"
            ),
            "verify-creator": VerifyCreatorManifestAdapter(),
            "plan-publication": PublicationPlanAdapter(
                publication_launcher, data_root / "publication-plans"
            ),
            "verify-publication-plan": VerifyPublicationPlanAdapter(),
        },
    )
    application = StudioApplication(store, engine, allowed_roots=_allowed_roots(repository))
    return application, engine


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repository = Path(__file__).resolve().parents[3]
    application, engine = build_runtime(repository, args.data_root)
    server = create_server(
        "127.0.0.1",
        args.port,
        application,
        web_root=repository / "apps" / "video-graph-studio" / "web",
    )
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Video Graph Studio: {url}", flush=True)
    print(f"Data root: {args.data_root.resolve()}", flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        active = engine.active_run_id
        if active:
            engine.cancel(active)
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
