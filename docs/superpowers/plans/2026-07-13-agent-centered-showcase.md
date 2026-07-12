# Agent-Centered Showcase Implementation Plan

**Goal:** Reorder and enrich the existing cinematic showcase so it introduces the complete product and then explains the embedded Agent as the project’s core feature, while producing concise resume-ready copy.

**Files:** `static/showcase.html`, `tests/test_showcase.py`, `CHANGELOG.md`, and the two supporting design/plan documents. Resume copy is delivered in the final response only.

## Task 1: Lock the content contract

1. Update `tests/test_showcase.py` to require the order `overview -> agent -> screens`, four concrete Agent scenarios, the phrases `有界 Tool-Calling Runtime`, `不是标准 ReAct`, `provider-native tool_calls`, the full memory explanation and the confirmation chain.
2. Run:

```powershell
python -m unittest tests.test_showcase -v
```

Expected: the new tests fail because the current page lacks the new structure and wording.

## Task 2: Rebuild the showcase narrative

1. Keep the existing Hero video and visual system.
2. Replace the early metric/pain/feature ordering with a compact project overview and six-stage product loop.
3. Move the Agent centerpiece directly after the overview.
4. Add scenario cards for career diagnosis, resume/JD work, interview preparation and opportunity follow-up.
5. Add a visual runtime flow: page context -> context builder -> layered memory -> policy/orchestrator -> 19 tools -> synthesis/proposal -> domain services.
6. Add a framework decision block that distinguishes this implementation from textbook ReAct and explains when LangGraph would become useful.
7. Keep the real screenshots, themes, startup, test evidence and GitHub Pages boundary.
8. Run the focused showcase tests until green.

## Task 3: Prepare resume material for the final response

1. Prepare a one-page project section with the title `职途 AI Agent 求职工作台` and four high-signal bullets.
2. Keep only content that can be pasted into the user’s resume project area.
3. Explicitly avoid claiming ReAct/LangChain/LangGraph.
4. Apply the Chinese humanizer pass: remove promotional filler, vary sentence structure and keep concrete implementation facts.

## Task 4: Verify the rendered result

1. Run `python -m unittest tests.test_showcase -v` and the full Python suite.
2. Run the Node unit commands from `docs/TESTING.md`.
3. Use `agent-browser` at 1440x900 and 390x844 to capture Hero, overview, Agent centerpiece and architecture sections.
4. Verify no horizontal overflow, anchor overlap or clipped text.
5. Run `git diff --check` and repository hygiene tests.

## Task 5: Publish

1. Update `CHANGELOG.md` with the new information architecture and resume wording.
2. Commit the expected files with a scoped message.
3. Push `main`, compare the remote SHA and verify GitHub Pages contains the new Agent/runtime text.
