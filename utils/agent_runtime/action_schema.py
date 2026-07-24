from __future__ import annotations

from copy import deepcopy
from typing import Any

from utils.domain.career import (
    ACTION_STATUSES,
    RESUME_SOURCE_TYPES,
    RESUME_STATUSES,
)
from utils.domain.database import APPLICATION_STATUSES

ALLOWED_ACTION_TYPES = frozenset(
    {
        "set_career_goal",
        "create_opportunity",
        "create_resume_version",
        "link_opportunity_resume",
        "create_interview_plan",
        "create_action_item",
        "complete_action_item",
        "update_opportunity",
        "save_career_report",
    }
)
PROPOSAL_STATUSES = frozenset(
    {"pending", "executing", "completed", "cancelled", "expired", "failed"}
)
DEFAULT_EXPIRY_MINUTES = 30
EXECUTION_LEASE_SECONDS = 30

OPPORTUNITY_TEXT_LIMITS = {
    "company": 300,
    "job_title": 300,
    "status": 50,
    "city": 200,
    "notes": 20_000,
    "jd_text": 200_000,
    "source_url": 2_000,
    "channel": 200,
    "contact_name": 300,
    "contact_info": 2_000,
    "next_action_at": 100,
    "interview_at": 100,
    "deadline_at": 100,
    "rejection_reason": 5_000,
    "offer_details": 20_000,
}
OPPORTUNITY_FIELDS = frozenset(
    {*OPPORTUNITY_TEXT_LIMITS, "salary_min", "salary_max", "resume_id", "priority"}
)


def _schema_object(properties: dict[str, Any], required: tuple[str, ...] = ()) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _schema_text(limit: int, *, required: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "string", "maxLength": limit}
    if required:
        schema["minLength"] = 1
    return schema


def _schema_integer(minimum: int | None = None, maximum: int | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "integer"}
    if minimum is not None:
        schema["minimum"] = minimum
    if maximum is not None:
        schema["maximum"] = maximum
    return schema


def _opportunity_argument_properties() -> dict[str, Any]:
    properties = {
        field: _schema_text(limit, required=field in {"company", "job_title", "status"})
        for field, limit in OPPORTUNITY_TEXT_LIMITS.items()
    }
    properties["status"] = {
        "type": "string",
        "enum": list(APPLICATION_STATUSES),
    }
    properties.update(
        {
            "salary_min": _schema_integer(0, 1_000_000_000),
            "salary_max": _schema_integer(0, 1_000_000_000),
            "resume_id": _schema_integer(1),
            "priority": _schema_integer(-1000, 1000),
        }
    )
    return properties


