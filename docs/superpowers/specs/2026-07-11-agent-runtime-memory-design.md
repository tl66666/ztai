# JobHunter Agent Runtime 与分层记忆设计

日期：2026-07-11  
状态：已确认总体方向，待实施

## 1. 背景与问题

当前 `utils/agent.py` 已具备 ReAct 循环和 13 个工具，但智能体质量受以下结构性问题限制：

- 对话记忆是进程内全局列表，所有用户共享，服务重启后丢失，也没有独立会话。
- 模型必须输出中文“思考/行动/参数”，代码再用正则解析；格式稍有变化就会失效。
- 工具参数只是自然语言说明，没有机器可校验的 JSON Schema。
- 工具读取的数据不完整。例如简历列表只返回预览，后续无法凭 ID 获取完整正文。
- 每次请求都拼接固定业务上下文，缺少按任务检索和按相关性裁剪。
- 工具、编排、记忆、本地降级和提示词集中在一个文件，难以独立测试和演进。
- 无 API Key 时主要依赖关键词匹配，不能维护任务状态，也不能完成连续追问。
- 没有智能体会话、消息、长期画像、任务结果、工具运行记录等持久化模型。
- 测试没有覆盖 Agent API、会话隔离、记忆写入、工具选择和错误恢复。

这些问题比“是否使用 LangChain”更直接地决定智能程度。

## 2. 技术决策

### 2.1 暂不引入完整 LangChain

本阶段采用项目内的轻量模块化 Agent Runtime，继续使用 Flask、SQLite 和现有 OpenAI-compatible HTTP 网关。

理由：

- 当前系统规模不需要 LangChain 的大量适配层。
- 主要缺口是状态建模、结构化调用、记忆生命周期和工具质量，不是缺少链式 API。
- 保持依赖轻量，便于课程演示、本地启动、排错和讲解。
- 通过 `ModelGateway`、`MemoryStore`、`ToolRegistry`、`AgentOrchestrator` 接口隔离实现，未来可将编排层替换为 LangGraph，而不改 API、工具和数据层。

当出现人工审批节点、多个专业 Agent 并行协作、长任务恢复或复杂状态图时，再评估 LangGraph。

### 2.2 不展示模型私有思维链

API 不再返回模型原始“思考”文本。前端只展示可审计的运行事件：识别到的任务、调用了什么工具、工具是否成功、是否需要用户补充信息。这样既能解释系统行为，也避免把不稳定的自由推理当作产品输出。

## 3. 目标与非目标

### 3.1 目标

- 每个用户可创建、恢复、切换和清空独立对话。
- 服务重启后仍能继续上下文。
- 智能体能基于用户画像、历史任务和实时业务数据给出个性化建议。
- 模型优先通过原生 `tool_calls` 选择工具；不支持时使用严格 JSON 兼容协议。
- 工具参数可校验、结果结构一致、错误可恢复、调用可审计。
- 长对话自动摘要，避免简单截断造成目标和约束丢失。
- 无 Key 或模型异常时仍能完成确定性业务查询，并给出清晰降级提示。
- 对关键行为建立自动化测试和可观测指标。

### 3.2 非目标

- 不做通用自治智能体平台。
- 不做多 Agent 协作、后台长任务和向量数据库。
- 不让 Agent 自动投递、删除简历、修改投递状态等产生外部或破坏性影响的操作。
- 不在第一阶段加入 RAG 文档库；现有数据量用 SQLite 结构化检索足够。

## 4. 总体架构

```text
POST /api/agent/chat
        |
        v
ConversationService ---- ConversationRepository (SQLite)
        |
        v
ContextBuilder
  |-- recent messages
  |-- conversation summary
  |-- active task state
  |-- semantic profile memories
  |-- relevant episodic memories
  `-- live career snapshot
        |
        v
AgentOrchestrator <---- ModelGateway
  |-- decide/respond
  |-- validate tool call
  |-- execute and observe
  |-- recover or ask user
  `-- finalize within budgets
        |
        v
ToolRegistry ---- domain services / external read-only services
        |
        v
MemoryWriter
  |-- persist messages
  |-- update task state
  |-- summarize long conversation
  |-- extract candidate profile facts
  `-- record completed episode
