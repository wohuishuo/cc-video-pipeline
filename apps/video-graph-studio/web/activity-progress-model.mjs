const PHASES = [
  ["download", "下载"],
  ["transcription", "语音转文字"],
  ["translation", "翻译"],
  ["voice", "配音"],
  ["composition", "字幕与视频合成"],
];

function emptyPhase([id, label]) {
  return {id, label, status: "PENDING", completed: 0, failed: 0, total: 0, reused: 0, percent: 0, elapsedSeconds: null};
}

function parseObject(message) {
  const value = String(message || "").trim();
  if (!value.startsWith("{")) return null;
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function timestamp(row) {
  const value = Date.parse(row?.created_at || row?.createdAt || "");
  return Number.isFinite(value) ? value : null;
}

function finishPercent(phase) {
  if (phase.total > 0) phase.percent = Math.max(0, Math.min(100, Math.round(100 * phase.completed / phase.total)));
  else if (phase.status === "COMPLETED") phase.percent = 100;
  else if (phase.status === "RUNNING") phase.percent = 5;
}

export function projectActivity(run) {
  const logs = [...(run?.logs || [])].sort((a, b) => Number(a.sequence || 0) - Number(b.sequence || 0));
  const phases = PHASES.map(emptyPhase);
  const byId = Object.fromEntries(phases.map((row) => [row.id, row]));
  const starts = {};
  let item = null;
  let failure = null;
  let activeLegacyPhase = null;
  let voiceTotal = 0;
  let voiceFailureCount = 0;

  function updatePhase(id, status, row) {
    const phase = byId[id];
    if (!phase) return;
    phase.status = status;
    if (status === "COMPLETED" && failure?.phase === id) failure = null;
    const at = timestamp(row);
    if (status === "RUNNING" && starts[id] == null) starts[id] = at;
    if (["COMPLETED", "FAILED"].includes(status) && starts[id] != null && at != null) {
      phase.elapsedSeconds = Math.max(0, Math.round((at - starts[id]) / 100) / 10);
    }
  }

  for (const row of logs) {
    const message = String(row.message || "");
    const object = parseObject(message);
    if (object?.event === "creator_phase" && byId[object.phase]) {
      const sourceItem = object.item && typeof object.item === "object" ? object.item : {};
      item = {
        ordinal: Number(sourceItem.ordinal || item?.ordinal || 0),
        total: Number(sourceItem.count || item?.total || 0),
        id: String(sourceItem.id || item?.id || ""),
      };
      updatePhase(object.phase, String(object.status || "RUNNING"), row);
      if (object.status === "FAILED") failure = {phase: object.phase, message: String(object.error || `${byId[object.phase].label}失败`)};
      activeLegacyPhase = object.phase;
      continue;
    }
    if (object?.event === "voice_progress") {
      const phase = byId.voice;
      phase.completed = Number(object.completed || 0);
      phase.failed = Number(object.failed || 0);
      phase.total = Number(object.total || 0);
      phase.reused = Number(object.reused || 0);
      updatePhase("voice", String(object.status || "RUNNING"), row);
      if (phase.status === "FAILED") failure = {phase: "voice", message: `${phase.failed} 个配音片段失败，可仅重试失败片段。`};
      activeLegacyPhase = "voice";
      continue;
    }

    let match = message.match(/^Started creator item (\d+)\/(\d+): (.+)$/);
    if (match) item = {ordinal: Number(match[1]), total: Number(match[2]), id: match[3]};
    if (/transcribing /i.test(message)) { activeLegacyPhase = "transcription"; updatePhase("transcription", "RUNNING", row); }
    if (/translating /i.test(message)) { activeLegacyPhase = "translation"; updatePhase("translation", "RUNNING", row); }
    match = message.match(/Translated (\d+)\/(\d+) segments/i);
    if (match) {
      const phase = byId.translation;
      phase.completed = Number(match[1]); phase.total = Number(match[2]);
      updatePhase("translation", phase.completed >= phase.total ? "COMPLETED" : "RUNNING", row);
    }
    match = message.match(/^\[(\d+)\/(\d+)\] (?:rendering|reused) /i);
    if (match) {
      voiceTotal = Math.max(voiceTotal, Number(match[2]));
      activeLegacyPhase = "voice";
      byId.voice.total = voiceTotal;
      updatePhase("voice", "RUNNING", row);
    }
    if (/localization/i.test(message) && !/creator-batch/i.test(message)) {
      activeLegacyPhase = "composition";
    }
    if (object?.resultClass) {
      const receipt = String(object.receipt || "").toLowerCase();
      let phase = activeLegacyPhase;
      if (receipt.includes("intake-receipt")) phase = "download";
      else if (receipt.includes("transcription-receipt")) phase = "transcription";
      else if (receipt.includes("translation-receipt")) phase = "translation";
      else if (receipt.includes("voice-receipt")) phase = "voice";
      else if (receipt.includes("localization-receipt")) phase = "composition";
      if (phase && ["COMPLETED", "DUPLICATE_COMPLETED"].includes(object.resultClass)) updatePhase(phase, "COMPLETED", row);
      if (phase && object.resultClass === "FAILED") {
        updatePhase(phase, "FAILED", row);
        const clipMatch = String(object.error || "").match(/(\d+) clip\(s\) failed/i);
        if (phase === "voice" && clipMatch) {
          voiceFailureCount = Number(clipMatch[1]);
          byId.voice.failed = voiceFailureCount;
          byId.voice.total = voiceTotal || byId.voice.total;
          byId.voice.completed = Math.max(0, byId.voice.total - voiceFailureCount);
          failure = {phase: "voice", message: `${voiceFailureCount} 个配音片段失败，可仅重试失败片段。`};
        } else {
          failure = {phase, message: String(object.error || `${byId[phase].label}失败`)};
        }
      }
    }
  }

  if (!logs.length && run?.status === "COMPLETED") phases.forEach((phase) => { phase.status = "COMPLETED"; });
  phases.forEach(finishPercent);
  return {
    item,
    phases,
    failure,
    rawLogText: logs.map((row) => `${String(row.sequence ?? "").padStart(3, "0")}  ${row.message ?? ""}`).join("\n"),
  };
}
