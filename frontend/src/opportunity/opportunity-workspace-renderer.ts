import type { OpportunityControllerDependencies } from "./opportunity-controller";

export interface OpportunityWorkspaceRenderer {
  render(workspace: any): void;
  date(value: unknown, fallback?: string): string;
  overview(workspace: any): void;
  match(workspace: any): void;
  resume(workspace: any): void;
  interview(workspace: any): void;
  timeline(workspace: any): void;
}

function required(
  byId: OpportunityControllerDependencies["byId"],
  id: string,
): HTMLElement {
  const node = byId(id);
  if (!node) throw new Error(`Missing opportunity workspace control: #${id}`);
  return node;
}

export function createOpportunityWorkspaceRenderer(
  deps: OpportunityControllerDependencies,
): OpportunityWorkspaceRenderer {
  const {
    byId,
    escapeHtml,
    renderIcons,
    syncAgentContext,
    parseFeedbackSummary,
  } = deps;

  function date(value: unknown, fallback = "未设置"): string {
    const formatted = value ? new Date(String(value)).toLocaleString() : fallback;
    return escapeHtml(formatted);
  }

  function overview(workspace: any): void {
    const opportunity = workspace.opportunity || {};
    const status = opportunity.needs_status_review
      ? `待确认（原状态：${opportunity.status || "未设置"}）`
      : opportunity.status || "未设置";
    required(byId, "opportunity-overview").innerHTML = `
      ${opportunity.needs_status_review ? '<p class="status-warning"><i data-lucide="triangle-alert"></i>这是旧版状态，请编辑并选择当前标准阶段。</p>' : ""}
      <dl class="opportunity-facts">
        <div><dt>公司</dt><dd>${escapeHtml(opportunity.company || "未填写")}</dd></div>
        <div><dt>岗位</dt><dd>${escapeHtml(opportunity.job_title || "未填写")}</dd></div>
        <div><dt>阶段</dt><dd>${escapeHtml(status)}</dd></div>
        <div><dt>城市</dt><dd>${escapeHtml(opportunity.city || "未填写")}</dd></div>
        <div><dt>优先级</dt><dd>${escapeHtml(opportunity.priority == null ? "未设置" : String(opportunity.priority))}</dd></div>
        <div><dt>下一步</dt><dd>${date(opportunity.next_action_at)}</dd></div>
        <div><dt>面试时间</dt><dd>${date(opportunity.interview_at)}</dd></div>
        <div><dt>投递时间</dt><dd>${date(opportunity.applied_at || opportunity.created_at)}</dd></div>
      </dl>
      ${opportunity.notes ? `<div class="workspace-note"><b>备注</b><p>${escapeHtml(opportunity.notes)}</p></div>` : ""}
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-edit" data-opportunity-id="${opportunity.id}"><i data-lucide="pencil"></i>编辑机会</button></div>`;
  }

  function match(workspace: any): void {
    const matches = workspace.matches || [];
    const jd = workspace.opportunity?.jd_text || "";
    required(byId, "opportunity-match").innerHTML = `
      <section class="workspace-section"><h4>岗位 JD</h4>
        ${jd ? `<div class="workspace-long-text">${escapeHtml(workspace.opportunity.jd_text)}</div>` : '<div class="opportunity-empty"><b>尚未保存 JD</b><span>回到 JD 匹配区粘贴岗位描述，再生成匹配结果。</span></div>'}
      </section>
      <section class="workspace-section"><h4>最近匹配</h4>
        ${matches.length ? `<div class="workspace-list">${matches.map((item: any) => `
          <div class="workspace-row"><div><b>${escapeHtml(item.job_title || "目标岗位")}</b><span>${escapeHtml(item.resume_title || "关联简历")} · ${date(item.created_at)}</span></div><strong>${escapeHtml(item.match_score == null ? "未评分" : `${item.match_score} 分`)}</strong>
          ${item.analysis ? `<p>${escapeHtml(item.analysis)}</p>` : ""}
          ${Object.keys(item.details || {}).length ? `<pre>${escapeHtml(JSON.stringify(item.details, null, 2))}</pre>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>尚无匹配结果</b><span>使用这份 JD 和关联简历完成一次匹配。</span></div>'}
      </section>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-use-jd"><i data-lucide="scan-search"></i>${jd ? "用此 JD 重新匹配" : "前往 JD 匹配"}</button></div>`;
  }

  function resume(workspace: any): void {
    const selected = workspace.resume;
    required(byId, "opportunity-resume").innerHTML = selected ? `
      <div class="workspace-version">
        <i data-lucide="file-text"></i><div><b>${escapeHtml(selected.title || "未命名简历")}</b><span>${escapeHtml(selected.version_label || "已关联版本")} · ${date(selected.updated_at || selected.created_at)}</span><small>${escapeHtml(selected.target_job_title || workspace.opportunity.job_title || "目标岗位")}</small></div>
      </div>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-open-resume" data-resume-id="${selected.id}" data-has-original="${selected.has_original ? "true" : "false"}"><i data-lucide="external-link"></i>${selected.has_original ? "打开简历原件" : "查看简历版本"}</button></div>` : `
      <div class="opportunity-empty"><b>尚未关联简历版本</b><span>选择一份与该岗位匹配的简历，再从 JD 区新建机会。</span></div>
      <div class="workspace-primary-action"><button type="button" class="primary" data-route-page="resume" data-route-module="input"><i data-lucide="file-plus-2"></i>准备简历</button></div>`;
  }

  function interview(workspace: any): void {
    const interviews = workspace.interviews || [];
    const actions = workspace.actions || [];
    const action = actions.find((item: any) => (
      ["interview", "interview_plan", "mock_interview"].includes(item.action_type)
      && ["pending", "in_progress"].includes(item.status)
    ));
    required(byId, "opportunity-interview").innerHTML = `
      <section class="workspace-section"><h4>面试记录</h4>
        ${interviews.length ? `<div class="workspace-list">${interviews.map((item: any) => `
          <div class="workspace-row"><div><b>${escapeHtml(item.job_title || "模拟面试")}</b><span>状态：${escapeHtml(item.status || "未设置")} · 阶段：${escapeHtml(item.current_stage || "未开始")}</span></div>${item.score == null ? "" : `<strong>${escapeHtml(`${item.score} 分`)}</strong>`}
            ${item.feedback ? `<p>${escapeHtml(parseFeedbackSummary(item.feedback) || item.feedback)}</p>` : ""}
            ${item.status === "active" ? `<button type="button" class="ghost" data-command="opportunity-continue-interview" data-session-id="${item.id}"><i data-lucide="play"></i>继续面试</button>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>尚无面试记录</b><span>从当前机会开始模拟面试，系统会保留机会和简历关联。</span></div>'}
      </section>
      <section class="workspace-section"><h4>准备行动</h4>
        ${actions.length ? `<div class="workspace-list">${actions.map((item: any) => `<div class="workspace-row"><div><b>${escapeHtml(item.title)}</b><span>${escapeHtml(item.status || "pending")} · ${date(item.due_at, "无截止时间")}</span></div>${item.description ? `<p>${escapeHtml(item.description)}</p>` : ""}</div>`).join("")}</div>` : '<div class="opportunity-empty"><b>暂无准备行动</b><span>先开始一轮模拟面试，再根据反馈补充行动。</span></div>'}
      </section>
      <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-prepare-interview"${action?.id ? ` data-action-id="${action.id}"` : ""}><i data-lucide="messages-square"></i>开始新面试</button></div>`;
  }

  function timeline(workspace: any): void {
    const events = workspace.timeline || [];
    required(byId, "opportunity-timeline").innerHTML = events.length
      ? `<ol class="workspace-timeline">${events.map((event: any) => `
        <li><i data-lucide="circle-dot"></i><div><b>${escapeHtml(event.event_type || "记录更新")}</b><span>${date(event.occurred_at)} · ${escapeHtml(event.source || "system")}</span></div></li>`).join("")}</ol>`
      : `<div class="opportunity-empty"><b>暂无时间线事件</b><span>编辑阶段、添加行动或开始面试后，事件会显示在这里。</span></div>
        <div class="workspace-primary-action"><button type="button" class="primary" data-command="opportunity-refresh" data-opportunity-id="${workspace.opportunity.id}"><i data-lucide="refresh-cw"></i>刷新时间线</button></div>`;
  }

  function render(workspace: any): void {
    const opportunity = workspace.opportunity || {};
    required(byId, "opportunityWorkspaceError").classList.add("hidden");
    required(byId, "opportunityWorkspaceTitle").textContent = `${opportunity.company || "未命名公司"} / ${opportunity.job_title || "目标岗位"}`;
    required(byId, "opportunityWorkspaceSubtitle").textContent = `当前阶段：${opportunity.needs_status_review ? "待确认" : opportunity.status || "未设置"}`;
    overview(workspace);
    match(workspace);
    resume(workspace);
    interview(workspace);
    timeline(workspace);
    syncAgentContext();
    renderIcons();
  }

  return { render, date, overview, match, resume, interview, timeline };
}
