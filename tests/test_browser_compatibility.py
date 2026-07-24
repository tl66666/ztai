import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BrowserCompatibilityFrontendContracts(unittest.TestCase):
    def test_visible_career_profile_editor_is_wired_to_profile_api(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        topbar = (
            ROOT / "frontend" / "src" / "shell" / "topbar-controller.ts"
        ).read_text(encoding="utf-8")

        for control_id in (
            "careerGoalForm",
            "careerGoalRole",
            "careerGoalCities",
            "careerGoalSalaryMin",
            "careerGoalSalaryMax",
            "careerGoalSkills",
            "saveCareerGoalBtn",
            "careerGoalStatus",
        ):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn('request("/profile"', topbar)
        self.assertIn('method: "PUT"', topbar)
        self.assertIn("saveCareerGoal", topbar)

    def test_audio_preview_has_accessible_error_and_download_fallbacks(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        controller = (
            ROOT / "frontend" / "src" / "interview" / "interview-audio.ts"
        ).read_text(encoding="utf-8")

        for control_id in (
            "audioPlaybackStatus",
            "audioDownloadLink",
            "roomAudioPlaybackStatus",
            "roomAudioDownloadLink",
        ):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn("audioPlaybackErrorMessage", controller)
        self.assertIn("audioFileDescriptor", controller)

    def test_fixed_agent_launcher_has_reserved_space_and_tabs_do_not_overlay_content(self):
        css = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("--agent-launcher-rail", css)
        self.assertIn("var(--agent-launcher-rail)", css)
        self.assertIn(".page-subnav {\n  position: relative;", css)
        self.assertRegex(css, r"@media \(max-width: 1120px\)[\s\S]+\.agent-launcher \{ top:")
        self.assertRegex(css, r"\.sidebar \{[\s\S]+padding-right:")

    def test_career_profile_errors_have_visible_retry_contract(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        topbar = (
            ROOT / "frontend" / "src" / "shell" / "topbar-controller.ts"
        ).read_text(encoding="utf-8")
        career_form = (
            ROOT / "frontend" / "src" / "career" / "career-form.mjs"
        ).read_text(encoding="utf-8")

        self.assertRegex(
            html,
            r'id="careerGoalStatus"[^>]+role="status"[^>]+aria-live="polite"',
        )
        self.assertIn('id="retryCareerGoalBtn"', html)
        self.assertIn("careerForm.loadProfile", topbar)
        self.assertIn("careerForm.saveProfile", topbar)
        self.assertIn('byId("retryCareerGoalBtn")?.addEventListener("click"', topbar)
        self.assertIn("加载失败，请重试", career_form)
        self.assertIn("保存失败，请重试", career_form)


if __name__ == "__main__":
    unittest.main()
