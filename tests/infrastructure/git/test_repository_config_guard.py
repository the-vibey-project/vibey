# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""RepositoryConfigGuard: which keys, in which scopes, stop vibey's git.

The real-git attack is reproduced in test_repository_controlled_execution.py; these pin
the rule itself against `git config --list --show-scope -z` listings."""

from pathlib import Path

import pytest

from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.git.interfaces import RepositoryConfigGuardInterface
from vibey.infrastructure.git.repository_config_guard import (
    REFUSED_KEYS,
    REPOSITORY_SCOPES,
    RepositoryConfigGuard,
    RepositoryExecutionRefused,
)


class Listing:
    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.calls: list[tuple[str, ...]] = []

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        self.calls.append(argv)
        return self.result


def _listing(*entries: tuple[str, str]) -> str:
    return "".join(f"{scope}\0{entry}\0" for scope, entry in entries)


def _guard() -> RepositoryConfigGuard:
    return RepositoryConfigGuard(Listing(CommandResult(0, "", "")))


def test_the_rule_is_exactly_filter_and_merge_drivers_in_the_repositorys_own_scopes() -> None:
    assert frozenset({"local", "worktree"}) == REPOSITORY_SCOPES
    assert [p.pattern for p in REFUSED_KEYS] == [
        r"filter\..+\.(clean|smudge|process)",
        r"merge\..+\.driver",
    ]


@pytest.mark.parametrize(
    "key",
    [
        "filter.planted.smudge",
        "filter.planted.clean",
        "filter.planted.process",
        "filter.With.Dots.In.Name.smudge",
        "merge.planted.driver",
    ],
)
@pytest.mark.parametrize("scope", ["local", "worktree"])
def test_a_driver_the_repository_declares_is_refused(key: str, scope: str) -> None:
    assert _guard().offending(_listing((scope, f"{key}\nsh -c evil"))) == (key,)


def test_a_valueless_driver_key_is_refused_too() -> None:
    assert _guard().offending(_listing(("local", "merge.planted.driver"))) == (
        "merge.planted.driver",
    )


@pytest.mark.parametrize("scope", ["global", "system", "command", "unknown"])
def test_a_driver_outside_the_repositorys_scopes_is_not_refused(scope: str) -> None:
    assert _guard().offending(_listing((scope, "filter.lfs.smudge\ngit-lfs smudge %f"))) == ()


@pytest.mark.parametrize(
    "entry",
    [
        "filter.lfs.required\ntrue",
        "merge.conflictstyle\ndiff3",
        "core.hookspath\n.githooks",
        "core.fsmonitor\ntrue",
        "user.name\nfilter.x.smudge",
    ],
)
def test_other_repository_keys_are_left_to_the_executor(entry: str) -> None:
    # hooksPath and fsmonitor are switched off by the executor's own -c, which
    # outranks the repository; refusing them would refuse every repository that
    # keeps its hooks in-tree.
    assert _guard().offending(_listing(("local", entry))) == ()


def test_each_refused_key_is_named_once() -> None:
    listing = _listing(
        ("local", "filter.a.smudge\nx"),
        ("worktree", "filter.a.smudge\ny"),
        ("local", "merge.b.driver\nz"),
    )
    assert _guard().offending(listing) == ("filter.a.smudge", "merge.b.driver")


async def test_check_reads_the_config_git_will_use_there_and_refuses_a_driver() -> None:
    executor = Listing(CommandResult(0, _listing(("local", "merge.x.driver\nevil")), ""))

    with pytest.raises(RepositoryExecutionRefused, match=r"merge\.x\.driver") as refused:
        await RepositoryConfigGuard(executor).check(Path("/repo"))

    assert executor.calls == [("git", "-C", "/repo", "config", "--list", "--show-scope", "-z")]
    assert refused.value.keys == ("merge.x.driver",)
    assert refused.value.directory == Path("/repo")
    assert "global git config" in str(refused.value)


async def test_a_config_that_cannot_be_read_is_refused_not_passed() -> None:
    executor = Listing(CommandResult(128, "", "fatal: bad config line 3"))

    with pytest.raises(RepositoryExecutionRefused, match="could not be read.*bad config"):
        await RepositoryConfigGuard(executor).check(Path("/repo"))


async def test_a_clean_config_passes() -> None:
    executor = Listing(CommandResult(0, _listing(("local", "user.name\nTest")), ""))
    await RepositoryConfigGuard(executor).check(Path("/repo"))


def test_the_guard_declares_its_interface() -> None:
    assert isinstance(_guard(), RepositoryConfigGuardInterface)
