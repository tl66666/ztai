from __future__ import annotations

import re
import uuid
from pathlib import Path

_SAFE_NAMESPACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_-]{0,199}$")


def owner_id(value: int) -> int:
    normalized = int(value)
    if normalized <= 0:
        raise ValueError("owner_id must be positive")
    return normalized


def object_key(*, owner: int, namespace: str, original_name: str) -> str:
    normalized_namespace = str(namespace).strip().strip("/")
    if (
        not _SAFE_NAMESPACE.fullmatch(normalized_namespace)
        or ".." in normalized_namespace.split("/")
        or "//" in normalized_namespace
    ):
        raise ValueError("invalid blob namespace")
    suffix = Path(original_name).suffix.lower()
    safe_suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,10}", suffix) else ""
    return (
        f"owners/{owner}/{normalized_namespace}/"
        f"{uuid.uuid4().hex}{safe_suffix}"
    )
