(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ContextualAgent = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CONTEXT_FIELDS = {
    module: "module",
    opportunity: "opportunity_id",
    resume: "resume_id",
  };

  const NAVIGATION_MODULES = {
    home: new Set([""]),
    resume: new Set(["input", "manage", "analysis", "export", "jd", "skills"]),
    interview: new Set(["mock", "professional", "practice", "records"]),
    tracker: new Set(["add", "board", "salary"]),
    agent: new Set([""]),
  };

  function positiveId(value) {
    const number = Number(value);
    return Number.isInteger(number) && number > 0 ? number : null;
  }

  function normalizedContext(input) {
    const result = {};
    if (typeof input?.module === "string" && input.module.trim()) {
      result.module = input.module.trim().slice(0, 100);
    }
    const opportunityId = positiveId(input?.opportunity_id ?? input?.opportunityId);
    const resumeId = positiveId(input?.resume_id ?? input?.resumeId);
    if (opportunityId) result.opportunity_id = opportunityId;
    if (resumeId) result.resume_id = resumeId;
    return result;
  }

  function createContextStore(initial = {}) {
    let current = normalizedContext(initial);
    const suppressed = new Map();

    return {
      sync(next = {}) {
        const normalized = normalizedContext(next);
        Object.entries(CONTEXT_FIELDS).forEach(([kind, field]) => {
          const value = normalized[field];
          if (value == null) {
            delete current[field];
            suppressed.delete(kind);
            return;
          }
          if (suppressed.get(kind) === String(value)) {
            delete current[field];
            return;
          }
          suppressed.delete(kind);
          current[field] = value;
        });
        return this.payload();
      },
      remove(kind) {
        const field = CONTEXT_FIELDS[kind];
        if (!field) return this.payload();
        if (current[field] != null) suppressed.set(kind, String(current[field]));
        delete current[field];
        return this.payload();
      },
      payload() {
        return { ...current };
      },
    };
  }

  function createLatestRequestGate() {
    let generation = 0;
    return {
      begin(identity = "") {
        generation += 1;
        return { generation, identity: String(identity) };
      },
      isCurrent(request, identity = "") {
        return Boolean(
          request
          && request.generation === generation
          && request.identity === String(identity)
        );
      },
      invalidate() {
        generation += 1;
      },
    };
  }

  function createConversationEpoch() {
    return createLatestRequestGate();
  }

  const TERMINAL_PROPOSAL_STATUSES = new Set([
    "completed", "cancelled", "expired", "failed",
  ]);

  function proposalVersion(proposal) {
    const revision = proposal?.revision == null ? NaN : Number(proposal.revision);
    if (Number.isFinite(revision)) return revision;
    const updatedAt = Date.parse(proposal?.updated_at || "");
    return Number.isFinite(updatedAt) ? updatedAt : null;
  }

  function mergeProposalState(current, incoming, options = {}) {
    if (!current) return incoming;
    if (!incoming || positiveId(current.id) !== positiveId(incoming.id)) return current;
    if (
      TERMINAL_PROPOSAL_STATUSES.has(String(current.status))
      && !TERMINAL_PROPOSAL_STATUSES.has(String(incoming.status))
    ) return current;
    const currentEpoch = Number(options.currentEpoch) || 0;
    const incomingEpoch = Number(options.incomingEpoch) || 0;
    if (incomingEpoch < currentEpoch) return current;
    const currentVersion = proposalVersion(current);
    const incomingVersion = proposalVersion(incoming);
    if (
      currentVersion !== null
      && incomingVersion !== null
      && incomingVersion < currentVersion
    ) return current;
    return { ...current, ...incoming };
  }

  function chatPayload(message, conversationId, context = {}) {
    const payload = {
      conversation_id: String(conversationId || ""),
      message: String(message || ""),
    };
    const safeContext = normalizedContext(context);
    if (Object.keys(safeContext).length) payload.context = safeContext;
    return payload;
  }

  function escapeHtml(value = "") {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function inputRequestHtml(request) {
    if (!request || request.kind !== "resume_select" || !Array.isArray(request.options)) return "";
    const workflow = request.workflow === "revision" ? "revision" : "analysis";
    const options = request.options.filter((option) => positiveId(option?.id)).map((option) => `
      <button type="button" class="agent-resume-choice" data-agent-resume-choice="${positiveId(option.id)}" data-agent-workflow="${workflow}">
        <b>${escapeHtml(option.label || `简历 #${option.id}`)}</b>
        ${option.preview ? `<small>${escapeHtml(option.preview)}</small>` : ""}
        <span>${workflow === "revision" ? "生成优化草稿" : "开始诊断"}</span>
      </button>
    `).join("");
    if (!options) return "";
    return `<section class="agent-input-request" data-agent-input-kind="resume_select">
      <p>${escapeHtml(request.prompt || "选择一份简历")}</p>
      <div class="agent-resume-choice-list">${options}</div>
    </section>`;
  }

  function selectionMessage(request, resumeId) {
    const id = positiveId(resumeId);
    if (!id) return "";
    const action = request?.workflow === "revision" ? "生成优化草稿" : "进行简历诊断";
    return `选择简历 #${id}，${action}`;
  }

  function normalizedSuggestedActions(actions) {
    if (!Array.isArray(actions)) return [];
    const seen = new Set();
    return actions.flatMap((action) => {
      const label = typeof action?.label === "string" ? action.label.trim().slice(0, 80) : "";
      const page = typeof action?.page === "string" ? action.page : "";
      const module = typeof action?.module === "string" ? action.module : "";
      if (!label || !NAVIGATION_MODULES[page]?.has(module)) return [];
      const key = `${page}:${module}`;
      if (seen.has(key)) return [];
      seen.add(key);
      return [{ label, page, module }];
    }).slice(0, 3);
  }

  function suggestedActionsHtml(actions) {
    const items = normalizedSuggestedActions(actions).map((action) => `
      <button type="button" data-agent-navigation data-agent-page="${escapeHtml(action.page)}" data-agent-module="${escapeHtml(action.module)}">
        ${escapeHtml(action.label)}<i data-lucide="arrow-right"></i>
      </button>
    `).join("");
    return items ? `<div class="agent-suggested-actions">${items}</div>` : "";
  }

  function proposalsFromMetadata(metadata) {
    if (!Array.isArray(metadata?.action_proposals)) return [];
    return metadata.action_proposals.filter((proposal) => (
      proposal && positiveId(proposal.id) && typeof proposal.status === "string"
    ));
  }

  function flattenEditable(editable, prefix = "") {
    if (!editable || typeof editable !== "object" || Array.isArray(editable)) return [];
    return Object.entries(editable).flatMap(([key, value]) => {
      const path = prefix ? `${prefix}.${key}` : key;
      if (value && typeof value === "object" && !Array.isArray(value)) {
        return flattenEditable(value, path);
      }
      return [{ path, value }];
    });
  }

  function proposalHtml(proposal) {
    const status = String(proposal?.status || "unknown");
    const pending = status === "pending";
    const busy = Boolean(proposal?.busy);
    const fields = flattenEditable(proposal?.editable).map(({ path, value }) => {
      const type = typeof value === "number" ? "number" : "text";
      const serialized = Array.isArray(value) ? JSON.stringify(value) : (value ?? "");
      return `<label class="agent-edit-field"><span>${escapeHtml(path)}</span><input class="input" type="${type}" data-agent-edit-field="${escapeHtml(path)}" value="${escapeHtml(serialized)}" ${pending && !busy ? "" : "disabled"}></label>`;
    }).join("");
    const draftControl = pending && proposal?.action_type === "create_resume_version"
      ? `<button type="button" class="ghost" data-agent-action="open-draft" ${busy ? "disabled" : ""}>查看并编辑草稿</button>`
      : "";
    const controls = pending ? `
      <div class="proposal-controls">
        ${draftControl}
        ${fields ? `<button type="button" class="ghost" data-agent-action="edit" ${busy ? "disabled" : ""}>保存修改</button>` : ""}
        <button type="button" class="primary" data-agent-action="confirm" ${busy ? "disabled" : ""}>确认执行</button>
        <button type="button" class="ghost" data-agent-action="cancel" ${busy ? "disabled" : ""}>取消</button>
      </div>` : proposal?.hydrationRetry ? `
      <div class="proposal-controls"><button type="button" class="ghost" data-agent-action="retry-hydration">重试加载</button></div>` : "";
    const result = proposal?.result?.id
      ? `<a class="proposal-result-link" href="${escapeHtml(resultHref(proposal.result))}" data-agent-result-link>${escapeHtml(resultLabel(proposal.result))}</a>`
      : "";
    return `<article class="agent-proposal" data-proposal-id="${escapeHtml(proposal?.id || "")}" data-status="${escapeHtml(status)}">
      <header><span class="proposal-status">${escapeHtml(statusLabel(status))}</span><span class="proposal-risk risk-${escapeHtml(proposal?.risk_level || "low")}">${escapeHtml(riskLabel(proposal?.risk_level))}</span></header>
      <p>${escapeHtml(proposal?.preview || "待确认操作")}</p>
      ${fields ? `<div class="proposal-fields">${fields}</div>` : ""}
      ${proposal?.error ? `<div class="proposal-error" role="alert">${escapeHtml(proposal.error)}</div>` : ""}
      ${result}${controls}
    </article>`;
  }

  function transitionProposal(current, event, payload = {}) {
    const next = { ...current, error: "" };
    if (event === "confirm_start" || event === "cancel_start" || event === "edit_start") {
      return { ...next, busy: true };
    }
    if (event.endsWith("_error")) {
      return { ...next, busy: false, error: String(payload.error || "操作失败，请重试") };
    }
    if (event.endsWith("_success") && payload.action) {
      return { ...next, ...payload.action, busy: false, error: "" };
    }
    return next;
  }

  function statusLabel(status) {
    return ({ pending: "等待确认", executing: "执行中", completed: "已完成", cancelled: "已取消", expired: "已过期", failed: "执行失败", stale: "提案不可用", forbidden: "无权访问", unavailable: "暂时无法加载" })[status] || "状态未知";
  }

  function riskLabel(risk) {
    return ({ low: "低风险", medium: "需确认", high: "高风险" })[risk] || "需确认";
  }

  function resultLabel(result) {
    const labels = { opportunity: "查看机会", resume: "查看简历", action_item: "查看行动", career_profile: "查看目标", career_report: "查看报告" };
    return labels[result?.entity_type] || "查看结果";
  }

  function resultRoute(result) {
    const id = positiveId(result?.id);
    if (!id) return null;
    const routes = {
      opportunity: { page: "tracker", module: "board", key: "opportunity" },
      resume: { page: "resume", module: "manage", key: "resume" },
      action_item: { page: "agent", module: null, key: "action" },
      career_profile: { page: "home", module: null, key: "profile" },
      career_report: { page: "agent", module: null, key: "report" },
    };
    return routes[result.entity_type] ? { ...routes[result.entity_type], id } : null;
  }

  function resultHref(result) {
    const route = resultRoute(result);
    if (!route) return "?page=home";
    const params = new URLSearchParams({ page: route.page });
    if (route.module) params.set("module", route.module);
    params.set(route.key, String(route.id));
    return `?${params.toString()}`;
  }

  function unavailableProposal(proposal, kind) {
    const statuses = { not_found: "stale", forbidden: "forbidden", server: "unavailable", network: "unavailable" };
    const messages = {
      not_found: "该提案已不存在，不能继续操作。",
      forbidden: "该提案不属于当前用户，不能继续操作。",
      server: "提案状态暂时无法读取，请重试。",
      network: "网络连接失败，无法确认提案最新状态。",
    };
    return {
      ...proposal,
      status: statuses[kind] || "unavailable",
      editable: {},
      error: messages[kind] || messages.server,
      hydrationRetry: kind === "server" || kind === "network",
      hydrationSource: proposal,
    };
  }

  function hydrationFailureKind(response, error = null) {
    if (error) return "network";
    if (response?.http_status === 404) return "not_found";
    if (response?.http_status === 403) return "forbidden";
    return "server";
  }

  function authoritativeHydrationSuccess(action) {
    if (!action || typeof action !== "object") return action;
    return {
      ...action,
      busy: false,
      error: "",
      hydrationRetry: false,
      hydrationSource: null,
    };
  }

  function isActiveOpportunity(status, canonicalStatuses = []) {
    if (status === "已结束" || status === "已拒绝") return false;
    return status === "Offer" || !canonicalStatuses.includes(status) || canonicalStatuses.includes(status);
  }

  function resultLookupState(expectedId, response, error = null) {
    if (error || !response || (!response.success && response.http_status !== 404)) {
      return { status: "unavailable", retry: true, entity: null };
    }
    const entity = response.success && positiveId(response.data?.id) === positiveId(expectedId)
      ? response.data
      : null;
    return entity
      ? { status: "located", retry: false, entity }
      : { status: "missing", retry: false, entity: null };
  }

  function profileResultHtml(profile) {
    const id = positiveId(profile?.id);
    if (!id) return "";
    const targetRole = typeof profile.target_role === "string" && profile.target_role.trim()
      ? profile.target_role.trim()
      : "未设置";
    const cities = Array.isArray(profile.cities)
      ? profile.cities.map((city) => String(city).trim()).filter(Boolean).join("、")
      : "";
    const salary = profile.salary && typeof profile.salary === "object" && !Array.isArray(profile.salary)
      ? [profile.salary.min, profile.salary.max].filter((value) => value !== undefined && value !== null && value !== "").join(" - ")
      : "";
    return `<article class="profile-result-summary is-result-highlight" id="focusedAgentResult" data-profile-id="${id}" tabindex="-1">
      <header><b>求职画像 #${id}</b><small>已验证 Agent 结果</small></header>
      <dl>
        <div><dt>目标岗位</dt><dd>${escapeHtml(targetRole)}</dd></div>
        <div><dt>目标城市</dt><dd>${escapeHtml(cities || "未设置")}</dd></div>
        <div><dt>期望薪资</dt><dd>${escapeHtml(salary || "未设置")}</dd></div>
      </dl>
    </article>`;
  }

  return {
    chatPayload,
    createContextStore,
    createConversationEpoch,
    createLatestRequestGate,
    escapeHtml,
    inputRequestHtml,
    selectionMessage,
    normalizedSuggestedActions,
    suggestedActionsHtml,
    flattenEditable,
    normalizedContext,
    proposalHtml,
    proposalsFromMetadata,
    resultRoute,
    resultHref,
    transitionProposal,
    unavailableProposal,
    hydrationFailureKind,
    authoritativeHydrationSuccess,
    isActiveOpportunity,
    mergeProposalState,
    resultLookupState,
    profileResultHtml,
  };
});
