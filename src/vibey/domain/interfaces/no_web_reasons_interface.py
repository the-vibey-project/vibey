# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for carrying why a session has no web in its one name (SP-LOOPS Phase 6, Task 6).

Mirrors `vibey/domain/no_web_reasons.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NoWebReasonsInterface(Protocol):
    def state(self, reason: str) -> str:
        """`VIBEY_WEB_STATE`'s value for a session with no web because of `reason` (one of the
        fixed reasons): `none:<its name>`, or bare `none` for a reason with no name, so free
        text never reaches an environment."""
        ...

    def reason(self, state: str) -> str | None:
        """The fixed reason a `VIBEY_WEB_STATE` value names; `UNSAID` for bare `none` or a name
        this vibey does not know; None when the value is not a no-web state at all."""
        ...
