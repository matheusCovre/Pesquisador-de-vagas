import json
import re

from app.crew.crew_runner import run_job_search_flow
from app.schemas.resume import JobOpportunity, JobSearchRequest, JobSearchResponse
from app.services.guardrail_service import assert_safe_search_query, minimize_message

DEFAULT_JOB_AREAS = [
    "Desenvolvimento de Software",
    "Automações de IA",
    "Automação Industrial",
    "Robótica",
]


def build_job_search_prompt(payload: JobSearchRequest) -> str:
    """Constrói e sanitiza o prompt de pesquisa focado nas áreas técnicas do candidato."""
    areas = [a.strip() for a in payload.areas if a.strip()] or DEFAULT_JOB_AREAS
    custom = minimize_message(payload.custom_query.strip()) if payload.custom_query else ""
    seniority = minimize_message(payload.seniority.strip() or "Qualquer nível")
    location = minimize_message(
        payload.location.strip()
        or "Brasil ou vagas internacionais elegíveis para residentes no Brasil"
    )

    assert_safe_search_query(" ".join([*areas, custom, seniority, location]))

    lines = [
        "Pesquisar vagas recentes e abertas focadas nas seguintes áreas:",
        ", ".join(areas) + ".",
        f"Nível / Senioridade: {seniority}.",
        f"Modalidade / Localidade: {location}.",
    ]
    if custom:
        lines.append(f"Critérios adicionais / palavras-chave: {custom}.")

    lines.append(
        "Ao final do relatório auditado, inclua quando possível um bloco JSON no formato "
        '{"vagas": [{"title": "...", "company": "...", "url": "https://...", '
        '"seniority": "...", "modality": "...", "salary": "...", '
        '"eligibility": "ELEGÍVEL|INELEGÍVEL|VERIFICAÇÃO_PENDENTE", "justification": "..."}]} '
        "contendo apenas vagas verificadas com URL real encontrada na pesquisa."
    )
    return "\n".join(lines)


def _extract_json_vagas(text: str) -> list[dict]:
    """Extrai objetos de vagas caso o agente inclua bloco JSON no relatório."""
    if not text:
        return []
    candidates: list[str] = re.findall(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.I)
    candidates.append(text.strip())

    for raw in candidates:
        try:
            parsed = json.loads(raw)
        except ValueError:
            continue
        if isinstance(parsed, dict) and isinstance(parsed.get("vagas"), list):
            return [item for item in parsed["vagas"] if isinstance(item, dict)]
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return []


def parse_jobs_from_report(report: str) -> list[JobOpportunity]:
    """Converte o bloco JSON estruturado do relatório em modelos JobOpportunity."""
    jobs: list[JobOpportunity] = []
    for item in _extract_json_vagas(report):
        title = str(item.get("title") or item.get("cargo") or "").strip()
        if not title:
            continue
        jobs.append(
            JobOpportunity(
                title=title,
                company=str(item.get("company") or item.get("empresa") or "Não informada").strip(),
                url=str(item.get("url") or "").strip(),
                seniority=str(item.get("seniority") or item.get("senioridade") or "").strip(),
                modality=str(item.get("modality") or item.get("modalidade") or "").strip(),
                salary=str(item.get("salary") or item.get("remuneracao") or "").strip(),
                eligibility=str(
                    item.get("eligibility") or item.get("elegibilidade") or "VERIFICAÇÃO_PENDENTE"
                ).strip(),
                justification=str(
                    item.get("justification") or item.get("justificativa") or ""
                ).strip(),
            )
        )
    return jobs


def search_focused_jobs(payload: JobSearchRequest) -> JobSearchResponse:
    """Orquestra a pesquisa e auditoria de vagas sem gerar currículo automaticamente."""
    search_prompt = build_job_search_prompt(payload)
    flow_result = run_job_search_flow(search_prompt)
    report = flow_result.get("vagas_audit") or flow_result.get("reply") or ""
    jobs = parse_jobs_from_report(report)
    return JobSearchResponse(
        status=flow_result.get("status", "PESQUISA_CONCLUIDA"),
        query=search_prompt,
        report=report,
        jobs=jobs,
        sources=flow_result.get("sources") or [],
    )
