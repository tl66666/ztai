"""JobHunter ASGI application package."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_application(*args: Any, **kwargs: Any) -> "FastAPI":
    """Load the application factory without making backend package imports stateful."""

    from backend.main import create_application as factory

    return factory(*args, **kwargs)


__all__ = ["create_application"]
