# JobHunter Integrated Agent Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn JobHunter into a portable, cross-browser, end-to-end career workspace where a confirmation-gated Agent can safely advance resume, JD, interview, application, and action-plan workflows.

**Architecture:** Introduce focused domain services as the only business write/read boundary, with versioned SQLite migrations and domain events. Flask routes and Agent tools call those services; Agent writes become persisted proposals that require explicit confirmation. The native frontend gains an opportunity workspace and contextual assistant while remaining framework-free.

**Tech Stack:** Python 3.10+, Flask, SQLite/FTS5, unittest, native HTML/CSS/JavaScript, Chart.js, Lucide, MediaRecorder/Web Speech feature detection, PowerShell, Playwright.

---

## File Map

- Create `utils/domain/database.py`: connection factory, migrations, local-user enforcement, canonical status migration.
- Create `utils/domain/career.py`: career profile, opportunity, resume-version, action-item, event, and readiness services.
- Create `utils/domain/interviews.py`: persisted interview session lifecycle.
- Create `utils/domain/__init__.py`: public service exports.
- Create `utils/agent_runtime/actions.py`: Agent action proposal creation and confirmation executor.
- Modify `utils/agent_runtime/tools.py`: use domain services and expose proposal tools.
- Modify `utils/agent_runtime/context.py`: richer live business snapshot and task context.
- Modify `utils/agent_runtime/local_policy.py`: deterministic proposal flows without a model key.
- Modify `utils/agent_runtime/orchestrator.py`: return proposed actions without executing them.
- Modify `app.py`: initialize migrations and expose thin domain/action APIs.
- Modify `static/index.html`: opportunity workspace, contextual Agent drawer, compatibility states.
- Modify `static/js/app.js`: shared context, action confirmation, feature detection, consistent statuses.
- Modify `static/css/style.css`: drawer/workspace responsive styles and asset URL fix.
- Modify `start-jobhunter.ps1` and `start.bat`: safe portable startup.
- Modify `static/showcase.html`, `README.md`, `.env.example`, `.gitignore`.
- Create `docs/ARCHITECTURE.md`, `docs/USER_GUIDE.md`, `docs/TESTING.md`, `CHANGELOG.md`.
- Create focused tests under `tests/` and browser artifacts only under `output/playwright/`.

## Phase A: Data Consistency And Domain Services

### Task 1: Versioned Schema And Legacy Migration

**Files:**
- Create: `utils/domain/database.py`
- Create: `utils/domain/__init__.py`
- Modify: `app.py`
- Test: `tests/test_domain_migrations.py`

- [ ] **Step 1: Write migration tests**

Create a temporary legacy database with an application status of `面试中`, run `migrate_database(path)`, and assert schema version `1`, normalized status `一面`, and the presence of `career_profiles`, `action_items`, `domain_events`, `career_reports`, `interview_sessions`, and `agent_action_proposals`.

```python
def test_migration_normalizes_legacy_status_and_is_idempotent(self):
    create_legacy_database(self.db_path, status="面试中")
    migrate_database(self.db_path)
    migrate_database(self.db_path)
    with connect(self.db_path) as conn:
        self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT status FROM job_applications").fetchone()[0], "一面")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    self.assertTrue({"career_profiles", "action_items", "domain_events", "career_reports", "interview_sessions", "agent_action_proposals"} <= tables)
```

- [ ] **Step 2: Run the migration test and confirm failure**

Run: `python -m unittest tests.test_domain_migrations -v`  
Expected: FAIL because `utils.domain.database` does not exist.

- [ ] **Step 3: Implement migration infrastructure**

Implement `connect`, `ensure_column`, transactional migration, `PRAGMA foreign_keys=ON`, and `PRAGMA user_version`. Add the approved columns and indexes. Normalize legacy statuses with this immutable mapping:

```python
APPLICATION_STATUSES = ("意向", "准备中", "已投递", "简历筛选", "笔试", "一面", "二面", "HR 面", "Offer", "已拒绝", "已结束")
LEGACY_STATUS_MAP = {"面试中": "一面", "面试": "一面", "筛选中": "简历筛选", "已录用": "Offer", "拒绝": "已拒绝"}
```

`migrate_database` must back up a non-temporary database to `<db>.backup-v0` before the first migration and must leave `user_version` unchanged if a transaction fails.

- [ ] **Step 4: Switch application initialization to migrations**

