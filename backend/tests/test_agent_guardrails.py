import json
from unittest.mock import MagicMock, patch

import pytest

from app.crew import crew_runner
from app.crew.tools import GeneratePdfTool, GenerateWordTool
from app.services.guardrail_service import GuardrailViolation


@pytest.mark.parametrize("tool_class", [GenerateWordTool, GeneratePdfTool])
def test_direct_tool_call_cannot_bypass_validation(resume, isolated_settings, tool_class):
    resume.summary = "Inventei uma experiência sênior."
    with pytest.raises(GuardrailViolation):
        tool_class()._run(resume.model_dump_json())
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_untrusted_current_resume_is_blocked_before_agent_creation(resume):
    resume.summary = "Trabalho em um projeto interno sem autorização."
    with patch.object(crew_runner, "create_pesquisador") as create:
        with pytest.raises(GuardrailViolation):
            crew_runner.build_curriculo_crew("Adaptar para Python", resume)
    create.assert_not_called()


def test_invalid_agent_output_is_not_returned_raw(isolated_settings):
    crew = MagicMock()
    raw = "conteúdo inesperado com segredo-nao-real"
    crew.kickoff.return_value = raw
    with patch.object(crew_runner, "build_curriculo_crew", return_value=crew):
        with pytest.raises(GuardrailViolation) as exc:
            crew_runner.run_multiagent_pipeline("Teste")
    assert raw not in str(exc.value)
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_plausible_but_unverified_agent_output_cannot_generate(resume, isolated_settings):
    resume.skills.append("Certificação não comprovada")
    crew = MagicMock()
    crew.kickoff.return_value = json.dumps(
        {"reply": "Aprovado!", "updated_resume": resume.model_dump()}
    )
    with patch.object(crew_runner, "build_curriculo_crew", return_value=crew):
        with pytest.raises(GuardrailViolation):
            crew_runner.run_multiagent_pipeline("Teste")
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_agent_cannot_fabricate_reply_or_document_paths(resume, isolated_settings):
    crew = MagicMock()
    crew.kickoff.return_value = json.dumps(
        {
            "reply": "Detalhes secretos do cliente que não podem ser divulgados.",
            "updated_resume": resume.model_dump(),
            "generated_files": {"pdf_id": "../../arquivo-confidencial.pdf"},
            "sources": ["http://intranet.internal/segredo"],
        }
    )
    with patch.object(crew_runner, "build_curriculo_crew", return_value=crew):
        reply, updated, sources, files = crew_runner.run_multiagent_pipeline("Teste")
    assert "Detalhes secretos" not in reply
    assert updated == resume
    assert sources == []
    for file_id in files.values():
        path = isolated_settings.CURRICULOS_DIR / file_id
        assert path.is_file()
        assert path.resolve().is_relative_to(isolated_settings.CURRICULOS_DIR.resolve())
