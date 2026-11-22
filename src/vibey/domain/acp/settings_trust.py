# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who may say what in `[acp]`: the user grants, a project only restricts (ADR-0101).

`vibey acp` runs in whatever folder an editor opened, and that folder's `vibey.toml` came with
the project: a cloned repository's file is not the person's word. Every `[acp]` key is therefore
the user's (read from their own `vibey.toml`), and the project's file may only narrow it -- never
widen, raise or loosen anything:

- **Switches** (`auto_bootstrap`, `auto_connect`, `auto_services`, `live_between_turns`): the
  project may turn one off, never on.
- **`install_postgres`**: the project may say `never`, never `ask`.
- **`services`, `modes`**: the project may drop items, never add one; the result keeps the user's
  order. A project whose `modes` share none with the user's leaves the user's (a session is never
  refused, and nothing is widened). `default_mode` is the project's only if it survives in the
  merged modes, else the user's if it survives, else the first merged mode.
- **Rates** (`hub_start_seconds`, `probe_seconds`, `live_poll_seconds`): slower, never faster.
- **Bounds and caps** (every timeout, `prompt_probe_seconds`, `cancel_grace_seconds`, `max_gate_prompts_per_turn`, the
  message, event, session and replay limits): lower, never higher.
- **The user's alone** (`restart`, `service_workdir`, `reject_words`,
  `notice_interval_seconds`): a project value is ignored, since none of them has a direction
  that is only stricter (a longer notice interval would quiet the keep-alive's warnings).

A key not named here is the user's alone, so a key added later is closed until it is classified.
`[supervisor]` and `[hub]` are not merged at all for `vibey acp`'s machine: they are read from
the user's file only. Declared by `interfaces/settings_trust_interface.py`.
"""

from dataclasses import replace
from typing import Final

from vibey.domain.acp.settings import AcpSettings

SWITCHES: Final = ("auto_bootstrap", "auto_connect", "auto_services", "live_between_turns")
USER_ONLY: Final = ("restart", "service_workdir", "reject_words", "notice_interval_seconds")
SLOWER_ONLY: Final = ("hub_start_seconds", "probe_seconds", "live_poll_seconds")
LOWER_ONLY: Final = (
    "prompt_probe_seconds",
    "bootstrap_timeout_seconds",
    "install_timeout_seconds",
    "permission_timeout_seconds",
    "cancel_grace_seconds",
    "max_gate_prompts_per_turn",
    "live_message_chars",
    "max_message_bytes",
    "pending_events_max",
    "sessions_max",
    "session_events_max",
    "replay_events_max",
)
NARROWED: Final = ("install_postgres", "services", "modes", "default_mode")
CLASSIFIED: Final = frozenset({*SWITCHES, *USER_ONLY, *SLOWER_ONLY, *LOWER_ONLY, *NARROWED})
"""Every key the merge knows; any other is the user's alone."""


class AcpSettingsTrust:
    """Declared by `interfaces/settings_trust_interface.py::AcpSettingsTrustInterface`."""

    def merge(
        self, user: AcpSettings, project: AcpSettings, project_keys: frozenset[str]
    ) -> AcpSettings:
        changes: dict[str, object] = {}
        for key in SWITCHES:
            if key in project_keys:
                changes[key] = getattr(user, key) and getattr(project, key)
        if "install_postgres" in project_keys and project.install_postgres == "never":
            changes["install_postgres"] = "never"
        if "services" in project_keys:
            changes["services"] = tuple(s for s in user.services if s in project.services)
        for key in SLOWER_ONLY:
            if key in project_keys:
                changes[key] = max(getattr(user, key), getattr(project, key))
        for key in LOWER_ONLY:
            if key in project_keys:
                changes[key] = min(getattr(user, key), getattr(project, key))
        if project_keys & {"modes", "default_mode"}:
            changes.update(self._modes(user, project, project_keys))
        return replace(user, **changes)  # type: ignore[arg-type]

    @staticmethod
    def _modes(
        user: AcpSettings, project: AcpSettings, project_keys: frozenset[str]
    ) -> dict[str, object]:
        modes = user.modes
        if "modes" in project_keys:
            # Never widened, never emptied: no shared mode leaves the user's.
            modes = tuple(m for m in user.modes if m in project.modes) or user.modes
        if "default_mode" in project_keys and project.default_mode in modes:
            default = project.default_mode
        elif user.default_mode in modes:
            default = user.default_mode
        else:
            default = modes[0]
        return {"modes": modes, "default_mode": default}
