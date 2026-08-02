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
    sourceMode: "creator",
    creatorRunId: "creator-run",
    catalog: {items, complete: true, truncated: false},
    selectedVideoIds: ["v3"],
    selectedLanguages: ["ru-RU"],
    voices: {"ru-RU": "ru-RU-DmitryNeural"},
    destinations: {},
    translationProvider: {id: "nllb", ready: true, defaultModel: "nllb"},
    voiceProvider: {id: "edge", ready: true},
    localOutputRoot: "C:/Videos/Localized",
  };
  assert.deepEqual(campaignReadiness(state), {ready: true, missing: []});
  assert.ok(campaignReadiness({...state, selectedVideoIds: []}).missing.includes("Select at least one video"));
  assert.ok(campaignReadiness({...state, translationProvider: {id: "deepseek", ready: false}}).missing.includes("Configure the selected translation provider"));
  assert.ok(campaignReadiness({...state, catalog: {...state.catalog, complete: false, truncated: true}}).missing.includes("Load the complete creator catalog"));
  assert.ok(campaignReadiness({...state, voiceProvider: {id: "qwen3", ready: false}}).missing.includes("Configure the selected voice provider"));
  assert.ok(campaignReadiness({...state, voiceProvider: {id: "qwen3", ready: true, supportedLocales: ["en-US"]}}).missing.includes("Selected voice provider does not support ru-RU"));
});

test("campaign payload omits unselected videos and preserves language routing", () => {
  const payload = buildCampaignPayload({
    sourceMode: "creator",
    creatorRunId: "creator-run",
    selectedVideoIds: ["v3", "v1"],
    selectedLanguages: ["ru-RU", "en-US"],
    voices: {"ru-RU": "ru-voice", "en-US": "en-voice"},
    destinations: {
      "ru-RU": [{platform: "youtube", account: "ru-main"}, {platform: "tiktok", account: "ru-short"}],
      "en-US": [{platform: "youtube", account: "en-main"}],
    },
    translationProvider: {id: "deepseek", ready: true, defaultModel: "deepseek-v4-flash"},
    voiceProvider: {id: "edge", ready: true},
    localOutputRoot: "C:/Videos/Localized",
    sourceLanguage: "zh",
    asrModel: "small",
    sourceVolume: 0.08,
  });
  assert.equal(payload.templateId, "creator-campaign");
  assert.deepEqual(payload.selectedVideoIds, ["v3", "v1"]);
  assert.ok(!payload.selectedVideoIds.includes("v2"));
  assert.equal(payload.translationProvider, "deepseek");
  assert.equal(payload.voiceProvider, "edge");
  assert.equal(payload.localOutputRoot, "C:/Videos/Localized");
  assert.deepEqual(payload.destinationPlans[0], {
    locale: "ru-RU",
    targets: [{platform: "youtube", account: "ru-main"}, {platform: "tiktok", account: "ru-short"}],
  });
});

test("local folder payload completes locally with zero publication routes", () => {
  const state = {
    sourceMode: "folder",
    localFolder: "C:/Videos/Input",
    localVideos: [{path: "C:/Videos/Input/a.mp4"}, {path: "C:/Videos/Input/b.mp4"}],
    selectedLanguages: ["ru-RU"],
    translationProvider: {id: "nllb", ready: true, defaultModel: "nllb"},
    voiceProvider: {id: "original", ready: true},
    voices: {"ru-RU": "original-audio"},
    destinations: {},
    localOutputRoot: "C:/Videos/Output",
  };

  assert.deepEqual(campaignReadiness(state), {ready: true, missing: []});
  assert.deepEqual(buildCampaignPayload(state), {
    templateId: "folder-dub",
    sourceRoot: "C:/Videos/Input",
    sourceLanguage: "auto",
    asrModel: "small",
    asrDevice: "auto",
    asrComputeType: "default",
    targetLanguages: ["ru-RU"],
    translationProvider: "nllb",
    translationModel: "nllb",
    translationDevice: "auto",
    translationBatchSize: 8,
    voiceProvider: "original",
    targetVoices: {"ru-RU": "original-audio"},
    sourceVolume: 1,
    localOutputRoot: "C:/Videos/Output",
  });
});
