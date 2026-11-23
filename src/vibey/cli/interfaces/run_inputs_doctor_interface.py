# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/run_inputs_doctor.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class RunInputsDoctorInterface(Protocol):
    """`vibey doctor`'s `run-inputs` section: which run input store is in force, the config file
    it came from, and whether it answers (SP-LOOPS Phase 3c, ADR-0105)."""

    def doctor_lines(self) -> tuple[list[str], bool]:
        """The section's one line, and whether it passed. Never raises (an exception is an
        `UNKNOWN` line), and never prints a credential's value."""
        ...
