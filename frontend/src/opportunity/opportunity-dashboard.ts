import type { OpportunityControllerDependencies } from "./opportunity-controller";

export interface OpportunityDashboard {
  evaluateSalary(): Promise<void>;
  load(): Promise<void>;
  renderCareerPulse(pulse: any): void;
  renderNextActions(actions: any[]): void;
}

function required<T extends HTMLElement>(
  byId: OpportunityControllerDependencies["byId"],
  id: string,
): T {
  const node = byId(id);
  if (!node) throw new Error(`Missing dashboard control: #${id}`);
  return node as T;
}

export function createOpportunityDashboard(
  deps: OpportunityControllerDependencies,
): OpportunityDashboard {
  const { userId, request, byId, escapeHtml, renderIcons } = deps;

  async function evaluateSalary(): Promise<void> {
    const data = await request("/salary/evaluate", {
      method: "POST",
      body: {
        job_type: required<HTMLInputElement>(byId, "salaryJob").value,
        experience: required<HTMLInputElement>(byId, "salaryExp").value,
        city: required<HTMLInputElement>(byId, "salaryCity").value,
        skills_count: Number(required<HTMLInputElement>(byId, "salarySkills").value || 0),
      },
    });
    const result = required(byId, "salaryResult");
    result.classList.remove("hidden");
    result.innerHTML = `<h4>${data.range.min} - ${data.range.max} / 月</h4><div>参考中位：${data.range.avg} / 月</div><div>${escapeHtml(data.advice)}</div>`;
  }

  function renderCareerPulse(pulse: any): void {
    if (!byId("careerPulse")) return;
    required(byId, "readinessScore").textContent = String(pulse.score ?? 0);
    required(byId, "readinessLabel").textContent = pulse.label || "待启动";
    required(byId, "readinessSummary").textContent = pulse.summary
      || "系统会根据简历、JD 匹配、面试训练和投递进度，给出下一步最该做的动作。";
    required(byId, "pulseBlockers").innerHTML = (pulse.blockers || [])
      .map((item: unknown) => `<span>${escapeHtml(item)}</span>`)
      .join("");
    required(byId, "weeklyPlan").innerHTML = (pulse.weekly_plan || [])
      .map((item: any, index: number) => `
        <button class="plan-step" onclick="jumpToModule('${item.page}', '${item.module}')">
          <b>${index + 1}</b>
          <span>${escapeHtml(item.title)}</span>
          <i data-lucide="arrow-right"></i>
        </button>
      `).join("");
    renderIcons();
  }

  function renderNextActions(actions: any[]): void {
    const box = byId("nextActions");
    if (!box) return;
    box.innerHTML = actions.length ? actions.map((action) => `
      <article class="next-action-card">
        <div>
          <b>${escapeHtml(action.title)}</b>
          <small>${escapeHtml(action.description)}</small>
        </div>
        <button class="ghost small" onclick="jumpToModule('${action.page}', '${action.module}')">${escapeHtml(action.cta || "去处理")}</button>
      </article>
    `).join("") : "";
  }

  async function load(): Promise<void> {
    const data = await request(`/dashboard/${userId}`);
    if (!data.success) return;
    required(byId, "statResumes").textContent = String(data.stats.resumes);
    required(byId, "statInterviews").textContent = String(data.stats.interviews);
    required(byId, "statMatches").textContent = String(data.stats.matches);
    required(byId, "statApps").textContent = String(data.stats.applications);
    renderNextActions(data.next_actions || []);
    renderCareerPulse(data.career_pulse || {});
  }

  return { evaluateSalary, load, renderCareerPulse, renderNextActions };
}