Keep `init_db()` as the compatibility entry point, but make it call the original base-table creation followed by `migrate_database(DB_PATH)`. Agent tables remain initialized through their existing migration function.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_domain_migrations tests.test_core_features -v`  
Expected: PASS.  
Commit: `feat: add versioned career data migrations`

### Task 2: Canonical Career And Opportunity Services

**Files:**
- Create: `utils/domain/career.py`
- Modify: `utils/domain/__init__.py`
- Modify: `app.py`
- Test: `tests/test_career_services.py`

- [ ] **Step 1: Write failing service tests**

Cover profile upsert, opportunity creation, status validation, legacy unknown-status visibility, resume-version creation, action completion, event creation in the same transaction, and local-user enforcement.

```python
def test_advancing_opportunity_records_event(self):
    service = CareerService(self.db_path, local_user_id=1)
    item = service.create_opportunity(1, {"company": "示例科技", "job_title": "测试工程师", "status": "意向"})
    updated = service.update_opportunity(1, item["id"], {"status": "准备中"})
    self.assertEqual(updated["status"], "准备中")
    self.assertEqual(service.timeline(1, item["id"])[-1]["event_type"], "opportunity.updated")
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python -m unittest tests.test_career_services -v`  
Expected: FAIL because `CareerService` is missing.

- [ ] **Step 3: Implement service contracts**

Implement `CareerService` methods:

```python
get_profile(user_id)
upsert_profile(user_id, values, source="user")
list_opportunities(user_id)
get_opportunity(user_id, opportunity_id)
create_opportunity(user_id, values, source="user")
update_opportunity(user_id, opportunity_id, changes, source="user")
create_resume_version(user_id, resume_id, content, metadata)
create_action_item(user_id, values, source="user")
complete_action_item(user_id, action_id, evidence="")
timeline(user_id, opportunity_id)
```

Every method checks `user_id == local_user_id`, validates lengths and status transitions, uses parameterized SQL, and writes a compact domain event in the same transaction.

- [ ] **Step 4: Convert opportunity and profile routes to thin adapters**

Add `/api/profile`, `/api/opportunities`, `/api/opportunities/<id>`, `/api/opportunities/<id>/timeline`, and `/api/action-items`. Keep current `/api/applications` routes as compatibility adapters to the same service and return a `canonical_statuses` field from list APIs.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_career_services tests.test_core_features -v`  
Expected: PASS.  
Commit: `feat: centralize career opportunity workflows`

### Task 3: Persisted Interview Sessions

**Files:**
- Create: `utils/domain/interviews.py`
- Modify: `app.py`
- Test: `tests/test_interview_persistence.py`

- [ ] **Step 1: Write restart-recovery tests**

Start a session through one `InterviewService` instance, submit an answer, recreate the service, resume the same session, finish it, and assert only one completed `interviews` row exists.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_interview_persistence -v`  
Expected: FAIL because sessions still depend on `INTERVIEW_SESSIONS`.

- [ ] **Step 3: Implement `InterviewService`**

Persist `state_json` after every answer. Provide:

```python
start(user_id, resume_id, job_title, jd, mode, career_profile) -> dict
get(user_id, session_id) -> dict | None
answer(user_id, session_id, answer, duration_seconds=None) -> dict
list_open(user_id) -> list[dict]
```

Use existing question, voice, skip-detection, and feedback helpers through injected callables so behavior remains compatible while storage changes.

- [ ] **Step 4: Convert interview routes and remove process memory dependency**

`POST /api/interview/sessions` and answer routes call the service. Add `GET /api/interview/sessions/open`. Do not delete the old global until all tests stop referencing it.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_interview_persistence tests.test_core_features -v`  
Expected: PASS.  
Commit: `feat: persist resumable interview sessions`

### Task 4: Evidence-Weighted Readiness

**Files:**
- Modify: `utils/domain/career.py`
- Modify: `app.py`
- Test: `tests/test_readiness.py`

- [ ] **Step 1: Write scoring boundary tests**

Assert no resume caps at 30, no real JD caps at 55, a recent complete interview below 40 cannot produce `可投递`, and each response includes component evidence and timestamps.

- [ ] **Step 2: Confirm current scoring fails**

Run: `python -m unittest tests.test_readiness -v`  
Expected: FAIL because current readiness rewards counts.

- [ ] **Step 3: Implement `calculate_readiness(user_id)`**

