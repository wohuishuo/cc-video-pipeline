import test from "node:test";
import assert from "node:assert/strict";

import * as workspaceModel from "../../apps/video-graph-studio/web/creator-workspace-model.mjs";

const {
  buildCampaignPayload,
  campaignCounts,
  campaignReadiness,
  filterCreatorItems,
  launchPresentation,
  selectVisibleIds,
  sourcePresentation,
  stageAction,
} = workspaceModel;


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
  assert.deepEqual(
    campaignReadiness({...state, catalog: {...state.catalog, complete: false, truncated: true}, allowPartialCatalog: true}),
    {ready: true, missing: []},
  );
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
    allowPartialCatalog: true,
  });
  assert.equal(payload.templateId, "creator-campaign");
  assert.deepEqual(payload.selectedVideoIds, ["v3", "v1"]);
  assert.ok(!payload.selectedVideoIds.includes("v2"));
  assert.equal(payload.translationProvider, "deepseek");
  assert.equal(payload.voiceProvider, "edge");
  assert.equal(payload.localOutputRoot, "C:/Videos/Localized");
  assert.equal(payload.allowPartialCatalog, true);
  assert.deepEqual(payload.destinationPlans[0], {
    locale: "ru-RU",
    targets: [{platform: "youtube", account: "ru-main"}, {platform: "tiktok", account: "ru-short"}],
  });
  assert.equal("qwenDevice" in payload, false);
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

test("restores only the committed authentication file reference for discovery retry", () => {
  assert.equal(typeof workspaceModel.authenticationFileFromRun, "function");
  assert.equal(
    workspaceModel.authenticationFileFromRun({parameters: {authenticationFile: " C:/Users/me/cookies.txt "}}),
    "C:/Users/me/cookies.txt",
  );
  assert.equal(workspaceModel.authenticationFileFromRun({parameters: {authenticationFile: null}}), "");
  assert.equal(workspaceModel.authenticationFileFromRun(null), "");
});

test("presents detected account and single-video links differently", () => {
  assert.deepEqual(sourcePresentation({sourceKind: "video", itemCount: 1, creator: {name: "Creator"}}), {
    title: "Creator",
    detail: "已识别为单个视频",
    buttonLabel: "识别链接",
  });
  assert.deepEqual(sourcePresentation({sourceKind: "profile", itemCount: 75, complete: true, truncated: false, creator: {name: "Creator"}}), {
    title: "Creator",
    detail: "75 条视频 · 完整账号清单",
    buttonLabel: "识别链接",
  });
});

test("stage actions name the next decision instead of saying continue", () => {
  assert.deepEqual(stageAction("source", {videoCount: 75}), {
    label: "查看 75 个视频",
    hint: "账号目录已读取，下一步确认要处理的视频。",
  });
  assert.deepEqual(stageAction("translation", {languageCount: 2}), {
    label: "选择配音",
    hint: "已选择 2 种目标语言，下一步为每种语言选择声音。",
  });
  assert.deepEqual(stageAction("source", {videoCount: 1, sourceKind: "video"}), {
    label: "查看 1 个视频",
    hint: "已识别并自动选中单个视频，下一步确认视频信息。",
  });
  assert.deepEqual(stageAction("output", {outputRoot: "C:/Videos"}), {
    label: "检查任务",
    hint: "成片将保存到 C:/Videos，上传平台仍为可选。",
  });
});

test("qwen campaign payload selects automatic GPU resolution explicitly", () => {
  const payload = buildCampaignPayload({
    sourceMode: "creator",
    creatorRunId: "creator-run",
    selectedVideoIds: ["v3"],
    selectedLanguages: ["ru-RU"],
    voices: {"ru-RU": "Ryan"},
    destinations: {},
    translationProvider: {id: "nllb", ready: true, defaultModel: "nllb"},
    voiceProvider: {id: "qwen3", ready: true},
    qwenDevice: "auto",
    localOutputRoot: "C:/Videos/Localized",
  });

  assert.equal(payload.voiceProvider, "qwen3");
  assert.equal(payload.qwenDevice, "auto");
});

test("launch presentation distinguishes blocked ready and running jobs", () => {
  assert.deepEqual(
    launchPresentation({ready: false, missing: ["Select at least one language", "Choose a local output folder"]}, false),
    {
      state: "blocked",
      title: "还差 2 项设置",
      description: "先完成下方检查项，再开始本地处理。",
      buttonLabel: "完成设置后开始",
      action: "blocked",
    },
  );
  assert.deepEqual(launchPresentation({ready: true, missing: []}, false), {
    state: "ready",
    title: "任务可以开始",
    description: "配置完整。系统会逐条处理，并保留已经完成的结果。",
    buttonLabel: "开始本地处理",
    action: "start",
  });
  assert.deepEqual(launchPresentation({ready: true, missing: []}, true), {
    state: "running",
    title: "已有任务正在处理",
    description: "打开进度页查看当前步骤、日志和输出位置。",
    buttonLabel: "查看任务进度",
    action: "activity",
  });
});
