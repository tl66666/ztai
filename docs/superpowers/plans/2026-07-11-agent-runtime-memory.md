# Agent Runtime and Layered Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the global-memory, regex-based ReAct loop with persistent per-user conversations, layered memory, schema-validated tools, structured model tool calls, and an honest local fallback.

**Architecture:** Flask routes call an `AgentService` that owns conversation lifecycle and delegates one run to `AgentOrchestrator`. The orchestrator builds relevant context from SQLite, asks the existing multi-provider gateway for a structured decision, executes tools through a registry, persists auditable events, and writes summaries/profile memories after completion. Existing business tables remain the source of truth.

**Tech Stack:** Python 3, Flask, SQLite, requests, unittest/pytest-compatible tests, vanilla JavaScript.

---

## File Map

- Create `utils/agent_runtime/__init__.py`: public runtime exports.
- Create `utils/agent_runtime/models.py`: typed messages, decisions, tool results, and run results.
- Create `utils/agent_runtime/memory.py`: SQLite conversation, task, run, and layered-memory repository.
- Create `utils/agent_runtime/tools.py`: JSON-Schema tool registry and migrated executors.
- Create `utils/agent_runtime/context.py`: bounded context selection and deterministic memory extraction.
- Create `utils/agent_runtime/local_policy.py`: no-Key intent and slot continuation policy.
- Create `utils/agent_runtime/orchestrator.py`: bounded structured decision loop.
- Create `utils/agent_runtime/service.py`: conversation lifecycle facade for Flask.
- Modify `utils/ai_client.py`: support `tools`, full assistant messages, and typed failures.
- Modify `app.py`: add tables, create runtime service, and expose conversation APIs.
- Modify `static/js/app.js`: persist a conversation ID, restore history, and render audit events.
- Modify `static/index.html`: add new-conversation and clear-current-conversation controls.
- Modify `static/css/style.css`: style the compact conversation controls and audit events.
- Create `tests/test_agent_memory.py`: persistence, isolation, summaries, and profile facts.
- Create `tests/test_agent_tools.py`: schema validation, ownership injection, and safe fetching.
- Create `tests/test_agent_orchestrator.py`: structured decisions, continuation, budgets, and fallback.
- Create `tests/test_agent_api.py`: Flask conversation endpoints and restart recovery.
- Modify `README.md`: document the implemented architecture and truthful fallback behavior.

### Task 1: Runtime Types and Persistent Conversation Store

**Files:**
- Create: `utils/agent_runtime/__init__.py`
- Create: `utils/agent_runtime/models.py`
- Create: `utils/agent_runtime/memory.py`
- Create: `tests/test_agent_memory.py`
- Modify: `app.py:126-203`

- [ ] **Step 1: Write failing persistence and isolation tests**

```python
def test_messages_are_isolated_by_user_and_conversation(tmp_path):
    db = str(tmp_path / "agent.db")
    create_agent_tables(db)
    store = MemoryStore(db)
    first = store.create_conversation(1, "第一段对话")
    second = store.create_conversation(2, "第二段对话")
    store.add_message(first.id, 1, "user", "我的目标是测试岗")
    store.add_message(second.id, 2, "user", "我的目标是运营岗")
    assert [m.content for m in store.list_messages(first.id, 1)] == ["我的目标是测试岗"]
    assert store.list_messages(first.id, 2) == []

def test_store_recovers_messages_after_recreation(tmp_path):
    db = str(tmp_path / "agent.db")
    create_agent_tables(db)
    conversation = MemoryStore(db).create_conversation(1, "恢复测试")
    MemoryStore(db).add_message(conversation.id, 1, "user", "记住杭州")
    assert MemoryStore(db).list_messages(conversation.id, 1)[0].content == "记住杭州"
```

- [ ] **Step 2: Run the tests and verify the expected failure**

Run: `python -m pytest tests/test_agent_memory.py -v`

Expected: collection fails because `utils.agent_runtime.memory` does not exist.

- [ ] **Step 3: Add typed records and the SQLite repository**

```python
# utils/agent_runtime/models.py
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class Conversation:
    id: str
    user_id: int
    title: str
    status: str = "active"

@dataclass(frozen=True)
class Message:
    id: int
    conversation_id: str
    user_id: int
    role: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ToolResult:
    ok: bool
    data: Any = None
    display_text: str = ""
    error_code: str = ""
    retryable: bool = False

@dataclass(frozen=True)
class AgentDecision:
    type: str
    tool: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    message: str = ""

@dataclass(frozen=True)
class AgentRunResult:
    reply: str
    status: str
    conversation_id: str
    events: list[dict[str, Any]] = field(default_factory=list)
    tools_used: list[str] = field(default_factory=list)
    ai_used: bool = False
```

