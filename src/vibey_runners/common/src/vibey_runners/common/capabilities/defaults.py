# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a bundle holds when the person has said nothing (SP-LOOPS, design Decisions 1 and 10).

Constants, not code: the marketplace that ships inside the installed wheel and the research
methodology plugins every loop gets unless the person's own `[loops]` says otherwise.
"""

from typing import Final

DEFAULT_MARKETPLACE_NAME: Final = "vibey"
"""The marketplace copy that ships in the wheel. The name is reserved: a person-added
marketplace may not take it, so a network source can never stand in for the shipped one."""

DEFAULT_RESEARCH_PLUGINS: Final[tuple[str, ...]] = ("currency-research",)
"""The research-methodology plugins in the default bundle, all from the shipped marketplace."""
