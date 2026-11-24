"""Política local conservadora: evidências vêm do servidor, nunca da saída da IA."""

import hashlib
import json
import logging
import re
import unicodedata

from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.schemas.resume import ResumeData

LOGGER = logging.getLogger(__name__)
LOCAL_CONTACT = "[DADO_LOCAL]"
CONTACT_FIELDS = ("name", "email", "phone", "location", "linkedin", "github")
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class SourceCandidate(BaseModel):
    name: str = Field(min_length=1)
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""


class SourceSkill(BaseModel):
    category: str
    description: str


class SourceExperience(BaseModel):
    company: str
    role: str
    period: str
    location: str | None = None
    highlights: list[str]


class SourceProject(BaseModel):
    id: str = ""
    title: str
    technologies: list[str] = Field(default_factory=list)
    status: str | None = None
    description: str
    url: str | None = None


class SourceResearch(BaseModel):
    description: str


class SourceVariant(BaseModel):
    id: str = ""
    title: str = ""
    headline: str
    summary: str
    skills: list[SourceSkill]
    experiences: list[SourceExperience]
    projects: list[SourceProject] = Field(default_factory=list)
    selectedProjectIds: list[str] = Field(default_factory=list)
    research: list[SourceResearch] = Field(default_factory=list)


class SourceEducation(BaseModel):
    degree: str
    institution: str
    campus: str = ""
    period: str = ""
    displayText: str = ""


class SourceLanguage(BaseModel):
    name: str
    level: str
    notes: str | None = None


class ApprovedSource(BaseModel):
    candidate: SourceCandidate
    variants: list[SourceVariant] = Field(min_length=1)
    education: list[SourceEducation]
    languages: list[SourceLanguage]
    layout: dict = Field(default_factory=dict)
    adaptationRules: dict = Field(default_factory=dict)


class GuardrailViolation(ValueError):
    def __init__(self, issues: list[dict[str, str]]):
        self.issues = issues
        # Não registrar nem devolver o texto bloqueado, dados pessoais ou segredos.
        LOGGER.warning("guardrail_blocked codes=%s", sorted({i["code"] for i in issues}))
        super().__init__(
            "Conteúdo bloqueado. Revise os campos indicados com base nas fontes locais."
        )


def issue(code: str, field: str) -> dict[str, str]:
    return {"code": code, "field": field}


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def load_approved_source() -> dict:
    try:
        raw = get_settings().GUARDRAIL_SOURCE_PATH.read_text(encoding="utf-8")
        return ApprovedSource.model_validate_json(raw).model_dump()
    except (OSError, ValueError, ValidationError, TypeError) as exc:
        raise GuardrailViolation([issue("approved_source_unavailable", "source")]) from exc


