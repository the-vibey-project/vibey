# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Why a session has no web, carried in the one name it is given (SP-LOOPS Phase 6, Task 6).

A session with no web is given exactly `VIBEY_WEB_STATE`, and no other web name. Its value is
`none:<reason name>`, where the name is one of the fixed few below, each standing for one of the
fixed reasons in `session_web_state.py`: no new environment name is needed for the reason to
reach the session's own `vibey search`, which says it in the same words the plan does.

Only a fixed name is ever written: a reason the worker does not know by name is written as bare
`none`, so free text never reaches an environment. Reading is the other way round: bare `none`,
or a name this vibey does not know, says only `UNSAID`, and anything that is not `none` at all
is not a no-web state. Pure. Declared by
`interfaces/no_web_reasons_interface.py::NoWebReasonsInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from vibey_runners.common.capabilities.web_grant_names import NO_WEB, REASON_SEPARATOR

from vibey.domain.session_web_state import NO_HUB, NO_RUN_FOLDER, NO_TOKEN, NOT_GIVEN, UNSAID

REASON_NAMES: Final[Mapping[str, str]] = {
    "no-hub": NO_HUB,
    "no-run-folder": NO_RUN_FOLDER,
    "no-token": NO_TOKEN,
    "not-given": NOT_GIVEN,
}
"""Each fixed reason's name, as it travels in `VIBEY_WEB_STATE`."""


class NoWebReasons:
    """Declared by `interfaces/no_web_reasons_interface.py::NoWebReasonsInterface`."""

    def __init__(self, names: Mapping[str, str] = REASON_NAMES) -> None:
        self._texts = dict(names)
        self._names = {text: name for name, text in names.items()}

    def state(self, reason: str) -> str:
        name = self._names.get(reason)
        return NO_WEB if name is None else f"{NO_WEB}{REASON_SEPARATOR}{name}"

    def reason(self, state: str) -> str | None:
        head, _, name = state.strip().partition(REASON_SEPARATOR)
        if head != NO_WEB:
            return None
        return self._texts.get(name, UNSAID)


NO_WEB_REASONS: Final[NoWebReasons] = NoWebReasons()
