import re
import zipfile
from io import BytesIO
from xml.etree import ElementTree

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 8 * 1024 * 1024


class UnsupportedUpload(RuntimeError):
    pass


async def extract_text_from_upload(file: UploadFile) -> str:
    payload = await file.read()
    if len(payload) > MAX_UPLOAD_BYTES:
        raise UnsupportedUpload("File is too large. Maximum size is 8 MB.")

    filename = (file.filename or "").lower()
    content_type = (file.content_type or "").lower()

    if filename.endswith(".docx") or content_type.endswith("wordprocessingml.document"):
        return _extract_docx_text(payload)

    if filename.endswith(".pdf") or content_type == "application/pdf":
        return _extract_pdf_text(payload)

    return _decode_text(payload)


def split_into_paragraphs(text: str, limit: int = 8) -> list[str]:
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    if not normalized:
        return []

    paragraphs = [
        re.sub(r"\s+", " ", item).strip()
        for item in re.split(r"\n{2,}", normalized)
        if item.strip()
    ]
    if len(paragraphs) == 1:
        sentences = re.split(r"(?<=[.!?。！？])\s+|\n+", normalized)
        paragraphs = [sentence.strip() for sentence in sentences if sentence.strip()]

    return paragraphs[:limit]


def count_words(text: str) -> int:
    korean_chunks = re.findall(r"[가-힣]+", text)
    latin_chunks = re.findall(r"[A-Za-z0-9_-]+", text)
    return len(korean_chunks) + len(latin_chunks)


def _decode_text(payload: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            decoded = payload.decode(encoding)
            return decoded.strip()
        except UnicodeDecodeError:
            continue
    raise UnsupportedUpload("Only text, PDF, and DOCX files are supported.")


def _extract_docx_text(payload: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            document = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise UnsupportedUpload("Could not read DOCX text.") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    try:
        root = ElementTree.fromstring(document)
    except ElementTree.ParseError as exc:
        raise UnsupportedUpload("Could not read DOCX text.") from exc

    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
        if text:
            paragraphs.append(text)

    return "\n\n".join(paragraphs).strip()


def _extract_pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:  # pragma: no cover - dependency exists in deployed env
        raise UnsupportedUpload("PDF extraction dependency is not installed.") from exc

    try:
        reader = PdfReader(BytesIO(payload))
        pages = [page.extract_text() or "" for page in reader.pages[:12]]
    except (
        AttributeError,
        EOFError,
        KeyError,
        OSError,
        PdfReadError,
        TypeError,
        ValueError,
    ) as exc:
        raise UnsupportedUpload("Could not read PDF text.") from exc

    return "\n\n".join(page.strip() for page in pages if page.strip()).strip()
