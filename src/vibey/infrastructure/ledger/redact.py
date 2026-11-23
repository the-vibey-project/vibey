# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction on write, ported in spirit from the *loop family: secrets must
never reach the ledger column, because the ledger is replicated into every
receiving worktree's .vibey/handoff/ledger.jsonl and read by whichever
engine is rotated in next. Pure text transform -- no I/O, safe to unit test
without a database, and applied by the ledger repository immediately
before a payload is persisted."""

import heapq
import re
import sys
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from functools import cache, cached_property
from typing import Final, cast

from vibey.domain.interfaces.publication_policy_interface import CredentialRedactorInterface
from vibey.infrastructure.ledger.interfaces.redact_interface import (
    CredentialShapeInterface,
    RunCursorFactory,
    RunCursorInterface,
    SecretTextRedactorInterface,
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


class RunCursor:
    """Where a run of one character class ends, remembering only the last run it read.

    Lookups for one segment of one shape never move backwards (each candidate starts
    after the one before it, and every segment's extent grows with its start), so a
    lookup inside the remembered run costs nothing and any other reads only characters
    no earlier lookup read. Each cursor therefore reads each character at most once, in
    constant memory -- unlike an index of every run in the text, which held 70 times the
    text in memory once a single prefix appeared in it.
    """

    def __init__(self, text: str, run: re.Pattern[str]) -> None:
        self._text = text
        self._run = run
        self._low = 0
        self._high = 0
        self._scanned = 0

    @property
    def scanned(self) -> int:
        return self._scanned

    def end(self, index: int) -> int:
        if self._low <= index < self._high:
            return self._high
        # `[class]*` matches at every index, so the match is never None.
        stop = cast(re.Match[str], self._run.match(self._text, index)).end()
        self._scanned += stop - index
        self._low, self._high = index, stop
        return stop


_PREFIX_ATOM = r"\\[sSdDwW]|\\[^A-Za-z0-9]|\[(?:\\.|[^\]\\])+\]|[^\\\[\]()*+?{}|.^$]"
"""One character's worth of prefix: an escaped punctuation mark, a class shorthand, a
character class, or a plain character. No quantifier, group, alternation, anchor or dot."""


@dataclass(frozen=True)
class CredentialShape:
    """One vendor's credential: a short prefix, then character-class runs.

    The prefix is a fixed number of single-character atoms (see `_PREFIX_ATOM`). Each
    segment then takes the longest run of its class, capped at its maximum, and fails
    below its minimum. That is exactly what the equivalent regex matches when no
    separator character, and no character of the next segment's class, is in a run's
    own class; and redaction stays idempotent when nothing in a shape can match a
    square bracket or match inside the marker. `__post_init__` refuses any shape that
    breaks one of those conditions, so a configured shape cannot silently diverge.
    """

    prefix: str
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        self._check_prefix()
        for index, (separator, char_class, minimum, maximum) in enumerate(self.segments):
            if minimum < 0:
                raise ValueError(f"segment {index}: the minimum {minimum} is negative")
            if maximum is not None and maximum < max(minimum, 1):
                raise ValueError(f"segment {index}: the maximum {maximum} is below the minimum")
            if "[" in separator or "]" in separator or re.search(f"[{char_class}]", "[]"):
                raise ValueError(f"segment {index}: a separator or class takes a square bracket")
            if index:
                self._check_boundary(index, separator, char_class)
        if next(self.matches(REDACTED, RunCursor), None) is not None:
            raise ValueError(f"the shape {self.prefix!r} matches inside the marker {REDACTED}")

    def _check_prefix(self) -> None:
        if not re.fullmatch(f"(?:{_PREFIX_ATOM})+", self.prefix):
            raise ValueError(
                f"the prefix {self.prefix!r} must match a bounded amount of text: plain or "
                "escaped characters and character classes, no quantifier, group or alternation"
            )
        for atom in re.findall(_PREFIX_ATOM, self.prefix):
            if re.fullmatch(atom, "[") or re.fullmatch(atom, "]"):
                raise ValueError(f"the prefix {self.prefix!r} can match a square bracket")

    def _check_boundary(self, index: int, separator: str, char_class: str) -> None:
        before = self.segments[index - 1][1]
        if separator:
            if re.fullmatch(f"[{before}]", separator[0]):
                raise ValueError(f"segment {index}: the separator is inside the run before it")
            return
        probe = _characters_either_class_can_match(before, char_class)
        if re.search(f"(?=[{before}])[{char_class}]", probe):
            raise ValueError(f"segments {index - 1} and {index} share a character")

    @cached_property
    def _start(self) -> re.Pattern[str]:
        return re.compile(self.prefix)

    @cached_property
    def _runs(self) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(f"[{char_class}]*") for _, char_class, _, _ in self.segments)

    def matches(self, text: str, cursor_factory: RunCursorFactory) -> Iterator[tuple[int, int]]:
        cursors = [cursor_factory(text, run) for run in self._runs]
        # Restarting one character on finds a start inside another prefix too, and a
        # literal-led pattern keeps the regex engine's fast literal search.
        candidate = self._start.search(text)
        while candidate is not None:
            stop = self._extent(text, candidate.end(), cursors)
            if stop is not None:
                yield candidate.start(), stop
            candidate = self._start.search(text, candidate.start() + 1)

    def _extent(self, text: str, position: int, cursors: list[RunCursorInterface]) -> int | None:
        for (separator, _, minimum, maximum), cursor in zip(self.segments, cursors, strict=True):
            if not text.startswith(separator, position):
                return None
            position += len(separator)
            available = cursor.end(position) - position
            if available < minimum:
                return None
            position += available if maximum is None else min(available, maximum)
        return position


_ASCII = "".join(map(chr, range(128)))


def _characters_either_class_can_match(first: str, second: str) -> str:
    """Every character two classes could share, to search for one they both match.

    A class body that is ASCII, has no escape and is not negated can only match ASCII, so
    when either class is one of those, the 128 ASCII characters are enough; otherwise every
    code point is (1.1 million, about 20 ms to build, so only for an unusual shape). A
    module function, beside `_every_character`, because the frozen `CredentialShape`
    checks itself while it is being made and must not carry the large string."""
    for body in (first, second):
        if body.isascii() and "\\" not in body and not body.startswith("^"):
            return _ASCII
    return _every_character()


@cache
def _every_character() -> str:
    """Every code point once, built at the first check that needs it."""
    return "".join(map(chr, range(sys.maxunicode + 1)))


_ALNUM = "A-Za-z0-9"
_BASE64URL = "A-Za-z0-9_-"


class SecretTextRedactor:
    """Replaces every vendor-shaped credential in free text with one `REDACTED` marker.

    A byte is replaced when any shape, matched at any start in the ORIGINAL text, covers
    it; overlapping matches are merged into one span as they stream out, in start order.

    Substituting one regex after another instead let a shorter shape inside a longer
    credential win: in `Bearer sk-AAAAAAAAAAAAAAAA.rest` the `sk-` key was replaced first,
    the Bearer pattern could no longer match across the marker, and "Bearer" and ".rest"
    -- bytes of the token -- survived. Resuming each regex where its last match ended
    missed a credential glued to the one before it (`sk-…sk-…`); restarting it at every
    start was quadratic (31 seconds on `"xoxb-" * 100000`); and indexing every run of a
    class in the text held up to 70 times the text in memory. Now each candidate start
    costs one cursor lookup per segment, each cursor reads each character at most once,
    and the matches are merged without being collected: time is linear in the text
    (each shape's prefix search, plus each segment's cursor) and memory is constant
    beyond the result.

    One search for any prefix at all comes first: most strings -- every log event, every
    streamed word -- hold none, and are returned as they are.

    Merged spans make the result independent of the order of the shapes, and idempotent:
    no shape can match a square bracket or inside the marker (`CredentialShape` checks
    it), so a second pass finds nothing the first did not. Spans that only touch stay
    separate, one marker each.
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
        cursor_factory: RunCursorFactory = RunCursor,
    ) -> None:
        self._shapes = tuple(shapes)
        self._cursor_factory = cursor_factory
        self._any_prefix = re.compile("|".join(f"(?:{shape.prefix})" for shape in self._shapes))

    def redact(self, text: str) -> str:
        if self._any_prefix.search(text) is None:
            return text
        pieces: list[str] = []
        cursor = 0
        for start, stop in self._merged(text):
            pieces += [text[cursor:start], REDACTED]
            cursor = stop
        pieces.append(text[cursor:])
        return "".join(pieces)

    def spans(self, text: str) -> list[tuple[int, int]]:
        if self._any_prefix.search(text) is None:
            return []
        return list(self._merged(text))

    def _merged(self, text: str) -> Iterator[tuple[int, int]]:
        streams = [shape.matches(text, self._cursor_factory) for shape in self._shapes]
        current: tuple[int, int] | None = None
        for start, stop in heapq.merge(*streams):
            if current is not None and start < current[1]:
                current = (current[0], max(current[1], stop))
                continue
            if current is not None:
                yield current
            current = (start, stop)
        if current is not None:
            yield current


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
    "RunCursor",
    "CredentialRedactor",
    "CredentialShape",
    "SecretTextRedactor",
    "contains_secret",
    "redact_payload",
]
