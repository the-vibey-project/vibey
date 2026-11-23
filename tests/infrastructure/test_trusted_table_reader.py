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


def _self_symlink(path: Path) -> Path:
    try:
        path.symlink_to(path)
    except (OSError, NotImplementedError):  # pragma: no cover - only where links cannot be made
        pytest.skip("this operating system cannot create a symlink here")
    return path


def test_a_file_that_is_a_symlink_to_itself_is_a_config_error(tmp_path: Path) -> None:
    loop = _self_symlink(tmp_path / "vibey.toml")
    with pytest.raises(ConfigError, match="cannot be read") as caught:
        TomlTrustedTableReader().read_table(loop, "loops")
    assert caught.value.path == str(loop)


def test_a_symlink_loop_is_never_the_same_file(tmp_path: Path) -> None:
    loop = _self_symlink(tmp_path / "vibey.toml")
    real = _write(tmp_path / "mine.toml", "")
    assert not TomlTrustedTableReader().same_file(loop, real)
    assert not TomlTrustedTableReader().same_file(real, loop)


@pytest.mark.parametrize(
    "nesting",
    [
        pytest.param("x = " + "[" * 600 + "]" * 600, id="arrays"),
        pytest.param("x = " + "{a=" * 600 + "1" + "}" * 600, id="inline-tables"),
    ],
)
def test_deep_nesting_is_a_config_error_not_a_recursion_error(tmp_path: Path, nesting: str) -> None:
    path = _write(tmp_path / "vibey.toml", nesting + "\n")
    with pytest.raises(ConfigError, match="nested too deeply"):
        TomlTrustedTableReader().read_table(path, "loops")


def test_a_path_under_a_file_is_no_file(tmp_path: Path) -> None:
    plain = _write(tmp_path / "plain", "")
    assert TomlTrustedTableReader().read_table(plain / "vibey.toml", "loops") is None


def test_a_folder_that_cannot_be_searched_is_a_config_error(tmp_path: Path) -> None:
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("permissions do not bind the superuser")
    folder = tmp_path / "locked"
    folder.mkdir()
    path = _write(folder / "vibey.toml", "[loops]\n")
    folder.chmod(0o000)
    try:
        try:
            os.stat(path)
        except PermissionError:
            pass
        else:  # pragma: no cover - only on a file system that ignores modes
            pytest.skip("this file system does not enforce folder permissions")
        with pytest.raises(ConfigError, match="cannot be read") as caught:
            TomlTrustedTableReader().read_table(path, "loops")
        assert caught.value.path == str(path)
    finally:
        folder.chmod(0o700)
