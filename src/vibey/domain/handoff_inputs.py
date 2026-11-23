# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which run inputs a handed-off run must be given (SP-LOOPS Phase 3c, Task 7).

A BUILD run that winds down is followed by a job whose prompt starts with the seed the no-loss
gate verified, byte for byte. The run inputs follow that seed: the follow-up is given exactly the
inputs the outgoing run was given, which its `vibey_run_inputs_given` event records. The
wind-down pins those digests into the follow-up's payload (`HANDOFF_INPUTS_KEY`); the incoming
run is given them and nothing else, so an input added after the handoff is not slipped in and a
lowered limit does not drop one. This is a handoff check beside the gate, not a gate rule
(operator ruling OR-5): `noloss.verify` and its ten rules are unchanged.

Pure: no I/O. Declared by `interfaces/handoff_inputs_interface.py::HandoffInputsInterface`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final
from uuid import UUID

from vibey.domain.interfaces.handoff_inputs_interface import HandoffInputsInterface
from vibey.domain.ledger import EventKind, LedgerEvent
from vibey.domain.run_input import GIVEN_ARTIFACT_TYPE, RUN_INPUT_RULE


class HandoffInputs:
    """Declared by `interfaces/handoff_inputs_interface.py::HandoffInputsInterface`."""

    def pinned(self, events: Sequence[LedgerEvent], job_id: UUID) -> tuple[str, ...] | None:
        given = [
            event
            for event in events
            if event.kind is EventKind.ARTIFACT_PRODUCED
            and event.job_id == job_id
            and event.payload.get("artifact_type") == GIVEN_ARTIFACT_TYPE
        ]
        if not given:
            return None
        latest = max(given, key=lambda event: event.seq)
        digests = latest.payload.get("digests")
        if not isinstance(digests, list) or not all(
            isinstance(digest, str) and RUN_INPUT_RULE.is_digest(digest) for digest in digests
        ):
            raise ValueError(
                f"the inputs event at seq {latest.seq} for job {job_id} does not list digests; "
                "the inputs a handed-off run must be given cannot be pinned"
            )
        return tuple(digests)


HANDOFF_INPUTS: Final[HandoffInputsInterface] = HandoffInputs()
"""The one rule. Annotated with the interface so `mypy --strict` checks the class against it."""
