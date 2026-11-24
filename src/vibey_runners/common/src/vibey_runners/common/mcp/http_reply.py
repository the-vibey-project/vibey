# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one HTTP exchange with a remote MCP server came back with (SP-LOOPS Phase 5, R13).

`headers` are the reply's own; `body` holds at most one byte more than the opener's limit, so a
reply longer than the limit is known to be one without being held whole. The body and headers
are the server's data: they are never written to a log, an events file or the ledger. Its own
module, not `http_opener.py`, so the opener's seam can name it without naming the opener. A
record with no behaviour, so no seam of its own.
"""

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HttpReply:
    status: int
    headers: Mapping[str, str]
    body: bytes
