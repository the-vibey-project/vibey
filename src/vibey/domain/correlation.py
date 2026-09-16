# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The delivery correlation id: one identifier for one delivery, end to end.

A delivery is everything a project's run does across the six phases and every
repository it touches. ``event.correlation_id`` was minted with ``uuid4()`` at
roughly ten separate sites, so one delivery left behind ten unrelated ids and
reconstructing it from the ledger meant joining by hand (issue #89). This module
derives the one id all of them now write.

**The id is keyed on the project alone, never on (project, cycle).** ``cycle``
increments on every REVIEW loop-back (``application/review_triage_handler.py``),
so keying on it would mint a fresh id each time the delivery went round again --
several ids for the one delivery, which is the opposite of the point. ``cycle``
stays what it already is: a field beside the id, not part of it.

Derivation is ``uuid5`` rather than ``uuid4``: the same project yields the same
correlation id in every worker, in every process, after every restart, with
nothing to store and nothing to hand across a process boundary. That also keeps
this module inside ``domain/``'s purity rule -- no clock, no randomness, no I/O.

What used to be carried by ``correlation_id`` -- "these events came from one
engine run" -- moves to ``LedgerEvent.causation_id``, which already existed and
was always ``None``. ``correlation_id`` is now the outer scope (the delivery)
and ``causation_id`` the inner (the run that caused the event).
"""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface

# The uri the default namespace is folded from, written out rather than
# pasted in as an opaque literal so a reader can re-derive it. A deployment
# that wants its deliveries in a namespace of its own passes one to
# ``DeliveryCorrelation`` instead of editing this (ADR-0018).
DELIVERY_NAMESPACE_URI = "https://the-vibey-project.github.io/vibey/delivery"

DELIVERY_NAMESPACE = uuid5(NAMESPACE_URL, DELIVERY_NAMESPACE_URI)


@dataclass(frozen=True, slots=True)
class CorrelationId:
    """One delivery's correlation id. Frozen, because a delivery that
    acquires a second id has stopped being traceable."""

    value: UUID

    def __str__(self) -> str:
        return str(self.value)


class DeliveryCorrelation:
    """Derives a delivery's correlation id from the project it belongs to."""

    def __init__(self, namespace: UUID = DELIVERY_NAMESPACE) -> None:
        self._namespace = namespace

    @property
    def namespace(self) -> UUID:
        """The namespace every id from this deriver is folded into."""
        return self._namespace

    def for_project(self, project_id: UUID) -> CorrelationId:
        """The delivery's correlation id. Same project, same id, always."""
        return CorrelationId(uuid5(self._namespace, str(project_id)))


# The published default deriver, and the default every write site takes as a
# parameter so a deployment can substitute its own namespace without editing
# call sites (ADR-0018). Sharing one instance is safe because derivation holds
# no state; a constant rather than a call in a default argument so the binding
# is evaluated once and is visibly the same object everywhere.
#
# The annotation is load-bearing. A `runtime_checkable` Protocol only
# hasattr-checks member *names* at runtime, so `isinstance` would still pass
# after a signature drifted; this assignment is what makes `mypy --strict`
# verify that `DeliveryCorrelation` -- and, through its return type,
# `CorrelationId` -- actually satisfies the declared seam.
DELIVERY_CORRELATION: DeliveryCorrelationInterface = DeliveryCorrelation()
