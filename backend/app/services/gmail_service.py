import base64
import os
import secrets
import tempfile
from email.message import EmailMessage
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import get_settings
from app.services.oauth_state_service import consume_attempt, save_attempt

DRIVE_FILE_SCOPE = "https://www.googleapis.com/auth/drive.file"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    DRIVE_FILE_SCOPE,
]


def _client_config() -> dict:
    settings = get_settings()
    if not settings.ID_CLIENT or not settings.KEY_CLIENT:
        raise ValueError("ID_CLIENT e KEY_CLIENT não configurados no .env")
    return {
        "web": {
            "client_id": settings.ID_CLIENT,
            "client_secret": settings.KEY_CLIENT,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }


def get_credentials() -> Credentials | None:
    settings = get_settings()
    token_path = Path(settings.GMAIL_TOKEN_PATH)
    if not token_path.exists():
        return None

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_credentials(creds.to_json())
    return creds if creds and creds.valid else None


def has_drive_scope(creds: Credentials | None = None) -> bool:
    target = creds or get_credentials()
    if not target:
        return False
    granted = set(target.scopes or ())
    return not granted or DRIVE_FILE_SCOPE in granted


def _save_credentials(serialized: str) -> None:
    token_path = Path(get_settings().GMAIL_TOKEN_PATH)
    token_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(dir=token_path.parent, prefix=".gmail-token-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(serialized)
        os.replace(temporary, token_path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_auth_url(browser_binding: str) -> str:
    settings = get_settings()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
        code_verifier=verifier,
        autogenerate_code_verifier=False,
    )
    auth_url, returned_state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    if not secrets.compare_digest(state, returned_state):
        raise ValueError("Não foi possível iniciar o login. Tente novamente.")
    save_attempt(state, browser_binding, verifier)
    return auth_url


def exchange_code_for_token(code: str, state: str, browser_binding: str) -> None:
    settings = get_settings()
    verifier = consume_attempt(state, browser_binding)
    if not code:
        raise ValueError("Autorização não concluída. Inicie uma nova conexão com o Gmail.")
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=state,
        code_verifier=verifier,
        autogenerate_code_verifier=False,
    )
    flow.fetch_token(code=code, code_verifier=verifier)
    _save_credentials(flow.credentials.to_json())


def list_messages(max_results: int = 15) -> list[dict]:
    creds = get_credentials()
    if not creds:
        raise PermissionError("Gmail não autenticado. Conecte via /api/gmail/auth-url.")

    service = build("gmail", "v1", credentials=creds)
    results = service.users().messages().list(userId="me", maxResults=max_results).execute()
    messages_meta = results.get("messages", [])

    items = []
    for meta in messages_meta:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=meta["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            )
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        labels = msg.get("labelIds", [])
        items.append(
            {
                "id": msg["id"],
                "direction": "sent" if "SENT" in labels else "received",
                "unread": "UNREAD" in labels,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", "(Sem assunto)"),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
                "body": msg.get("snippet", ""),
            }
        )
    return items


def send_email_with_attachment(
    to_email: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    filename: str,
    mime_subtype: str,
) -> dict:
    creds = get_credentials()
    if not creds:
        raise PermissionError("Gmail não autenticado. Conecte via /api/gmail/auth-url.")

    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    message.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype=mime_subtype,
        filename=filename,
    )

    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service = build("gmail", "v1", credentials=creds)
    sent = service.users().messages().send(userId="me", body={"raw": encoded}).execute()
    return {"id": sent.get("id"), "status": "sent"}
