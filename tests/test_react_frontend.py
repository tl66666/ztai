import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReactFrontendArchitectureContracts(unittest.TestCase):
    def test_react_composition_root_is_loaded_as_a_local_es_module(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        main = (
            ROOT / "frontend" / "src" / "app" / "main.tsx"
        ).read_text(encoding="utf-8")

        self.assertIn('<div id="reactAppRoot"></div>', html)
        self.assertIn(
            '<script type="module" src="js/react_app.js"></script>',
            html,
        )
        self.assertIn('createRoot(rootNode)', main)
        self.assertIn("<StrictMode>", main)
        self.assertNotIn("unpkg.com", html)
        self.assertNotIn("cdn.jsdelivr.net", html)

    def test_visible_sidebar_is_owned_by_react_and_preserves_product_semantics(self):
        sidebar = (
            ROOT / "frontend" / "src" / "shell" / "sidebar.tsx"
        ).read_text(encoding="utf-8")
        navigation = (
            ROOT / "frontend" / "src" / "shell" / "navigation-model.ts"
        ).read_text(encoding="utf-8")

        self.assertIn('className="sidebar"', sidebar)
        self.assertIn('aria-label="主导航"', sidebar)
        self.assertIn('aria-current={activePage === page ? "page" : undefined}', sidebar)
        for label in ("项目总览", "简历实验室", "面试训练场", "投递看板", "求职指挥台"):
            self.assertIn(f'label: "{label}"', navigation)

    def test_react_runtime_and_strict_types_are_declared_locally(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        tsconfig = json.loads((ROOT / "tsconfig.json").read_text(encoding="utf-8"))
        vite = (ROOT / "vite.config.ts").read_text(encoding="utf-8")

        self.assertIn("react", package["dependencies"])
        self.assertIn("react-dom", package["dependencies"])
        self.assertIn("lucide-react", package["dependencies"])
        self.assertTrue(tsconfig["compilerOptions"]["strict"])
        self.assertEqual(tsconfig["compilerOptions"]["jsx"], "react-jsx")
        self.assertIn('entry: "frontend/src/app/main.tsx"', vite)
        self.assertIn('formats: ["es"]', vite)

    def test_feature_factories_are_direct_es_module_imports(self):
        app = (
            ROOT / "frontend" / "src" / "app" / "runtime.ts"
        ).read_text(encoding="utf-8")

        for factory in (
            'import { createResumeController } from "../resume/resume-controller"',
            'import { createInterviewController } from "../interview/interview-controller"',
            'import { createOpportunityController } from "../opportunity/opportunity-controller"',
        ):
            self.assertIn(factory, app)
        self.assertNotIn("JobHunterResumeController", app)
        self.assertNotIn("JobHunterInterviewController", app)
        self.assertNotIn("JobHunterOpportunityController", app)


if __name__ == "__main__":
    unittest.main()
