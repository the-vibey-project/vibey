# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for the delegated approver's deterministic check (vibey ADR-0016, ADR-0049).

Sub-doctrine 12.f puts the judgement in the operator's grant and leaves the approver only the
applying of it. The parts of that grant a machine can decide -- is it switched on, whose change
is this, where does it land, what does it touch, are the gates green, is the approving account
an author -- are decided here, by code, before any model reads a line of the diff. What is left
for the model is only what the gates cannot see.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ApprovalVerdictInterface(Protocol):
    """Whether every condition of `[unattended_approval]` held for one pull request head."""

    @property
    def number(self) -> int:
        """The pull request judged."""
        ...

    @property
    def head(self) -> str:
        """The head commit the conditions were judged against; empty when it was never read."""
        ...

    @property
    def refusals(self) -> tuple[str, ...]:
        """Every condition that did not hold, each as a sentence naming it. Empty only when
        all of them held -- and a condition that could not be read is one that did not."""
        ...

    @property
    def granted(self) -> bool:
        """True exactly when there is no refusal."""
        ...

    def report(self) -> str:
        """The verdict as printed: the head, then every refusal, or the grant and how to pin
        the head it was given for."""
        ...


@runtime_checkable
class ApprovalCheckInterface(Protocol):
    """Applies the operator's grant to one pull request and refuses on anything unproven."""

    def evaluate(self, number: int, head: str | None = None) -> ApprovalVerdictInterface:
        """Judge pull request `number` against every condition of the grant. With `head`, a
        pull request whose head is anything else is refused, so what was examined is what is
        approved. Never raises: a failure to read is a refusal (12.f)."""
        ...

    def run(self, number: int, head: str | None = None) -> int:
        """Print the verdict and return the command's exit status: 0 granted, 1 refused."""
        ...
