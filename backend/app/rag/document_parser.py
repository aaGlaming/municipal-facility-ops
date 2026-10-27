"""Safe, bounded parsers for documents accepted by the RAG ingestion boundary."""

from __future__ import annotations

import io
import re
import stat
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import PurePath
from xml.etree import ElementTree


class DocumentParseError(ValueError):
    """Raised when an accepted file cannot be parsed safely."""


@dataclass(frozen=True)
class ParsedPart:
    page_number: int | None
    heading: str | None
    text: str
    source_location: str | None


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".md", ".markdown", ".txt", ".html", ".htm"}
MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".txt": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
}


def validate_filename(filename: str | None) -> str:
    candidate = (filename or "").strip()
    if (
        not candidate
        or len(candidate) > 255
        or candidate != PurePath(candidate).name
        or "/" in candidate
        or "\\" in candidate
    ):
        raise DocumentParseError("UNSAFE_FILENAME")
    if ".." in candidate or any(ord(char) < 32 for char in candidate) or any(char in '<>:"|?*' for char in candidate):
        raise DocumentParseError("UNSAFE_FILENAME")
    extension = PurePath(candidate).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise DocumentParseError("UNSUPPORTED_EXTENSION")
    return candidate


def validate_media_type(filename: str, media_type: str | None) -> str:
    expected = MEDIA_TYPES[PurePath(filename).suffix.lower()]
    if not media_type:
        return expected
    normalized = media_type.lower().split(";", 1)[0].strip()
    if normalized not in {expected, "application/octet-stream"}:
        raise DocumentParseError("MEDIA_TYPE_MISMATCH")
    return expected


def parse_document(filename: str, content: bytes) -> list[ParsedPart]:
    extension = PurePath(filename).suffix.lower()
    if extension in {".md", ".markdown", ".txt", ".html", ".htm"} and b"\x00" in content:
        raise DocumentParseError("UNSAFE_CONTENT")
    if extension in {".md", ".markdown"}:
        parts = _parse_markdown(content)
    elif extension == ".txt":
        parts = _parse_text(content)
    elif extension in {".html", ".htm"}:
        if re.search(rb"<\s*(script|iframe|object)\b|javascript\s*:", content, flags=re.IGNORECASE):
            raise DocumentParseError("UNSAFE_CONTENT")
        parts = _parse_html(content)
    elif extension == ".docx":
        parts = _parse_docx(content)
    elif extension == ".pdf":
        parts = _parse_pdf(content)
    else:
        raise DocumentParseError("UNSUPPORTED_EXTENSION")
    if not parts:
        raise DocumentParseError("EMPTY_DOCUMENT")
    return parts


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentParseError("INVALID_TEXT_ENCODING") from exc


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _parse_text(content: bytes) -> list[ParsedPart]:
    return [
        ParsedPart(None, None, _clean(block), None) for block in re.split(r"\n\s*\n", _decode(content)) if _clean(block)
    ]


def _parse_markdown(content: bytes) -> list[ParsedPart]:
    parts: list[ParsedPart] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = _clean(" ".join(buffer))
        if text:
            parts.append(ParsedPart(None, heading, text, None))
        buffer = []

    for line in _decode(content).splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            flush()
            heading = _clean(match.group(1))
        elif line.strip():
            buffer.append(line)
        else:
            flush()
    flush()
    return parts


