# Portable Video Platform IO Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a portable CLI whose four independent platform adapters download the best available video up to 1080p and prepare authenticated uploads without publicly publishing test content.

**Architecture:** A small Python package owns contracts, process execution, receipts, and CLI routing. Download adapters invoke the installed `yt-dlp`; upload adapters invoke a pinned checkout of `dreammis/social-auto-upload` through isolated subprocess boundaries. Platform capabilities and evidence are recorded separately, so one failure cannot be reported as aggregate success.

**Tech Stack:** Python 3.12 standard library, pytest, yt-dlp CLI, FFmpeg/FFprobe, Git, dreammis/social-auto-upload.

## Global Constraints

- Public-video extraction attempts anonymous access first; cookies are optional and never stored in Git.
- Requested maximum height is 1080p; receipts record probed reality and never invent 1080p.
- YouTube, Bilibili, Douyin, and TikTok own independent capability status.
- Upload verification stops at draft or final-confirmation state and never publicly publishes test media.
- No absolute username-specific path may appear in production configuration.
- Dependencies are pinned by source URL and Git revision.
- Windows PowerShell is the primary launcher; the Python package remains portable.

---

### Task 1: Core contracts, process runner, and redacted receipts

**Files:**
- Create: `video_platform/__init__.py`
- Create: `video_platform/models.py`
- Create: `video_platform/process.py`
- Create: `video_platform/receipts.py`
- Test: `tests/video_platform/test_core.py`

**Interfaces:**
- Produces: `Platform`, `JobReceipt`, `ProcessResult`, `ProcessRunner.run(args, cwd=None)`, `write_receipt(receipt, path)`.
- Consumes: Python standard library only.

- [ ] **Step 1: Write failing contract tests**

```python
def test_receipt_json_redacts_credentials(tmp_path):
    receipt = JobReceipt(platform=Platform.YOUTUBE, operation="download", status="ok", facts={"cookie_file": "secret.txt"})
    path = write_receipt(receipt, tmp_path / "receipt.json")
    assert "secret.txt" not in path.read_text(encoding="utf-8")

def test_process_runner_returns_structured_result():
    result = ProcessRunner().run([sys.executable, "-c", "print('ok')"])
    assert result.exit_code == 0
    assert result.stdout.strip() == "ok"
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/video_platform/test_core.py -q`

Expected: collection fails because `video_platform` does not exist.

- [ ] **Step 3: Implement minimal immutable models, subprocess execution, atomic JSON receipt writing, and secret-key redaction**

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/video_platform/test_core.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

```powershell
git add video_platform tests/video_platform/test_core.py
git commit -m "feat: add portable platform IO core"
```

### Task 2: Platform routing and yt-dlp download command construction

**Files:**
- Create: `video_platform/platforms.py`
- Create: `video_platform/download.py`
- Test: `tests/video_platform/test_download.py`

**Interfaces:**
- Consumes: `Platform`, `ProcessRunner`.
- Produces: `detect_platform(url) -> Platform`, `DownloadRequest`, `YtDlpDownloader.build_args(request)`, `YtDlpDownloader.download(request) -> JobReceipt`.

- [ ] **Step 1: Write failing routing and argument tests**

```python
@pytest.mark.parametrize(("url", "platform"), [
    ("https://www.youtube.com/watch?v=x", Platform.YOUTUBE),
    ("https://www.bilibili.com/video/BV1x", Platform.BILIBILI),
    ("https://www.douyin.com/video/1", Platform.DOUYIN),
    ("https://www.tiktok.com/@a/video/1", Platform.TIKTOK),
])
def test_detect_platform(url, platform):
    assert detect_platform(url) is platform

def test_download_args_cap_height_and_do_not_require_cookie(tmp_path):
    args = YtDlpDownloader().build_args(DownloadRequest(Platform.YOUTUBE, "https://youtu.be/x", tmp_path, 1080))
    assert "height<=1080" in " ".join(args)
    assert "--cookies" not in args
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/video_platform/test_download.py -q`

