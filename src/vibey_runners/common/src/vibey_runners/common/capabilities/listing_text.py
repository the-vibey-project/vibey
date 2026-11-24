# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The standing listing a loop's system prompt carries, the form it took, and what it is
estimated to cost (SP-LOOPS Phase 5, R9). `form` is `full`, `names` (descriptions left out) or
`count` (one line). A record with no behaviour, so no seam of its own."""

from dataclasses import dataclass
from typing import Literal

ListingForm = Literal["full", "names", "count"]


@dataclass(frozen=True, slots=True)
class ListingText:
    text: str
    form: ListingForm
    tokens: int
