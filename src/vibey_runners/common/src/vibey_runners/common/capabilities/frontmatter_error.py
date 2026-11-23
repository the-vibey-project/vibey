# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A SKILL.md whose frontmatter cannot be read; the message is the reason a skill is skipped."""


class FrontmatterError(ValueError):
    """Raised by `SkillFrontmatter.parse`."""
