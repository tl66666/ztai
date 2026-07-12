from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = ROOT / "static" / "showcase.html"
ASSET_AUDIT = ROOT / "docs" / "SHOWCASE_ASSETS.md"


class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, str, str]] = []
        self.videos: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name: value or "" for name, value in attrs}
        for attribute in ("href", "src", "poster"):
            if values.get(attribute):
                self.references.append((tag, attribute, values[attribute]))
        if tag == "video":
            self.videos.append(values)


class ShowcaseContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = SHOWCASE.read_text(encoding="utf-8")
        cls.parser = _ReferenceParser()
        cls.parser.feed(cls.html)

    def test_first_view_names_product_and_contextual_agent(self):
        hero = self.html.split("</header>", 1)[0]
        self.assertRegex(hero, r"JobHunter|职途\s*AI")
        self.assertIn("上下文求职 Agent", hero)
        self.assertIn("agent-workbench.webp", hero)

    def test_showcase_explains_real_workflow_and_agent_boundary(self):
        for phrase in (
            "职业目标",
            "简历",
            "JD",
            "面试",
            "投递看板",
            "复盘",
            "提议",
            "确认",
            "不会自动投递",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_agent_writes_use_one_confirmation_without_invented_delete_capability(self):
        self.assertIn("所有 Agent 写入", self.html)
        self.assertIn("提议 → 预览 → 单次确认", self.html)
        self.assertIn("risk_level", self.html)
        self.assertNotIn("更强确认", self.html)
        self.assertNotRegex(self.html, r"Agent[^。]{0,40}删除|删除[^。]{0,40}Agent")

    def test_showcase_explains_agent_architecture_tools_and_memory(self):
        for phrase in (
            "领域服务",
            "Agent Runtime",
            "工具",
            "工作记忆",
            "语义记忆",
            "情景记忆",
            "任务记忆",
            "审计",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_local_mode_privacy_startup_and_browser_support_are_explicit(self):
        for phrase in (
            "无需 API Key",
            "本地规则模式",
            "本地单用户",
            "SQLite",
            "start.bat",
            "Microsoft Edge",
            "Google Chrome",
            "Mozilla Firefox",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_static_page_has_no_server_only_or_absolute_local_references(self):
        lowered = self.html.lower()
        self.assertNotIn("localhost", lowered)
        self.assertNotIn("127.0.0.1", lowered)
        self.assertNotRegex(lowered, r"(?:href|src|poster)=[\"']/api/")
        self.assertNotRegex(lowered, r"(?:href|src|poster)=[\"']/assets/")

    def test_all_local_references_are_relative_and_exist(self):
        for tag, attribute, reference in self.parser.references:
            parsed = urlsplit(reference)
            if parsed.scheme in {"http", "https", "mailto"} or reference.startswith("#"):
                continue
            with self.subTest(reference=reference):
                self.assertFalse(reference.startswith("/"), f"{reference} is server-root relative")
                target = (SHOWCASE.parent / parsed.path).resolve()
                self.assertTrue(target.is_relative_to(ROOT.resolve()))
                self.assertTrue(target.exists(), f"missing {tag}[{attribute}] target: {reference}")

    def test_product_screenshots_are_tracked_static_assets_with_alt_text(self):
        screenshot_refs = [
            reference
            for tag, attribute, reference in self.parser.references
            if tag == "img" and attribute == "src" and "assets/showcase/" in reference
        ]
        self.assertGreaterEqual(len(screenshot_refs), 4)
        self.assertIn("assets/showcase/agent-workbench.webp", screenshot_refs)
        for reference in screenshot_refs:
            with self.subTest(reference=reference):
                self.assertNotIn("output/", reference)
                self.assertTrue(reference.endswith(".webp"), "showcase screenshots must use optimized WebP")
                self.assertRegex(self.html, rf'<img[^>]+src=["\']{re.escape(reference)}["\'][^>]+alt=["\'][^"\']+["\']')

    def test_static_pages_boundary_and_current_verification_are_visible(self):
        for phrase in (
            "GitHub Pages",
            "静态项目展示",
            "不能在此直接使用 Agent",
            "Python 276/276",
            "本机缺少 Firefox",
            "PASS",
            "SKIP",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_showcase_assets_are_optimized_audited_and_small(self):
        self.assertFalse((ROOT / "static" / "assets" / "images" / "success (2).mp4").exists())
        favicon = ROOT / "static" / "assets" / "showcase" / "favicon.png"
        self.assertTrue(favicon.exists())
        self.assertLessEqual(favicon.stat().st_size, 10_000)
        self.assertIn('href="assets/showcase/favicon.png"', self.html)
        self.assertTrue(ASSET_AUDIT.exists())
        audit = ASSET_AUDIT.read_text(encoding="utf-8")
        for phrase in ("SHA-256", "Before", "After", "新增", "迁移", "删除", "success (2).mp4"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, audit)

    def test_video_elements_have_local_posters(self):
        for video in self.parser.videos:
            with self.subTest(video=video.get("src", "video")):
                self.assertTrue(video.get("poster"), "video must have a poster")
                self.assertFalse(video["poster"].startswith("/"))

    def test_accessibility_and_motion_fallback_are_present(self):
        self.assertIn(":focus-visible", self.html)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.html)
        self.assertRegex(self.html, r"overflow-x:\s*(?:clip|hidden)")
        self.assertRegex(self.html, r"img\s*\{[^}]*height:\s*auto", "screenshots must retain their natural aspect ratio")
        self.assertIn("@media (max-width: 640px)", self.html)


if __name__ == "__main__":
    unittest.main()
