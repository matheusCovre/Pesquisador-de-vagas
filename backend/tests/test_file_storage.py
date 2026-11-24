from pathlib import Path
from unittest.mock import patch

import pytest

from app.services.file_storage_service import save_resume_file


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_save_preserves_bytes_and_versions(isolated_settings, file_format):
    first = save_resume_file(b"primeira versao", file_format)
    second = save_resume_file(b"segunda versao", file_format)
    root = isolated_settings.CURRICULOS_DIR
    assert first != second
    assert (root / first).read_bytes() == b"primeira versao"
    assert (root / second).read_bytes() == b"segunda versao"
    assert Path(first).parts[0] == "gerados"
    assert Path(first).suffix == f".{file_format}"
    assert (root / first).resolve().is_relative_to(root.resolve())


@pytest.mark.parametrize("file_format", ["txt", "../pdf", "", "PDF"])
def test_rejects_invalid_format_without_writing(isolated_settings, file_format):
    with pytest.raises(ValueError, match="Formato"):
        save_resume_file(b"conteudo", file_format)
    assert not isolated_settings.CURRICULOS_DIR.exists()


def test_collision_does_not_overwrite_or_delete_existing_file(isolated_settings):
    with patch("app.services.file_storage_service.uuid4", return_value="mesmo-id"):
        first = save_resume_file(b"original", "pdf")
        with pytest.raises(FileExistsError):
            save_resume_file(b"substituto", "pdf")
    assert (isolated_settings.CURRICULOS_DIR / first).read_bytes() == b"original"


def test_disk_failure_removes_incomplete_file(isolated_settings):
    original_open = Path.open

    class FailingFile:
        def __init__(self, file):
            self.file = file

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.file.close()

        def write(self, data):
            self.file.write(data[:2])
            raise OSError("Disco cheio")

    def failing_open(path, mode="r", *args, **kwargs):
        file = original_open(path, mode, *args, **kwargs)
        return FailingFile(file) if mode == "xb" else file

    with patch.object(Path, "open", failing_open), pytest.raises(OSError, match="Disco cheio"):
        save_resume_file(b"conteudo completo", "pdf")
    assert not list(isolated_settings.CURRICULOS_DIR.rglob("*.pdf"))
