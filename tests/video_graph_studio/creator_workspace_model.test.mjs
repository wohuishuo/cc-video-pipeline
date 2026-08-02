import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCampaignPayload,
  campaignCounts,
  campaignReadiness,
  filterCreatorItems,
  selectVisibleIds,
} from "../../apps/video-graph-studio/web/creator-workspace-model.mjs";


const items = [
  {id: "v3", title: "Factory automation", publishedAt: 300},
  {id: "v2", title: "AI workflow", publishedAt: 200},
  {id: "v1", title: "Camera setup", publishedAt: 100},
];

test("filters creator videos and selects all visible rows without changing order", () => {
  assert.deepEqual(filterCreatorItems(items, "AI").map((row) => row.id), ["v2"]);
  assert.deepEqual(selectVisibleIds(["v1"], filterCreatorItems(items, "factory")), ["v1", "v3"]);
});

test("counts source by language by per-language destinations exactly", () => {
  const counts = campaignCounts(
    ["v3", "v1"],
    ["ru-RU", "en-US"],
    {
      "ru-RU": [{platform: "youtube"}, {platform: "tiktok"}],
      "en-US": [{platform: "youtube"}],
    },
  );
  assert.deepEqual(counts, {videos: 2, localizedVideos: 4, publicationJobs: 6});
});

test("readiness explains missing facts and accepts a complete campaign", () => {
  const state = {
    creatorRunId: "creator-run",
    catalog: {items},
    selectedVideoIds: ["v3"],
    selectedLanguages: ["ru-RU"],
    voices: {"ru-RU": "ru-RU-DmitryNeural"},
    destinations: {"ru-RU": [{platform: "youtube", account: "main"}]},
    translationProvider: {id: "nllb", ready: true, defaultModel: "nllb"},
  };
  assert.deepEqual(campaignReadiness(state), {ready: true, missing: []});
  assert.ok(campaignReadiness({...state, selectedVideoIds: []}).missing.includes("Select at least one video"));
  assert.ok(campaignReadiness({...state, translationProvider: {id: "deepseek", ready: false}}).missing.includes("Configure the selected translation provider"));
});

test("campaign payload omits unselected videos and preserves language routing", () => {
  const payload = buildCampaignPayload({
    creatorRunId: "creator-run",
    selectedVideoIds: ["v3", "v1"],
    selectedLanguages: ["ru-RU", "en-US"],
    voices: {"ru-RU": "ru-voice", "en-US": "en-voice"},
    destinations: {
      "ru-RU": [{platform: "youtube", account: "ru-main"}, {platform: "tiktok", account: "ru-short"}],
      "en-US": [{platform: "youtube", account: "en-main"}],
    },
    translationProvider: {id: "deepseek", ready: true, defaultModel: "deepseek-v4-flash"},
    sourceLanguage: "zh",
    asrModel: "small",
    sourceVolume: 0.08,
  });
  assert.equal(payload.templateId, "creator-campaign");
  assert.deepEqual(payload.selectedVideoIds, ["v3", "v1"]);
  assert.ok(!payload.selectedVideoIds.includes("v2"));
  assert.equal(payload.translationProvider, "deepseek");
  assert.deepEqual(payload.destinationPlans[0], {
    locale: "ru-RU",
    targets: [{platform: "youtube", account: "ru-main"}, {platform: "tiktok", account: "ru-short"}],
  });
});
