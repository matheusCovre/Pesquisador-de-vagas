from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.config import get_settings


def save_resume_file(content: bytes, file_format: Literal["docx", "pdf"]) -> str:
    """Salva o arquivo e retorna o identificador relativo à pasta de currículos."""
    if file_format not in {"docx", "pdf"}:
        raise ValueError("Formato de currículo inválido.")
    relative_path = (
        Path("gerados") / datetime.now(UTC).strftime("%Y/%m/%d") / f"{uuid4()}.{file_format}"
    )
    destination = get_settings().CURRICULOS_DIR / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    file = destination.open("xb")
    try:
        with file:
            destination.chmod(0o600)
            file.write(content)
    except OSError:
        # Não deixar arquivos incompletos após uma falha de gravação.
        destination.unlink(missing_ok=True)
        raise
    return relative_path.as_posix()
