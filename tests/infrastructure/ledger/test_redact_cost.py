# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction costs time linear in the text, whatever an engine writes into a payload.

Every ledger append redacts every string in its payload, and engine output is untrusted, so
a redactor that rescans a run once per candidate start is a denial of service: an earlier
fix that searched again from every match's start + 1 took about 25 seconds on
`"xoxb-" * 100000`. These inputs are the worst cases for each shape -- long runs of one
prefix, runs of near-miss prefixes, one very long token. The bound is generous on purpose
(a loaded machine is not a failure); the counted test pins the work exactly.
"""

import time

import pytest

from vibey.infrastructure.ledger.interfaces import TextRunIndexInterface
from vibey.infrastructure.ledger.redact import REDACTED, SecretTextRedactor, TextRunIndex

_ADVERSARIAL = {
    "slack prefixes": "xoxb-" * 100_000,
    "openai near-miss prefixes": "sk-" * 100_000,
    "bearer words": "Bearer " * 100_000,
    "aws prefixes": "AKIA" * 50_000,
    "jwt prefixes with no dot": "eyJ" * 100_000,
    "jwt prefixes then dots": "eyJ" * 100_000 + ".aaaaaaaaaaaa.bbbbbbbbbbbb",
    "one long token": "sk-" + "A" * 500_000,
    "one long bearer token": "Bearer " + "a" * 500_000,
}


@pytest.mark.parametrize("text", _ADVERSARIAL.values(), ids=_ADVERSARIAL.keys())
def test_redacting_an_adversarial_string_takes_linear_time(text: str) -> None:
    began = time.perf_counter()
    redacted = SecretTextRedactor().redact(text)
    assert time.perf_counter() - began < 5.0
    assert SecretTextRedactor().redact(redacted) == redacted


class _CountingRunIndex:
    """The real index, counting every run lookup and every class it indexes."""

    def __init__(self, text: str) -> None:
        self._inner = TextRunIndex(text)
        self.lookups = 0
        self.classes: set[str] = set()
        _CountingRunIndex.last = self

    last: "_CountingRunIndex | None" = None

    def end(self, char_class: str, index: int) -> int:
        self.lookups += 1
        self.classes.add(char_class)
        return self._inner.end(char_class, index)


def test_each_candidate_start_is_looked_at_once_per_segment_never_rescanned() -> None:
    text = "xoxb-" * 100_000
    redactor = SecretTextRedactor(index_factory=_CountingRunIndex)
    assert redactor.redact(text) == REDACTED
    counted = _CountingRunIndex.last
    assert counted is not None
    assert isinstance(counted, TextRunIndexInterface)
    # One Slack candidate per "xoxb-", one segment each; no other shape has a candidate.
    assert counted.lookups == 100_000
    assert counted.classes == {"A-Za-z0-9-"}


def test_a_string_with_no_candidate_prefix_indexes_nothing() -> None:
    redactor = SecretTextRedactor(index_factory=_CountingRunIndex)
    _CountingRunIndex.last = None
    assert redactor.redact("plain words " * 10_000) == "plain words " * 10_000
    counted = _CountingRunIndex.last
    assert counted is not None
    assert counted.lookups == 0
