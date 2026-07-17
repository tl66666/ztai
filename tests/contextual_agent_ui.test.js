const assert = require("node:assert/strict");
const AgentUI = require("../static/js/contextual_agent.js");

const contexts = AgentUI.createContextStore();
contexts.sync({ module: "resume:jd", opportunityId: 41, resumeId: 7 });
assert.deepEqual(contexts.payload(), {
  module: "resume:jd",
  opportunity_id: 41,
  resume_id: 7,
});
contexts.remove("opportunity");
contexts.sync({ module: "resume:jd", opportunityId: 41, resumeId: 7 });
assert.equal(contexts.payload().opportunity_id, undefined, "removed entity stays removed in the current context");
contexts.sync({ module: "resume:jd", opportunityId: 42, resumeId: 7 });
assert.equal(contexts.payload().opportunity_id, 42, "a genuinely new entity is synchronized");
assert.deepEqual(
  AgentUI.chatPayload("hello", "conversation-1", contexts.payload()),
  {
    conversation_id: "conversation-1",
    message: "hello",
    context: { module: "resume:jd", opportunity_id: 42, resume_id: 7 },
  },
  "the browser sends user text and identifiers, never entity content",
);
assert.ok(!("user_id" in AgentUI.chatPayload("hello", "conversation-1", {})));

const resumeRequest = {
  kind: "resume_select",
  workflow: "revision",
  prompt: "选择要进行优化草稿的简历",
  options: [
    { id: 7, label: '<script>resume</script>', preview: '<img src=x>' },
  ],
};
const requestHtml = AgentUI.inputRequestHtml(resumeRequest);
assert.ok(requestHtml.includes('data-agent-resume-choice="7"'));
assert.ok(requestHtml.includes("&lt;script&gt;resume"));
assert.ok(requestHtml.includes("&lt;img"));
assert.ok(!requestHtml.includes("<script>resume"));
assert.ok(!requestHtml.includes("<img src=x>"));
assert.equal(AgentUI.selectionMessage(resumeRequest, 7), "选择简历 #7，生成优化草稿");

const proposal = {
  id: 9,
  action_type: "create_opportunity",
  preview: '<img src=x onerror="owned()">',
  risk_level: "medium",
  status: "pending",
  editable: { company: '<script>owned()</script>', priority: 2 },
};
const restored = AgentUI.proposalsFromMetadata({ action_proposals: [proposal] });
assert.equal(restored.length, 1);
assert.equal(restored[0].id, 9);
const rendered = AgentUI.proposalHtml(restored[0]);
assert.ok(rendered.includes("&lt;img"));
assert.ok(rendered.includes("&lt;script&gt;"));
assert.ok(!rendered.includes("<script>"));
assert.ok(rendered.includes('data-agent-action="confirm"'));
assert.ok(rendered.includes('data-agent-action="cancel"'));
assert.ok(rendered.includes('data-agent-edit-field="company"'));

let actionState = AgentUI.transitionProposal(proposal, "confirm_start");
assert.equal(actionState.busy, true);
assert.equal(actionState.status, "pending");
actionState = AgentUI.transitionProposal(actionState, "confirm_error", { error: "network" });
assert.equal(actionState.busy, false);
assert.equal(actionState.status, "pending");
assert.equal(actionState.error, "network");
actionState = AgentUI.transitionProposal(actionState, "confirm_success", {
  action: { ...proposal, status: "completed", result: { entity_type: "opportunity", id: 41 } },
});
assert.equal(actionState.status, "completed");
assert.equal(actionState.result.id, 41);
assert.ok(!AgentUI.proposalHtml(actionState).includes('data-agent-action="confirm"'));

let cancelled = AgentUI.transitionProposal(proposal, "cancel_start");
cancelled = AgentUI.transitionProposal(cancelled, "cancel_success", {
  action: { ...proposal, status: "cancelled" },
});
assert.equal(cancelled.status, "cancelled");
assert.ok(!AgentUI.proposalHtml(cancelled).includes('data-agent-action="cancel"'));

for (const kind of ["not_found", "forbidden", "server", "network"]) {
  const unavailable = AgentUI.unavailableProposal(proposal, kind);
  const html = AgentUI.proposalHtml(unavailable);
  assert.notEqual(unavailable.status, "pending");
  assert.deepEqual(unavailable.editable, {});
  assert.ok(!html.includes('data-agent-action="confirm"'));
  assert.ok(!html.includes('data-agent-action="cancel"'));
  assert.equal(
    html.includes('data-agent-action="retry-hydration"'),
    kind === "server" || kind === "network",
  );
}

const retrySource = AgentUI.unavailableProposal(proposal, "network");
const retryBusy = { ...retrySource, hydrationRetry: false, busy: true };
const hydratedPending = AgentUI.mergeProposalState(
  retryBusy,
  AgentUI.authoritativeHydrationSuccess({
    ...proposal,
    status: "pending",
    preview: "fresh authoritative preview",
  }),
  { currentEpoch: 2, incomingEpoch: 2 },
);
assert.equal(hydratedPending.busy, false);
assert.equal(hydratedPending.error, "");
assert.equal(hydratedPending.hydrationRetry, false);
assert.equal(hydratedPending.hydrationSource, null);
const hydratedPendingHtml = AgentUI.proposalHtml(hydratedPending);
assert.ok(hydratedPendingHtml.includes('data-agent-action="edit"'));
assert.ok(hydratedPendingHtml.includes('data-agent-action="confirm"'));
assert.ok(hydratedPendingHtml.includes('data-agent-action="cancel"'));
assert.ok(!hydratedPendingHtml.includes("disabled"));