class _HTMLPartsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[ParsedPart] = []
        self.heading: str | None = None
        self.buffer: list[str] = []
        self.in_table = False
        self.in_cell = False
        self.row: list[str] = []
        self.table_rows: list[str] = []
        self.cell: list[str] = []
        self.skip_depth = 0

    def _flush(self) -> None:
        text = _clean(" ".join(self.buffer))
        if text:
            self.parts.append(ParsedPart(None, self.heading, text, None))
        self.buffer = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"}:
            self.skip_depth += 1
        elif self.skip_depth == 0 and tag in {"h1", "h2", "h3", "h4", "h5", "h6", "title"}:
            self._flush()
            self.heading = None
            self.in_cell = False
            self.cell = []
        elif self.skip_depth == 0 and tag == "table":
            self._flush()
            self.in_table = True
            self.table_rows = []
        elif self.skip_depth == 0 and self.in_table and tag == "tr":
            self.row = []
        elif self.skip_depth == 0 and self.in_table and tag in {"th", "td"}:
            self.in_cell = True
            self.cell = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object"}:
            self.skip_depth = max(0, self.skip_depth - 1)
        elif self.skip_depth == 0 and self.in_table and tag in {"th", "td"} and self.in_cell:
            self.row.append(_clean(" ".join(self.cell)))
            self.in_cell = False
            self.cell = []
        elif self.skip_depth == 0 and self.in_table and tag == "tr":
            row_text = " | ".join(cell for cell in self.row if cell)
            if row_text:
                self.table_rows.append(row_text)
            self.row = []
        elif self.skip_depth == 0 and tag == "table":
            self.in_table = False
            if self.table_rows:
                self.parts.append(ParsedPart(None, self.heading, "\n".join(self.table_rows), "table"))
            self.table_rows = []
        elif self.skip_depth == 0 and tag in {"h1", "h2", "h3", "h4", "h5", "h6", "title"}:
            value = _clean(" ".join(self.buffer))
            if value:
                self.heading = value
            self.buffer = []
        elif self.skip_depth == 0 and tag in {"p", "li", "div", "br"}:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_table and self.in_cell:
            self.cell.append(data)
        else:
            self.buffer.append(data)


def _parse_html(content: bytes) -> list[ParsedPart]:
    parser = _HTMLPartsParser()
    parser.feed(_decode(content))
    parser._flush()
    return parser.parts


def _parse_docx(content: bytes) -> list[ParsedPart]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile as exc:
        raise DocumentParseError("INVALID_DOCX") from exc
    total_uncompressed = 0
    for info in archive.infolist():
        mode = (info.external_attr >> 16) & 0xFFFF
        if info.filename.startswith(("/", "\\")) or ".." in PurePath(info.filename).parts or stat.S_ISLNK(mode):
            raise DocumentParseError("UNSAFE_ARCHIVE")
        total_uncompressed += info.file_size
        if total_uncompressed > 50 * 1024 * 1024:
            raise DocumentParseError("ARCHIVE_TOO_LARGE")
    try:
        xml = ElementTree.fromstring(archive.read("word/document.xml"))
    except (KeyError, ElementTree.ParseError) as exc:
        raise DocumentParseError("INVALID_DOCX") from exc
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    parts: list[ParsedPart] = []
    heading: str | None = None
    body = xml.find("w:body", ns)
    if body is None:
        return []
    for child in list(body):
        if child.tag.endswith("}p"):
            text = _clean("".join(node.text or "" for node in child.findall(".//w:t", ns)))
            if not text:
                continue
            style = child.find("w:pPr/w:pStyle", ns)
            if style is not None and str(style.attrib.get(f"{{{ns['w']}}}val", "")).lower().startswith("heading"):
                heading = text
            else:
                parts.append(ParsedPart(None, heading, text, "paragraph"))
        elif child.tag.endswith("}tbl"):
            rows = []
            for row in child.findall("w:tr", ns):
                cells = []
                for cell in row.findall("w:tc", ns):
                    cells.append(_clean(" ".join(node.text or "" for node in cell.findall(".//w:t", ns))))
                if any(cells):
                    rows.append(" | ".join(cells))
            if rows:
                parts.append(ParsedPart(None, heading, "\n".join(rows), "table"))
    return parts


def _parse_pdf(content: bytes) -> list[ParsedPart]:
    if not content.startswith(b"%PDF-"):
        raise DocumentParseError("INVALID_PDF")
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content), strict=False)
        if len(reader.pages) > 500:
            raise DocumentParseError("PDF_TOO_MANY_PAGES")
        parts = []
        total_characters = 0
        for number, page in enumerate(reader.pages, start=1):
            text = _clean(page.extract_text() or "")
            if text:
                total_characters += len(text)
                if total_characters > 5_000_000:
                    raise DocumentParseError("PDF_TEXT_TOO_LARGE")
                parts.append(ParsedPart(number, None, text, f"page:{number}"))
        return parts
    except DocumentParseError:
        raise
    except Exception as exc:  # parser errors vary by PDF implementation
        raise DocumentParseError("INVALID_PDF") from exc
