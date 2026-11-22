# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/untrusted_text.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class UntrustedTextInterface(Protocol):
    """Makes text from the open web safe to print."""

    @staticmethod
    def clean(text: str) -> str:
        """No escape sequence, control or format character; tabs and newlines kept."""
        ...

    @staticmethod
    def is_clean_url(url: str) -> bool:
        """Whether a URL holds no control, format or space character."""
        ...
