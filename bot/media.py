"""Safe Telegram attachment preparation for multimodal AI prompts."""
import base64
import io
import mimetypes
import os
import posixpath
import zipfile


class MediaError(Exception):
    """A safe, user-facing attachment error."""


def _file_name(document):
    return (getattr(document, "file_name", None) or "attachment").strip()


async def _download(bot, file_id, declared_size, max_bytes):
    if declared_size and int(declared_size) > max_bytes:
        raise MediaError("file is larger than the configured limit")
    tg_file = await bot.get_file(file_id)
    data = await tg_file.download_as_bytearray()
    data = bytes(data)
    if len(data) > max_bytes:
        raise MediaError("file is larger than the configured limit")
    return data


def _mime_for(name, declared=None):
    declared = (declared or "").split(";", 1)[0].strip().lower()
    if declared:
        return declared
    return mimetypes.guess_type(name)[0] or "application/octet-stream"


def _decode_text(data):
    for encoding in ("utf-8-sig", "utf-8", "cp1256", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data):
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MediaError("PDF parser is not installed on the server") from exc
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except Exception as exc:
        raise MediaError("could not read this PDF") from exc


def _extract_docx(data):
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MediaError("DOCX parser is not installed on the server") from exc
    try:
        document = Document(io.BytesIO(data))
        return "\n".join(p.text for p in document.paragraphs if p.text.strip()).strip()
    except Exception as exc:
        raise MediaError("could not read this DOCX file") from exc


def _extract_xlsx(data, max_chars=30000):
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise MediaError("XLSX parser is not installed on the server") from exc
    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        blocks = []
        for sheet in workbook.worksheets:
            blocks.append("[Sheet: %s]" % sheet.title)
            for row in sheet.iter_rows(values_only=True):
                values = ["" if value is None else str(value) for value in row]
                if any(values):
                    blocks.append("\t".join(values))
        return "\n".join(blocks)[:max_chars]
    except Exception as exc:
        raise MediaError("could not read this XLSX file") from exc


def _safe_archive_name(name):
    normalized = posixpath.normpath(str(name).replace("\\", "/"))
    return normalized not in (".", "..") and not normalized.startswith("../") and not normalized.startswith("/")


def _extract_zip(data, max_files=20, max_chars=30000):
    """Read a ZIP in memory without extracting to disk or following paths."""
    text_suffixes = {
        ".txt", ".md", ".csv", ".tsv", ".json", ".xml", ".html", ".htm",
        ".py", ".js", ".ts", ".java", ".go", ".rs", ".c", ".cpp", ".h",
        ".sql", ".yaml", ".yml", ".toml", ".ini", ".log", ".env",
    }
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        infos = [item for item in archive.infolist() if not item.is_dir()]
        if len(infos) > max(1, int(max_files)):
            raise MediaError("ZIP contains more files than the configured limit")
        blocks = []
        total_uncompressed = 0
        for info in infos:
            if not _safe_archive_name(info.filename):
                raise MediaError("ZIP contains an unsafe path")
            if info.file_size > max_chars * 4:
                raise MediaError("a file inside ZIP is too large")
            total_uncompressed += info.file_size
            if total_uncompressed > max_chars * 8:
                raise MediaError("uncompressed ZIP content is too large")
            suffix = os.path.splitext(info.filename)[1].lower()
            if suffix not in text_suffixes:
                blocks.append("[Skipped binary file: %s]" % info.filename)
                continue
            blocks.append("[File: %s]\n%s" % (info.filename, _decode_text(archive.read(info))))
        text = "\n\n".join(blocks)
        return text[:max_chars] + ("\n[ZIP content truncated]" if len(text) > max_chars else "")
    except zipfile.BadZipFile as exc:
        raise MediaError("this is not a valid ZIP file") from exc


async def prepare_attachment(message, bot, max_bytes, default_prompt="Analyze this attachment.",
                             max_archive_files=20, max_extracted_chars=30000):
    """Return ``(prompt_content, display_name)`` for a safe AI attachment."""
    photo = getattr(message, "photo", None) or []
    document = getattr(message, "document", None)
    caption = (getattr(message, "caption", None) or getattr(message, "text", None) or "").strip()

    if photo:
        item = photo[-1]
        data = await _download(bot, item.file_id, getattr(item, "file_size", 0), max_bytes)
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {"type": "text", "text": caption or default_prompt},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,%s" % encoded}},
        ], "photo"

    if not document:
        raise MediaError("this attachment type is not supported")

    name = _file_name(document)
    mime = _mime_for(name, getattr(document, "mime_type", None))
    data = await _download(bot, document.file_id, getattr(document, "file_size", 0), max_bytes)
    suffix = os.path.splitext(name)[1].lower()

    if mime.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {"type": "text", "text": caption or default_prompt},
            {"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime, encoded)}},
        ], name

    if suffix == ".zip" or mime in ("application/zip", "application/x-zip-compressed"):
        text = _extract_zip(data, max_archive_files, max_extracted_chars)
    elif mime == "application/pdf" or suffix == ".pdf":
        text = _extract_pdf(data)
    elif suffix == ".docx" or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = _extract_docx(data)
    elif suffix == ".xlsx" or mime == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        text = _extract_xlsx(data, max_extracted_chars)
    elif mime.startswith("text/") or suffix in {
        ".txt", ".md", ".csv", ".tsv", ".json", ".xml", ".html", ".htm", ".py", ".js", ".ts", ".java", ".go", ".rs", ".sql", ".yaml", ".yml", ".log"
    }:
        text = _decode_text(data)
    else:
        raise MediaError("this file type is not supported; send an image, PDF, DOCX, ZIP or text file")

    if not text.strip():
        raise MediaError("no readable text was found in this file")
    if len(text) > max_extracted_chars:
        text = text[:max_extracted_chars] + "\n[content truncated]"
    prefix = caption or default_prompt
    return "%s\n\n[File: %s]\n%s" % (prefix, name, text), name
