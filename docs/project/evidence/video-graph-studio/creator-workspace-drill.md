# Creator Campaign Workspace browser drill

Date: 2026-08-02. Surface: current loopback launcher at `http://127.0.0.1:8765/` in the Codex in-app browser.

## Live facts

- Creator Discovery run `29f174aa-7e6b-4271-a1a4-a5e6ae7f2778` completed both owner steps against the supplied Douyin profile.
- The verified catalog projected three real items from manifest SHA-256 `438f4e329ff1b34a1372071a040dafc7739102e44fc5295d4c6817bcc4fa9a6a` without downloading media.
- The Videos stage displayed three real titles, stable IDs, dates and truthful `UNKNOWN_ASR` subtitle badges.
- Select Visible chose all three items. The Languages stage displayed 20 rows and enabled independent voices for Russian and English.
- Switching to DeepSeek displayed `Setup required` because `DEEPSEEK_API_KEY` was absent; switching back to local NLLB restored a ready preflight.
- Destination routing accepted Russian to YouTube `ru-main` plus TikTok `ru-short`, and English to YouTube `en-main`. Account text survived later platform selection after the input-state repair.
- Review reported exactly 3 source videos, 6 localized videos and 9 publication routes. Preflight enabled Start Campaign.
- Desktop width had zero document overflow. A temporary 390 x 844 mobile viewport also had zero document overflow, a sticky horizontal stage rail and a full-width footer. The viewport was reset afterward.
- Browser console error count was zero.

## Effect boundary

The browser deliberately did not press Start Campaign because that would begin a multi-video download, ASR, translation, voice and encode workload. Selection and request construction are domain verified; the live creator discovery is platform integrated. YouTube routes are labeled `READY_PRIVATE` but still require a separate credential-confirmed publication execution. Bilibili, Douyin and TikTok routes are labeled `PLAN_ONLY`; no upload claim is made.
