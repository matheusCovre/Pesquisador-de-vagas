from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.routers import gmail
from app.schemas.resume import SendEmailRequest


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_send_uses_saved_file_and_registers_only_reference(resume, isolated_settings, file_format):
    payload = SendEmailRequest(
        recipient_email="rh@example.com",
        company="Teste",
        subject="Teste",
        body="Teste",
        format=file_format,
        reviewed_by_user=True,
        resume=resume,
    )
    with (
        patch.object(
            gmail, "send_email_with_attachment", return_value={"id": "email-teste"}
        ) as send,
        patch.object(gmail, "register_candidatura_flow", return_value={}) as register,
    ):
        result = gmail.gmail_send(payload)
    file_id = result["arquivo_id"]
    saved = (isolated_settings.CURRICULOS_DIR / file_id).read_bytes()
    assert send.call_args.kwargs["attachment_bytes"] == saved
    metadata = register.call_args.kwargs
    assert metadata[f"arquivo_{file_format}_id"] == file_id
    assert metadata["comprovante_id"] == "email-teste"
    assert "resume_data" not in metadata
    assert "curriculo" not in metadata


def test_failed_send_does_not_register_candidatura(resume):
    payload = SendEmailRequest(
        recipient_email="rh@example.com",
        subject="Teste",
        body="Teste",
        resume=resume,
        reviewed_by_user=True,
    )
    with (
        patch.object(gmail, "send_email_with_attachment", side_effect=PermissionError("Sem login")),
        patch.object(gmail, "register_candidatura_flow") as register,
        pytest.raises(HTTPException) as exc,
    ):
        gmail.gmail_send(payload)
    assert exc.value.status_code == 401
    register.assert_not_called()


def test_missing_gmail_credentials_returns_disconnected():
    assert gmail.gmail_status() == {"connected": False}
