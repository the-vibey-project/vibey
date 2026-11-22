# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who may say what in `[acp]`: the user grants, a project only restricts (ADR-0101).

`vibey acp` runs in whatever folder an editor opened, and that folder's `vibey.toml` came with
the project: a cloned repository's file is not the person's word. Anything that reaches a
service unit, a command line, or a file outside the project is therefore read from the user's
own `vibey.toml` (their configuration folder), and the project's may only narrow it:

- **Grants** (`auto_bootstrap`, `auto_connect`, `auto_services`): the project may turn one off,
  never on.
- **`install_postgres`**: the project may say `never`, never `ask`.
- **`services`**: the project may drop a service, never add one.
- **`restart`, `service_workdir`**: the user's alone.
- **Rates** (`hub_start_seconds`, `probe_seconds`): the project may make them slower, never
  faster. **Bounds** (`bootstrap_timeout_seconds`, `install_timeout_seconds`): shorter, never
  longer.
- **Every other key** shapes the session in the editor and reaches nothing outside it (modes,
  gate prompts, the live feed, message sizes): the project's value wins over the user's, as a
  project setting does. `modes` and `default_mode` are taken together, so they always agree.

`[supervisor]` and `[hub]` are not merged at all for `vibey acp`'s machine: they are read from
the user's file only. Declared by `interfaces/settings_trust_interface.py`.
"""

from dataclasses import fields, replace
from typing import Final

from vibey.domain.acp.settings import AcpSettings

GRANTS: Final = ("auto_bootstrap", "auto_connect", "auto_services")
USER_ONLY: Final = ("restart", "service_workdir")
SLOWER_ONLY: Final = ("hub_start_seconds", "probe_seconds")
SHORTER_ONLY: Final = ("bootstrap_timeout_seconds", "install_timeout_seconds")
_MODES: Final = ("modes", "default_mode")
_POWERS: Final = frozenset(
    {*GRANTS, *USER_ONLY, *SLOWER_ONLY, *SHORTER_ONLY, "install_postgres", "services"}
)


class AcpSettingsTrust:
    """Declared by `interfaces/settings_trust_interface.py::AcpSettingsTrustInterface`."""

    def merge(
        self, user: AcpSettings, project: AcpSettings, project_keys: frozenset[str]
    ) -> AcpSettings:
        changes: dict[str, object] = {}
        for key in GRANTS:
            if key in project_keys:
                changes[key] = getattr(user, key) and getattr(project, key)
        if "install_postgres" in project_keys and project.install_postgres == "never":
            changes["install_postgres"] = "never"
        if "services" in project_keys:
            changes["services"] = tuple(s for s in user.services if s in project.services)
        for key in SLOWER_ONLY:
            if key in project_keys:
                changes[key] = max(getattr(user, key), getattr(project, key))
        for key in SHORTER_ONLY:
            if key in project_keys:
                changes[key] = min(getattr(user, key), getattr(project, key))
        if project_keys & set(_MODES):
            changes.update({key: getattr(project, key) for key in _MODES})
        for item in fields(AcpSettings):
            key = item.name
            if key in project_keys and key not in _POWERS and key not in _MODES:
                changes[key] = getattr(project, key)
        return replace(user, **changes)  # type: ignore[arg-type]
