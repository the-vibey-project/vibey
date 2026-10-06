# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`StateSyncSettingsLoader`: every `VIBEY_STATE_*` setting, its default, and what it refuses."""

from pathlib import Path

import pytest

from vibey.domain.state_sync import TABLES, ConflictRule
from vibey.infrastructure.state.interfaces.settings_interface import (
    StateSyncSettingsInterface,
    StateSyncSettingsLoaderInterface,
)
from vibey.infrastructure.state.settings import StateSyncSettings, StateSyncSettingsLoader


def load(**environ: str) -> StateSyncSettings:
    return StateSyncSettingsLoader().load(environ)


def test_each_satisfies_its_interface() -> None:
    assert isinstance(StateSyncSettings(), StateSyncSettingsInterface)
    assert isinstance(StateSyncSettingsLoader(), StateSyncSettingsLoaderInterface)


def test_the_defaults() -> None:
    assert StateSyncSettings() == StateSyncSettings(
        "", "vibey-state", "state.vibey", "", "", "", (), 5
    )
    assert load(HOME="/home/me") == StateSyncSettings(
        key_file="/home/me/.config/vibey/state.key", tables=TABLES
    )


def test_every_setting_is_read_from_the_environment() -> None:
    loaded = load(
        VIBEY_STATE_REPOSITORY=" o/r ",
        VIBEY_STATE_BRANCH="state/main",
        VIBEY_STATE_PATH="db.sealed",
        VIBEY_STATE_PG_URL="postgresql://sync@db/vibey",
        VIBEY_STATE_KEY=" k ",
        VIBEY_STATE_KEY_FILE="/keys/state.key",
        VIBEY_STATE_ATTEMPTS="9",
        VIBEY_PG_URL="postgresql://app@db/vibey",
        XDG_CONFIG_HOME="/xdg",
    )
    assert loaded == StateSyncSettings(
        repository="o/r",
        branch="state/main",
        path="db.sealed",
        pg_url="postgresql://sync@db/vibey",
        key="k",
        key_file="/keys/state.key",
        tables=TABLES,
        attempts=9,
    )


def test_a_blank_setting_takes_its_default() -> None:
    loaded = load(VIBEY_STATE_BRANCH="  ", VIBEY_STATE_PATH="", VIBEY_STATE_ATTEMPTS=" ")
    assert (loaded.branch, loaded.path, loaded.attempts) == ("vibey-state", "state.vibey", 5)


def test_the_database_falls_back_to_vibey_pg_url() -> None:
    assert load(VIBEY_PG_URL=" postgresql://app@db/vibey ").pg_url == "postgresql://app@db/vibey"
    assert load().pg_url == ""


def test_the_key_file_defaults_under_xdg_config_home() -> None:
    assert load(XDG_CONFIG_HOME="/xdg", HOME="/home/me").key_file == "/xdg/vibey/state.key"
    assert load(XDG_CONFIG_HOME=" ", HOME="/home/me").key_file == (
        "/home/me/.config/vibey/state.key"
    )


def test_with_no_home_the_key_file_is_under_the_users_home() -> None:
    assert load().key_file == str(Path("~").expanduser() / ".config" / "vibey" / "state.key")


@pytest.mark.parametrize(("value", "why"), [("many", "a whole number"), ("1.5", "a whole number")])
def test_attempts_that_are_not_a_whole_number_are_refused(value: str, why: str) -> None:
    with pytest.raises(ValueError, match=f"VIBEY_STATE_ATTEMPTS must be {why}"):
        load(VIBEY_STATE_ATTEMPTS=value)


@pytest.mark.parametrize("value", ["0", "-2"])
def test_fewer_than_one_attempt_is_refused(value: str) -> None:
    with pytest.raises(ValueError, match="VIBEY_STATE_ATTEMPTS must be at least 1"):
        load(VIBEY_STATE_ATTEMPTS=value)


def test_one_attempt_is_enough() -> None:
    assert load(VIBEY_STATE_ATTEMPTS="1").attempts == 1


@pytest.mark.parametrize("branch", ["-f", "--delete", "a..b", "..", "my branch", "a b c"])
def test_a_branch_that_is_not_a_branch_name_is_refused(branch: str) -> None:
    with pytest.raises(ValueError, match="VIBEY_STATE_BRANCH is not a branch name"):
        load(VIBEY_STATE_BRANCH=branch)


def test_conflict_rules_are_applied_to_their_tables() -> None:
    tables = load(VIBEY_STATE_CONFLICTS="engine_health=theirs, handoff=mine").tables
    rules = {spec.name: spec.rule for spec in tables}
    assert rules["engine_health"] is ConflictRule.THEIRS
    assert rules["handoff"] is ConflictRule.MINE
    assert [spec.name for spec in tables] == [spec.name for spec in TABLES]
    untouched = {spec.name: spec.rule for spec in TABLES}
    assert {n: r for n, r in rules.items() if n not in {"engine_health", "handoff"}} == {
        n: r for n, r in untouched.items() if n not in {"engine_health", "handoff"}
    }


@pytest.mark.parametrize(
    "conflicts", ["engine_health=sometimes", "no_such_table=mine", "engine_health"]
)
def test_a_bad_conflict_rule_is_refused(conflicts: str) -> None:
    with pytest.raises(ValueError):
        load(VIBEY_STATE_CONFLICTS=conflicts)
