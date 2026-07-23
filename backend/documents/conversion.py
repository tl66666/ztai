from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def convert_word_to_pdf(
    source_path: str | Path,
    target_path: str | Path,
) -> bool:
    """Convert Word to PDF through optional platform adapters."""

    source = Path(source_path).resolve()
    target = Path(target_path).resolve()
    if sys.platform == "win32" and _convert_with_windows_com(source, target):
        return True
    return _convert_with_libreoffice(source, target)


def convert_pdf_to_word(
    source_path: str | Path,
    target_path: str | Path,
) -> None:
    from pdf2docx import Converter

    converter = Converter(str(source_path))
    try:
        converter.convert(str(target_path), start=0, end=None)
    finally:
        converter.close()


def _convert_with_windows_com(source: Path, target: Path) -> bool:
    """Optional Windows-only adapter; never imported on macOS or Linux."""

    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return False

    word = None
    document = None
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        document = word.Documents.Open(str(source), ReadOnly=True)
        document.SaveAs(str(target), FileFormat=17)
        return target.is_file() and target.stat().st_size > 0
    except Exception:
        return False
    finally:
        if document is not None:
            document.Close(False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()


def _convert_with_libreoffice(source: Path, target: Path) -> bool:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if not executable:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            executable,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(target.parent),
            str(source),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    generated = target.parent / f"{source.stem}.pdf"
    if result.returncode != 0 or not generated.is_file():
        return False
    if os.path.normcase(generated) != os.path.normcase(target):
        generated.replace(target)
    return target.is_file() and target.stat().st_size > 0
