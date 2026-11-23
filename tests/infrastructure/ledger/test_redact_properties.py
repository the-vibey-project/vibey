# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction is idempotent, total and exact, as properties.

Idempotent: redacting what was redacted changes nothing, so a payload redacted on write
and again on export is the same payload. Total: a secret at any nesting is gone, whatever
the container it sits in, and every byte of it is gone, even where credential shapes
overlap or one credential is glued to the next. Order-free: the order the patterns are
tried in never changes the result. Exact: a payload that holds no secret comes back equal,
so redaction never alters text it had no business touching.

Only string VALUES are scanned for secret patterns; a secret in a dictionary KEY is not
redacted by redact_payload, and is out of scope here (keys are drawn from digits and spaces).
"""

import re

from hypothesis import example, given
from hypothesis import strategies as st

from tests.ledger_strategies import (
    JSON_TEXT,
    PLAIN_KEYS,
    PLAIN_WORDS,
    json_payloads,
    plain_payloads,
)
from vibey.infrastructure.ledger.redact import (
    REDACTED,
    SecretTextRedactor,
    contains_secret,
    redact_payload,
)

_ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_B64URL = _ALNUM + "_-"


def _run(alphabet: str, low: int, high: int) -> st.SearchStrategy[str]:
    return st.text(alphabet=alphabet, min_size=low, max_size=high)


_SECRETS = st.one_of(
    _run(_ALNUM, 16, 40).map(lambda tail: "sk-" + tail),
    _run("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", 16, 16).map(lambda tail: "AKIA" + tail),
    _run(_ALNUM, 36, 50).map(lambda tail: "ghp_" + tail),
    st.tuples(st.sampled_from("baprs"), _run(_ALNUM + "-", 10, 30)).map(
        lambda parts: f"xox{parts[0]}-{parts[1]}"
    ),
    _run(_B64URL, 35, 35).map(lambda tail: "AIza" + tail),
    st.tuples(_run(_B64URL, 10, 20), _run(_B64URL, 10, 20), _run(_B64URL, 10, 20)).map(
        lambda parts: "eyJ{}.{}.{}".format(*parts)
    ),
    _run(_ALNUM + "._-", 10, 30).map(lambda tail: "Bearer " + tail),
    _run(_ALNUM + "._-", 40, 80).map(lambda tail: "Bearer " + tail),  # a tail a cap would cut
)
"""One secret in each of the shapes redact.py recognises."""


@st.composite
def _planted(draw: st.DrawFn) -> tuple[dict[str, object], str, str, str]:
    """A secret-free payload with one secret buried inside a string, under any mix of lists
    and objects up to five levels down. Returns the payload, the text before the secret,
    the text after it (starting with a space, so it cannot extend the secret) and the
    secret, to look for afterwards."""
    secret = draw(_SECRETS)
    before = draw(PLAIN_WORDS)
    after = " " + draw(PLAIN_WORDS)
    buried: object = before + secret + after
    for _ in range(draw(st.integers(0, 5))):
        siblings = draw(st.lists(PLAIN_KEYS, max_size=2))
        if draw(st.booleans()):
            buried = [*siblings, buried]
        else:
            buried = {**dict.fromkeys(siblings, "kept"), "planted_inner": buried}
    payload = draw(plain_payloads())
    payload["planted"] = buried
    return payload, before, after, secret


def _leaves(value: object) -> list[str]:
    """Every string leaf of a JSON value."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [leaf for item in value.values() for leaf in _leaves(item)]
    if isinstance(value, list):
        return [leaf for item in value for leaf in _leaves(item)]
    return []


_SENSITIVE_KEYS = st.sampled_from(["api_key", "API-KEY", "Secret", "db_password", "auth_token"])


@st.composite
def _sensitive_payloads(draw: st.DrawFn) -> dict[str, object]:
    """A payload with a value under a sensitive key, nested in objects and lists."""
    buried: object = {draw(_SENSITIVE_KEYS): draw(JSON_TEXT | st.lists(JSON_TEXT, max_size=3))}
    for _ in range(draw(st.integers(0, 3))):
        buried = [buried] if draw(st.booleans()) else {"n": buried}
    return {**draw(json_payloads()), "outer": buried}


@given(
    payload=st.one_of(
        _planted().map(lambda planted: planted[0]),
        _sensitive_payloads(),
        json_payloads(),
    )
)
def test_redacting_twice_is_redacting_once(payload: dict[str, object]) -> None:
    once = redact_payload(payload)
    assert redact_payload(once) == once


@given(planted=_planted())
# The counterexample Hypothesis found (#1886 follow-up): a Bearer token whose tail opens like
# an `sk-` key. The `sk-` pattern ran first and left "Bearer [REDACTED]".
@example(planted=({"planted": "Bearer sk-" + "0" * 37 + " "}, "", " ", "Bearer sk-" + "0" * 37))
def test_a_planted_secret_is_replaced_whole_and_nothing_else_is_touched(
    planted: tuple[dict[str, object], str, str, str],
) -> None:
    payload, before, after, secret = planted
    assert contains_secret(payload)
    redacted = redact_payload(payload)
    # The whole secret is replaced, not a prefix of it: no fragment of the tail survives.
    assert before + REDACTED + after in _leaves(redacted)
    assert secret not in repr(redacted)
    assert not contains_secret(redacted)


