# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[acp]` in vibey.toml: defaults, and every refusal named by key (SP-ACP, Task 2)."""

from pathlib import Path

import pytest

from vibey.domain.acp.settings import AcpSettings
from vibey.domain.config import ConfigError
from vibey.infrastructure.acp.acp_settings_loader import AcpSettingsLoader
from vibey.infrastructure.acp.interfaces.acp_settings_loader_interface import (
    AcpSettingsLoaderInterface,
)


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "vibey.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert AcpSettingsLoader().load(tmp_path / "absent.toml") == AcpSettings()


def test_missing_table_gives_defaults(tmp_path: Path) -> None:
    assert AcpSettingsLoader().load(_write(tmp_path, "[supervisor]\ndelivery = true\n")) == (
        AcpSettings()
    )


def test_the_defaults_are_the_documented_table() -> None:
    d = AcpSettings()
    assert d.auto_bootstrap is True
    assert d.auto_connect is True
    assert d.auto_services is True
    assert d.install_postgres == "ask"
    assert d.services == ("hub", "worker")
    assert d.restart == "always"
    assert d.service_workdir == ""
    assert d.probe_seconds == 30
    assert d.modes == ("observe", "drive")
    assert d.default_mode == "drive"
    assert d.bootstrap_timeout_seconds == 120
    assert d.permission_timeout_seconds == 600
    assert d.max_gate_prompts_per_turn == 3
    assert d.reject_words == ("reject", "decline", "deny", "no", "cancel")
    assert d.live_poll_seconds == 1.0
    assert d.live_message_chars == 400
    assert d.live_between_turns is True
    assert d.cancel_grace_seconds == 2.0
    assert d.max_message_bytes == 16_777_216
    assert d.pending_events_max == 1000


def test_every_key_is_read_by_name(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        """
[acp]
auto_bootstrap = false
auto_connect = false
auto_services = false
install_postgres = "never"
services = ["worker"]
restart = "on-failure"
service_workdir = "/srv/vibey"
probe_seconds = 5
modes = ["observe"]
default_mode = "observe"
bootstrap_timeout_seconds = 1
permission_timeout_seconds = 2
max_gate_prompts_per_turn = 0
reject_words = ["nope"]
live_poll_seconds = 0.5
live_message_chars = 40
live_between_turns = false
cancel_grace_seconds = 0
max_message_bytes = 65536
pending_events_max = 1
""",
    )
    assert AcpSettingsLoader().load(path) == AcpSettings(
        auto_bootstrap=False,
        auto_connect=False,
        auto_services=False,
        install_postgres="never",
        services=("worker",),
        restart="on-failure",
        service_workdir="/srv/vibey",
        probe_seconds=5,
        modes=("observe",),
        default_mode="observe",
        bootstrap_timeout_seconds=1,
        permission_timeout_seconds=2,
        max_gate_prompts_per_turn=0,
        reject_words=("nope",),
        live_poll_seconds=0.5,
        live_message_chars=40,
        live_between_turns=False,
        cancel_grace_seconds=0.0,
        max_message_bytes=65536,
        pending_events_max=1,
    )


def test_reject_words_are_lower_cased_and_trimmed() -> None:
    loaded = AcpSettingsLoader().from_mapping({"reject_words": ["No", " DENY "]})
    assert loaded.reject_words == ("no", "deny")


def test_an_integer_is_accepted_for_a_float_key() -> None:
    loaded = AcpSettingsLoader().from_mapping({"live_poll_seconds": 2})
    assert loaded.live_poll_seconds == 2.0
    assert isinstance(loaded.live_poll_seconds, float)


def test_an_empty_services_list_is_allowed() -> None:
    assert AcpSettingsLoader().from_mapping({"services": []}).services == ()


def test_unknown_key_is_refused_by_name(tmp_path: Path) -> None:
    path = _write(tmp_path, "[acp]\nprobe_secs = 30\n")
    with pytest.raises(ConfigError, match=r"\[acp\] probe_secs is not a known key") as error:
        AcpSettingsLoader().load(path)
    assert error.value.path == str(path)


def test_several_unknown_keys_are_all_named() -> None:
    with pytest.raises(ConfigError, match=r"alpha.*beta|beta.*alpha"):
        AcpSettingsLoader().from_mapping({"alpha": 1, "beta": 2})


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("probe_seconds", 4),
        ("modes", []),
        ("modes", ["observe", "spend"]),
        ("default_mode", "spend"),
        ("services", ["delivery"]),
        ("services", "hub"),
        ("services", ["hub", "hub"]),
        ("modes", ["drive", "drive"]),
        ("restart", "never"),
        ("max_message_bytes", 1024),
        ("install_postgres", "yes"),
        ("auto_bootstrap", "yes"),
        ("auto_connect", 1),
        ("probe_seconds", True),
        ("probe_seconds", "30"),
        ("probe_seconds", 30.5),
        ("bootstrap_timeout_seconds", 0),
        ("permission_timeout_seconds", 0),
        ("max_gate_prompts_per_turn", -1),
        ("reject_words", "no"),
        ("reject_words", ["no", 3]),
        ("live_poll_seconds", 0.1),
        ("live_poll_seconds", "1"),
        ("live_poll_seconds", True),
        ("live_message_chars", 39),
        ("cancel_grace_seconds", -0.5),
        ("pending_events_max", 0),
        ("service_workdir", 5),
        ("live_poll_seconds", float("nan")),
        ("live_poll_seconds", float("inf")),
        ("cancel_grace_seconds", float("-inf")),
        ("cancel_grace_seconds", float("inf")),
        ("reject_words", [""]),
        ("reject_words", ["  "]),
        ("live_between_turns", "true"),
    ],
)
def test_out_of_bound_values_are_refused_by_name(tmp_path: Path, key: str, value: object) -> None:
    with pytest.raises(ConfigError, match=rf"\[acp\] {key} ") as error:
        AcpSettingsLoader().from_mapping({key: value})
    assert key in error.value.message


def test_default_mode_must_be_one_of_the_declared_modes() -> None:
    with pytest.raises(ConfigError, match=r"\[acp\] default_mode "):
        AcpSettingsLoader().from_mapping({"modes": ["observe"]})
    ok = AcpSettingsLoader().from_mapping({"modes": ["observe"], "default_mode": "observe"})
    assert ok.modes == ("observe",)


def test_a_non_table_acp_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"\[acp\] must be a table"):
        AcpSettingsLoader().load(_write(tmp_path, 'acp = "on"\n'))


def test_a_file_that_is_not_toml_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not valid TOML"):
        AcpSettingsLoader().load(_write(tmp_path, "[acp\n"))


def test_an_unreadable_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot be read"):
        AcpSettingsLoader().load(tmp_path)


def test_the_implementation_satisfies_its_interface() -> None:
    assert isinstance(AcpSettingsLoader(), AcpSettingsLoaderInterface)