Return:

```python
{
  "score": 0,
  "label": "先补基础",
  "components": {
    "resume": {"score": 0, "weight": 25, "evidence": []},
    "alignment": {"score": 0, "weight": 20, "evidence": []},
    "interview": {"score": 0, "weight": 25, "evidence": []},
    "practice": {"score": 0, "weight": 15, "evidence": []},
    "pipeline": {"score": 0, "weight": 15, "evidence": []},
  },
  "caps": [], "blockers": [], "weekly_plan": []
}
```

Use recent quality and completion, not raw counts. Keep the existing dashboard response fields for frontend compatibility.

- [ ] **Step 4: Run tests and commit**

Run: `python -m unittest tests.test_readiness tests.test_core_features -v`  
Expected: PASS.  
Commit: `feat: make career readiness evidence based`

## Phase B: Executable Agent And Business Memory

### Task 5: Action Proposal Store And Confirmation API

**Files:**
- Create: `utils/agent_runtime/actions.py`
- Modify: `app.py`
- Test: `tests/test_agent_actions.py`

- [ ] **Step 1: Write proposal security tests**

Cover create, preview, edit-safe fields, confirm, cancel, expiry, ownership, invalid transition, and double-confirm idempotency.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_agent_actions -v`  
Expected: FAIL because action proposals are not implemented.

- [ ] **Step 3: Implement action registry and executor**

Allow exactly these action names: `set_career_goal`, `create_opportunity`, `create_resume_version`, `link_opportunity_resume`, `create_interview_plan`, `create_action_item`, `complete_action_item`, `update_opportunity`, and `save_career_report`. Persist normalized arguments, a human preview, `risk_level`, expiry, idempotency key, and result.

- [ ] **Step 4: Add confirmation endpoints**

Add `GET /api/agent/actions/<id>`, `POST /api/agent/actions/<id>/confirm`, `POST /api/agent/actions/<id>/cancel`. The confirm endpoint reloads the proposal from SQLite and never trusts action parameters sent by the browser.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_agent_actions tests.test_agent_api -v`  
Expected: PASS.  
Commit: `feat: add confirmation gated agent actions`

### Task 6: Domain-Backed Agent Tools

**Files:**
- Modify: `utils/agent_runtime/tools.py`
- Modify: `utils/agent_runtime/local_policy.py`
- Modify: `utils/agent_runtime/orchestrator.py`
- Test: `tests/test_agent_domain_tools.py`

- [ ] **Step 1: Write tool contract tests**

Assert read tools return the same opportunity/status/readiness data as services and write-intent tools return a proposal without changing business tables.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_agent_domain_tools -v`  
Expected: FAIL because tools still execute duplicate legacy logic.

- [ ] **Step 3: Replace duplicate tool executors**

Keep compatibility names while adding `get_career_profile`, `get_opportunity`, `get_training_insights`, `list_action_items`, and `propose_career_action`. Inject the local user and service instances; models never receive `user_id` as a writable argument.

- [ ] **Step 4: Extend no-key policy**

Deterministically gather missing slots, then propose safe local actions. Without a key it may create proposals and calculate results, but must state that generated prose uses local templates.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_agent_domain_tools tests.test_agent_tools tests.test_agent_orchestrator -v`  
Expected: PASS.  
Commit: `feat: connect agent tools to career services`

### Task 7: Business Events And Rich Context

**Files:**
- Modify: `utils/agent_runtime/context.py`
- Modify: `utils/agent_runtime/memory.py`
- Modify: `utils/domain/career.py`
- Test: `tests/test_agent_business_memory.py`

- [ ] **Step 1: Write context feedback tests**

Create a low interview result and an opportunity-stage event through services. Assert context contains the relevant opportunity, selected resume, blocker, active action, and recent outcome without copying full resume text into semantic memory.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_agent_business_memory -v`  
Expected: FAIL because live context contains counts only.

- [ ] **Step 3: Implement hybrid retrieval**

Build the snapshot from structured entities, active actions, recent events, match evidence, and score trends. Add optional FTS5 indexing for confirmed semantic and episodic summaries; catch `sqlite3.OperationalError` and fall back to structured/substring ranking.

- [ ] **Step 4: Auto-complete action items from events**

When an event meets an action completion condition, update the action in the same transaction and expose the result to the next Agent turn.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_agent_business_memory tests.test_agent_memory -v`  
Expected: PASS.  
Commit: `feat: feed career outcomes into agent memory`

