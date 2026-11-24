from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.schemas.resume import (
    CandidateInfo,
    EducationItem,
    ExperienceItem,
    ExportRequest,
    ProjectItem,
    ResumeData,
)
from app.services.document_service import (
    extract_text_from_docx,
    extract_text_from_pdf,
    generate_and_save_resume,
)
from app.services.guardrail_service import (
    MAX_UPLOAD_BYTES,
    GuardrailViolation,
    load_approved_source,
    verify_resume,
)
from app.services.upload_guardrail_service import verify_upload

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/starter", response_model=ResumeData)
def get_starter_resume():
    """Retorna o currículo inicial aprovado a partir da base local."""
    source = load_approved_source()
    candidate = source["candidate"]
    variant = source["variants"][0]
    project_map = {p["id"]: p for p in variant.get("projects", []) if p.get("id")}
    selected_ids = variant.get("selectedProjectIds") or []
    selected_projects = (
        [project_map[pid] for pid in selected_ids if pid in project_map]
        if selected_ids
        else variant.get("projects", [])[:3]
    )
    return ResumeData(
        id="cv-base-01",
        title=variant.get("title") or variant["headline"],
        targetRole="Oportunidade em análise",
        targetCompany="Base local revisada",
        candidate=CandidateInfo(
            name=candidate["name"],
            headline=variant["headline"],
            email=candidate.get("email", ""),
            phone=candidate.get("phone", ""),
            location=candidate.get("location", ""),
            linkedin=candidate.get("linkedin", ""),
            github=candidate.get("github", ""),
        ),
        summary=variant["summary"],
        experiences=[
            ExperienceItem(
                role=exp["role"],
                company=exp["company"],
                period=exp["period"],
                location=exp.get("location") or "",
                highlights=exp["highlights"],
            )
            for exp in variant["experiences"]
        ],
        projects=[
            ProjectItem(
                title=proj["title"],
                technologies=proj.get("technologies", []),
                description=proj["description"],
                status=proj.get("status"),
                url=proj.get("url"),
            )
            for proj in selected_projects
        ],
        education=[
            EducationItem(
                degree=edu["degree"],
                institution=edu["institution"],
                period=edu.get("period") or edu.get("displayText", "").split(" | ")[-1],
            )
            for edu in source["education"]
        ],
        research=[item["description"] for item in variant.get("research", [])],
        skills=[f"{skill['category']}: {skill['description']}" for skill in variant["skills"]],
        languages=[f"{lang['name']} ({lang['level']})" for lang in source["languages"]],
    )


@router.post("/verify")
def verify_resume_document(payload: ResumeData):
    try:
        return {**verify_resume(payload), "issues": []}
    except GuardrailViolation as exc:
        return {"status": "blocked", "issues": exc.issues}


@router.post("/export")
def export_resume(payload: ExportRequest):
    content, file_id = generate_and_save_resume(payload.resume, payload.format)
    if payload.format == "pdf":
        return Response(
            content=content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="curriculo.pdf"',
                "X-Document-Id": file_id,
            },
        )

    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": 'attachment; filename="curriculo.docx"',
            "X-Document-Id": file_id,
        },
    )


@router.post("/parse")
async def parse_resume_file(file: UploadFile = File(...)):
    raw = await file.read(MAX_UPLOAD_BYTES + 1)
    filename = (file.filename or "").lower()

    if filename.endswith(".pdf"):
        verify_upload(raw, "pdf")
        text = extract_text_from_pdf(raw)
    elif filename.endswith(".docx"):
        verify_upload(raw, "docx")
        text = extract_text_from_docx(raw)
    else:
        raise HTTPException(status_code=400, detail="Formato não suportado. Envie .pdf ou .docx.")

    return {"filename": file.filename, "text": text, "trusted": False, "requires_review": True}
