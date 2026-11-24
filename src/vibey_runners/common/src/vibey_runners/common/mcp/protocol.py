# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP protocol versions the family speaks, oldest first (SP-LOOPS Phase 5, R2 and R15).

vibey's MCP server answers with one of these, and the client in this package offers the latest
and accepts any of them in the server's answer. One list, so both ends move together. Constants
only (ADR-0016 exempts them from the interface rule).
"""

from typing import Final

SUPPORTED_PROTOCOLS: Final[tuple[str, ...]] = (
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
)
LATEST_PROTOCOL: Final = SUPPORTED_PROTOCOLS[-1]
