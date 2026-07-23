# JobHunter 测试与发布指南

本项目的质量门禁覆盖 Python 业务契约、原生 JavaScript 状态逻辑、真实浏览器流程、Windows 启动器和仓库隐私。所有命令从仓库根目录运行。

## 1. 环境

- Python 3.11+
- Node.js 20+（JavaScript 与浏览器测试）
- PowerShell 5.1+（Windows 启动 smoke）
- Playwright 包及 Chromium/Firefox；Edge 矩阵使用系统安装的 Microsoft Edge

安装 Python 依赖：

```bash
uv sync --frozen
```

## 2. Python 测试

完整套件：

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

测试使用临时数据库，不应读取或修改仓库根目录的 `jobhunter.db`。重点分组：

| 范围 | 测试文件 |
| --- | --- |
| 本地安全边界与离线依赖 | `test_security_boundaries.py` |
| 数据迁移与领域服务 | `test_domain_migrations.py`、`test_career_services.py` |
| 面试恢复与准备度 | `test_interview_persistence.py`、`test_readiness.py` |
| Agent 动作/工具/记忆 | `test_agent_actions.py`、`test_agent_domain_tools.py`、`test_agent_business_memory.py` |
| 前端静态契约 | `test_opportunity_frontend.py`、`test_contextual_agent_frontend.py`、`test_browser_compatibility.py` |
| 启动、展示和发布卫生 | `test_startup_script.py`、`test_showcase.py`、`test_repository_hygiene.py` |

仓库卫生测试通过 `git ls-files` 检查实际跟踪内容，拒绝数据库、真实 `.env`、上传/导出/运行产物、高置信度密钥格式、个人主目录路径和失效 README 链接。

## 3. JavaScript 单元测试

使用 Node 内置 test runner，无需构建：

```powershell
node --test tests/js/*.test.js tests/interview_submission_state.test.js
node tests/contextual_agent_ui.test.js
node tests/agent_request_races.test.js
node tests/js/test_opportunity_handoffs.js
node tests/js/test_opportunity_history.js
node tests/js/test_opportunity_load_generation.js
```

这些测试覆盖：

- Web Speech 标准/前缀实现和不可用状态；
- MediaRecorder、`getUserMedia` 与 Chromium/Firefox MIME 选择；
- 音频上传/文字降级、重复提交和陈旧异步响应；
- 机会 Back/Forward、深链接、错误保留、重试和不可变跨模块交接；
- Agent 请求代际、上下文 ID、提案确认控件和响应式壳层契约。

## 4. 浏览器端到端测试

规格：`tests/browser/job_hunter_flow.spec.js`。

全新环境安装：

```powershell
npm install --no-save playwright
npx playwright install chromium firefox
node --test tests/browser/job_hunter_flow.spec.js
```

若 Playwright 已由其他工具安装，可把 `NODE_PATH` 指向包含 `playwright` 的 `node_modules`，并按需指定浏览器：

```powershell
$env:NODE_PATH = "C:\path\to\node_modules"
$env:PLAYWRIGHT_CHROMIUM_EXECUTABLE = "C:\path\to\chrome.exe"
$env:PLAYWRIGHT_FIREFOX_EXECUTABLE = "C:\path\to\firefox.exe"
node --test tests/browser/job_hunter_flow.spec.js
```

矩阵行为：

- Chromium、Firefox、已安装的 Edge；缺少的浏览器输出明确 SKIP 原因，不冒充通过。
- `1440x900` 桌面和 `390x844` 移动视口；Chromium 另做中间宽度几何 smoke。
- 每个组合使用独立空闲回环端口、临时 SQLite 和 Flask 子进程。
- 关闭所有模型 Key，走确定性本地 Agent，避免测试依赖外部模型。
- 完成职业档案、简历、JD 匹配、机会、Agent 提案确认、面试恢复、阶段更新和可见时间线。
- 检查项目资源 404、页面异常、控制台 error、横向溢出、关键遮挡和 Agent 桌面/移动布局。
- 使用可解码 WAV 验证上传/回放，再用损坏音频验证错误与文字降级。

产物写到 `output/playwright/`：

```text
<browser>-<viewport>.png
<browser>-<viewport>-trace.zip
<browser>-<viewport>-server.log
```

目录被 Git 忽略。测试注册前会清理旧的同名矩阵产物，避免把过期截图误认为本次结果。

## 5. Windows 启动器验证

静态契约：

```powershell
python -m unittest tests.test_startup_script -v
```

干净路径 smoke：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-start.ps1
```

脚本把跟踪的运行文件复制到包含中文和空格的临时目录，以 `-NoBrowser -SkipInstall` 启动，访问健康端点，并只停止自己创建的进程。它还验证首选端口已有其他服务时不会结束该服务。

## 6. 静态检查

```powershell
python -m compileall -q app.py config.py utils tests
node --check static/js/app.js
node --check static/js/browser_capabilities.js
node --check tests/browser/job_hunter_flow.spec.js
git diff --check
```

## 7. 手工视觉检查

自动矩阵后检查最新桌面和移动截图：

- 产品名、当前机会和 Agent 是首屏可识别信号；
- Agent 抽屉/底部面板不遮住关闭、发送、确认和取消按钮；
- 长公司名、岗位名、状态和错误信息不溢出容器；
- 机会概览、JD、简历、面试、时间线页签可以返回；
- 网络/500 错误保留机会 URL 并显示重试；404/403 才清理无效实体；
- 提案确认后对应实体和时间线真实更新；
- 展示页图片来自真实产品，移动端无横向滚动，减少动态偏好生效。

## 8. 发布前完整门禁

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
node --test tests/js/*.test.js tests/interview_submission_state.test.js
node tests/contextual_agent_ui.test.js
node tests/agent_request_races.test.js
node tests/js/test_opportunity_handoffs.js
node tests/js/test_opportunity_history.js
node tests/js/test_opportunity_load_generation.js
python -m compileall -q app.py config.py utils tests
node --check static/js/app.js
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/smoke-start.ps1
git diff --check
git status --short
```

随后执行完整 Playwright 矩阵并检查截图。只有在所有可用浏览器通过、SKIP 原因明确、工作区仅含预期发布变更且无隐私产物时，才提交和推送。

## 9. 失败排查

- 服务未启动：查看 `output/runtime/server-error.log` 或对应 E2E server log。
- Agent 流程失败：确认测试未设置模型 Key，并检查提案状态和时间线响应。
- Firefox/Edge SKIP：先看输出中的检测路径，再确认对应浏览器是否安装。
- 音频失败：区分“浏览器不支持录音”与“上传文件不可解码”；前者必须仍可文字回答。
- 端口问题：不要结束未知进程；使用启动器自动端口或指定新的 `-Port`。