def _career_action_argument_schemas() -> dict[str, dict[str, Any]]:
    string_list_200 = {
        "type": "array",
        "maxItems": 200,
        "items": _schema_text(500, required=True),
    }
    preference_list = {
        "type": "array",
        "maxItems": 50,
        "items": _schema_text(100, required=True),
    }
    profile = _schema_object(
        {
            "career_direction": _schema_text(10_000),
            "target_role": _schema_text(10_000),
            "cities": string_list_200,
            "salary": _schema_object(
                {
                    "min": _schema_integer(0, 1_000_000_000),
                    "max": _schema_integer(0, 1_000_000_000),
                    "currency": _schema_text(50, required=True),
                }
            ),
            "experience": _schema_text(10_000),
            "confirmed_skills": string_list_200,
            "preferences": _schema_object(
                {
                    "remote": {"type": "boolean"},
                    "hybrid": {"type": "boolean"},
                    "onsite": {"type": "boolean"},
                    "relocation": {"type": "boolean"},
                    "employment_types": preference_list,
                    "work_modes": preference_list,
                    "industries": preference_list,
                    "company_sizes": preference_list,
                }
            ),
            "constraints": string_list_200,
        }
    )
    profile["minProperties"] = 1

    metadata = _schema_object(
        {
            "version_label": _schema_text(300),
            "target_job_title": _schema_text(300),
            "application_id": _schema_integer(1),
            "status": {"type": "string", "enum": list(RESUME_STATUSES)},
            "source_type": {"type": "string", "enum": list(RESUME_SOURCE_TYPES)},
            "title": _schema_text(300),
            "action_id": _schema_integer(1),
        }
    )
    action_item_properties = {
        "opportunity_id": _schema_integer(1),
        "application_id": _schema_integer(1),
        "title": _schema_text(500, required=True),
        "type": _schema_text(100),
        "description": _schema_text(20_000),
        "status": {"type": "string", "enum": list(ACTION_STATUSES)},
        "priority": _schema_integer(-1000, 1000),
        "due_date": _schema_text(100),
        "due_at": _schema_text(100),
    }
    changes = _schema_object(_opportunity_argument_properties())
    changes["minProperties"] = 1
    report_content = {
        "type": "object",
        "maxProperties": 500,
        "x-maxDataDepth": 10,
        "propertyNames": {"type": "string", "minLength": 1, "maxLength": 200},
        "additionalProperties": {"$ref": "#/$defs/jsonValue"},
    }
    return {
        "set_career_goal": profile,
        "create_opportunity": _schema_object(
            _opportunity_argument_properties(), ("company", "job_title")
        ),
        "create_resume_version": _schema_object(
            {
                "resume_id": _schema_integer(1),
                "content": _schema_text(1_000_000, required=True),
                "metadata": metadata,
            },
            ("resume_id", "content", "metadata"),
        ),
        "link_opportunity_resume": _schema_object(
            {"opportunity_id": _schema_integer(1), "resume_id": _schema_integer(1)},
            ("opportunity_id", "resume_id"),
        ),
        "create_interview_plan": _schema_object(
            {
                "opportunity_id": _schema_integer(1),
                "title": _schema_text(500, required=True),
                "description": _schema_text(20_000),
                "due_at": _schema_text(100),
            },
            ("opportunity_id",),
        ),
        "create_action_item": _schema_object(action_item_properties, ("title",)),
        "complete_action_item": _schema_object(
            {"action_id": _schema_integer(1), "evidence": _schema_text(20_000)},
            ("action_id",),
        ),
        "update_opportunity": _schema_object(
            {"opportunity_id": _schema_integer(1), "changes": changes},
            ("opportunity_id", "changes"),
        ),
        "save_career_report": _schema_object(
            {
                "action_id": _schema_integer(1),
                "report_type": _schema_text(100, required=True),
                "title": _schema_text(500),
                "period_start": _schema_text(100),
                "period_end": _schema_text(100),
                "content": report_content,
                "status": {"type": "string", "enum": ["draft", "ready", "archived"]},
            },
            ("report_type", "content"),
        ),
    }


def career_action_tool_schema() -> dict[str, Any]:
    """Return the model-facing schema derived from canonical action validation."""
    rationale = _schema_text(1000)
    argument_schemas = _career_action_argument_schemas()
    branches = []
    for action_type in sorted(ALLOWED_ACTION_TYPES):
        branches.append(
            _schema_object(
                {
                    "action_type": {"const": action_type},
                    "arguments": argument_schemas[action_type],
                    "rationale": rationale,
                },
                ("action_type", "arguments"),
            )
        )
    schema = _schema_object(
        {
            "action_type": {"type": "string", "enum": sorted(ALLOWED_ACTION_TYPES)},
            "arguments": {"type": "object"},
            "rationale": rationale,
        },
        ("action_type", "arguments"),
    )
    schema["oneOf"] = branches
    schema["$defs"] = {
        "jsonValue": {
            "oneOf": [
                {"type": "null"},
                {"type": "boolean"},
                {
                    "type": "number",
                    "minimum": -1_000_000_000_000_000,
                    "maximum": 1_000_000_000_000_000,
                },
                {"type": "string", "maxLength": 20_000},
                {
                    "type": "array",
                    "maxItems": 500,
                    "items": {"$ref": "#/$defs/jsonValue"},
                },
                {
                    "type": "object",
                    "maxProperties": 500,
                    "propertyNames": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 200,
                    },
                    "additionalProperties": {"$ref": "#/$defs/jsonValue"},
                },
            ]
        }
    }
    return deepcopy(schema)
