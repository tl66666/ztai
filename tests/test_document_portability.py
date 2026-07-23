from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.documents.conversion import convert_word_to_pdf
from backend.documents.resume_renderer import (
    build_resume_docx,
    build_resume_pdf,
    register_chinese_pdf_font,
)


class PortableDocumentTests(unittest.TestCase):
    def test_chinese_resume_renderers_do_not_depend_on_os_fonts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf_path = root / "resume.pdf"
            docx_path = root / "resume.docx"
            resume = {
                "title": "中文简历",
                "content": "项目经历\n使用 FastAPI 构建跨平台后端。",
            }

            build_resume_pdf(resume, pdf_path)
            build_resume_docx(resume, docx_path)

            self.assertEqual(register_chinese_pdf_font(), "STSong-Light")
            self.assertGreater(pdf_path.stat().st_size, 1000)
            self.assertGreater(docx_path.stat().st_size, 1000)

    def test_non_windows_conversion_does_not_import_windows_com(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("backend.documents.conversion.sys.platform", "linux"),
            patch(
                "backend.documents.conversion.shutil.which",
                return_value=None,
            ),
        ):
            root = Path(directory)
            source = root / "resume.docx"
            source.write_bytes(b"placeholder")

            converted = convert_word_to_pdf(source, root / "resume.pdf")

            self.assertFalse(converted)
