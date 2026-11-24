# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One page of a run's skill shelf, as `skills_list` answers it: the entries on page `number` of
`pages` (both counted from 1). An entry too long for any page carries an empty description. A
record with no behaviour, so no seam of its own."""

from dataclasses import dataclass

from vibey_runners.common.capabilities.shelf_entry import ShelfEntry


@dataclass(frozen=True, slots=True)
class ShelfPage:
    entries: tuple[ShelfEntry, ...]
    number: int
    pages: int
