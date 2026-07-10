from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


SUPPORTED_EXTENSIONS = {".txt", ".md"}
SUPPORTED_CONTENT_TYPES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",
}


class UnsupportedDocumentType(ValueError):
    pass


def _safe_filename(filename: str) -> str:
    return Path(filename).name


def validate_document_file(uploaded_file) -> None:
    safe_name = _safe_filename(uploaded_file.name)
    if safe_name != uploaded_file.name:
        raise ValidationError("Uploaded filename must not contain path separators.")

    if len(safe_name) > 255:
        raise ValidationError("Uploaded filename is too long.")

    extension = Path(safe_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValidationError("Only .txt and .md files are supported in this phase.")

    content_type = getattr(uploaded_file, "content_type", "")
    if content_type and content_type not in SUPPORTED_CONTENT_TYPES:
        raise ValidationError("Unsupported document content type.")

    if getattr(uploaded_file, "size", 0) <= 0:
        raise ValidationError("Uploaded file must not be empty.")

    max_size = getattr(settings, "SUPPORTFLOW_MAX_UPLOAD_SIZE", 0)
    if max_size and uploaded_file.size > max_size:
        raise ValidationError("Uploaded file is too large.")


def extract_text_from_file(file_obj, filename: str) -> str:
    extension = Path(_safe_filename(filename)).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise UnsupportedDocumentType("Only .txt and .md files are supported in this phase.")

    file_obj.open("rb")
    try:
        raw_content = file_obj.read()
    finally:
        file_obj.close()

    if isinstance(raw_content, str):
        return raw_content.strip()

    try:
        return raw_content.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ValueError("Document must be UTF-8 encoded.") from exc
