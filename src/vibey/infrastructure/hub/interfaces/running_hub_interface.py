# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over finding the hub running on this computer (SP-LOOPS Phase 6, Task 5).

Implemented by `running_hub.py`. Its one method, `url`, is declared once, by the application's
`HubLocatorInterface`; this is the same seam under the hub's own name. Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.run_web_grants_interface import HubLocatorInterface


@runtime_checkable
class RunningHubInterface(HubLocatorInterface, Protocol):
    """`url`, as `HubLocatorInterface` declares it."""
