# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[inputs]`: the run input limits come from the person's own `vibey.toml` only (SP-LOOPS Phase
3, Task 3; ADR-0018 for the keys, ADR-0101 for whose file grants). The trust rule is pure: the
tables come through `TrustedTableReaderInterface`, here an in-memory fake, and once through the
real reader over files in pytest's temporary folder."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from vibey.application.dto import TrustedRunInputsSettings
from vibey.application.interfaces.run_inputs_settings_interface import (
    RunInputsSettingsLoaderInterface,
)
from vibey.application.run_inputs_settings import RunInputsSettings, RunInputsSettingsLoader
from vibey.domain.config import ConfigError
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader

USER = Path("/home/person/.config/vibey/vibey.toml")
PROJECT = Path("/work/repo/vibey.toml")


class FakeTables:
    """The port, in memory: a path maps to its `[inputs]` table, or is absent."""

    def __init__(self, tables: Mapping[Path, Mapping[str, Any]], *, same: bool = False) -> None:
        self._tables = tables
        self._same = same

    def read_table(self, path: Path, table: str) -> Mapping[str, object] | None:
        assert table == "inputs"
        return self._tables.get(path)

    def same_file(self, first: Path, second: Path) -> bool:
        return self._same or first == second


def _load(
    mine: Mapping[str, Any] | None = None,
    project: Mapping[str, Any] | None = None,
    *,
    project_path: Path | None = PROJECT,
    same: bool = False,
) -> TrustedRunInputsSettings:
    tables: dict[Path, Mapping[str, Any]] = {}
    if mine is not None:
        tables[USER] = mine
    if project is not None:
        tables[PROJECT] = project
    return RunInputsSettingsLoader(FakeTables(tables, same=same)).load(USER, project_path)


def test_the_defaults_are_one_mib_eight_mib_and_sixty_four_items() -> None:
    settings = RunInputsSettings()
    assert settings.max_item_bytes == 1_048_576
    assert settings.max_project_bytes == 8_388_608
    assert settings.max_items == 64
    assert settings.max_prompt_bytes == 65_536


def test_from_table_reads_each_key() -> None:
    settings = RunInputsSettings.from_table(
        {"max_item_bytes": 10, "max_project_bytes": 20, "max_items": 3, "max_prompt_bytes": 7}
    )
    assert settings == RunInputsSettings(
        max_item_bytes=10, max_project_bytes=20, max_items=3, max_prompt_bytes=7
    )


def test_an_empty_table_is_the_defaults() -> None:
    assert RunInputsSettings.from_table({}) == RunInputsSettings()


@pytest.mark.parametrize("value", [0, -1, "1", 1.5, True, None])
@pytest.mark.parametrize(
    "key", ["max_item_bytes", "max_project_bytes", "max_items", "max_prompt_bytes"]
)
def test_a_value_that_is_not_a_positive_integer_is_refused(key: str, value: object) -> None:
    with pytest.raises(ValueError, match=key):
        RunInputsSettings.from_table({key: value})


def test_an_item_limit_over_the_project_limit_is_refused() -> None:
    with pytest.raises(ValueError, match="max_item_bytes"):
        RunInputsSettings.from_table({"max_item_bytes": 10, "max_project_bytes": 5})


def test_an_unknown_key_is_refused_rather_than_ignored() -> None:
    with pytest.raises(ValueError, match="max_item_byte"):
        RunInputsSettings.from_table({"max_item_byte": 10})


def test_no_user_file_is_the_defaults_with_no_notice() -> None:
    loaded = _load(project_path=None)
    assert loaded == TrustedRunInputsSettings(RunInputsSettings(), ())


def test_the_persons_own_table_sets_the_limits() -> None:
    loaded = _load({"max_items": 5}, project_path=None)
    assert loaded.settings.max_items == 5
    assert loaded.notices == ()


def test_a_bad_value_in_the_persons_own_file_is_a_config_error_naming_it() -> None:
    with pytest.raises(ConfigError) as caught:
        _load({"max_item_bytes": 0})
    assert str(USER) in str(caught.value)


def test_a_project_inputs_table_is_ignored_with_one_notice() -> None:
    loaded = _load(project={"max_item_bytes": 999_999_999, "max_items": 9999})
    assert loaded.settings == RunInputsSettings()
    assert len(loaded.notices) == 1
    assert str(PROJECT) in loaded.notices[0]
    assert "[inputs]" in loaded.notices[0]
    assert str(USER) in loaded.notices[0]


def test_a_project_file_with_no_inputs_table_says_nothing() -> None:
    assert _load(project={}).notices == ()


def test_a_project_path_with_no_file_says_nothing() -> None:
    assert _load().notices == ()


def test_the_persons_own_file_opened_as_a_project_is_not_a_project() -> None:
    loaded = _load({"max_items": 7}, project={"max_items": 1}, same=True)
    assert loaded.settings.max_items == 7
    assert loaded.notices == ()


def test_the_real_reader_over_a_project_folder_file(tmp_path: Path) -> None:
    user = tmp_path / "config" / "vibey.toml"
    user.parent.mkdir()
    user.write_text("[inputs]\nmax_items = 4\n")
    project = tmp_path / "repo" / "vibey.toml"
    project.parent.mkdir()
    project.write_text("[inputs]\nmax_item_bytes = 999999999\n")
    loaded = RunInputsSettingsLoader(TomlTrustedTableReader()).load(user, project)
    assert loaded.settings == RunInputsSettings(max_items=4)
    assert len(loaded.notices) == 1


def test_the_loader_meets_its_interface() -> None:
    assert isinstance(RunInputsSettingsLoader(FakeTables({})), RunInputsSettingsLoaderInterface)
