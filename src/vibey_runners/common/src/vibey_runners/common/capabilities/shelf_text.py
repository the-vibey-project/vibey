# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One page of a skill's or command's text, as `skill_read` answers it: page `number` of
`pages` (both counted from 1). The pages of one text, joined in order, are the file's text
exactly: nothing is cut (SP-LOOPS Phase 5, R11). A record with no behaviour, so no seam of its
own."""

from dataclasses import dataclass

from vibey_runners.common.capabilities.shelf_entry import ShelfKind


@dataclass(frozen=True, slots=True)
class ShelfText:
    name: str
    kind: ShelfKind
    number: int
    pages: int
    text: str