Expected: imports fail because routing and downloader do not exist.

- [ ] **Step 3: Implement host allowlists, portable output paths, yt-dlp JSON progress capture, optional `--cookies`, and FFprobe verification**

- [ ] **Step 4: Add and pass failure tests for unsupported URL, missing output, and actual height below 1080**

Run: `python -m pytest tests/video_platform/test_download.py -q`

- [ ] **Step 5: Commit**

```powershell
git add video_platform/platforms.py video_platform/download.py tests/video_platform/test_download.py
git commit -m "feat: add independent yt-dlp download adapters"
```

### Task 3: Portable CLI and doctor/capability projection

**Files:**
- Create: `video_platform/cli.py`
- Create: `video_platform/__main__.py`
- Create: `video-platform.ps1`
- Test: `tests/video_platform/test_cli.py`

**Interfaces:**
- Consumes: platform detection, downloader, receipts.
- Produces: `python -m video_platform doctor|capabilities|download|login|upload` and PowerShell launcher.

- [ ] **Step 1: Write failing CLI tests**

```python
def test_doctor_reports_each_dependency(capsys):
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code in (0, 1)
    assert set(payload["dependencies"]) >= {"python", "yt-dlp", "ffmpeg", "ffprobe", "git"}

def test_capabilities_never_collapses_platform_statuses(capsys):
    main(["capabilities", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert set(payload["platforms"]) == {"youtube", "bilibili", "douyin", "tiktok"}
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/video_platform/test_cli.py -q`

- [ ] **Step 3: Implement argparse commands and a location-independent PowerShell launcher using `$PSScriptRoot`**

- [ ] **Step 4: Run GREEN and manual doctor**

Run: `python -m pytest tests/video_platform/test_cli.py -q`

Run: `powershell -ExecutionPolicy Bypass -File .\video-platform.ps1 doctor --json`

- [ ] **Step 5: Commit**

```powershell
git add video_platform/cli.py video_platform/__main__.py video-platform.ps1 tests/video_platform/test_cli.py
git commit -m "feat: add portable video platform CLI"
```

### Task 4: Pinned social-auto-upload dependency installer

**Files:**
- Create: `vendor/video-uploaders.lock.json`
- Create: `tools/install_video_uploaders.ps1`
- Create: `video_platform/dependencies.py`
- Test: `tests/video_platform/test_dependencies.py`

**Interfaces:**
- Produces: `DependencyManifest.load(path)`, `resolve_uploader_checkout(root)`, repeatable installer.
- Consumes: Git and Python 3.12.

- [ ] **Step 1: Write failing manifest tests**

```python
def test_uploader_dependency_is_pinned_to_full_git_revision():
    manifest = DependencyManifest.load(Path("vendor/video-uploaders.lock.json"))
    dep = manifest.dependencies["social-auto-upload"]
    assert dep.url == "https://github.com/dreammis/social-auto-upload.git"
    assert re.fullmatch(r"[0-9a-f]{40}", dep.revision)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/video_platform/test_dependencies.py -q`

- [ ] **Step 3: Resolve the current upstream commit, record license/source, and implement an idempotent installer into `.tools/social-auto-upload` with its own virtual environment**

- [ ] **Step 4: Run GREEN, install, and verify pinned HEAD**

Run: `python -m pytest tests/video_platform/test_dependencies.py -q`

Run: `powershell -ExecutionPolicy Bypass -File .\tools\install_video_uploaders.ps1`

Run: `git -C .tools/social-auto-upload rev-parse HEAD`

- [ ] **Step 5: Commit**

```powershell
git add vendor/video-uploaders.lock.json tools/install_video_uploaders.ps1 video_platform/dependencies.py tests/video_platform/test_dependencies.py
git commit -m "build: pin social platform upload dependency"
```

### Task 5: Isolated upload adapters and duplicate protection

