import type { ApiRequest } from "../shared/api-client";
import type { RuntimeUi } from "../shared/runtime-ui";
import { createAgentResultFocus } from "./agent-result-focus";

export interface AgentWorkspaceDependencies {
  userId: number;
  conversationStorageKey: string;
  state: any;
  request: ApiRequest;
  ui: RuntimeUi;
  contextualAgent: any;
  contextPayload(): Record<string, unknown>;
  openDrawer(event?: { currentTarget?: EventTarget | null }): void;
  closeDrawer(): void;
  navigate(page: string, module: string): unknown;
  loadResumes(): Promise<unknown>;
  loadApplications(): Promise<unknown>;
  loadDashboard(): Promise<unknown>;
  loadOpportunityWorkspace(id: number, request?: any): Promise<unknown>;
  syncAgentContext(): void;
  storage?: Storage;
  windowObject?: Window;
  documentObject?: Document;
}

export interface AgentWorkspace {
  loadCommandCenter(): Promise<void>;
  renderCommandOpportunities(): void;
  openProposal(proposalId: number, opener?: HTMLElement | null): void;
  sendMessage(message?: string, context?: Record<string, unknown>): Promise<void>;
  generateCareerReport(): Promise<void>;
  loadConversations(preferredId?: string, restore?: boolean): Promise<void>;
  createConversation(): Promise<void>;
  clearConversation(): Promise<void>;
  handleChatLogClick(event: Event): Promise<void>;
  focusResultFromLocation(): Promise<void>;
}

