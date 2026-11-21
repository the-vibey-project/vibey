# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP observe and drive modes and the scopes each grants (SP-ACP, Task 2)."""

import pytest
from acp.schema import SessionModeState
from acp_wire import assert_wire_exact

from vibey.domain.acp.interfaces.modes_interface import AcpModesInterface
from vibey.domain.acp.modes import AcpMode, AcpModes, UnknownMode
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope


def test_observe_is_view_only_and_drive_never_contains_spend() -> None:
    modes = AcpModes(AcpSettings())
    assert modes.scopes_for("observe", AGENT_DEFAULT_SCOPES) == {HubScope.VIEW}
    assert HubScope.SPEND not in modes.scopes_for("drive", frozenset(HubScope))
    assert modes.scopes_for("drive", frozenset(HubScope)) == AGENT_DEFAULT_SCOPES


def test_no_mode_ever_grants_spend_bump_or_workflows() -> None:
    modes = AcpModes(AcpSettings())
    for mode in modes.available():
        granted = modes.scopes_for(mode.id, frozenset(HubScope))
        for forbidden in (HubScope.SPEND, HubScope.BUMP, HubScope.WORKFLOWS):
            assert forbidden not in granted


def test_drive_is_narrowed_by_hub_agent_scopes() -> None:
    assert AcpModes(AcpSettings()).scopes_for("drive", frozenset({HubScope.VIEW})) == {
        HubScope.VIEW
    }
    assert AcpModes(AcpSettings()).scopes_for("observe", frozenset()) == frozenset()


def test_session_modes_dict_validates_against_the_sdk_schema() -> None:
    payload = AcpModes(AcpSettings()).session_modes("drive")
    assert_wire_exact(SessionModeState, payload)
    state = SessionModeState.model_validate(payload)
    assert state.current_mode_id == "drive"
    assert [mode.id for mode in state.available_modes] == ["observe", "drive"]


def test_available_modes_carry_the_documented_names_and_descriptions() -> None:
    observe, drive = AcpModes(AcpSettings()).available()
    assert observe == AcpMode(
        "observe",
        "Observe",
        "Read projects, gates and the ledger. Never answers or starts anything.",
    )
    assert drive == AcpMode(
        "drive",
        "Drive",
        "Read, answer non-spending gates, and start, pause or unwind work.",
    )


def test_available_follows_the_settings_in_their_order() -> None:
    only = AcpModes(AcpSettings(modes=("observe",), default_mode="observe"))
    assert [mode.id for mode in only.available()] == ["observe"]
    reordered = AcpModes(AcpSettings(modes=("drive", "observe")))
    assert [mode.id for mode in reordered.available()] == ["drive", "observe"]


def test_a_mode_the_settings_do_not_offer_is_unknown() -> None:
    modes = AcpModes(AcpSettings(modes=("observe",), default_mode="observe"))
    with pytest.raises(UnknownMode):
        modes.scopes_for("drive", AGENT_DEFAULT_SCOPES)
    with pytest.raises(UnknownMode):
        modes.session_modes("drive")


def test_an_unknown_mode_id_is_refused_by_name() -> None:
    modes = AcpModes(AcpSettings())
    with pytest.raises(UnknownMode, match="spend") as error:
        modes.scopes_for("spend", AGENT_DEFAULT_SCOPES)
    assert isinstance(error.value, VibeyError)
    with pytest.raises(UnknownMode):
        modes.session_modes("spend")


def test_the_implementation_satisfies_its_interface() -> None:
    assert isinstance(AcpModes(AcpSettings()), AcpModesInterface)
