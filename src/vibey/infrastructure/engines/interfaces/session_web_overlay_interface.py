# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for what a session's environment and plan say about the web (SP-LOOPS Phase 6,
Task 5).

Mirrors `vibey/infrastructure/engines/session_web_overlay.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.dto import RunWebAccess


@runtime_checkable
class SessionWebOverlayInterface(Protocol):
    """The web part of an engine session's environment and plan."""

    def environment(self, web: RunWebAccess | None) -> dict[str, str]:
        """With a grant, exactly `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE`; otherwise exactly
        `VIBEY_WEB_STATE=none`, so the session's `vibey search` never searches in its own
        process. Never a token, a search backend's address or a key."""
        ...

    def plan_note(self, web: RunWebAccess | None, command: str) -> str | None:
        """The plan's web paragraph: how to run `command search` and `command fetch` with a
        grant; that search is unavailable and the fixed reason why without one; None when the
        run does not say."""
        ...
