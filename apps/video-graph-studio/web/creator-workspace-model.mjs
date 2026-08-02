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
    if (state.catalog && (!state.catalog.complete || state.catalog.truncated)) {
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
    ...common,
    destinationPlans: locales.map((locale) => ({
      locale,
      targets: (state.destinations?.[locale] || []).map(({platform, account}) => ({platform, account})),
    })),
  };
}
