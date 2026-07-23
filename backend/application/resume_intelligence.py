from __future__ import annotations

import json
import os
from collections.abc import Callable
from typing import Any

from utils.agent_runtime.resume_draft import model_resume_draft
from utils.ai_client import extract_keywords
from utils.domain.database import connect

from .resume_analysis import (
    CAREER_PROFILES,
    build_career_radar,
    build_resume_audit,
    career_jd_focus,
    extract_jd_focus,
    score_resume_against_jd,
    select_career_profile,
    tailor_resume_locally,
)


class ResumeIntelligenceModule:
    """Own resume intelligence, JD analysis, and their persisted evidence."""

    def __init__(
        self,
        db_path: str | os.PathLike[str],
        ai_client_provider: Callable[[], Any],
        *,
        local_user_id: int,
    ):
        self._db_path = os.fspath(db_path)
        self._ai_client_provider = ai_client_provider
        self._local_user_id = int(local_user_id)

    def analyze(self, resume_id: int, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = self._resume(resume_id)
        if row is None:
            return self._missing()
        result = self._ai_client_provider().analyze_resume(
            row["content"], body.get("job_title", "")
        )
        analysis = result["content"]
        with connect(self._db_path) as connection:
            connection.execute(
                "UPDATE resumes SET analysis_result = ? WHERE id = ? AND user_id = ?",
                (analysis, resume_id, self._local_user_id),
            )
        return {
            "success": True,
            "analysis": analysis,
            "keywords": extract_keywords(row["content"]),
            "ai_used": result["success"],
            "provider": result["provider"],
        }, 200

    def audit(self, resume_id: int, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = self._resume(resume_id)
        if row is None:
            return self._missing()
        return {
            "success": True,
            **build_resume_audit(row["content"], body.get("job_title", ""), body.get("jd", "")),
        }, 200

    def improve(self, resume_id: int, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = self._resume(resume_id)
        if row is None:
            return self._missing()
        job_title = body.get("job_title") or "目标岗位"
        improved = self._improved(row["content"], job_title, body.get("jd") or "")
        new_title = f"{row['title']}-优化版"
        new_id = None
        if body.get("save", True):
            with connect(self._db_path) as connection:
                cursor = connection.execute(
                    """INSERT INTO resumes
                       (user_id, title, content, analysis_result, tailored_result)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        self._local_user_id,
                        new_title,
                        improved["improved_resume"],
                        json.dumps(improved["audit"], ensure_ascii=False),
                        json.dumps(improved, ensure_ascii=False),
                    ),
                )
                new_id = int(cursor.lastrowid)
        return {
            "success": True,
            "new_resume_id": new_id,
            "new_title": new_title,
            **improved,
        }, 200

    def optimize(self, resume_id: int, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = self._resume(resume_id)
        if row is None:
            return self._missing()
        improved = self._improved(row["content"], body.get("job_title", ""), body.get("jd", ""))
        client = self._ai_client_provider()
        return {
            "success": True,
            "suggestions": improved["improved_resume"],
            "ai_used": improved["ai_used"],
            "provider": client.provider.id if improved["ai_used"] else "local",
        }, 200

    def tailor(self, resume_id: int, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        row = self._resume(resume_id)
        if row is None:
            return self._missing()
        job_title = str(body.get("job_title") or "目标岗位").strip()
        jd = str(body.get("jd") or body.get("job_requirements") or "").strip()
        tailored = tailor_resume_locally(row["content"], job_title, jd)
        client = self._ai_client_provider()
        draft = (
            model_resume_draft(client, row["content"], job_title, jd, timeout=55)
            if jd and client.api_key
            else None
        )
        if draft and draft.mode == "model":
            tailored["ai_rewrite"] = draft.content
        with connect(self._db_path) as connection:
            connection.execute(
                """UPDATE resumes SET tailored_result = ?
                   WHERE id = ? AND user_id = ?""",
                (
                    json.dumps(tailored, ensure_ascii=False),
                    resume_id,
                    self._local_user_id,
                ),
            )
        return {
            "success": True,
            **tailored,
            "ai_used": bool(draft and draft.mode == "model"),
        }, 200

    def job_match(self, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        resume_id = self._positive_integer(body.get("resume_id"), "resume_id", required=True)
        application_id = self._positive_integer(
            body.get("application_id"), "application_id", required=False
        )
        row = self._resume_any_owner(resume_id)
        if row is None:
            return {"success": False, "message": "resume not found"}, 404
        if int(row["user_id"]) != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")
        if application_id is not None:
            with connect(self._db_path) as connection:
                application = connection.execute(
                    """SELECT id FROM job_applications
                       WHERE id = ? AND user_id = ? AND deleted_at IS NULL""",
                    (application_id, self._local_user_id),
                ).fetchone()
            if application is None:
                return {"success": False, "message": "opportunity not found"}, 404
        job_title = str(body.get("job_title") or "目标岗位").strip()[:300]
        jd = str(body.get("job_requirements") or body.get("jd") or "")
        score, matched, missing = score_resume_against_jd(row["content"], jd + " " + job_title)
        ai = self._ai_client_provider().match_job(row["content"], job_title, jd)
        analysis = ai.get("content", "")
        details = {
            "matched": matched,
            "missing": missing,
            "provider": ai.get("provider") or "local",
            "model": ai.get("model"),
            "ai_used": bool(ai.get("success")),
        }
        with connect(self._db_path) as connection:
            connection.execute(
                """INSERT INTO job_matches
                   (user_id, resume_id, job_title, match_score, analysis,
                    jd_text, details_json, application_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    self._local_user_id,
                    resume_id,
                    job_title,
                    score,
                    analysis,
                    jd,
                    json.dumps(details, ensure_ascii=False),
                    application_id,
                ),
            )
        return {
            "success": True,
            "match_score": score,
            "matched_keywords": matched,
            "missing_keywords": missing,
            "analysis": analysis,
            "ai_used": bool(ai.get("success")),
        }, 200

    def skills_radar(self, body: dict[str, Any]) -> dict[str, Any]:
        text = str(body.get("resume_content") or "")
        if body.get("resume_id"):
            row = self._resume(int(body["resume_id"]))
            text = row["content"] if row else text
        profile_key = select_career_profile(
            body, text=text, job_title=str(body.get("job_title") or "")
        )
        if profile_key != "tech" or body.get("career_profile") or body.get("profile"):
            profile = CAREER_PROFILES[profile_key]
            return {
                "success": True,
                "profile": {
                    "id": profile_key,
                    "label": profile["label"],
                    "interviewer": profile["interviewer"],
                },
                "radar_data": build_career_radar(text, profile_key),
                "ai_comment": (
                    f"能力图谱已按「{profile['label']}」画像生成，"
                    "建议优先补足低分维度的真实任务、工具方法和结果证据。"
                ),
                "ai_used": False,
            }
        categories = {
            "编程基础": ["Python", "Java", "Flask", "Spring"],
            "测试能力": ["Selenium", "Pytest", "JMeter", "Postman", "接口测试", "自动化测试"],
            "工程工具": ["Git", "Docker", "Linux", "MySQL", "Redis"],
            "AI 应用": ["AI", "智能体", "大模型"],
            "表达呈现": ["报告", "文档", "沟通", "项目"],
        }
        radar = []
        for name, words in categories.items():
            matched = [word for word in words if word.lower() in text.lower()]
            score = min(10, 3 + len(matched) * 2)
            missing = [word for word in words if word not in matched][:4]
            suggestion = "继续补充项目证据，避免只在技能栏堆关键词。"
            if score <= 5:
                suggestion = (
                    f"建议补充 {name} 证据："
                    f"{', '.join(missing) or '工具/方法/结果'}，"
                    "写进项目经历而不是只放技能栏。"
                )
            elif score <= 7:
                suggestion = f"{name} 基础可用，下一步补充量化结果或真实场景。"
            radar.append(
                {
                    "category": name,
                    "score": score,
                    "matched": matched,
                    "missing": missing,
                    "suggestion": suggestion,
                }
            )
        return {
            "success": True,
            "radar_data": radar,
            "ai_comment": "技能图谱已根据简历关键词生成，建议补足低分象限的项目证据。",
            "ai_used": False,
        }

    def analyze_jd(self, body: dict[str, Any]) -> dict[str, Any]:
        jd = str(body.get("jd_content") or "")
        profile_key = select_career_profile(
            body, text=jd, job_title=str(body.get("job_title") or "")
        )
        profile = CAREER_PROFILES[profile_key]
        keywords = extract_keywords(jd)
        focus = (
            career_jd_focus(jd, profile_key)
            if profile_key != "tech" or body.get("career_profile")
            else extract_jd_focus(jd)
        )
        risk_flags = []
        if any(word in jd for word in ["抗压", "高强度", "能加班", "狼性"]):
            risk_flags.append("JD 中出现高强度/加班暗示，面试时建议确认工作节奏。")
        if not keywords:
            risk_flags.append("JD 信息较少，建议补充岗位职责和任职要求后再分析。")
        focus_summary = "; ".join(
            f"{name}: {', '.join(words) or '未明显出现'}" for name, words in list(focus.items())[:3]
        )
        return {
            "success": True,
            "content": "## JD 解析\n"
            f"- 求职画像：{profile['label']}（模拟面试官：{profile['interviewer']}）\n"
            f"- 核心关键词：{', '.join(keywords) or '需补充 JD'}\n"
            f"- 能力焦点：{focus_summary}\n"
            f"- 风险提示：{'；'.join(risk_flags) if risk_flags else '暂未发现明显风险词'}\n"
            "- 面试准备：准备一个项目深挖案例、一个问题定位案例、一个协作沟通案例。\n"
            "- 简历策略：把 JD 高频词写入项目经历，而不是只堆在技能栏。",
            "keywords": keywords,
            "focus": focus,
            "profile": {
                "id": profile_key,
                "label": profile["label"],
                "interviewer": profile["interviewer"],
            },
            "risk_flags": risk_flags,
            "ai_used": False,
        }

    @staticmethod
    def compare_jds(body: dict[str, Any]) -> dict[str, Any]:
        summaries = [
            f"JD{index}：关键词 {', '.join(extract_keywords(str(jd))[:6]) or '不明显'}"
            for index, jd in enumerate(body.get("jds", []), 1)
        ]
        return {
            "success": True,
            "content": "## 多 JD 对比\n"
            + "\n".join(f"- {item}" for item in summaries)
            + "\n\n建议优先选择关键词与你项目经历重合度最高的岗位。",
            "ai_used": False,
        }

    def _improved(self, resume_text: str, job_title: str, jd: str) -> dict[str, Any]:
        audit = build_resume_audit(resume_text, job_title, jd)
        local = tailor_resume_locally(resume_text, job_title, jd)
        client = self._ai_client_provider()
        draft = (
            model_resume_draft(client, resume_text, job_title, jd, timeout=55)
            if client.api_key
            else None
        )
        return {
            "audit": audit,
            "strategy": [
                "保留真实经历，不编造公司和夸张结果。",
                "把“做过功能”改成“负责什么、如何验证、产出什么”。",
                "优先补齐 JD 高频词，并把关键词放进项目证据里。",
                "生成新版本而不是覆盖原简历，方便对比和回滚。",
            ],
            "improved_resume": (
                draft.content if draft and draft.mode == "model" else local["tailored_resume"]
            ),
            "ai_used": bool(draft and draft.mode == "model"),
        }

    def _resume(self, resume_id: int):
        with connect(self._db_path) as connection:
            return connection.execute(
                "SELECT * FROM resumes WHERE id = ? AND user_id = ?",
                (resume_id, self._local_user_id),
            ).fetchone()

    def _resume_any_owner(self, resume_id: int):
        with connect(self._db_path) as connection:
            return connection.execute("SELECT * FROM resumes WHERE id = ?", (resume_id,)).fetchone()

    @staticmethod
    def _positive_integer(value: Any, name: str, *, required: bool) -> int | None:
        if value in (None, ""):
            if required:
                raise ValueError(f"{name} is required")
            return None
        try:
            normalized = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be a valid integer") from exc
        if normalized <= 0:
            suffix = " is required" if required else " must be positive"
            raise ValueError(name + suffix)
        return normalized

    @staticmethod
    def _missing() -> tuple[dict[str, Any], int]:
        return {"success": False, "message": "简历不存在"}, 404
