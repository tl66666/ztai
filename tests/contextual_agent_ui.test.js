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
    user_id: 1,
    conversation_id: "conversation-1",
    message: "hello",
    context: { module: "resume:jd", opportunity_id: 42, resume_id: 7 },
  },
  "the browser sends user text and identifiers, never entity content",
);

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

console.log("contextual agent behavior tests passed");
