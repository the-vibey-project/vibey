# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind deciding and recording a project's abandonment.

Mirrors `vibey/domain/abandonment.py` (ADR-0016). Interfaces declare; they never consume.
The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from vibey.domain.abandonment import AbandonmentVerdict
    from vibey.domain.phase import PhaseState


@runtime_checkable
class AbandonmentPolicyInterface(Protocol):
    """Whether a project may be abandoned, and the words its record is made of. Pure."""

    @property
    def guard(self) -> str:
        """The rule the `PhaseTransitioned` into abandoned names as its `guard`."""
        ...

    @property
    def unsettled_states(self) -> frozenset[str]:
        """The job states an abandonment cancels: every one a job can still leave."""
        ...

    def reason(self, text: str) -> str:
        """`text`, stripped, when it can be recorded. Raises `InvalidAbandonment` for an
        empty, over-long or control-bearing reason."""
        ...

    def actor(self, label: str | None, *, account: str) -> str:
        """`label`, stripped, when given and recordable; else `account`. Raises
        `InvalidAbandonment` for a label that cannot be recorded."""
        ...

    def decide(self, state: PhaseState) -> AbandonmentVerdict:
        """`ABANDON` when the phase machine allows the move into abandoned,
        `ALREADY_ABANDONED` when the project is there already. Raises
        `AbandonmentRefused` for a done project, a phase with no edge to abandoned, or a
        phase this vibey does not know."""
        ...

    def transition_attribution(
        self,
        *,
        reason: str,
        by: str,
        account: str,
        cancelled_jobs: Sequence[UUID],
        withdrawn_gates: Sequence[UUID],
    ) -> dict[str, object]:
        """The fields an operator's abandonment adds to its `PhaseTransitioned` payload."""
        ...

    def withdrawn_answer(self) -> dict[str, object]:
        """What a withdrawn gate's `answer` column holds: it was closed, not answered."""
        ...

    def request_id(self, project_id: UUID) -> str:
        """The request id a withdrawn gate records, so a later answer is refused as a
        second one and names the abandonment that closed it."""
        ...

    def withdrawal_payload(
        self,
        *,
        gate_id: UUID,
        gate_kind: str,
        job_id: UUID | None,
        request_id: str,
        by: str,
        account: str,
    ) -> dict[str, object]:
        """The `GateWithdrawn` payload for one gate the abandonment closed."""
        ...
