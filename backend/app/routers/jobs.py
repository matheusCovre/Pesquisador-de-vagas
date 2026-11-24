from fastapi import APIRouter, HTTPException

from app.schemas.resume import JobSearchRequest, JobSearchResponse
from app.services.guardrail_service import GuardrailViolation
from app.services.job_search_service import search_focused_jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/search", response_model=JobSearchResponse)
def search_jobs(payload: JobSearchRequest):
    """Pesquisa e audita vagas focadas nas áreas escolhidas pelo candidato."""
    try:
        return search_focused_jobs(payload)
    except GuardrailViolation:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Não foi possível concluir a pesquisa de vagas.",
        ) from exc
