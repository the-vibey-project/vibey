# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The web-search lines `vibey doctor` and `vibey acp`'s doctor step print.

Two lines in doctor's `MARK name detail` grammar, so `vibey doctor --json` reads them as checks
(no new key in its document):

    PASS web-search                 local SearXNG answering at http://127.0.0.1:8080
    UNKNOWN web-search-backup       no Brave backup configured (optional: ...)

- `web-search`: whether a SearXNG answers at the configured address and proves it is one (a
  bounded GET of its `/config`, which sends no query and no secret; `SearxngBackend.health`),
  and, when `VIBEY_SEARXNG_INSTANCE` is set, the expected one. Not answering, or something else
  answering, is a `WARN` with the fix, never a `FAIL`: vibey still runs, its searches fail (or go
  to the Brave backup) until it does. A search setting the worker would refuse to start with is
  the one `FAIL`.
- `web-search-backup`: whether a Brave key is configured, and by which variable; never the key.

The URL is shown without credentials, query or fragment, and every detail is cleaned as a raised
check's message is (`DoctorChecks.cleaned`). The section never raises.

Declared by `interfaces/web_search_doctor_interface.py` (ADR-0016).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any, Final

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.cli.interfaces.web_search_doctor_interface import WebSearchDoctorInterface
from vibey.domain.config import ConfigError
from vibey.infrastructure.web.search import (
    BRAVE_KEY_ALIAS_ENV,
    BRAVE_KEY_ENV,
    SEARXNG_URL_ENV,
    SearxngBackend,
    WebSearchSettings,
    display_url,
)

NAME: Final = "web-search"
BACKUP_NAME: Final = "web-search-backup"
_WIDTH: Final = 26


class WebSearchDoctor:
    """Declared by `interfaces/web_search_doctor_interface.py::WebSearchDoctorInterface`."""

    def __init__(
        self,
        *,
        environ: Callable[[], Mapping[str, str]] | None = None,
        opener: Callable[..., Any] | None = None,
    ) -> None:
        self._environ = environ if environ is not None else self._process_environment
        self._opener = opener

    def doctor_lines(self) -> tuple[list[str], bool]:
        try:
            return self._lines()
        except Exception as exc:  # noqa: BLE001 - the section never breaks doctor
            reason = DoctorChecks.cleaned(f"{type(exc).__name__}: {exc}")
            return [f"UNKNOWN {NAME:<{_WIDTH}} could not check web search ({reason})"], True

    def _lines(self) -> tuple[list[str], bool]:
        try:
            settings = WebSearchSettings.from_environment(self._environ())
        except ConfigError as exc:
            return [f"FAIL {NAME:<{_WIDTH}} {DoctorChecks.cleaned(str(exc), limit=400)}"], False
        where = DoctorChecks.cleaned(display_url(settings.searxng_url))
        down = SearxngBackend(
            settings.searxng_url,
            timeout_seconds=settings.timeout_seconds,
            opener=self._opener,
            instance=settings.searxng_instance,
        ).health()
        if down is None:
            expected = " (the expected instance)" if settings.searxng_instance else ""
            local = f"PASS {NAME:<{_WIDTH}} local SearXNG answering at {where}{expected}"
        elif SearxngBackend.is_impostor(down):
            who, _, why = down.partition(" listening there ")
            local = (
                f"WARN {NAME:<{_WIDTH}} {who} listening at {where} {DoctorChecks.cleaned(why)}:"
                " vibey will not use its answers; stop it, or run SearXNG elsewhere and point"
                f" {SEARXNG_URL_ENV} there"
            )
        else:
            local = (
                f"WARN {NAME:<{_WIDTH}} local SearXNG not answering at {where}"
                f" ({DoctorChecks.cleaned(down)}): start SearXNG there with its JSON format"
                f" enabled, or point {SEARXNG_URL_ENV} at yours; until then vibey's searches"
                " fail, or go to Brave when a backup key is set"
            )
        backup = (
            f"PASS {BACKUP_NAME:<{_WIDTH}} Brave backup configured via {settings.brave_key_env}:"
            " asked only when the local SearXNG fails, and never given to an engine session"
            if settings.brave_key_env is not None
            else f"UNKNOWN {BACKUP_NAME:<{_WIDTH}} no Brave backup configured (optional:"
            f" {BRAVE_KEY_ENV} or {BRAVE_KEY_ALIAS_ENV}; used only when the local SearXNG fails)"
        )
        return [local, backup], True

    @staticmethod
    def _process_environment() -> Mapping[str, str]:
        return os.environ


WEB_SEARCH_DOCTOR: Final[WebSearchDoctorInterface] = WebSearchDoctor()
"""The section as `vibey doctor` and `vibey acp` run it: this process's environment, probed
through the guarded opener."""
