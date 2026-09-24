# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the pre-push gate's scope: does this push carry code at all (vibey ADR-0016)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PushVerdictInterface(Protocol):
    """Whether a push carries code, and the one sentence that says why."""

    @property
    def carries_code(self) -> bool: ...

    @property
    def reason(self) -> str: ...


@runtime_checkable
class PushScopeInterface(Protocol):
    """Judges the refs git hands a pre-push hook, by the gate's own rule.

    A push carries no code only when every ref it updates is outside `refs/heads/` and
    `refs/tags/` and every commit it sends is the empty tree with no parents. Every other
    push -- and every push whose objects cannot be read -- carries code, and the full gate
    judges it.
    """

    def judge(self, pre_push_input: str) -> PushVerdictInterface:
        """The verdict on git's pre-push standard input: one line per ref,
        `<local ref> <local object> <remote ref> <remote object>`."""
        ...

    def is_empty_root(self, commit: str) -> tuple[bool, str]:
        """Whether `commit` is a commit whose tree is empty and which has no parents; when
        it is not, the reason names what it carries instead."""
        ...
