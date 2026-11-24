# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `vibey` the web tools run is the family's one finder (SP-LOOPS Phase 6): its behaviour is
proven in `vibey_runners.common`'s own suite; this runner's import path names the same object."""

from vibey_runners.common.infrastructure import vibey_command as common

from qwenloop.infrastructure.interfaces import VibeyCommandInterface
from qwenloop.infrastructure.vibey_command import VIBEY_COMMAND, VibeyCommand


def test_this_runners_vibey_command_is_the_familys_own() -> None:
    assert VibeyCommand is common.VibeyCommand
    assert VIBEY_COMMAND is common.VIBEY_COMMAND
    assert isinstance(VIBEY_COMMAND, VibeyCommandInterface)
