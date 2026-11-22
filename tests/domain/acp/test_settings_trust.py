# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpSettingsTrust`: the user's `[acp]` grants, a project's only restricts (ADR-0101).

A cloned repository's `vibey.toml` is not the person's word: whatever it says, it can turn a
grant off, drop a service, refuse PostgreSQL, or slow and shorten a bound -- never the reverse.
Module-level test functions (ADR-0016)."""

from dataclasses import fields

import pytest

from vibey.domain.acp.interfaces.settings_trust_interface import AcpSettingsTrustInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.settings_trust import CLASSIFIED, AcpSettingsTrust

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


def test_every_key_is_classified_so_none_is_the_projects_to_widen() -> None:
    assert ALL == CLASSIFIED


def test_a_project_cannot_widen_observe_only_to_drive() -> None:
    user = AcpSettings(modes=("observe",), default_mode="observe")
    project = AcpSettings(modes=("observe", "drive"), default_mode="drive")
    for keys in ({"modes", "default_mode"}, {"default_mode"}, {"modes"}):
        merged = TRUST.merge(user, project, frozenset(keys))
        assert (merged.modes, merged.default_mode) == (("observe",), "observe")


def test_a_project_can_narrow_drive_to_observe() -> None:
    user = AcpSettings()  # observe and drive, drive by default
    merged = TRUST.merge(
        user,
        AcpSettings(modes=("observe",), default_mode="observe"),
        frozenset({"modes", "default_mode"}),
    )
    assert (merged.modes, merged.default_mode) == (("observe",), "observe")


def test_a_project_may_pick_the_default_among_the_users_modes() -> None:
    merged = TRUST.merge(
        AcpSettings(), AcpSettings(default_mode="observe"), frozenset({"default_mode"})
    )
    assert (merged.modes, merged.default_mode) == (("observe", "drive"), "observe")


def test_modes_keep_the_users_order_and_a_default_that_survives() -> None:
    user = AcpSettings(modes=("drive", "observe"), default_mode="drive")
    project = AcpSettings(modes=("observe", "drive"), default_mode="observe")
    merged = TRUST.merge(user, project, frozenset({"modes"}))
    assert (merged.modes, merged.default_mode) == (("drive", "observe"), "drive")


def test_a_default_lost_to_the_narrowing_falls_to_the_first_merged_mode() -> None:
    user = AcpSettings(modes=("observe", "drive"), default_mode="drive")
    project = AcpSettings(modes=("observe",), default_mode="observe")
    merged = TRUST.merge(user, project, frozenset({"modes"}))
    assert (merged.modes, merged.default_mode) == (("observe",), "observe")


def test_modes_sharing_nothing_leave_the_users_never_an_empty_session() -> None:
    user = AcpSettings(modes=("drive",), default_mode="drive")
    project = AcpSettings(modes=("observe",), default_mode="observe")
    merged = TRUST.merge(user, project, frozenset({"modes", "default_mode"}))
    assert (merged.modes, merged.default_mode) == (("drive",), "drive")


LOOSER = {
    "max_gate_prompts_per_turn": 50,
    "permission_timeout_seconds": 86_400,
    "cancel_grace_seconds": 600.0,
    "live_message_chars": 100_000,
    "max_message_bytes": 1 << 30,
    "pending_events_max": 10**7,
    "sessions_max": 10**7,
    "session_events_max": 10**9,
    "replay_events_max": 10_000,
    "bootstrap_timeout_seconds": 10**6,
    "install_timeout_seconds": 10**6,
}
STRICTER = {
    "max_gate_prompts_per_turn": 0,
    "permission_timeout_seconds": 5,
    "cancel_grace_seconds": 0.0,
    "live_message_chars": 40,
    "max_message_bytes": 65_536,
    "pending_events_max": 1,
    "sessions_max": 1,
    "session_events_max": 1,
    "replay_events_max": 1,
    "bootstrap_timeout_seconds": 1,
    "install_timeout_seconds": 1,
}


@pytest.mark.parametrize("key", sorted(LOOSER))
def test_a_project_cannot_raise_a_cap_or_lengthen_a_bound(key: str) -> None:
    user = AcpSettings()
    merged = TRUST.merge(user, AcpSettings(**{key: LOOSER[key]}), frozenset({key}))
    assert getattr(merged, key) == getattr(user, key)


@pytest.mark.parametrize("key", sorted(STRICTER))
def test_a_project_can_lower_a_cap_or_shorten_a_bound(key: str) -> None:
    merged = TRUST.merge(AcpSettings(), AcpSettings(**{key: STRICTER[key]}), frozenset({key}))
    assert getattr(merged, key) == STRICTER[key]


def test_a_project_can_slow_the_live_feed_never_speed_it_up() -> None:
    user = AcpSettings(live_poll_seconds=1.0)
    keys = frozenset({"live_poll_seconds"})
    assert TRUST.merge(user, AcpSettings(live_poll_seconds=0.2), keys).live_poll_seconds == 1.0
    assert TRUST.merge(user, AcpSettings(live_poll_seconds=5.0), keys).live_poll_seconds == 5.0


def test_a_project_can_hold_the_feed_between_turns_never_open_it() -> None:
    keys = frozenset({"live_between_turns"})
    held = AcpSettings(live_between_turns=False)
    assert TRUST.merge(held, AcpSettings(), keys).live_between_turns is False
    assert TRUST.merge(AcpSettings(), held, keys).live_between_turns is False


def test_the_words_that_mark_a_refusal_are_the_users_alone() -> None:
    user = AcpSettings(reject_words=("reject", "deny"))
    project = AcpSettings(reject_words=("approve",))
    merged = TRUST.merge(user, project, frozenset({"reject_words"}))
    assert merged.reject_words == ("reject", "deny")


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
