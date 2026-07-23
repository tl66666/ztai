import importlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from utils.domain.database import connect


ROOT = Path(__file__).resolve().parents[1]


class OpportunityFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        sources = [
            ROOT / "static" / "js" / "app.js",
            ROOT / "frontend" / "src" / "opportunity" / "opportunity-controller.ts",
            ROOT / "frontend" / "src" / "opportunity" / "application-board.ts",
            ROOT / "frontend" / "src" / "opportunity" / "opportunity-dashboard.ts",
            ROOT / "frontend" / "src" / "opportunity" / "opportunity-workspace.ts",
            ROOT / "frontend" / "src" / "opportunity" / "opportunity-workspace-renderer.ts",
            ROOT / "frontend" / "src" / "shell" / "shell-controller.ts",
        ]
        cls.script = "\n".join(path.read_text(encoding="utf-8") for path in sources)
        cls.interview_controller = (
            ROOT
            / "frontend"
            / "src"
            / "interview"
            / "interview-controller.ts"
        ).read_text(encoding="utf-8")

    def test_kanban_uses_api_statuses_and_keeps_legacy_records_visible(self):
        self.assertIn("data.canonical_statuses", self.script)
        self.assertIn("needs_status_review", self.script)
        self.assertIn('stage: "待确认"', self.script)
        self.assertIn('data-lucide="triangle-alert"', self.script)
        self.assertNotIn(
            'const stages = ["已投递", "简历筛选", "笔试", "一面", "二面", "HR 面", "Offer", "已拒绝"]',
            self.script,
        )

    def test_workspace_has_stable_accessible_tabs_and_panels(self):
        self.assertIn('id="opportunityWorkspace"', self.html)
        self.assertIn('role="tablist"', self.html)
        for tab_id, panel_id, label in (
            ("overview", "opportunity-overview", "概览"),
            ("match", "opportunity-match", "JD 与匹配"),
            ("resume", "opportunity-resume", "简历版本"),
            ("interview", "opportunity-interview", "面试准备"),
            ("timeline", "opportunity-timeline", "时间线"),
        ):
            self.assertIn(f'id="opportunity-tab-{tab_id}"', self.html)
            self.assertIn(f'aria-controls="{panel_id}"', self.html)
            self.assertIn(f'id="{panel_id}"', self.html)
            self.assertIn(label, self.html)
        self.assertIn('aria-selected="true"', self.html)
        self.assertIn('role="tabpanel"', self.html)
        self.assertIn("event.key === \"ArrowRight\"", self.script)

    def test_entity_ids_drive_deep_links_and_cross_feature_handoffs(self):
        self.assertIn("currentOpportunityId", self.script)
        self.assertIn("return history.open", self.script)
        self.assertIn("applicationPayloadForJob(state.pendingApplicationHandoff", self.script)
        self.assertIn("buildInterviewStartPayload({", self.interview_controller)
        self.assertIn("}, handoff)", self.interview_controller)
        self.assertIn("buildMatchPayload", self.script)
        self.assertIn("actionId", self.script)

    def test_opportunity_interview_handoff_is_cleared_after_successful_start(self):
        start = re.search(
            r"async function start\(\).*?function renderFeedbackHtml",
            self.interview_controller,
            re.DOTALL,
        ).group(0)
        self.assertIn("state.interviewOpportunityHandoff = null", start)
        self.assertGreater(
            start.index("state.interviewOpportunityHandoff = null"),
            start.index("if (!data.success)"),
        )

    def test_back_forward_history_restores_workspace_behaviorally(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "js" / "test_opportunity_history.js")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_entity_handoffs_are_immutable_and_one_shot_behaviorally(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "js" / "test_opportunity_handoffs.js")],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_opportunity_loads_are_latest_request_wins_behaviorally(self):
        result = subprocess.run(
            ["node", str(ROOT / "tests" / "js" / "test_opportunity_load_generation.js")],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_quality_handoffs_errors_and_focus_are_wired(self):
        self.assertIn('id="applicationHandoffNotice"', self.html)
        self.assertIn('id="clearApplicationHandoff"', self.html)
        self.assertIn('id="applicationBoardHeading"', self.html)
        self.assertIn('id="matchOpportunityNotice"', self.html)
        self.assertIn('id="clearMatchOpportunityLink"', self.html)
        self.assertIn('<script src="js/opportunity_handoffs.js"></script>', self.html)
        for token in (
            "interviewOpportunityHandoff", "pendingApplicationHandoff", "matchOpportunityId",
            "buildInterviewStartPayload", "applicationPayloadForJob", "buildMatchPayload",
            "retryOpportunityWorkspace", "opportunityWorkspaceError", "opportunityOpener",
            "focus({ preventScroll: true })", "navigateToRoute", "onRouteTransition",
            "routeLeavesFlow", "opportunityLoadGeneration", "requestState.isCurrent",
            "focusCleanedRoute", "focusRoute:", "tabIndex = -1",
        ):
            self.assertIn(token, self.script)
        self.assertNotIn("application_id: state.currentOpportunityId", self.script)

    def test_app_uses_the_history_controller_as_its_single_route_sync(self):
        history_script = '<script src="js/opportunity_history.js"></script>'
        app_script = '<script src="js/app.js"></script>'
        self.assertIn(history_script, self.html)
        self.assertLess(self.html.index(history_script), self.html.index(app_script))
        self.assertIn("OpportunityHistory.createOpportunityHistoryController", self.script)
        self.assertIn("opportunityHistory.bind()", self.script)
        self.assertIn("await history().sync()", self.script)
        self.assertIn("return history.open", self.script)
        self.assertIn("history.close", self.script)
        self.assertNotIn('params.get("opportunity")', self.script)
        self.assertNotIn("function opportunityWorkspaceUrl", self.script)

    def test_cards_have_a_visible_icon_and_text_workspace_command(self):
        self.assertIn('data-lucide="panel-right-open"', self.script)
        self.assertIn("打开详情", self.script)
        self.assertIn("openOpportunityWorkspace", self.script)

    def test_main_app_assets_are_document_absolute(self):
        self.assertNotIn('src="assets/images/', self.html)
        self.assertNotIn('`assets/images/', self.script)
        self.assertIn('src="/assets/images/', self.html)
        self.assertIn('`/assets/images/', self.script)
        self.assertNotIn('/css/assets/images/', self.html + self.script)

    def test_workspace_renders_raw_api_fields_through_escape_helpers(self):
        self.assertIn("renderOpportunityOverview", self.script)
        self.assertIn("escapeHtml(opportunity.company", self.script)
        self.assertIn("escapeHtml(opportunity.job_title", self.script)
        self.assertIn("escapeHtml(workspace.opportunity.jd_text", self.script)
        self.assertIn("escapeHtml(event.event_type", self.script)
        self.assertIn("opportunityWorkspaceError", self.html)
        self.assertIn("opportunity-empty", self.script)


class OpportunityWorkspaceApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "workspace.db")
        os.environ["JOBHUNTER_DB_PATH"] = self.db_path
        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.app_module.app.config["TESTING"] = True
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

    def tearDown(self):
        os.environ.pop("JOBHUNTER_DB_PATH", None)
        self.temp_dir.cleanup()

    def _seed_workspace(self):
        with connect(self.db_path) as conn:
            resume_id = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (1, 'Backend v3', 'PRIVATE RESUME BODY')"
            ).lastrowid
        opportunity = self.client.post(
            "/api/opportunities",
            json={
                "company": "Acme <script>",
                "job_title": "Backend Engineer",
                "status": "一面",
                "city": "杭州",
                "priority": 2,
                "next_action_at": "2026-07-20 10:00:00",
                "interview_at": "2026-07-22 14:00:00",
                "jd_text": "LOCAL STORED JD",
                "contact_info": "private@example.com",
                "resume_id": resume_id,
            },
        ).get_json()["data"]
        opportunity_id = opportunity["id"]
        with connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO job_matches
                   (user_id, resume_id, job_title, match_score, analysis, jd_text, details_json, application_id)
                   VALUES (1, ?, 'Backend Engineer', 86, 'good match', 'LOCAL STORED JD', ?, ?)""",
                (resume_id, json.dumps({"strengths": ["Python"]}), opportunity_id),
            )
            conn.execute(
                """INSERT INTO interview_sessions
                   (user_id, application_id, resume_id, job_title, status, current_stage, conversation_json, score)
                   VALUES (1, ?, ?, 'Backend Engineer', 'active', 'technical', 'PRIVATE CONVERSATION', NULL)""",
                (opportunity_id, resume_id),
            )
            conn.execute(
                """INSERT INTO action_items
                   (user_id, application_id, title, description, status, priority, due_at)
                   VALUES (1, ?, 'Prepare system design', 'Review tradeoffs', 'pending', 2, '2026-07-21')""",
                (opportunity_id,),
            )
            foreign_resume = conn.execute(
                "INSERT INTO resumes (user_id, title, content) VALUES (2, 'FOREIGN RESUME', 'FOREIGN BODY')"
            ).lastrowid
            conn.execute(
                """INSERT INTO job_matches
                   (user_id, resume_id, job_title, match_score, analysis, application_id)
                   VALUES (2, ?, 'FOREIGN MATCH', 99, 'FOREIGN ANALYSIS', ?)""",
                (foreign_resume, opportunity_id),
            )
            conn.execute(
                """INSERT INTO interview_sessions
                   (user_id, application_id, resume_id, job_title, status, conversation_json)
                   VALUES (2, ?, ?, 'FOREIGN INTERVIEW', 'completed', 'FOREIGN CONVERSATION')""",
                (opportunity_id, foreign_resume),
            )
        return opportunity_id, resume_id

    def test_workspace_returns_safe_owned_associated_data(self):
        opportunity_id, resume_id = self._seed_workspace()

        response = self.client.get(f"/api/opportunities/{opportunity_id}/workspace")
        payload = response.get_json()
        serialized = json.dumps(payload, ensure_ascii=False)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["success"])
        self.assertEqual(payload["opportunity"]["id"], opportunity_id)
        self.assertEqual(payload["opportunity"]["jd_text"], "LOCAL STORED JD")
        self.assertNotIn("contact_info", payload["opportunity"])
        self.assertEqual(payload["resume"]["id"], resume_id)
        self.assertNotIn("content", payload["resume"])
        self.assertEqual(payload["matches"][0]["match_score"], 86)
        self.assertEqual(payload["matches"][0]["details"], {"strengths": ["Python"]})
        self.assertNotIn("jd_text", payload["matches"][0])
        self.assertEqual(payload["interviews"][0]["status"], "active")
        self.assertNotIn("conversation_json", payload["interviews"][0])
        self.assertEqual(payload["actions"][0]["title"], "Prepare system design")
        self.assertEqual(
            payload["timeline"],
            sorted(payload["timeline"], key=lambda item: (item["occurred_at"], item["id"])),
        )
        for secret in (
            "private@example.com",
            "PRIVATE RESUME BODY",
            "PRIVATE CONVERSATION",
            "FOREIGN RESUME",
            "FOREIGN MATCH",
            "FOREIGN INTERVIEW",
            "FOREIGN CONVERSATION",
        ):
            self.assertNotIn(secret, serialized)

    def test_workspace_rejects_cross_user_and_deleted_opportunities(self):
        with connect(self.db_path) as conn:
            foreign_id = conn.execute(
                "INSERT INTO job_applications (user_id, company, job_title) VALUES (2, 'Private', 'Role')"
            ).lastrowid
        local_id = self.client.post(
            "/api/opportunities", json={"company": "Deleted", "job_title": "Role"}
        ).get_json()["data"]["id"]
        self.client.delete(f"/api/applications/{local_id}")

        foreign = self.client.get(f"/api/opportunities/{foreign_id}/workspace")
        deleted = self.client.get(f"/api/opportunities/{local_id}/workspace")

        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(deleted.status_code, 404)
        self.assertTrue(foreign.is_json)
        self.assertTrue(deleted.is_json)
        self.assertFalse(foreign.get_json()["success"])
        self.assertFalse(deleted.get_json()["success"])

    def test_linked_match_appears_after_workspace_refresh(self):
        opportunity_id, resume_id = self._seed_workspace()
        response = self.client.post(
            "/api/job-match",
            json={
                "resume_id": resume_id,
                "job_title": "Backend Engineer",
                "jd": "Python Flask SQL API testing requirements " * 4,
                "application_id": opportunity_id,
            },
        )
        workspace = self.client.get(f"/api/opportunities/{opportunity_id}/workspace").get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])
        self.assertEqual(len(workspace["matches"]), 2)


if __name__ == "__main__":
    unittest.main()
