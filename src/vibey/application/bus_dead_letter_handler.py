# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A dead letter, parked for a person, and what happens when they answer (ADR-0056).

The reaper never deletes a dead letter. It parks one as a `bus.dead_letter` job and raises
a `bus_dead_lettered` gate beside it, in one transaction, with the message's body, the
queue it died on and the broker's reason in the job's payload. No worker waits on the
answer: the job holds no lease while it is parked.

The answer re-readies the job, and this handler settles it:

- ``--choice replay`` publishes the body back to the queue it was dead-lettered from.
  Delivery is at least once -- a worker that dies after the publish and before the ack
  publishes it again on the retry -- so the consumer must be idempotent, as every vibey
  consumer is. A body the broker cut short, or one that is not a JSON object, is never
  replayed: the gate is raised again, saying so.
- ``--choice dismiss`` settles it with nothing sent.

Either way the broker's copy stays on the dead-letter queue as evidence; clearing it is a
person's act, never a reaper's. Any other answer raises the gate again.
"""

from collections.abc import Mapping
from typing import Final

from vibey.application.dto import HumanGateRecord, HumanGateRequest, JobRecord
from vibey.application.interfaces.bus import BusPort
from vibey.application.interfaces.gates import HumanGateRepository
from vibey.application.interfaces.queue import Outcome, Park, Success
from vibey.application.interfaces.queue_reap import BusDeadLetterGateInterface

BUS_DEAD_LETTER_KIND: Final = "bus.dead_letter"
BUS_DEAD_LETTER_GATE_KIND: Final = "bus_dead_lettered"
REPLAY: Final = "replay"
DISMISS: Final = "dismiss"


class BusDeadLetterGate:
    """The gate a parked dead letter carries: what died, where, why, and the two answers.

    Every value shown comes from the message's own headers, which its publisher wrote, so
    each is quoted and cut to `SHOWN_CHARS`: data for a person to read, never text that can
    pass for the prompt's own (SD-01 §4).
    """

    SHOWN_CHARS: Final = 200

    def request(self, payload: Mapping[str, object], *, note: str = "") -> HumanGateRequest:
        replayable = isinstance(payload.get("payload"), Mapping) and not payload.get(
            "truncated", False
        )
        origin = self._shown(payload.get("origin_queue"))
        lead = f"{note} " if note else ""
        replay = (
            f"`--choice {REPLAY}` publishes it back to {origin} "
            "(at least once: its consumer must be idempotent); "
            if replayable
            else "It cannot be replayed: its body is not a whole JSON object. "
        )
        return HumanGateRequest(
            kind=BUS_DEAD_LETTER_GATE_KIND,
            prompt=(
                f"{lead}A message dead-lettered from {origin} "
                f"(reason: {self._shown(payload.get('reason'))}) waits on "
                f"{self._shown(payload.get('queue'))} as {self._shown(payload.get('identity'))}. "
                f"Nothing retries it on its own. {replay}"
                f"`--choice {DISMISS}` settles it with nothing sent. The broker's copy stays "
                "on the dead-letter queue either way."
            ),
            options=(REPLAY, DISMISS) if replayable else (DISMISS,),
        )

    def _shown(self, value: object) -> str:
        return repr(str(value)[: self.SHOWN_CHARS])


BUS_DEAD_LETTER_GATE: Final[BusDeadLetterGateInterface] = BusDeadLetterGate()


class BusDeadLetterHandler:
    """Settles a parked `bus.dead_letter` job by its gate's answer."""

    def __init__(
        self,
        *,
        gates: HumanGateRepository,
        bus: BusPort,
        gate: BusDeadLetterGateInterface = BUS_DEAD_LETTER_GATE,
    ) -> None:
        self._gates = gates
        self._bus = bus
        self._gate = gate

    async def handle(self, job: JobRecord) -> Outcome:
        choice = self._choice(await self._gates.latest_for_job(job.id))
        identity = str(job.payload.get("identity"))
        if choice == DISMISS:
            return Success({"dismissed": identity})
        if choice == REPLAY:
            body = job.payload.get("payload")
            origin = job.payload.get("origin_queue")
            if (
                isinstance(body, Mapping)
                and isinstance(origin, str)
                and origin
                and not job.payload.get("truncated", False)
            ):
                await self._bus.publish(origin, dict(body))
                return Success({"replayed": identity, "to": origin})
            return Park(
                self._gate.request(job.payload, note="That dead letter cannot be replayed.")
            )
        return Park(
            self._gate.request(job.payload, note=f"Answer --choice {REPLAY} or --choice {DISMISS}.")
        )

    @staticmethod
    def _choice(gate: HumanGateRecord | None) -> str | None:
        if gate is None or gate.answer is None:
            return None
        value = gate.answer.get("choice")
        return value.strip().lower() if isinstance(value, str) else None
