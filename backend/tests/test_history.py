from unittest.mock import patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.routers import history


@pytest.mark.parametrize(
    "status",
    [
        "enviado_sem_resposta",
        "enviado_com_resposta",
        "confirmacao",
        "entrevista",
        "rejeicao",
        "aprovacao",
        "cancelamento",
    ],
)
def test_supported_status_is_accepted(status):
    assert history.AtualizarStatusRequest(status_novo=status).status_novo == status


def test_unknown_status_is_rejected():
    with pytest.raises(ValidationError):
        history.AtualizarStatusRequest(status_novo="invalido")


def test_missing_candidatura_returns_404():
    with patch.object(history, "update_candidatura_status", return_value={}):
        with pytest.raises(HTTPException) as exc:
            history.patch_candidatura_status(
                "ausente", history.AtualizarStatusRequest(status_novo="entrevista")
            )
    assert exc.value.status_code == 404


def test_status_update_returns_updated_record():
    updated = {"id": "candidatura-teste", "status_atual": "entrevista"}
    with patch.object(history, "update_candidatura_status", return_value=updated) as update:
        result = history.patch_candidatura_status(
            "candidatura-teste", history.AtualizarStatusRequest(status_novo="entrevista")
        )
    assert result == updated
    update.assert_called_once_with("candidatura-teste", "entrevista")


def test_database_failure_is_not_returned_as_empty_history():
    with patch.object(history, "list_candidaturas", side_effect=RuntimeError("Banco indisponível")):
        with pytest.raises(HTTPException) as exc:
            history.get_history()
    assert exc.value.status_code == 500


def test_unknown_model_returns_400():
    payload = history.RegistrarCandidaturaRequest(empresa_nome="Teste", vaga_titulo="Python")
    with patch.object(
        history, "register_candidatura_flow", side_effect=ValueError("Modelo ausente")
    ):
        with pytest.raises(HTTPException) as exc:
            history.create_candidatura_record(payload)
    assert exc.value.status_code == 400
