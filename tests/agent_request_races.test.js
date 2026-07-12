const assert = require("node:assert/strict");
const AgentUI = require("../static/js/contextual_agent.js");

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function main() {
  const conversationGate = AgentUI.createLatestRequestGate();
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
