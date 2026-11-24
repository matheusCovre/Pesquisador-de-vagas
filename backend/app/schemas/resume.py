from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_max_length=20000)


class CandidateInfo(StrictModel):
    name: str
    headline: str
    email: str
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""


class ExperienceItem(StrictModel):
    role: str
    company: str
    period: str
    location: str = ""
    highlights: list[str] = Field(default_factory=list)


class EducationItem(StrictModel):
    degree: str
    institution: str
    period: str


class ProjectItem(StrictModel):
    title: str
    technologies: list[str] = Field(default_factory=list)
    description: str
    status: str | None = None
    url: str | None = None


class ResumeData(StrictModel):
    id: str = "cv-001"
    title: str
    targetRole: str
    targetCompany: str
    updatedAt: str = ""
    candidate: CandidateInfo
    summary: str
    experiences: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    research: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    resume: ResumeData | None = None
    use_search: bool = True


class ChatResponse(BaseModel):
    reply: str
    updated_resume: ResumeData | None = None
    sources: list[str] = Field(default_factory=list)
    generated_files: dict[str, str] | None = None
    blocked: bool = False
    draft_resume: ResumeData | None = None
    verification_issues: list[dict[str, str]] = Field(default_factory=list)


class ExportRequest(BaseModel):
    format: Literal["pdf", "docx"]
    resume: ResumeData


class SendEmailRequest(BaseModel):
    reviewed_by_user: bool = False
    recipient_name: str = ""
    recipient_email: str
    company: str = ""
    subject: str
    body: str
    format: Literal["pdf", "docx"] = "pdf"
    resume: ResumeData


class JobSearchRequest(BaseModel):
    areas: list[str] = Field(
        default_factory=lambda: [
            "Desenvolvimento de Software",
            "Automações de IA",
            "Automação Industrial",
            "Robótica",
        ]
    )
    custom_query: str = ""
    seniority: str = "Qualquer nível"
    location: str = "Brasil ou vagas internacionais elegíveis para residentes no Brasil"


class JobOpportunity(BaseModel):
    title: str
    company: str = "Não informada"
    url: str = ""
    seniority: str = ""
    modality: str = ""
    salary: str = ""
    eligibility: str = "VERIFICAÇÃO_PENDENTE"
    justification: str = ""


class JobSearchResponse(BaseModel):
    status: str
    query: str
    report: str
    jobs: list[JobOpportunity] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
