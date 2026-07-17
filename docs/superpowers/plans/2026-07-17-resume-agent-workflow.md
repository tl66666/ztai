# Resume Agent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the career Agent into a real resume workflow that lets a user select a saved resume, generate a controlled revision proposal, edit its full draft, and save a new version only after confirmation.

**Architecture:** Keep the existing self-built runtime rather than adding LangChain/LangGraph. `LocalPolicy` will persist a `resume_workflow` task across turns, tools will prepare a source-faithful local draft when no model key exists or a model-assisted draft when one is configured, and `ActionProposalService` remains the sole write boundary. The UI renders structured resume choices and loads the full draft only through an owned proposal endpoint.

**Tech Stack:** Flask, SQLite, Python `unittest`, native JavaScript, existing AgentOrchestrator, ToolRegistry, MemoryStore and ActionProposalService.

---

### Task 1: Surface structured workflow input

**Files:**
- Modify: `utils/agent_runtime/models.py`
- Modify: `utils/agent_runtime/orchestrator.py`
- Modify: `utils/agent_runtime/service.py`
- Modify: `app.py`
- Test: `tests/test_agent_resume_workflow.py`

- [ ] Add an `input_request` result field that is persisted in assistant-message metadata and returned by `/api/agent/chat`.
- [ ] Make `needs_input` decisions expose only choice metadata (`kind`, `workflow`, prompt and owned IDs), never resume content.

### Task 2: Add the local-first resume revision tool chain

**Files:**
- Create: `utils/agent_runtime/resume_draft.py`
- Modify: `utils/agent_runtime/tools.py`
- Modify: `utils/agent_runtime/local_policy.py`
- Test: `tests/test_agent_resume_workflow.py`

- [ ] Add deterministic diagnostics and source-faithful normalization for no-key mode.
- [ ] Use a configured model only to create a factual revision draft; it cannot execute writes.
- [ ] Persist `resume_workflow` selection state and create one `create_resume_version` proposal after a resume is selected.

### Task 3: Enable controlled review and save

**Files:**
- Modify: `utils/agent_runtime/actions.py`
- Modify: `app.py`
- Modify: `static/js/contextual_agent.js`
- Modify: `static/js/app.js`
- Modify: `static/index.html`
- Test: `tests/test_agent_resume_workflow.py`
- Test: `tests/contextual_agent_ui.test.js`

- [ ] Add an owned `draft` endpoint for pending `create_resume_version` proposals only.
- [ ] Render resume-choice controls and a full draft editor in the Agent drawer.
- [ ] Save edits back to the pending proposal, then rely on the existing confirm endpoint to create a new version.

### Task 4: Verify the workflow

**Files:**
- Test: `tests/test_agent_resume_workflow.py`
- Test: `tests/test_agent_api.py`
- Test: `tests/contextual_agent_ui.test.js`

- [ ] Run the new tests first in red state, then verify them green.
- [ ] Run the Python and Node Agent suites and a browser flow that selects a resume, edits the draft and confirms the new version.
