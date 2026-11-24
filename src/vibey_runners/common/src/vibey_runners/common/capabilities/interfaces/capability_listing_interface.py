# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of the standing capability listing a loop's system prompt carries (SP-LOOPS Phase 5,
R9)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.listing_text import ListingText
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.shelf_entry import ShelfEntry


@runtime_checkable
class CapabilityListingInterface(Protocol):
    def render(
        self, entries: Sequence[ShelfEntry], servers: Sequence[McpServerSpec], budget_tokens: int
    ) -> ListingText:
        """The listing of `entries` and `servers` in the first form whose estimated tokens are
        at most `budget_tokens`: `full` (skills with descriptions, commands and servers by
        name), `names` (no descriptions, and a line saying why), or `count` (one line, saying
        why). Skills and commands are headed as instructions, servers as data. An empty shelf
        with no servers is `""`. `tokens <= budget_tokens` always holds. Raises `ValueError`
        for a budget below `[loops] capability_prompt_tokens`'s floor."""
        ...
