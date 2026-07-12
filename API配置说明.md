# 模型 API 配置说明

职途 AI 支持“远程模型 + 确定性本地规则”两种运行模式。没有 API Key 时，简历、机会、面试、看板、基础匹配和 Agent 操作提案仍可运行；界面会明确显示本地模式，不伪造远程模型结果。

## 支持的供应商

| 供应商 | 环境变量 | Key 管理入口 |
| --- | --- | --- |
| 智谱 GLM | `GLM_API_KEY` | <https://open.bigmodel.cn/apikey/platform> |
| DeepSeek | `DEEPSEEK_API_KEY` | <https://platform.deepseek.com/api_keys> |
| Kimi / Moonshot | `KIMI_API_KEY` 或 `MOONSHOT_API_KEY` | <https://platform.moonshot.cn/console/api-keys> |

模型 ID 可能由供应商调整，请以供应商控制台和项目页面中的可选项为准。`JOBHUNTER_MODEL` 或页面自定义模型 ID 可以覆盖默认值，但不会改变供应商 API 地址。

## 页面临时配置

启动系统，打开“模型配置”，选择供应商和模型后输入 Key。Key 通过本机回环 HTTP 发送到 Flask，只保存在当前 Python 进程内存中：

- 不写入 SQLite；
- 不写入浏览器 localStorage；
- 不写入仓库；
- 服务退出后失效。

该方式适合本机演示。不要在已改为局域网或公网监听的未加密服务中提交 Key。

## 环境变量配置

项目根目录的 `.env.example` 是变量清单，应用不会自动加载 `.env` 文件。请在启动进程前设置环境变量，例如：

```powershell
$env:GLM_API_KEY = "你的 Key"
$env:JOBHUNTER_MODEL = "供应商支持的模型 ID"
python app.py
```

也可以在操作系统或安全的开发工具中管理环境变量。不要把真实 Key 写入 `.env.example`、脚本、截图或 Git 历史。

## 数据传输边界

启用远程模型后，为完成请求所需的用户消息、经过裁剪的上下文和工具结果会发送到所选供应商。简历、JD 和面试内容可能包含个人信息，请先阅读供应商隐私条款并按需脱敏。

Agent 的业务写入仍由本地动作提案控制：远程模型只能提出操作，用户确认后由本地领域服务执行。网页搜索和抓取是另外的外部访问能力，仅在任务需要时调用，并拒绝本机和内网地址。

## 故障排查

- 显示“本地模式”：确认 Key、供应商和模型 ID 是否匹配，并检查网络。
- 远程接口报错：系统会返回可诊断错误或降级；查看 `output/runtime/server-error.log`。
- 修改环境变量后无效：重新启动 Python 进程。
- 页面配置重启后丢失：这是设计行为；需要持久配置时使用系统环境变量或受控启动脚本。

更多运行和隐私说明见 [README](README.md) 与 [架构说明](docs/ARCHITECTURE.md)。
