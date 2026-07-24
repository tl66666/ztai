from __future__ import annotations

import math
import re


def validate_tool_arguments(schema: dict, arguments: dict) -> list[str]:
    return _validate_schema_value(schema, arguments, "参数", schema, 0, 0, None)


def _validate_schema_value(
    schema: dict,
    value,
    path: str,
    root_schema: dict,
    schema_depth: int,
    data_depth: int,
    max_data_depth: int | None,
) -> list[str]:
    if schema_depth > 100:
        return [f"{path} 结构过于复杂"]
    if "x-maxDataDepth" in schema:
        max_data_depth = int(schema["x-maxDataDepth"])
        data_depth = 0
    if max_data_depth is not None and data_depth > max_data_depth:
        return [f"{path} 嵌套过深"]
    if "$ref" in schema:
        target = _resolve_local_ref(root_schema, schema["$ref"])
        return _validate_schema_value(
            target,
            value,
            path,
            root_schema,
            schema_depth + 1,
            data_depth,
            max_data_depth,
        )

    errors: list[str] = []
    if "oneOf" in schema:
        matches = [
            branch
            for branch in schema["oneOf"]
            if not _validate_schema_value(
                branch,
                value,
                path,
                root_schema,
                schema_depth + 1,
                data_depth,
                max_data_depth,
            )
        ]
        if len(matches) != 1:
            errors.append(f"{path} 不符合允许结构")
            return errors

    if "const" in schema and value != schema["const"]:
        return [f"{path} 必须为 {schema['const']}"]
    if "enum" in schema and value not in schema["enum"]:
        return [f"{path} 不在允许范围"]

    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_matches_schema_type(item, value) for item in expected_types):
            return [f"{path} 类型错误"]

    if isinstance(value, dict):
        if len(value) < schema.get("minProperties", 0):
            errors.append(f"{path} 字段不足")
        if len(value) > schema.get("maxProperties", 1_000_000):
            errors.append(f"{path} 字段过多")
        properties = schema.get("properties", {})
        property_names = schema.get("propertyNames")
        if isinstance(property_names, dict):
            for key in value:
                errors.extend(
                    _validate_schema_value(
                        property_names,
                        key,
                        f"{path} 字段名",
                        root_schema,
                        schema_depth + 1,
                        data_depth,
                        max_data_depth,
                    )
                )
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"缺少参数 {path}.{key}")
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if key in properties:
                errors.extend(
                    _validate_schema_value(
                        properties[key],
                        item,
                        child_path,
                        root_schema,
                        schema_depth + 1,
                        data_depth + 1,
                        max_data_depth,
                    )
                )
            elif additional is False:
                errors.append(f"不支持参数 {child_path}")
            elif isinstance(additional, dict):
                errors.extend(
                    _validate_schema_value(
                        additional,
                        item,
                        child_path,
                        root_schema,
                        schema_depth + 1,
                        data_depth + 1,
                        max_data_depth,
                    )
                )
    elif isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path} 项目不足")
        if len(value) > schema.get("maxItems", 1_000_000):
            errors.append(f"{path} 项目过多")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(
                    _validate_schema_value(
                        item_schema,
                        item,
                        f"{path}[{index}]",
                        root_schema,
                        schema_depth + 1,
                        data_depth + 1,
                        max_data_depth,
                    )
                )
    elif isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path} 太短")
        if len(value) > schema.get("maxLength", 1_000_000):
            errors.append(f"{path} 太长")
        pattern = schema.get("pattern")
        if pattern and not re.fullmatch(pattern, value):
            errors.append(f"{path} 格式错误")
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path} 必须是有限数字")
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path} 过小")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path} 过大")
    return errors


def _resolve_local_ref(root_schema: dict, reference: str) -> dict:
    if not reference.startswith("#/"):
        return {}
    current = root_schema
    for part in reference[2:].split("/"):
        current = current.get(part, {}) if isinstance(current, dict) else {}
    return current if isinstance(current, dict) else {}


def _matches_schema_type(expected: str, value) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True
