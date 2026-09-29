# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind defect classification.

Mirrors `vibey/domain/defect.py` (ADR-0016). Interfaces declare; they never consume. The
domain types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from vibey.domain.defect import DefectVerdict, FailureSignature


@runtime_checkable
class FailureNormalizerInterface(Protocol):
    """Reduces a failure's detail to what would be the same the next time the same fault
    hit, and hashes it with the failure's class."""

    def normalize(self, detail: str) -> str: ...

    def signature(self, failure_class: str, detail: str) -> FailureSignature: ...


@runtime_checkable
class RepeatedFailurePolicyInterface(Protocol):
    """Whether a job's recent failures, newest first, were all one failure."""

    def judge(
        self, recent: Sequence[FailureSignature], *, threshold: int
    ) -> DefectVerdict | None: ...


@runtime_checkable
class DefectAnswerPolicyInterface(Protocol):
    """What an answer to a `defect` gate does to its job."""

    def abandons(self, gate_kind: str, answer: Mapping[str, object] | None) -> bool:
        """True when the answer cancels the job instead of running it again."""
        ...
