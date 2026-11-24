from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import supabase_service


def test_missing_credentials_fail_before_creating_client():
    with patch.object(supabase_service, "create_client") as create:
        with pytest.raises(RuntimeError, match="não configurados"):
            supabase_service.get_supabase_client()
    create.assert_not_called()


def test_unknown_model_does_not_create_company_or_job():
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = SimpleNamespace(
        data=[]
    )
    with (
        patch.object(supabase_service, "get_supabase_client", return_value=client),
        patch.object(supabase_service, "get_or_create_empresa") as company,
        pytest.raises(ValueError, match="não encontrado"),
    ):
        supabase_service.register_candidatura_flow("Teste", "Python", "inexistente", "modelo-teste")
    company.assert_not_called()


def test_existing_company_is_reused():
    client = MagicMock()
    query = client.table.return_value
    company = {"id": "empresa-existente", "nome": "Teste"}
    query.select.return_value.ilike.return_value.limit.return_value.execute.return_value = (
        SimpleNamespace(data=[company])
    )
    with patch.object(supabase_service, "get_supabase_client", return_value=client):
        result = supabase_service.get_or_create_empresa("Teste")
    assert result == company
    query.insert.assert_not_called()
