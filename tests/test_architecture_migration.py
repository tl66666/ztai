from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAX_LEGACY_ROUTE_DECORATORS = 0
MAX_LEGACY_ROUTE_OPERATIONS = 0


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
    def test_flask_route_surface_is_removed(self) -> None:
        decorators, operations = _legacy_route_counts()

        self.assertEqual(decorators, MAX_LEGACY_ROUTE_DECORATORS)
        self.assertEqual(operations, MAX_LEGACY_ROUTE_OPERATIONS)
        self.assertFalse((ROOT / "app.py").exists())

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
        self.assertNotIn("from app", backend_sources)
        self.assertFalse(
            (ROOT / "backend" / "adapters" / "legacy_flask.py").exists()
        )
        self.assertFalse(
            (ROOT / "backend" / "adapters" / "legacy_training.py").exists()
        )

    def test_application_modules_do_not_own_sql(self) -> None:
        application_root = ROOT / "backend" / "application"
        violations = []
        sql_statement = re.compile(
            r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA)\b",
            re.IGNORECASE,
        )
        for path in application_root.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if sql_statement.match(node.value):
                        violations.append(f"{path.name}:{node.lineno}:SQL")
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    modules = (
                        [alias.name for alias in node.names]
                        if isinstance(node, ast.Import)
                        else [node.module or ""]
                    )
                    if any(
                        module == "sqlite3"
                        or module == "utils.domain.database"
                        for module in modules
                    ):
                        violations.append(f"{path.name}:{node.lineno}:database-import")

        self.assertEqual(violations, [])

    def test_runtime_does_not_invoke_the_offline_sqlite_migrator(self) -> None:
        runtime_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                ROOT / "backend" / "core" / "runtime.py",
                ROOT / "backend" / "application" / "container.py",
                ROOT / "utils" / "agent_runtime" / "actions.py",
            )
        )

        self.assertNotIn("migrate_database(", runtime_sources)
        self.assertNotIn("create_agent_tables(", runtime_sources)

    def test_production_domain_persistence_has_no_sqlite_specifics(self) -> None:
        sql_statement = re.compile(
            r"^\s*(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA)\b",
            re.IGNORECASE,
        )
        production_paths = (
            ROOT / "utils" / "domain" / "career.py",
            ROOT / "utils" / "domain" / "events.py",
            ROOT / "utils" / "domain" / "interviews.py",
            ROOT / "backend" / "api" / "career.py",
            *sorted((ROOT / "backend" / "adapters" / "persistence" / "sqlalchemy").glob("*.py")),
            *sorted((ROOT / "utils" / "agent_runtime").glob("*.py")),
        )
        sqlite_tokens = (
            "PRAGMA",
            "BEGIN IMMEDIATE",
            "datetime(",
            "fts5",
        )
        violations = []
        for path in production_paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any(alias.name == "sqlite3" for alias in node.names):
                        violations.append(f"{path.relative_to(ROOT)}:{node.lineno}:sqlite3")
                elif isinstance(node, ast.ImportFrom):
                    if node.module == "utils.domain.database" and any(
                        alias.name in {"connect", "ensure_column", "migrate_database"}
                        for alias in node.names
                    ):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}:legacy-database"
                        )
                    if node.module == "sqlalchemy.dialects.sqlite" or (
                        node.module == "sqlalchemy.dialects"
                        and any(alias.name == "sqlite" for alias in node.names)
                    ):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}:sqlite-dialect"
                        )
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    normalized = node.value.casefold()
                    for token in sqlite_tokens:
                        if token.casefold() in normalized:
                            violations.append(
                                f"{path.relative_to(ROOT)}:{node.lineno}:{token}"
                            )
                    if "?" in node.value and sql_statement.match(node.value):
                        violations.append(
                            f"{path.relative_to(ROOT)}:{node.lineno}:qmark-SQL"
                        )

        self.assertEqual(violations, [])

    def test_career_constructor_has_no_schema_guards(self) -> None:
        source = (ROOT / "utils" / "domain" / "career.py").read_text(
            encoding="utf-8"
        )
        tree = ast.parse(source)
        career_class = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "CareerService"
        )
        constructor = next(
            node
            for node in career_class.body
            if isinstance(node, ast.FunctionDef) and node.name == "__init__"
        )
        guards = []
        for node in ast.walk(constructor):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "ensure_column"
                and len(node.args) >= 3
                and all(
                    isinstance(argument, ast.Constant)
                    for argument in node.args[1:3]
                )
            ):
                guards.append((node.args[1].value, node.args[2].value))

        self.assertEqual(guards, [])


if __name__ == "__main__":
    unittest.main()
