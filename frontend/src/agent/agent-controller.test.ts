import { beforeEach, describe, expect, it, vi } from "vitest";

import { createAgentController } from "./agent-controller";

function contextualAgentStub() {
  let payload: Record<string, unknown> = {};
  return {
    createContextStore: () => ({
      sync: (next: Record<string, unknown>) => {
        payload = {
          module: next.module,
          opportunity_id: next.opportunityId,
          resume_id: next.resumeId,
        };
      },
      payload: () => payload,
      remove: (kind: string) => {
        const keys: Record<string, string> = {
          module: "module",
          opportunity: "opportunity_id",
          resume: "resume_id",
        };
        delete payload[keys[kind]];
      },
    }),
  };
}

describe("Agent controller", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <button id="agentLauncher" aria-expanded="false"></button>
      <button id="openAgentWorkspace"><span>打开</span></button>
      <div id="agentDrawerBackdrop" class="hidden"></div>
      <aside id="agentDrawer" aria-hidden="true">
        <button id="closeAgentDrawer"></button>
        <div id="agentContextChips"></div>
      </aside>
      <select id="analysisResumeSelect"><option value="7" selected>版本</option></select>
    `;
  });

  it("derives and renders current module, opportunity, and resume context", () => {
    const controller = createAgentController({
      state: {
        currentPage: "resume",
        currentModule: "analysis",
        currentOpportunityId: 11,
        applications: [{ id: 11, company: "示例公司", job_title: "测试工程师" }],
        applicationStatuses: [],
        resumes: [{ id: 7, title: "测试版简历" }],
        agentDrawerOpener: null,
      },
      byId: (id) => document.getElementById(id),
      contextualAgent: contextualAgentStub(),
      escapeHtml: String,
      escapeAttr: String,
      renderIcons: vi.fn(),
      loadCommandCenter: vi.fn(),
    });

    controller.syncContext();

    expect(controller.contextPayload()).toEqual({
      module: "resume:analysis",
      opportunity_id: 11,
      resume_id: 7,
    });
    expect(document.getElementById("agentContextChips")?.textContent).toContain(
      "示例公司 / 测试工程师",
    );
    expect(document.getElementById("agentContextChips")?.textContent).toContain(
      "测试版简历",
    );
  });

  it("uses delegated controls to open and close the global drawer", () => {
    const loadCommandCenter = vi.fn();
    const controller = createAgentController({
      state: {
        currentPage: "home",
        currentModule: "",
        currentOpportunityId: null,
        applications: [],
        applicationStatuses: [],
        resumes: [],
        agentDrawerOpener: null,
      },
      byId: (id) => document.getElementById(id),
      contextualAgent: contextualAgentStub(),
      escapeHtml: String,
      escapeAttr: String,
      renderIcons: vi.fn(),
      loadCommandCenter,
    });
    controller.bind();

    document.querySelector<HTMLElement>("#openAgentWorkspace span")?.click();
    expect(document.getElementById("agentDrawer")?.getAttribute("aria-hidden")).toBe("false");
    expect(loadCommandCenter).toHaveBeenCalledOnce();
    document.getElementById("closeAgentDrawer")?.click();
    expect(document.getElementById("agentDrawer")?.getAttribute("aria-hidden")).toBe("true");
    document.getElementById("agentLauncher")?.click();
    document.getElementById("agentDrawerBackdrop")?.click();
    expect(document.getElementById("agentDrawer")?.getAttribute("aria-hidden")).toBe("true");
  });
});
