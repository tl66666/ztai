from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ContextualAgentFrontendTests(unittest.TestCase):
    def test_global_agent_shell_is_outside_page_sections_and_accessible(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        launcher = html.index('id="agentLauncher"')
        drawer = html.index('id="agentDrawer"')
        main_close = html.index("</main>")
        self.assertGreater(launcher, main_close)
        self.assertGreater(drawer, main_close)
        self.assertIn('aria-controls="agentDrawer"', html)
        self.assertIn('aria-expanded="false"', html)
        self.assertIn('role="dialog"', html)
        self.assertIn('aria-modal="true"', html)
        self.assertIn('id="closeAgentDrawer"', html)
        self.assertIn('id="agentDrawerBackdrop"', html)

    def test_context_and_proposal_contracts_are_present(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="agentContextChips"', html)
        self.assertIn('id="agentActiveActions"', html)
        self.assertIn('id="agentCommandOpportunities"', html)
        self.assertIn('id="openAgentWorkspace"', html)

    def test_profile_result_uses_a_dedicated_entity_summary_not_the_preset_select(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")
        result_flow = script[
            script.index("async function focusAgentResultFromQuery"):
            script.index("async function refreshAfterAgentAction")
        ]

        self.assertIn('id="agentResultFocus"', html)
        self.assertIn("ContextualAgent.profileResultHtml(lookup.entity)", result_flow)
        self.assertNotIn('$("careerProfileSelect")', result_flow)

    def test_context_chip_remove_control_meets_touch_target(self):
        css = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertRegex(
            css,
            r"\.agent-context-chip button\s*\{[^}]*width:\s*44px;[^}]*height:\s*44px;",
        )
        self.assertRegex(css, r"\.agent-context-chip\s*\{[^}]*min-height:\s*44px;")

    def test_contextual_agent_behavior_harness(self):
        completed = subprocess.run(
            ["node", str(ROOT / "tests" / "contextual_agent_ui.test.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)


if __name__ == "__main__":
    unittest.main()
