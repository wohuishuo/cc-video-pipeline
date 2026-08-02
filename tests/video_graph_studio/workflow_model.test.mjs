import test from "node:test";
import assert from "node:assert/strict";

import {
  evaluateReadiness,
  groupWorkflowGoals,
  nextZoom,
  projectGraph,
  resolveTemplate,
} from "../../apps/video-graph-studio/web/workflow-model.mjs";


const catalog = [
  {
    templateId: "folder-dub",
    goalId: "dub",
    group: "Create",
    title: "Dub complete videos",
    summary: "Create localized MP4 files.",
    sourceKind: "folder",
    effect: "local-only",
    requirements: ["source-folder", "languages"],
    nodes: [
      { id: "intake", title: "Prepare source", loop: "Source" },
      { id: "verify-source", title: "Verify source", loop: "Source" },
    ],
    edges: [{ source: "intake", target: "verify-source", relationship: "Fact" }],
  },
  {
    templateId: "url-dub",
    goalId: "dub",
    group: "Create",
    title: "Dub complete videos",
    summary: "Download and create localized MP4 files.",
    sourceKind: "url",
    effect: "downloads-source",
    requirements: ["source-url", "languages"],
    nodes: [
      { id: "intake", title: "Prepare source", loop: "Source" },
      { id: "verify-source", title: "Verify source", loop: "Source" },
      { id: "transcribe", title: "Transcribe media", loop: "Transcription" },
    ],
    edges: [
      { source: "intake", target: "verify-source", relationship: "Fact" },
      { source: "verify-source", target: "transcribe", relationship: "Fact" },
    ],
  },
  {
    templateId: "publication-execute",
    goalId: "publication-execute",
    group: "Publish",
    title: "Publish one private video",
    summary: "Execute an exact confirmed plan.",
    sourceKind: "run",
    effect: "contacts-youtube-private",
    requirements: ["plan-run", "confirmation", "vault"],
    nodes: [{ id: "execute-publication", title: "Publish", loop: "Publication" }],
    edges: [],
  },
];


test("groups source variants under one creator outcome", () => {
  const groups = groupWorkflowGoals(catalog);

  assert.deepEqual(groups.map((group) => group.group), ["Create", "Publish"]);
  assert.equal(groups[0].goals.length, 1);
  assert.equal(groups[0].goals[0].goalId, "dub");
  assert.deepEqual(
    groups[0].goals[0].variants.map((variant) => variant.sourceKind),
    ["folder", "url"],
  );
  assert.equal(groups[1].goals[0].effect, "contacts-youtube-private");
});


test("resolves only an advertised goal and source variant", () => {
  assert.equal(resolveTemplate(catalog, "dub", "url").templateId, "url-dub");
  assert.equal(resolveTemplate(catalog, "dub", "creator"), null);
  assert.equal(resolveTemplate(catalog, "missing", "url"), null);
});


test("readiness reports independent connection and input blockers", () => {
  const result = evaluateReadiness({
    connection: { contracts: false, health: true, access: true, catalog: true },
    workflow: catalog[1],
    values: { sourceUrl: "", targetLanguages: [] },
  });

  assert.equal(result.ready, false);
  assert.deepEqual(
    result.checks.filter((check) => check.status === "blocked").map((check) => check.id),
    ["contracts", "source-url", "languages"],
  );
});


test("readiness permits a complete draft and preserves platform effect", () => {
  const result = evaluateReadiness({
    connection: { contracts: true, health: true, access: true, catalog: true },
    workflow: catalog[1],
    values: {
      sourceUrl: "https://www.youtube.com/watch?v=abc123",
      targetLanguages: ["ru-RU"],
    },
  });

  assert.equal(result.ready, true);
  assert.equal(result.effect, "downloads-source");
  assert.equal(result.checks.every((check) => check.status === "ready"), true);
});


test("projects exact graph order and only committed run statuses", () => {
  const workflow = {
    ...catalog[1],
    nodes: Array.from({ length: 10 }, (_, index) => ({
      id: `step-${index + 1}`,
      title: `Step ${index + 1}`,
      loop: index < 2 ? "Source" : "Production",
    })),
  };
  const run = {
    status: "RUNNING",
    steps: [
      { nodeId: "step-1", status: "COMPLETED" },
      { nodeId: "step-2", status: "RUNNING" },
    ],
  };

  const projection = projectGraph(workflow, run);

  assert.equal(projection.length, 10);
  assert.deepEqual(projection.map((node) => node.id), workflow.nodes.map((node) => node.id));
  assert.deepEqual(projection.slice(0, 3).map((node) => node.status), ["COMPLETED", "RUNNING", "WAITING"]);
});


test("zoom uses bounded deterministic steps", () => {
  assert.equal(nextZoom(100, "in"), 110);
  assert.equal(nextZoom(100, "out"), 90);
  assert.equal(nextZoom(140, "in"), 140);
  assert.equal(nextZoom(60, "out"), 60);
});
