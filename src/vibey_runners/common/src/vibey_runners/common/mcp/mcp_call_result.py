# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one `tools/call` returned: its text parts joined with a newline, and whether the server
marked the result an error. The text is data, whatever the server's trust (Decision 9). A
record with no behaviour, so no seam of its own."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class McpCallResult:
    text: str
    is_error: bool
