export interface AgentDrawerDependencies {
  state: {
    agentDrawerOpener: Element | null;
  };
  byId: (id: string) => HTMLElement | null;
  syncContext: () => unknown;
  loadCommandCenter: () => unknown;
  documentObject: Document;
  windowObject: Window;
}

export interface AgentDrawer {
  open(event?: { currentTarget?: EventTarget | null }): void;
  close(): void;
  handleKeydown(event: KeyboardEvent): void;
}

export function createAgentDrawer(
  deps: AgentDrawerDependencies,
): AgentDrawer {
  const {
    state,
    byId,
    syncContext,
    loadCommandCenter,
    documentObject,
    windowObject,
  } = deps;

  function open(event?: { currentTarget?: EventTarget | null }): void {
    const drawer = byId("agentDrawer");
    if (!drawer || drawer.getAttribute("aria-hidden") === "false") return;
    const opener = event?.currentTarget instanceof Element
      ? event.currentTarget
      : documentObject.activeElement;
    state.agentDrawerOpener = opener;
    syncContext();
    drawer.setAttribute("aria-hidden", "false");
    byId("agentLauncher")?.setAttribute("aria-expanded", "true");
    byId("agentDrawerBackdrop")?.classList.remove("hidden");
    documentObject.body.classList.add("agent-drawer-open");
    windowObject.requestAnimationFrame(() => {
      byId("closeAgentDrawer")?.focus({ preventScroll: true });
    });
    loadCommandCenter();
  }

  function close(): void {
    const drawer = byId("agentDrawer");
    if (!drawer || drawer.getAttribute("aria-hidden") === "true") return;
    drawer.setAttribute("aria-hidden", "true");
    byId("agentLauncher")?.setAttribute("aria-expanded", "false");
    byId("agentDrawerBackdrop")?.classList.add("hidden");
    documentObject.body.classList.remove("agent-drawer-open");
    const opener = state.agentDrawerOpener?.isConnected
      ? state.agentDrawerOpener
      : byId("agentLauncher");
    state.agentDrawerOpener = null;
    if (opener instanceof HTMLElement) opener.focus({ preventScroll: true });
  }

  function handleKeydown(event: KeyboardEvent): void {
    const drawer = byId("agentDrawer");
    if (!drawer || drawer.getAttribute("aria-hidden") !== "false") return;
    if (event.key === "Escape") {
      event.preventDefault();
      close();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...drawer.querySelectorAll<HTMLElement>(
      "button:not([disabled]), input:not([disabled]), textarea:not([disabled]), "
      + "select:not([disabled]), a[href]",
    )].filter((node) => node.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && documentObject.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && documentObject.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return { open, close, handleKeydown };
}
