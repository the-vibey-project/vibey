# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Fossify SMS seam.

Mirrors `vibey/infrastructure/sms/fossify.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.sms import SmsPort


@runtime_checkable
class FossifySmsAdapterInterface(SmsPort, Protocol):
    """The self-hosted Fossify implementation of the SMS port."""
