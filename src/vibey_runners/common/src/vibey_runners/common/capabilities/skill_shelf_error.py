# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A name or page a run's skill shelf does not hold, or a text it cannot read now (SP-LOOPS
Phase 5). The message names the shelf's size and the page count, so the model can ask again; a
loop's tool hands it back as a tool error, never raises it out of a turn."""


class SkillShelfError(LookupError):
    """Raised by `SkillShelf.page` and `SkillShelf.read`."""
