# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two ACP session modes and the hub scopes each one may use (SP-ACP).

`observe` reads; `drive` reads, answers a gate that does not spend, and starts, pauses or
unwinds work. Neither ever holds `spend`: the mode table has no such entry, and the result
is intersected with the scopes the hub grants the agent principal (`[hub] agent_scopes`), so
a mode can narrow what the hub allows and never widen it. Declared by
`interfaces/modes_interface.py`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope

OBSERVE: Final = "observe"
DRIVE: Final = "drive"


class UnknownMode(VibeyError):
    """The mode id is not one `[acp] modes` offers."""


@dataclass(frozen=True, slots=True)
class AcpMode:
    """One entry of ACP's `SessionModeState.availableModes`."""

    id: str
    name: str
    description: str


MODE_CATALOGUE: Final[Mapping[str, AcpMode]] = {
    OBSERVE: AcpMode(
        OBSERVE,
        "Observe",
        "Read projects, gates and the ledger. Never answers or starts anything.",
    ),
    DRIVE: AcpMode(
        DRIVE,
        "Drive",
        "Read, answer non-spending gates, and start, pause or unwind work.",
    ),
}

MODE_SCOPES: Final[Mapping[str, frozenset[HubScope]]] = {
    OBSERVE: frozenset({HubScope.VIEW}),
    DRIVE: frozenset({HubScope.VIEW, HubScope.ANSWER, HubScope.RUN}),
}
"""What each mode may use at most. `SPEND` is in neither, and a test holds it so."""


class AcpModes:
    """Declared by `interfaces/modes_interface.py`."""

    def __init__(self, settings: AcpSettings) -> None:
        self._offered = settings.modes

    def available(self) -> tuple[AcpMode, ...]:
        return tuple(MODE_CATALOGUE[mode_id] for mode_id in self._offered)

    def scopes_for(self, mode_id: str, agent_scopes: frozenset[HubScope]) -> frozenset[HubScope]:
        self._require(mode_id)
        return MODE_SCOPES[mode_id] & agent_scopes

    def session_modes(self, current: str) -> dict[str, Any]:
        self._require(current)
        return {
            "currentModeId": current,
            "availableModes": [
                {"id": mode.id, "name": mode.name, "description": mode.description}
                for mode in self.available()
            ],
        }

    def _require(self, mode_id: str) -> None:
        if mode_id not in self._offered:
            offered = ", ".join(self._offered)
            raise UnknownMode(f"mode {mode_id!r} is not offered; the modes are: {offered}")
