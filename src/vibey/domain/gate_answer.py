# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A gate is answered once: what identifies one answering request.

A human gate (ADR-0009) is answered by a compare-and-set on `answered_at IS NULL`: the
first answer stands, and every later one is refused, never written over it. A client
that retries -- a dropped connection, a replayed webhook, the Kubernetes operator's
level-triggered reconcile -- must be able to tell "my answer landed" from "someone
else's did". So every answer carries a **request id**:

- The same request id, with the same answer, is a no-op success: it reports the answer
  already recorded and writes nothing.
- A different request id, or the same one with a different answer, is refused
  (`GateAlreadyAnswered`), and nothing is written.

A caller that names no request id is a new request every time; `vibey answer` run twice
is two requests, so the second is refused. A caller that retries names one: a person's
client mints it once per intent (`--request-id`), and a reconciler derives it from what
it is applying (`derived`), so every pass of the same spec is the same request.

A request id is stored and printed, so it must be one line of visible text, not over
`MAX_LENGTH`. Pure: no I/O.
"""

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from typing import ClassVar, Final
from uuid import UUID

from vibey.domain.errors import InvalidAnswer


class GateAnswerRequestIds:
    """Checks and derives the id of one answering request. Pure.

    Declared by `interfaces/gate_answer_interface.py::GateAnswerRequestIdsInterface`."""

    MAX_LENGTH: ClassVar[int] = 200
    """Room for a UUID, a prefix and a digest; short enough for one line of output."""

    def checked(self, request_id: str) -> str:
        """`request_id` as given, or `InvalidAnswer` when it cannot be stored."""
        if not request_id:
            raise InvalidAnswer("a request id cannot be empty")
        if len(request_id) > self.MAX_LENGTH:
            raise InvalidAnswer(f"a request id is over {self.MAX_LENGTH} characters")
        if any(unicodedata.category(char).startswith(("C", "Z")) for char in request_id):
            raise InvalidAnswer(
                "a request id cannot contain spaces, control or formatting characters"
            )
        return request_id

    def derived(self, source: str, gate_id: UUID, answer: Mapping[str, object]) -> str:
        """The one request id `source` uses for this answer to this gate, every time.

        `source:` then the SHA-256 of the gate id and the answer as canonical JSON (keys
        sorted, no whitespace). A reconciler re-applying an unchanged spec derives the
        same id, so its replay is the no-op it should be; a changed answer derives
        another, so it is refused rather than written over the first."""
        canonical = json.dumps(
            {"gate_id": str(gate_id), "answer": answer},
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        digest = hashlib.sha256(canonical.encode("ascii")).hexdigest()
        return self.checked(f"{source}:{digest}")


GATE_ANSWER_REQUEST_IDS: Final = GateAnswerRequestIds()
"""The policy every answering path shares. Stateless, so one instance serves."""
