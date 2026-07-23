from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These ceilings must only move down while the compatibility application is retired.
MAX_LEGACY_ROUTE_DECORATORS = 55
MAX_LEGACY_ROUTE_OPERATIONS = 59


def _legacy_route_counts() -> tuple[int, int]:
    legacy_source = ROOT / "app.py"
    if not legacy_source.exists():
        return 0, 0

    tree = ast.parse(legacy_source.read_text(encoding="utf-8"))
    decorators = 0
    operations = 0
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if (
                not isinstance(decorator, ast.Call)
                or not isinstance(decorator.func, ast.Attribute)
                or decorator.func.attr != "route"
            ):
                continue
            decorators += 1
            methods = next(
                (
                    keyword.value
                    for keyword in decorator.keywords
                    if keyword.arg == "methods"
                ),
                None,
            )
            if isinstance(methods, (ast.List, ast.Tuple)):
                operations += len(methods.elts)
            else:
                operations += 1
    return decorators, operations


class ArchitectureMigrationTests(unittest.TestCase):
    def test_legacy_route_surface_cannot_grow(self) -> None:
        decorators, operations = _legacy_route_counts()

        self.assertLessEqual(decorators, MAX_LEGACY_ROUTE_DECORATORS)
        self.assertLessEqual(operations, MAX_LEGACY_ROUTE_OPERATIONS)

    def test_container_delivery_layer_stays_out_of_current_architecture(self) -> None:
        retired_paths = (
            "Dockerfile",
            ".dockerignore",
            "compose.yaml",
            "deploy/backend.env.example",
        )

        self.assertFalse([path for path in retired_paths if (ROOT / path).exists()])

    def test_asgi_runtime_has_no_wsgi_or_app_module_dependency(self) -> None:
        backend_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (ROOT / "backend").rglob("*.py")
        )

        self.assertNotIn("a2wsgi", backend_sources)
        self.assertNotIn("WSGIMiddleware", backend_sources)
        self.assertNotIn("legacy_flask", backend_sources)
        self.assertNotIn("legacy_training", backend_sources)
        self.assertNotIn("import app", backend_sources)
        self.assertFalse(
            (ROOT / "backend" / "adapters" / "legacy_flask.py").exists()
        )
        self.assertFalse(
            (ROOT / "backend" / "adapters" / "legacy_training.py").exists()
        )


if __name__ == "__main__":
    unittest.main()
