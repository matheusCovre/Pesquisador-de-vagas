import json
import os
import re

os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from crewai import Crew, Process  # noqa: E402
from crewai.flow.flow import Flow, listen, or_, router, start  # noqa: E402
from pydantic import BaseModel, Field, ValidationError  # noqa: E402

from app.crew.agents import (  # noqa: E402
    create_chatbot,
    create_escritor,
    create_pesquisador,
    create_verificador,
)
from app.crew.tasks import (  # noqa: E402
    create_atendimento_candidato_task,
    create_desenvolver_curriculo_task,
    create_pesquisar_vagas_task,
    create_verificar_curriculo_task,
    create_verificar_vagas_task,
)
from app.schemas.resume import ResumeData  # noqa: E402
from app.services.document_service import generate_and_save_resume  # noqa: E402
from app.services.guardrail_service import (  # noqa: E402
    CONTACT_FIELDS,
    LOCAL_CONTACT,
    GuardrailViolation,
    issue,
    load_approved_source,
    minimize_message,
    privacy_issues,
    professional_context,
    restore_local_contacts,
    verify_resume,
)

SEARCH_KEYWORDS = (
    "vaga",
    "vagas",
    "oportunidade",
    "oportunidades",
    "pesquisar",
    "buscar",
    "procurar",
    "estágio",
    "estagio",
    "trainee",
    "júnior",
    "junior",
)

EDIT_KEYWORDS = (
    "adaptar",
    "adapte",
    "atualizar",
    "atualize",
    "melhorar",
    "melhore",
    "reescrever",
    "gerar currículo",
    "gerar curriculo",
    "estruturar",
)


class CurriculoFlowState(BaseModel):
    user_message: str = ""
    sanitized_message: str = ""
    current_resume: ResumeData | None = None
    resume_context: str = ""
    use_search: bool = True
    search_only: bool = False
    vagas_report: str = ""
    vagas_audit: str = ""
    draft_output: str = ""
    verification_output: str = ""
    guardrail_feedback: str = ""
    revision_count: int = 0
    max_revisions: int = 1
    status: str = ""
    reply: str = ""
    updated_resume: ResumeData | None = None
    blocked: bool = False
    draft_resume: ResumeData | None = None
    verification_issues: list[dict[str, str]] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    generated_files: dict[str, str] | None = None


def _extract_urls(text: str) -> list[str]:
    if not text:
        return []
    seen: list[str] = []
    for raw_url in re.findall(r"https?://[^\s\)\]\>\"']+", text):
        cleaned = raw_url.rstrip(".,;:")
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    return text


def _extract_resume_from_text(raw: str) -> ResumeData | None:
    if not raw:
        return None
    candidates = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.I)
    candidates.append(_strip_code_fences(raw))
    first_brace = raw.find("{")
    last_brace = raw.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        candidates.append(raw[first_brace : last_brace + 1])

    for item in candidates:
        try:
            parsed = json.loads(item)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        candidate_obj = parsed.get("updated_resume", parsed)
        if not isinstance(candidate_obj, dict):
            continue
        try:
            return ResumeData.model_validate(candidate_obj)
        except (ValidationError, ValueError, TypeError):
            continue
    return None


def extract_safe_draft(
    raw_ver: str, raw_draft: str
) -> tuple[ResumeData | None, list[dict[str, str]]]:
    """Extrai rascunho apenas se não houver vazamento de PII/segredos, retornando os apontamentos."""
    parsed = _extract_resume_from_text(raw_ver) or _extract_resume_from_text(raw_draft)
    if parsed is None:
        return None, []
    restored = restore_local_contacts(parsed)
    candidate = load_approved_source()["candidate"]
    p_issues = privacy_issues(
        restored.model_dump_json(), (candidate.get("email", ""),), (candidate.get("phone", ""),)
    )
    if p_issues:
        return None, p_issues
    try:
        verify_resume(restored)
        return restored, []
    except GuardrailViolation as exc:
        return restored, exc.issues


