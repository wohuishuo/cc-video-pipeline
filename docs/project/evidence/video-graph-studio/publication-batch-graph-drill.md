# Publication Batch Graph Drill

## Scope

This drill verifies browser and loopback-API composition for the independent Publication Batch capability. It deliberately stops before execution: no source download, ASR, translation, speech synthesis, media render, upload or platform contact occurred.

## Environment

- Date: 2026-08-02
- Binding: `127.0.0.1:8878`
- Mode: anonymous local Studio with an isolated data root
- Browser viewport: 1280 × 720

## Browser evidence

The browser selected `Folder+Release` and exposed:

- source folder, source language, ASR model/device and translation controls;
- metadata-template path, account label and bounded YouTube credential ID reference;
- YouTube, Bilibili, Douyin and TikTok target selection;
- RU, EN and KK language selection;
- `0 / 12` progress, a visible Run button and the Publication Batch owner in the inspector.

The Run button remained inside the viewport and the browser console reported no errors.

## API evidence

Loopback API command `CMD-RUN-CREATE` admitted run `86d98a18-bcdf-4af6-bc1d-95ccedb9a091` with Graph ID `folder-release` and status `CREATED`. The immutable Graph contained exactly these twelve nodes:

1. `intake`
2. `verify-source`
3. `transcribe`
4. `verify-transcript`
5. `translate`
6. `verify-translation`
7. `render-voice`
8. `verify-voice`
9. `localize-video`
10. `verify-localization`
11. `plan-publication-batch`
12. `verify-publication-batch`

The admitted parameters preserved ordered languages `ru-RU,en-US`, ordered targets `youtube,tiktok`, exact account coverage, the `youtube-main` credential reference and `public: false`. Every step remained `PENDING`; the run was not submitted to the durable start queue.

## Claim boundary

This is platform-integrated browser/API composition evidence for run admission and projection, plus domain evidence for the underlying adapters. It is not evidence of a started multi-derivative Release run or a real authenticated publication.
