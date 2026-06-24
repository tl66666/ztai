import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class ProviderRegistryTests(unittest.TestCase):
    def test_provider_catalog_includes_glm_deepseek_and_kimi(self):
        from utils.ai_client import AIProviderRegistry

        providers = AIProviderRegistry().list_public()
        provider_ids = {item["id"] for item in providers}

        self.assertIn("glm", provider_ids)
        self.assertIn("deepseek", provider_ids)
        self.assertIn("kimi", provider_ids)
        self.assertTrue(all("model" in item for item in providers))

    def test_client_can_switch_provider_without_losing_catalog(self):
        from utils.ai_client import AIProviderRegistry, MultiModelAIClient

        registry = AIProviderRegistry()
        client = MultiModelAIClient(registry=registry)

        client.configure(provider_id="deepseek", api_key="sk-test")

        self.assertEqual(client.provider.id, "deepseek")
        self.assertEqual(len(client.available_providers()), 3)


class BackendFeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["JOBHUNTER_DB_PATH"] = os.path.join(self.temp_dir.name, "test.db")

        import importlib
        import app as app_module

        self.app_module = importlib.reload(app_module)
        self.app_module.app.config["TESTING"] = True
        self.app_module.init_db()
        self.client = self.app_module.app.test_client()

        response = self.client.post(
            "/api/resumes",
            json={
                "user_id": 1,
                "title": "测试工程师简历",
                "content": "唐乐，软件测试专业。熟悉 Python、Selenium、JMeter、接口测试，做过求职辅助 Web 系统。",
            },
        )
        self.resume_id = response.get_json()["resume_id"]

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("JOBHUNTER_DB_PATH", None)

    def test_tailor_resume_for_jd_returns_structured_sections(self):
        response = self.client.post(
            f"/api/resumes/{self.resume_id}/tailor",
            json={
                "job_title": "AI 应用测试工程师",
                "jd": "负责 AI Web 系统测试、自动化测试、接口测试、性能测试，要求熟悉 Selenium、Pytest、JMeter。",
            },
        )

        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("tailored_resume", data)
        self.assertIn("keyword_gaps", data)
        self.assertIn("AI 应用测试工程师", data["positioning"])

    def test_interview_session_follows_real_process(self):
        start = self.client.post(
            "/api/interview/sessions",
            json={
                "user_id": 1,
                "resume_id": self.resume_id,
                "job_title": "软件测试工程师",
                "jd": "负责 Web 功能测试、接口测试和自动化测试。",
                "mode": "campus",
            },
        ).get_json()

        self.assertTrue(start["success"])
        self.assertEqual(start["stage"], "opening")
        self.assertIn("自我介绍", start["question"])

        answer = self.client.post(
            f"/api/interview/sessions/{start['session_id']}/answer",
            json={"answer": "面试官你好，我是唐乐，做过 Flask 求职辅助系统测试，使用过 Selenium 和 JMeter。"},
        ).get_json()

        self.assertTrue(answer["success"])
        self.assertIn(answer["stage"], {"resume_deep_dive", "technical", "behavioral", "candidate_questions", "finished"})
        self.assertIn("feedback", answer)

    def test_dashboard_returns_career_pulse(self):
        response = self.client.get("/api/dashboard/1")
        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("career_pulse", data)
        self.assertIn("score", data["career_pulse"])
        self.assertIn("weekly_plan", data["career_pulse"])

    def test_career_profiles_include_non_tech_directions(self):
        response = self.client.get("/api/career/profiles")
        data = response.get_json()

        self.assertTrue(data["success"])
        profile_ids = {item["id"] for item in data["profiles"]}
        self.assertIn("finance", profile_ids)
        self.assertIn("education", profile_ids)
        self.assertIn("ops", profile_ids)

    def test_finance_skill_radar_uses_finance_ability_model(self):
        response = self.client.post(
            "/api/skills/radar",
            json={
                "career_profile": "finance",
                "resume_content": "熟悉会计凭证、Excel 透视表、发票整理、财务报表和税务申报。",
            },
        )
        data = response.get_json()

        self.assertTrue(data["success"])
        self.assertEqual(data["profile"]["id"], "finance")
        categories = {item["category"] for item in data["radar_data"]}
        self.assertIn("会计基础", categories)
        self.assertIn("税务合规", categories)

    def test_non_tech_question_bank_and_professional_pack(self):
        questions = self.client.get("/api/questions?category=ops").get_json()
        self.assertTrue(questions["success"])
        self.assertGreaterEqual(len(questions["data"]), 5)

        pack = self.client.post(
            "/api/interview/professional-pack",
            json={"category": "career", "career_profile": "education", "job_title": "小学语文教师"},
        ).get_json()

        self.assertTrue(pack["success"])
        self.assertEqual(pack["profile"]["id"], "education")
        self.assertGreaterEqual(len(pack["questions"]), 5)


if __name__ == "__main__":
    unittest.main()