class CurriculoFlow(Flow[CurriculoFlowState]):
    """Workflow CrewAI com @start, @router e @listen para orquestrar os agentes."""

    @start()
    def preparar_contexto(self) -> str:
        self.state.sanitized_message = minimize_message(self.state.user_message)

        masked_resume: ResumeData | None = None
        if self.state.current_resume is not None:
            verify_resume(self.state.current_resume)
            masked_resume = self.state.current_resume.model_copy(deep=True)
            for field in CONTACT_FIELDS:
                setattr(masked_resume.candidate, field, LOCAL_CONTACT)

        resume_json = (
            json.dumps(masked_resume.model_dump(), ensure_ascii=False, indent=2)
            if masked_resume
            else "Nenhum currículo carregado."
        )
        self.state.resume_context = (
            resume_json
            + "\n\nBASE PROFISSIONAL LOCAL REVISADA (única fonte de afirmações):\n"
            + professional_context()
            + "\n\nContrato JSON obrigatório:\n"
            + json.dumps(ResumeData.model_json_schema())
        )
        return "contexto_pronto"

    @router(preparar_contexto)
    def rotear_intencao(self) -> str:
        if self.state.search_only:
            return "pesquisar_e_escrever"
        msg = self.state.sanitized_message.casefold()
        wants_search = self.state.use_search and any(kw in msg for kw in SEARCH_KEYWORDS)
        if wants_search:
            return "pesquisar_e_escrever"
        if any(kw in msg for kw in EDIT_KEYWORDS):
            return "escrever_sem_pesquisa"
        return "apenas_chat"

    @listen("pesquisar_e_escrever")
    def pesquisar_e_verificar_vagas(self) -> str:
        pesquisador = create_pesquisador()
        verificador = create_verificador()

        pesquisa_task = create_pesquisar_vagas_task(
            pesquisador,
            user_message=self.state.sanitized_message,
        )
        auditoria_vagas_task = create_verificar_vagas_task(
            verificador,
            context_tasks=[pesquisa_task],
        )

        crew = Crew(
            agents=[pesquisador, verificador],
            tasks=[pesquisa_task, auditoria_vagas_task],
            process=Process.sequential,
            verbose=False,
        )
        result = str(crew.kickoff())
        self.state.vagas_report = str(getattr(pesquisa_task, "output", "") or "")
        self.state.vagas_audit = result
        return result

    @router(pesquisar_e_verificar_vagas)
    def avaliar_vagas(self) -> str:
        audit_upper = self.state.vagas_audit.upper()
        if "INELEGÍVEL" in audit_upper and "ELEGÍVEL" not in audit_upper.replace("INELEGÍVEL", ""):
            self.state.status = "SEM_VAGAS"
            return "sem_vagas_elegiveis"
        if self.state.search_only:
            self.state.status = "PESQUISA_CONCLUIDA"
            return "pesquisa_concluida"
        return "vagas_elegiveis"

    @listen(or_("vagas_elegiveis", "escrever_sem_pesquisa", "revisar_curriculo"))
    def desenvolver_e_verificar_curriculo(self) -> str:
        escritor = create_escritor()
        verificador = create_verificador()

        extra_context = self.state.resume_context
        if self.state.vagas_audit:
            extra_context += f"\n\nAuditoria de vagas:\n{self.state.vagas_audit}"
        if self.state.revision_count > 0 and (
            self.state.guardrail_feedback or self.state.verification_output
        ):
            extra_context += f"\n\nSolicitação de revisão #{self.state.revision_count}:"
            if self.state.guardrail_feedback:
                extra_context += f"\n[GUARDRAIL] {self.state.guardrail_feedback}"
            if self.state.verification_output:
                extra_context += f"\n{self.state.verification_output}"

        escrita_task = create_desenvolver_curriculo_task(
            escritor,
            current_resume_json=extra_context,
        )
        verificacao_task = create_verificar_curriculo_task(
            verificador,
            context_tasks=[escrita_task],
        )

        crew = Crew(
            agents=[escritor, verificador],
            tasks=[escrita_task, verificacao_task],
            process=Process.sequential,
            verbose=False,
        )
        result = str(crew.kickoff())
        self.state.draft_output = str(getattr(escrita_task, "output", "") or "")
        self.state.verification_output = result
        return result

    @router(desenvolver_e_verificar_curriculo)
    def avaliar_curriculo(self) -> str:
        ver_upper = self.state.verification_output.upper()
        if "BLOQUEADO" in ver_upper and "APROVADO_PARA_REVISAO_HUMANA" not in ver_upper:
            if self.state.revision_count < self.state.max_revisions:
                self.state.guardrail_feedback = (
                    "O verificador bloqueou a versão anterior. Remova qualquer afirmação sem "
                    "evidência ou dado sensível e utilize apenas fatos literais da base local."
                )
                self.state.revision_count += 1
                return "revisar_curriculo"
            self.state.status = "BLOQUEADO"
            return "bloqueado"

        if (
            any(tag in ver_upper for tag in ("REVISAR", "CORRIGIR"))
            and self.state.revision_count < self.state.max_revisions
        ):
            self.state.guardrail_feedback = ""
            self.state.revision_count += 1
            return "revisar_curriculo"

        parsed_resume = _extract_resume_from_text(
            self.state.verification_output
        ) or _extract_resume_from_text(self.state.draft_output)

        if parsed_resume is None:
            if self.state.revision_count < self.state.max_revisions:
                self.state.guardrail_feedback = (
                    "A saída anterior não trouxe um JSON ResumeData válido. "
                    "Entregue o currículo no contrato JSON obrigatório usando apenas fatos da base local."
                )
                self.state.revision_count += 1
                return "revisar_curriculo"
            raise GuardrailViolation([issue("invalid_agent_output", "response")])

        restored = restore_local_contacts(parsed_resume)
        try:
            verify_resume(restored)
        except GuardrailViolation as exc:
            if self.state.revision_count < self.state.max_revisions:
                fields_desc = ", ".join(f"{i['code']} ({i['field']})" for i in exc.issues)
                self.state.guardrail_feedback = (
                    f"Bloqueio pelos guardrails nos campos: {fields_desc}. "
                    "Corrija usando exclusivamente textos literais da BASE PROFISSIONAL LOCAL REVISADA."
                )
                self.state.revision_count += 1
                return "revisar_curriculo"
            raise

        _, docx_id = generate_and_save_resume(restored, "docx")
        _, pdf_id = generate_and_save_resume(restored, "pdf")

        self.state.updated_resume = restored
        self.state.generated_files = {"docx_id": docx_id, "pdf_id": pdf_id}
        self.state.status = "APROVADO_PARA_REVISAO_HUMANA"
        return "aprovado"

    @listen(
        or_("apenas_chat", "sem_vagas_elegiveis", "bloqueado", "aprovado", "pesquisa_concluida")
    )
    def finalizar_atendimento(self) -> dict:
        self.state.sources = _extract_urls(f"{self.state.vagas_audit}\n{self.state.vagas_report}")

        if self.state.status == "APROVADO_PARA_REVISAO_HUMANA":
            self.state.reply = (
                "Currículo verificado contra a base local. Revise o documento antes de enviar."
            )
        elif self.state.status == "PESQUISA_CONCLUIDA":
            self.state.updated_resume = None
            self.state.generated_files = None
            self.state.reply = (
                self.state.vagas_audit.strip()
                or self.state.vagas_report.strip()
                or "Pesquisa concluída sem oportunidades retornadas."
            )
        elif self.state.status == "BLOQUEADO":
            self.state.blocked = True
            self.state.updated_resume = None
            self.state.generated_files = None
            safe_draft, ver_issues = extract_safe_draft(
                self.state.verification_output, self.state.draft_output
            )
            self.state.draft_resume = safe_draft
            self.state.verification_issues = ver_issues
            self.state.reply = "Documento bloqueado na verificação por falta de evidência ou risco de confidencialidade."
        elif self.state.status == "SEM_VAGAS":
            self.state.updated_resume = None
            self.state.generated_files = None
            self.state.reply = (
                "Nenhuma vaga elegível foi aprovada na auditoria para gerar currículo."
            )
        else:
            chatbot = create_chatbot()
            chat_task = create_atendimento_candidato_task(
                chatbot,
                user_message=self.state.sanitized_message,
            )
            crew = Crew(
                agents=[chatbot],
                tasks=[chat_task],
                process=Process.sequential,
                verbose=False,
            )
            crew.kickoff()
            self.state.status = "CHAT"
            self.state.updated_resume = None
            self.state.generated_files = None
            self.state.reply = (
                "Atendimento concluído sem alterações no currículo. "
                "Informe uma vaga ou peça para pesquisar/adaptar o documento."
            )

        return {
            "reply": self.state.reply,
            "updated_resume": self.state.updated_resume,
            "sources": self.state.sources,
            "generated_files": self.state.generated_files,
            "blocked": self.state.blocked,
            "draft_resume": self.state.draft_resume,
            "verification_issues": self.state.verification_issues,
        }
