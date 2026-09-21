# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seam for the OpenCode subprocess adapter (ADR-0016).

The dependency port the application consumes stays in
``application/interfaces/process_interface.py``; this interface is the
mechanical mirror beside the concrete class and extends that port so the two
can never drift.
"""

from typing import Protocol

from opencodeloop.application.interfaces.process_interface import ProcessInterface


class OpenCodeProcessInterface(ProcessInterface, Protocol):
    """The contract ``OpenCodeProcess`` implements."""
