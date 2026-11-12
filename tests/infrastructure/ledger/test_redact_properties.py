# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Redaction is idempotent, total and exact, as properties.

Idempotent: redacting what was redacted changes nothing, so a payload redacted on write
and again on export is the same payload. Total: a secret at any nesting is gone, whatever
the container it sits in. Exact: a payload that holds no secret comes back equal, so
redaction never alters text it had no business touching.
"""

from hypothesis import given
from hypothesis import strategies as st

from tests.ledger_strategies import JSON_TEXT, PLAIN_WORDS, json_payloads, plain_payloads
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
)
"""One secret in each of the shapes redact.py recognises."""


@st.composite
def _planted(draw: st.DrawFn) -> tuple[dict[str, object], str]:
    """A secret-free payload with one secret buried inside it, in free text, under any mix
    of lists and objects, up to five levels down; and the secret, to look for afterwards."""
    secret = draw(_SECRETS)
    buried: object = draw(PLAIN_WORDS) + secret + draw(PLAIN_WORDS)
    for _ in range(draw(st.integers(0, 5))):
        siblings = draw(st.lists(PLAIN_WORDS, max_size=2))
        if draw(st.booleans()):
            buried = [*siblings, buried]
        else:
            buried = {**dict.fromkeys(siblings, "kept"), "inner": buried}
    payload = draw(plain_payloads())
    payload["planted"] = buried
    return payload, secret


@given(payload=json_payloads())
def test_redacting_twice_is_redacting_once(payload: dict[str, object]) -> None:
    once = redact_payload(payload)
    assert redact_payload(once) == once


@given(planted=_planted())
def test_a_planted_secret_is_gone_and_the_payload_is_reported_as_holding_one(
    planted: tuple[dict[str, object], str],
) -> None:
    payload, secret = planted
    assert contains_secret(payload)
    assert secret in repr(payload)
    redacted = redact_payload(payload)
    assert not contains_secret(redacted)
    assert secret not in repr(redacted)
    assert REDACTED in repr(redacted)


@given(payload=plain_payloads())
def test_a_payload_with_no_secret_comes_back_unchanged(payload: dict[str, object]) -> None:
    assert redact_payload(payload) == payload
    assert not contains_secret(payload)


@given(
    key=st.sampled_from(["api_key", "API-KEY", "Secret", "db_password", "auth_token"]),
    value=JSON_TEXT | st.integers() | st.lists(JSON_TEXT, max_size=3),
)
def test_a_value_under_a_sensitive_key_is_redacted_whatever_it_is(key: str, value: object) -> None:
    assert redact_payload({key: value}) == {key: REDACTED}
    assert redact_payload({"outer": {key: value}}) == {"outer": {key: REDACTED}}
