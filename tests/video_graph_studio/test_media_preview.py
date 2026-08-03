import threading
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


APP = Path(__file__).resolve().parents[2] / "apps" / "video-graph-studio"
sys.path.insert(0, str(APP))

from studio.api import StudioApplication  # noqa: E402
from studio.server import create_server  # noqa: E402
from test_result_projection import completed_run  # noqa: E402


def preview_server(tmp_path):
    run, video = completed_run(tmp_path)

    class Store:
        def get_run(self, run_id):
            if run_id != "run-1":
                raise KeyError(run_id)
            return run

    application = StudioApplication(Store(), object(), allowed_roots=(tmp_path,))
    result = application.handle("GET", "/api/v1/runs/run-1/results", {}, None)[1]
    video_id = result["videos"][0]["id"]
    server = create_server("127.0.0.1", 0, application, web_root=tmp_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, f"http://127.0.0.1:{server.server_port}", video, video_id


def test_preview_serves_full_file_and_bounded_byte_range(tmp_path):
    server, thread, base, video, video_id = preview_server(tmp_path)
    try:
        with urlopen(f"{base}/api/v1/runs/run-1/media/{video_id}", timeout=5) as response:
            assert response.status == 200
            assert response.headers["Content-Type"] == "video/mp4"
            assert response.headers["Accept-Ranges"] == "bytes"
            assert response.read() == video.read_bytes()

        request = Request(
            f"{base}/api/v1/runs/run-1/media/{video_id}",
            headers={"Range": "bytes=2-5"},
        )
        with urlopen(request, timeout=5) as response:
            assert response.status == 206
            assert response.headers["Content-Range"] == "bytes 2-5/10"
            assert response.read() == b"2345"
    finally:
        server.shutdown()
        thread.join()


def test_preview_rejects_unverified_ids_and_invalid_ranges(tmp_path):
    server, thread, base, _video, video_id = preview_server(tmp_path)
    try:
        for url, headers, expected in (
            (f"{base}/api/v1/runs/run-1/media/not-a-result", {}, 404),
            (f"{base}/api/v1/runs/run-1/media/{video_id}", {"Range": "bytes=99-100"}, 416),
            (f"{base}/api/v1/runs/run-1/media/../../secret", {}, 404),
        ):
            try:
                urlopen(Request(url, headers=headers), timeout=5)
            except HTTPError as error:
                assert error.code == expected
            else:
                raise AssertionError(f"unverified media request was accepted: {url}")
    finally:
        server.shutdown()
        thread.join()