const hydratedCompleted = AgentUI.mergeProposalState(
  retryBusy,
  AgentUI.authoritativeHydrationSuccess({
    ...proposal,
    status: "completed",
    result: { entity_type: "opportunity", id: 41 },
  }),
  { currentEpoch: 2, incomingEpoch: 2 },
);
assert.equal(hydratedCompleted.status, "completed");
assert.equal(hydratedCompleted.busy, false);
assert.equal(hydratedCompleted.error, "");
assert.equal(hydratedCompleted.hydrationRetry, false);
assert.equal(hydratedCompleted.hydrationSource, null);
const hydratedCompletedHtml = AgentUI.proposalHtml(hydratedCompleted);
assert.ok(hydratedCompletedHtml.includes("data-agent-result-link"));
assert.ok(!hydratedCompletedHtml.includes('data-agent-action="confirm"'));
assert.ok(!hydratedCompletedHtml.includes('data-agent-action="retry-hydration"'));

assert.equal(AgentUI.hydrationFailureKind({ http_status: 404 }), "not_found");
assert.equal(AgentUI.hydrationFailureKind({ http_status: 403 }), "forbidden");
assert.equal(AgentUI.hydrationFailureKind({ http_status: 500 }), "server");
assert.equal(AgentUI.hydrationFailureKind(null, new Error("offline")), "network");

assert.deepEqual(AgentUI.resultRoute({ entity_type: "opportunity", id: 41 }), {
  page: "tracker", module: "board", key: "opportunity", id: 41,
});
assert.deepEqual(AgentUI.resultRoute({ entity_type: "resume", id: 7 }), {
  page: "resume", module: "manage", key: "resume", id: 7,
});
assert.deepEqual(AgentUI.resultRoute({ entity_type: "action_item", id: 5 }), {
  page: "agent", module: null, key: "action", id: 5,
});
assert.deepEqual(AgentUI.resultRoute({ entity_type: "career_profile", id: 3 }), {
  page: "home", module: null, key: "profile", id: 3,
});
assert.deepEqual(AgentUI.resultRoute({ entity_type: "career_report", id: 11 }), {
  page: "agent", module: null, key: "report", id: 11,
});
for (const result of [
  { entity_type: "opportunity", id: 41 },
  { entity_type: "resume", id: 7 },
  { entity_type: "action_item", id: 5 },
  { entity_type: "career_profile", id: 3 },
  { entity_type: "career_report", id: 11 },
]) {
  assert.ok(AgentUI.resultHref(result).includes(`=${result.id}`));
}

const canonicalStatuses = ["意向", "已投递", "Offer", "已拒绝", "已结束"];
assert.equal(AgentUI.isActiveOpportunity("Offer", canonicalStatuses), true);
assert.equal(AgentUI.isActiveOpportunity("已结束", canonicalStatuses), false);
assert.equal(AgentUI.isActiveOpportunity("已拒绝", canonicalStatuses), false);
assert.equal(AgentUI.isActiveOpportunity("旧版未知状态", canonicalStatuses), true);

assert.deepEqual(
  AgentUI.resultLookupState(7, { success: true, data: { id: 7, title: "Weekly" } }),
  { status: "located", retry: false, entity: { id: 7, title: "Weekly" } },
);
assert.deepEqual(
  AgentUI.resultLookupState(7, { success: true, data: { id: 8 } }),
  { status: "missing", retry: false, entity: null },
);
assert.deepEqual(
  AgentUI.resultLookupState(7, { success: false, http_status: 404 }),
  { status: "missing", retry: false, entity: null },
);
assert.deepEqual(
  AgentUI.resultLookupState(7, { success: false, http_status: 500 }),
  { status: "unavailable", retry: true, entity: null },
);
assert.deepEqual(
  AgentUI.resultLookupState(7, null, new Error("offline")),
  { status: "unavailable", retry: true, entity: null },
);

const profileResult = AgentUI.profileResultHtml({
  id: 7,
  target_role: '<img src=x onerror="owned()">Backend Engineer',
  cities: ["Shanghai", "<script>owned()</script>"],
  salary: { min: 20, max: 30 },
});
assert.ok(profileResult.includes('id="focusedAgentResult"'));
assert.ok(profileResult.includes('data-profile-id="7"'));
assert.ok(profileResult.includes("Backend Engineer"));
assert.ok(profileResult.includes("Shanghai"));
assert.ok(profileResult.includes("20"));
assert.ok(profileResult.includes("30"));
assert.ok(profileResult.includes("&lt;img"));
assert.ok(profileResult.includes("&lt;script&gt;"));
assert.ok(!profileResult.includes("<img"));
assert.ok(!profileResult.includes("<script>"));

console.log("contextual agent behavior tests passed");