@st.composite
def _secret_soup(draw: st.DrawFn) -> tuple[str, list[tuple[int, int]]]:
    """Secrets and plain words glued together with no separator, so one secret's text can
    run into the next and the shapes overlap. Returns the text and where each secret sits."""
    parts = draw(
        st.lists(
            st.one_of(
                _SECRETS.map(lambda secret: (secret, True)),
                PLAIN_WORDS.map(lambda word: (word, False)),
            ),
            max_size=4,
        )
    )
    text, where = "", []
    for part, is_secret in parts:
        if is_secret:
            where.append((len(text), len(text) + len(part)))
        text += part
    return text, where


def _glued(*parts: str) -> tuple[str, list[tuple[int, int]]]:
    starts = [sum(len(part) for part in parts[:index]) for index in range(len(parts))]
    return "".join(parts), [
        (start, start + len(part)) for start, part in zip(starts, parts, strict=True)
    ]


# The order of the shapes is not a parameter here: the redactor merges every shape's
# matches in start order, so order-independence holds by construction and a permutation
# check would prove nothing. What can go wrong is coverage, checked byte by byte.
@given(soup=_secret_soup())
@example(soup=_glued("Bearer sk-" + "0" * 37))
@example(soup=_glued("sk-" + "A" * 16, "sk-" + "B" * 16))
def test_every_byte_of_every_secret_is_replaced(
    soup: tuple[str, list[tuple[int, int]]],
) -> None:
    text, secrets = soup
    redactor = SecretTextRedactor()
    spans = redactor.spans(text)
    for start, stop in secrets:
        assert any(low <= start and stop <= high for low, high in spans), text[start:stop]
    redacted = redactor.redact(text)
    assert redactor.redact(redacted) == redacted


_ORACLE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{36,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{10,}"),
)
"""The credential regexes the shapes replaced, kept here as the specification."""


def _oracle_spans(text: str) -> list[tuple[int, int]]:
    """What the shapes must redact, by brute force: every regex tried at every start, the
    overlapping matches merged. Quadratic, so only fit for short test strings."""
    found = sorted(
        match.span()
        for pattern in _ORACLE_PATTERNS
        for start in range(len(text))
        if (match := pattern.match(text, start)) is not None
    )
    merged: list[tuple[int, int]] = []
    for start, stop in found:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged


_LOOK_ALIKES = [
    "\u00a0",  # no-break space: whitespace to `\s`
    "\u2028",  # line separator: whitespace to `\s`
    "\x85",  # next line: whitespace to `\s`
    "\x1c",  # file separator: whitespace to `\s`
    "\u3000",  # ideographic space: whitespace to `\s`
    "\u200b",  # zero-width space: NOT whitespace to `\s`
    "\uff11",  # fullwidth digit one: not in any ASCII class
    "\u0661",  # Arabic-Indic digit one: not in any ASCII class
    "\u212a",  # Kelvin sign, a K look-alike
]
"""Characters at the edges of the shapes' classes, so the `\\s` and ASCII-only boundaries
stay pinned to what the regexes did."""

_SHAPE_ALPHABET = st.sampled_from(
    ["sk-", "AKIA", "ghp_", "xoxb-", "xoxz-", "AIza", "eyJ", "Bearer", " ", "\t", ".", "-", "_"]
    + _LOOK_ALIKES
) | st.text(alphabet="aA0zZ9.-_ \t" + "".join(_LOOK_ALIKES), min_size=1, max_size=20)


@given(
    text=st.one_of(
        _secret_soup().map(lambda soup: soup[0]),
        st.lists(_SHAPE_ALPHABET | _SECRETS, max_size=8).map("".join),
    )
)
@example(
    text="eyJ"
    + "a" * 10
    + "."
    + "b" * 10
    + "."
    + "eyJ"
    + "c" * 10
    + "."
    + "d" * 10
    + "."
    + "e" * 10
)
@example(text="Bearer \t\n " + "a" * 12 + "Bearer " + "b" * 10)
def test_the_shapes_redact_exactly_what_the_credential_regexes_match_at_every_start(
    text: str,
) -> None:
    assert SecretTextRedactor().spans(text) == _oracle_spans(text)


_NEAR_MISSES = [
    "sk-" + "a1B2c3D4e5F6g7H",  # 15 characters
    "AKIA" + "ABCDEFGHIJKLMNO",  # 15 characters
    "ghp_" + "a" * 35,
    "Bearer abc",
    "xoxz-abcdefghijklmnop",
    "eyJ.a.b",
    "AIza" + "a" * 34,
]


@given(payload=plain_payloads(), near_miss=st.sampled_from(_NEAR_MISSES), pad=PLAIN_WORDS)
def test_a_payload_with_no_secret_comes_back_unchanged(
    payload: dict[str, object], near_miss: str, pad: str
) -> None:
    payload["near"] = [near_miss, pad + " " + near_miss]
    assert redact_payload(payload) == payload
    assert not contains_secret(payload)


def test_every_secret_in_one_string_is_replaced_and_whitespace_may_be_a_tab() -> None:
    text = "a sk-" + "A" * 16 + " b AKIA" + "B" * 16 + " c Bearer\t" + "c" * 12 + " d"
    assert redact_payload({"t": text}) == {"t": f"a {REDACTED} b {REDACTED} c {REDACTED} d"}


@given(
    key=_SENSITIVE_KEYS,
    value=JSON_TEXT | st.integers() | st.lists(JSON_TEXT, max_size=3),
)
def test_a_value_under_a_sensitive_key_is_redacted_whatever_it_is(key: str, value: object) -> None:
    assert redact_payload({key: value}) == {key: REDACTED}
    assert redact_payload({"outer": {key: value}}) == {"outer": {key: REDACTED}}
