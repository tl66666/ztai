# 职途AI：基于 AI 智能体的求职辅助 Web 系统

职途AI 是一个围绕真实求职流程设计的 AI Agent Web 系统，面向应届生、实训项目展示和转岗求职场景。系统把简历管理、JD 匹配、简历优化、模拟面试、语音表达复盘、题库训练、投递跟进和 AI 求职教练串成一条闭环，让用户不是单点问答，而是按“准备简历 -> 匹配岗位 -> 训练面试 -> 追踪投递 -> 复盘提升”的路径持续推进。

项目展示页：启动后访问 [http://localhost:5000/showcase.html](http://localhost:5000/showcase.html)

主系统入口：启动后访问 [http://localhost:5000](http://localhost:5000)

## 项目亮点

- **AI 智能体求职闭环**：系统根据用户简历、JD、面试记录、语音记录和投递数据生成“求职准备度”和下一步行动建议。
- **多模型网关**：支持智谱 GLM、DeepSeek、Kimi / Moonshot 三类模型供应商，可切换模型，也支持自定义模型 ID；未配置 Key 时自动进入本地规则兜底，保证演示和测试可用。
- **简历实验室**：支持简历录入、文件上传、编辑、原件替换、PDF/Word 导出转换、客观锐评、JD 定制优化、技能图谱和版本管理。
- **真实面试训练场**：覆盖完整模拟面试、专业知识面试、题库练习、语音输入、真实录音回放、声音指标分析和训练记录复盘。
- **投递看板**：管理公司、岗位、阶段、城市和备注，支持推进投递阶段、生成跟进话术、薪资评估和机会池复盘。
- **双主题视觉系统**：Anime 二次元轻潮风和 Glass 玻璃科技风可切换，图片、Logo、背景和卡片风格统一。
- **可测试可交付**：后端接口、兜底算法和核心流程配有测试；仓库包含 `.gitignore`、`.env.example`、`LICENSE` 和项目展示页。

## 功能模块

### 1. 项目总览

- 展示简历、面试、JD 匹配、投递数量。
- “今日求职作战台”根据真实数据计算求职准备度。
- 自动识别短板：如无简历、无 JD 匹配、面试分低、缺少语音复盘、无投递记录。
- 下一步行动按钮可直接跳转到对应功能模块。

### 2. 简历实验室

- **录入编辑**：粘贴简历文本或上传 PDF / Word / TXT / 图片，保存原始文件和解析文本。
- **我的简历**：集中管理多份简历，可编辑、诊断、删除、打开原件、替换原件。
- **分析修改**：按岗位和 JD 对简历做结构诊断，输出综合分、优势证据、风险点、证据缺口、修改优先级。
- **JD 优化**：粘贴 BOSS 直聘、智联、猎聘等平台 JD，生成匹配分、关键词命中、缺口、项目改写建议和面试讲述点。
- **格式导出转换**：支持导出 PDF / Word，支持 PDF 转 Word、Word 转 PDF；Windows 环境优先调用 Microsoft Word 做高保真转换。
- **技能图谱**：根据简历关键词生成能力雷达图，指出技能短板和补证据方向。

### 3. 面试训练场

- **完整模拟面试**：按真实流程推进自我介绍、项目深挖、技术追问、行为面、反问总结。
- **统一回答区**：文本输入、浏览器语音转文字、真实录音、回放和 AI 表达分析合并到同一工作区。
- **专业知识面试**：按软件测试、Python / Flask、前端基础、AI Agent 等方向生成题组，左侧选题，右侧作答评分。
- **题库练习**：按题型训练，保存题目、回答、评分、参考答案和表达升级建议。
- **训练记录**：可查看模拟面试对话、答题记录、语音转写、音频播放器和声音指标；支持单条删除和清空。
- **幻觉控制**：用户回答“不知道 / 下一题 / 跳过”时，系统不会编造高分，会给出跳过反馈和参考学习方向。

### 4. 投递看板

- 新增公司、岗位、阶段、城市和备注。
- 按阶段生成看板列，支持推进到下一阶段。
- 对每条投递生成跟进建议、风险点和可发送话术。
- 薪资评估根据城市、经验和技能数量给出参考区间。

### 5. AI 教练

- 结合当前简历、投递、面试和训练数据回答求职问题。
- 支持生成“求职作战报告”，用于总结简历资产、JD 匹配、面试训练和投递推进状态。

## 技术栈

### 后端

- **Python 3 + Flask**：提供 REST API、静态资源服务、文件上传下载、业务流程编排。
- **SQLite**：本地轻量数据库，存储简历、JD 匹配、面试会话、投递记录、题库练习记录和语音分析记录。
- **Requests**：封装多模型厂商 API 请求。
- **python-docx**：读取和生成 Word 简历。
- **reportlab**：生成 PDF 简历，支持中文字体注册。
- **pdf2docx / PyPDF2**：处理 PDF 文本提取和 PDF 转 Word。
- **Microsoft Word COM（Windows 可选）**：Word 转 PDF 时优先调用本机 Office，提高图片和版式保真度。

### 前端

- **HTML / CSS / JavaScript 原生实现**：无复杂构建链，适合实训展示和本地部署。
- **Chart.js**：绘制技能雷达图。
- **Lucide Icons**：统一图标系统。
- **Web Speech API**：实现浏览器语音转文字。
- **MediaRecorder API + Web Audio API**：实现真实录音、回放、音量、停顿、爆音等基础声音指标分析。
- **CSS 变量主题系统**：支持 Anime / Glass 两套视觉主题切换。

### AI 网关

- **智谱 GLM**：默认保留 `glm-4.7-flash`。
- **DeepSeek**：支持 `deepseek-v4-flash`、`deepseek-v4-pro`、`deepseek-chat`、`deepseek-reasoner`。
- **Kimi / Moonshot**：支持 `kimi-k2.6`、`moonshot-v1-8k`、`moonshot-v1-32k`、`moonshot-v1-128k`。
- **自定义模型 ID**：当厂商模型名更新时，可在页面中输入自定义模型 ID。
- **本地兜底策略**：未配置 Key 或接口不可用时，系统仍能基于规则完成简历诊断、JD 匹配、面试反馈和展示流程。

### 测试与质量

- **unittest + Flask test client**：覆盖模型供应商注册、供应商切换、JD 简历优化、模拟面试流程等核心路径。
- **语法检查**：`python -m py_compile` 检查后端，`node --check` 检查前端脚本。
- **Playwright 截图验证（可选）**：用于检查本地页面视觉渲染。

## 目录结构

```text
jobhunter/
├─ app.py                    # Flask 后端入口和主要业务 API
├─ config.py                 # 兼容旧配置和题库配置
├─ requirements.txt          # Python 依赖
├─ README.md                 # 项目说明
├─ LICENSE                   # MIT License
├─ .env.example              # 环境变量示例
├─ .gitignore                # Git 忽略规则
├─ static/
│  ├─ index.html             # 主系统页面
│  ├─ showcase.html          # 项目展示页
│  ├─ css/style.css          # 主题和布局样式
│  ├─ js/app.js              # 前端交互逻辑
│  └─ assets/                # AI 生成视觉素材和提示词
├─ tests/
│  └─ test_core_features.py  # 核心功能测试
└─ utils/
   ├─ ai_client.py           # 多模型 AI 网关
   ├─ resume_analyzer.py     # 兼容旧版简历分析工具
   ├─ job_matcher.py         # 兼容旧版岗位匹配工具
   └─ interview_engine.py    # 兼容旧版面试引擎
```

运行时生成的 `jobhunter.db`、`uploads/`、`exports/`、`output/` 不提交到仓库。

## 快速开始

```powershell
cd "C:\Users\唐乐\Desktop\实训\项目\jobhunter"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

访问：

```text
http://localhost:5000
http://localhost:5000/showcase.html
```

## 模型配置

页面右上角点击“模型配置”，选择供应商、模型并填写对应 API Key。

智谱 GLM API Key 获取地址：

```text
https://open.bigmodel.cn/apikey/platform
```

也可以使用环境变量：

```powershell
$env:GLM_API_KEY="你的智谱 Key"
$env:DEEPSEEK_API_KEY="你的 DeepSeek Key"
$env:KIMI_API_KEY="你的 Kimi Key"
$env:MOONSHOT_API_KEY="你的 Moonshot Key"
python app.py
```

## 常用接口

- `GET /api/dashboard/<user_id>`：项目总览、求职准备度、下一步行动。
- `POST /api/resumes`：保存文本简历。
- `POST /api/resumes/upload`：上传并解析简历文件。
- `PUT /api/resumes/<resume_id>`：编辑更新简历。
- `GET /api/resumes/<resume_id>/original`：打开原始简历文件。
- `POST /api/resumes/<resume_id>/replace-file`：替换原始简历文件。
- `POST /api/resumes/<resume_id>/audit`：简历结构诊断。
- `POST /api/resumes/<resume_id>/improve`：生成优化版简历。
- `POST /api/resumes/<resume_id>/tailor`：按 JD 定制简历。
- `GET /api/resumes/<resume_id>/export/pdf`：导出 PDF。
- `GET /api/resumes/<resume_id>/export/word`：导出 Word。
- `POST /api/interview/sessions`：开始模拟面试。
- `POST /api/interview/sessions/<session_id>/answer`：提交面试回答。
- `POST /api/interview/analyze-audio`：真实录音分析。
- `POST /api/interview/practice-feedback`：题库练习评分。
- `GET /api/training-records/<user_id>`：训练记录查询。
- `POST /api/applications`：新增投递记录。
- `POST /api/applications/<application_id>/coach`：生成投递跟进建议。
- `POST /api/career/report/<user_id>`：生成求职作战报告。

## 测试

```powershell
python -m py_compile app.py utils\ai_client.py
python tests\test_core_features.py
node --check static\js\app.js
```

## 可写进简历的项目描述

项目名称：基于 AI 智能体的求职辅助 Web 系统

- 设计并实现面向求职场景的 AI Agent Web 系统，覆盖简历管理、JD 匹配、简历优化、模拟面试、语音表达分析、投递追踪和 AI 求职教练等模块。
- 封装多模型 AI 网关，支持智谱 GLM、DeepSeek、Kimi / Moonshot 供应商切换和自定义模型 ID，并设计本地规则兜底，保证 API 不可用时核心流程仍可演示和测试。
- 实现 JD 驱动的简历优化能力，输出关键词命中、能力差距、匹配分、项目经历改写和面试讲述要点，提升简历与岗位的对应度。
- 设计真实模拟面试流程，包含自我介绍、项目深挖、技术追问、行为面和反问环节，并对回答进行语速、停顿、结构感、关键词命中和表达升级分析。
- 使用 Flask + SQLite 提供后端接口，原生 JavaScript + Chart.js 构建前端交互，并补充核心接口测试，形成可演示、可测试、可迭代的实训项目。

## 项目体检与后续优化方向

详见 [docs/PRODUCT_AUDIT.md](docs/PRODUCT_AUDIT.md)。
