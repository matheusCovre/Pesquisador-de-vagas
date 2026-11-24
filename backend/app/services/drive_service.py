from io import BytesIO

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from app.config import get_settings
from app.services.gmail_service import get_credentials, has_drive_scope

FOLDER_MIME = "application/vnd.google-apps.folder"


def _require_drive_service():
    creds = get_credentials()
    if not creds:
        raise PermissionError("Google Drive não autenticado. Conecte via /api/gmail/auth-url.")
    if not has_drive_scope(creds):
        raise PermissionError(
            "Token atual não possui permissão do Google Drive. Reconecte a conta Google."
        )
    return build("drive", "v3", credentials=creds)


def _get_or_create_folder(service, folder_name: str) -> str:
    safe_name = folder_name.replace("'", "\\'")
    query = f"name = '{safe_name}' and mimeType = '{FOLDER_MIME}' and trashed = false"
    existing = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = existing.get("files", [])
    if files:
        return files[0]["id"]

    created = (
        service.files()
        .create(
            body={"name": folder_name, "mimeType": FOLDER_MIME},
            fields="id",
        )
        .execute()
    )
    return created["id"]


def upload_resume_to_drive(file_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Envia o currículo validado para a pasta dedicada no Google Drive."""
    service = _require_drive_service()
    folder_id = _get_or_create_folder(service, get_settings().GOOGLE_DRIVE_FOLDER_NAME)
    media = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mime_type, resumable=False)
    created = (
        service.files()
        .create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id, name, webViewLink",
        )
        .execute()
    )
    return {
        "id": created.get("id"),
        "name": created.get("name"),
        "webViewLink": created.get("webViewLink", ""),
        "folder_id": folder_id,
    }


def list_drive_resumes(limit: int = 20) -> list[dict]:
    """Lista os currículos salvos na pasta dedicada do Google Drive."""
    service = _require_drive_service()
    folder_id = _get_or_create_folder(service, get_settings().GOOGLE_DRIVE_FOLDER_NAME)
    query = f"'{folder_id}' in parents and trashed = false"
    res = (
        service.files()
        .list(
            q=query,
            pageSize=limit,
            orderBy="modifiedTime desc",
            fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
        )
        .execute()
    )
    return res.get("files", [])
