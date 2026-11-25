# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The two environment names that carry a session's web grant (SP-LOOPS Phase 6, R1, R3).

A session the vibey worker started while a hub was running holds its own web-only grant as two
names: the hub's loopback address and the path of the session's token file -- never the token,
which stays in its 0600 file in the run's own 0700 folder. Neither is a secret, so they are the
only names like a secret that may pass a scrub: the local runner's shell keeps exactly these
two, and a local MCP server may keep exactly these two in its `env_allow` (`bundle.py`), which
is how the worker's `vibey-web` connector reaches the hub. One list, here, for both.

A session without a grant is given only `STATE_NAME`, as `none` or `none:<reason>` (`NO_WEB`,
then `REASON_SEPARATOR` and one of the worker's fixed reason names), so whatever it runs can tell
it has no web, and vibey's own commands can say why.

A record with no behaviour, so no seam of its own.
"""

from typing import Final

HUB_URL_NAME: Final = "VIBEY_HUB_URL"
"""The hub a session reaches, on this computer's loopback (`http://127.0.0.1:<port>`)."""
TOKEN_FILE_NAME: Final = "VIBEY_WEB_TOKEN_FILE"
"""Where the session's own token is: a path, never the token."""
WEB_GRANT_NAMES: Final[frozenset[str]] = frozenset({HUB_URL_NAME, TOKEN_FILE_NAME})
"""Both, and only these, exactly as spelled: a name merely like them is still refused."""
STATE_NAME: Final = "VIBEY_WEB_STATE"
"""Set, and alone, when the session has no web: `none`, or `none:<reason>`."""
NO_WEB: Final = "none"
"""The state of a session with no web."""
REASON_SEPARATOR: Final = ":"
"""Between `none` and the worker's fixed name for why."""
