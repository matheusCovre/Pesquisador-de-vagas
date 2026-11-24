from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.routers import chat, documents, drive, gmail, history, jobs
from app.services.guardrail_service import GuardrailViolation

app = FastAPI(title="Pesquisador de Vagas API", version="0.1.0")


@app.exception_handler(GuardrailViolation)
async def handle_guardrail_violation(request, exc: GuardrailViolation):
    return JSONResponse(
        status_code=422,
        content={"detail": "Conteúdo bloqueado pelo guardrail.", "issues": exc.issues},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Document-Id"],
)

app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(drive.router)
app.include_router(gmail.router)
app.include_router(history.router)
app.include_router(jobs.router)


@app.get("/health")
def health_check():
    settings = get_settings()
    return {
        "status": "ok",
        "env": {
            "openai_configured": bool(settings.OPENAI_API_KEY),
            "tavily_configured": bool(settings.TAVILY_API_KEY),
            "google_oauth_configured": bool(settings.ID_CLIENT and settings.KEY_CLIENT),
            "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_KEY),
        },
        "models": {
            "write": settings.MODEL_WRITE,
            "pesquisa": settings.MODEL_PESQUISA,
            "chat": settings.MODEL_CHAT,
            "planilha": settings.MODEL_PLANILHA,
        },
    }
