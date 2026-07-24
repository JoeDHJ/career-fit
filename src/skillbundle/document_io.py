"""Safe local text extraction and identifier previews for resume imports."""

from __future__ import annotations

from base64 import b64decode
from io import BytesIO
import re
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile


MAX_DOCUMENT_BYTES = 1_000_000
MAX_EXTRACTED_CHARACTERS = 40_000
MAX_PDF_PAGES = 25

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_PHONE = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-])\d{3,4}[\s.-]\d{3,4}(?!\d)"
)
_US_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_URL = re.compile(r"\bhttps?://[^\s<>]+", re.I)
_WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


class DocumentExtractionError(ValueError):
    """Raised when an uploaded document cannot be safely converted to text."""


def _safe_text(value: str) -> str:
    return value.replace("\x00", "").strip()[:MAX_EXTRACTED_CHARACTERS]


def _docx_text(payload: bytes) -> str:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            entries = archive.infolist()
            if len(entries) > 200 or sum(item.file_size for item in entries) > 8_000_000:
                raise DocumentExtractionError("The DOCX file is too complex to import safely.")
            try:
                document_xml = archive.read("word/document.xml")
            except KeyError as error:
                raise DocumentExtractionError("This DOCX file has no readable document text.") from error
    except BadZipFile as error:
        raise DocumentExtractionError("The selected .docx file is not a valid Word document.") from error
    try:
        root = ElementTree.fromstring(document_xml)
    except ElementTree.ParseError as error:
        raise DocumentExtractionError("The DOCX text could not be read safely.") from error
    paragraphs = []
    for paragraph in root.iter(f"{_WORD_NAMESPACE}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{_WORD_NAMESPACE}t"))
        if text.strip():
            paragraphs.append(text.strip())
    return _safe_text("\n".join(paragraphs))


def _pdf_text(payload: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(payload))
    except Exception as error:  # pypdf normalizes several malformed-PDF errors.
        raise DocumentExtractionError("The selected PDF could not be opened.") from error
    if reader.is_encrypted:
        raise DocumentExtractionError("Password-protected PDFs cannot be imported.")
    if len(reader.pages) > MAX_PDF_PAGES:
        raise DocumentExtractionError("The PDF has too many pages; import a shorter resume.")
    try:
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise DocumentExtractionError("The PDF text could not be extracted.") from error
    text = _safe_text(text)
    if not text:
        raise DocumentExtractionError(
            "This PDF has no selectable text. It may be a scan; paste a text version instead."
        )
    return text


def redact_common_direct_identifiers(value: str) -> tuple[str, list[str]]:
    """Return a preview with common direct identifiers removed, plus categories."""

    found: list[str] = []

    def replace(pattern: re.Pattern[str], replacement: str, category: str, text: str) -> str:
        if pattern.search(text):
            found.append(category)
        return pattern.sub(replacement, text)

    redacted = value
    redacted = replace(_URL, "[redacted URL]", "URLs", redacted)
    redacted = replace(_EMAIL, "[redacted email]", "email addresses", redacted)
    redacted = replace(_PHONE, "[redacted phone]", "phone numbers", redacted)
    redacted = replace(_US_SSN, "[redacted government ID]", "government IDs", redacted)
    return redacted, found


def extract_import_preview(
    encoded: str, filename: str, content_type: str = ""
) -> dict[str, object]:
    """Decode one locally uploaded resume and return an editable safety preview."""

    if not isinstance(encoded, str) or not isinstance(filename, str):
        raise DocumentExtractionError("The document request is malformed.")
    try:
        payload = b64decode(encoded, validate=True)
    except ValueError as error:
        raise DocumentExtractionError("The document content is not valid base64.") from error
    if not payload or len(payload) > MAX_DOCUMENT_BYTES:
        raise DocumentExtractionError("Documents must be between 1 byte and 1 MB.")
    extension = Path(filename).suffix.lower()
    if extension == ".docx":
        text = _docx_text(payload)
        document_type = "DOCX"
    elif extension == ".pdf":
        text = _pdf_text(payload)
        document_type = "text PDF"
    elif extension in {".txt", ".md", ".json"}:
        text = _safe_text(payload.decode("utf-8", errors="replace"))
        document_type = "text"
    else:
        raise DocumentExtractionError("Use a DOCX, text PDF, TXT, Markdown, or JSON file.")
    if not text:
        raise DocumentExtractionError("No readable text was found in this document.")
    preview, identifiers = redact_common_direct_identifiers(text)
    notice = (
        "Common direct identifiers were removed from this editable preview. "
        "Names, employers, addresses, and sensitive facts may remain; edit before using it."
        if identifiers
        else "Review this editable preview before using it. Names, employers, addresses, and sensitive facts may remain."
    )
    return {
        "filename": Path(filename).name[:180],
        "document_type": document_type,
        "redacted_preview": preview,
        "detected_identifier_types": identifiers,
        "notice": notice,
        "content_type": str(content_type)[:120],
    }
