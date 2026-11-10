import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.core.errors import AppError


def is_pdf(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(5) == b"%PDF-"
    except OSError:
        return False


def is_docx(path: Path) -> bool:
    if not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            return "word/document.xml" in archive.namelist()
    except zipfile.BadZipFile:
        return False


def validate_resume_file(path: Path, file_type: str) -> None:
    if file_type == "pdf":
        if not is_pdf(path):
            raise AppError("文件内容不是有效的 PDF", 400)
        return
    if file_type == "docx":
        if not is_docx(path):
            raise AppError("文件内容不是有效的 DOCX", 400)
        return
    raise AppError("只支持 PDF 和 DOCX", 400)


def extract_text(path: Path, file_type: str) -> str:
    if file_type == "pdf":
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        text = "\n".join(pages)
    elif file_type == "docx":
        document = Document(str(path))
        parts = [paragraph.text for paragraph in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append(" ".join(cell.text.strip() for cell in row.cells if cell.text.strip()))
        text = "\n".join(parts)
    else:
        raise AppError("只支持 PDF 和 DOCX", 400)
    text = text.replace("\x00", "").strip()
    if len(text) > 200_000:
        text = text[:200_000]
    if len(text) < 20:
        raise AppError("未能从文件中提取足够文本，暂不支持扫描版 PDF", 400)
    return text
