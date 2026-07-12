# Agent-Centered Project Showcase Design

## Goal

Keep the restored cinematic JobHunter showcase, but rebuild its information hierarchy so a first-time visitor understands the whole product first and then recognizes the embedded career Agent as the main differentiator.

## Audience

- HR and teachers need the problem, product scope, real screens and outcome in under one minute.
- Frontend/backend interviewers need the Agent architecture, tools, memory, safety boundary and framework choice without exaggerated claims.
- Beginners need plain-language explanations before implementation details.

## Narrative Order

1. Hero: name the product as an AI Agent career operating system and summarize the end-to-end job-search loop.
2. Product overview: show the six business stages and explain what data is connected.
3. Agent centerpiece: place the real desktop Agent screenshot near the top and explain the four jobs it performs.
4. Agent implementation: show context reconstruction, memory retrieval, bounded planning, tool execution, synthesis and confirmation-gated writes.
5. Framework decision: explicitly state that the current runtime is self-built with Flask and SQLite. It is tool-calling with bounded orchestration, not a textbook ReAct implementation and not LangChain/LangGraph.
6. Product evidence: retain themes, real module screenshots, business loop, engineering stack, verification and local startup.

## Accurate Agent Claims

- 19 structured tools grouped around resume/JD, interview/training, opportunities/actions, career decisions and constrained public web access.
- Model mode uses provider-native `tool_calls`; no-Key mode uses deterministic multi-tool plans selected by intent.
- Memory is layered into working, summary, semantic, episodic, task and live business memory. The public visual may summarize this as four user-facing memory concerns while the technical section names all stored layers.
- Writes follow proposal, redacted preview, single confirmation, domain service execution and idempotent receipt.
- The Agent does not auto-apply, contact recruiters or guarantee offers.

## Visual Direction

Retain the original full-bleed video Hero, Instrument Serif accent type, dark cinematic palette, liquid-glass navigation, Anime/Glass backgrounds and stacked real screenshots. Add a single unframed Agent system map and compact capability panels inside the existing visual language. Desktop Web evidence remains primary; mobile screenshots are QA artifacts only.

## Resume Output

Do not modify the user’s external resume or repository resume document in this task. The final response must provide only the JobHunter project section as paste-ready text. Its title contains “AI Agent”, it fits a one-page resume, and it describes the self-built bounded tool-calling runtime without the inaccurate “ReAct framework / 13 tools” wording visible in the old resume.

## Verification

- Static contract tests verify section order, accurate framework wording, Agent scenarios, tool/memory/write-chain explanations and resume content.
- Browser QA covers 1440x900 and 390x844, with no horizontal overflow or fixed-nav overlap.
- Existing full Python, Node, startup and browser test gates remain unchanged.
