# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over an engine session's token file (SP-LOOPS Phase 6, Task 2; R1).

Implemented by `session_token_store.py`. Its methods -- `write`, `read`, `remove` -- are
declared once, by the application's `SessionTokenFilesInterface`, which `SessionWebPrincipals`
consumes; this is the same seam under the hub's own name. Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.session_web_principals_interface import (
    SessionTokenFilesInterface,
)


@runtime_checkable
class SessionTokenStoreInterface(SessionTokenFilesInterface, Protocol):
    """`write`, `read` and `remove`, as `SessionTokenFilesInterface` declares them."""
