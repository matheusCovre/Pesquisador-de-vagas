import json
import socket
import sys

import pytest

from app.config import Settings, get_settings
from app.schemas.resume import ResumeData


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch, resume):
    """Não carregar credenciais reais nem escrever na pasta dos currículos."""
    settings = Settings(
        _env_file=None,
        OPENAI_API_KEY="",
        TAVILY_API_KEY="",
        ID_CLIENT="",
        KEY_CLIENT="",
        SUPABASE_KEY="",
        CURRICULOS_DIR=tmp_path / "curriculos",
        GMAIL_TOKEN_PATH=str(tmp_path / "gmail_token.json"),
        GMAIL_OAUTH_DB_PATH=tmp_path / "private" / "oauth.sqlite3",
        GUARDRAIL_SOURCE_PATH=tmp_path / "approved.json",
    )
    source = {
        "candidate": resume.candidate.model_dump(exclude={"headline"}),
        "variants": [
            {
                "headline": resume.candidate.headline,
                "summary": resume.summary,
                "skills": [
                    {"category": "Desenvolvimento", "description": ", ".join(resume.skills)}
                ],
                "experiences": [item.model_dump() for item in resume.experiences],
            }
        ],
        "education": [item.model_dump() for item in resume.education],
        "languages": [{"name": "Português", "level": "Nativo", "notes": None}],
    }
    settings.GUARDRAIL_SOURCE_PATH.write_text(json.dumps(source), encoding="utf-8")
    get_settings.cache_clear()
    # Substituir também funções importadas diretamente pelos módulos carregados.
    for name, module in list(sys.modules.items()):
        if name.startswith("app.") and hasattr(module, "get_settings"):
            monkeypatch.setattr(module, "get_settings", lambda: settings)
    yield settings
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def block_external_connections(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Testes não podem acessar serviços externos.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)


@pytest.fixture
def resume():
    return ResumeData(
        title="Currículo de teste",
        targetRole="Desenvolvedor Python",
        targetCompany="Empresa de teste",
        candidate={
            "name": "Pessoa de teste",
            "headline": "Python e automação",
            "email": "teste@example.com",
        },
        summary="Experiência com desenvolvimento Python.",
        experiences=[
            {
                "role": "Desenvolvedor",
                "company": "Empresa exemplo",
                "period": "2025 – 2026",
                "highlights": ["Integração de APIs."],
            }
        ],
        education=[
            {
                "degree": "Engenharia",
                "institution": "Instituição de teste",
                "period": "Em andamento",
            }
        ],
        skills=["Python", "FastAPI"],
        languages=["Português (Nativo)"],
    )
