from io import BytesIO
from zipfile import BadZipFile, ZipFile

import pymupdf

from app.services.guardrail_service import (
    MAX_UPLOAD_BYTES,
    GuardrailViolation,
    assert_private_text,
    issue,
    load_approved_source,
)


def verify_upload(raw: bytes, file_format: str) -> None:
    if not raw or len(raw) > MAX_UPLOAD_BYTES:
        raise GuardrailViolation([issue("invalid_upload_size", "file")])
    try:
        if file_format == "docx":
            with ZipFile(BytesIO(raw)) as archive:
                entries = archive.infolist()
                if len(entries) > 1000 or sum(e.file_size for e in entries) > 20 * 1024 * 1024:
                    raise GuardrailViolation([issue("unsafe_document_archive", "file")])
                if "word/document.xml" not in archive.namelist():
                    raise ValueError
                if any(
                    "embeddings/" in e.filename or "vbaproject" in e.filename.casefold()
                    for e in entries
                ):
                    raise GuardrailViolation([issue("embedded_content", "file")])
                text = "\n".join(
                    archive.read(e).decode("utf-8", errors="replace")
                    for e in entries
                    if e.filename.endswith((".xml", ".rels"))
                )
        elif file_format == "pdf":
            with pymupdf.open(stream=raw, filetype="pdf") as document:
                if document.is_encrypted or len(document) > 10 or document.embfile_count():
                    raise GuardrailViolation([issue("unsafe_pdf", "file")])
                text = (
                    str(document.metadata) + "\n" + "\n".join(page.get_text() for page in document)
                )
        else:
            raise ValueError
    except GuardrailViolation:
        raise
    except (BadZipFile, ValueError, RuntimeError, OSError) as exc:
        raise GuardrailViolation([issue("invalid_document", "file")]) from exc
    candidate = load_approved_source()["candidate"]
    assert_private_text(text, (candidate["email"],), (candidate["phone"],))
