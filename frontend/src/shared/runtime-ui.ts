export type Tone = "tap" | "jump" | "success" | "warn";

export interface SoundState {
  soundEnabled: boolean;
  audioContext: AudioContext | null;
}

export interface ToastOptions {
  silent?: boolean;
}

export interface RuntimeUi {
  byId<T extends HTMLElement = HTMLElement>(id: string): T | null;
  renderIcons(): boolean;
  withLoading<T>(task: () => Promise<T>, message?: string): Promise<T>;
  playTone(type?: string): void;
  toast(message: string, options?: ToastOptions): void;
  escapeHtml(value?: unknown): string;
  renderText(value?: unknown): string;
  downloadBlob(blob: Blob, filename: string): void;
  downloadResponse(response: Response, fallbackName: string): Promise<void>;
}

export function createRuntimeUi(
  state: SoundState,
  windowObject: Window = window,
  documentObject: Document = document,
): RuntimeUi {
  let toastTimer: ReturnType<typeof setTimeout> | undefined;

  function byId<T extends HTMLElement = HTMLElement>(id: string): T | null {
    return documentObject.getElementById(id) as T | null;
  }

  function renderIcons(): boolean {
    const iconLibrary = windowObject.lucide;
    if (!iconLibrary || typeof iconLibrary.createIcons !== "function") return false;
    try {
      iconLibrary.createIcons();
      return true;
    } catch (error) {
      console.warn("Icon rendering is unavailable; text controls remain usable.", error);
      return false;
    }
  }

  async function withLoading<T>(
    task: () => Promise<T>,
    message = "AI 正在整理你的求职策略...",
  ): Promise<T> {
    const layer = byId("loadingLayer");
    const label = layer?.querySelector("span");
    if (label) label.textContent = message;
    layer?.classList.remove("hidden");
    try {
      return await task();
    } finally {
      layer?.classList.add("hidden");
    }
  }

  function playTone(type = "tap"): void {
    if (!state.soundEnabled) return;
    const AudioContextConstructor = (windowObject as Window & typeof globalThis).AudioContext
      || windowObject.webkitAudioContext;
    if (!AudioContextConstructor) return;
    try {
      const context = state.audioContext || new AudioContextConstructor();
      state.audioContext = context;
      if (context.state === "suspended") void context.resume();
      const now = context.currentTime;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      const presets: Record<Tone, { freq: number; duration: number; volume: number }> = {
        tap: { freq: 520, duration: 0.055, volume: 0.018 },
        jump: { freq: 660, duration: 0.075, volume: 0.022 },
        success: { freq: 840, duration: 0.09, volume: 0.025 },
        warn: { freq: 260, duration: 0.08, volume: 0.018 },
      };
      const tone = presets[type as Tone] || presets.tap;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(tone.freq, now);
      oscillator.frequency.exponentialRampToValueAtTime(
        Math.max(120, tone.freq * 0.82),
        now + tone.duration,
      );
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(tone.volume, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + tone.duration);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(now);
      oscillator.stop(now + tone.duration + 0.02);
    } catch (error) {
      console.warn("UI sound skipped", error);
    }
  }

  function toast(message: string, options: ToastOptions = {}): void {
    const node = byId("toast");
    if (!node) return;
    node.textContent = message;
    node.classList.remove("hidden");
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.add("hidden"), 2600);
    if (!options.silent) {
      const isWarning = /失败|请先|不支持|不存在|错误/.test(message);
      playTone(isWarning ? "warn" : "success");
    }
  }

  function escapeHtml(value: unknown = ""): string {
    const div = documentObject.createElement("div");
    div.textContent = String(value);
    return div.innerHTML;
  }

  function renderText(value: unknown = ""): string {
    return escapeHtml(value)
      .replace(/^### (.*)$/gm, "<h5>$1</h5>")
      .replace(/^## (.*)$/gm, "<h4>$1</h4>")
      .replace(/^\s*---+\s*$/gm, "<hr>")
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/^(\d+)\. (.*)$/gm, "<div>$1. $2</div>")
      .replace(/^- (.*)$/gm, "<div>• $1</div>")
      .replace(/\n/g, "<br>");
  }

  function downloadBlob(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = documentObject.createElement("a");
    link.href = url;
    link.download = filename;
    documentObject.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  async function downloadResponse(response: Response, fallbackName: string): Promise<void> {
    if (!response.ok) {
      const text = await response.text();
      try {
        const data = JSON.parse(text) as { message?: string };
        toast(data.message || "文件处理失败");
      } catch {
        toast("文件处理失败");
      }
      return;
    }
    const disposition = response.headers.get("content-disposition") || "";
    const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i);
    const filename = decodeURIComponent(match?.[1] || match?.[2] || fallbackName);
    downloadBlob(await response.blob(), filename);
    toast("文件已生成并开始下载");
  }

  return {
    byId,
    renderIcons,
    withLoading,
    playTone,
    toast,
    escapeHtml,
    renderText,
    downloadBlob,
    downloadResponse,
  };
}
