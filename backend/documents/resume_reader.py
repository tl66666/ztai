from __future__ import annotations

from pathlib import Path

ALLOWED_RESUME_EXTENSIONS = frozenset(
    {"pdf", "doc", "docx", "txt", "png", "jpg", "jpeg"}
)


def parse_resume_file(file_path: str | Path, file_type: str) -> str:
    """Extract portable text while preserving the legacy upload contract."""

    path = Path(file_path)
    normalized_type = file_type.lower()
    try:
        if normalized_type == "txt":
            for encoding in ("utf-8", "gbk"):
                try:
                    return path.read_text(encoding=encoding)
                except UnicodeDecodeError:
                    continue
        if normalized_type == "pdf":
            import PyPDF2

            with path.open("rb") as source:
                reader = PyPDF2.PdfReader(source)
                return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if normalized_type == "docx":
            from docx import Document

            document = Document(path)
            return "\n".join(
                paragraph.text
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            )
        if normalized_type == "doc":
            raise ValueError(
                "旧版 .doc 需要 LibreOffice/Gotenberg 转换后解析；请优先上传 .docx"
            )
        return "图片简历已上传。建议手动补充文本内容，便于 AI 分析。"
    except Exception as exc:
        return f"文件已上传，但解析失败：{exc}"
