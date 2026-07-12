# JobHunter 测试指南

## Python 测试

在项目根目录运行：

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

测试默认使用临时 SQLite 数据库，不应读写个人的 `jobhunter.db`。

## JavaScript 单元测试

浏览器能力检测和面试提交状态使用 Node 内置 test runner，不需要前端构建：

```powershell
node --test tests/js/browser_capabilities.test.js tests/js/career_form.test.js tests/js/interview_media.test.js tests/js/isolated_server.test.js tests/js/browser_artifacts.test.js tests/interview_submission_state.test.js
node tests/contextual_agent_ui.test.js
node tests/agent_request_races.test.js
node tests/js/test_opportunity_handoffs.js
node tests/js/test_opportunity_history.js
node tests/js/test_opportunity_load_generation.js
```

`browser_capabilities.test.js` 覆盖标准和 WebKit 前缀语音识别、录音 API 完整性、Chromium/WebKit 风格 WebM 与 Firefox 风格 Ogg MIME 选择、文件扩展名，以及无录音能力时的上传和文字降级。

## 浏览器端到端测试

端到端规格位于 `tests/browser/job_hunter_flow.spec.js`，使用 `playwright` 和 Node 内置 test runner。它会自动：

- 为每个浏览器和视口组合选择独立的空闲回环端口；
- 为每个组合创建独立临时 SQLite 数据库和 Flask 进程，不在矩阵中共享业务状态；
- 关闭所有模型 Key，使用确定性本地 Agent；
- 通过可见表单完成职业档案、简历、JD 匹配、机会、Agent 提案确认、面试恢复和可见时间线流程；
- 实际构造并上传可解码的 PCM WAV，验证浏览器播放、提交和合理时长；再单独上传损坏 WAV，验证错误提示、原文件下载、未知时长和文字回答降级；
- 检查同源资源 404、页面异常、控制台 error、横向溢出、关键控件遮挡和 Agent 响应式布局；
- 每个组合结束后停止自己的服务并删除临时数据库。

先安装 Node.js 20+ 和 Playwright。若仓库没有本地 `node_modules/playwright`，将 `NODE_PATH` 指向已有 Playwright 安装目录：

```powershell
$env:NODE_PATH = "C:\path\to\node_modules"
node --test tests/browser/job_hunter_flow.spec.js
```

全新测试环境可先安装 Playwright 和浏览器：

```powershell
npm install --no-save playwright
npx playwright install chromium firefox
node --test tests/browser/job_hunter_flow.spec.js
```

支持的环境变量：

| 变量 | 用途 |
| --- | --- |
| `PYTHON` | 指定启动隔离 Flask 服务的 Python 可执行文件，默认 `python` |
| `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | 覆盖 Chromium 可执行文件路径 |
| `PLAYWRIGHT_FIREFOX_EXECUTABLE` | 覆盖 Firefox 可执行文件路径 |
| `NODE_PATH` | 指向包含 `playwright` 包的 `node_modules` |

完整业务矩阵固定覆盖 `1440x900` 桌面视口和 `390x844` 移动视口；Chromium 另外覆盖 `900x900` 与 `768x900` 平板 launcher、导航、主控件和 Agent 抽屉几何 smoke。Microsoft Edge 通过 Playwright `channel: "msedge"` 启动；系统未安装 Edge 时会输出带检测路径的 SKIP。Firefox 可执行文件不存在时同样输出具体路径并 SKIP。缺失浏览器不计为 PASS，也不会静默回退到 Chromium。

Web Speech 和 MediaRecorder 不请求真实麦克风权限。纯 JS 单元测试验证支持矩阵；E2E 在页面初始化时注入“不支持”能力，在可见面试页和重载恢复后验证语音/录音控件降级，同时确认音频上传、原文件下载和文字回答仍可用。Lucide 和 Chart.js 两个第三方 CDN 在 E2E 中替换为稳定空实现，项目自身 HTML、CSS、JavaScript、图片和 API 均访问真实 Flask 服务。

截图、trace 和服务日志写入 `output/playwright/`。suite 注册测试前统一删除所有浏览器与视口组合的旧同名产物，包括本机缺少浏览器而即将 SKIP 的组合；业务流程在 `finally` 中等待 Agent 抽屉关闭动画完成后写入当前截图并停止 trace。失败和成功都会留下本次调试证据。该目录已被 `.gitignore` 忽略，不提交截图、trace、视频、临时数据库或运行日志。测试失败时先检查：

```text
output/playwright/<browser>-<viewport>-server.log
output/playwright/<browser>-<viewport>.png
output/playwright/<browser>-<viewport>-trace.zip
```

## 静态检查

```powershell
node --check static/js/browser_capabilities.js
node --check static/js/app.js
node --check tests/browser/job_hunter_flow.spec.js
python -m py_compile app.py config.py utils/agent_runtime/*.py utils/domain/*.py
```