Implement `create_agent_tables(db_path)` with the five tables and indexes from the design. Implement `MemoryStore.create_conversation`, `get_conversation`, `list_conversations`, `add_message`, `list_messages`, `clear_conversation`, `save_summary`, `upsert_memory`, `list_memories`, `create_task`, `update_task`, and `record_run`. Every read must filter by both conversation ID and user ID where applicable. Use `uuid.uuid4().hex`, `sqlite3.Row`, JSON metadata, parameterized SQL, and a fresh connection per operation.

Add the same idempotent DDL to `app.init_db()` so production startup creates the tables.

- [ ] **Step 4: Run memory tests**

Run: `python -m pytest tests/test_agent_memory.py -v`

Expected: all memory persistence and isolation tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py utils/agent_runtime tests/test_agent_memory.py
git commit -m "feat: add persistent agent conversation store"
```

### Task 2: Structured Multi-Provider Model Gateway

**Files:**
- Modify: `utils/ai_client.py:151-207`
- Create: `tests/test_ai_client_tools.py`

- [ ] **Step 1: Write failing gateway tests**

```python
def test_chat_sends_tools_and_returns_tool_calls(monkeypatch):
    response = FakeResponse(200, {"choices": [{"message": {
        "role": "assistant", "content": None,
        "tool_calls": [{"id": "call_1", "type": "function", "function": {
            "name": "get_dashboard", "arguments": "{}"}}]
    }}], "usage": {"total_tokens": 30}})
    monkeypatch.setattr("utils.ai_client.requests.post", lambda *a, **k: response)
    client = MultiModelAIClient(api_key="key")
    result = client.chat([{"role": "user", "content": "看板"}], tools=[DASHBOARD_SCHEMA])
    assert result["success"] is True
    assert result["message"]["tool_calls"][0]["function"]["name"] == "get_dashboard"

def test_remote_failure_is_diagnostic_not_fake_success(monkeypatch):
    monkeypatch.setattr("utils.ai_client.requests.post", lambda *a, **k: FakeResponse(429, {"error": "limited"}))
    result = MultiModelAIClient(api_key="key").chat([{"role": "user", "content": "你好"}])
    assert result["success"] is False
    assert result["error_code"] == "rate_limited"
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python -m pytest tests/test_ai_client_tools.py -v`

Expected: failures for unsupported `tools` and missing `message`/`error_code`.

- [ ] **Step 3: Extend `chat` without breaking existing callers**

Change the signature to:

```python
def chat(self, messages, temperature=0.6, max_tokens=2200, timeout=45,
         tools=None, tool_choice=None, response_format=None):
```

Only add optional payload fields when supplied. On HTTP 200 return `message`, `content`, `usage`, provider and model. Map 401/403 to `authentication_error`, 429 to `rate_limited`, timeout to `timeout`, other request failures to `network_error`, and malformed responses to `invalid_response`. Keep `_local_response` only when no key is configured; remote API failures must not be represented as successful AI output.

- [ ] **Step 4: Run gateway and existing tests**

Run: `python -m pytest tests/test_ai_client_tools.py tests/test_core_features.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add utils/ai_client.py tests/test_ai_client_tools.py
git commit -m "feat: support structured model tool calls"
```

### Task 3: Schema-Validated Tool Registry

**Files:**
- Create: `utils/agent_runtime/tools.py`
- Create: `tests/test_agent_tools.py`

- [ ] **Step 1: Write failing registry tests**

```python
def test_runtime_injects_user_id_instead_of_trusting_model(tmp_path):
    registry = build_tool_registry(str(seed_database(tmp_path)))
    result = registry.execute("list_resumes", {"user_id": 999}, user_id=1)
    assert result.ok
    assert all(item["user_id"] == 1 for item in result.data)

def test_invalid_arguments_return_stable_error(tmp_path):
    result = build_tool_registry(str(seed_database(tmp_path))).execute(
        "match_job", {"resume_id": "bad"}, user_id=1)
    assert result.error_code == "invalid_arguments"
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_agent_tools.py -v`

Expected: import failure for the new registry.

- [ ] **Step 3: Implement the registry and migrate tools**

```python
@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    executor: Callable[[dict, ToolContext], ToolResult]
    read_only: bool = True
    timeout_seconds: int = 10

