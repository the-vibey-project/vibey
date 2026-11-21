# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpSettings` refuses an invalid value however it is built (SP-ACP)."""

import dataclasses
import math

import pytest

from vibey.domain.acp.modes import MODE_CATALOGUE, MODE_SCOPES
from vibey.domain.acp.settings import (
    FLOAT_MINIMA,
    INTEGER_MINIMA,
    KNOWN_MODES,
    AcpSettings,
    InvalidAcpSettings,
)
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope


def test_the_defaults_are_valid() -> None:
    assert AcpSettings().default_mode in AcpSettings().modes


def test_mode_ids_are_defined_once() -> None:
    assert set(KNOWN_MODES) == set(MODE_CATALOGUE) == set(MODE_SCOPES)


def test_no_mode_holds_spend_bump_or_workflows() -> None:
    for scopes in MODE_SCOPES.values():
        assert not scopes & {HubScope.SPEND, HubScope.BUMP, HubScope.WORKFLOWS}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("install_postgres", "yes"),
        ("restart", "never"),
        ("services", ("delivery",)),
        ("services", ("hub", "hub")),
        ("modes", ()),
        ("modes", ("observe", "spend")),
        ("modes", ("drive", "drive")),
        ("default_mode", "spend"),
        ("reject_words", ("",)),
        ("reject_words", ("No",)),
        ("live_poll_seconds", math.nan),
        ("live_poll_seconds", math.inf),
        ("cancel_grace_seconds", -math.inf),
        ("cancel_grace_seconds", -0.5),
        *[(key, minimum - 1) for key, minimum in INTEGER_MINIMA.items()],
        *[(key, minimum - 0.1) for key, minimum in FLOAT_MINIMA.items()],
    ],
)
def test_direct_construction_refuses_invalid_values_by_name(field: str, value: object) -> None:
    with pytest.raises(InvalidAcpSettings, match=field) as error:
        dataclasses.replace(AcpSettings(), **{field: value})
    assert isinstance(error.value, VibeyError)


def test_default_mode_must_be_among_the_modes() -> None:
    with pytest.raises(InvalidAcpSettings, match="default_mode"):
        AcpSettings(modes=("observe",))
    assert AcpSettings(modes=("observe",), default_mode="observe").modes == ("observe",)


def test_the_replay_bound_keeps_a_load_inside_the_hubs_burst() -> None:
    assert AcpSettings().replay_events_max == 2000
    assert AcpSettings(replay_events_max=10_000).replay_events_max == 10_000
    with pytest.raises(InvalidAcpSettings, match="replay_events_max must be at most 10000"):
        AcpSettings(replay_events_max=10_001)
