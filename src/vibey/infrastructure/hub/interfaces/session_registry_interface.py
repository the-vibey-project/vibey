# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over the session principals the worker minted and the hub finds (SP-LOOPS Phase 6,
Task 2).

Implemented by `session_registry.py`. Its methods -- `record`, `find`, `forget` -- are declared
once, by the application's `SessionPrincipalRegistryInterface`, and `entries` by its
`SessionPrincipalListingInterface` (Task 7); this is the same seam under the hub's own name.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.session_registry_sweep_interface import (
    SessionPrincipalListingInterface,
)
from vibey.application.interfaces.session_web_principals_interface import (
    SessionPrincipalRegistryInterface,
)


@runtime_checkable
class SessionRegistryInterface(
    SessionPrincipalRegistryInterface, SessionPrincipalListingInterface, Protocol
):
    """`record`, `find` and `forget`, as `SessionPrincipalRegistryInterface` declares them, and
    `entries`, as `SessionPrincipalListingInterface` does."""