class ToolRegistry:
    def schemas(self, names=None):
        selected = [t for t in self._tools.values() if names is None or t.name in names]
        return [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.parameters
        }} for t in selected]

    def execute(self, name, arguments, user_id):
        definition = self._tools.get(name)
        if not definition:
            return ToolResult(False, error_code="unknown_tool")
        errors = validate_arguments(definition.parameters, arguments)
        if errors:
            return ToolResult(False, display_text="工具参数不完整", error_code="invalid_arguments")
        safe_args = {k: v for k, v in arguments.items() if k != "user_id"}
        return definition.executor(safe_args, ToolContext(user_id=user_id, db_path=self.db_path))
```

Register `list_resumes`, `get_resume`, `analyze_resume`, `match_job`, `analyze_jd`, `get_interview_question`, `evaluate_answer`, `evaluate_salary`, `list_applications`, `get_dashboard`, `generate_career_report`, `web_search`, and `fetch_webpage`. Reuse existing analyzers and SQL logic, but return structured data. Implement the small JSON-Schema subset needed here: required fields, object/string/integer types, enums, minimum and maximum length.

For `fetch_webpage`, reject loopback/private/link-local hosts after DNS resolution, allow only HTTP/HTTPS, enforce text content types, disable unlimited redirects, and cap read content at 256 KB.

- [ ] **Step 4: Run tool tests**

Run: `python -m pytest tests/test_agent_tools.py -v`

Expected: validation, user isolation, resume retrieval, and URL-safety tests pass.

- [ ] **Step 5: Commit**

```bash
git add utils/agent_runtime/tools.py tests/test_agent_tools.py
git commit -m "feat: add schema validated agent tools"
```

### Task 4: Context Builder and Layered Memory

**Files:**
- Create: `utils/agent_runtime/context.py`
- Modify: `utils/agent_runtime/memory.py`
- Modify: `tests/test_agent_memory.py`

- [ ] **Step 1: Add failing context tests**

```python
def test_context_prefers_confirmed_relevant_memories(store):
    store.upsert_memory(1, "semantic", "preference", "city", "杭州", .95, "confirmed")
    store.upsert_memory(1, "semantic", "preference", "city", "上海", .55, "superseded")
    context = ContextBuilder(store, db_path=store.db_path).build(1, conversation_id, "杭州测试岗位")
    assert "杭州" in context.profile_facts
    assert "上海" not in context.profile_facts

def test_long_conversation_creates_rolling_summary(store):
    for index in range(18):
        store.add_message(conversation_id, 1, "user", f"第{index}条消息")
    assert ContextBuilder(store, store.db_path).needs_summary(conversation_id, 1)
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_agent_memory.py -v`

Expected: missing `ContextBuilder` and memory methods.

- [ ] **Step 3: Implement bounded context and deterministic fact extraction**

`ContextBuilder.build()` returns a `RuntimeContext` with summary, last 12 messages, active task, up to 8 confirmed/candidate facts sorted by confidence and keyword relevance, up to 3 related episodes, and a live career snapshot selected by detected task type. Cap each section and the combined serialized context.

Implement explicit-pattern extraction for stable facts:

```python
FACT_PATTERNS = {
    "target_city": re.compile(r"(?:想去|目标城市|优先考虑)([\u4e00-\u9fa5]{2,8})"),
    "target_role": re.compile(r"(?:目标岗位|想找|应聘)([\u4e00-\u9fa5A-Za-z0-9 /+-]{2,30})"),
    "salary_expectation": re.compile(r"(?:期望薪资|薪资期望|想要)(\d{1,3}[kK千万]?(?:[-~到]\d{1,3}[kK千万]?)?)"),
}
```

Only explicit matches become confirmed semantic memories. LLM-inferred facts, if later added, must enter as candidates. Implement a deterministic extractive summary fallback; when AI is available, the orchestrator may replace it with the fixed summary schema.

- [ ] **Step 4: Run memory/context tests**

Run: `python -m pytest tests/test_agent_memory.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add utils/agent_runtime/context.py utils/agent_runtime/memory.py tests/test_agent_memory.py
git commit -m "feat: add layered agent context and memory"
```

### Task 5: Bounded Orchestrator and Honest Local Policy

**Files:**
- Create: `utils/agent_runtime/local_policy.py`
- Create: `utils/agent_runtime/orchestrator.py`
- Create: `tests/test_agent_orchestrator.py`

- [ ] **Step 1: Write failing orchestrator tests**

```python
def test_orchestrator_executes_native_tool_call(fake_gateway, registry, store):
    fake_gateway.queue_tool("get_dashboard", {})
    fake_gateway.queue_final("你目前有 2 份简历。")
    result = make_orchestrator(fake_gateway, registry, store).run(1, conversation_id, "看我的进度")
    assert result.tools_used == ["get_dashboard"]
    assert result.status == "completed"

