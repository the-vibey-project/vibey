# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/intake_trust.py` implements. Interfaces declare; they never consume.

The triaged-delivery bridge turns a GitHub issue into the first words of a DESIGN ledger. Before
it does, `IntakeTrust` asks the forge -- in the storm's one provenance query -- whose words the
issue carries and who applied the labels that queued it, and judges both against the reviewed
trust grant with the storm's own `IssueGate` (ADR-0053, sub-doctrine 12.j). `IntakeFrame` then
quotes the admitted text through `PromptShield` so DESIGN reads it as data.
"""

from pathlib import Path
from types import ModuleType
from typing import Protocol


class IntakeVerdictInterface(Protocol):
    """An admitted issue: the exact text judged, and the evidence it was judged on."""

    @property
    def number(self) -> int: ...

    @property
    def title(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def author(self) -> str: ...

    @property
    def accounts(self) -> tuple[str, ...]:
        """Every account that wrote the text: the author, each editor and each renamer."""
        ...

    @property
    def curators(self) -> tuple[str, ...]:
        """Whoever last applied each managed label the issue carries."""
        ...

    @property
    def grant(self) -> str:
        """Where the trust grant was read: `<ref>@<sha>`."""
        ...


class IntakeTrustInterface(Protocol):
    """Admits an issue's text to the bridge, or says why not."""

    def admit(self, number: int) -> IntakeVerdictInterface:
        """The verdict for an admitted issue. Raises `Untrusted` when a stranger wrote or
        labelled it (a verdict: hold it for a person), and `ProvenanceUnreadable` when the
        forge or the grant could not be read (not a verdict: retry it)."""
        ...


class IntakeFrameInterface(Protocol):
    """The DESIGN intake: the harness's provenance line, then the issue quoted as data."""

    def text(self, repository: str, verdict: IntakeVerdictInterface) -> str: ...

    def suspicious(self, verdict: IntakeVerdictInterface) -> bool:
        """PromptShield's phrase heuristic -- recorded as evidence, never a gate."""
        ...

    def name(self, verdict: IntakeVerdictInterface) -> str:
        """A one-line project name: the issue number and its control-free title."""
        ...


class StormToolsInterface(Protocol):
    """The storm's tools directory, and its trust seam loaded from it."""

    @property
    def directory(self) -> Path: ...

    def module(self) -> ModuleType:
        """`storm_trust`, loaded once. Raises RuntimeError when the directory lacks it."""
        ...