def source_fingerprint(source: dict) -> str:
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def privacy_issues(
    text: str, allowed_emails: tuple[str, ...] = (), allowed_phones: tuple[str, ...] = ()
) -> list[dict[str, str]]:
    rules = {
        "personal_document": r"\b\d{3}\.?\d{3}\.?\d{3}[-\s]?\d{2}\b|\b(?:CPF|RG|CNH|passaporte)\s*[:=]\s*\S+",
        "credential": r"\bsk-[A-Za-z0-9_-]{12,}|-----BEGIN .*PRIVATE KEY-----|\b(?:api[_ -]?key|password|senha|token|client_secret)\s*[:=]\s*\S+",
        "internal_endpoint": r"https?://[^\s]*(?:\.internal\b|\.local\b)|\b(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b",
        "sensitive_personal_data": r"\b(?:diagn[oó]stico m[eé]dico|meu tipo sangu[ií]neo|minha religi[aã]o|minha orienta[cç][aã]o sexual|filia[cç][aã]o sindical|data de nascimento|endere[cç]o residencial)\b",
        "confidential_detail": r"\b(?:cliente|projeto|arquitetura|m[eé]trica|processo|c[oó]digo)\s+(?:intern[oa]s?|confidencia[il]s?|propriet[aá]ri[oa]s?)\b",
    }
    findings = [
        issue(code, "content") for code, pattern in rules.items() if re.search(pattern, text, re.I)
    ]
    allowed = {normalized(email) for email in allowed_emails}
    emails = re.findall(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    if any(normalized(email) not in allowed for email in emails):
        findings.append(issue("unapproved_personal_contact", "content"))
    phone_text = text
    for phone in allowed_phones:
        if phone:
            phone_text = phone_text.replace(phone, "")
    if re.search(r"(?:\+55\s*)?\(?\d{2}\)?[\s.-]+\d{4,5}[\s-]?\d{4}\b", phone_text):
        findings.append(issue("unapproved_phone", "content"))
    return findings


def assert_private_text(
    text: str, allowed_emails: tuple[str, ...] = (), allowed_phones: tuple[str, ...] = ()
) -> None:
    findings = privacy_issues(text, allowed_emails, allowed_phones)
    if findings:
        raise GuardrailViolation(findings)


def verify_resume(resume: ResumeData) -> dict:
    source = load_approved_source()
    candidate = source["candidate"]
    findings = privacy_issues(
        resume.model_dump_json(), (candidate.get("email", ""),), (candidate.get("phone", ""),)
    )

    def approved(value: str, choices: list[str], field: str) -> None:
        if normalized(value) not in {normalized(str(choice)) for choice in choices}:
            findings.append(issue("unsupported_claim", field))

    for field in CONTACT_FIELDS:
        approved(
            getattr(resume.candidate, field),
            [candidate.get(field, ""), *([""] if field != "name" else [])],
            f"candidate.{field}",
        )
    variants = source["variants"]
    approved(resume.candidate.headline, [v["headline"] for v in variants], "candidate.headline")
    approved(resume.summary, [v["summary"] for v in variants], "summary")
    skills = []
    for variant in variants:
        for skill in variant["skills"]:
            skills.extend([skill["description"], f"{skill['category']}: {skill['description']}"])
            # Preservar qualificadores como "SQL (fundamentos)" e "WBC (estudos...)".
            skills.extend(part.strip().rstrip(".") for part in skill["description"].split(","))
    for index, skill in enumerate(resume.skills):
        approved(skill, skills, f"skills.{index}")
    for index, experience in enumerate(resume.experiences):
        choices = [
            e
            for v in variants
            for e in v["experiences"]
            if all(
                normalized(getattr(experience, key)) == normalized(e.get(key) or "")
                for key in ("company", "role", "period", "location")
            )
        ]
        if not choices:
            findings.append(issue("unsupported_experience", f"experiences.{index}"))
        for number, highlight in enumerate(experience.highlights):
            approved(
                highlight,
                [h for e in choices for h in e["highlights"]],
                f"experiences.{index}.highlights.{number}",
            )
    for index, education in enumerate(resume.education):
        if not any(
            normalized(education.degree) == normalized(e["degree"])
            and normalized(education.institution)
            in {
                normalized(e["institution"]),
                normalized(f"{e['institution']}, Câmpus {e.get('campus', '')}"),
            }
            and normalized(education.period)
            in {
                normalized(e.get("period", "")),
                normalized(e.get("displayText", "").split(" | ")[-1]),
            }
            for e in source["education"]
        ):
            findings.append(issue("unsupported_education", f"education.{index}"))
    languages = [
        value
        for language in source["languages"]
        for value in (
            f"{language['name']} ({language['level']})",
            f"{language['name']} {language['level']}",
            f"{language['name']} ({language['level']}) — {language.get('notes') or ''}",
        )
    ]
    for index, language in enumerate(resume.languages):
        approved(language, languages, f"languages.{index}")
    max_projects = int(source.get("layout", {}).get("projectSelection", {}).get("max", 3) or 3)
    if len(resume.projects) > max_projects:
        findings.append(issue("too_many_projects", "projects"))
    approved_projects = [p for v in variants for p in v.get("projects", [])]
    for index, project in enumerate(resume.projects):
        if not any(
            normalized(project.title) == normalized(p["title"])
            and normalized(project.description) == normalized(p["description"])
            and normalized(project.status or "") == normalized(p.get("status") or "")
            and normalized(project.url or "") == normalized(p.get("url") or "")
            and {normalized(t) for t in project.technologies}.issubset(
                {normalized(t) for t in p.get("technologies", [])}
            )
            for p in approved_projects
        ):
            findings.append(issue("unsupported_project", f"projects.{index}"))
    research_choices = [r["description"] for v in variants for r in v.get("research", [])]
    for index, item in enumerate(resume.research):
        approved(item, research_choices, f"research.{index}")
    if findings:
        raise GuardrailViolation(findings)
    return {
        "status": "approved",
        "policy": "approved-facts-v1",
        "source_sha256": source_fingerprint(source),
    }


def restore_local_contacts(resume: ResumeData) -> ResumeData:
    """Somente placeholders do prompt são substituídos; alterações da IA são verificadas."""
    candidate = load_approved_source()["candidate"]
    result = resume.model_copy(deep=True)
    for field in CONTACT_FIELDS:
        if getattr(result.candidate, field) == LOCAL_CONTACT:
            setattr(result.candidate, field, candidate.get(field, ""))
    return result


def professional_context() -> str:
    source = load_approved_source()
    # Não enviar identidade, contato, nomes de arquivos ou notas privadas ao provedor.
    variant_keys = (
        "id",
        "title",
        "headline",
        "summary",
        "skills",
        "experiences",
        "projects",
        "selectedProjectIds",
        "research",
    )
    variants = [
        {key: variant[key] for key in variant_keys if key in variant}
        for variant in source["variants"]
    ]
    payload = {
        "variants": variants,
        "education": source["education"],
        "languages": source["languages"],
    }
    if source.get("layout"):
        payload["layout"] = source["layout"]
    if source.get("adaptationRules"):
        payload["adaptationRules"] = source["adaptationRules"]
    return json.dumps(payload, ensure_ascii=False)


def minimize_message(message: str) -> str:
    candidate = load_approved_source()["candidate"]
    for field in CONTACT_FIELDS:
        value = candidate.get(field, "")
        if value:
            message = re.sub(re.escape(value), LOCAL_CONTACT, message, flags=re.I)
    assert_private_text(message)
    return message


def assert_safe_search_query(query: str) -> None:
    # Pesquisas na web não precisam de dados de identificação do candidato.
    candidate = load_approved_source()["candidate"]
    assert_private_text(query)
    if any(
        value and normalized(value) in normalized(query)
        for key in CONTACT_FIELDS
        if (value := candidate.get(key, ""))
    ):
        raise GuardrailViolation([issue("personal_data_in_search", "query")])