export function createAgentWorkspace(deps: AgentWorkspaceDependencies): AgentWorkspace {
  const {
    userId: USER_ID,
    conversationStorageKey: JOBHUNTER_AGENT_CONVERSATION,
    state,
    request: api,
    ui,
    contextualAgent,
    contextPayload,
    openDrawer,
    closeDrawer,
    navigate,
    loadResumes,
    loadApplications,
    loadDashboard,
    loadOpportunityWorkspace,
    syncAgentContext,
    storage = localStorage,
    windowObject = window,
    documentObject = document,
  } = deps;
  const $ = (id: string): any => ui.byId(id);
  const {
    escapeHtml,
    renderIcons,
    renderText,
    toast,
    withLoading,
  } = ui;
  const agentConversationEpoch = contextualAgent.createConversationEpoch();
  const agentCommandCenterGate = contextualAgent.createLatestRequestGate();
  const resultFocus = createAgentResultFocus({
    request: api,
    ui,
    contextualAgent,
    windowObject,
    documentObject,
  });

async function loadAgentCommandCenter() {
  const request = agentCommandCenterGate.begin("command-center");
  const proposalEpoch = state.agentProposalMutationEpoch;
  let data;
  try {
    data = await api("/agent/actions");
  } catch (_error) {
    data = { success: false, actions: [] };
  }
  if (
    !agentCommandCenterGate.isCurrent(request, "command-center")
    || proposalEpoch !== state.agentProposalMutationEpoch
  ) return;
  const actions = data.success ? data.actions || [] : [];
  state.agentCommandProposalIds.forEach((proposalId: any) => {
    if (!state.agentConversationProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  const mergedActions = actions
    .map((proposal: any) => mergeAgentProposal(proposal, proposalEpoch))
    .filter((proposal: any) => proposal?.status === "pending");
  state.agentCommandProposalIds = new Set(mergedActions.map((proposal: any) => Number(proposal.id)));
  renderAgentCommandActions(mergedActions, data.success ? "" : "待确认操作暂时无法加载");
  renderAgentCommandOpportunities();
}

function renderAgentCommandActions(actions: any, error: any = "") {
  const box = $("agentActiveActions");
  const count = actions.length;
  $("agentActionCount").textContent = String(count);
  $("agentLauncherBadge").textContent = String(count);
  $("agentLauncherBadge").classList.toggle("hidden", !count);
  if (!box) return;
  if (error) {
    box.innerHTML = `<div class="command-empty" role="alert">${escapeHtml(error)}<button type="button" class="ghost small" data-command="agent-command-retry">重试</button></div>`;
    return;
  }
  box.innerHTML = count ? actions.map((proposal: any) => `
    <button type="button" class="command-row" data-command="agent-proposal-open" data-proposal-id="${Number(proposal.id)}">
      <span><b>${escapeHtml(proposal.preview || "待确认操作")}</b><small>${escapeHtml(proposal.risk_level === "high" ? "高风险" : proposal.risk_level === "medium" ? "需确认" : "低风险")}</small></span>
      <i data-lucide="arrow-right"></i>
    </button>`).join("") : '<div class="command-empty"><b>没有待确认操作</b><span>Agent 提出的写入动作会先出现在这里。</span></div>';
  renderIcons();
}

function renderAgentCommandOpportunities() {
  const box = $("agentCommandOpportunities");
  if (!box) return;
  const active = state.applications.filter((item: any) => (
    contextualAgent.isActiveOpportunity(item.status, state.applicationStatuses)
  )).slice(0, 6);
  box.innerHTML = active.length ? active.map((item: any) => `
    <button type="button" class="command-row" data-command="agent-opportunity-open" data-opportunity-id="${Number(item.id)}">
      <span><b>${escapeHtml(item.company || "未命名公司")} / ${escapeHtml(item.job_title || "目标岗位")}</b><small>${escapeHtml(item.needs_status_review ? "待确认" : item.status || "未设置")}</small></span>
      <i data-lucide="panel-right-open"></i>
    </button>`).join("") : '<div class="command-empty"><b>暂无活跃机会</b><span>在投递看板添加机会后，会同步到这里。</span></div>';
  renderIcons();
}

function openAgentProposal(proposalId: any, opener: any = null) {
  openDrawer({ currentTarget: opener || $("agentLauncher") });
  const existing = $("chatLog").querySelector(`[data-proposal-id="${Number(proposalId)}"]`);
  if (existing) return existing.scrollIntoView({ block: "center", behavior: "smooth" });
  const proposal = state.agentProposals.get(Number(proposalId));
  if (!proposal) return;
  appendMessage("这项操作需要你的确认。", "bot", { proposals: [proposal] });
}

async function sendAgentMessage(forcedMessage: any = "", extraContext: any = {}) {
  const input = $("agentInput");
  const hasForcedMessage = typeof forcedMessage === "string" && forcedMessage.trim();
  const message = contextualAgent.outboundMessage(forcedMessage, input?.value || "");
  if (!message) return;
  if (!state.agentConversationId) await createAgentConversation();
  const conversationId = state.agentConversationId;
  if (!conversationId) return;
  agentConversationEpoch.invalidate();
  appendMessage(message, "user");
  if (!hasForcedMessage) input.value = "";
  const chatRequest = {
    ...contextualAgent.chatPayload(message, conversationId, {
      ...contextPayload(),
      ...extraContext,
    }),
    conversation_id: conversationId,
  };
  const data = await withLoading(
    () => api("/agent/chat", {
      method: "POST",
      body: chatRequest,
    }),
    "求职 Agent 正在读取上下文并处理任务..."
  );
  if (state.agentConversationId !== conversationId || (data.success && data.conversation_id !== conversationId)) return;
  if (!data.success) return toast(data.message || "求职 Agent 暂时不可用");
  storage.setItem(JOBHUNTER_AGENT_CONVERSATION, conversationId);
  const reply = data.reply || data.message || "我暂时没想好，换个问法试试。";
  appendMessage(reply, "bot", {
    proposals: data.action_proposals || [],
    inputRequest: data.input_request || {},
  });
  renderAgentEvents(data.events || [], data.status);
  renderAgentSuggestedActions(data.suggested_actions || []);
  await loadAgentConversations(conversationId, false);
  await loadAgentCommandCenter();
}

async function generateCareerReport() {
  $("agentInput").value = "结合我的简历、面试和投递数据，生成一份求职作战报告";
  await sendAgentMessage();
}

function appendMessage(text: any, type: any, options: any = {}) {
  const node = documentObject.createElement("div");
  node.className = `message ${type}`;
  node.innerHTML = renderText(text);
  $("chatLog").appendChild(node);
  renderAgentProposals(options.proposals || [], node);
  renderAgentInputRequest(options.inputRequest || {}, node);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
}

function renderAgentInputRequest(inputRequest: any, messageNode: any) {
  if (!messageNode || !contextualAgent) return;
  const html = contextualAgent.inputRequestHtml(inputRequest);
  if (html) messageNode.insertAdjacentHTML("beforeend", html);
}

async function loadAgentConversations(preferredId: any = "", restore: any = true) {
  const data = await api(`/agent/conversations/${USER_ID}`);
  if (!data.success) return;
  let conversations = data.conversations || [];
  if (!conversations.length) {
    await createAgentConversation();
    return;
  }
  const saved = preferredId || state.agentConversationId || storage.getItem(JOBHUNTER_AGENT_CONVERSATION);
  state.agentConversationId = conversations.some((item: any) => item.id === saved)
    ? saved
    : conversations[0].id;
  storage.setItem(JOBHUNTER_AGENT_CONVERSATION, state.agentConversationId);
  const select = $("agentConversationSelect");
  select.innerHTML = conversations.map((item: any) => (
    `<option value="${escapeHtml(item.id)}">${escapeHtml(item.title || "新对话")}</option>`
  )).join("");
  select.value = state.agentConversationId;
  if (restore) await restoreAgentMessages();
}

async function createAgentConversation() {
  const data = await api("/agent/conversations", {
    method: "POST",
    body: { user_id: USER_ID, title: "新对话" },
  });
  if (!data.success) return toast(data.message || "新建会话失败");
  agentConversationEpoch.invalidate();
  state.agentConversationId = data.conversation.id;
  storage.setItem(JOBHUNTER_AGENT_CONVERSATION, state.agentConversationId);
  await loadAgentConversations(state.agentConversationId, false);
  renderAgentWelcome();
  $("agentInput")?.focus();
}

async function clearAgentConversation() {
  if (!state.agentConversationId) return;
  if (!confirm("确定清空当前求职 Agent 会话吗？其他会话和求职数据不会受影响。")) return;
  const data = await api(`/agent/conversations/${state.agentConversationId}/clear`, {
    method: "POST",
    body: { user_id: USER_ID },
  });
  if (!data.success) return toast(data.message || "清空失败");
  agentConversationEpoch.invalidate();
  renderAgentWelcome();
  toast("当前会话已清空");
}

async function restoreAgentMessages() {
  const conversationId = state.agentConversationId;
  if (!conversationId) {
    agentConversationEpoch.invalidate();
    return renderAgentWelcome();
  }
  const request = agentConversationEpoch.begin(conversationId);
  let data;
  try {
    data = await api(
      `/agent/conversations/${conversationId}/messages?user_id=${USER_ID}`
    );
  } catch (_error) {
    data = { success: false, messages: [] };
  }
  if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
  if (!data.success || !data.messages?.length) return renderAgentWelcome();
  const preparedMessages = [];
  for (const message of data.messages) {
    const proposals = message.role === "assistant"
      ? await hydrateAgentProposals(contextualAgent.proposalsFromMetadata(message.metadata))
      : [];
    if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
    preparedMessages.push({ message, proposals });
  }
  if (!agentConversationEpoch.isCurrent(request, state.agentConversationId)) return;
  state.agentConversationProposalIds.forEach((proposalId: any) => {
    if (!state.agentCommandProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  state.agentConversationProposalIds = new Set(
    preparedMessages.flatMap(({ proposals }: any) => (
      proposals.map((proposal: any) => Number(proposal.id))
    ))
  );
  $("chatLog").innerHTML = "";
  for (const { message, proposals } of preparedMessages) {
    appendMessage(message.content, message.role === "user" ? "user" : "bot", {
      proposals,
      inputRequest: message.metadata?.input_request || {},
    });
    if (message.role === "assistant") {
      renderAgentEvents(message.metadata?.events || [], message.metadata?.status || "completed");
      renderAgentSuggestedActions(message.metadata?.suggested_actions || []);
    }
  }
}

async function hydrateAgentProposals(proposals: any) {
  return Promise.all(proposals.map(hydrateAgentProposal));
}

async function hydrateAgentProposal(proposal: any) {
  let latest;
  try {
    latest = await api(`/agent/actions/${Number(proposal.id)}`);
  } catch (_error) {
    return contextualAgent.unavailableProposal(
      proposal, contextualAgent.hydrationFailureKind(null, _error)
    );
  }
  if (!latest.success) {
    return contextualAgent.unavailableProposal(
      proposal, contextualAgent.hydrationFailureKind(latest)
    );
  }
  return contextualAgent.authoritativeHydrationSuccess(latest.action);
}

function renderAgentProposals(proposals: any, messageNode: any) {
  if (!messageNode || !proposals.length) return;
  proposals.forEach((proposal: any) => {
    state.agentConversationProposalIds.add(Number(proposal.id));
    const merged = mergeAgentProposal(proposal, state.agentProposalMutationEpoch);
    messageNode.insertAdjacentHTML("beforeend", contextualAgent.proposalHtml(merged));
  });
}

function mergeAgentProposal(proposal: any, incomingEpoch: any = state.agentProposalMutationEpoch) {
  const proposalId = Number(proposal?.id);
  if (!Number.isInteger(proposalId) || proposalId <= 0) return proposal;
  const current = state.agentProposals.get(proposalId);
  const currentEpoch = state.agentProposalEpochs.get(proposalId) || 0;
  const merged = contextualAgent.mergeProposalState(current, proposal, {
    currentEpoch,
    incomingEpoch,
  });
  if (merged !== current) {
    state.agentProposals.set(proposalId, merged);
    state.agentProposalEpochs.set(proposalId, Math.max(currentEpoch, incomingEpoch));
  }
  return merged;
}

function advanceAgentProposalMutation() {
  state.agentProposalMutationEpoch += 1;
  agentConversationEpoch.invalidate();
  return state.agentProposalMutationEpoch;
}

function proposalError(data: any, fallback: any) {
  return data?.error?.message || data?.message || fallback;
}

function proposalChanges(card: any, proposal: any) {
  const changes: Record<string, any> = {};
  card.querySelectorAll("[data-agent-edit-field]").forEach((input: any) => {
    const path = input.dataset.agentEditField.split(".");
    const original = path.reduce((value: any, key: string) => value?.[key], proposal.editable);
    let value = input.value;
    if (typeof original === "number") value = Number(value);
    if (Array.isArray(original)) {
      try {
        value = JSON.parse(value);
      } catch (_error) {
        value = input.value.split(",").map((item: string) => item.trim()).filter(Boolean);
      }
    }
    let target = changes;
    path.forEach((key: string, index: number) => {
      if (index === path.length - 1) target[key] = value;
      else target = target[key] ||= {};
    });
  });
  return changes;
}

function replaceProposalCard(card: any, proposal: any, incomingEpoch: any = state.agentProposalMutationEpoch) {
  const merged = mergeAgentProposal(proposal, incomingEpoch);
  card.outerHTML = contextualAgent.proposalHtml(merged);
  renderIcons();
  return merged;
}

async function handleAgentChatLogClick(event: any) {
  const navigation = event.target.closest("[data-agent-navigation]");
  if (navigation) {
    const actions = contextualAgent.normalizedSuggestedActions([{
      label: navigation.textContent || "下一步",
      page: navigation.dataset.agentPage,
      module: navigation.dataset.agentModule,
    }]);
    if (actions[0]) {
      closeDrawer();
      navigate(actions[0].page, actions[0].module);
    }
    return;
  }
  const choice = event.target.closest("[data-agent-resume-choice]");
  if (choice) {
    const resumeId = Number(choice.dataset.agentResumeChoice);
    const workflow = ["revision", "analysis", "interview_questions"].includes(choice.dataset.agentWorkflow)
      ? choice.dataset.agentWorkflow : "analysis";
    const message = contextualAgent.selectionMessage({ workflow }, {
      id: resumeId,
      label: choice.dataset.agentResumeLabel,
    });
    if (message) await sendAgentMessage(message, { resume_id: resumeId });
    return;
  }
  await handleProposalClick(event);
}

async function openAgentResumeDraft(card: any, proposal: any) {
  const existing = card.querySelector(".agent-draft-editor");
  if (existing) return existing.scrollIntoView({ block: "nearest", behavior: "smooth" });
  let data;
  try {
    data = await api(`/agent/actions/${Number(proposal.id)}/draft`);
  } catch (_error) {
    toast("草稿暂时无法加载，请重试");
    return;
  }
  if (!data.success || !data.draft) {
    toast(proposalError(data, "草稿暂时无法加载"));
    return;
  }
  const draft = data.draft;
  const editor = documentObject.createElement("section");
  editor.className = "agent-draft-editor";
  editor.innerHTML = `<header><b>版本草稿</b><small>确认前可编辑；保存后会新建版本，不覆盖原简历。</small></header>`;
  const textarea = documentObject.createElement("textarea");
  textarea.className = "input textarea agent-draft-content";
  textarea.rows = 12;
  textarea.value = String(draft.content || "");
  textarea.setAttribute("aria-label", "可编辑的简历版本草稿");
  const controls = documentObject.createElement("div");
  controls.className = "proposal-controls";
  const save = documentObject.createElement("button");
  save.type = "button";
  save.className = "ghost";
  save.dataset.agentAction = "save-draft";
  save.textContent = "保存草稿修改";
  controls.appendChild(save);
  editor.append(textarea, controls);
  card.appendChild(editor);
  textarea.focus({ preventScroll: true });
}

async function saveAgentResumeDraft(card: any, proposal: any) {
  const textarea = card.querySelector(".agent-draft-content");
  const content = String(textarea?.value || "").trim();
  if (!content) return toast("草稿正文不能为空");
  const save = card.querySelector('[data-agent-action="save-draft"]');
  if (save) save.disabled = true;
  try {
    const data = await api(`/agent/actions/${Number(proposal.id)}/edit`, {
      method: "POST", body: { content },
    });
    if (!data.success) return toast(proposalError(data, "草稿保存失败，请重试"));
    mergeAgentProposal(data.action, advanceAgentProposalMutation());
    toast("草稿已更新，确认后才会保存为新版本");
  } catch (_error) {
    toast("网络连接失败，草稿未保存");
  } finally {
    if (save) save.disabled = false;
  }
}

async function handleProposalClick(event: any) {
  const button = event.target.closest("[data-agent-action]");
  if (!button) return;
  const card = button.closest("[data-proposal-id]");
  const proposalId = Number(card?.dataset.proposalId);
  const actionName = button.dataset.agentAction;
  const proposal = state.agentProposals.get(proposalId);
  if (card && proposal && actionName === "open-draft") {
    await openAgentResumeDraft(card, proposal);
    return;
  }
  if (card && proposal && actionName === "save-draft") {
    await saveAgentResumeDraft(card, proposal);
    return;
  }
  if (card && proposal && actionName === "retry-hydration") {
    const hydrationEpoch = advanceAgentProposalMutation();
    const source = proposal.hydrationSource || proposal;
    replaceProposalCard(card, { ...proposal, hydrationRetry: false, busy: true }, hydrationEpoch);
    const hydrated = await hydrateAgentProposal(source);
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    if (freshCard) replaceProposalCard(freshCard, hydrated, hydrationEpoch);
    return;
  }
  if (!card || !proposal || proposal.status !== "pending") return;
  const mutationEpoch = advanceAgentProposalMutation();
  const body = actionName === "edit" ? proposalChanges(card, proposal) : {};
  const startEvent = `${actionName}_start`;
  let next = contextualAgent.transitionProposal(proposal, startEvent);
  replaceProposalCard(card, next, mutationEpoch);
  try {
    const data = await api(`/agent/actions/${proposalId}/${actionName}`, { method: "POST", body });
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    if (!data.success) {
      next = contextualAgent.transitionProposal(next, `${actionName}_error`, {
        error: proposalError(data, "操作失败，请重试"),
      });
      if (freshCard) replaceProposalCard(freshCard, next, mutationEpoch);
      return;
    }
    const successEpoch = advanceAgentProposalMutation();
    next = contextualAgent.transitionProposal(next, `${actionName}_success`, { action: data.action });
    if (freshCard) replaceProposalCard(freshCard, next, successEpoch);
    const commandRefresh = loadAgentCommandCenter();
    if (actionName === "confirm") {
      await refreshAfterAgentAction(next.result);
      toast("操作已确认并完成");
    } else if (actionName === "cancel") {
      toast("操作已取消，业务数据未改变");
    } else {
      toast("预览已更新，请确认后执行");
    }
    await commandRefresh;
  } catch (_error) {
    const freshCard = $("chatLog").querySelector(`[data-proposal-id="${proposalId}"]`);
    next = contextualAgent.transitionProposal(next, `${actionName}_error`, { error: "网络连接失败，请重试" });
    if (freshCard) replaceProposalCard(freshCard, next, mutationEpoch);
  }
}

async function refreshAfterAgentAction(result: any) {
  const openOpportunityId = state.currentOpportunityId;
  await Promise.all([loadResumes(), loadApplications(), loadDashboard()]);
  if (openOpportunityId) {
    await loadOpportunityWorkspace(openOpportunityId, { isCurrent: () => true });
  }
  syncAgentContext();
}

function renderAgentWelcome() {
  state.agentConversationProposalIds.forEach((proposalId: any) => {
    if (!state.agentCommandProposalIds.has(proposalId)) state.agentProposals.delete(proposalId);
  });
  state.agentConversationProposalIds = new Set();
  $("chatLog").innerHTML = "";
  appendMessage(
    "你好，我是你的求职 Agent。无需 API Key 也能读取本地求职数据、诊断当前进度并安排下一步；配置模型后还可以处理更开放的问题。",
    "bot"
  );
}

function renderAgentEvents(events: any, status: any = "completed") {
  if (!events.length && status === "completed") return;
  const labels = {
    list_resumes: "读取简历列表",
    get_resume: "读取简历正文",
    analyze_resume: "分析简历",
    diagnose_resume: "本地诊断简历",
    prepare_resume_revision: "生成可编辑草稿",
    propose_career_action: "创建待确认操作",
    match_job: "匹配目标岗位",
    analyze_jd: "解析岗位 JD",
    get_interview_question: "获取面试题",
    generate_resume_interview_questions: "生成定制面试题",
    evaluate_answer: "评估面试回答",
    list_applications: "读取投递记录",
    get_dashboard: "读取求职看板",
    get_career_profile: "读取职业目标",
    list_action_items: "读取行动项",
    get_training_insights: "汇总训练记录",
    generate_career_report: "汇总求职报告",
    web_search: "搜索公开信息",
    fetch_webpage: "读取公开网页",
  };
  const rows = events.map((event: any) => `
    <span class="agent-event ${event.status === "success" ? "is-success" : "is-error"}">
      <i data-lucide="${event.status === "success" ? "check" : "triangle-alert"}"></i>
      ${escapeHtml((labels as Record<string, string>)[event.name] || event.name)}
    </span>
  `).join("");
  const statusText = status === "degraded" ? "本地执行" : status === "needs_input" ? "选择简历后继续" : "任务记录";
  const node = $("chatLog").lastElementChild;
  node?.insertAdjacentHTML("beforeend", `<div class="agent-events"><small>${statusText}</small>${rows}</div>`);
  renderIcons();
}

function renderAgentSuggestedActions(actions: any) {
  const html = contextualAgent.suggestedActionsHtml(actions);
  if (!html) return;
  const node = $("chatLog").lastElementChild;
  node?.insertAdjacentHTML("beforeend", html);
  renderIcons();
}

  return {
    loadCommandCenter: loadAgentCommandCenter,
    renderCommandOpportunities: renderAgentCommandOpportunities,
    openProposal: openAgentProposal,
    sendMessage: sendAgentMessage,
    generateCareerReport,
    loadConversations: loadAgentConversations,
    createConversation: createAgentConversation,
    clearConversation: clearAgentConversation,
    handleChatLogClick: handleAgentChatLogClick,
    focusResultFromLocation: resultFocus.focusFromLocation,
  };
}
