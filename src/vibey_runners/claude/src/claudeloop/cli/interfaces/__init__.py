# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the CLI layer declares (ADR-0016). Interfaces declare; they never consume."""

from claudeloop.cli.interfaces.outcome_interface import RunOutcomeReporterInterface

__all__ = ["RunOutcomeReporterInterface"]
