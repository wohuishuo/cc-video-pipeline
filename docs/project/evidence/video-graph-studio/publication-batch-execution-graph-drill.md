# Publication Batch Execution Graph drill

## Objective

Prove that the local browser can select a completed Release fact, bind the exact Publication Batch Plan SHA and create the independent execution Graph without widening the page or contacting a platform.

## Environment

- Date: 2026-08-02
- Studio: loopback `http://127.0.0.1:8876`
- Viewport: 1280 x 720
- Temporary data root: `%LOCALAPPDATA%\Temp\video-graph-studio-publication-batch-drill`
- Completed Release run: `5a9643d9-60ce-4e28-84f4-6ce03f512269`
- Publication Batch Plan SHA-256: `9450c2cc7e5842d1494e16bb87338f57d8da4247c4fdb77867704b9fbc5049a5`

## Observations

1. Selecting **Release Execute** automatically filled the latest eligible Release run and exact batch-plan SHA.
2. The health projection remained `System ready`; the credential, Vault and confirmation controls were visible; the Run action was enabled.
3. The canvas rendered exactly `Verified Release plan`, `Execute serial private release` and `Verify every publication` presentation roles over the two executable owner nodes.
4. The API admitted run `b90cd6af-9284-49bd-a3b8-c9bc07718a40` as `CREATED` with graph fingerprint `88420e16d427324b348a72265bb2149438ffa651b4c81bd718d98115c577f1ec`.
5. The document width remained exactly 1280 pixels. The 1,782-pixel workflow choice row scrolled inside its 1,248-pixel container instead of widening the document.

## Safety boundary

The admitted run was deliberately not started. No credential was injected and no YouTube, Bilibili, Douyin or TikTok endpoint was contacted. This is browser and Graph-composition evidence, not authenticated publication evidence.
