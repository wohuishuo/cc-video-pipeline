# Portable Video Platform Download and Upload Design

## Observable result

From a clean checkout on a supported computer, one command can verify and then invoke an independent adapter for YouTube, Bilibili, Douyin, or TikTok. Downloads produce a locally verified video at up to 1080p when the source exposes that quality. Uploads stop at a saved draft or the final publish-confirmation boundary during automated verification.

## Scope

The first release supports:

- public-video download from YouTube, Bilibili, Douyin, and TikTok;
- a requested maximum height of 1080p with audio/video merge and post-download probing;
- optional Netscape cookie files, used only when anonymous extraction is insufficient;
- upload preparation for all four platforms through local authenticated browser profiles or platform credentials;
- dry-run, capability inspection, health checks, structured receipts, and portable configuration;
- Windows PowerShell as the primary launcher, with the Python CLI remaining portable to Linux and macOS.

It does not promise that every public URL exposes 1080p, bypass access controls, publish during automated tests, or make browser sessions portable between machines.

## Chosen approach

Use `yt-dlp` as the shared download engine and vendor `dreammis/social-auto-upload` as a pinned external dependency for upload adapters. Each platform remains an independent vertical slice behind a common CLI contract.

Rejected alternatives:

- four unrelated download/upload command sets: potentially robust but duplicates configuration, receipts, validation, and error handling;
- generic browser-agent clicking for every operation: easy to begin but too brittle for repeatable uploads;
- a single all-platform service owning credentials and jobs: merges independent platform state and makes one failure block the others.

## Command interface

```text
video-platform doctor
video-platform capabilities
video-platform download <platform> <url> [--max-height 1080] [--cookies path]
video-platform upload <platform> <video> --metadata metadata.json --draft
video-platform login <platform> [--profile-dir path]
```

Every command returns a nonzero exit code on failure and writes a JSON receipt containing platform, adapter version, input identity, selected format, output path or draft boundary, timestamps, and verification facts. Secrets and cookie contents never appear in receipts.

## State owners and invariants

| State | Unique owner | Invariant |
| --- | --- | --- |
| platform selection and invocation | CLI coordinator | routes one request; owns no platform session |
| downloaded artifact | platform download job | one successful receipt identifies one probed local file |
| format selection | yt-dlp adapter | never claims 1080p unless the probed output height is 1080 or greater |
| cookie source | credential resolver | absent by default; file is read-only and never copied into the repository |
| authenticated upload session | platform upload adapter | one platform cannot read or mutate another platform's profile |
| upload draft job | platform upload job | idempotency key prevents accidental duplicate submission within the local ledger |
| dependency version | dependency manifest | installs a pinned revision and records its license/source |

## Cookie policy

Anonymous extraction is always attempted first for public videos. Cookies are retried only when the extractor reports authentication, format, age, region, or anti-bot restrictions and a cookie source was supplied. A platform can therefore work without cookies, but the tool must not promise full format availability without testing the specific URL.

Cookie files and browser profiles live outside Git and are referenced through command arguments or environment variables:

```text
VIDEO_PLATFORM_COOKIES_YOUTUBE
VIDEO_PLATFORM_COOKIES_BILIBILI
VIDEO_PLATFORM_COOKIES_DOUYIN
VIDEO_PLATFORM_COOKIES_TIKTOK
VIDEO_PLATFORM_PROFILE_ROOT
```

## Independent platform slices

Each slice implements the same contracts but is tested separately:

1. URL ownership validation.
2. Anonymous metadata/format query.
3. Optional authenticated retry.
4. Download or draft-upload command.
5. Artifact/draft verification.
6. Receipt emission and cleanup on partial failure.

YouTube, Bilibili, Douyin, and TikTok have separate capability statuses. The aggregate command never converts three passing platforms into a claim that all four pass.

## Capability DAG

```text
Pinned dependency manifest
  -> Adapter process runner
  -> Receipt and artifact verifier
  -> Platform download adapter (x4)
  -> Platform upload adapter (x4)
  -> Portable CLI coordinator
  -> Aggregate capability report
```

Edges are typed as follows:

- dependency manifest `Factory` adapter process runner;
- process runner `Adapter` platform adapters;
- platform adapters `Fact` receipts;
- receipts `Query` artifact verifier;
- CLI coordinator `Command` one selected adapter;
- verified receipts `Projection` aggregate capability report.

The lowest unproven capability is the pinned dependency manifest plus portable process runner. Real upload execution is blocked by the decision gate of an authenticated user account, but login detection and draft-boundary behavior can be verified without public publication.

## Failure handling

- Unsupported URL: fail before invoking a downloader.
- No 1080p format: download the best format not exceeding 1080p and record the actual height; never label it 1080p.
- Cookie absent: retain the anonymous error and give the exact optional retry command.
- Cookie expired: report authentication failure without printing cookie data.
- Interrupted download: use a job directory and keep resumable partial files; no success receipt.
- Upload page/API changed: fail that platform only and retain diagnostics/screenshots outside credential storage.
- Duplicate upload request: require a new idempotency key or an explicit override; automated tests never override.

## Verification

Automated tests cover URL routing, optional-cookie fallback, format selection, receipt redaction, idempotency, failure cleanup, and adapter isolation. Platform verification uses one public test URL per platform for metadata and a bounded sample download, followed by FFprobe checks. Upload verification checks dependency startup, login-state detection, file selection, metadata filling, and arrival at draft/final-confirmation state. It does not click the final public-publish control.

## Delivery levels

- A platform is `DOMAIN_VERIFIED` when its contracts pass with fake external processes and adjacent real receipt verification.
- It is `PLATFORM_INTEGRATED` only after a real URL download or authenticated draft upload succeeds on that platform.
- It is not `PRODUCTION_VERIFIED` without durability, recovery, concurrency, security, monitoring, and repeated operational evidence.
