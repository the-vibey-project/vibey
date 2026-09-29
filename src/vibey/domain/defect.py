# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Telling a defect from bad luck: when a job's failures are all the same one.

An exhausted job used to park on a gate offering more attempts whatever it had failed
with. When every recent failure is the same failure, more attempts cannot change the
outcome -- the operator granted attempts six times on two jobs that failed identically
each time. So each failure is reduced to a **signature**: its class and its detail with
the parts that differ between two runs of the same fault -- ids, timestamps, durations,
addresses, temporary paths, attempt counters -- replaced by placeholders, then hashed.
When the last K signatures are one signature (`RepeatedFailurePolicy`), the job is a
**defect**, and the worker raises a `defect` gate that offers no grant.

Pure: text in, verdicts out. The worker records each failure's signature on the ledger
(`JobFailed`) and reads the last K back; the decision is made here.
"""

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from vibey.domain.interfaces.defect_interface import (
    DefectAnswerPolicyInterface,
    FailureNormalizerInterface,
    RepeatedFailurePolicyInterface,
)
from vibey.domain.job import DEFECT_GATE_KIND

DEFAULT_IDENTICAL_FAILURES: Final = 3
"""How many consecutive identical failures make a defect when `[queue.defect]` says
nothing: two could be a coincidence, three is a pattern."""

MIN_IDENTICAL_FAILURES: Final = 2
"""One failure is always identical to itself, so the smallest meaningful run is two."""

EXCERPT_LENGTH: Final = 240
"""How much of a normalized detail a signature carries for a person to read."""

DEFECT_REQUEUE: Final = "requeue"
DEFECT_ABANDON: Final = "abandon"
DEFECT_OPTIONS: Final = (DEFECT_REQUEUE, DEFECT_ABANDON)
"""A defect gate's answers: run the job once more after a fix has landed, or stop it."""


@dataclass(frozen=True, slots=True)
class FailureSignature:
    """One failure, reduced to what would be the same the next time the same fault hit."""

    failure_class: str
    digest: str
    """The hash of the class and the whole normalized detail; the identity compared."""
    excerpt: str
    """The normalized detail's head, for a person. Never compared."""

    def payload(self) -> dict[str, object]:
        return {
            "failure_class": self.failure_class,
            "signature": self.digest,
            "excerpt": self.excerpt,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "FailureSignature | None":
        """The signature a `JobFailed` event recorded, or None for a payload no vibey wrote
        as one: such a record is skipped, never guessed at."""
        failure_class = payload.get("failure_class")
        digest = payload.get("signature")
        excerpt = payload.get("excerpt", "")
        if not (
            isinstance(failure_class, str) and isinstance(digest, str) and isinstance(excerpt, str)
        ):
            return None
        return cls(failure_class=failure_class, digest=digest, excerpt=excerpt)


_RULES: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "<uuid>",
    ),
    (
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?"
            r"(?:Z|[+-]\d{2}:?\d{2})?)?"
        ),
        "<time>",
    ),
    (re.compile(r"\b\d{1,2}:\d{2}:\d{2}(?:[.,]\d+)?\b"), "<time>"),
    (re.compile(r"\b0x[0-9a-fA-F]+\b"), "<addr>"),
    (re.compile(r"(?:/private)?/(?:tmp|var/folders)/\S+"), "<tmp>"),
    (
        re.compile(
            r"\b\d+(?:\.\d+)?\s?(?:ms|us|µs|ns|s|secs?|seconds?|mins?|minutes?|h|hrs?|hours?)\b"
        ),
        "<duration>",
    ),
    (
        re.compile(
            r"\b(attempts?|retry|retries|tries|try|round|rounds|pass)\s*#?\s*\d+"
            r"(?:\s*(?:/|of)\s*\d+)?",
            re.IGNORECASE,
        ),
        r"\1 <n>",
    ),
    (re.compile(r"\b(?=[0-9a-f]*\d)[0-9a-f]{7,}\b"), "<hex>"),
    (re.compile(r"\b\d{5,}\b"), "<n>"),
    (re.compile(r"\s+"), " "),
)
"""Applied in order. Ids before timestamps before numbers, so a UUID's digit runs are not
read as a number first; whitespace last, so a placeholder never glues two words together."""


class FailureNormalizer:
    """Reduces a failure to its signature. Stateless."""

    def normalize(self, detail: str) -> str:
        text = detail
        for pattern, replacement in _RULES:
            text = pattern.sub(replacement, text)
        return text.strip()

    def signature(self, failure_class: str, detail: str) -> FailureSignature:
        normalized = self.normalize(detail)
        digest = hashlib.sha256(f"{failure_class}\x1f{normalized}".encode()).hexdigest()[:16]
        return FailureSignature(
            failure_class=failure_class,
            digest=digest,
            excerpt=normalized[:EXCERPT_LENGTH],
        )


FAILURE_NORMALIZER: Final[FailureNormalizerInterface] = FailureNormalizer()
"""The normalizer every recorder and reader shares."""


@dataclass(frozen=True, slots=True)
class DefectVerdict:
    """A job whose most recent failures were all one failure."""

    signature: FailureSignature
    identical: int
    """How many of the most recent failures, counted back from the latest, share it."""


class RepeatedFailurePolicy:
    """Judges a job's recent failures, newest first. Stateless."""

    def judge(self, recent: Sequence[FailureSignature], *, threshold: int) -> DefectVerdict | None:
        """A verdict when the newest `threshold` failures share one signature; None when
        they do not, when fewer are recorded, or when `threshold` switches the check off
        (below `MIN_IDENTICAL_FAILURES`, which `[queue.defect]` spells 0)."""
        if threshold < MIN_IDENTICAL_FAILURES or len(recent) < threshold:
            return None
        latest = recent[0]
        identical = 0
        for signature in recent:
            if signature.digest != latest.digest:
                break
            identical += 1
        if identical < threshold:
            return None
        return DefectVerdict(signature=latest, identical=identical)


REPEATED_FAILURE_POLICY: Final[RepeatedFailurePolicyInterface] = RepeatedFailurePolicy()


class DefectAnswerPolicy:
    """What an answer to a `defect` gate does to its job. Stateless."""

    def abandons(self, gate_kind: str, answer: Mapping[str, object] | None) -> bool:
        """True only for a defect gate answered `{"choice": "abandon"}`: that job is
        cancelled when the answer lands. Every other answer -- `requeue`, or anything a
        person typed -- runs it once more, the way "answer anything to retry" always has."""
        return (
            gate_kind == DEFECT_GATE_KIND
            and answer is not None
            and answer.get("choice") == DEFECT_ABANDON
        )


DEFECT_ANSWERS: Final[DefectAnswerPolicyInterface] = DefectAnswerPolicy()
