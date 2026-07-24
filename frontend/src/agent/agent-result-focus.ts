import type { ApiRequest } from "../shared/api-client";
import type { RuntimeUi } from "../shared/runtime-ui";

export interface AgentResultFocusDependencies {
  request: ApiRequest;
  ui: RuntimeUi;
  contextualAgent: any;
  windowObject?: Window;
  documentObject?: Document;
}

export function createAgentResultFocus(
  deps: AgentResultFocusDependencies,
): { focusFromLocation(): Promise<void> } {
  const {
    request,
    ui,
    contextualAgent,
    windowObject = window,
    documentObject = document,
  } = deps;
  const byId = (id: string): HTMLElement | null => ui.byId(id);

  function renderLookup(key: string, id: number, lookup: any): void {
    const labels: Record<string, string> = {
      action: "行动",
      profile: "求职目标",
      report: "求职报告",
    };
    const host = key === "profile"
      ? byId("agentResultFocus")
      : byId("agentActiveActions");
    if (!host) return;
    host.classList.remove("hidden");
    if (lookup.status === "located") {
      const entity = lookup.entity || {};
      if (key === "profile") {
        host.innerHTML = contextualAgent.profileResultHtml(lookup.entity);
      } else {
        host.insertAdjacentHTML("afterbegin", `
          <div class="command-row is-result-highlight" id="focusedAgentResult" tabindex="-1"><span><b>${ui.escapeHtml(entity.title || labels[key])}</b><small>已验证 ${ui.escapeHtml(labels[key])} #${id}</small></span></div>`);
      }
    } else {
      const message = lookup.status === "missing"
        ? "结果不存在或已失效"
        : "结果暂时无法读取";
      host.insertAdjacentHTML("afterbegin", `
        <div class="command-empty" id="focusedAgentResult" tabindex="-1" role="status"><b>${message}</b><span>${ui.escapeHtml(labels[key])} #${id}</span>${lookup.retry ? '<button type="button" class="ghost small" data-command="agent-result-retry">重试</button>' : ""}</div>`);
    }
    byId("focusedAgentResult")?.focus({ preventScroll: true });
  }

  async function focusFromLocation(): Promise<void> {
    const params = new URLSearchParams(windowObject.location.search);
    const key = ["resume", "action", "profile", "report"]
      .find((candidate) => params.has(candidate));
    if (!key) return;
    const id = Number(params.get(key));
    if (!Number.isInteger(id) || id <= 0) return;
    byId("focusedAgentResult")?.remove();
    byId("agentResultFocus")?.classList.add("hidden");
    if (key === "resume") {
      const card = documentObject.querySelector<HTMLElement>(`[data-resume-id="${id}"]`);
      if (!card) {
        ui.toast("结果简历不存在或已归档");
        return;
      }
      card.classList.add("is-result-highlight");
      card.focus({ preventScroll: true });
      card.scrollIntoView({ block: "center", behavior: "smooth" });
      return;
    }
    if (key === "action") {
      let data;
      try {
        const response = await request("/action-items");
        const action = response.success
          ? (response.data || []).find((item: any) => Number(item.id) === id)
          : null;
        data = action
          ? { success: true, data: action }
          : { success: false, http_status: response.http_status || 404 };
      } catch (error) {
        renderLookup(key, id, contextualAgent.resultLookupState(id, null, error));
        return;
      }
      const lookup = contextualAgent.resultLookupState(id, data);
      const action = lookup.entity;
      if (action) {
        byId("agentActiveActions")?.insertAdjacentHTML("afterbegin", `
          <div class="command-row is-result-highlight" tabindex="-1" id="focusedAgentResult"><span><b>${ui.escapeHtml(action.title)}</b><small>${ui.escapeHtml(action.status || "pending")} · 行动 #${id}</small></span></div>`);
        byId("focusedAgentResult")?.focus({ preventScroll: true });
        return;
      }
      renderLookup(key, id, lookup);
      return;
    }
    const endpoint = key === "profile" ? `/profile/${id}` : `/career-reports/${id}`;
    let response;
    try {
      response = await request(endpoint);
    } catch (error) {
      renderLookup(key, id, contextualAgent.resultLookupState(id, null, error));
      return;
    }
    renderLookup(key, id, contextualAgent.resultLookupState(id, response));
  }

  return { focusFromLocation };
}