def test_missing_slot_persists_task_and_continues_next_turn(local_orchestrator):
    first = local_orchestrator.run(1, conversation_id, "帮我匹配岗位")
    assert first.status == "needs_input"
    second = local_orchestrator.run(1, conversation_id, "Python 测试工程师")
    assert second.status in {"completed", "degraded"}

def test_repeated_identical_tool_call_stops(fake_gateway, registry, store):
    fake_gateway.repeat_tool("get_dashboard", {})
    result = make_orchestrator(fake_gateway, registry, store).run(1, conversation_id, "看板")
    assert result.status == "degraded"
    assert len(result.tools_used) <= 2
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_agent_orchestrator.py -v`

Expected: imports fail for orchestrator and local policy.

- [ ] **Step 3: Implement structured decisions and bounded execution**

Implement `AgentOrchestrator.run(user_id, conversation_id, message)` with this contract:

```python
for iteration in range(self.max_iterations):
    decision = self.policy.decide(state, tool_schemas)
    if decision.type == "final":
        return finalize(decision.message, "completed")
    if decision.type == "needs_input":
        return finalize(decision.message, "needs_input")
    fingerprint = (decision.tool, canonical_json(decision.arguments))
    if fingerprint in state.call_fingerprints:
        return finalize("工具调用重复，已根据现有信息停止。", "degraded")
    result = self.tools.execute(decision.tool, decision.arguments, user_id)
    state.observe(decision.tool, result)
return finalize(state.best_available_answer(), "degraded")
```

`RemoteModelPolicy` uses native `tool_calls`; when absent, it accepts only the strict JSON decision object. `LocalPolicy` uses scored intents and persistent slots for internal deterministic tools. It must report `degraded`, never claim autonomous model reasoning, and directly return `needs_input` for missing resume/role/JD slots.

Persist user message before execution, assistant message after execution, tool audit events in message metadata, task state across turns, explicit facts from Task 4, a completed episode, and one `agent_runs` record even on failure.

- [ ] **Step 4: Run orchestrator tests**

Run: `python -m pytest tests/test_agent_orchestrator.py -v`

Expected: native calls, local continuation, duplicate detection, budgets, and error recovery pass.

- [ ] **Step 5: Commit**

```bash
git add utils/agent_runtime/local_policy.py utils/agent_runtime/orchestrator.py tests/test_agent_orchestrator.py
git commit -m "feat: replace regex react loop with bounded orchestrator"
```

### Task 6: Conversation Service and Flask APIs

**Files:**
- Create: `utils/agent_runtime/service.py`
- Modify: `utils/agent_runtime/__init__.py`
- Modify: `app.py:1649-1682`
- Create: `tests/test_agent_api.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_chat_creates_and_reuses_conversation(client):
    first = client.post("/api/agent/chat", json={"user_id": 1, "message": "你好"}).get_json()
    second = client.post("/api/agent/chat", json={
        "user_id": 1, "conversation_id": first["conversation_id"], "message": "继续"
    }).get_json()
    assert second["conversation_id"] == first["conversation_id"]

def test_clear_only_affects_requested_conversation(client):
    first = create_conversation(client, 1)
    second = create_conversation(client, 1)
    client.post(f"/api/agent/conversations/{first}/clear", json={"user_id": 1})
    assert list_messages(client, first, 1) == []
    assert list_messages(client, second, 1) != []
```

- [ ] **Step 2: Run and verify failure**

Run: `python -m pytest tests/test_agent_api.py -v`

Expected: conversation endpoints return 404 or lack `conversation_id`.

- [ ] **Step 3: Implement service and routes**

Create one lazy `get_agent_service()` bound to `DB_PATH`. Add:

```python
@app.post("/api/agent/conversations")
def create_agent_conversation(): ...

@app.get("/api/agent/conversations/<int:user_id>")
def list_agent_conversations(user_id): ...

@app.get("/api/agent/conversations/<conversation_id>/messages")
def list_agent_messages(conversation_id): ...

