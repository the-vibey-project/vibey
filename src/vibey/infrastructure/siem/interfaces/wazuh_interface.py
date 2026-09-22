# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Wazuh SIEM seam.

Mirrors `vibey/infrastructure/siem/wazuh.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.siem import SiemPort


@runtime_checkable
class WazuhSiemAdapterInterface(SiemPort, Protocol):
    """The self-hosted Wazuh implementation of the SIEM port."""
