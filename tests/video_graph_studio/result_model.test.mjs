import assert from "node:assert/strict";
import test from "node:test";

import {formatBytes, formatDuration, formatTokens, presentResult} from "../../apps/video-graph-studio/web/result-model.mjs";


test("formats completion metrics without turning missing usage into zero", () => {
  assert.equal(formatBytes(55_964_309, "en-US"), "53.4 MB");
  assert.equal(formatDuration(200, "en-US"), "3m 20s");
  assert.equal(formatTokens(null, "en-US"), "Not reported");
  assert.equal(formatTokens({totalTokens: 12345}, "en-US"), "12,345");
});


test("presents localized completion facts and only previewable videos", () => {
  const result = presentResult(
    {
      elapsedSeconds: 65,
      totalBytes: 1_500_000,
      outputRoot: "C:\\Users\\eugen\\Videos\\run-1",
      reportedUsage: null,
      videos: [
        {id: "one", available: true, targetLanguage: "ru-RU", title: "One", size: 1_500_000},
        {id: "two", available: false, title: "Two", error: "fingerprint mismatch"},
      ],
    },
    "ru-RU",
  );

  assert.equal(result.metrics.elapsed, "1 мин 5 с");
  assert.equal(result.metrics.tokens, "Не предоставлено");
  assert.equal(result.outputRoot, "C:\\Users\\eugen\\Videos\\run-1");
  assert.deepEqual(result.previewableIds, ["one"]);
});
