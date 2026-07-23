# 职途 AI Agent（JobHunter）

一个把简历、岗位、面试、投递和复盘连接起来的本地优先求职工作台。它的 Agent 不是独立聊天页，而是贯穿整个产品的行动助手：能读取当前机会和简历上下文、找出阻塞点、调用求职工具，并把写入操作先整理成预览，只有用户确认后才执行。

[在线项目展示](https://tl66666.github.io/ztai/static/showcase.html) · [项目交接](docs/PROJECT_HANDOFF.md) · [用户指南](docs/USER_GUIDE.md) · [Agent 双模式](docs/AGENT_MODES.md) · [架构说明](docs/ARCHITECTURE.md) · [测试指南](docs/TESTING.md) · [简历项目素材](docs/RESUME_PROJECT_ENTRY.md) · [版本记录](CHANGELOG.md)

> 本地开发默认使用 SQLite 和本地文件存储；生产目标为 Cloudflare 前端、Ubuntu FastAPI、PostgreSQL 与 R2。

## 它解决什么问题

求职很少是一次问答，而是一个持续数周的过程：同一份简历要适配多个 JD，面试反馈要回到训练计划，投递阶段又决定下一步动作。常见工具只完成其中一个环节，用户仍要手工搬运信息。

职途 AI 将这些信息组织为一条可追踪链路：

```text
职业目标 -> 简历版本 -> 岗位机会/JD -> 匹配证据 -> 面试训练
    ^                                             |
    |          投递阶段、结果与行动复盘            v
    +---------------------------------------------+
```

系统重点解决：

- 简历修改缺少证据，不知道应该为哪个岗位改什么。
- JD、简历、面试和投递记录彼此割裂，重复录入且容易忘记。
- 通用聊天助手不了解当前机会，建议空泛，也不能可靠推进任务。
- 面试训练只“出题”，没有恢复、反馈、语音降级和结果回流。
- 求职过程缺少可解释的准备度、阻塞项和下一步行动。

## Agent 为什么是项目特色

全局 Agent 可在总览、简历、面试和投递模块中随时打开。页面只提交用户输入和实体 ID，服务端重新读取权威数据，避免把旧文本当成当前事实。

Agent 的工作方式是：

1. 识别当前模块、机会和简历上下文。
2. 从分层记忆和实时业务数据中检索相关目标、历史结果与待办。
3. 选择严格 JSON Schema 定义的内部工具；需要公开实时信息时才使用联网工具。
4. 对新增机会、更新阶段、创建简历版本、制定面试计划等写操作生成提案。
5. 展示影响范围和可编辑字段，等待用户确认或取消。
6. 执行后写入回执和业务时间线，让下一轮对话能看到真实结果。

这套边界让 Agent 既能推进工作，又不会因为模型误判直接修改求职数据。无 API Key 时，用户可以点击 Agent 中的“带我开始”，或输入“我是新用户，带我开始使用这个求职系统”；本地策略会读取看板、职业档案、行动项和训练记录，按当前缺口给出可点击入口。简历任务会先让用户选择具体简历，再完成诊断、事实保真草稿或定制面试题，确认后才另存新版本。配置模型后，再由模型负责完整简历深度改写和开放式理解表达；确定性任务仍优先本地执行。详见 [Agent 双模式说明](docs/AGENT_MODES.md)。

## 主要功能

| 模块 | 能完成的任务 |
| --- | --- |
| 项目总览 | 查看证据加权准备度、阻塞项、近期结果和本周行动 |
| 简历实验室 | 上传或粘贴简历、分析证据、维护版本、按 JD 匹配和导出 |
| 机会工作区 | 在同一处查看岗位概览、JD、关联简历、面试和完整时间线 |
| 面试训练场 | 模拟面试、专业题、文本/录音回答、反馈、重启恢复和复盘 |
| 投递看板 | 使用统一阶段管理机会，保留未知旧状态并提示人工确认 |
| Agent 指挥台 | 查看活跃机会、待确认操作、行动项和跨模块会话 |

支持计算机/软件/AI、运营/新媒体、市场/销售、财务/会计、教育/师范、行政/人事等求职方向。语音能力会根据浏览器特性检测；不支持语音识别或录音时，文字回答和音频上传仍可使用。

## 快速开始（跨平台）

Windows、macOS 和 Linux 使用同一套 Python/ASGI 运行入口，不依赖 PowerShell：

```bash
uv sync --frozen
uv run python -m backend.cli
```

默认后端访问 `http://127.0.0.1:5000`。前端开发使用 `npm run dev`；Windows、macOS
与 Linux 均使用相同命令，不再维护 PowerShell 或批处理启动链。

## 传统 pip 兼容启动

```bash
python -m pip install -r requirements.txt
python -m backend.cli
```

默认访问 `http://127.0.0.1:5000`。系统默认只监听回环地址，当前版本是本地单用户应用，不适合直接暴露到公网或多人共享网络。

## 模型配置与无 Key 模式

系统支持智谱 GLM、DeepSeek、Kimi/Moonshot 等 OpenAI-compatible 接口。可以在页面“模型配置”中临时提交 Key，或在启动进程前设置环境变量：

```bash
DEEPSEEK_API_KEY="你的 Key" uv run python -m backend.cli
```

页面输入的 Key 不写入 SQLite、浏览器存储或仓库；为支持重启后复用，它会保存到 Git 忽略的本机 `output/runtime/ai-config.json`。该文件包含明文 Key，应仅由当前电脑用户保管；在“模型配置”中留空保存即可清除。使用远程模型时，完成请求所需的对话和上下文会发送给所选供应商，请勿提交不愿交给该供应商处理的敏感信息。

未配置 Key 时不会伪造“已调用大模型”。界面会显示本地规则模式，仍可完成多工具求职诊断、结构化查询、简历建议、机会盘点、面试准备和安全操作提案；对超出本地意图库的开放问题，会给出可执行示例而不是空白回复。

## 数据与隐私

- 简历、JD、面试、投递、记忆和操作回执默认保存在本机 `jobhunter.db`。
- 上传文件位于 `uploads/`，导出文件位于 `exports/`；这些目录和数据库均被 Git 忽略。
- Agent 写操作必须经过提案确认，确认接口限制为同端口回环来源。
- 业务表是实时事实来源；长期记忆只保存确认过的偏好、摘要和结果引用，避免复制整份简历。
- 本地模式使用固定开发身份；公开部署必须配置 Cloudflare Access、精确邮箱 allowlist、
  PostgreSQL 与 R2，不能把 `local` 认证模式直接暴露到公网。

## 浏览器与可选能力

| 能力 | Edge / Chrome | Firefox | 降级方式 |
| --- | --- | --- | --- |
| 核心求职流程 | 支持 | 支持 | 无 |
| Agent 抽屉/底部面板 | 支持 | 支持 | 无 |
| 语音识别 | 取决于浏览器 Web Speech 实现 | 通常不可用 | 文字输入 |
| 浏览器录音 | WebM/Opus（按能力选择） | Ogg/Opus（按能力选择） | 音频上传或文字输入 |
| Word 转 PDF | 浏览器无关 | 浏览器无关 | 安装 Office 可提高 Windows 转换保真度 |

## 技术设计

- 后端：FastAPI 模块化单体、Pydantic、Uvicorn；没有 Flask/WSGI 兼容层。
- 前端：React 19、strict TypeScript、Vite 单一 ESM graph，复用原页面 DOM/CSS。
- 数据：SQLAlchemy 2 + Alembic；SQLite 本地 adapter、PostgreSQL 生产 adapter。
- 文件与任务：Local/R2 `BlobStorage`、opaque `BlobRef`、可恢复 `background_jobs` worker。
- Agent：22 个结构化工具、有界编排循环、本地确定性多工具规划、分层记忆、上下文重建、确认式动作、幂等回执。
- 测试：Python `unittest`、Vitest、Node test runner、Playwright 浏览器矩阵、跨平台启动 smoke。

生产拓扑与配置见[生产架构](docs/PRODUCTION_ARCHITECTURE.md)。SQLite 和本地文件只作为
本地 adapter；生产公开前仍需在真实 PostgreSQL、R2 与 Cloudflare Access 环境完成验收。

本项目目前没有引入 LangChain/LangGraph。现有问题的核心是业务事实、工具边界、记忆质量和交互闭环，而不是缺少编排框架；轻量自研运行时更符合本地单体应用，也更容易审计。具体取舍和未来引入条件见[架构说明](docs/ARCHITECTURE.md)。

## 开发与发布

运行完整 Python 测试：

```bash
uv run python -m unittest discover -s tests -p "test_*.py"
```

浏览器测试、静态检查和干净路径启动验证见[测试指南](docs/TESTING.md)。发布前必须通过仓库卫生测试，禁止提交真实 Key、数据库、个人简历、音频、运行日志和 Playwright 产物。

## 已知限制

- 当前身份模型是单租户 allowlist，不提供组织级多人协作和权限管理。
- 本地规则模式可执行确定性任务，但不能替代高质量大模型的开放式表达。
- 薪资估算、匹配分和准备度是求职辅助信息，不是招聘结果保证。
- Web Speech 支持取决于浏览器和系统；始终保留文字与文件上传路径。
- Office 格式转换质量取决于操作系统、字体和本机 Office 环境。

## 维护入口

- [产品审计](docs/PRODUCT_AUDIT.md)
- [展示页资源审计](docs/SHOWCASE_ASSETS.md)
- [Agent 产品设计](docs/superpowers/specs/2026-07-12-integrated-agent-product-design.md)
- [许可证](LICENSE)
