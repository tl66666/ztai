const assert = require("node:assert/strict");
const test = require("node:test");

const InterviewMedia = require("../../static/js/interview_media.js");

function undecodableBlob() {
  return { arrayBuffer: async () => new ArrayBuffer(8) };
}

function contextClass({ decodeError = null, duration = 2.25 } = {}) {
  return class FakeAudioContext {
    static instances = [];

    constructor() {
      this.closed = false;
      this.constructor.instances.push(this);
    }

    async decodeAudioData() {
      if (decodeError) throw decodeError;
      return {
        duration,
        getChannelData: () => new Float32Array([0, 0.1, -0.2, 0.5]),
      };
    }

    async close() {
      this.closed = true;
    }
  };
}

test("upload decode failure never derives duration from recording start time", async () => {
  const FailingContext = contextClass({ decodeError: new Error("invalid audio") });
  const metrics = await InterviewMedia.computeAudioMetrics(undecodableBlob(), {
    source: "upload",
    startedAt: 1,
    now: 9_000_000,
    AudioContext: FailingContext,
  });

  assert.equal(metrics.duration_seconds, null);
  assert.equal(FailingContext.instances[0].closed, true);
});

test("recording fallback rejects missing or implausibly old start times", async () => {
  const noContext = null;
  const missing = await InterviewMedia.computeAudioMetrics(undecodableBlob(), {
    source: "recording", startedAt: 0, now: 10_000, AudioContext: noContext,
  });
  const old = await InterviewMedia.computeAudioMetrics(undecodableBlob(), {
    source: "recording", startedAt: 1, now: 86_400_001, AudioContext: noContext,
  });
  assert.equal(missing.duration_seconds, null);
  assert.equal(old.duration_seconds, null);
});

test("audio context closes after successful decoding", async () => {
  const SuccessfulContext = contextClass({ duration: 2.25 });
  const metrics = await InterviewMedia.computeAudioMetrics(undecodableBlob(), {
    source: "upload", AudioContext: SuccessfulContext,
  });
  assert.equal(metrics.duration_seconds, 2.25);
  assert.equal(SuccessfulContext.instances[0].closed, true);
});

test("shared audio decoding closes its context on success and failure", async () => {
  const SuccessfulContext = contextClass({ duration: 1 });
  const decoded = await InterviewMedia.decodeAudioBlob(undecodableBlob(), SuccessfulContext);
  assert.equal(decoded.duration, 1);
  assert.equal(SuccessfulContext.instances[0].closed, true);

  const FailingContext = contextClass({ decodeError: new Error("decode failed") });
  await assert.rejects(
    InterviewMedia.decodeAudioBlob(undecodableBlob(), FailingContext),
    /decode failed/,
  );
  assert.equal(FailingContext.instances[0].closed, true);
});

test("stale recorder stop cannot publish over a newer recording", async () => {
  const callbacks = new Map();
  const published = [];
  let activeToken = 1;
  const makeRecorder = (name) => ({
    mimeType: "audio/webm",
    set ondataavailable(value) { callbacks.set(`${name}:data`, value); },
    set onstop(value) { callbacks.set(`${name}:stop`, value); },
    set onerror(value) { callbacks.set(`${name}:error`, value); },
  });
  const stream = () => ({ getTracks: () => [{ stop() {} }] });

  InterviewMedia.bindRecorderSession({
    recorder: makeRecorder("old"), stream: stream(), token: 1,
    isCurrent: (token) => token === activeToken,
    createBlob: (chunks, options) => ({ chunks, type: options.type }),
    computeMetrics: async () => ({ duration_seconds: 1 }),
    publish: (value) => published.push(value),
  });
  assert.equal(typeof callbacks.get("old:data"), "function");
  assert.equal(typeof callbacks.get("old:stop"), "function");
  activeToken = 2;
  InterviewMedia.bindRecorderSession({
    recorder: makeRecorder("new"), stream: stream(), token: 2,
    isCurrent: (token) => token === activeToken,
    createBlob: (chunks, options) => ({ chunks, type: options.type }),
    computeMetrics: async () => ({ duration_seconds: 2 }),
    publish: (value) => published.push(value),
  });
  assert.equal(typeof callbacks.get("new:data"), "function");
  assert.equal(typeof callbacks.get("new:stop"), "function");
  callbacks.get("old:data")({ data: { size: 1, id: "old" } });
  callbacks.get("new:data")({ data: { size: 1, id: "new" } });
  await callbacks.get("old:stop")();
  await callbacks.get("new:stop")();

  assert.equal(published.length, 1);
  assert.equal(published[0].blob.chunks[0].id, "new");
});

test("speech interim replacements do not append duplicate transcripts", () => {
  const session = InterviewMedia.createSpeechTranscriptSession("原回答：");
  const interim = (text, isFinal = false) => ({ 0: { transcript: text }, isFinal });

  assert.equal(session.update({ results: [interim("你")] }), "原回答：你");
  assert.equal(session.update({ results: [interim("你好")] }), "原回答：你好");
  assert.equal(session.update({ results: [interim("你好", true), interim("世界")] }), "原回答：你好世界");
});

test("speech callbacks replace interim text and clear active state on end or error", () => {
  const recognition = {};
  let text = "已有：";
  const activeStates = [];
  const errors = [];
  const controller = InterviewMedia.bindSpeechRecognition(recognition, {
    getText: () => text,
    setText: (value) => { text = value; },
    setActive: (value) => activeStates.push(value),
    onError: (error) => errors.push(error.error),
  });
  const result = (value, isFinal = false) => ({ 0: { transcript: value }, isFinal });

  controller.begin();
  recognition.onresult({ results: [result("你")] });
  recognition.onresult({ results: [result("你好")] });
  assert.equal(text, "已有：你好");
  recognition.onend();
  assert.equal(controller.isActive(), false);
  controller.begin();
  recognition.onerror({ error: "network" });
  assert.equal(controller.isActive(), false);
  assert.deepEqual(activeStates, [true, false, true, false]);
  assert.deepEqual(errors, ["network"]);
});
