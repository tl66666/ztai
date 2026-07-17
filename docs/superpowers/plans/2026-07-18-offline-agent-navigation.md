# Offline Agent Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the no-Key career Agent turn a user's current job-search state into safe, clickable next steps through the existing JobHunter workflow.

**Architecture:** `LocalPolicy` recognizes a guided-start intent and, after its existing bounded reads, emits validated navigation suggestions based on missing profile, resume, JD match, interview, and opportunity evidence. `AgentOrchestrator` persists those suggestions in assistant-message metadata; `AgentService` uses a safe route fallback for all other tool-based runs. The browser reuses the existing suggested-action renderer, so all guidance buttons only navigate to existing pages and never write business data.

**Tech Stack:** Python, Flask, SQLite, native JavaScript, Python `unittest`, Node test runner.

---

### Task 1: Lock Down Valid Agent Navigation

**Files:**
- Modify: `tests/test_agent_api.py`
- Modify: `utils/agent_runtime/service.py`

- [ ] **Step 1: Write failing route tests**

```python
def test_dashboard_suggestion_uses_existing_home_page(self):
    response = self.client.post(..., json={"message": "分析我的求职情况"}).get_json()
    self.assertEqual(response["suggested_actions"][0]["page"], "home")
```

- [ ] **Step 2: Run the route test**

Run: `python -m unittest tests.test_agent_api.AgentAPITests.test_dashboard_suggestion_uses_existing_home_page -v`

Expected: FAIL because `AgentService._suggested_actions()` returns `dashboard` while the frontend only has `home`, `resume`, `interview`, `tracker`, and `agent`.

- [ ] **Step 3: Implement safe fallback routes**

```python
"get_dashboard": {"label": "查看项目总览", "page": "home", "module": ""}
```

Keep route values within the frontend page/module contract and deduplicate duplicate suggestions.

- [ ] **Step 4: Run the route test green**

Run: `python -m unittest tests.test_agent_api.AgentAPITests.test_dashboard_suggestion_uses_existing_home_page -v`

Expected: PASS.

### Task 2: Produce Data-Driven Offline Guidance

**Files:**
- Modify: `tests/test_agent_orchestrator.py`
- Modify: `utils/agent_runtime/models.py`
- Modify: `utils/agent_runtime/orchestrator.py`
- Modify: `utils/agent_runtime/local_policy.py`

- [ ] **Step 1: Write failing guided-start tests**

```python
result = self.make_orchestrator(LocalPolicy()).run(
    1, self.conversation.id, "我是新用户，带我开始使用这个求职系统"
)
self.assertEqual(result.tools_used, ["get_dashboard", "get_career_profile", "list_action_items", "get_training_insights"])
self.assertEqual(result.suggested_actions[0]["page"], "resume")
self.assertEqual(result.suggested_actions[0]["module"], "input")
```

Use an empty registry fixture for the first-user journey and the existing populated fixture for the resume/JD/interview path.

- [ ] **Step 2: Run the guided-start tests**

Run: `python -m unittest tests.test_agent_orchestrator.AgentOrchestratorTests.test_local_agent_guides_first_time_user tests.test_agent_orchestrator.AgentOrchestratorTests.test_local_agent_guides_existing_user_to_next_gap -v`

Expected: FAIL because the local policy treats these phrases as fallback text and `AgentRunResult` cannot carry structured navigation suggestions.

- [ ] **Step 3: Add only the required result contract**

```python
@dataclass(frozen=True)
class AgentRunResult:
    ...
    suggested_actions: list[dict[str, str]] = field(default_factory=list)
```

Have `LocalPolicy` create at most three actions in this priority order: career target, resume input, JD matching, interview practice, opportunity add/board. `AgentOrchestrator._finish()` persists them in message metadata and returns them. Do not create a proposal or mutate data.

- [ ] **Step 4: Run the guided-start tests green**

Run: `python -m unittest tests.test_agent_orchestrator.AgentOrchestratorTests.test_local_agent_guides_first_time_user tests.test_agent_orchestrator.AgentOrchestratorTests.test_local_agent_guides_existing_user_to_next_gap -v`

Expected: PASS.

### Task 3: Render and Restore Guidance in the Agent Drawer

**Files:**
- Modify: `tests/contextual_agent_ui.test.js`
- Modify: `tests/test_agent_frontend.py`
- Modify: `static/index.html`
- Modify: `static/js/app.js`
- Modify: `static/css/style.css`

- [ ] **Step 1: Write the failing frontend contract**

```javascript
assert.ok(AgentUI.suggestedActionsHtml([{ label: "录入第一份简历", page: "resume", module: "input" }]).includes('data-agent-navigation'));
```

- [ ] **Step 2: Run the Node test**

Run: `node tests/contextual_agent_ui.test.js`

Expected: FAIL because navigation suggestions are rendered only from the live response and are not restored from message metadata.

- [ ] **Step 3: Render validated action buttons and add a guided-start prompt**

```html
<button class="ghost small" data-prompt="我是新用户，带我开始使用这个求职系统">带我开始</button>
```

Store and restore `suggested_actions` from the assistant metadata. Buttons must call the existing `jumpToModule(page, module)` only after route validation; no custom URL or write action is accepted.

- [ ] **Step 4: Run frontend tests green**

Run: `node tests/contextual_agent_ui.test.js; python -m unittest tests.test_agent_frontend -v`

Expected: PASS.

### Task 4: Document and Verify Real Scenarios

**Files:**
- Modify: `README.md`
- Modify: `docs/USER_GUIDE.md`
- Test: `tests/test_agent_api.py`
- Test: `tests/test_agent_orchestrator.py`
- Test: `tests/contextual_agent_ui.test.js`

- [ ] **Step 1: Document the no-Key guided-start path**

Describe the explicit command, data read, navigation behavior, no-write boundary, and the difference from model-backed open-ended answers.

- [ ] **Step 2: Run full regression verification**

Run: `python -m unittest discover -s tests -p "test_*.py" -v`

Run: `Get-ChildItem tests -Filter '*.test.js' | ForEach-Object { node $_.FullName }`

Expected: all Python and Node tests PASS.
