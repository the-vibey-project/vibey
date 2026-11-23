# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading one table of a trusted-config `vibey.toml` from disk: the I/O half of ADR-0101's
two-file rule, kept out of the application layer (SP-LOOPS Task 3 review)."""

import os
from pathlib import Path

import pytest

from vibey.application.interfaces.trusted_table_reader_interface import (
    TrustedTableReaderInterface,
)
from vibey.domain.config import ConfigError
from vibey.infrastructure.trusted_table_reader import (
    MAX_CONFIG_BYTES,
    TomlTrustedTableReader,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_a_missing_file_is_none(tmp_path: Path) -> None:
    assert TomlTrustedTableReader().read_table(tmp_path / "absent.toml", "loops") is None
    assert isinstance(TomlTrustedTableReader(), TrustedTableReaderInterface)


def test_a_file_without_the_table_is_an_empty_table(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", '[project]\nname = "x"\n')
    assert TomlTrustedTableReader().read_table(path, "loops") == {}


def test_the_table_is_returned(tmp_path: Path) -> None:
    path = _write(tmp_path / "vibey.toml", '[loops]\nskills = ["a"]\n')
    assert TomlTrustedTableReader().read_table(path, "loops") == {"skills": ["a"]}


@pytest.mark.parametrize(
    ("text", "reason"),
    [("loops = 3\n", r"\[loops\] must be a table"), ("[loops\n", "is not valid TOML")],
)
def test_an_unreadable_table_is_a_config_error(tmp_path: Path, text: str, reason: str) -> None:
    path = _write(tmp_path / "vibey.toml", text)
    with pytest.raises(ConfigError, match=reason) as caught:
        TomlTrustedTableReader().read_table(path, "loops")
    assert caught.value.path == str(path)


def test_bytes_that_are_not_utf8_are_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    path.write_bytes(b"[loops]\nskills = ['\xff']\n")
    with pytest.raises(ConfigError, match="is not valid TOML"):
        TomlTrustedTableReader().read_table(path, "loops")


def test_an_oversized_file_is_a_config_error(tmp_path: Path) -> None:
    path = tmp_path / "vibey.toml"
    path.write_bytes(b"#" * (MAX_CONFIG_BYTES + 1))
    with pytest.raises(ConfigError, match=f"larger than {MAX_CONFIG_BYTES} bytes"):
        TomlTrustedTableReader().read_table(path, "loops")


def test_a_folder_is_refused_as_not_a_regular_file(tmp_path: Path) -> None:
    folder = tmp_path / "vibey.toml"
    folder.mkdir()
    with pytest.raises(ConfigError, match="not a regular file"):
        TomlTrustedTableReader().read_table(folder, "loops")


def test_a_fifo_is_refused_without_hanging(tmp_path: Path) -> None:
    fifo = tmp_path / "vibey.toml"
    os.mkfifo(fifo)
    with pytest.raises(ConfigError, match="not a regular file"):
        TomlTrustedTableReader().read_table(fifo, "loops")


def test_a_file_that_cannot_be_opened_is_a_config_error(tmp_path: Path) -> None:
    def refuse(path: Path) -> int:
        raise PermissionError("denied")

    path = _write(tmp_path / "vibey.toml", "[loops]\n")
    with pytest.raises(ConfigError, match="cannot be read: denied"):
        TomlTrustedTableReader(opener=refuse).read_table(path, "loops")


def test_a_symlinked_config_is_followed(tmp_path: Path) -> None:
    real = _write(tmp_path / "dotfiles.toml", '[loops]\nskills = ["a"]\n')
    link = tmp_path / "vibey.toml"
    link.symlink_to(real)
    assert TomlTrustedTableReader().read_table(link, "loops") == {"skills": ["a"]}


def test_same_file_compares_resolved_paths(tmp_path: Path) -> None:
    real = _write(tmp_path / "vibey.toml", "")
    link = tmp_path / "link.toml"
    link.symlink_to(real)
    reader = TomlTrustedTableReader()
    assert reader.same_file(link, real)
    assert reader.same_file(tmp_path / "x" / ".." / "vibey.toml", real)
    assert not reader.same_file(tmp_path / "other.toml", real)
