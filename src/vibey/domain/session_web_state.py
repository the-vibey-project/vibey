# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Whether an engine session can reach the web, and the fixed words for why it cannot
(SP-LOOPS Phase 6, Task 5).

A session either holds its own web-only grant from a running hub (`hub`: its environment names
the hub's loopback address and the path of its token file, never the token) or it has no web at
all (`none`). There is no third state: a session never searches in its own process.

When a session has no web, its plan says so and why, in one of the fixed reasons below, so the
model is never left to guess and never told something the worker did not observe. The reason
also travels in the session's one name, `VIBEY_WEB_STATE=none:<reason name>`
(`no_web_reasons.py`, Task 6), so `vibey search` and `vibey fetch` in that session say the same
reason, never "no hub is running" when one is.

The three names are the family's own (`vibey_runners.common.capabilities.web_grant_names`): the
local runner's shell and a local MCP server's `env_allow` admit exactly the grant's two.

Pure: constants only.
"""

from typing import Final, Literal

from vibey_runners.common.capabilities.web_grant_names import (
    HUB_URL_NAME,
    STATE_NAME,
    TOKEN_FILE_NAME,
)

type WebState = Literal["hub", "none"]
"""`hub`: the session holds its own grant. `none`: the session has no web."""

WEB_STATES: Final[tuple[WebState, ...]] = ("hub", "none")

HUB_URL_VARIABLE: Final = HUB_URL_NAME
"""The hub a session reaches, on this computer's loopback (`http://127.0.0.1:<port>`)."""
TOKEN_FILE_VARIABLE: Final = TOKEN_FILE_NAME
"""Where the session's own token is: a path, never the token (R1)."""
STATE_VARIABLE: Final = STATE_NAME
"""`none:<reason name>` when the session has no web (`no_web_reasons.py`)."""
SESSION_WEB_VARIABLES: Final[frozenset[str]] = frozenset(
    {HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE, STATE_VARIABLE}
)
"""Every name the worker lays over a session's environment for the web: the two of `hub`, or
the one of `none`. Nothing else about the web reaches a session -- no search backend's address
and no key -- and no allow-list can admit these: only the worker's own overlay sets them."""

NO_HUB: Final = "no hub is running; start one with `vibey serve`"
"""No hub was running when the session started."""

NO_RUN_FOLDER: Final = (
    "this engine's session has no run folder of its own to hold a web token, so it was given none"
)
"""The engine takes no capability snapshot, so the run has no owner-only folder for a token (R1:
a token lives only in a run's own 0700 folder)."""

NO_TOKEN: Final = (
    "a hub is running, but this session's web token could not be made; the worker's log says why"
)
"""A hub was running and minting the session's grant failed."""

NOT_GIVEN: Final = "the worker that started this session gave it no web access"
"""The session is not a BUILD run the worker opened web access for (a DESIGN or review session,
a conformance probe): it was never offered a grant."""

UNSAID: Final = "the worker that started this session did not say why"
"""The session is marked `none` with no reason name this vibey knows: nothing more is claimed."""
