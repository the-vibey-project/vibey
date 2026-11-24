# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What an engine session's environment and plan say about the web (SP-LOOPS Phase 6, Task 5;
R1).

A session that holds its own grant is given exactly two names: the running hub's loopback
address (`VIBEY_HUB_URL`) and the path of its token file (`VIBEY_WEB_TOKEN_FILE`), never the
token; its plan says how to run `vibey search` and `vibey fetch`. Any other session -- no hub, no
run folder, a grant that could not be made, or a caller that did not say -- is given exactly
`VIBEY_WEB_STATE=none:<reason name>`, so its `vibey search` refuses rather than search in its own
process, and says the same fixed reason its plan does (`domain/no_web_reasons.py`, Task 6); a
caller that did not say is `not-given`. When the run says why, its plan says so in fixed text
(`domain/session_web_state.py`).

No search backend's address, no key and no `WEBSEARCH_*` name is in either: the session's search
is the hub's. The names are laid over the session's environment by the worker alone
(`MODEL_SESSION_FORBIDDEN.overlay_grants`); no allow-list may admit them.

Declared by `interfaces/session_web_overlay_interface.py::SessionWebOverlayInterface`.
"""

from __future__ import annotations

from typing import Final

from vibey.application.dto import RunWebAccess
from vibey.domain.no_web_reasons import NO_WEB_REASONS
from vibey.domain.session_web_state import (
    HUB_URL_VARIABLE,
    NOT_GIVEN,
    STATE_VARIABLE,
    TOKEN_FILE_VARIABLE,
)
from vibey.infrastructure.web.session import web_access_note


class SessionWebOverlay:
    """Declared by `interfaces/session_web_overlay_interface.py::SessionWebOverlayInterface`."""

    def environment(self, web: RunWebAccess | None) -> dict[str, str]:
        if web is None:
            return {STATE_VARIABLE: NO_WEB_REASONS.state(NOT_GIVEN)}
        if web.token_file is None:
            return {STATE_VARIABLE: NO_WEB_REASONS.state(web.reason)}
        return {HUB_URL_VARIABLE: web.hub_url, TOKEN_FILE_VARIABLE: str(web.token_file)}

    def plan_note(self, web: RunWebAccess | None, command: str) -> str | None:
        if web is None:
            return None
        if web.state == "hub":
            return web_access_note(command)
        return (
            "## Web access\n\n"
            f"Web search and page fetching are unavailable in this session: {web.reason}. "
            "Use the repository and what you already know instead."
        )


SESSION_WEB_OVERLAY: Final[SessionWebOverlay] = SessionWebOverlay()
