from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers import drive
from app.schemas.resume import ExportRequest
from app.services import drive_service
from app.services.guardrail_service import GuardrailViolation


def test_drive_status_disconnected():
    assert drive.drive_status() == {"connected": False, "has_drive_scope": False}


def test_drive_files_requires_authentication():
    with pytest.raises(HTTPException) as exc:
        drive.drive_files()
    assert exc.value.status_code == 401


def test_drive_upload_validates_before_sending(resume, isolated_settings):
    tampered = resume.model_copy(deep=True)
    tampered.skills.append("Competência não autorizada")

    with (
        patch.object(drive, "upload_resume_to_drive") as upload,
        pytest.raises(GuardrailViolation),
    ):
        drive.drive_upload(ExportRequest(format="pdf", resume=tampered))

    upload.assert_not_called()
    assert not isolated_settings.CURRICULOS_DIR.exists()


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_drive_upload_saves_and_uploads_verified_file(resume, isolated_settings, file_format):
    with patch.object(
        drive,
        "upload_resume_to_drive",
        return_value={"id": "drv-123", "name": f"curriculo.{file_format}", "webViewLink": ""},
    ) as upload:
        res = drive.drive_upload(ExportRequest(format=file_format, resume=resume))

    file_id = res["arquivo_id"]
    saved = (isolated_settings.CURRICULOS_DIR / file_id).read_bytes()
    assert upload.call_args.kwargs["file_bytes"] == saved
    assert res["drive"]["id"] == "drv-123"


def test_drive_service_creates_folder_and_uploads(isolated_settings):
    fake_files = MagicMock()
    fake_files.list.return_value.execute.return_value = {"files": []}
    fake_files.create.return_value.execute.side_effect = [
        {"id": "folder-1"},
        {"id": "file-1", "name": "curriculo.pdf", "webViewLink": "https://drive.google.com/file/1"},
    ]
    fake_service = MagicMock()
    fake_service.files.return_value = fake_files
    fake_creds = MagicMock(valid=True, scopes=["https://www.googleapis.com/auth/drive.file"])

    with (
        patch.object(drive_service, "get_credentials", return_value=fake_creds),
        patch.object(drive_service, "build", return_value=fake_service),
    ):
        uploaded = drive_service.upload_resume_to_drive(
            b"%PDF-1.4", "curriculo.pdf", "application/pdf"
        )

    assert uploaded["folder_id"] == "folder-1"
    assert uploaded["id"] == "file-1"
