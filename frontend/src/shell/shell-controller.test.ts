import { beforeEach, describe, expect, it, vi } from "vitest";

import { createShellController } from "./shell-controller";

describe("Shell controller", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <h1 id="pageTitle"></h1>
      <button class="nav-item" data-page="home"><span>首页</span></button>
      <section id="page-home" class="page"></section>
      <section id="page-agent" class="page"></section>
    `;
  });

  it("delegates navigation through the history seam for current and future controls", () => {
    const navigate = vi.fn();
    const controller = createShellController({
      state: { currentPage: "home", currentModule: "" },
      byId: (id) => document.getElementById(id),
      history: () => ({ navigate, sync: vi.fn() }),
      playTone: vi.fn(),
      syncAgentContext: vi.fn(),
      loadAgentCommandCenter: vi.fn(),
      routeLeavesFlow: vi.fn(() => false),
      clearApplicationHandoff: vi.fn(),
      clearMatchOpportunityLink: vi.fn(),
    });
    controller.bindNavigation();

    document.querySelector<HTMLElement>("[data-page='home'] span")?.click();
    const dynamic = document.createElement("button");
    dynamic.dataset.page = "agent";
    document.body.append(dynamic);
    dynamic.click();

    expect(navigate).toHaveBeenNthCalledWith(1, "home", {
      module: null,
      historyMode: "push",
    });
    expect(navigate).toHaveBeenNthCalledWith(2, "agent", {
      module: null,
      historyMode: "push",
    });
  });

  it("renders the requested page and loads the command center only for Agent", () => {
    const loadAgentCommandCenter = vi.fn();
    const state = { currentPage: "home", currentModule: "overview" };
    const controller = createShellController({
      state,
      byId: (id) => document.getElementById(id),
      history: () => ({ navigate: vi.fn(), sync: vi.fn() }),
      playTone: vi.fn(),
      syncAgentContext: vi.fn(),
      loadAgentCommandCenter,
      routeLeavesFlow: vi.fn(() => false),
      clearApplicationHandoff: vi.fn(),
      clearMatchOpportunityLink: vi.fn(),
    });

    controller.renderPage("agent");

    expect(state).toEqual({ currentPage: "agent", currentModule: "" });
    expect(document.getElementById("page-agent")?.classList).toContain("active");
    expect(document.getElementById("pageTitle")?.textContent).toBe("求职指挥台");
    expect(loadAgentCommandCenter).toHaveBeenCalledOnce();
  });
});