**Files:**
- Create: `video_platform/upload.py`
- Create: `video_platform/uploaders/youtube.py`
- Create: `video_platform/uploaders/bilibili.py`
- Create: `video_platform/uploaders/douyin.py`
- Create: `video_platform/uploaders/tiktok.py`
- Create: `video_platform/uploaders/__init__.py`
- Test: `tests/video_platform/test_upload.py`

**Interfaces:**
- Consumes: pinned uploader checkout, `ProcessRunner`, receipts.
- Produces: `UploadRequest`, `UploadAdapter.prepare(request)`, per-platform login and draft commands.

- [ ] **Step 1: Write failing isolation and safety tests**

```python
def test_draft_is_mandatory_for_automated_upload():
    with pytest.raises(ValueError, match="draft"):
        UploadRequest(Platform.YOUTUBE, Path("video.mp4"), Path("meta.json"), draft=False)

def test_each_adapter_uses_its_own_profile(tmp_path):
    adapters = build_upload_adapters(tmp_path)
    assert len({a.profile_dir for a in adapters.values()}) == 4

def test_duplicate_idempotency_key_is_rejected(tmp_path):
    ledger = UploadLedger(tmp_path / "uploads.jsonl")
    ledger.reserve("same", Platform.TIKTOK)
    with pytest.raises(DuplicateUpload):
        ledger.reserve("same", Platform.TIKTOK)
```

- [ ] **Step 2: Run RED**

Run: `python -m pytest tests/video_platform/test_upload.py -q`

- [ ] **Step 3: Implement adapters as subprocess translators without importing upstream internals; require draft mode; isolate profiles; redact diagnostics; reserve idempotency before page interaction**

- [ ] **Step 4: Run GREEN**

Run: `python -m pytest tests/video_platform/test_upload.py -q`

- [ ] **Step 5: Commit**

```powershell
git add video_platform/upload.py video_platform/uploaders tests/video_platform/test_upload.py
git commit -m "feat: add isolated draft upload adapters"
```

### Task 6: Real platform probes and evidence ledger

**Files:**
- Create: `tests/platform/test_public_downloads.py`
- Create: `docs/mvp/video-platform-io/vertical-slice-brief.md`
- Create: `docs/mvp/video-platform-io/capability-dag.md`
- Create: `docs/mvp/video-platform-io/capability-evidence.md`
- Create: `docs/mvp/video-platform-io/delivery-ledger.md`
- Modify: `TOOLS.md`

**Interfaces:**
- Consumes: complete CLI and adapters.
- Produces: executable evidence per platform and honest delivery classification.

- [ ] **Step 1: Add opt-in platform tests that accept public URLs through environment variables and assert receipt platform, output existence, FFprobe dimensions, and audio stream**

```python
@pytest.mark.platform
@pytest.mark.parametrize("platform", list(Platform))
def test_public_download(platform, platform_url, tmp_path):
    receipt = YtDlpDownloader().download(DownloadRequest(platform, platform_url, tmp_path, 1080))
    assert receipt.status == "ok"
    assert Path(receipt.output_path).exists()
    assert receipt.facts["height"] <= 1080
    assert receipt.facts["has_audio"] is True
```

- [ ] **Step 2: Run platform probes separately and preserve every result, including failures caused by unavailable public URLs or authentication**

Run: `python -m pytest tests/platform/test_public_downloads.py -m platform -v`

- [ ] **Step 3: Run upload dependency doctor and per-platform login-state/draft-boundary probes without clicking public publish**

Run: `python -m video_platform capabilities --refresh --json`

- [ ] **Step 4: Write all four required MVP artifacts with commands, revisions, results, substitutes, decision gates, supported claims, and forbidden claims; update `TOOLS.md` with portable commands**

- [ ] **Step 5: Run full verification and commit**

Run: `python -m pytest tests/video_platform -q`

Run: `python -m pytest tests/platform/test_public_downloads.py -m platform -v`

Run: `python -m video_platform doctor --json`

```powershell
git add tests/platform docs/mvp/video-platform-io TOOLS.md
git commit -m "docs: record video platform capability evidence"
```
