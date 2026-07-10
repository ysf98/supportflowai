import pytest
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.documents.models import Document
from apps.documents.services.chunking import split_text_into_chunks
from apps.documents.services.extraction import extract_text_from_file, validate_document_file
from apps.documents.services.processing import process_document
from apps.organizations.services import create_organization_with_owner

User = get_user_model()


def test_split_text_into_chunks_is_deterministic():
    text = " ".join(f"word-{index}" for index in range(12))

    chunks = split_text_into_chunks(text, max_words=5, overlap_words=2)

    assert [chunk.index for chunk in chunks] == [0, 1, 2, 3]
    assert chunks[0].content == "word-0 word-1 word-2 word-3 word-4"
    assert chunks[1].metadata == {"start_word": 3, "end_word": 8}


def test_extract_text_from_utf8_txt_file():
    uploaded_file = SimpleUploadedFile(
        "support.txt",
        b"Internal support documentation\n",
        content_type="text/plain",
    )

    text = extract_text_from_file(uploaded_file, "support.txt")

    assert text == "Internal support documentation"


def test_validate_document_file_rejects_path_separators():
    class UploadedFileWithUnsafeName:
        name = "../support.txt"
        content_type = "text/plain"
        size = 30

    uploaded_file = UploadedFileWithUnsafeName()

    with pytest.raises(ValidationError, match="path separators"):
        validate_document_file(uploaded_file)


def test_validate_document_file_rejects_empty_files():
    uploaded_file = SimpleUploadedFile("empty.txt", b"", content_type="text/plain")

    with pytest.raises(ValidationError, match="must not be empty"):
        validate_document_file(uploaded_file)


def test_validate_document_file_rejects_files_over_size_limit():
    uploaded_file = SimpleUploadedFile("large.txt", b"abcdef", content_type="text/plain")

    with override_settings(SUPPORTFLOW_MAX_UPLOAD_SIZE=5):
        with pytest.raises(ValidationError, match="too large"):
            validate_document_file(uploaded_file)


@pytest.mark.django_db
def test_process_document_extracts_text_and_creates_chunks(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        uploaded_file = SimpleUploadedFile(
            "guide.md",
            b"# Guide\n\n" + b" ".join([b"word"] * 250),
            content_type="text/markdown",
        )
        document = Document.objects.create(
            organization=organization,
            uploaded_by=owner,
            title="Guide",
            file=uploaded_file,
            original_filename="guide.md",
            content_type="text/markdown",
            size=uploaded_file.size,
        )

        processed = process_document(document)

        assert processed.status == Document.Status.PROCESSED
        assert processed.extracted_text.startswith("# Guide")
        assert processed.chunks.count() == 2
        assert processed.chunks.first().organization == organization


@pytest.mark.django_db
def test_document_upload_path_uses_safe_generated_filename(tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        owner = User.objects.create_user(email="owner@example.com", password="password-123")
        organization = create_organization_with_owner(name="Docs Org", owner=owner)
        uploaded_file = SimpleUploadedFile(
            "customer handbook.md",
            b"# Handbook",
            content_type="text/markdown",
        )

        document = Document.objects.create(
            organization=organization,
            uploaded_by=owner,
            title="Handbook",
            file=uploaded_file,
            original_filename="customer handbook.md",
            content_type="text/markdown",
            size=uploaded_file.size,
        )

        assert document.file.name.startswith(f"documents/{organization.id}/")
        assert document.file.name.endswith(".md")
        assert "customer handbook" not in document.file.name
