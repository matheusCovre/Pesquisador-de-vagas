from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI & Models
    OPENAI_API_KEY: str = ""
    MODEL_WRITE: str = "gpt-6-luna"
    MODEL_PESQUISA: str = "gpt-6-luna"
    MODEL_CHAT: str = "gpt-6-luna"
    MODEL_PLANILHA: str = "gpt-6-luna"

    # Tavily Search
    TAVILY_API_KEY: str = ""

    # Google Cloud / Gmail OAuth2
    ID_CLIENT: str = ""
    KEY_CLIENT: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/gmail/callback"
    GMAIL_TOKEN_PATH: str = str(
        Path(__file__).resolve().parents[2] / "storage" / "private" / "gmail_token.json"
    )
    GMAIL_OAUTH_DB_PATH: Path = (
        Path(__file__).resolve().parents[2] / "storage" / "private" / "gmail_oauth.sqlite3"
    )
    GOOGLE_DRIVE_FOLDER_NAME: str = "CurriculoAI_Gerados"

    # Supabase
    SUPABASE_URL: str = "http://127.0.0.1:54321"
    SUPABASE_KEY: str = ""

    # Arquivos persistentes fora do PostgreSQL.
    CURRICULOS_DIR: Path = Path(__file__).resolve().parents[2] / "storage" / "curriculos"
    GUARDRAIL_SOURCE_PATH: Path = (
        Path(__file__).resolve().parents[2] / "storage" / "private" / "estrutura_curriculo.json"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
