# 贡献指南

感谢你对职途 AI 项目的关注！以下是参与贡献的流程和规范。

## 开发环境准备

1. 安装 Python 3.11+（推荐 3.12）
2. 安装 Node.js 22+（推荐 22.16 LTS）
3. 克隆仓库并安装依赖：

```bash
# Python 依赖（推荐 uv）
uv sync --frozen

# 或使用 pip
python -m pip install -r requirements.txt

# 前端依赖
npm install
```

4. Windows 用户可直接双击 `start.bat` 启动开发环境。

## 分支与提交规范

### 分支命名

- 功能分支：`feature/[功能名称]`，如 `feature/resume-preview`
- 修复分支：`fix/[问题名称]`，如 `fix/interview-reconnect`
- 文档分支：`docs/[文档名称]`

**禁止直接向 `main` 分支提交代码。**

### 提交信息

使用 Conventional Commits 格式：

```
<type>(<scope>): <description>

type: feat | fix | docs | style | refactor | test | ci | chore
scope: 可选，如 agent, api, frontend, tests, ci
```

示例：
- `feat(agent): 新增简历定制面试题生成`
- `fix(ci): 修复 Windows 文件锁定导致测试失败`
- `docs(readme): 添加项目结构说明`

## 代码规范

### Python

- 行宽不超过 100 字符
- 使用 ruff 检查：`ruff check .`
- 目标版本：py311
- 规则集：E, F, I, UP

### TypeScript / React

- 严格模式 TypeScript
- 使用 `tsc --noEmit` 进行类型检查
- 组件使用函数式组件和 Hooks

### 通用

- 不引入 LangChain / LangGraph 等编排框架
- Agent 工具使用严格 JSON Schema 定义
- 写操作必须经过提案确认流程
- API Key 只在服务端读取，不暴露给前端

## 测试要求

提交前必须通过以下测试：

```bash
# Python 单元测试
uv run python -m unittest discover -s tests -p "test_*.py"

# 前端单元测试
npm run test:unit

# 类型检查
npm run typecheck

# 仓库卫生检查
uv run python -m unittest tests.test_repository_hygiene
```

### 测试规范

- 临时目录使用 `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`
- `tearDown` 中使用 `gc.collect()` + `shutil.rmtree` fallback 处理 Windows 文件锁
- subprocess 调用 npm 时使用 `shell=(sys.platform == "win32")` 确保跨平台兼容
- 日期敏感测试使用 SQLite `datetime('now', '-N days')` 而非硬编码日期

## CI 矩阵

所有 PR 需通过以下矩阵测试：

| 平台 | Python 版本 |
| --- | --- |
| ubuntu-latest | 3.11, 3.12, 3.13 |
| macos-latest | 3.11, 3.12, 3.13 |
| windows-latest | 3.11, 3.12, 3.13 |

前端测试覆盖 ubuntu、macos、windows 三个平台。

## 发布前检查清单

- [ ] 所有测试通过（Python + 前端 + 类型检查）
- [ ] 未提交真实 API Key、数据库、个人简历、音频或日志
- [ ] CHANGELOG.md 已更新
- [ ] 文档与代码一致（无过时的框架引用）
- [ ] CI 全绿

## 文件安全

**禁止提交以下内容：**

- 真实 API Key 或环境变量文件（`.env`）
- 数据库文件（`*.db`, `*.sqlite`）
- 个人简历、音频、导出文件
- 运行日志和 Playwright 测试产物
- `node_modules/`、`dist/`、`.venv/` 等依赖目录

## 许可证

本项目使用 MIT 许可证。提交的代码将自动适用同一许可证。
