const assert = require("node:assert/strict");
const test = require("node:test");

const Capabilities = require("../../static/js/browser_capabilities.js");

test("detects standard, prefixed, and missing speech recognition", () => {
  class StandardRecognition {}
  class PrefixedRecognition {}

  assert.deepEqual(Capabilities.speechRecognition({ SpeechRecognition: StandardRecognition }), {
    kind: "standard",
    Recognition: StandardRecognition,
  });
  assert.deepEqual(Capabilities.speechRecognition({ webkitSpeechRecognition: PrefixedRecognition }), {
    kind: "webkit",
    Recognition: PrefixedRecognition,
  });
  assert.deepEqual(Capabilities.speechRecognition({}), {
    kind: "none",
    Recognition: null,
  });
});

test("requires both MediaRecorder and getUserMedia for in-browser recording", () => {
  class Recorder {}
  assert.equal(Capabilities.canRecordAudio({ MediaRecorder: Recorder }, { mediaDevices: { getUserMedia() {} } }), true);
  assert.equal(Capabilities.canRecordAudio({ MediaRecorder: Recorder }, {}), false);
  assert.equal(Capabilities.canRecordAudio({}, { mediaDevices: { getUserMedia() {} } }), false);
});

test("selects the first MIME type supported by the recorder", () => {
  const supported = new Set(["audio/webm", "audio/ogg;codecs=opus"]);
  const Recorder = { isTypeSupported: (mime) => supported.has(mime) };

  assert.deepEqual(Capabilities.selectRecorderFormat(Recorder), {
    mimeType: "audio/webm",
    extension: "webm",
  });
});

test("uses Firefox-style Ogg Opus when WebM is unavailable", () => {
  const Recorder = { isTypeSupported: (mime) => mime === "audio/ogg;codecs=opus" };

  assert.deepEqual(Capabilities.selectRecorderFormat(Recorder), {
    mimeType: "audio/ogg;codecs=opus",
    extension: "ogg",
  });
});

test("falls back to recorder defaults when MIME probing is absent or inconclusive", () => {
  assert.equal(Capabilities.selectRecorderFormat(function Recorder() {}), null);
  assert.equal(Capabilities.selectRecorderFormat({ isTypeSupported: () => false }), null);
});

test("maps recorded and uploaded audio MIME types to matching extensions", () => {
  assert.equal(Capabilities.extensionForMime("audio/webm;codecs=opus"), "webm");
  assert.equal(Capabilities.extensionForMime("audio/ogg; codecs=opus"), "ogg");
  assert.equal(Capabilities.extensionForMime("audio/mp4"), "m4a");
  assert.equal(Capabilities.extensionForMime("audio/mpeg"), "mp3");
  assert.equal(Capabilities.extensionForMime("audio/wav"), "wav");
  assert.equal(Capabilities.extensionForMime(""), "");
  assert.equal(Capabilities.extensionForMime("application/octet-stream"), "");
});

test("preserves safe uploaded extensions when MIME is empty", () => {
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "answer.wav", type: "" }), {
    filename: "answer.wav",
    extension: "wav",
    mimeType: "",
    mayNotPlay: false,
  });
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "voice.m4a", type: "" }), {
    filename: "voice.m4a",
    extension: "m4a",
    mimeType: "",
    mayNotPlay: false,
  });
});

test("known MIME types replace conflicting filename extensions", () => {
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "answer.wav", type: "audio/mpeg" }), {
    filename: "answer.mp3",
    extension: "mp3",
    mimeType: "audio/mpeg",
    mayNotPlay: false,
  });
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "answer.mp3", type: "audio/wav" }), {
    filename: "answer.wav",
    extension: "wav",
    mimeType: "audio/wav",
    mayNotPlay: false,
  });
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "answer.mp4", type: "audio/mp4" }), {
    filename: "answer.m4a",
    extension: "m4a",
    mimeType: "audio/mp4",
    mayNotPlay: false,
  });
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "answer.m4a", type: "audio/mp4" }), {
    filename: "answer.m4a",
    extension: "m4a",
    mimeType: "audio/mp4",
    mayNotPlay: false,
  });
});

test("uses a safe non-WebM fallback for unknown uploads without extensions", () => {
  assert.deepEqual(Capabilities.audioFileDescriptor({ name: "voice<>clip", type: "application/octet-stream" }), {
    filename: "voice__clip.audio",
    extension: "audio",
    mimeType: "application/octet-stream",
    mayNotPlay: true,
  });
  assert.match(Capabilities.audioPlaybackErrorMessage(), /下载原文件/);
});

test("keeps upload and text fallbacks when live recording is unavailable", () => {
  assert.deepEqual(Capabilities.audioInputPlan({}, {}), {
    canRecord: false,
    recorderFormat: null,
    canUpload: true,
    canType: true,
  });
});

function element() {
  const classes = new Set();
  return {
    hidden: false,
    disabled: false,
    textContent: "",
    dataset: {},
    classList: {
      toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
      contains: (name) => classes.has(name),
    },
  };
}

test("applies accessible fallback state without disabling upload or text", () => {
  const elements = new Map([
    ["voiceBtn", element()],
    ["speechCapabilityStatus", element()],
    ["recordAudioBtn", element()],
    ["stopAudioBtn", element()],
    ["roomRecordBtn", element()],
    ["roomStopRecordBtn", element()],
    ["recordingCapabilityStatus", element()],
    ["audioFileInput", element()],
    ["answerInput", element()],
    ["roomAnswer", element()],
  ]);
  const documentLike = { getElementById: (id) => elements.get(id) || null };

  Capabilities.applyCapabilityUI(documentLike, {
    speech: { kind: "none", Recognition: null },
    audio: { canRecord: false, recorderFormat: null, canUpload: true, canType: true },
  });

  assert.equal(elements.get("voiceBtn").hidden, true);
  assert.equal(elements.get("voiceBtn").disabled, true);
  assert.equal(elements.get("voiceBtn").classList.contains("hidden"), true);
  assert.match(elements.get("speechCapabilityStatus").textContent, /文字/);
  for (const id of ["recordAudioBtn", "stopAudioBtn", "roomRecordBtn", "roomStopRecordBtn"]) {
    assert.equal(elements.get(id).hidden, true);
    assert.equal(elements.get(id).disabled, true);
    assert.equal(elements.get(id).classList.contains("hidden"), true);
  }
  assert.match(elements.get("recordingCapabilityStatus").textContent, /上传/);
  assert.equal(elements.get("audioFileInput").disabled, false);
  assert.equal(elements.get("answerInput").disabled, false);
  assert.equal(elements.get("roomAnswer").disabled, false);
});

test("converts speech start errors into a handled result", () => {
  const permissionError = new Error("permission denied");
  const result = Capabilities.startSpeechSafely({ start: () => { throw permissionError; } });

  assert.equal(result.ok, false);
  assert.equal(result.error, permissionError);
});
