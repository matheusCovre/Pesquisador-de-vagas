import base64
import hashlib
import json
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.gmail import router
from app.services import gmail_service, oauth_state_service
from app.services.oauth_state_service import SESSION_COOKIE, consume_attempt


@pytest.fixture
def oauth_settings(isolated_settings):
    isolated_settings.ID_CLIENT = "cliente-de-teste.apps.googleusercontent.com"
    isolated_settings.KEY_CLIENT = "segredo-ficticio"
    return isolated_settings


def start(binding="navegador-teste"):
    url = gmail_service.create_auth_url(binding)
    return parse_qs(urlsplit(url).query)


def test_callback_restores_original_pkce_verifier_and_state(oauth_settings):
    query = start()
    state = query["state"][0]
    fake_flow = MagicMock()
    fake_flow.credentials.to_json.return_value = '{"token":"token-ficticio"}'
    with patch.object(gmail_service.Flow, "from_client_config", return_value=fake_flow) as factory:
        gmail_service.exchange_code_for_token("codigo-ficticio", state, "navegador-teste")
    verifier = factory.call_args.kwargs["code_verifier"]
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    assert query["code_challenge"] == [challenge]
    assert query["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in query
    assert factory.call_args.kwargs["state"] == state
    assert factory.call_args.kwargs["autogenerate_code_verifier"] is False
    fake_flow.fetch_token.assert_called_once_with(code="codigo-ficticio", code_verifier=verifier)
    token = Path(oauth_settings.GMAIL_TOKEN_PATH)
    assert json.loads(token.read_text())["token"] == "token-ficticio"
    assert token.stat().st_mode & 0o777 == 0o600
    assert oauth_settings.GMAIL_OAUTH_DB_PATH.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        consume_attempt(state, "navegador-teste")


@pytest.mark.parametrize(
    "state,browser", [("", "navegador-teste"), ("invalido", "navegador-teste"), ("invalido", "")]
)
def test_missing_or_unknown_state_never_calls_google(oauth_settings, state, browser):
    with patch.object(gmail_service.Flow, "from_client_config") as factory:
        with pytest.raises(ValueError):
            gmail_service.exchange_code_for_token("codigo", state, browser)
    factory.assert_not_called()


def test_browser_mismatch_does_not_consume_legitimate_login(oauth_settings):
    state = start()["state"][0]
    with pytest.raises(ValueError):
        consume_attempt(state, "outro-navegador")
    assert consume_attempt(state, "navegador-teste")


def test_expired_attempt_is_deleted(oauth_settings):
    state = start()["state"][0]
    with patch.object(oauth_state_service.time, "time", return_value=time.time() + 601):
        with pytest.raises(ValueError):
            consume_attempt(state, "navegador-teste")
    with sqlite3.connect(oauth_settings.GMAIL_OAUTH_DB_PATH) as connection:
        assert connection.execute("select count(*) from pending_oauth").fetchone()[0] == 0


def test_parallel_tabs_have_independent_verifiers(oauth_settings):
    first, second = start(), start()
    assert first["state"] != second["state"]
    assert consume_attempt(first["state"][0], "navegador-teste") != consume_attempt(
        second["state"][0], "navegador-teste"
    )


def test_only_one_concurrent_callback_can_consume_attempt(oauth_settings):
    state = start()["state"][0]

    def consume():
        try:
            consume_attempt(state, "navegador-teste")
            return "ok"
        except ValueError:
            return "blocked"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: consume(), range(2))) == ["blocked", "ok"]


def test_google_failure_still_consumes_attempt(oauth_settings):
    state = start()["state"][0]
    fake_flow = MagicMock()
    fake_flow.fetch_token.side_effect = RuntimeError("Falha simulada")
    with patch.object(gmail_service.Flow, "from_client_config", return_value=fake_flow):
        with pytest.raises(RuntimeError):
            gmail_service.exchange_code_for_token("codigo", state, "navegador-teste")
    with pytest.raises(ValueError):
        consume_attempt(state, "navegador-teste")
    assert not Path(oauth_settings.GMAIL_TOKEN_PATH).exists()


def test_callback_rejects_changed_redirect_uri(oauth_settings):
    state = start()["state"][0]
    oauth_settings.GOOGLE_REDIRECT_URI = "http://localhost:9999/api/gmail/callback"
    with pytest.raises(ValueError):
        consume_attempt(state, "navegador-teste")


@pytest.fixture
def client(oauth_settings):
    app = FastAPI()
    app.include_router(router)
    with TestClient(app, base_url="http://localhost:8000", follow_redirects=False) as client:
        yield client


def test_http_login_cookie_and_callback_round_trip(client, oauth_settings):
    entry = client.get("/api/gmail/auth-url").json()["auth_url"]
    assert entry == "http://localhost:8000/api/gmail/auth"
    response = client.get(entry)
    assert response.status_code == 307
    cookie_header = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie_header
        and "SameSite=lax" in cookie_header
        and "Max-Age=600" in cookie_header
    )
    assert "Secure" not in cookie_header  # HTTP apenas no ambiente local.
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    flow = MagicMock()
    flow.credentials.to_json.return_value = '{"token":"ficticio"}'
    with patch.object(gmail_service.Flow, "from_client_config", return_value=flow):
        callback = client.get("/api/gmail/callback", params={"code": "codigo", "state": state})
    assert callback.status_code == 307
    assert "gmail=connected" in callback.headers["location"]
    assert callback.headers["Referrer-Policy"] == "no-referrer"
    assert (
        client.get("/api/gmail/callback", params={"code": "codigo", "state": state}).status_code
        == 400
    )


def test_auth_start_uses_callback_hostname(client):
    response = client.get("http://127.0.0.1:8000/api/gmail/auth")
    assert response.status_code == 307
    assert response.headers["location"] == "http://localhost:8000/api/gmail/auth"
    assert "set-cookie" not in response.headers


def test_denied_consent_consumes_pending_login(client):
    response = client.get("/api/gmail/auth")
    state = parse_qs(urlsplit(response.headers["location"]).query)["state"][0]
    binding = client.cookies.get(SESSION_COOKIE)
    with patch.object(gmail_service.Flow, "from_client_config") as factory:
        denied = client.get(
            "/api/gmail/callback", params={"error": "access_denied", "state": state}
        )
    assert denied.status_code == 400
    factory.assert_not_called()
    with pytest.raises(ValueError):
        consume_attempt(state, binding)


def test_callback_error_does_not_expose_provider_details(client):
    with patch(
        "app.routers.gmail.exchange_code_for_token", side_effect=RuntimeError("segredo-do-provedor")
    ):
        response = client.get(
            "/api/gmail/callback", params={"code": "segredo", "state": "qualquer"}
        )
    assert response.status_code == 400
    assert "segredo" not in response.text
