from __future__ import annotations

from typing import Any


class ActionExecutionMixin:
    def _execute(self, action_type: str, arguments: dict[str, Any], source: str) -> dict[str, Any]:
        service = self.career_service
        user_id = self.local_user_id
        if action_type == "set_career_goal":
            entity = service.upsert_profile(user_id, arguments, source=source)
            return self._result("career_profile", entity)
        if action_type == "create_opportunity":
            entity = service.create_opportunity(user_id, arguments, source=source)
            return self._result("opportunity", entity)
        if action_type == "create_resume_version":
            entity = service.create_resume_version(
                user_id,
                arguments["resume_id"],
                arguments["content"],
                arguments["metadata"],
                source=source,
            )
            return self._result("resume", entity)
        if action_type == "link_opportunity_resume":
            entity = service.update_opportunity(
                user_id,
                arguments["opportunity_id"],
                {"resume_id": arguments["resume_id"]},
                source=source,
            )
            return self._result("opportunity", entity)
        if action_type == "create_interview_plan":
            values = {
                "opportunity_id": arguments["opportunity_id"],
                "title": arguments.get("title", "Prepare interview"),
                "description": arguments.get("description"),
                "due_at": arguments.get("due_at"),
                "type": "interview_plan",
            }
            entity = service.create_action_item(user_id, values, source=source)
            return self._result("action_item", entity)
        if action_type == "create_action_item":
            entity = service.create_action_item(user_id, arguments, source=source)
            return self._result("action_item", entity)
        if action_type == "complete_action_item":
            entity = service.complete_action_item(
                user_id,
                arguments["action_id"],
                arguments.get("evidence", ""),
                source=source,
            )
            return self._result("action_item", entity)
        if action_type == "update_opportunity":
            entity = service.update_opportunity(
                user_id, arguments["opportunity_id"], arguments["changes"], source=source
            )
            return self._result("opportunity", entity)
        if action_type == "save_career_report":
            entity = service.save_report(user_id, arguments, source=source)
            return self._result("career_report", entity)
        raise ValueError("invalid action type")

    @staticmethod
    def _result(entity_type: str, entity: dict[str, Any]) -> dict[str, Any]:
        result = {"entity_type": entity_type, "id": entity.get("id")}
        if "status" in entity:
            result["status"] = entity["status"]
        return result
