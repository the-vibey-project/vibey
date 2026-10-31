# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An HTTP opener that answers from a queue and keeps the `timeout` each call carried (#728, #729).

It stands in for `urllib.request.urlopen` in a surface adapter's `opener` seam, with no mock
and no patching: a call takes the next canned reply and is recorded.
"""

from __future__ import annotations

import json
from typing import Any


class RecordedResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def __enter__(self) -> RecordedResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class RecordingOpener:
    def __init__(self, *replies: bytes | dict[str, Any] | list[Any]) -> None:
        self._replies = list(replies)
        self.timeouts: list[float | None] = []

    def __call__(self, request: object, timeout: float | None = None) -> RecordedResponse:
        self.timeouts.append(timeout)
        reply = self._replies.pop(0)
        return RecordedResponse(reply if isinstance(reply, bytes) else json.dumps(reply).encode())
