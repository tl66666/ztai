import type { OpportunityControllerDependencies } from "./opportunity-controller";

export interface ApplicationBoardCallbacks {
  loadDashboard(): Promise<unknown>;
  openWorkspace(id: number): Promise<unknown>;
  closeWorkspace(): unknown;
}

export interface ApplicationBoard {
  save(): Promise<void>;
  edit(id: number): Promise<void>;
  remove(id: number): Promise<void>;
  load(): Promise<void>;
  advance(id: number): Promise<void>;
  coach(id: number): Promise<void>;
}

function required<T extends HTMLElement>(
  byId: OpportunityControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing application control: #${id}`);
  return node as T;
}

export function createApplicationBoard(
  deps: OpportunityControllerDependencies,
  callbacks: ApplicationBoardCallbacks,
): ApplicationBoard {
  const {
    userId,
    state,
    request,
    byId,
    escapeHtml,
    renderText,
    toast,
    withLoading,
    renderIcons,
    renderAgentCommandOpportunities,
    applicationPayloadForJob,
    clearApplicationHandoff,
    jumpToModule,
    confirmAction,
  } = deps;

  async function save(): Promise<void> {
    const company = required<HTMLInputElement>(byId, "appCompany").value.trim();
    const job = required<HTMLInputElement>(byId, "appJob").value.trim();
    if (!company || !job) {
      toast("请填写公司和岗位");
      return;
    }
    const payload: Record<string, unknown> = {
      user_id: userId,
      company,
      job_title: job,
      status: required<HTMLSelectElement>(byId, "appStatus").value,
      city: required<HTMLInputElement>(byId, "appCity").value,
      notes: required<HTMLTextAreaElement>(byId, "appNotes").value,
      ...applicationPayloadForJob(state.pendingApplicationHandoff, job),
    };
    if (state.editingAppId) {
      delete payload.jd_text;
      delete payload.resume_id;
    }
    Object.keys(payload).forEach((key) => payload[key] === undefined && delete payload[key]);
    const editingId = state.editingAppId;
    const data = await request(
      editingId ? `/applications/${editingId}` : "/applications",
      { method: editingId ? "PUT" : "POST", body: payload },
    );
    if (!data.success) return;
    const savedId = editingId || Number(data.application_id);
    toast(editingId ? "投递记录已更新" : "投递记录已添加");
    state.editingAppId = null;
    clearApplicationHandoff();
    required(byId, "saveAppBtn").innerHTML = `<i data-lucide="plus"></i>添加记录`;
    for (const id of ["appCompany", "appJob", "appCity", "appNotes"]) {
      required<HTMLInputElement | HTMLTextAreaElement>(byId, id).value = "";
    }
    await Promise.all([load(), callbacks.loadDashboard()]);
    if (Number.isInteger(savedId) && savedId > 0) {
      await callbacks.openWorkspace(savedId);
    }
    renderIcons();
  }

  async function edit(id: number): Promise<void> {
    const data = await request(`/applications/detail/${id}`);
    if (!data.success) {
      toast(data.message || "投递记录不存在");
      return;
    }
    const item = data.data;
    clearApplicationHandoff();
    state.editingAppId = id;
    required<HTMLInputElement>(byId, "appCompany").value = item.company || "";
    required<HTMLInputElement>(byId, "appJob").value = item.job_title || "";
    const status = required<HTMLSelectElement>(byId, "appStatus");
    if (![...status.options].some((option) => option.value === item.status)) {
      status.add(new Option(`待确认：${item.status || "未设置"}`, item.status, true, true));
    }
    status.value = item.status || "已投递";
    required<HTMLInputElement>(byId, "appCity").value = item.city || "";
    required<HTMLTextAreaElement>(byId, "appNotes").value = item.notes || "";
    required(byId, "saveAppBtn").innerHTML = `<i data-lucide="save"></i>更新记录`;
    jumpToModule("tracker", "add");
    renderIcons();
  }

  async function remove(id: number): Promise<void> {
    if (!confirmAction("确定删除这条投递记录吗？")) return;
    const data = await request(`/applications/${id}`, { method: "DELETE" });
    if (!data.success) {
      toast(data.message || "删除失败");
      return;
    }
    toast("投递记录已删除");
    if (state.currentOpportunityId === id) callbacks.closeWorkspace();
    await Promise.all([load(), callbacks.loadDashboard()]);
  }

  async function load(): Promise<void> {
    const data = await request(`/applications/${userId}`);
    const list = required(byId, "applicationList");
    if (!data.success) {
      list.innerHTML = `<div class="workspace-message" role="alert">投递记录加载失败，请稍后重试。</div>`;
      return;
    }
    const apps = data.data || [];
    state.applications = apps;
    const canonicalStatuses = Array.isArray(data.canonical_statuses)
      ? data.canonical_statuses
      : [];
    state.applicationStatuses = canonicalStatuses;
    const statusSelect = required<HTMLSelectElement>(byId, "appStatus");
    const previousStatus = statusSelect.value;
    statusSelect.innerHTML = canonicalStatuses.map((status: string) => (
      `<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`
    )).join("");
    statusSelect.value = canonicalStatuses.includes(previousStatus)
      ? previousStatus
      : (canonicalStatuses.includes("已投递") ? "已投递" : canonicalStatuses[0] || "");
    if (!apps.length) {
      list.innerHTML = `<div class="opportunity-empty"><strong>暂无投递</strong><span>添加第一条记录后，这里会按阶段自动成列。</span><button class="primary" onclick="jumpToModule('tracker','add')"><i data-lucide="plus"></i>新增投递</button></div>`;
      renderAgentCommandOpportunities();
      renderIcons();
      return;
    }
    const canonicalSet = new Set(canonicalStatuses);
    const unknownItems = apps.filter(
      (item: any) => item.needs_status_review || !canonicalSet.has(item.status),
    );
    const anchorIndexes = new Set([0, 2, 3]);
    const grouped = canonicalStatuses.map((stage: string, index: number) => ({
      stage,
      items: apps.filter((item: any) => item.status === stage),
      anchor: anchorIndexes.has(index) || stage === "Offer",
    })).filter((group: any) => group.items.length || group.anchor);
    if (unknownItems.length) {
      grouped.unshift({
        stage: "待确认",
        items: unknownItems,
        warning: true,
        anchor: false,
      });
    }
    list.innerHTML = grouped.map((group: any) => `
      <section class="kanban-column${group.warning ? " needs-review" : ""}">
        <h4>${group.warning ? '<i data-lucide="triangle-alert" aria-hidden="true"></i>' : ""}${escapeHtml(group.stage)}<span>${group.items.length}</span></h4>
        ${group.warning ? '<p class="status-warning"><i data-lucide="triangle-alert" aria-hidden="true"></i>旧状态需要确认，请编辑后选择当前阶段。</p>' : ""}
        ${group.items.length ? group.items.map((item: any) => `
          <article class="kanban-card">
            <strong>${escapeHtml(item.company)}</strong>
            <span>${escapeHtml(item.job_title)}</span>
            <span class="status-text">阶段：${escapeHtml(item.needs_status_review ? `待确认（原状态：${item.status || "未设置"}）` : item.status)}</span>
            <em>${escapeHtml(item.city || "城市未填")}</em>
            <p>${escapeHtml(item.notes || "暂无备注，建议补充投递渠道、面试反馈或待办。")}</p>
            <button class="primary small details-command" onclick="openOpportunityWorkspace(${item.id})"><i data-lucide="panel-right-open"></i>打开详情</button>
            <div class="kanban-card-actions">
              <button class="ghost small" onclick="coachApplication(${item.id})">跟进建议</button>
              ${item.needs_status_review ? "" : `<button class="ghost small" onclick="advanceApplication(${item.id})">推进</button>`}
              <button class="ghost small" onclick="editApplication(${item.id})">编辑</button>
              <button class="ghost small danger" onclick="deleteApplication(${item.id})">删除</button>
            </div>
          </article>
        `).join("") : `<div class="kanban-empty"><span>暂无记录</span></div>`}
      </section>
    `).join("");
    renderAgentCommandOpportunities();
    renderIcons();
  }

  async function advance(id: number): Promise<void> {
    const data = await request(`/applications/${id}/advance`, {
      method: "POST",
      body: { user_id: userId },
    });
    if (!data.success) {
      toast(data.message || "推进失败");
      return;
    }
    toast(`已推进到：${data.status}`);
    await Promise.all([load(), callbacks.loadDashboard()]);
  }

  async function coach(id: number): Promise<void> {
    const data = await withLoading(
      () => request(`/applications/${id}/coach`, {
        method: "POST",
        body: { user_id: userId },
      }),
      "AI 正在整理投递跟进策略...",
    );
    jumpToModule("tracker", "board");
    const result = required(byId, "applicationCoachResult");
    result.classList.remove("hidden");
    result.innerHTML = `
      <h4>${escapeHtml(data.title || "投递跟进建议")}</h4>
      <div><b>下一步：</b>${escapeHtml(data.next_action || "")}</div>
      <div><b>风险点：</b>${escapeHtml(data.risk || "")}</div>
      <div><b>可发送话术：</b><br>${escapeHtml(data.message_template || "")}</div>
      ${data.ai_note ? `<div><b>AI 补充：</b><br>${renderText(data.ai_note)}</div>` : ""}
    `;
    result.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  return { save, edit, remove, load, advance, coach };
}
