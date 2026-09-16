# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The delivery correlation id: one identifier for one delivery, end to end.

A delivery is everything a project's run does across the six phases and every
repository it touches. Until now the only identifiers a reader could join on
were ``project_id``, ``cycle`` and per-job ids, so reconstructing one delivery
from logs meant joining by hand (issue #89).

**The id is keyed on the project alone, never on (project, cycle).** ``cycle``
increments on every REVIEW loop-back (``application/review_triage_handler.py``),
so keying on it would mint a fresh id each time the delivery went round again --
several ids for the one delivery, which is the opposite of the point. ``cycle``
stays what it already is: a field beside the id, not part of it.

Derivation is ``uuid5`` rather than ``uuid4``: the same project yields the same
delivery id in every worker, in every process, after every restart, with nothing
to store and nothing to hand across a process boundary. That also keeps this
module inside ``domain/``'s purity rule -- no clock, no randomness, no I/O
(ADR-0017's separation of what is derivable from what must be observed).

The ``correlation_id`` already on ``LedgerEvent`` is a different, narrower thing:
one work *thread* within a delivery, minted per item. The two coexist -- this one
is the outer scope, that one the inner.
"""

from dataclasses import dataclass
from uuid import NAMESPACE_URL, UUID, uuid5

# The uri the default namespace is folded from, written out rather than
# pasted in as an opaque literal so a reader can re-derive it. A deployment
# that wants its deliveries in a namespace of its own passes one to
# ``DeliveryCorrelation`` instead of editing this (ADR-0018).
DELIVERY_NAMESPACE_URI = "https://the-vibey-project.github.io/vibey/delivery"

DELIVERY_NAMESPACE = uuid5(NAMESPACE_URL, DELIVERY_NAMESPACE_URI)


@dataclass(frozen=True, slots=True)
class DeliveryId:
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

    def for_project(self, project_id: UUID) -> DeliveryId:
        """The delivery id for ``project_id``. Same input, same id, always."""
        return DeliveryId(uuid5(self._namespace, str(project_id)))
