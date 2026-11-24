import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.schemas.resume import SendEmailRequest
from app.services.document_service import generate_and_save_resume
from app.services.gmail_service import (
    create_auth_url,
    exchange_code_for_token,
    get_credentials,
    list_messages,
    send_email_with_attachment,
)
from app.services.guardrail_service import (
    GuardrailViolation,
    assert_private_text,
    issue,
    verify_resume,
)
from app.services.oauth_state_service import OAUTH_TTL_SECONDS, SESSION_COOKIE
from app.services.supabase_service import register_candidatura_flow

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.get("/status")
def gmail_status():
    creds = get_credentials()
    return {"connected": creds is not None}


@router.get("/auth-url")
def gmail_auth_url():
    # Iniciar no navegador permite definir o cookie no mesmo host do callback,
    # inclusive se a interface estiver aberta em 127.0.0.1 em vez de localhost.
    _origin = urlsplit(get_settings().GOOGLE_REDIRECT_URI)
    return {"auth_url": f"{_origin.scheme}://{_origin.netloc}/api/gmail/auth"}


@router.get("/auth")
def gmail_start_auth(request: Request):
    callback = urlsplit(get_settings().GOOGLE_REDIRECT_URI)
    origin = f"{callback.scheme}://{callback.netloc}"
    if str(request.base_url).rstrip("/") != origin:
        return RedirectResponse(origin + "/api/gmail/auth")
    browser_binding = request.cookies.get(SESSION_COOKIE) or secrets.token_urlsafe(32)
    try:
        response = RedirectResponse(create_auth_url(browser_binding))
        response.set_cookie(
            SESSION_COOKIE,
            browser_binding,
            max_age=OAUTH_TTL_SECONDS,
            httponly=True,
            secure=callback.scheme == "https",
            samesite="lax",
            path="/api/gmail",
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/callback")
def gmail_callback(request: Request, code: str = "", state: str = "", error: str = ""):
    try:
        exchange_code_for_token(
            "" if error else code, state, request.cookies.get(SESSION_COOKIE, "")
        )
        response = RedirectResponse(url="http://localhost:5173/?gmail=connected")
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível concluir o login Gmail. Inicie uma nova conexão e autorize novamente.",
        ) from exc


@router.get("/messages")
def gmail_messages(limit: int = 15):
    try:
        return {"messages": list_messages(max_results=limit)}
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao listar Gmail: {exc}") from exc


@router.post("/send")
def gmail_send(payload: SendEmailRequest):
    if not payload.reviewed_by_user:
        raise GuardrailViolation([issue("human_review_required", "reviewed_by_user")])
    verify_resume(payload.resume)
    assert_private_text(
        payload.subject + "\n" + payload.body,
        (payload.resume.candidate.email, payload.recipient_email),
        (payload.resume.candidate.phone,),
    )
    file_bytes, file_id = generate_and_save_resume(payload.resume, payload.format)
    if payload.format == "pdf":
        filename = "curriculo.pdf"
        mime_subtype = "pdf"
    else:
        filename = "curriculo.docx"
        mime_subtype = "vnd.openxmlformats-officedocument.wordprocessingml.document"

    try:
        result = send_email_with_attachment(
            to_email=str(payload.recipient_email),
            subject=payload.subject,
            body=payload.body,
            attachment_bytes=file_bytes,
            filename=filename,
            mime_subtype=mime_subtype,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao enviar Gmail: {exc}") from exc

    settings = get_settings()
    history_res = register_candidatura_flow(
        empresa_nome=payload.company or "Empresa não informada",
        vaga_titulo=payload.resume.targetRole or payload.resume.title,
        modelo_codigo="ia_python",
        modelo_ia=settings.MODEL_WRITE,
        comprovante_id=result.get("id"),
        arquivo_pdf_id=file_id if payload.format == "pdf" else None,
        arquivo_docx_id=file_id if payload.format == "docx" else None,
    )

    return {"gmail": result, "history": history_res, "arquivo_id": file_id}