## Phase C: Contextual Frontend And Browser Compatibility

### Task 8: Opportunity Workspace And Consistent Status UI

**Files:**
- Modify: `static/index.html`
- Modify: `static/js/app.js`
- Modify: `static/css/style.css`
- Test: `tests/test_opportunity_frontend.py`

- [ ] **Step 1: Write frontend contract tests**

Assert the canonical statuses come from API data, unknown values render in an `待确认` column, opportunity detail has overview/JD/resume/interview/timeline tabs, and asset URLs are document-absolute or correctly relative.

- [ ] **Step 2: Confirm current contracts fail**

Run: `python -m unittest tests.test_opportunity_frontend -v`  
Expected: FAIL because status columns are hard-coded and background URLs resolve under `/css/`.

- [ ] **Step 3: Implement workspace markup and rendering**

Use full-width unframed module bands and one card per repeated opportunity. Store current opportunity ID in state, load detail from API, and carry IDs rather than copying only text between forms.

- [ ] **Step 4: Fix asset URLs**

Set image `src` and `--asset-bg` from absolute application paths such as `/assets/images/resume-analysis.png`; verify GitHub showcase uses its own relative paths and does not reuse server-root URLs.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_opportunity_frontend tests.test_core_features -v`  
Expected: PASS.  
Commit: `feat: add connected opportunity workspace`

### Task 9: Global Contextual Agent And Action Approval UI

**Files:**
- Modify: `static/index.html`
- Modify: `static/js/app.js`
- Modify: `static/css/style.css`
- Test: `tests/test_contextual_agent_frontend.py`

- [ ] **Step 1: Write contract tests**

Assert a global launcher exists outside page sections, context chips expose removable resume/opportunity/module context, proposals have preview/edit/confirm/cancel controls, and the standalone Agent page includes active actions and opportunities.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_contextual_agent_frontend -v`  
Expected: FAIL because the Agent exists only as a page.

- [ ] **Step 3: Implement responsive assistant shell**

Desktop uses a right side drawer; mobile uses a bottom sheet with a stable close button and no horizontal overflow. Send only entity IDs plus user-entered text; the server rebuilds authoritative context.

- [ ] **Step 4: Implement proposal confirmation flow**

