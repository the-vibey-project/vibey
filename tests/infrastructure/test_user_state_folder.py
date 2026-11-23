# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The person's own state folder (SP-LOOPS Phase 3, fix round 1: R-A). The platform lookup is a
stand-in, so nothing here reads the real home folder's state."""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_state_path

from vibey.infrastructure.interfaces.user_state_folder_interface import UserStateFolderInterface
from vibey.infrastructure.user_state_folder import UserStateFolder


def test_the_folder_is_the_platforms_state_folder_for_vibey() -> None:
    seen: list[str] = []

    def lookup(app: str) -> Path:
        seen.append(app)
        return Path("/home/person/.local/state") / app

    folder = UserStateFolder(lookup)
    assert folder.path() == Path("/home/person/.local/state/vibey")
    assert folder.inputs() == Path("/home/person/.local/state/vibey/inputs")
    assert seen == ["vibey", "vibey"]


def test_a_relative_state_folder_is_never_the_folder_vibey_runs_in() -> None:
    folder = UserStateFolder(lambda app: Path("relative") / app)
    assert folder.path() == Path.home() / ".local" / "state" / "vibey"


def test_the_default_lookup_is_platformdirs() -> None:
    expected = Path(user_state_path("vibey"))
    if not expected.is_absolute():  # the same rule, so the test holds on any platform
        expected = Path.home() / ".local" / "state" / "vibey"
    assert UserStateFolder().path() == expected


def test_the_folder_meets_its_interface() -> None:
    assert isinstance(UserStateFolder(), UserStateFolderInterface)
