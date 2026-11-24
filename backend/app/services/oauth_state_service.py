"""Tentativas OAuth locais com consumo atômico, expiração e vínculo ao navegador."""

import hashlib
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager

from app.config import get_settings

OAUTH_TTL_SECONDS = 600
SESSION_COOKIE = "gmail_oauth_browser"
INVALID_ATTEMPT = "Login expirado ou inválido. Inicie uma nova conexão com o Gmail."


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def _database():
    path = get_settings().GMAIL_OAUTH_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Criar com permissão restrita antes de escrever qualquer verificador.
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY, 0o600)
    os.close(descriptor)
    path.chmod(0o600)
    connection = sqlite3.connect(path, timeout=10)
    try:
        connection.execute("""create table if not exists pending_oauth (
            state_hash text primary key, browser_hash text not null,
            verifier text not null, expires_at real not null,
            redirect_uri text not null, client_id text not null
        )""")
        connection.commit()
        yield connection
    finally:
        connection.close()


def save_attempt(state: str, browser_binding: str, verifier: str) -> None:
    if not browser_binding:
        raise ValueError(INVALID_ATTEMPT)
    settings = get_settings()
    with _database() as connection, connection:
        connection.execute("delete from pending_oauth where expires_at <= ?", (time.time(),))
        connection.execute(
            "insert into pending_oauth values (?, ?, ?, ?, ?, ?)",
            (
                _digest(state),
                _digest(browser_binding),
                verifier,
                time.time() + OAUTH_TTL_SECONDS,
                settings.GOOGLE_REDIRECT_URI,
                settings.ID_CLIENT,
            ),
        )


def consume_attempt(state: str, browser_binding: str) -> str:
    if not state or not browser_binding or len(state) > 256 or len(browser_binding) > 256:
        raise ValueError(INVALID_ATTEMPT)
    settings = get_settings()
    with _database() as connection, connection:
        connection.execute("begin immediate")
        row = connection.execute(
            "select browser_hash, verifier, expires_at, redirect_uri, client_id from pending_oauth where state_hash = ?",
            (_digest(state),),
        ).fetchone()
        if row is None or not secrets.compare_digest(row[0], _digest(browser_binding)):
            raise ValueError(INVALID_ATTEMPT)
        # Consumir antes da chamada de rede, inclusive em falhas do provedor.
        connection.execute("delete from pending_oauth where state_hash = ?", (_digest(state),))
        connection.commit()
        if row[2] <= time.time() or row[3:] != (settings.GOOGLE_REDIRECT_URI, settings.ID_CLIENT):
            raise ValueError(INVALID_ATTEMPT)
        return row[1]
