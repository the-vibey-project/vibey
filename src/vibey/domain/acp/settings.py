# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[acp]` in `vibey.toml`: what `vibey acp` may do on its own and how it behaves (SP-ACP).

Every value a reasonable adopter could want different is a key here (ADR-0018); nothing in
the ACP code reads a literal where a key exists. `infrastructure/acp/acp_settings_loader.py`
reads and bounds the table; this module holds its shape, its defaults and the closed sets a
key may name. Pure: no I/O.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

from vibey.domain.errors import VibeyError

KNOWN_SERVICES: Final = ("hub", "worker")
"""The user-level services `services` may name."""
KNOWN_MODES: Final = ("observe", "drive")
"""The session modes `modes` may name."""
INSTALL_POSTGRES_CHOICES: Final = ("ask", "never")
"""`install_postgres`: ask through `session/request_permission`, or never install."""
RESTART_POLICIES: Final = ("always", "on-failure")
"""`restart`: the service manager's policy for the units `vibey acp` loads."""
INTEGER_MINIMA: Final[Mapping[str, int]] = {
    "probe_seconds": 5,
    "hub_start_seconds": 1,
    "bootstrap_timeout_seconds": 1,
    "permission_timeout_seconds": 1,
    "max_gate_prompts_per_turn": 0,
    "live_message_chars": 40,
    "max_message_bytes": 65_536,
    "pending_events_max": 1,
    "sessions_max": 1,
    "session_events_max": 1,
    "replay_events_max": 1,
}
"""The least each integer key may be."""
INTEGER_MAXIMA: Final[Mapping[str, int]] = {
    "replay_events_max": 10_000,
}
"""The most each bounded integer key may be. A load reads the replayed tail in pages of 200, one
request each, so 10000 events is 51 requests: inside the hub's per-principal burst of 120, with
room left for the turns and `vibey mcp` that share it."""
HUB_KEYS: Final = ("sessions_max", "session_events_max")
"""The `[acp]` keys the hub (`vibey serve`) reads: the bounds on what it keeps of ACP sessions.
Every other key is the editor's, and a mistake in one never stops the hub."""
FLOAT_MINIMA: Final[Mapping[str, float]] = {
    "live_poll_seconds": 0.2,
    "cancel_grace_seconds": 0.0,
}
"""The least each number key may be; a number must also be finite."""


class InvalidAcpSettings(VibeyError):
    """An `AcpSettings` value is outside what its key allows. The message starts with the key."""


@dataclass(frozen=True, slots=True)
class AcpSettings:
    """The `[acp]` table, with its defaults (docs/reference/configuration.md#acp)."""

    auto_bootstrap: bool = True
    auto_connect: bool = True
    auto_services: bool = True
    install_postgres: str = "ask"
    services: tuple[str, ...] = ("hub", "worker")
    restart: str = "always"
    service_workdir: str = ""
    probe_seconds: int = 30
    hub_start_seconds: int = 60
    """The least time between two `vibey hub start` attempts when a hub read finds no hub; the
    attempt runs off the event loop, and every read in between hears "the hub is away" at once."""
    modes: tuple[str, ...] = ("observe", "drive")
    default_mode: str = "drive"
    bootstrap_timeout_seconds: int = 120
    permission_timeout_seconds: int = 600
    max_gate_prompts_per_turn: int = 3
    reject_words: tuple[str, ...] = ("reject", "decline", "deny", "no", "cancel")
    live_poll_seconds: float = 1.0
    live_message_chars: int = 400
    live_between_turns: bool = True
    cancel_grace_seconds: float = 2.0
    max_message_bytes: int = 16_777_216
    pending_events_max: int = 1000
    sessions_max: int = 1000
    """The most ACP sessions the hub keeps for one principal; past it a new one is refused."""
    session_events_max: int = 100_000
    """The most events the hub keeps in one session's log; past it an append is refused."""
    replay_events_max: int = 2000
    """The most of a session's newest events `session/load` shows again; older ones are said to
    be skipped, once."""

    def __post_init__(self) -> None:
        for key, choices in (
            ("install_postgres", INSTALL_POSTGRES_CHOICES),
            ("restart", RESTART_POLICIES),
        ):
            if getattr(self, key) not in choices:
                raise InvalidAcpSettings(f"{key} must be one of {', '.join(choices)}")
        self._subset("services", self.services, KNOWN_SERVICES)
        self._subset("modes", self.modes, KNOWN_MODES)
        if not self.modes:
            raise InvalidAcpSettings("modes must not be empty")
        if self.default_mode not in self.modes:
            raise InvalidAcpSettings(
                f"default_mode must be one of modes ({', '.join(self.modes)}), "
                f"not {self.default_mode!r}"
            )
        for key, minimum in {**INTEGER_MINIMA, **FLOAT_MINIMA}.items():
            value = getattr(self, key)
            if not math.isfinite(value) or value < minimum:
                raise InvalidAcpSettings(f"{key} must be a finite number of at least {minimum}")
        for key, maximum in INTEGER_MAXIMA.items():
            if getattr(self, key) > maximum:
                raise InvalidAcpSettings(f"{key} must be at most {maximum}")
        if any(not word or word != word.lower() for word in self.reject_words):
            raise InvalidAcpSettings("reject_words must be non-empty lower-case words")

    @staticmethod
    def _subset(key: str, items: tuple[str, ...], known: tuple[str, ...]) -> None:
        if any(item not in known for item in items) or len(set(items)) != len(items):
            raise InvalidAcpSettings(f"{key} must list each of {', '.join(known)} at most once")
