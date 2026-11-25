# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over where a session's token comes from (SP-LOOPS Phase 6, Task 2).

Implemented by `session_token_source.py`. `token` is declared once, by the application's
`SessionTokenSourceInterface`. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.session_web_principals_interface import (
    SessionTokenSourceInterface,
)


@runtime_checkable
class SecretsSessionTokenSourceInterface(SessionTokenSourceInterface, Protocol):
    """`token`, as `SessionTokenSourceInterface` declares it."""
