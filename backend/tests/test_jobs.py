from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.crew import crew_runner, flow
from app.services.job_search_service import parse_jobs_from_report
from main import app

client = TestClient(app)


def _mock_task(output: str = "") -> MagicMock:
    task = MagicMock()
    task.output = output
    return task


def test_flow_search_only_skips_writer_and_returns_audit(isolated_settings):
    vagas_crew = MagicMock()
    vagas_crew.kickoff.return_value = (
        "Classificação: ELEGÍVEL\n"
        "- Estágio em Automação Industrial & Robótica: https://example.com/vaga-robotica"
    )

    with (
        patch.object(flow, "create_pesquisador", return_value=MagicMock()),
        patch.object(flow, "create_verificador", return_value=MagicMock()),
        patch.object(
            flow,
            "create_pesquisar_vagas_task",
            return_value=_mock_task("Relatório inicial"),
        ),
        patch.object(flow, "create_verificar_vagas_task", return_value=_mock_task()),
        patch.object(flow, "create_escritor") as mock_esc,
        patch.object(flow, "Crew", return_value=vagas_crew),
    ):
        result = crew_runner.run_job_search_flow("Desenvolvimento de Software e Robótica")

    mock_esc.assert_not_called()
    assert result["status"] == "PESQUISA_CONCLUIDA"
    assert "https://example.com/vaga-robotica" in result["sources"]
    assert "ELEGÍVEL" in result["vagas_audit"]
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_parse_jobs_from_report_handles_json_block_and_fallback():
    report = (
        "Auditoria concluída.\n"
        "```json\n"
        '{"vagas": [{"title": "Dev Python & Automações de IA Jr", '
        '"company": "TechFlow", "url": "https://techflow.example/jobs/1", '
        '"seniority": "Júnior", "modality": "Remoto Brasil", '
        '"salary": "R$ 5.000", "eligibility": "ELEGÍVEL", '
        '"justification": "Aceita graduação em andamento."}]}\n'
        "```"
    )
    jobs = parse_jobs_from_report(report)
    assert len(jobs) == 1
    assert jobs[0].title == "Dev Python & Automações de IA Jr"
    assert jobs[0].company == "TechFlow"
    assert jobs[0].eligibility == "ELEGÍVEL"

    assert parse_jobs_from_report("Texto livre sem JSON.") == []


def test_jobs_search_endpoint_uses_default_focused_areas(isolated_settings):
    captured = {}

    def _fake_flow(prompt: str):
        captured["prompt"] = prompt
        return {
            "status": "PESQUISA_CONCLUIDA",
            "reply": "ELEGÍVEL",
            "vagas_report": "",
            "vagas_audit": (
                "```json\n"
                '{"vagas": [{"title": "Engenharia de Automação Industrial Jr", '
                '"company": "RoboLab", "url": "https://robolab.example/vaga", '
                '"eligibility": "ELEGÍVEL"}]}\n'
                "```"
            ),
            "sources": ["https://robolab.example/vaga"],
        }

    with patch("app.services.job_search_service.run_job_search_flow", side_effect=_fake_flow):
        res = client.post("/api/jobs/search", json={})

    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "PESQUISA_CONCLUIDA"
    assert len(body["jobs"]) == 1
    assert body["jobs"][0]["title"] == "Engenharia de Automação Industrial Jr"
    assert "Desenvolvimento de Software" in captured["prompt"]
    assert "Automações de IA" in captured["prompt"]
    assert "Automação Industrial" in captured["prompt"]
    assert "Robótica" in captured["prompt"]


def test_jobs_search_endpoint_blocks_personal_data_in_query(isolated_settings):
    res = client.post(
        "/api/jobs/search",
        json={"custom_query": "CPF 123.456.789-00 vaga python"},
    )
    assert res.status_code == 422
    assert res.json()["issues"][0]["code"] == "personal_document"
