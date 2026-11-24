import json

from crewai import Crew, Process

from app.crew.agents import (
    create_chatbot,
    create_escritor,
    create_manager,
    create_pesquisador,
    create_verificador,
)
from app.crew.flow import CurriculoFlow, extract_safe_draft
from app.crew.tasks import (
    create_atendimento_candidato_task,
    create_desenvolver_curriculo_task,
    create_pesquisar_vagas_task,
    create_verificar_curriculo_task,
    create_verificar_vagas_task,
)
from app.schemas.resume import ResumeData
from app.services.document_service import generate_and_save_resume
from app.services.guardrail_service import (
    CONTACT_FIELDS,
    LOCAL_CONTACT,
    GuardrailViolation,
    issue,
    minimize_message,
    professional_context,
    restore_local_contacts,
    verify_resume,
)


def build_curriculo_crew(
    user_message: str,
    current_resume: ResumeData | None = None,
) -> Crew:
    """Monta a Crew hierárquica com Manager, Pesquisador, Escritor, Verificador e Chatbot."""
    user_message = minimize_message(user_message)
    if current_resume:
        verify_resume(current_resume)
        current_resume = current_resume.model_copy(deep=True)
        for field in CONTACT_FIELDS:
            setattr(current_resume.candidate, field, LOCAL_CONTACT)
    pesquisador = create_pesquisador()
    escritor = create_escritor()
    verificador = create_verificador()
    chatbot = create_chatbot()
    manager = create_manager()

    resume_json = (
        json.dumps(current_resume.model_dump(), ensure_ascii=False, indent=2)
        if current_resume
        else "Nenhum currículo carregado."
    )

    resume_json += (
        "\n\nBASE PROFISSIONAL LOCAL REVISADA (única fonte de afirmações):\n"
        + professional_context()
    )
    resume_json += "\n\nContrato JSON obrigatório:\n" + json.dumps(ResumeData.model_json_schema())
    pesquisa_task = create_pesquisar_vagas_task(pesquisador, user_message=user_message)
    verificacao_vagas_task = create_verificar_vagas_task(
        verificador,
        context_tasks=[pesquisa_task],
    )
    escrita_task = create_desenvolver_curriculo_task(
        escritor,
        current_resume_json=resume_json,
        context_tasks=[pesquisa_task, verificacao_vagas_task],
    )
    verificacao_curriculo_task = create_verificar_curriculo_task(
        verificador,
        context_tasks=[pesquisa_task, verificacao_vagas_task, escrita_task],
    )
    chat_task = create_atendimento_candidato_task(
        chatbot,
        user_message=user_message,
        context_tasks=[
            pesquisa_task,
            verificacao_vagas_task,
            escrita_task,
            verificacao_curriculo_task,
        ],
    )

    return Crew(
        agents=[pesquisador, escritor, verificador, chatbot],
        tasks=[
            pesquisa_task,
            verificacao_vagas_task,
            escrita_task,
            verificacao_curriculo_task,
            chat_task,
        ],
        process=Process.hierarchical,
        manager_agent=manager,
        verbose=False,
    )


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return text


def run_multiagent_pipeline(
    user_message: str,
    current_resume: ResumeData | None = None,
) -> tuple[str, ResumeData | None, list[str], dict[str, str] | None]:
    """Executa o fluxo completo dos 5 agentes e normaliza a resposta."""
    crew = build_curriculo_crew(
        user_message=user_message,
        current_resume=current_resume,
    )
    raw_result = _strip_code_fences(str(crew.kickoff()))

    try:
        parsed = json.loads(raw_result)
        if not isinstance(parsed, dict):
            raise ValueError
        updated_raw = parsed.get("updated_resume")
        updated_resume = ResumeData(**updated_raw) if isinstance(updated_raw, dict) else None
        if updated_resume is None:
            return (
                "Nenhum currículo verificado foi produzido. Revise a base local e a solicitação.",
                None,
                [],
                None,
            )
        updated_resume = restore_local_contacts(updated_resume)
        verify_resume(updated_resume)
    except GuardrailViolation:
        raise
    except (ValueError, TypeError) as exc:
        raise GuardrailViolation([issue("invalid_agent_output", "response")]) from exc
    # Não aceitar texto livre nem caminhos de arquivos produzidos pelo modelo.
    _, docx_id = generate_and_save_resume(updated_resume, "docx")
    _, pdf_id = generate_and_save_resume(updated_resume, "pdf")
    return (
        "Currículo verificado contra a base local. Revise o documento antes de enviar.",
        updated_resume,
        [],
        {"docx_id": docx_id, "pdf_id": pdf_id},
    )


def run_flow_pipeline(
    user_message: str,
    current_resume: ResumeData | None = None,
    use_search: bool = True,
) -> tuple[str, ResumeData | None, list[str], dict[str, str] | None]:
    """Executa o workflow CrewAI Flow (@start, @router, @listen) com guardrails."""
    flow = CurriculoFlow()
    result = flow.kickoff(
        inputs={
            "user_message": user_message,
            "current_resume": current_resume,
            "use_search": use_search,
            "search_only": False,
        }
    )
    return (
        result["reply"],
        result["updated_resume"],
        result["sources"],
        result["generated_files"],
    )


def run_chat_flow_detailed(
    user_message: str,
    current_resume: ResumeData | None = None,
    use_search: bool = True,
) -> dict:
    """Executa o workflow CrewAI Flow retornando também rascunho/apontamentos quando bloqueado."""
    flow = CurriculoFlow()
    try:
        return flow.kickoff(
            inputs={
                "user_message": user_message,
                "current_resume": current_resume,
                "use_search": use_search,
                "search_only": False,
            }
        )
    except GuardrailViolation as exc:
        if flow.state.verification_output or flow.state.draft_output:
            safe_draft, ver_issues = extract_safe_draft(
                flow.state.verification_output, flow.state.draft_output
            )
            if safe_draft is not None:
                return {
                    "reply": (
                        "Documento bloqueado na verificação por falta de evidência ou risco de confidencialidade. "
                        "Abra o rascunho para editar e verificar antes de exportar."
                    ),
                    "updated_resume": None,
                    "sources": flow.state.sources,
                    "generated_files": None,
                    "blocked": True,
                    "draft_resume": safe_draft,
                    "verification_issues": ver_issues or exc.issues,
                }
        raise


def run_job_search_flow(user_message: str) -> dict:
    """Executa apenas a etapa de pesquisa e auditoria de vagas no CrewAI Flow."""
    flow = CurriculoFlow()
    result = flow.kickoff(
        inputs={
            "user_message": user_message,
            "current_resume": None,
            "use_search": True,
            "search_only": True,
        }
    )
    return {
        "status": flow.state.status or "PESQUISA_CONCLUIDA",
        "reply": result["reply"],
        "vagas_report": flow.state.vagas_report,
        "vagas_audit": flow.state.vagas_audit,
        "sources": result["sources"],
    }
