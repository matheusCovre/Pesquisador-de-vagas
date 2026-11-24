from fastapi import APIRouter, HTTPException

from app.schemas.resume import ExportRequest
from app.services.document_service import generate_and_save_resume
from app.services.drive_service import list_drive_resumes, upload_resume_to_drive
from app.services.gmail_service import get_credentials, has_drive_scope

router = APIRouter(prefix="/api/drive", tags=["drive"])


@router.get("/status")
def drive_status():
    creds = get_credentials()
    return {
        "connected": creds is not None and has_drive_scope(creds),
        "has_drive_scope": has_drive_scope(creds) if creds else False,
    }


@router.get("/files")
def drive_files(limit: int = 20):
    try:
        return {"files": list_drive_resumes(limit=limit)}
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao listar Google Drive: {exc}") from exc


@router.post("/upload")
def drive_upload(payload: ExportRequest):
    file_bytes, file_id = generate_and_save_resume(payload.resume, payload.format)
    safe_company = (payload.resume.targetCompany or "curriculo").strip().replace(" ", "_")
    if payload.format == "pdf":
        filename = f"curriculo_{safe_company}.pdf"
        mime_type = "application/pdf"
    else:
        filename = f"curriculo_{safe_company}.docx"
        mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    try:
        drive_file = upload_resume_to_drive(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro ao enviar para o Google Drive: {exc}"
        ) from exc

    return {"drive": drive_file, "arquivo_id": file_id}
