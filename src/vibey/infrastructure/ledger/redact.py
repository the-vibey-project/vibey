# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction on write, ported in spirit from the *loop family: secrets must
never reach the ledger column, because the ledger is replicated into every
receiving worktree's .vibey/handoff/ledger.jsonl and read by whichever
engine is rotated in next. Pure text transform -- no I/O, safe to unit test
without a database, and applied by the ledger repository immediately
before a payload is persisted."""

import re
from bisect import bisect_right
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from vibey.domain.interfaces.publication_policy_interface import CredentialRedactorInterface
from vibey.infrastructure.ledger.interfaces.redact_interface import (
    CredentialShapeInterface,
    SecretTextRedactorInterface,
    TextRunIndexInterface,
)

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_NAMES = re.compile(
    r"(api[_-]?key|secret|password|passwd|token|auth[_-]?header|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)


Segment = tuple[str, str, int, int | None]
"""One part of a credential shape: `(separator, character class, minimum, maximum)`. The
separator is literal text that must come first (often empty); the class is a regex
character-class body such as `A-Za-z0-9`; `maximum` is None for an unbounded run."""


class TextRunIndex:
    """Where each maximal run of a character class ends, in one piece of text.

    A class is indexed the first time it is asked for, by one linear regex pass over the
    text, and every lookup after that is a binary search: so a credential's extent costs
    one lookup per segment, however many candidate credentials share one long run.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._runs: dict[str, tuple[list[int], list[int]]] = {}

    def end(self, char_class: str, index: int) -> int:
        if char_class not in self._runs:
            spans = [run.span() for run in re.finditer(f"[{char_class}]+", self._text)]
            self._runs[char_class] = ([start for start, _ in spans], [stop for _, stop in spans])
        starts, stops = self._runs[char_class]
        slot = bisect_right(starts, index) - 1
        if slot >= 0 and index < stops[slot]:
            return stops[slot]
        return index


@dataclass(frozen=True)
class CredentialShape:
    """One vendor's credential: a short prefix, then character-class runs.

    `prefix` is a regex that must match a bounded amount of text (a literal, or a literal
    with a character class in it, such as `xox[baprs]-`). Each segment then takes the
    longest run of its class, capped at its maximum, and fails below its minimum. That is
    exactly what the equivalent regex matches provided no separator character, and no
    character of the next segment's class, is in a run's own class -- true of every
    default shape, and checked against the regexes in the property suite.
    """

    prefix: str
    segments: tuple[Segment, ...]

    @cached_property
    def _starts(self) -> re.Pattern[str]:
        # A lookahead finds every start, including one inside another prefix.
        return re.compile(f"(?=({self.prefix}))")

    def matches(self, text: str, runs: TextRunIndexInterface) -> Iterator[tuple[int, int]]:
        for candidate in self._starts.finditer(text):
            stop = self._extent(text, candidate.end(1), runs)
            if stop is not None:
                yield candidate.start(), stop

    def _extent(self, text: str, position: int, runs: TextRunIndexInterface) -> int | None:
        for separator, char_class, minimum, maximum in self.segments:
            if not text.startswith(separator, position):
                return None
            position += len(separator)
            available = runs.end(char_class, position) - position
            if available < minimum:
                return None
            position += available if maximum is None else min(available, maximum)
        return position


_ALNUM = "A-Za-z0-9"
_BASE64URL = "A-Za-z0-9_-"


