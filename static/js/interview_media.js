(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.InterviewMedia = api;
})(typeof window !== "undefined" ? window : globalThis, function () {
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

  return {
    computeAudioMetrics,
    decodeAudioBlob,
    bindRecorderSession,
    createSpeechTranscriptSession,
    bindSpeechRecognition,
  };
});
