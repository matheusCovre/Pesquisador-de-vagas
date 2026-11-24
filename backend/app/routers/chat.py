from fastapi import APIRouter, HTTPException

from app.schemas.resume import ChatRequest, ChatResponse
from app.services.crew_service import run_resume_chat
from app.services.guardrail_service import GuardrailViolation

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat_with_agents(payload: ChatRequest):
    try:
        result = run_resume_chat(
            user_message=payload.message,
            current_resume=payload.resume,
            use_search=payload.use_search,
        )
        return ChatResponse(
            reply=result["reply"],
            updated_resume=result.get("updated_resume"),
            sources=result.get("sources") or [],
            generated_files=result.get("generated_files"),
            blocked=bool(result.get("blocked", False)),
            draft_resume=result.get("draft_resume"),
            verification_issues=result.get("verification_issues") or [],
        )
    except GuardrailViolation:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail="Não foi possível concluir a verificação do currículo."
        ) from exc
