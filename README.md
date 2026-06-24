# 职途 AI：基于 AI 智能体的求职辅助 Web 系统

职途 AI 是一个围绕真实求职流程设计的 AI Agent Web 系统。系统把简历管理、JD 匹配、简历优化、模拟面试、语音表达分析、题库训练、投递追踪和 AI 求职教练整合成一条完整闭环，目标不是做一个简单聊天页面，而是让用户能按“整理简历 → 匹配岗位 → 优化表达 → 训练面试 → 跟进投递 → 复盘提升”的路径持续推进。

项目展示页：启动后访问 [http://localhost:5000/showcase.html](http://localhost:5000/showcase.html)

GitHub Pages 展示入口：[https://tl66666.github.io/ztai/static/showcase.html](https://tl66666.github.io/ztai/static/showcase.html)

说明：GitHub 仓库地址用于查看源码，GitHub Pages 地址用于打开项目展示页；本地 Flask 的 `/` 入口是主系统页面，`/showcase.html` 是项目展示页；GitHub Pages 的静态展示页位于 `/static/showcase.html`。

主系统入口：启动后访问 [http://localhost:5000](http://localhost:5000)

## 项目定位

- 面向应届生、实习求职、转岗求职和个人求职管理场景。
- 重点解决求职准备分散、简历修改缺乏依据、模拟面试不够真实、投递进度难复盘的问题。
- 通过“多模型 AI 网关 + 本地规则兜底”的方式保证真实 API 可用时更智能、无 Key 时仍可演示和测试。
- 前端提供 Anime 和 Glass 两套主题，兼顾年轻化视觉和职业工具感。

## 核心功能

### 1. 项目总览

- 汇总简历数量、面试次数、JD 匹配次数、投递数量。
- 根据真实数据生成“职业脉冲”状态，包括准备度评分、当前短板、下一步行动建议。
- 支持从总览直接跳转到简历实验室、面试训练场、投递看板。
- 首页 Hero 支持动态视频背景和主题化图片兜底，视觉上区分 Anime / Glass 风格。

### 2. 简历实验室

- **简历录入与上传**：支持粘贴文本，也支持上传 Word、PDF、TXT 等文件，保存原始文件和解析文本。
- **简历管理**：支持查看、编辑、删除、替换原文件、打开原始文件。
- **简历分析**：选择指定简历后，系统会从结构完整度、项目表达、技能证据、量化结果、风险点等角度输出分析。
- **简历修改**：根据分析结果生成可执行的修改建议，包括标题、项目经历、技能描述、成果表达等。
- **JD 优化**：支持粘贴真实招聘 JD，计算关键词命中、岗位匹配度、能力差距和简历改写方向，并提供 Boss 直聘入口方便获取 JD。
- **技能图谱**：根据简历内容生成技能覆盖、短板方向和补强路线，使用雷达图展示能力结构。
- **格式导出与转换**：支持导出 PDF、导出 Word、PDF 转 Word、Word 转 PDF；在 Windows 环境下可优先调用 Microsoft Word 提升转换保真度。
- **版本化思路**：同一用户可保存多份简历，适合维护“测试岗版本、AI 项目版本、校招版本”等不同方向。

### 3. 面试训练场

- **完整模拟面试**：按真实流程推进自我介绍、项目深挖、技术追问、行为面、反问总结。
- **专业知识面试**：按岗位方向生成题组，例如软件测试、Python / Flask、前端基础、AI Agent 等。
- **题库训练**：支持答题、查看解析、跳过下一题、保存评分和反馈。
- **统一回答工作区**：文本输入、语音识别、真实录音、录音回放和 AI 反馈集中在一个区域，避免多处回答入口混乱。
- **语音能力**：使用 Web Speech API 做语音转文字，使用 MediaRecorder API 录制真实音频，支持回放自己的回答。
- **语音分析**：结合音频时长、文本长度、语速、停顿、语气词和结构感给出表达建议。
- **训练记录**：保存模拟面试、题库练习、语音回答和 AI 反馈，可查看详情、回放语音、删除记录。
- **幻觉控制**：当用户回答“不知道、下一题、跳过”时，系统不会强行编造高分反馈，而是给出合理跳过、参考答案或学习方向。

### 4. 投递看板

- 新增投递记录，记录公司、岗位、阶段、城市和备注。
- 按投递阶段组织机会池，避免多个岗位混在一起。
- 支持生成跟进建议、风险提醒、沟通话术和复盘建议。
- 薪资评估根据城市、经验、技能数量等信息给出参考区间。

### 5. AI 求职教练

- 结合当前简历、JD、投递、面试和训练记录回答求职问题。
- 支持生成阶段性求职作战报告。
- 提醒用户补齐简历证据、练习薄弱题型、复盘投递结果。

### 6. 双主题视觉系统

- **Anime 主题**：二次元轻潮流风格，使用柔和粉、薄荷绿、浅紫和插画素材，适合年轻用户体验。
- **Glass 主题**：玻璃拟态科技风格，弱化角色感，强调透明层次、暗色面板和职业工具感，适合正式展示。
- 主题切换会同步影响 Logo、背景、卡片、Hero 图、状态组件和视觉资产。

## 技术栈

### 后端

- **Python 3**：项目主要后端语言。
- **Flask**：提供 REST API、静态资源服务、文件上传下载和业务流程编排。
- **SQLite**：本地轻量数据库，存储简历、投递、面试会话、训练记录、JD 匹配和语音分析记录。
- **Requests**：封装多厂商模型 API 请求。
- **python-docx**：读取和生成 Word 简历。
- **reportlab**：生成 PDF 文件，并处理中文字体注册。
- **pdf2docx / PyPDF2**：处理 PDF 文本提取、PDF 转 Word 等格式转换。
- **Microsoft Word COM（Windows 可选）**：Word 转 PDF 时优先调用本机 Office，提高图片和排版保真度。

### 前端

- **HTML / CSS / JavaScript 原生实现**：无复杂构建链，适合本地部署、课堂演示和实训验收。
- **CSS Variables**：实现 Anime / Glass 双主题切换。
- **Chart.js**：绘制技能雷达图和能力结构图。
- **Lucide Icons**：统一图标系统。
- **Web Speech API**：浏览器语音转文字。
- **MediaRecorder API**：录制真实音频回答。
- **Web Audio API**：辅助分析音频音量、时长、停顿等基础指标。
- **HTML5 Video**：独立产品页面使用视频素材增强视觉表现。

### AI 网关

- **智谱 GLM**：默认保留 `glm-4.7-flash`。
- **DeepSeek**：支持 `deepseek-v4-flash`、`deepseek-v4-pro`、`deepseek-chat`、`deepseek-reasoner`。
- **Kimi / Moonshot**：支持 `kimi-2.6`、`moonshot-v1-8k`、`moonshot-v1-32k`、`moonshot-v1-128k`。
- **自定义模型 ID**：前端可以输入自定义模型名称，用于适配后续新增模型。
- **本地规则兜底**：无 Key、网络失败或 API 异常时，系统仍能基于规则完成简历诊断、JD 匹配、面试反馈和展示流程。

### 测试与质量

- **unittest + Flask test client**：覆盖核心后端接口和 AI 客户端配置逻辑。
- **node --check**：检查前端脚本语法。
- **python -m py_compile**：检查后端 Python 语法。
- **Playwright 截图验证（可选）**：用于检查页面视觉效果。
- **Git 忽略规范**：数据库、上传文件、导出文件、截图输出、个人简历文件和 `.env` 不提交到仓库。

## 数据流设计

```text
用户输入/上传
  -> 前端模块收集上下文
  -> Flask API
  -> SQLite 持久化
  -> AI 网关或本地规则引擎
  -> 结构化 JSON 结果
  -> 前端渲染分析报告、面试反馈、技能图谱或投递建议
```

典型流程：

1. 用户上传简历，系统保存原始文件并解析文本。
2. 用户粘贴岗位 JD，系统提取关键词并与简历做匹配。
3. AI 或本地规则生成匹配分、风险点、改写建议和面试讲述要点。
4. 用户进入面试训练，基于目标岗位进行模拟问答。
5. 系统保存文本、录音、语音分析和 AI 反馈。
6. 投递看板记录岗位阶段，AI 教练根据全局数据给出下一步建议。

## 目录结构

```text
jobhunter/
├── app.py                         # Flask 后端入口和主要业务 API
├── config.py                      # 兼容旧版的题库、技能词和配置数据
├── requirements.txt               # Python 依赖
├── README.md                      # 项目说明
├── API配置说明.md                 # 模型 API 配置说明
├── 测试步骤说明.md                # 验收和测试步骤
├── LICENSE                        # MIT License
├── .env.example                   # 环境变量示例
├── .gitignore                     # Git 忽略规则
├── docs/
│   └── PRODUCT_AUDIT.md           # 产品体检与改造记录
├── static/
│   ├── index.html                 # 主系统页面
│   ├── showcase.html              # 项目展示页
│   ├── css/style.css              # 主题和布局样式
│   ├── js/app.js                  # 前端交互逻辑
│   └── assets/                    # 图片、视频和提示词素材
├── tests/
│   └── test_core_features.py      # 核心功能测试
└── utils/
    ├── ai_client.py               # 多模型 AI 网关
    ├── resume_analyzer.py         # 兼容旧版简历分析工具
    ├── job_matcher.py             # 兼容旧版岗位匹配工具
    └── interview_engine.py        # 兼容旧版面试引擎
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

- `GET /api/dashboard/<user_id>`：项目总览、职业脉冲、下一步行动。
- `GET /api/resumes/<user_id>`：获取简历列表。
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
- `POST /api/interview/analyze-audio`：分析真实录音。
- `POST /api/interview/practice-feedback`：题库练习评分。
- `GET /api/training-records/<user_id>`：查询训练记录。
- `DELETE /api/training-records/<record_id>`：删除训练记录。
- `POST /api/applications`：新增投递记录。
- `POST /api/applications/<application_id>/coach`：生成投递跟进建议。
- `POST /api/career/report/<user_id>`：生成求职作战报告。
- `POST /api/config/model`：保存模型配置。

## 测试

```powershell
python -m py_compile app.py utils\ai_client.py
python tests\test_core_features.py
node --check static\js\app.js
```

## 项目文档

- [API 配置说明](API配置说明.md)
- [测试步骤说明](测试步骤说明.md)
- [产品体检与改造记录](docs/PRODUCT_AUDIT.md)