```

模块按职责拆分：

- `utils/agent/models.py`：运行状态、消息、工具调用、结果等数据类型。
- `utils/agent/tools.py`：工具定义、JSON Schema、注册表和统一执行结果。
- `utils/agent/memory.py`：会话、消息、摘要、画像和情景记忆的 SQLite 存取。
- `utils/agent/context.py`：按 token/字符预算构建相关上下文。
- `utils/agent/orchestrator.py`：有限状态循环、工具执行和终止策略。
- `utils/agent/prompts.py`：系统规则、规划提示和记忆抽取提示。
- `utils/agent/local_policy.py`：无 Key 时的确定性意图与槽位策略。
- `utils/agent/service.py`：提供给 Flask 路由的稳定入口。

原 `utils/agent.py` 在迁移期只保留兼容导入，最终删除其全局状态和正则 ReAct 实现。

## 5. 分层记忆设计

### 5.1 工作记忆

只存在于单次 `run()` 中，包含：

- 当前用户输入。
- 当前任务类型和已知槽位。
- 本轮工具调用与结构化结果。
- 剩余模型调用、工具调用和上下文预算。
- 是否等待用户补充信息。

工作记忆不直接作为长期事实保存。

### 5.2 会话记忆

按 `user_id + conversation_id` 存储完整消息。上下文默认使用最近 12 条消息；较早消息由摘要承接。前端首次聊天自动创建会话，后续请求必须携带 `conversation_id`。

### 5.3 摘要记忆

当未摘要消息超过 16 条或估算上下文超过预算时生成滚动摘要，固定包含：

- 用户当前目标。
- 已确认事实与约束。
- 已完成事项和关键结论。
- 尚未解决的问题。
- 下一步承诺或待办。

摘要保存覆盖到的最后一条消息 ID，防止重复总结。

### 5.4 语义记忆

保存相对稳定的用户画像，例如目标岗位、期望城市、经验阶段、技能、薪资偏好、面试薄弱项和沟通偏好。每条事实包含：

- `category`、`key`、`value_json`。
- `confidence`，范围 0 到 1。
- `source_message_id` 和来源类型。
- `status`：`candidate`、`confirmed`、`superseded`。
- `updated_at`。

模型抽取的事实先标记为 `candidate`。明确陈述可自动确认；敏感或可能变化的信息只在回答中求证，不静默覆盖。相同键的新值会替代旧值并保留来源。

### 5.5 情景记忆

保存一次完整求职任务的压缩结果，例如“针对 A 公司测试岗完成 JD 匹配，主要缺口为接口自动化证据”。字段包括任务类型、标题、输入摘要、结果摘要、工具列表、关联业务对象和时间。

检索采用 SQLite 结构化条件与简单关键词评分：同一任务类型、岗位、公司、关联简历优先。当前数据规模不引入向量库。

### 5.6 业务事实

简历正文、JD 匹配、面试成绩、投递状态仍以现有业务表为唯一事实来源。上下文构建器只读取与当前问题相关的切片，避免把整份简历和全部历史每轮重复注入模型。

## 6. 数据库设计

新增表：

```sql
agent_conversations(
  id TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  title TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  summary TEXT,
  summary_until_message_id INTEGER,
  created_at TEXT,
  updated_at TEXT
)

agent_messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT
)

agent_tasks(
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT NOT NULL,
  slots_json TEXT,
  result_summary TEXT,
  created_at TEXT,
  updated_at TEXT
)

agent_memories(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  kind TEXT NOT NULL,
  category TEXT,
  memory_key TEXT,
  value_json TEXT NOT NULL,
  confidence REAL NOT NULL,
  status TEXT NOT NULL,
  source_message_id INTEGER,
  related_entity_type TEXT,
  related_entity_id TEXT,
  created_at TEXT,
  updated_at TEXT
)

