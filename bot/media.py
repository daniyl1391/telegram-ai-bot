"""Telegram attachment preparation for multimodal AI prompts.

The bot keeps receipts in the payment flow, while every other photo/document is
turned into an AI input. Images are sent as data URLs (so the Telegram bot token
is never exposed to an AI provider); common text formats, PDF and DOCX files are
extracted locally when their optional parser is installed.
"""
import base64
import io
import mimetypes
import os


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


async def prepare_attachment(message, bot, max_bytes, default_prompt="Analyze this attachment."):
    """Return ``(prompt_content, display_name)`` for a Telegram attachment.

    ``prompt_content`` is either text or OpenAI-compatible multimodal content.
    The caller decides whether the selected model supports vision; providers
    that do not will return a normal, readable API error instead of crashing.
    """
    photo = getattr(message, "photo", None) or []
    document = getattr(message, "document", None)
    caption = (getattr(message, "caption", None) or getattr(message, "text", None) or "").strip()

    if photo:
        item = photo[-1]
        data = await _download(bot, item.file_id, getattr(item, "file_size", 0), max_bytes)
        mime = "image/jpeg"
        encoded = base64.b64encode(data).decode("ascii")
        text = caption or default_prompt
        return [
            {"type": "text", "text": text},
            {"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime, encoded)}},
        ], "photo"

    if not document:
        raise MediaError("this attachment type is not supported")

    name = _file_name(document)
    mime = _mime_for(name, getattr(document, "mime_type", None))
    data = await _download(bot, document.file_id, getattr(document, "file_size", 0), max_bytes)

    if mime.startswith("image/") or os.path.splitext(name)[1].lower() in {
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"
    }:
        encoded = base64.b64encode(data).decode("ascii")
        return [
            {"type": "text", "text": caption or default_prompt},
            {"type": "image_url", "image_url": {"url": "data:%s;base64,%s" % (mime, encoded)}},
        ], name

    suffix = os.path.splitext(name)[1].lower()
    if mime == "application/pdf" or suffix == ".pdf":
        text = _extract_pdf(data)
    elif suffix == ".docx" or mime == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text = _extract_docx(data)
    elif mime.startswith("text/") or suffix in {
        ".txt", ".md", ".csv", ".json", ".xml", ".html", ".py", ".js", ".ts", ".log"
    }:
        text = _decode_text(data)
    else:
        raise MediaError("this file type is not supported; send an image, PDF, DOCX or text file")

    if not text.strip():
        raise MediaError("no readable text was found in this file")
    if len(text) > 30000:
        text = text[:30000] + "\n[content truncated]"
    prefix = caption or default_prompt
    return "%s\n\n[File: %s]\n%s" % (prefix, name, text), name
