from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import get_settings
from app.services.supabase_service import (
    list_candidaturas,
    list_modelos,
    register_candidatura_flow,
    update_candidatura_status,
)

router = APIRouter(prefix="/api/history", tags=["history"])

StatusCandidatura = Literal[
    "enviado_sem_resposta",
    "enviado_com_resposta",
    "confirmacao",
    "entrevista",
    "rejeicao",
    "aprovacao",
    "cancelamento",
]


class RegistrarCandidaturaRequest(BaseModel):
    empresa_nome: str
    vaga_titulo: str
    modelo_codigo: str = "ia_python"
    comprovante_id: str | None = None
    arquivo_docx_id: str | None = None
    arquivo_pdf_id: str | None = None


class AtualizarStatusRequest(BaseModel):
    status_novo: StatusCandidatura


@router.get("")
def get_history(limit: int = 20):
    try:
        return {"items": list_candidaturas(limit=limit)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao consultar Supabase: {exc}") from exc


@router.get("/modelos")
def get_modelos():
    try:
        return {"modelos": list_modelos()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao listar modelos: {exc}") from exc


@router.post("/candidaturas")
def create_candidatura_record(payload: RegistrarCandidaturaRequest):
    settings = get_settings()
    try:
        return register_candidatura_flow(
            empresa_nome=payload.empresa_nome,
            vaga_titulo=payload.vaga_titulo,
            modelo_codigo=payload.modelo_codigo,
            modelo_ia=settings.MODEL_WRITE,
            comprovante_id=payload.comprovante_id,
            arquivo_docx_id=payload.arquivo_docx_id,
            arquivo_pdf_id=payload.arquivo_pdf_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Erro ao registrar candidatura: {exc}"
        ) from exc


@router.patch("/candidaturas/{candidatura_id}/status")
def patch_candidatura_status(candidatura_id: str, payload: AtualizarStatusRequest):
    try:
        updated = update_candidatura_status(candidatura_id, payload.status_novo)
        if not updated:
            raise HTTPException(status_code=404, detail="Candidatura não encontrada.")
        return updated
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar status: {exc}") from exc