class SecretTextRedactor:
    """Replaces every vendor-shaped credential in free text with one `REDACTED` marker.

    A byte is replaced when any shape, matched at any start in the ORIGINAL text, covers
    it; overlapping matches are merged into one span before anything is replaced.

    Substituting one regex after another instead let a shorter shape inside a longer
    credential win: in `Bearer sk-AAAAAAAAAAAAAAAA.rest` the `sk-` key was replaced first,
    the Bearer pattern could no longer match across the marker, and "Bearer" and ".rest"
    -- bytes of the token -- survived. Resuming each regex where its last match ended
    missed a credential glued to the one before it (`sk-…sk-…`), and restarting it at
    every start instead was quadratic -- 31 seconds on `"xoxb-" * 100000`, a denial of
    service on the ledger append path. The shapes are matched at every start, each in
    one run lookup per segment (see `TextRunIndex`), so the cost is O(n log n) in the
    length of the text, never quadratic.

    Merged spans make the result independent of the order of the shapes, and idempotent:
    no default shape can match a square bracket, so none matches across or inside a
    marker, and a second pass finds nothing the first did not. Spans that only touch
    stay separate, one marker each.
    """

    DEFAULT_SHAPES: Final[tuple[CredentialShape, ...]] = (
        CredentialShape("sk-", (("", _ALNUM, 16, None),)),  # OpenAI / Anthropic secret keys
        CredentialShape("AKIA", (("", "0-9A-Z", 16, 16),)),  # AWS access key id
        CredentialShape("ghp_", (("", _ALNUM, 36, None),)),  # GitHub personal access token
        CredentialShape("xox[baprs]-", (("", "A-Za-z0-9-", 10, None),)),  # Slack tokens
        CredentialShape("AIza", (("", _BASE64URL, 35, 35),)),  # Google API key
        CredentialShape(  # JWT
            "eyJ",
            (("", _BASE64URL, 10, None), (".", _BASE64URL, 10, None), (".", _BASE64URL, 10, None)),
        ),
        CredentialShape("Bearer", (("", r"\s", 1, None), ("", "A-Za-z0-9._-", 10, None))),
    )
    """Vendor-shaped credentials, independent of the field name they appear under (a
    secret pasted into free text is still a secret)."""

    def __init__(
        self,
        shapes: Sequence[CredentialShapeInterface] = DEFAULT_SHAPES,
        index_factory: Callable[[str], TextRunIndexInterface] = TextRunIndex,
    ) -> None:
        self._shapes = tuple(shapes)
        self._index_factory = index_factory

    def redact(self, text: str) -> str:
        pieces: list[str] = []
        cursor = 0
        for start, stop in self.spans(text):
            pieces += [text[cursor:start], REDACTED]
            cursor = stop
        pieces.append(text[cursor:])
        return "".join(pieces)

    def spans(self, text: str) -> list[tuple[int, int]]:
        runs = self._index_factory(text)
        found = sorted(span for shape in self._shapes for span in shape.matches(text, runs))
        merged: list[tuple[int, int]] = []
        for start, stop in found:
            if merged and start < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
            else:
                merged.append((start, stop))
        return merged


_TEXT_REDACTOR: Final[SecretTextRedactorInterface] = SecretTextRedactor()


def _redact_value(key: str | None, value: object) -> object:
    if key is not None and _SENSITIVE_KEY_NAMES.search(key):
        return REDACTED
    if isinstance(value, str):
        return _TEXT_REDACTOR.redact(value)
    if isinstance(value, Mapping):
        return redact_payload(value)
    if isinstance(value, list | tuple):
        return [_redact_value(None, item) for item in value]
    return value


def redact_payload(payload: Mapping[str, object]) -> dict[str, object]:
    """Recursively redacts sensitive key names and vendor-shaped secret
    patterns found anywhere in the payload, including inside nested
    mappings, lists, and free text."""
    return {key: _redact_value(key, value) for key, value in payload.items()}


def contains_secret(payload: Mapping[str, object]) -> bool:
    """True if redact_payload would change anything -- useful for a fast
    assertion in tests without diffing the whole structure."""
    return redact_payload(payload) != dict(payload)


class CredentialRedactor:
    """`redact_payload` as an object, for the publication policy's last pass.

    The seam is declared where it is consumed, as the domain's
    `CredentialRedactorInterface` (domain/publication_policy.py), so the policy
    stays pure and the credential patterns stay here, in one place.
    """

    def redact(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        return redact_payload(payload)


CREDENTIAL_REDACTOR: Final[CredentialRedactorInterface] = CredentialRedactor()
"""The redactor `vibey ledger export` gives the publication policy. Annotated with
the interface so `mypy --strict` checks the class against its declared seam."""


__all__ = [
    "CREDENTIAL_REDACTOR",
    "REDACTED",
    "CredentialRedactor",
    "CredentialShape",
    "SecretTextRedactor",
    "TextRunIndex",
    "contains_secret",
    "redact_payload",
]