Render server previews with text-safe escaping. Confirm calls the proposal endpoint, refreshes affected modules and conversation context, and shows the resulting entity link. Cancel does not mutate business tables.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_contextual_agent_frontend tests.test_agent_frontend -v`  
Expected: PASS.  
Commit: `feat: embed agent across career workflows`

### Task 10: Browser Feature Detection And E2E

**Files:**
- Modify: `static/js/app.js`
- Modify: `static/css/style.css`
- Create: `tests/browser/job_hunter_flow.spec.js`
- Create: `docs/TESTING.md`

- [ ] **Step 1: Add capability unit contracts**

Define pure helpers for speech recognition availability and ordered MediaRecorder MIME selection. Add Node assertions for Chromium-style and Firefox-style support matrices.

- [ ] **Step 2: Implement graceful degradation**

Hide unsupported speech-to-text controls with an accessible status, retain text answers, select recorder MIME using `MediaRecorder.isTypeSupported`, and retain audio upload when recording is unavailable.

- [ ] **Step 3: Add real browser flows**

The Playwright flow creates isolated temporary data, completes profile -> resume -> opportunity/JD -> proposal confirmation -> interview restart -> stage update, and checks no project 404, page error, overlap, or horizontal overflow at 1440x900 and 390x844.

- [ ] **Step 4: Run browser matrix**

Run Chromium and Firefox. Run Edge with `channel: 'msedge'` when installed; otherwise emit an explicit SKIP reason. Expected: all available browsers PASS, zero unhandled console errors.

- [ ] **Step 5: Commit**

Commit: `test: cover cross browser career workflows`

## Phase D: Portable Startup, Showcase, And Release

### Task 11: Safe Portable Windows Launcher

**Files:**
- Modify: `start-jobhunter.ps1`
- Modify: `start.bat`
- Create: `tests/test_startup_script.py`
- Create: `scripts/smoke-start.ps1`

- [ ] **Step 1: Write static safety tests**

Assert scripts contain no developer path, use `$PSScriptRoot`, do not `taskkill` an arbitrary port owner, support `-NoBrowser`, `-Port`, `-SkipInstall`, and write logs under `output/runtime`.

- [ ] **Step 2: Confirm failure**

Run: `python -m unittest tests.test_startup_script -v`  
Expected: FAIL because the existing script kills port owners and lacks required switches.

- [ ] **Step 3: Rewrite launcher lifecycle**

Detect `py -3` then `python`, require 3.10+, verify pip, install missing requirements unless skipped, find the first free port without killing other processes, start with `JOBHUNTER_PORT`, health-check `/api/config/ai-status`, open the default browser unless disabled, and terminate only the returned child PID.

- [ ] **Step 4: Add clean-path smoke test**

Copy required tracked files into a temporary directory containing Chinese characters and spaces, launch with a random port and `-NoBrowser -SkipInstall`, request the health endpoint, and stop the owned process.

- [ ] **Step 5: Run tests and commit**

Run: `python -m unittest tests.test_startup_script -v` and `powershell -ExecutionPolicy Bypass -File scripts/smoke-start.ps1`  
Expected: PASS.  
Commit: `feat: make windows launcher portable and safe`

### Task 12: Showcase And Asset Governance

**Files:**
- Modify: `static/showcase.html`
- Modify: `static/assets/`
- Modify: `.gitignore`
- Test: `tests/test_showcase.py`

- [ ] **Step 1: Write showcase contract tests**

Check relative GitHub Pages links, no server-only API claims, browser compatibility text, startup instructions, architecture/Agent/memory sections, reduced-motion CSS, video poster, and no missing tracked asset references.

- [ ] **Step 2: Audit tracked assets**

Generate an exact reference list from HTML/CSS/JS. Delete only unreferenced duplicates after recording before/after byte totals. Resize/compress oversized images and videos while retaining legible screenshots and both active themes.

- [ ] **Step 3: Rebuild showcase content**

Use actual product screenshots and factual capability text. Keep the product name in the first viewport, show a hint of the next section, avoid nested cards, and make the static nature of GitHub Pages explicit.

- [ ] **Step 4: Test and commit**

Run: `python -m unittest tests.test_showcase -v` plus desktop/mobile browser screenshots.  
Expected: PASS with no broken resources.  
Commit: `docs: refresh product showcase and assets`

### Task 13: Documentation, Privacy, And Repository Release

**Files:**
- Modify: `README.md`
- Modify: `.env.example`
- Modify: `.gitignore`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/USER_GUIDE.md`
- Modify: `docs/TESTING.md`
- Create: `CHANGELOG.md`
- Test: `tests/test_repository_hygiene.py`

- [ ] **Step 1: Add repository hygiene tests**

Reject tracked databases, `.env`, uploaded resumes/audio, exports, runtime logs, Playwright output, and common key patterns. Verify all README local links exist and no developer absolute path appears in tracked text.

- [ ] **Step 2: Update documentation**

Document the real architecture, Agent approval boundary, local privacy model, Edge/Chrome/Firefox matrix, Windows launcher, manual startup, optional Office conversion, no-key behavior, troubleshooting, tests, and known limits.

- [ ] **Step 3: Run full release verification**

Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q app.py utils tests
node --check static/js/app.js
git diff --check
git status --short
```

Expected: all tests PASS, syntax checks exit 0, no whitespace errors, only intentional tracked changes before the release commit.

- [ ] **Step 4: Browser release verification**

Run the complete Chromium/Firefox/available Edge matrix and visually inspect desktop/mobile screenshots. Verify zero project resource 404s and that the Agent proposal flow updates the opportunity timeline.

- [ ] **Step 5: Commit and push**

Commit: `release: complete integrated agent career workspace`  
Review `git log`, `git status`, and `git remote -v`; push the verified `main` branch to `origin`. Do not force-push. Verify the remote commit and GitHub Pages URL after publication.

## Plan Self-Review

- Every design requirement maps to Tasks 1-13.
- Domain names are consistent: the legacy `job_applications` table remains the persisted opportunity aggregate, while APIs and services use “opportunity”.
- All Agent writes go through `agent_action_proposals`; no tool directly mutates business data.
- Cross-browser voice behavior always retains text input and upload fallbacks.
- Launcher tests cover ownership-safe cleanup and non-default ports.
- GitHub push is last and requires tests, privacy checks, clean status, and browser verification.
