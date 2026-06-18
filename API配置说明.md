# API 配置说明

本项目支持“真实大模型调用 + 本地规则兜底”的双引擎模式。没有 API Key 时，系统仍然可以完成简历解析、JD 匹配、题库练习和基础面试反馈；配置 API Key 后，会启用更完整的智能体分析能力。

## 支持的模型厂商

| 厂商 | 默认模型 | 获取 API Key |
| --- | --- | --- |
| 智谱 GLM | GLM-4.7-Flash | <https://open.bigmodel.cn/apikey/platform> |
| DeepSeek | deepseek-v4-pro / deepseek-v4-flash | <https://platform.deepseek.com/api_keys> |
| Kimi / Moonshot | kimi-2.6 | <https://platform.moonshot.cn/console/api-keys> |

前端右上角进入“模型配置”，可以选择厂商、模型，也可以输入自定义模型 ID。自定义模型 ID 会优先覆盖下拉模型，适合以后替换为兼容 OpenAI Chat Completions 协议的新模型。

## 推荐配置方式

### 方式一：页面临时配置

1. 启动项目并访问 <http://localhost:5000>。
2. 点击右上角“模型配置”。
3. 选择厂商和模型。
4. 粘贴对应厂商的 API Key。
5. 点击保存后，左下角状态会显示当前供应商和模型。

这种方式适合演示和调试。Key 保存在浏览器本地，不会写入仓库。

### 方式二：环境变量配置

复制 `.env.example` 为 `.env`，按需填写：

```bash
GLM_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
KIMI_API_KEY=sk-xxx
```

`.env` 已被 `.gitignore` 忽略，不应提交到 GitHub。

## 后端智能体调用逻辑

系统通过 `utils/ai_client.py` 统一封装模型调用：

1. 前端提交任务类型、简历文本、JD、面试回答等上下文。
2. 后端根据当前模型配置生成结构化提示词。
3. 优先调用真实模型接口。
4. 如果缺少 Key、接口失败或网络异常，自动降级到本地规则引擎。
5. 返回统一 JSON，前端按模块渲染为分析报告、修改建议、面试反馈或训练记录。

这种设计可以保证项目在课堂验收、离线演示和真实使用三种场景下都能运行。

## 常见问题

**Q：没有 API Key 能不能演示？**  
可以。系统会进入“本地兜底”模式，核心流程仍然可用。

**Q：为什么模型回复不够强？**  
先确认右上角模型配置是否保存成功，再检查 Key 是否属于对应厂商。如果 Key 不匹配，系统会降级。

**Q：自定义模型 ID 有什么用？**  
用于兼容同厂商新增模型，或接入 OpenAI 兼容接口时快速切换模型名称。

**Q：API Key 会不会上传到 GitHub？**  
不会。`.env`、数据库、上传文件、导出文件都已加入忽略列表。
