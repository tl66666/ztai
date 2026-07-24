const EMPTY_METRICS = Object.freeze({
    duration_seconds: null,
    peak: 0,
    average_volume: 0,
    silence_ratio: 0,
    pause_count: 0,
    clipping_ratio: 0,
  });

  function fallbackDuration(source, startedAt, now) {
    if (source !== "recording" || !Number.isFinite(startedAt) || startedAt <= 0) return null;
    const elapsed = now - startedAt;
    if (!Number.isFinite(elapsed) || elapsed < 0 || elapsed > 4 * 60 * 60 * 1000) return null;
    return Math.max(1, Math.round(elapsed / 1000));
  }

  async function computeAudioMetrics(blob, options = {}) {
    const {
      source = "upload",
      startedAt = 0,
      now = Date.now(),
      AudioContext = null,
    } = options;
    const fallback = { ...EMPTY_METRICS, duration_seconds: fallbackDuration(source, startedAt, now) };
    if (!AudioContext) return fallback;
    let context = null;
    try {
      const arrayBuffer = await blob.arrayBuffer();
      context = new AudioContext();
      const audioBuffer = await context.decodeAudioData(arrayBuffer.slice(0));
      const data = audioBuffer.getChannelData(0);
      const step = Math.max(1, Math.floor(data.length / 24000));
      let sum = 0;
      let peak = 0;
      let silent = 0;
      let clipped = 0;
      let pauseCount = 0;
      let inPause = false;
      for (let index = 0; index < data.length; index += step) {
        const value = Math.abs(data[index]);
        sum += value * value;
        peak = Math.max(peak, value);
        if (value < 0.018) {
          silent += 1;
          if (!inPause) pauseCount += 1;
          inPause = true;
        } else {
          inPause = false;
        }
        if (value > 0.96) clipped += 1;
      }
      const samples = Math.ceil(data.length / step);
      return {
        duration_seconds: Number(Number(audioBuffer.duration || 0).toFixed(2)),
        peak: Number(peak.toFixed(3)),
        average_volume: Number(Math.sqrt(sum / Math.max(1, samples)).toFixed(3)),
        silence_ratio: Number((silent / Math.max(1, samples)).toFixed(2)),
        pause_count: pauseCount,
        clipping_ratio: Number((clipped / Math.max(1, samples)).toFixed(3)),
      };
    } catch (_error) {
      return fallback;
    } finally {
      if (context?.close) {
        try {
          await context.close();
        } catch (_error) {
          // Closing is best-effort after decode; no context is retained.
        }
      }
    }
  }

  async function decodeAudioBlob(blob, AudioContext) {
    const context = new AudioContext();
    try {
      return await context.decodeAudioData(await blob.arrayBuffer());
    } finally {
      if (context.close) await context.close();
    }
  }

  function stopTracks(stream) {
    stream?.getTracks?.().forEach((track) => track.stop());
  }

  function bindRecorderSession(options) {
    const {
      recorder,
      stream,
      token,
      format = null,
      isCurrent,
      createBlob,
      computeMetrics,
      publish,
      onError = () => {},
    } = options;
    const chunks = [];
    recorder.ondataavailable = (event) => {
      if (event.data?.size > 0) chunks.push(event.data);
    };
    recorder.onerror = (error) => {
      stopTracks(stream);
      if (isCurrent(token)) onError(error);
    };
    recorder.onstop = async () => {
      stopTracks(stream);
      const mimeType = recorder.mimeType || format?.mimeType || "";
      const blob = createBlob(chunks, { type: mimeType });
      const metrics = await computeMetrics(blob);
      if (!isCurrent(token)) return;
      publish({ blob, metrics, mimeType, token });
    };
  }

  function createSpeechTranscriptSession(baseText = "") {
    const base = String(baseText);
    return {
      update(event) {
        let finalText = "";
        let interimText = "";
        for (let index = 0; index < event.results.length; index += 1) {
          const result = event.results[index];
          const transcript = result?.[0]?.transcript || "";
          if (result.isFinal) finalText += transcript;
          else interimText += transcript;
        }
        return `${base}${finalText}${interimText}`;
      },
    };
  }

  function bindSpeechRecognition(recognition, options) {
    const { getText, setText, setActive, onError } = options;
    let active = false;
    let session = null;
    const finish = () => {
      active = false;
      session = null;
      setActive(false);
    };
    recognition.onresult = (event) => {
      if (active && session) setText(session.update(event));
    };
    recognition.onend = finish;
    recognition.onerror = (error) => {
      finish();
      onError(error);
    };
    return {
      begin() {
        session = createSpeechTranscriptSession(getText());
        active = true;
        setActive(true);
      },
      finish,
      isActive() { return active; },
    };
  }

  function createRecordingController(dependencies) {
    const {
      acquireStream,
      createRecorder,
      createBlob,
      computeMetrics,
      publish,
      onError = () => {},
      onRecorderChange = () => {},
      now = () => Date.now(),
    } = dependencies;
    let epoch = 0;
    let startingToken = null;
    let active = null;

    const setActive = (value) => {
      active = value;
      onRecorderChange(value?.recorder || null);
    };

    async function start({ target, format }) {
      if (startingToken !== null || active) return { ok: false, reason: "busy" };
      const token = ++epoch;
      startingToken = token;
      let stream = null;
      try {
        stream = await acquireStream();
        if (token !== epoch) {
          stopTracks(stream);
          return { ok: false, reason: "cancelled" };
        }
        const recorderOptions = format?.mimeType ? { mimeType: format.mimeType } : undefined;
        const recorder = createRecorder(stream, recorderOptions);
        const startedAt = now();
        setActive({ recorder, stream, token, target });
        bindRecorderSession({
          recorder,
          stream,
          token,
          format,
          isCurrent: (candidate) => candidate === epoch,
          createBlob,
          computeMetrics: (blob) => computeMetrics(blob, "recording", startedAt),
          publish: (result) => {
            if (active?.token === token) setActive(null);
            publish({ ...result, target });
          },
          onError: (error) => {
            if (active?.token === token) setActive(null);
            onError(error);
          },
        });
        recorder.start();
        return { ok: true, recorder, token };
      } catch (error) {
        stopTracks(stream);
        if (active?.token === token) setActive(null);
        onError(error);
        return { ok: false, reason: "error", error };
      } finally {
        if (startingToken === token) startingToken = null;
      }
    }

    function invalidate() {
      epoch += 1;
      startingToken = null;
      const current = active;
      if (!current) return;
      setActive(null);
      try {
        if (current.recorder.state === "recording") current.recorder.stop();
      } finally {
        stopTracks(current.stream);
      }
    }

    function stop() {
      if (!active) return false;
      if (active.recorder.state !== "recording") return false;
      active.recorder.stop();
      return true;
    }

    return {
      start,
      stop,
      invalidate,
      activeRecorder() { return active?.recorder || null; },
    };
  }

  function createObjectUrlRegistry({ create, revoke }) {
    const urls = new Map();
    const clear = (target) => {
      const url = urls.get(target);
      if (!url) return;
      revoke(url);
      urls.delete(target);
    };
    const clearAll = () => [...urls.keys()].forEach(clear);
    return {
      replace(target, blob) {
        clearAll();
        const url = create(blob);
        urls.set(target, url);
        return url;
      },
      get(target) { return urls.get(target) || null; },
      clear,
      clearAll,
    };
  }

  export {
    computeAudioMetrics,
    decodeAudioBlob,
    bindRecorderSession,
    createSpeechTranscriptSession,
    bindSpeechRecognition,
    createRecordingController,
    createObjectUrlRegistry,
  };
