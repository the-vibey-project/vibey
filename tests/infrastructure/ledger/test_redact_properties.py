# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction is idempotent, total and exact, as properties.

Idempotent: redacting what was redacted changes nothing, so a payload redacted on write
and again on export is the same payload. Total: a secret at any nesting is gone, whatever
the container it sits in. Exact: a payload that holds no secret comes back equal, so
redaction never alters text it had no business touching.

Only string VALUES are scanned for secret patterns; a secret in a dictionary KEY is not
redacted by redact_payload, and is out of scope here (keys are drawn from digits and spaces).
"""

from hypothesis import given
from hypothesis import strategies as st

from tests.ledger_strategies import (
    JSON_TEXT,
    PLAIN_KEYS,
    PLAIN_WORDS,
    json_payloads,
    plain_payloads,
)
from vibey.infrastructure.ledger.redact import REDACTED, contains_secret, redact_payload

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
