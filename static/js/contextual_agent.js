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

  function chatPayload(message, conversationId, context = {}) {
    const payload = {
      user_id: 1,
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
    const controls = pending ? `
      <div class="proposal-controls">
        ${fields ? `<button type="button" class="ghost" data-agent-action="edit" ${busy ? "disabled" : ""}>保存修改</button>` : ""}
        <button type="button" class="primary" data-agent-action="confirm" ${busy ? "disabled" : ""}>确认执行</button>
        <button type="button" class="ghost" data-agent-action="cancel" ${busy ? "disabled" : ""}>取消</button>
      </div>` : "";
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
    return ({ pending: "等待确认", executing: "执行中", completed: "已完成", cancelled: "已取消", expired: "已过期", failed: "执行失败" })[status] || "状态未知";
  }

  function riskLabel(risk) {
    return ({ low: "低风险", medium: "需确认", high: "高风险" })[risk] || "需确认";
  }

  function resultLabel(result) {
    const labels = { opportunity: "查看机会", resume: "查看简历", action_item: "查看行动", career_profile: "查看目标", career_report: "查看报告" };
    return labels[result?.entity_type] || "查看结果";
  }

  function resultHref(result) {
    if (result?.entity_type === "opportunity") return `?page=tracker&module=board&opportunity=${positiveId(result.id) || ""}`;
    if (result?.entity_type === "resume") return "?page=resume&module=manage";
    if (result?.entity_type === "action_item") return "?page=agent";
    return "?page=home";
  }

  return {
    chatPayload,
    createContextStore,
    escapeHtml,
    flattenEditable,
    normalizedContext,
    proposalHtml,
    proposalsFromMetadata,
    resultHref,
    transitionProposal,
  };
});
