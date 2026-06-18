"""AI model gateway for JobHunter AI.

All supported vendors expose OpenAI-compatible chat-completions endpoints.
The gateway keeps provider/model selection explicit and falls back to a local
rules engine when no API key is configured, so the project remains demoable.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Dict, Iterable, List, Optional

import requests


@dataclass(frozen=True)
class AIModelOption:
    id: str
    name: str
    note: str
    recommended_for: str


@dataclass(frozen=True)
class AIProvider:
    id: str
    name: str
    api_url: str
    env_key: str
    default_model: str
    models: List[AIModelOption]
    note: str


class AIProviderRegistry:
    """Catalog of model providers and concrete model ids."""

    def __init__(self) -> None:
        self._providers: Dict[str, AIProvider] = {
            "glm": AIProvider(
                id="glm",
                name="智谱 GLM",
                api_url="https://open.bigmodel.cn/api/paas/v4/chat/completions",
                env_key="GLM_API_KEY",
                default_model="glm-4.7-flash",
                models=[
                    AIModelOption("glm-4.7-flash", "GLM-4.7-Flash", "原项目保留的免费/低成本模型", "日常问答、简历诊断、演示"),
                ],
                note="保留原来的智谱免费模型接入方式。",
            ),
            "deepseek": AIProvider(
                id="deepseek",
                name="DeepSeek",
                api_url="https://api.deepseek.com/chat/completions",
                env_key="DEEPSEEK_API_KEY",
                default_model="deepseek-v4-flash",
                models=[
                    AIModelOption("deepseek-v4-flash", "DeepSeek V4 Flash", "速度优先，适合页面实时反馈", "JD 快速解析、题库评分、AI 教练"),
                    AIModelOption("deepseek-v4-pro", "DeepSeek V4 Pro", "质量优先，适合复杂分析", "简历深度改写、面试复盘"),
                    AIModelOption("deepseek-chat", "DeepSeek Chat 兼容别名", "官方兼容模型名，通常映射到当前 chat 模型", "兼容旧配置"),
                    AIModelOption("deepseek-reasoner", "DeepSeek Reasoner", "推理模型，适合结构化分析", "复杂岗位拆解、职业规划"),
                ],
                note="DeepSeek 采用 OpenAI-compatible 调用格式。",
            ),
            "kimi": AIProvider(
                id="kimi",
                name="Kimi / Moonshot",
                api_url="https://api.moonshot.cn/v1/chat/completions",
                env_key="KIMI_API_KEY",
                default_model="kimi-k2.6",
                models=[
                    AIModelOption("kimi-k2.6", "Kimi K2.6", "新一代 Kimi 模型，适合长文本与 Agent 场景", "长简历、长 JD、综合复盘"),
                    AIModelOption("moonshot-v1-8k", "Moonshot v1 8K", "兼容旧版短上下文模型", "短问答、轻量演示"),
                    AIModelOption("moonshot-v1-32k", "Moonshot v1 32K", "兼容旧版中长上下文模型", "多 JD 对比、长简历"),
                    AIModelOption("moonshot-v1-128k", "Moonshot v1 128K", "兼容旧版长上下文模型", "超长材料分析"),
                ],
                note="Kimi/Moonshot 采用 OpenAI-compatible 调用格式。",
            ),
        }

    def get(self, provider_id: str) -> AIProvider:
        return self._providers.get(provider_id) or self._providers["glm"]

    def has_model(self, provider_id: str, model_id: str) -> bool:
        provider = self.get(provider_id)
        return any(model.id == model_id for model in provider.models)

    def list(self) -> List[AIProvider]:
        return list(self._providers.values())

    def list_public(self) -> List[dict]:
        return [
            {
                "id": provider.id,
                "name": provider.name,
                "api_url": provider.api_url,
                "env_key": provider.env_key,
                "model": provider.default_model,
                "default_model": provider.default_model,
                "note": provider.note,
                "models": [
                    {
                        "id": model.id,
                        "name": model.name,
                        "note": model.note,
                        "recommended_for": model.recommended_for,
                    }
                    for model in provider.models
                ],
            }
            for provider in self.list()
        ]


class MultiModelAIClient:
    """OpenAI-compatible multi-provider client."""

    def __init__(
        self,
        provider_id: str = "glm",
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        registry: Optional[AIProviderRegistry] = None,
    ) -> None:
        self.registry = registry or AIProviderRegistry()
        self.provider = self.registry.get(provider_id)
        self.selected_model = model_id or os.environ.get("JOBHUNTER_MODEL") or self.provider.default_model
        self.api_key = api_key if api_key is not None else self._read_env_key(self.provider)

    @property
    def model(self) -> str:
        return self.selected_model

    def configure(self, provider_id: str, api_key: str = "", model_id: str = "") -> "MultiModelAIClient":
        self.provider = self.registry.get(provider_id)
        self.selected_model = model_id or self.provider.default_model
        self.api_key = api_key or self._read_env_key(self.provider)
        return self

    @staticmethod
    def _read_env_key(provider: AIProvider) -> str:
        if provider.id == "kimi":
            return os.environ.get("KIMI_API_KEY") or os.environ.get("MOONSHOT_API_KEY", "")
        return os.environ.get(provider.env_key, "")

    def available_providers(self) -> List[dict]:
        return self.registry.list_public()

    def chat(
        self,
        messages: List[dict],
        temperature: float = 0.6,
        max_tokens: int = 2200,
        timeout: int = 45,
    ) -> dict:
        if not self.api_key:
            return {
                "success": False,
                "provider": "local",
                "model": "local-career-agent",
                "message": "未配置 API Key，已使用本地智能规则兜底。",
                "content": self._local_response(messages),
            }

        payload = {
            "model": self.selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                self.provider.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "provider": self.provider.id,
                    "model": self.selected_model,
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                }
            return {
                "success": False,
                "provider": self.provider.id,
                "model": self.selected_model,
                "message": f"HTTP {response.status_code}: {response.text[:240]}",
                "content": self._local_response(messages),
            }
        except Exception as exc:
            return {
                "success": False,
                "provider": self.provider.id,
                "model": self.selected_model,
                "message": str(exc),
                "content": self._local_response(messages),
            }

    def analyze_resume(self, resume_content: str, job_title: str = "") -> dict:
        return self.chat([
            {"role": "system", "content": "你是资深招聘顾问。请从岗位匹配、项目含金量、表达质量、量化结果、风险点五个维度诊断简历，并给出具体改法。"},
            {"role": "user", "content": f"目标岗位：{job_title or '未指定'}\n简历：\n{resume_content[:4200]}"},
        ])

    def optimize_resume(self, resume_content: str, job_title: str = "", jd: str = "") -> dict:
        return self.chat([
            {"role": "system", "content": "你是简历优化专家。请输出：1 匹配定位；2 JD关键词；3 原句问题；4 改写示例；5 面试讲述建议。回答要中文、具体、可直接复制修改。"},
            {"role": "user", "content": f"目标岗位：{job_title}\nJD：{jd[:2600]}\n简历：\n{resume_content[:4200]}"},
        ])

    def match_job(self, resume_content: str, job_title: str, job_requirements: str = "") -> dict:
        return self.chat([
            {"role": "system", "content": "你是岗位匹配分析师。请给出0-100匹配分、已命中能力、缺口、投递建议、面试准备清单。"},
            {"role": "user", "content": f"岗位：{job_title}\nJD：{job_requirements[:3200]}\n简历：\n{resume_content[:3600]}"},
        ])

    def agent_chat(self, user_message: str, context: str = "") -> dict:
        return self.chat([
            {"role": "system", "content": "你是 JobHunter AI 求职教练。风格年轻、具体、会追问，能把建议拆成可执行步骤。不要空话。"},
            {"role": "user", "content": f"上下文：{context}\n问题：{user_message}"},
        ])

    def _local_response(self, messages: Iterable[dict]) -> str:
        text = "\n".join(str(item.get("content", "")) for item in messages)
        keywords = extract_keywords(text)
        keyword_lines = "\n".join(f"- {kw}：写进项目动作或测试证据里，不要只堆在技能栏。" for kw in keywords[:6])

        if any(word in text for word in ["JD", "岗位", "简历", "匹配"]):
            return (
                "## 本地求职 Agent 分析\n"
                "### 结论\n"
                "这份材料需要围绕目标岗位重排信息优先级：先让 HR 看到岗位关键词，再用项目证据证明你做过。\n\n"
                "### 关键词策略\n"
                f"{keyword_lines or '- 暂未识别到明显关键词，请补充岗位职责、任职要求和项目技术栈。'}\n\n"
                "### 改写方向\n"
                "- 项目标题写清业务场景，例如“AI 智能体求职辅助 Web 系统”。\n"
                "- 每段经历按“负责模块-使用工具-验证对象-结果产出”组织。\n"
                "- 如果是测试岗位，强调测试用例、接口验证、缺陷闭环、性能指标。\n"
                "- 如果是开发岗位，强调架构设计、模型接入、异常兜底、数据流。\n\n"
                "### 面试讲法\n"
                "用 30 秒讲项目背景，60 秒讲你的职责，60 秒讲一个具体问题如何定位和解决。"
            )

        return (
            "我建议先把问题拆成三步：\n"
            "1. 明确目标岗位和 JD 关键词。\n"
            "2. 找你项目里能证明这些关键词的证据。\n"
            "3. 把证据改写成可面试讲述的 STAR 结构。\n"
            "你可以继续把岗位 JD 或项目经历发给我，我会直接帮你改。"
        )


def extract_keywords(text: str) -> List[str]:
    tech_words = [
        "Python", "Flask", "Django", "FastAPI", "Java", "Spring", "Vue", "React", "TypeScript",
        "Selenium", "Pytest", "JMeter", "Postman", "MySQL", "Redis", "Docker", "Linux",
        "接口测试", "自动化测试", "性能测试", "功能测试", "测试用例", "缺陷", "回归测试",
        "AI", "智能体", "大模型", "Prompt", "JD", "简历", "模拟面试",
    ]
    found: List[str] = []
    lower = text.lower()
    for word in tech_words:
        if word.lower() in lower and word not in found:
            found.append(word)

    chinese_terms = re.findall(r"[\u4e00-\u9fa5]{2,10}", text)
    markers = ["测试", "开发", "简历", "面试", "项目", "岗位", "系统", "接口", "模型", "智能"]
    for term in chinese_terms:
        if term not in found and any(marker in term for marker in markers):
            found.append(term)
        if len(found) >= 14:
            break
    return found


_registry = AIProviderRegistry()
ai_client = MultiModelAIClient(registry=_registry)


def get_ai_client() -> MultiModelAIClient:
    return ai_client


def set_api_key(api_key: str, provider_id: str = "glm", model_id: str = "") -> MultiModelAIClient:
    global ai_client
    ai_client = MultiModelAIClient(provider_id=provider_id, model_id=model_id, api_key=api_key, registry=_registry)
    return ai_client
