import assert from "node:assert/strict";
import test from "node:test";

import {projectActivity} from "../../apps/video-graph-studio/web/activity-progress-model.mjs";

function log(sequence, message, seconds = sequence) {
  return {sequence, message, created_at: new Date(Date.UTC(2026, 7, 3, 8, 0, seconds)).toISOString()};
}

test("projects structured creator phases and voice counters", () => {
  const messages = [
    {event: "creator_phase", item: {ordinal: 2, count: 4, id: "v2"}, phase: "download", status: "RUNNING"},
    {event: "creator_phase", item: {ordinal: 2, count: 4, id: "v2"}, phase: "download", status: "COMPLETED"},
    {event: "creator_phase", item: {ordinal: 2, count: 4, id: "v2"}, phase: "voice", status: "RUNNING"},
    {event: "voice_progress", status: "RUNNING", completed: 7, failed: 0, total: 10, reused: 2},
  ];
  const result = projectActivity({status: "RUNNING", logs: messages.map((row, index) => log(index + 1, JSON.stringify(row)))});

  assert.deepEqual(result.item, {ordinal: 2, total: 4, id: "v2"});
  assert.equal(result.phases.find((row) => row.id === "download").status, "COMPLETED");
  assert.deepEqual(
    Object.fromEntries(["completed", "failed", "total", "reused"].map((key) => [key, result.phases.find((row) => row.id === "voice")[key]])),
    {completed: 7, failed: 0, total: 10, reused: 2},
  );
  assert.match(result.rawLogText, /^001  /);
});

test("projects the existing failed legacy run accurately", () => {
  const rows = [
    "Started creator item 1/1: 7666656722269850926",
    '{"resultClass":"COMPLETED","receipt":"intake-receipt.json","manifest":"source-manifest.json","error":null}',
    "[1/1] transcribing media-id",
    "Detected zh; committed 62 segment(s)",
    '{"resultClass":"COMPLETED","receipt":"transcription-receipt.json","manifest":"transcript-manifest.json","error":null}',
    "[1/1] translating ru-RU/media-id",
    "Translated 62/62 segments to ru-RU",
    '{"resultClass":"COMPLETED","receipt":"translation-receipt.json","manifest":"translation-manifest.json","error":null}',
    "[61/62] rendering ru-RU/media-id/61",
    "Synthesized 3.408s with ru-RU-DmitryNeural",
    "[62/62] rendering ru-RU/media-id/62",
    "Synthesized 3.384s with ru-RU-DmitryNeural",
    '{"resultClass":"FAILED","receipt":"voice-receipt.json","manifest":null,"error":"10 clip(s) failed"}',
    "Creator item 7666656722269850926: FAILED",
  ];
  const result = projectActivity({status: "FAILED", logs: rows.map((message, index) => log(index + 1, message))});
  const phases = Object.fromEntries(result.phases.map((row) => [row.id, row]));

  assert.deepEqual(result.item, {ordinal: 1, total: 1, id: "7666656722269850926"});
  assert.equal(phases.download.status, "COMPLETED");
  assert.equal(phases.transcription.status, "COMPLETED");
  assert.equal(phases.translation.status, "COMPLETED");
  assert.equal(phases.voice.status, "FAILED");
  assert.equal(phases.voice.completed, 52);
  assert.equal(phases.voice.total, 62);
  assert.equal(phases.voice.failed, 10);
  assert.equal(phases.composition.status, "PENDING");
  assert.match(result.failure.message, /10.*配音片段/);
});

test("clears an earlier phase failure after a successful retry", () => {
  const rows = [
    {event: "creator_phase", item: {ordinal: 1, count: 1, id: "v1"}, phase: "voice", status: "FAILED", error: "10 clips failed"},
    {event: "creator_phase", item: {ordinal: 1, count: 1, id: "v1"}, phase: "voice", status: "RUNNING"},
    {event: "voice_progress", status: "COMPLETED", completed: 62, failed: 0, total: 62, reused: 54},
    {event: "creator_phase", item: {ordinal: 1, count: 1, id: "v1"}, phase: "voice", status: "COMPLETED"},
  ];
  const result = projectActivity({status: "COMPLETED", logs: rows.map((row, index) => log(index + 1, JSON.stringify(row)))});

  assert.equal(result.phases.find((row) => row.id === "voice").status, "COMPLETED");
  assert.equal(result.failure, null);
});
