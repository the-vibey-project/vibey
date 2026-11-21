# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`[acp]` in `vibey.toml`: what `vibey acp` may do on its own and how it behaves (SP-ACP).

Every value a reasonable adopter could want different is a key here (ADR-0018); nothing in
the ACP code reads a literal where a key exists. `infrastructure/acp/acp_settings_loader.py`
reads and bounds the table; this module holds its shape, its defaults and the closed sets a
key may name. Pure: no I/O.
"""

from dataclasses import dataclass
from typing import Final

KNOWN_SERVICES: Final = ("hub", "worker")
"""The user-level services `services` may name."""
KNOWN_MODES: Final = ("observe", "drive")
"""The session modes `modes` may name."""
INSTALL_POSTGRES_CHOICES: Final = ("ask", "never")
"""`install_postgres`: ask through `session/request_permission`, or never install."""
RESTART_POLICIES: Final = ("always", "on-failure")
"""`restart`: the service manager's policy for the units `vibey acp` loads."""


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
