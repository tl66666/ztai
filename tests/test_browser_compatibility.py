from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BrowserCompatibilityFrontendContracts(unittest.TestCase):
    def test_visible_career_profile_editor_is_wired_to_profile_api(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

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
        self.assertIn('api("/profile")', app)
        self.assertIn('method: "PUT"', app)
        self.assertIn("saveCareerGoal", app)

    def test_audio_preview_has_accessible_error_and_download_fallbacks(self):
        html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "static" / "js" / "app.js").read_text(encoding="utf-8")

        for control_id in (
            "audioPlaybackStatus",
            "audioDownloadLink",
            "roomAudioPlaybackStatus",
            "roomAudioDownloadLink",
        ):
            self.assertIn(f'id="{control_id}"', html)
        self.assertIn("audioPlaybackErrorMessage", app)
        self.assertIn("audioFileDescriptor", app)

    def test_fixed_agent_launcher_has_reserved_space_and_tabs_do_not_overlay_content(self):
        css = (ROOT / "static" / "css" / "style.css").read_text(encoding="utf-8")

        self.assertIn("--agent-launcher-rail", css)
        self.assertIn("var(--agent-launcher-rail)", css)
        self.assertIn(".page-subnav {\n  position: relative;", css)
        self.assertRegex(css, r"@media \(max-width: 1120px\)[\s\S]+\.agent-launcher \{ top:")
        self.assertRegex(css, r"\.sidebar \{[\s\S]+padding-right:")


if __name__ == "__main__":
    unittest.main()
