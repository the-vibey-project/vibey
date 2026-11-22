# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpSettingsTrust`: the user's `[acp]` grants, a project's only restricts (ADR-0101).

A cloned repository's `vibey.toml` is not the person's word: whatever it says, it can turn a
grant off, drop a service, refuse PostgreSQL, or slow and shorten a bound -- never the reverse.
Module-level test functions (ADR-0016)."""

from dataclasses import fields

import pytest

from vibey.domain.acp.interfaces.settings_trust_interface import AcpSettingsTrustInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.settings_trust import AcpSettingsTrust

TRUST = AcpSettingsTrust()
ALL = frozenset(item.name for item in fields(AcpSettings))


def test_the_trust_is_its_interface() -> None:
    assert isinstance(TRUST, AcpSettingsTrustInterface)


def test_a_project_that_says_nothing_leaves_the_users_settings() -> None:
    user = AcpSettings(auto_services=False, probe_seconds=60, restart="on-failure")
    assert TRUST.merge(user, AcpSettings(), frozenset()) == user


@pytest.mark.parametrize("key", ["auto_bootstrap", "auto_connect", "auto_services"])
def test_a_project_can_turn_a_grant_off_never_on(key: str) -> None:
    on, off = AcpSettings(**{key: True}), AcpSettings(**{key: False})
    assert getattr(TRUST.merge(on, off, frozenset({key})), key) is False
    assert getattr(TRUST.merge(off, on, frozenset({key})), key) is False
    assert getattr(TRUST.merge(on, on, frozenset({key})), key) is True


def test_a_project_can_refuse_postgresql_never_ask_for_it() -> None:
    ask, never = AcpSettings(install_postgres="ask"), AcpSettings(install_postgres="never")
    keys = frozenset({"install_postgres"})
    assert TRUST.merge(ask, never, keys).install_postgres == "never"
    assert TRUST.merge(never, ask, keys).install_postgres == "never"


def test_a_project_can_drop_a_service_never_add_one() -> None:
    worker_only = AcpSettings(services=("worker",))
    both = AcpSettings(services=("hub", "worker"))
    keys = frozenset({"services"})
    assert TRUST.merge(worker_only, both, keys).services == ("worker",)
    assert TRUST.merge(both, AcpSettings(services=("hub",)), keys).services == ("hub",)
    assert TRUST.merge(both, AcpSettings(services=()), keys).services == ()


def test_restart_and_the_workdir_are_the_users_alone() -> None:
    user = AcpSettings(restart="on-failure", service_workdir="/home/op/vibey")
    project = AcpSettings(restart="always", service_workdir="/etc")
    merged = TRUST.merge(user, project, frozenset({"restart", "service_workdir"}))
    assert (merged.restart, merged.service_workdir) == ("on-failure", "/home/op/vibey")


def test_rates_only_slow_down_and_bounds_only_shorten() -> None:
    user = AcpSettings(
        hub_start_seconds=60,
        probe_seconds=30,
        bootstrap_timeout_seconds=120,
        install_timeout_seconds=1800,
    )
    eager = AcpSettings(
        hub_start_seconds=1,
        probe_seconds=5,
        bootstrap_timeout_seconds=9999,
        install_timeout_seconds=99999,
    )
    calm = AcpSettings(
        hub_start_seconds=600,
        probe_seconds=300,
        bootstrap_timeout_seconds=10,
        install_timeout_seconds=60,
    )
    keys = frozenset(
        {
            "hub_start_seconds",
            "probe_seconds",
            "bootstrap_timeout_seconds",
            "install_timeout_seconds",
        }
    )
    assert TRUST.merge(user, eager, keys) == user
    assert TRUST.merge(user, calm, keys) == calm


def test_session_keys_are_the_projects_and_modes_travel_together() -> None:
    user = AcpSettings(default_mode="drive", live_message_chars=400)
    project = AcpSettings(modes=("observe",), default_mode="observe", live_message_chars=80)
    merged = TRUST.merge(user, project, frozenset({"modes", "live_message_chars"}))
    assert (merged.modes, merged.default_mode, merged.live_message_chars) == (
        ("observe",),
        "observe",
        80,
    )


def test_a_hostile_project_that_sets_every_key_gains_nothing() -> None:
    user = AcpSettings(auto_services=False, install_postgres="never", services=("worker",))
    hostile = AcpSettings(
        auto_bootstrap=True,
        auto_connect=True,
        auto_services=True,
        install_postgres="ask",
        services=("hub", "worker"),
        restart="always",
        service_workdir="/tmp/evil",
        hub_start_seconds=1,
        probe_seconds=5,
    )
    merged = TRUST.merge(user, hostile, ALL)
    assert merged.auto_services is False
    assert merged.install_postgres == "never"
    assert merged.services == ("worker",)
    assert merged.service_workdir == ""
    assert (merged.hub_start_seconds, merged.probe_seconds) == (60, 30)
