# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction costs time and memory linear in the text, whatever an engine writes.

Every ledger append redacts every string in its payload, logging redacts every event and the
wire log every streamed word, and engine output is untrusted. Two earlier versions of this
fix were each a denial of service: searching again from every match's start + 1 took 31
seconds on `"xoxb-" * 100000`, and indexing every run of a character class across the whole
text took 734 MB to redact 10 MB of prose that held each credential prefix once. These are
the worst cases for each shape. Time bounds are generous on purpose (a loaded machine is not
a failure); the counted tests pin the work exactly.
"""

import re
import time
import tracemalloc
from collections.abc import Callable

import pytest

from vibey.infrastructure.ledger.interfaces import RunCursorInterface
from vibey.infrastructure.ledger.redact import REDACTED, RunCursor, SecretTextRedactor

_N = 400_000
_ADVERSARIAL = {
    "slack prefixes": "xoxb-" * _N,
    "openai near-miss prefixes": "sk-" * _N,
    "bearer words": "Bearer " * _N,
    "aws prefixes": "AKIA" * _N,
    "github prefixes": "ghp_" * _N,
    "jwt prefixes with no dot": "eyJ" * _N,
    "jwt prefixes then dots": "eyJ" * _N + ".aaaaaaaaaaaa.bbbbbbbbbbbb",
    "short jwt segments": ("eyJ" + "a" * 10 + ".") * _N,
    "one long token": "sk-" + "A" * 500_000,
    "one long bearer token": "Bearer " + "a" * 500_000,
}

_PROSE = "the quick brown fox jumps over the lazy dog, " * 230_000  # about 10 MB
_PROSE_WITH_PREFIXES = {
    "each prefix once": _PROSE + " sk- AKIA ghp_ xoxb- AIza eyJ Bearer",
    "one bearer token": _PROSE + " Bearer abcdefghijkl",
}


@pytest.mark.parametrize("text", _ADVERSARIAL.values(), ids=_ADVERSARIAL.keys())
def test_redacting_an_adversarial_string_takes_linear_time(text: str) -> None:
    began = time.perf_counter()
    redacted = SecretTextRedactor().redact(text)
    assert time.perf_counter() - began < 20.0  # quadratic would take minutes
    assert SecretTextRedactor().redact(redacted) == redacted


def _peak_bytes(work: Callable[[], object]) -> int:
    tracemalloc.start()
    try:
        work()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


@pytest.mark.parametrize(
    "text",
    [*_PROSE_WITH_PREFIXES.values(), *_ADVERSARIAL.values()],
    ids=[*_PROSE_WITH_PREFIXES, *_ADVERSARIAL],
)
def test_redaction_never_holds_more_than_a_small_multiple_of_the_text(text: str) -> None:
    redactor = SecretTextRedactor()
    assert _peak_bytes(lambda: redactor.redact(text)) < 3 * len(text)
    assert _peak_bytes(lambda: redactor.spans(text)) < 3 * len(text)


class _CountingCursor:
    """The real cursor, counting every lookup."""

    def __init__(self, text: str, run: re.Pattern[str]) -> None:
        self.inner = RunCursor(text, run)
        self.lookups = 0

    @property
    def scanned(self) -> int:
        return self.inner.scanned

    def end(self, index: int) -> int:
        self.lookups += 1
        return self.inner.end(index)


def _counting() -> tuple[list[_CountingCursor], Callable[[str, re.Pattern[str]], _CountingCursor]]:
    made: list[_CountingCursor] = []

    def factory(text: str, run: re.Pattern[str]) -> _CountingCursor:
        made.append(_CountingCursor(text, run))
        return made[-1]

    return made, factory


def test_each_candidate_start_is_looked_at_once_per_segment() -> None:
    made, factory = _counting()
    assert SecretTextRedactor(cursor_factory=factory).redact("xoxb-" * 100_000) == REDACTED
    assert all(isinstance(cursor, RunCursorInterface) for cursor in made)
    # One Slack candidate per "xoxb-", one segment each; no other shape has a candidate.
    assert sum(cursor.lookups for cursor in made) == 100_000


@pytest.mark.parametrize(
    "text",
    ["eyJ" * 100_000 + ".aaaaaaaaaaaa.bbbbbbbbbbbb", "xoxb-" * 100_000, "AKIA" * 100_000],
)
def test_no_cursor_reads_a_character_of_the_text_twice(text: str) -> None:
    # A JWT candidate's later segments move past its first; a cache shared between them
    # would forget the long first run and rescan it for every one of the 100,000 starts.
    made, factory = _counting()
    SecretTextRedactor(cursor_factory=factory).redact(text)
    assert made
    assert all(cursor.scanned <= len(text) for cursor in made)


def test_a_string_with_no_candidate_prefix_is_returned_as_it_is() -> None:
    made, factory = _counting()
    redactor = SecretTextRedactor(cursor_factory=factory)
    strings = [f"step {index}: wrote the outbox table, cost 0.01" for index in range(1_000_000)]
    assert all(redactor.redact(text) is text for text in strings)
    assert all(redactor.spans(text) == [] for text in strings[:1000])
    assert made == []


def test_redacting_a_small_clean_string_costs_little_more_than_one_regex_search() -> None:
    # Logging redacts every event and the wire log every streamed word: a million small
    # strings. Best of three, against one search per string, so load slows both alike.
    strings = [f"step {index}: wrote the outbox table, cost 0.01" for index in range(200_000)]
    one_search = re.compile("sk-|AKIA|ghp_|xox[baprs]-|AIza|eyJ|Bearer").search
    redact = SecretTextRedactor().redact

    def best(work: Callable[[str], object]) -> float:
        times = []
        for _ in range(3):
            began = time.perf_counter()
            for text in strings:
                work(text)
            times.append(time.perf_counter() - began)
        return min(times)

    assert best(redact) < 8 * best(one_search)
