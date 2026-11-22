# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction on write, ported in spirit from the *loop family: secrets must
never reach the ledger column, because the ledger is replicated into every
receiving worktree's .vibey/handoff/ledger.jsonl and read by whichever
engine is rotated in next. Pure text transform -- no I/O, safe to unit test
without a database, and applied by the ledger repository immediately
before a payload is persisted."""

import re
from collections.abc import Iterator, Mapping, Sequence
from typing import Final

from vibey.domain.interfaces.publication_policy_interface import CredentialRedactorInterface
from vibey.infrastructure.ledger.interfaces.redact_interface import SecretTextRedactorInterface

REDACTED = "[REDACTED]"

_SENSITIVE_KEY_NAMES = re.compile(
    r"(api[_-]?key|secret|password|passwd|token|auth[_-]?header|private[_-]?key|access[_-]?key)",
    re.IGNORECASE,
)


class SecretTextRedactor:
    """Replaces every vendor-shaped credential in free text with one `REDACTED` marker.

    A byte is replaced when any pattern, matched at any start in the ORIGINAL text,
    covers it; overlapping matches are merged into one span before anything is
    replaced. Substituting one pattern after another instead let a shorter shape
    inside a longer credential win: in `Bearer sk-AAAAAAAAAAAAAAAA.rest` the `sk-` key
    was replaced first, the Bearer pattern could no longer match across the marker,
    and "Bearer" and ".rest" -- bytes of the token -- survived. Merged spans make the
    result independent of the order the patterns are listed in, and idempotent: no
    pattern matches across a marker, so a second pass finds nothing the first did not.
    Spans that only touch stay separate, one marker each, as they always were.
    """

    DEFAULT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
        re.compile(r"sk-[A-Za-z0-9]{16,}"),  # OpenAI / Anthropic-style secret keys
        re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
        re.compile(r"ghp_[A-Za-z0-9]{36,}"),  # GitHub personal access token
        re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack tokens
        re.compile(r"AIza[0-9A-Za-z_-]{35}"),  # Google API key
        re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
        re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"),
    )
    """Vendor-shaped credential patterns, independent of the field name they appear
    under (a secret pasted into free text is still a secret). Redaction is idempotent
    for any patterns that, like these, have no anchors or lookarounds and cannot match
    a square bracket, so none can match across or inside a marker."""

    def __init__(self, patterns: Sequence[re.Pattern[str]] = DEFAULT_PATTERNS) -> None:
        self._patterns = tuple(patterns)

    def redact(self, text: str) -> str:
        pieces: list[str] = []
        cursor = 0
        for start, stop in self.spans(text):
            pieces += [text[cursor:start], REDACTED]
            cursor = stop
        pieces.append(text[cursor:])
        return "".join(pieces)

    def spans(self, text: str) -> list[tuple[int, int]]:
        found = sorted(
            span
            for pattern in self._patterns
            for span in self._matches_at_every_start(pattern, text)
        )
        merged: list[tuple[int, int]] = []
        for start, stop in found:
            if merged and start < merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
            else:
                merged.append((start, stop))
        return merged

    @staticmethod
    def _matches_at_every_start(pattern: re.Pattern[str], text: str) -> Iterator[tuple[int, int]]:
        """Every match, including one that starts inside the match before it.

        `finditer` resumes where the last match ended, so a credential glued to the one
        before it -- `sk-AAAAAAAAAAAAAAAAsk-BBBBBBBBBBBBBBBB`, where the first greedy match
        takes the second key's `sk` -- was never matched, and its body survived."""
        match = pattern.search(text)
        while match is not None:
            yield match.span()
            match = pattern.search(text, match.start() + 1)


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
    "SecretTextRedactor",
    "contains_secret",
    "redact_payload",
]