@app.post("/api/agent/conversations/<conversation_id>/clear")
def clear_agent_conversation(conversation_id): ...
```

Update `/api/agent/chat` to accept `user_id` and optional `conversation_id`, create a conversation when missing, and return `reply`, `status`, `conversation_id`, `events`, `suggested_actions`, `tools_used`, and `ai_used`. Replace the global `/clear-memory` behavior with a deprecated wrapper that requires a conversation ID and never clears all users.

- [ ] **Step 4: Run API and regression tests**

Run: `python -m pytest tests/test_agent_api.py tests/test_core_features.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app.py utils/agent_runtime/service.py utils/agent_runtime/__init__.py tests/test_agent_api.py
git commit -m "feat: expose persistent agent conversation APIs"
```

### Task 7: Frontend Conversation Continuity and Audit Events

**Files:**
- Modify: `static/index.html`
- Modify: `static/js/app.js:1668-1696`
- Modify: `static/css/style.css`

- [ ] **Step 1: Add a browser-visible acceptance fixture**

Add stable IDs `agentConversationSelect`, `newAgentConversation`, and `clearAgentConversation` near the existing coach header. Keep controls compact and accessible with labels/tooltips.

- [ ] **Step 2: Implement conversation state and API calls**

```javascript
const AGENT_CONVERSATION_KEY = `jobhunter-agent-conversation-${USER_ID}`;

async function ensureAgentConversation() {
  const saved = localStorage.getItem(AGENT_CONVERSATION_KEY);
  if (saved) return saved;
  const data = await api("/agent/conversations", { method: "POST", body: { user_id: USER_ID } });
  localStorage.setItem(AGENT_CONVERSATION_KEY, data.conversation.id);
  return data.conversation.id;
}
```

On coach view load, list conversations and restore messages. Send `user_id` and `conversation_id` with chat. New conversation creates and selects one; clear affects only the selected conversation. Render `events` as compact status rows using escaped labels and Lucide icons. Remove the “Agent autonomous reasoning process” wording.

- [ ] **Step 3: Run static syntax and backend tests**

Run: `node --check static/js/app.js`

Expected: no syntax errors.

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add static/index.html static/js/app.js static/css/style.css
git commit -m "feat: add persistent agent conversations to coach ui"
```

### Task 8: Documentation, Full Verification, and Browser QA

**Files:**
- Modify: `README.md`
- Modify: `docs/PRODUCT_AUDIT.md`

- [ ] **Step 1: Update product documentation**

Document persistent conversation memory, the six memory layers, structured tool calls, honest degraded mode, conversation APIs, and safety limits. Remove claims that the no-Key keyword router is a true autonomous Agent. Keep the tool count aligned with the actual registry after the split of list/get resume.

- [ ] **Step 2: Run the complete automated suite**

Run: `python -m pytest -v`

Expected: all original and new tests pass with no unexpected warnings.

Run: `python -m compileall app.py utils tests`

Expected: compilation succeeds.

Run: `node --check static/js/app.js`

Expected: no syntax errors.

- [ ] **Step 3: Start the server and perform browser QA**

Run: `python app.py`

Verify at `http://127.0.0.1:5000`:

1. Create a conversation and send “我想找杭州的 Python 测试岗位”。
2. Ask “按刚才的岗位看看我的简历”，confirm the earlier role is reused.
3. Refresh, confirm both messages return.
4. Create a second conversation, confirm it starts without the first transcript.
5. Switch back, clear only the first conversation, and confirm the second remains.
6. Confirm audit events show tool names/status but no raw private reasoning.
7. Confirm layout has no overlap at 1440x900 and 390x844.

- [ ] **Step 4: Inspect the database and working tree**

Run: `python -c "import sqlite3; c=sqlite3.connect('jobhunter.db'); print({t:c.execute('select count(*) from '+t).fetchone()[0] for t in ['agent_conversations','agent_messages','agent_tasks','agent_memories','agent_runs']})"`

Expected: conversations/messages/runs are nonzero after QA and no query errors occur.

Run: `git status --short`

Expected: only intentional QA artifacts, if any, are listed; do not commit database or generated uploads.

- [ ] **Step 5: Commit documentation**

```bash
git add README.md docs/PRODUCT_AUDIT.md
git commit -m "docs: describe layered memory agent runtime"
```

## Plan Self-Review

- Spec coverage: storage, six memory layers, model tool calls, JSON compatibility, tools, local fallback, API, frontend, safety, tests, metrics, migration, and docs are each assigned to a task.
- Scope: all tasks contribute to one independently deployable Agent Runtime; no multi-agent or vector-search work is included.
- Type consistency: `Conversation`, `Message`, `ToolResult`, `AgentDecision`, `AgentRunResult`, `MemoryStore`, `ToolRegistry`, `ContextBuilder`, `AgentOrchestrator`, and `AgentService` names are stable throughout.
- Migration safety: only additive SQLite DDL is planned; existing business tables remain unchanged.
