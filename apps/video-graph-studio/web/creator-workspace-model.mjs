export function filterCreatorItems(items, query) {
  const needle = String(query || "").trim().toLocaleLowerCase();
  if (!needle) return [...(items || [])];
  return (items || []).filter((item) =>
    [item.id, item.title].some((value) => String(value || "").toLocaleLowerCase().includes(needle)),
  );
}

export function selectVisibleIds(selectedIds, visibleItems) {
  const selected = new Set(selectedIds || []);
  for (const item of visibleItems || []) selected.add(item.id);
  return [...selected];
}

export function authenticationFileFromRun(run) {
  const value = run?.parameters?.authenticationFile;
  return typeof value === "string" ? value.trim() : "";
}

export function stageAction(stage, facts = {}) {
  const videoCount = Number(facts.videoCount || 0);
  const languageCount = Number(facts.languageCount || 0);
  switch (stage) {
    case "source":
      return {
        label: videoCount ? `查看 ${videoCount} 个视频` : "查看视频",
        hint: videoCount ? "账号目录已读取，下一步确认要处理的视频。" : "选择账号或本地视频文件夹。",
      };
    case "videos":
      return {
        label: "选择翻译语言",
        hint: videoCount ? `已选择 ${videoCount} 个视频，下一步选择目标语言。` : "先选择至少一个视频。",
      };
    case "translation":
      return {
        label: "选择配音",
        hint: languageCount ? `已选择 ${languageCount} 种目标语言，下一步为每种语言选择声音。` : "先选择至少一种目标语言。",
      };
    case "voice":
      return {label: "设置输出", hint: facts.voiceName ? `已选择 ${facts.voiceName}，下一步确认保存位置。` : "选择配音方式。"};
    case "output":
      return {
        label: "检查任务",
        hint: facts.outputRoot ? `成片将保存到 ${facts.outputRoot}，上传平台仍为可选。` : "选择本地输出文件夹。",
      };
    case "review":
      return facts.hasActiveRun
        ? {label: "查看任务进度", hint: "当前任务正在执行。"}
        : {label: "开始处理", hint: facts.ready ? "配置完整，可以开始本地处理。" : "完成检查项后即可开始。"};
    case "activity":
      return {label: "返回任务检查", hint: "运行进度和持久日志会自动更新。"};
    default:
      return {label: "下一步", hint: ""};
  }
}

export function launchPresentation(readiness, hasActiveRun) {
  if (hasActiveRun) {
    return {
      state: "running",
      title: "已有任务正在处理",
      description: "打开进度页查看当前步骤、日志和输出位置。",
      buttonLabel: "查看任务进度",
      action: "activity",
    };
  }
  if (readiness?.ready) {
    return {
      state: "ready",
      title: "任务可以开始",
      description: "配置完整。系统会逐条处理，并保留已经完成的结果。",
      buttonLabel: "开始本地处理",
      action: "start",
    };
  }
  const missingCount = readiness?.missing?.length || 0;
  return {
    state: "blocked",
    title: `还差 ${missingCount} 项设置`,
    description: "先完成下方检查项，再开始本地处理。",
    buttonLabel: "完成设置后开始",
    action: "blocked",
  };
}

export function campaignCounts(selectedVideoIds, selectedLanguages, destinations) {
  const videos = new Set(selectedVideoIds || []).size;
  const languages = new Set(selectedLanguages || []).size;
  const targetCount = [...new Set(selectedLanguages || [])]
    .reduce((sum, locale) => sum + (destinations?.[locale] || []).length, 0);
  return {
    videos,
    localizedVideos: videos * languages,
    publicationJobs: videos * targetCount,
  };
}

export function campaignReadiness(state) {
  const missing = [];
  const sourceMode = state.sourceMode || "creator";
  if (sourceMode === "folder") {
    if (!String(state.localFolder || "").trim() || !state.localVideos?.length) {
      missing.push("Choose a local folder with videos");
    }
  } else {
    if (!state.creatorRunId || !state.catalog?.items?.length) missing.push("Discover a creator account");
    if (state.catalog && (!state.catalog.complete || state.catalog.truncated) && !state.allowPartialCatalog) {
      missing.push("Load the complete creator catalog");
    }
    if (!state.selectedVideoIds?.length) missing.push("Select at least one video");
  }
  if (!state.selectedLanguages?.length) missing.push("Select at least one language");
  if (!state.translationProvider?.ready) missing.push("Configure the selected translation provider");
  if (!state.voiceProvider?.ready) missing.push("Configure the selected voice provider");
  if (!String(state.localOutputRoot || "").trim()) missing.push("Choose a local output folder");
  for (const locale of state.selectedLanguages || []) {
    if (state.voiceProvider?.supportedLocales?.length && !state.voiceProvider.supportedLocales.includes(locale)) {
      missing.push(`Selected voice provider does not support ${locale}`);
    }
    if (!String(state.voices?.[locale] || "").trim()) missing.push(`Choose a voice for ${locale}`);
    const targets = state.destinations?.[locale] || [];
    if (targets.some((target) => !target.platform || !String(target.account || "").trim())) {
      missing.push(`Complete destination accounts for ${locale}`);
    }
  }
  return {ready: missing.length === 0, missing};
}

export function buildCampaignPayload(state) {
  const locales = [...new Set(state.selectedLanguages || [])];
  const common = {
    sourceLanguage: state.sourceLanguage || "auto",
    asrModel: state.asrModel || "small",
    asrDevice: state.asrDevice || "auto",
    asrComputeType: state.asrComputeType || "default",
    targetLanguages: locales,
    translationProvider: state.translationProvider.id,
    translationModel: state.translationProvider.defaultModel,
    translationDevice: "auto",
    translationBatchSize: 8,
    voiceProvider: state.voiceProvider?.id || "edge",
    targetVoices: Object.fromEntries(locales.map((locale) => [locale, state.voices[locale]])),
    sourceVolume: state.voiceProvider?.id === "original" ? 1 : Number(state.sourceVolume ?? 0.12),
    localOutputRoot: String(state.localOutputRoot || ""),
  };
  if ((state.sourceMode || "creator") === "folder") {
    return {
      templateId: "folder-dub",
      sourceRoot: state.localFolder,
      ...common,
    };
  }
  return {
    templateId: "creator-campaign",
    creatorRunId: state.creatorRunId,
    selectedVideoIds: [...new Set(state.selectedVideoIds || [])],
    allowPartialCatalog: state.allowPartialCatalog === true,
    ...common,
    destinationPlans: locales.map((locale) => ({
      locale,
      targets: (state.destinations?.[locale] || []).map(({platform, account}) => ({platform, account})),
    })),
  };
}
