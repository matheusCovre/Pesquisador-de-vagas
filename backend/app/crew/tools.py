import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from tavily import TavilyClient

from app.config import get_settings
from app.schemas.resume import ResumeData
from app.services.document_service import generate_and_save_resume
from app.services.guardrail_service import assert_safe_search_query, restore_local_contacts


class TavilySearchInput(BaseModel):
    query: str = Field(..., description="Termo de busca sobre vaga, empresa ou requisitos.")
    max_results: int = Field(default=5, description="Quantidade máxima de resultados.")


class TavilySearchTool(BaseTool):
    name: str = "pesquisa_tavily"
    description: str = "Pesquisa na web via Tavily API informações sobre empresas, vagas, tecnologias e requisitos."
    args_schema: type[BaseModel] = TavilySearchInput

    def _run(self, query: str, max_results: int = 5) -> str:
        assert_safe_search_query(query)
        settings = get_settings()
        if not settings.TAVILY_API_KEY:
            return json.dumps({"error": "TAVILY_API_KEY não configurada."})

        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results)
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")[:500],
            }
            for item in response.get("results", [])
        ]
        return json.dumps({"results": results}, ensure_ascii=False)


class ResumeToolInput(BaseModel):
    resume_json: str = Field(
        ...,
        description="JSON válido no formato ResumeData (title, targetRole, targetCompany, candidate, summary, experiences, education, skills, languages).",
    )


class GenerateWordTool(BaseTool):
    name: str = "gerar_curriculo_word"
    description: str = "Gera e salva o currículo em formato Word (.docx) a partir de um JSON ResumeData e retorna o file_id."
    args_schema: type[BaseModel] = ResumeToolInput

    def _run(self, resume_json: str) -> str:
        data = json.loads(resume_json)
        resume = restore_local_contacts(ResumeData(**data))
        _, file_id = generate_and_save_resume(resume, "docx")
        return json.dumps({"format": "docx", "file_id": file_id}, ensure_ascii=False)


class GeneratePdfTool(BaseTool):
    name: str = "gerar_curriculo_pdf"
    description: str = "Gera e salva o currículo em formato PDF (.pdf) a partir de um JSON ResumeData e retorna o file_id."
    args_schema: type[BaseModel] = ResumeToolInput

    def _run(self, resume_json: str) -> str:
        data = json.loads(resume_json)
        resume = restore_local_contacts(ResumeData(**data))
        _, file_id = generate_and_save_resume(resume, "pdf")
        return json.dumps({"format": "pdf", "file_id": file_id}, ensure_ascii=False)
