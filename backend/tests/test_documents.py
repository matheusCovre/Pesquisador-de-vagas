import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest
from fastapi import HTTPException, UploadFile

from app.routers.documents import export_resume, get_starter_resume, parse_resume_file
from app.schemas.resume import ExportRequest, ProjectItem
from app.services.document_service import (
    extract_text_from_docx,
    extract_text_from_pdf,
    generate_and_save_resume,
)
from app.services.guardrail_service import GuardrailViolation, professional_context, verify_resume


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_export_returns_saved_readable_document(resume, isolated_settings, file_format):
    response = export_resume(ExportRequest(format=file_format, resume=resume))
    assert response.status_code == 200
    file_id = response.headers["X-Document-Id"]
    assert (isolated_settings.CURRICULOS_DIR / file_id).read_bytes() == response.body
    assert f'filename="curriculo.{file_format}"' in response.headers["Content-Disposition"]
    extract = extract_text_from_pdf if file_format == "pdf" else extract_text_from_docx
    text = extract(response.body)
    for expected in [resume.candidate.name, resume.summary, "Integração de APIs.", "FastAPI"]:
        assert expected in text


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_uploaded_document_can_be_parsed(resume, file_format):
    content, _ = generate_and_save_resume(resume, file_format)
    file = UploadFile(filename=f"CURRICULO.{file_format.upper()}", file=BytesIO(content))
    result = asyncio.run(parse_resume_file(file))
    assert result["filename"] == file.filename
    assert resume.candidate.name in result["text"]


def test_unsupported_upload_returns_400():
    file = UploadFile(filename="curriculo.txt", file=BytesIO(b"texto"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(parse_resume_file(file))
    assert exc.value.status_code == 400


def test_invalid_generation_format_does_not_write(resume, isolated_settings):
    with pytest.raises(ValueError):
        generate_and_save_resume(resume, "txt")
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_export_propagates_storage_error(resume):
    with (
        patch("app.services.document_service.save_resume_file", side_effect=OSError("Disco cheio")),
        pytest.raises(OSError, match="Disco cheio"),
    ):
        export_resume(ExportRequest(format="pdf", resume=resume))


def test_starter_resume_passes_verification():
    starter = get_starter_resume()
    response = export_resume(ExportRequest(format="pdf", resume=starter))
    assert response.status_code == 200


@pytest.fixture
def example_starter(isolated_settings):
    database_dir = Path(__file__).resolve().parents[2] / "database"
    isolated_settings.GUARDRAIL_SOURCE_PATH = database_dir / "estrutura_curriculo.example.json"
    return get_starter_resume()


def test_example_renders_one_page_with_projects_and_research(example_starter):
    starter = example_starter
    assert len(starter.projects) == 3
    assert len(starter.research) >= 1

    pdf_res = export_resume(ExportRequest(format="pdf", resume=starter))
    docx_res = export_resume(ExportRequest(format="docx", resume=starter))
    assert pdf_res.status_code == 200
    assert docx_res.status_code == 200

    with pymupdf.open(stream=pdf_res.body, filetype="pdf") as pdf_doc:
        assert len(pdf_doc) == 1

    pdf_text = extract_text_from_pdf(pdf_res.body)
    docx_text = extract_text_from_docx(docx_res.body)
    for text in (pdf_text, docx_text):
        assert "PROJETOS SELECIONADOS" in text
        assert "PESQUISA E APRESENTAÇÕES" in text
        assert starter.projects[0].title in text

    ctx = professional_context()
    assert starter.projects[0].title in ctx
    assert starter.research[0] in ctx
    assert starter.candidate.email not in ctx


def test_unapproved_project_or_research_is_blocked(example_starter):
    starter = example_starter
    invented_project = starter.model_copy(deep=True)
    invented_project.projects[0].description = "Projeto inventado sem comprovação na base."
    with pytest.raises(GuardrailViolation) as exc:
        verify_resume(invented_project)
    assert exc.value.issues[0]["code"] == "unsupported_project"

    too_many = starter.model_copy(deep=True)
    too_many.projects.append(ProjectItem.model_validate(starter.projects[0].model_dump()))
    with pytest.raises(GuardrailViolation) as exc_many:
        verify_resume(too_many)
    assert exc_many.value.issues[0]["code"] == "too_many_projects"

    invented_research = starter.model_copy(deep=True)
    invented_research.research.append("Artigo publicado na NeurIPS 2026.")
    with pytest.raises(GuardrailViolation) as exc_res:
        verify_resume(invented_research)
    assert exc_res.value.issues[0]["code"] == "unsupported_claim"
    assert exc_res.value.issues[0]["field"] == "research.1"
