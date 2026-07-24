const assert = require("node:assert/strict");
const AgentUI = require("../frontend/src/agent/contextual-agent.mjs");

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function main() {
  const conversationGate = AgentUI.createConversationEpoch();
  const slowMessagesA = deferred();
  const slowHydrationA = deferred();
  const conversationCommits = [];

  async function restore(conversationId, messageFetch, hydrationFetch) {
    const request = conversationGate.begin(conversationId);
    const messages = await messageFetch();
    if (!conversationGate.isCurrent(request, conversationId)) return;
    const hydrated = await hydrationFetch(messages);
    if (!conversationGate.isCurrent(request, conversationId)) return;
    conversationCommits.push({ conversationId, hydrated });
  }

  const restoreA = restore("A", () => slowMessagesA.promise, () => slowHydrationA.promise);
  slowMessagesA.resolve(["A message"]);
  await Promise.resolve();
  const restoreB = restore("B", async () => ["B message"], async () => ["B current"]);
  await restoreB;
  slowHydrationA.resolve(["A stale"]);
  await restoreA;
  assert.deepEqual(conversationCommits, [
    { conversationId: "B", hydrated: ["B current"] },
  ], "slow A hydration cannot overwrite or mix into conversation B");

  const sendEpoch = AgentUI.createConversationEpoch();
  const sendHydration = deferred();
  const sendResponse = deferred();
  const sendCommits = [];
  let selectedConversation = "A";
  const staleRestore = (async () => {
    const request = sendEpoch.begin("A");
    const hydrated = await sendHydration.promise;
    if (sendEpoch.isCurrent(request, selectedConversation)) sendCommits.push(hydrated);
  })();
  sendEpoch.invalidate();
  sendCommits.push("A user message");
  const send = (async () => {
    const response = await sendResponse.promise;
    if (selectedConversation === "A" && response.conversation_id === "A") {
      sendCommits.push(response.reply);
    }
  })();
  sendHydration.resolve("stale restored history");
  selectedConversation = "B";
  sendEpoch.begin("B");
  sendResponse.resolve({ conversation_id: "A", reply: "stale A reply" });
  await Promise.all([staleRestore, send]);
  assert.deepEqual(
    sendCommits,
    ["A user message"],
    "send invalidates restore and an A response cannot commit after switching to B",
  );

  for (const local of [
    { id: 9, status: "completed", preview: "confirmed result" },
    { id: 9, status: "cancelled", preview: "cancelled result" },
    { id: 9, status: "expired", preview: "expired result" },
    { id: 9, status: "failed", preview: "failed result" },
  ]) {
    const merged = AgentUI.mergeProposalState(
      local,
      { id: 9, status: "pending", preview: "stale restore" },
      { currentEpoch: 2, incomingEpoch: 1 },
    );
    assert.deepEqual(merged, local, `${local.status} cannot be downgraded to pending`);
  }
  const edited = { id: 9, status: "pending", preview: "new edited preview" };
  assert.deepEqual(
    AgentUI.mergeProposalState(
      edited,
      { id: 9, status: "pending", preview: "old preview" },
      { currentEpoch: 3, incomingEpoch: 1 },
    ),
    edited,
    "old hydration cannot overwrite a newer edit preview",
  );
  const revisionTwo = { id: 9, status: "pending", preview: "revision 2", revision: 2 };
  assert.deepEqual(
    AgentUI.mergeProposalState(
      revisionTwo,
      { id: 9, status: "pending", preview: "revision 1", revision: 1 },
      { currentEpoch: 3, incomingEpoch: 3 },
    ),
    revisionTwo,
  );
  const newerTimestamp = {
    id: 9, status: "pending", preview: "newer", updated_at: "2026-07-12T10:00:00Z",
  };
  assert.deepEqual(
    AgentUI.mergeProposalState(
      newerTimestamp,
      { id: 9, status: "pending", preview: "older", updated_at: "2026-07-12T09:00:00Z" },
      { currentEpoch: 3, incomingEpoch: 3 },
    ),
    newerTimestamp,
  );

  const mutationEpoch = AgentUI.createConversationEpoch();
  const staleProposalHydration = deferred();
  const proposalCommits = [];
  const restoreProposal = (async () => {
    const request = mutationEpoch.begin("A");
    const staleProposal = await staleProposalHydration.promise;
    if (mutationEpoch.isCurrent(request, "A")) proposalCommits.push(staleProposal);
  })();
  mutationEpoch.invalidate();
  proposalCommits.push({ id: 9, status: "completed", preview: "local terminal" });
  staleProposalHydration.resolve({ id: 9, status: "pending", preview: "old restore" });
  await restoreProposal;
  assert.deepEqual(proposalCommits, [
    { id: 9, status: "completed", preview: "local terminal" },
  ], "proposal mutation invalidates outstanding restore DOM and Map commit");

  const commandGate = AgentUI.createLatestRequestGate();
  const oldPendingFetch = deferred();
  const commandCommits = [];
  async function loadCommands(fetchActions) {
    const request = commandGate.begin("command-center");
    const actions = await fetchActions();
    if (!commandGate.isCurrent(request, "command-center")) return;
    commandCommits.push(actions);
  }

  const oldLoad = loadCommands(() => oldPendingFetch.promise);
  const newLoad = loadCommands(async () => []);
  await newLoad;
  oldPendingFetch.resolve([{ id: 9, status: "pending" }]);
  await oldLoad;
  assert.deepEqual(commandCommits, [[]], "an old pending response cannot downgrade a newer empty result");

  console.log("agent request race tests passed");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
