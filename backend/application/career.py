from __future__ import annotations

from typing import Any

from utils.domain import APPLICATION_STATUSES


class CareerModule:
    """Own career profile, action item, and application compatibility flows."""

    def __init__(self, career_service: Any, *, local_user_id: int):
        self._career_service = career_service
        self._local_user_id = int(local_user_id)

    def profile(self) -> dict[str, Any]:
        return {
            "success": True,
            "data": self._career_service.get_profile(self._local_user_id),
        }

    def update_profile(self, body: dict[str, Any]) -> dict[str, Any]:
        return {
            "success": True,
            "data": self._career_service.upsert_profile(self._local_user_id, body),
        }

    def profile_result(self, profile_id: int) -> dict[str, Any]:
        profile = self._career_service.get_profile(self._local_user_id)
        if profile is None or int(profile.get("id") or 0) != profile_id:
            raise LookupError("结果不存在或已失效")
        return {"success": True, "data": profile}

    def report_result(self, report_id: int) -> dict[str, Any]:
        report = self._career_service.get_report(self._local_user_id, report_id)
        return {"success": True, "data": report}

    def action_items(self) -> dict[str, Any]:
        return {
            "success": True,
            "data": self._career_service.list_action_items(self._local_user_id),
        }

    def create_action_item(self, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        action = self._career_service.create_action_item(self._local_user_id, body)
        return {"success": True, "data": action}, 201

    def complete_action_item(self, action_id: int, body: dict[str, Any]) -> dict[str, Any]:
        action = self._career_service.complete_action_item(
            self._local_user_id,
            action_id,
            body.get("evidence", ""),
        )
        return {"success": True, "data": action}

    def create_application(self, body: dict[str, Any]) -> tuple[dict[str, Any], int]:
        values = {
            "company": body.get("company", "未命名公司"),
            "job_title": body.get("job_title", "目标岗位"),
            "status": body.get("status", "已投递"),
            "city": body.get("city", ""),
            "salary_min": body.get("salary_min"),
            "salary_max": body.get("salary_max"),
            "notes": body.get("notes", ""),
            "jd_text": body.get("jd_text"),
            "resume_id": body.get("resume_id"),
        }
        application = self._career_service.create_opportunity(self._local_user_id, values)
        return {
            "success": True,
            "application_id": application["id"],
        }, 200

    def applications(self, requested_user_id: int) -> dict[str, Any]:
        self._require_local_user(requested_user_id)
        rows = self._career_service.list_opportunities(self._local_user_id)
        return {
            "success": True,
            "data": rows,
            "canonical_statuses": APPLICATION_STATUSES,
        }

    def application(self, application_id: int) -> dict[str, Any]:
        row = self._career_service.get_opportunity(self._local_user_id, application_id)
        return {"success": True, "data": row}

    def update_application(self, application_id: int, body: dict[str, Any]) -> dict[str, Any]:
        changes = {
            "company": body.get("company", "未命名公司"),
            "job_title": body.get("job_title", "目标岗位"),
            "status": body.get("status", "已投递"),
            "city": body.get("city", ""),
            "notes": body.get("notes", ""),
        }
        self._career_service.update_opportunity(self._local_user_id, application_id, changes)
        return {"success": True, "message": "投递记录已更新"}

    def delete_application(self, application_id: int) -> dict[str, Any]:
        self._career_service.delete_opportunity(self._local_user_id, application_id)
        return {"success": True, "message": "投递记录已删除"}

    def advance_application(self, application_id: int) -> dict[str, Any]:
        opportunity = self._career_service.get_opportunity(self._local_user_id, application_id)
        current = opportunity["status"]
        stages = list(APPLICATION_STATUSES)
        if current == "已结束":
            next_status = current
        elif current in {"Offer", "已拒绝"}:
            next_status = "已结束"
        else:
            next_status = stages[stages.index(current) + 1]
        self._career_service.update_opportunity(
            self._local_user_id,
            application_id,
            {"status": next_status},
        )
        return {"success": True, "status": next_status}

    @staticmethod
    def salary(body: dict[str, Any]) -> dict[str, Any]:
        city_factor = {
            "北京": 1.25,
            "上海": 1.25,
            "深圳": 1.2,
            "广州": 1.05,
            "杭州": 1.15,
            "成都": 0.9,
            "武汉": 0.85,
        }.get(body.get("city"), 1)
        base = {
            "应届生": 9000,
            "1-3年": 15000,
            "3-5年": 24000,
            "5年以上": 36000,
        }.get(body.get("experience", "应届生"), 12000)
        skills_bonus = min(5000, int(body.get("skills_count") or 0) * 500)
        average = int((base + skills_bonus) * city_factor)
        return {
            "success": True,
            "range": {
                "min": int(average * 0.75),
                "avg": average,
                "max": int(average * 1.35),
            },
            "advice": ("谈薪时用岗位 JD 匹配度、项目结果和可立即上手的工具链作为依据。"),
        }

    def _require_local_user(self, requested_user_id: int) -> None:
        if int(requested_user_id) != self._local_user_id:
            raise PermissionError("当前本地版本仅允许访问当前用户数据")
