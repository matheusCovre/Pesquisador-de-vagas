import json
from unittest.mock import MagicMock, patch

import pytest

from app.crew import crew_runner, flow
from app.services.guardrail_service import GuardrailViolation


def _mock_task(output: str = "") -> MagicMock:
    task = MagicMock()
    task.output = output
    return task


def test_flow_routes_simple_chat_without_search_or_writer(isolated_settings):
    crew_instance = MagicMock()
    crew_instance.kickoff.return_value = "Resposta livre ignorada"

    with (
        patch.object(flow, "create_chatbot", return_value=MagicMock()),
        patch.object(flow, "create_atendimento_candidato_task", return_value=_mock_task()),
        patch.object(flow, "create_pesquisador") as mock_pesq,
        patch.object(flow, "create_escritor") as mock_esc,
        patch.object(flow, "Crew", return_value=crew_instance),
    ):
        reply, updated, sources, files = crew_runner.run_flow_pipeline(
            "Qual o status das minhas candidaturas?",
            use_search=True,
        )

    mock_pesq.assert_not_called()
    mock_esc.assert_not_called()
    assert updated is None
    assert sources == []
    assert files is None
    assert "Atendimento concluído" in reply
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_flow_routes_edit_without_search_and_generates_files(resume, isolated_settings):
    approved_json = json.dumps({"updated_resume": resume.model_dump()})
    crew_instance = MagicMock()
    crew_instance.kickoff.return_value = approved_json

    with (
        patch.object(flow, "create_pesquisador") as mock_pesq,
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_desenvolver_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", return_value=crew_instance),
    ):
        reply, updated, sources, files = crew_runner.run_flow_pipeline(
            "Adaptar o currículo atual",
            current_resume=resume,
            use_search=True,
        )

    mock_pesq.assert_not_called()
    assert "Currículo verificado" in reply
    assert updated == resume
    assert sources == []
    assert set(files) == {"docx_id", "pdf_id"}
    assert (isolated_settings.CURRICULOS_DIR / files["docx_id"]).is_file()
    assert (isolated_settings.CURRICULOS_DIR / files["pdf_id"]).is_file()


def test_flow_stops_when_all_opportunities_are_ineligible(isolated_settings):
    vagas_crew = MagicMock()
    vagas_crew.kickoff.return_value = "Classificação: INELEGÍVEL (exige sênior)."

    with (
        patch.object(flow, "create_pesquisador", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_pesquisar_vagas_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_vagas_task", return_value=_mock_task()),
        patch.object(flow, "create_escritor") as mock_esc,
        patch.object(flow, "Crew", return_value=vagas_crew),
    ):
        reply, updated, _, files = crew_runner.run_flow_pipeline(
            "Buscar vagas de IA",
            use_search=True,
        )

    mock_esc.assert_not_called()
    assert "Nenhuma vaga elegível" in reply
    assert updated is None
    assert files is None
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_flow_supports_one_revision_before_approval(resume, isolated_settings):
    approved_json = json.dumps({"updated_resume": resume.model_dump()})
    vagas_crew = MagicMock()
    vagas_crew.kickoff.return_value = "Classificação: ELEGÍVEL"
    rev_crew = MagicMock()
    rev_crew.kickoff.return_value = "REVISAR: ajustar ordem das competências."
    ok_crew = MagicMock()
    ok_crew.kickoff.return_value = approved_json

    with (
        patch.object(flow, "create_pesquisador", return_value=MagicMock()),
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_pesquisar_vagas_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_vagas_task", return_value=_mock_task()),
        patch.object(flow, "create_desenvolver_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", side_effect=[vagas_crew, rev_crew, ok_crew]),
    ):
        _, updated, _, files = crew_runner.run_flow_pipeline(
            "Pesquisar vaga Python Jr",
            current_resume=resume,
        )

    assert updated == resume
    assert (isolated_settings.CURRICULOS_DIR / files["pdf_id"]).is_file()


def test_flow_blocks_when_verifier_returns_bloqueado(resume, isolated_settings):
    blocked_crew = MagicMock()
    blocked_crew.kickoff.return_value = "STATUS: BLOQUEADO - risco de confidencialidade."

    with (
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_desenvolver_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", return_value=blocked_crew),
    ):
        reply, updated, _, files = crew_runner.run_flow_pipeline(
            "Adaptar currículo",
            current_resume=resume,
            use_search=False,
        )

    assert "bloqueado" in reply.lower()
    assert updated is None
    assert files is None
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_flow_still_enforces_deterministic_guardrail(resume, isolated_settings):
    tampered = resume.model_copy(deep=True)
    tampered.skills.append("Experiência inventada")
    bad_crew = MagicMock()
    bad_crew.kickoff.return_value = json.dumps({"updated_resume": tampered.model_dump()})

    with (
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_desenvolver_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", return_value=bad_crew),
        pytest.raises(GuardrailViolation),
    ):
        crew_runner.run_flow_pipeline(
            "Adaptar currículo",
            current_resume=resume,
            use_search=False,
        )

    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_flow_requests_editor_revision_on_deterministic_guardrail_block(resume, isolated_settings):
    tampered = resume.model_copy(deep=True)
    tampered.skills.append("Experiência inventada")
    bad_crew = MagicMock()
    bad_crew.kickoff.return_value = json.dumps({"updated_resume": tampered.model_dump()})
    fixed_crew = MagicMock()
    fixed_crew.kickoff.return_value = json.dumps({"updated_resume": resume.model_dump()})

    captured_prompts = []

    def _capture_task(agent, current_resume_json: str, context_tasks=None):
        captured_prompts.append(current_resume_json)
        return _mock_task()

    with (
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_desenvolver_curriculo_task", side_effect=_capture_task),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", side_effect=[bad_crew, fixed_crew]),
    ):
        reply, updated, _, files = crew_runner.run_flow_pipeline(
            "Adaptar currículo",
            current_resume=resume,
            use_search=False,
        )

    assert len(captured_prompts) == 2
    assert "[GUARDRAIL]" in captured_prompts[1]
    assert "unsupported_claim" in captured_prompts[1]
    assert "Currículo verificado" in reply
    assert updated == resume
    assert set(files) == {"docx_id", "pdf_id"}


def test_detailed_chat_returns_safe_draft_when_still_blocked(resume, isolated_settings):
    tampered = resume.model_copy(deep=True)
    tampered.skills.append("Ferramenta sem evidência")
    bad_crew = MagicMock()
    bad_crew.kickoff.return_value = (
        "STATUS: BLOQUEADO\n\n```json\n"
        + json.dumps({"updated_resume": tampered.model_dump()})
        + "\n```"
    )

    with (
        patch.object(flow, "create_escritor", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(flow, "create_desenvolver_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "create_verificar_curriculo_task", return_value=_mock_task()),
        patch.object(flow, "Crew", return_value=bad_crew),
    ):
        result = crew_runner.run_chat_flow_detailed(
            "Adaptar currículo",
            current_resume=resume,
            use_search=False,
        )

    assert result["blocked"] is True
    assert result["updated_resume"] is None
    assert result["generated_files"] is None
    assert result["draft_resume"] == tampered
    assert result["verification_issues"][0]["code"] == "unsupported_claim"
    assert not isolated_settings.CURRICULOS_DIR.exists()
