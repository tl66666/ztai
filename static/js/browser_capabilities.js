(function exposeBrowserCapabilities(root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.BrowserCapabilities = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function createBrowserCapabilities() {
  const RECORDER_FORMATS = Object.freeze([
    Object.freeze({ mimeType: "audio/webm;codecs=opus", extension: "webm" }),
    Object.freeze({ mimeType: "audio/webm", extension: "webm" }),
    Object.freeze({ mimeType: "audio/ogg;codecs=opus", extension: "ogg" }),
    Object.freeze({ mimeType: "audio/ogg", extension: "ogg" }),
    Object.freeze({ mimeType: "audio/mp4", extension: "m4a" }),
  ]);

  function speechRecognition(scope = {}) {
    if (typeof scope.SpeechRecognition === "function") {
      return { kind: "standard", Recognition: scope.SpeechRecognition };
    }
    if (typeof scope.webkitSpeechRecognition === "function") {
      return { kind: "webkit", Recognition: scope.webkitSpeechRecognition };
    }
    return { kind: "none", Recognition: null };
  }

  function canRecordAudio(scope = {}, navigatorLike = {}) {
    return typeof scope.MediaRecorder === "function"
      && typeof navigatorLike.mediaDevices?.getUserMedia === "function";
  }

  function selectRecorderFormat(Recorder) {
    if (typeof Recorder?.isTypeSupported !== "function") return null;
    const supported = RECORDER_FORMATS.find(({ mimeType }) => Recorder.isTypeSupported(mimeType));
    return supported ? { ...supported } : null;
  }

  function extensionForMime(mime = "") {
    const normalized = String(mime).toLowerCase();
    if (normalized.includes("mp4") || normalized.includes("m4a")) return "m4a";
    if (normalized.includes("ogg")) return "ogg";
    if (normalized.includes("mpeg") || normalized.includes("mp3")) return "mp3";
    if (normalized.includes("wav")) return "wav";
    return "webm";
  }

  function audioInputPlan(scope = {}, navigatorLike = {}) {
    const canRecord = canRecordAudio(scope, navigatorLike);
    return {
      canRecord,
      recorderFormat: canRecord ? selectRecorderFormat(scope.MediaRecorder) : null,
      canUpload: true,
      canType: true,
    };
  }

  function setUnavailable(element, unavailable) {
    if (!element) return;
    element.hidden = unavailable;
    element.disabled = unavailable;
    element.classList?.toggle("hidden", unavailable);
    element.setAttribute?.("aria-hidden", String(unavailable));
  }

  function applyCapabilityUI(documentLike, capabilities) {
    const get = (id) => documentLike?.getElementById?.(id);
    const speechUnavailable = capabilities.speech?.kind === "none";
    setUnavailable(get("voiceBtn"), speechUnavailable);
    const speechStatus = get("speechCapabilityStatus");
    if (speechStatus) {
      speechStatus.textContent = speechUnavailable
        ? "当前浏览器不支持语音转文字，请直接使用文字回答。"
        : "语音转文字可用，文字回答始终可用。";
    }

    const recordingUnavailable = !capabilities.audio?.canRecord;
    for (const id of ["recordAudioBtn", "stopAudioBtn", "roomRecordBtn", "roomStopRecordBtn"]) {
      setUnavailable(get(id), recordingUnavailable);
    }
    const recordingStatus = get("recordingCapabilityStatus");
    if (recordingStatus) {
      recordingStatus.textContent = recordingUnavailable
        ? "当前浏览器不能直接录音，仍可上传音频或使用文字回答。"
        : "浏览器录音可用，也可以上传音频或使用文字回答。";
    }
  }

  function startSpeechSafely(recognition) {
    try {
      recognition.start();
      return { ok: true, error: null };
    } catch (error) {
      return { ok: false, error };
    }
  }

  return {
    RECORDER_FORMATS,
    speechRecognition,
    canRecordAudio,
    selectRecorderFormat,
    extensionForMime,
    audioInputPlan,
    applyCapabilityUI,
    startSpeechSafely,
  };
});
