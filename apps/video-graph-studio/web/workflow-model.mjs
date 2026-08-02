const GROUP_ORDER = ["Prepare", "Create", "Batch", "Publish", "Account"];
const ZOOM_STEPS = [60, 75, 90, 100, 110, 125, 140];

const REQUIREMENTS = {
  "source-folder": ["Source folder", (values) => Boolean(values.sourceRoot?.trim())],
  "source-url": ["Supported social URL", (values) => isSupportedUrl(values.sourceUrl)],
  languages: ["At least one target language", (values) => Array.isArray(values.targetLanguages) && values.targetLanguages.length > 0],
  asr: ["Speech recognition settings", (values) => Boolean(values.asrModel && values.asrDevice && values.sourceLanguage)],
  translation: ["Translation settings", (values) => Boolean(values.translationDevice) && Number(values.translationBatchSize) > 0],
  voices: ["One voice per language", (values) => voicesCoverLanguages(values.targetLanguages, values.targetVoices)],
  "source-volume": ["Source audio mix", (values) => Number(values.sourceVolume) >= 0 && Number(values.sourceVolume) <= 1],
  voice: ["Voice", (values) => Boolean(values.voice?.trim())],
  platforms: ["At least one output target", (values) => Array.isArray(values.platforms) && values.platforms.length > 0],
  "metadata-template": ["Metadata template JSON", (values) => Boolean(values.metadataTemplatePath?.trim())],
  "release-account": ["Release account label", (values) => Boolean(values.releaseAccount?.trim())],
  "release-targets": ["At least one release target", (values) => Array.isArray(values.releaseTargets) && values.releaseTargets.length > 0],
  "creator-options": ["Creator batch limit", (values) => Number.isInteger(Number(values.maxItems)) && Number(values.maxItems) >= 0],
  video: ["Finished video", (values) => Boolean(values.videoPath?.trim())],
  metadata: ["Metadata JSON", (values) => Boolean(values.metadataPath?.trim())],
  "publication-targets": ["At least one publication target", (values) => Array.isArray(values.publicationTargets) && values.publicationTargets.length > 0],
  account: ["Publication account", (values) => Boolean(values.account?.trim())],
  "plan-run": ["Completed publication-plan run", (values) => Boolean(values.planRunId?.trim())],
  "release-run": ["Completed Release-plan run", (values) => Boolean(values.releasePlanRunId?.trim())],
  confirmation: ["Exact 64-character SHA-256", (values) => /^[0-9a-f]{64}$/i.test(values.confirmation || "")],
  vault: ["Existing Credential Vault", (values) => Boolean(values.credentialVaultPath?.trim())],
  "client-config": ["Google desktop client JSON", (values) => Boolean(values.clientConfigPath?.trim())],
  "vault-destination": ["Credential Vault destination", (values) => Boolean(values.credentialVaultPath?.trim())],
  credential: ["Credential ID", (values) => /^[a-z0-9][a-z0-9-]{0,62}$/.test(values.credentialId || "")],
  label: ["Account label", (values) => Boolean(values.label?.trim())],
};

function isSupportedUrl(value) {
  try {
    const url = new URL(value);
    const host = url.hostname.toLowerCase();
    return url.protocol === "https:" && ["youtube.com", "youtu.be", "bilibili.com", "b23.tv", "douyin.com", "tiktok.com"]
      .some((suffix) => host === suffix || host.endsWith(`.${suffix}`));
  } catch {
    return false;
  }
}

function voicesCoverLanguages(languages, voices) {
  return Array.isArray(languages) && languages.length > 0 && voices && typeof voices === "object"
    && languages.every((language) => typeof voices[language] === "string" && voices[language].trim());
}

export function groupWorkflowGoals(catalog) {
  const groups = new Map();
  for (const workflow of catalog) {
    if (!groups.has(workflow.group)) groups.set(workflow.group, new Map());
    const goals = groups.get(workflow.group);
    if (!goals.has(workflow.goalId)) {
      goals.set(workflow.goalId, {
        goalId: workflow.goalId,
        title: workflow.title,
        summary: workflow.summary,
        effect: workflow.effect,
        variants: [],
      });
    }
    goals.get(workflow.goalId).variants.push({
      templateId: workflow.templateId,
      sourceKind: workflow.sourceKind,
      effect: workflow.effect,
    });
  }
  return [...groups.entries()]
    .sort(([left], [right]) => GROUP_ORDER.indexOf(left) - GROUP_ORDER.indexOf(right))
    .map(([group, goals]) => ({ group, goals: [...goals.values()] }));
}

export function resolveTemplate(catalog, goalId, sourceKind) {
  return catalog.find((workflow) => workflow.goalId === goalId && workflow.sourceKind === sourceKind) || null;
}

export function evaluateReadiness({ connection, workflow, values }) {
  const checks = [
    connectionCheck("contracts", "Client contract", connection.contracts),
    connectionCheck("health", "Studio service", connection.health),
    connectionCheck("access", "Workspace access", connection.access),
    connectionCheck("catalog", "Workflow catalog", connection.catalog),
  ];
  if (!workflow) {
    checks.push({ id: "workflow", label: "Workflow outcome", status: "blocked", detail: "Choose an outcome and source." });
  } else {
    for (const requirement of workflow.requirements || []) {
      const contract = REQUIREMENTS[requirement];
      const valid = contract ? Boolean(contract[1](values || {})) : false;
      checks.push({
        id: requirement,
        label: contract?.[0] || requirement,
        status: valid ? "ready" : "blocked",
        detail: valid ? "Ready" : "Required before this Graph can run.",
      });
    }
  }
  return {
    ready: Boolean(workflow) && checks.every((check) => check.status === "ready"),
    effect: workflow?.effect || "none",
    checks,
  };
}

function connectionCheck(id, label, value) {
  return {
    id,
    label,
    status: value ? "ready" : "blocked",
    detail: value ? "Ready" : "Reconnect to continue.",
  };
}

export function projectGraph(workflow, run) {
  const statuses = new Map((run?.steps || []).map((step) => [step.nodeId, step.status]));
  return (workflow?.nodes || []).map((node, index) => ({
    ...node,
    step: node.step || index + 1,
    status: statuses.get(node.id) || "WAITING",
  }));
}

export function nextZoom(current, direction) {
  const nearest = ZOOM_STEPS.reduce((best, value) => (
    Math.abs(value - current) < Math.abs(best - current) ? value : best
  ), ZOOM_STEPS[0]);
  const index = ZOOM_STEPS.indexOf(nearest);
  if (direction === "in") return ZOOM_STEPS[Math.min(index + 1, ZOOM_STEPS.length - 1)];
  if (direction === "out") return ZOOM_STEPS[Math.max(index - 1, 0)];
  return nearest;
}