agent_runs(
  id TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL,
  user_id INTEGER NOT NULL,
  task_id TEXT,
  status TEXT NOT NULL,
  provider TEXT,
  model TEXT,
  iterations INTEGER,
  tools_json TEXT,
  events_json TEXT,
  error_code TEXT,
  latency_ms INTEGER,
  created_at TEXT
)
```

为 `conversation_id`、`user_id/kind/status`、`task_id` 和时间字段建立索引。迁移通过现有 `init_db()` 的幂等建表执行，不修改和丢弃已有数据。

## 7. 工具体系

### 7.1 工具协议

每个工具定义：

- 唯一名称和面向模型的简短描述。
- 标准 JSON Schema 参数。
- `read_only`、`requires_confirmation`、`timeout_seconds` 等策略元数据。
- 执行器返回统一的 `ToolResult(ok, data, display_text, error_code, retryable)`。

模型不可传入任意 `user_id`；运行时强制注入当前请求的用户 ID，避免跨用户读取。

### 7.2 工具重组

第一阶段保留对外能力，但修正边界：

- `list_resumes`：只列元数据。
- `get_resume`：按 ID 获取完整正文，未指定时可取最近一份。
- `analyze_resume`：可接收 `resume_id`，内部加载正文，避免模型复制长文本参数。
- `match_job`：接收 `resume_id`、岗位和 JD。
- `analyze_jd`：结构化返回岗位、技能、职责和面试重点。
- `get_interview_question`、`evaluate_answer`：保留并统一返回结构。
- `list_applications`、`get_dashboard`、`generate_career_report`：只读业务数据。
- `evaluate_salary`：明确标记为估算，并说明规则数据不是实时行情。
- `web_search`、`fetch_webpage`：保留只读，加入 URL 安全、内容类型、大小和超时限制。

`ask_user` 不再伪装成工具。编排器直接返回 `needs_input` 状态和一个明确问题，保留待完成任务及已收集槽位。

### 7.3 工具选择策略

- 闲聊和知识解释允许直接回答。
- 涉及用户自身情况时，优先查业务事实或记忆，不凭空假设。
- 数据查询优先调用内部工具；需要时效性的外部信息才联网。
- 一个工具失败时，根据 `retryable` 决定重试、换方案或向用户说明。
- 默认最多 4 次工具调用、2 次模型规划调用，复杂报告最多 6 次工具调用。

## 8. 模型网关与编排协议

### 8.1 原生工具调用

扩展 `MultiModelAIClient.chat()`：

- 接受 `tools`、`tool_choice` 和结构化响应选项。
- 返回完整 assistant message，包括 `content` 和 `tool_calls`。
- 保留 provider、model、usage、错误类型和是否实际使用远端模型。
- 只有明确的网络、鉴权、限流或格式错误才降级，不把失败伪装成成功模型回答。

如果供应商或选定模型不支持原生工具调用，则使用单一严格 JSON 决策协议：

```json
{
  "type": "tool_call | final | needs_input",
  "tool": "optional_tool_name",
  "arguments": {},
  "message": "optional user-facing content"
}
```

兼容层只解析 JSON，不再解析自由文本中的中文标签。

### 8.2 有限状态编排

状态为：

```text
LOAD_CONTEXT -> DECIDE -> VALIDATE -> EXECUTE -> OBSERVE
                       |                          |
                       v                          v
                 NEEDS_INPUT <------ RECOVER ----+
                       |
                       v
                    FINALIZE
```

终止条件：模型给出最终答复、需要用户输入、达到预算、出现不可恢复错误或检测到重复工具调用。达到预算时使用已有可靠结果总结，不再次无限调用模型。

### 8.3 提示词分层

- 身份与边界：求职教练、事实优先、不得伪造用户经历。
- 决策规则：何时直接回答、查内部数据、联网或追问。
- 当前任务：只注入本任务所需槽位和可用工具子集。
- 记忆与事实：明确区分“用户确认事实”“模型推断”“实时业务数据”。
- 输出要求：中文、具体、给出下一步，避免重复介绍能力列表。

## 9. 无 Key 降级模式

无 Key 时不冒充完整 LLM Agent，而是运行本地任务路由器：

- 使用可测试的意图评分识别简历、JD、面试、投递、报告、看板和薪资任务。
- 用槽位状态维护多轮追问，例如先询问简历，再询问目标岗位。
- 能确定性查询内部数据和执行本地分析器。
- 不能可靠完成的生成式任务明确说明限制，并给出可执行入口。
- 联网工具是否可用与模型 Key 分开判断。

本地路由器和远端 Agent 共用同一会话、任务、工具及记忆层，因此切换模型不会丢上下文。

## 10. API 与前端设计

新增或调整接口：

- `POST /api/agent/conversations`：创建会话。
- `GET /api/agent/conversations/<user_id>`：列出会话。
- `GET /api/agent/conversations/<id>/messages`：恢复历史消息。
- `POST /api/agent/chat`：请求包含 `user_id`、`conversation_id`、`message`。
- `DELETE /api/agent/conversations/<id>`：归档指定会话，不影响其他会话。
- `POST /api/agent/conversations/<id>/clear`：只清空当前会话消息和摘要。

聊天响应：

```json
{
  "success": true,
  "conversation_id": "uuid",
  "reply": "...",
  "status": "completed | needs_input | degraded",
  "events": [
    {"type": "tool", "name": "get_resume", "status": "success"}
  ],
  "suggested_actions": [
    {"label": "开始模拟面试", "page": "interview", "module": "mock"}
  ]
}
```

前端增加轻量会话选择、新对话和清空当前会话；刷新后恢复消息。运行过程只显示“读取了最近简历”“完成岗位匹配”等事件，不显示私有推理文本。建议动作可直接跳转到现有业务模块。

## 11. 安全与可靠性

- 服务端以当前请求用户 ID 覆盖模型参数，所有数据库查询必须带用户过滤。
- 工具参数长度、类型和枚举统一校验。
- `fetch_webpage` 仅允许 HTTP/HTTPS，拒绝本机、内网和非文本响应，限制重定向与下载大小，降低 SSRF 风险。
- 工具输出作为不可信数据注入，提示模型忽略网页中的指令。
- 不自动执行删除、写入投递、发送消息或外部提交；未来写工具必须明确二次确认。
- 日志和 `agent_runs` 不保存 API Key；长简历和网页正文只记录摘要。
- 数据库失败、模型超时、格式错误、工具超时使用稳定错误码，前端显示可恢复提示。

## 12. 测试策略

### 12.1 单元测试

- 工具 Schema 和参数校验。
- 会话隔离、消息顺序、清空和重启恢复。
- 摘要触发与覆盖位置。
- 语义事实新增、确认、替换和来源追踪。
- 相关记忆排序和上下文预算。
- 原生 `tool_calls` 与 JSON 兼容决策解析。
- 重复调用检测、最大预算和错误恢复。
- 本地路由器的意图、槽位和连续追问。

### 12.2 集成测试

- 新建会话 -> 询问简历 -> 调用工具 -> 保存回答。
- 两个用户、两个会话互不读取记忆。
- 服务对象重建后可从 SQLite 恢复上下文。
- 缺少简历时返回 `needs_input`，补充后继续原任务。
- 模型超时后转为 `degraded`，内部只读工具仍可用。
- 恶意工具参数不能越权读取其他用户数据。

### 12.3 端到端验收

- 刷新页面后聊天记录仍在。
- “分析我最近的简历”能自动找到真实简历，不要求重新粘贴。
- “按刚才那个岗位出题”能引用当前任务中的岗位。
- “我更想去杭州，薪资 12k 左右”会成为有来源的用户画像，后续建议能使用。
- 清空当前会话不会清空其他会话，也不会删除业务数据。
- 工具失败时用户得到明确说明，而不是原始异常或虚构结果。

## 13. 可观测性与成功指标

每次运行记录：状态、模型、耗时、迭代数、工具名称、错误码和降级原因。验收指标：

- 会话隔离测试 100% 通过。
- 结构化决策解析不依赖正则自由文本。
- 典型单工具问题在 1 次工具调用内完成。
- 缺槽位问题只追问必要信息，并能在下一轮继续任务。
- 模型或工具失败不会返回 HTTP 500，也不会丢失用户消息。
- 无 Key 模式明确标记 `degraded`，不宣称“大模型自主决策”。

## 14. 实施顺序

1. 建立 Agent 数据类型、数据库表和仓储层。
2. 重构 AI 网关，支持结构化工具调用和可诊断错误。
3. 建立工具注册表，迁移并修正现有工具。
4. 实现上下文构建、分层记忆和本地任务状态。
5. 实现编排器及兼容入口，替换旧正则 ReAct。
6. 调整 Flask API 和前端会话交互。
7. 补齐单元、集成和端到端测试。
8. 更新 README、工具数量和架构说明，避免宣传与实现不一致。

## 15. 迁移与回滚

- 数据库变更仅新增表和索引，现有业务表不变。
- 新服务先保留旧 `run_agent()` 签名适配层，路由切换后再删除旧全局记忆。
- 前端在没有 `conversation_id` 时由后端自动创建，兼容旧请求。
- 若新编排器发生不可恢复错误，可临时切回本地任务路由器，但不恢复全局内存和正则 ReAct。

## 16. 完成定义

实现完成必须同时满足：

- 所有新增测试与原有测试通过。
- 真实浏览器验证新建会话、连续追问、刷新恢复、会话切换和清空流程。
- SQLite 中可观察到隔离的会话、消息、任务、记忆和运行记录。
- 有 Key 和无 Key 两种模式均有稳定、诚实的产品行为。
- README 与实际架构、工具清单、降级能力一致。
