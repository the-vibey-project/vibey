# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import re

import pytest

from vibey.domain.interfaces import CredentialRedactorInterface
from vibey.infrastructure.ledger.interfaces import SecretTextRedactorInterface
from vibey.infrastructure.ledger.redact import (
    CREDENTIAL_REDACTOR,
    REDACTED,
    CredentialRedactor,
    SecretTextRedactor,
    contains_secret,
    redact_payload,
)


def test_sensitive_key_name_is_redacted_regardless_of_value() -> None:
    payload = {"api_key": "anything", "note": "fine"}
    result = redact_payload(payload)
    assert result["api_key"] == REDACTED
    assert result["note"] == "fine"


def test_openai_style_secret_key_is_redacted_in_free_text() -> None:
    payload = {"text": "use sk-abcdefghijklmnopqrstuvwx to authenticate"}
    result = redact_payload(payload)
    assert "sk-abcdefghijklmnopqrstuvwx" not in result["text"]
    assert REDACTED in result["text"]


def test_aws_access_key_id_is_redacted() -> None:
    payload = {"text": "key is AKIAABCDEFGHIJKLMNOP"}
    result = redact_payload(payload)
    assert "AKIAABCDEFGHIJKLMNOP" not in result["text"]


def test_github_token_is_redacted() -> None:
    payload = {"text": "ghp_" + "a" * 40}
    result = redact_payload(payload)
    assert "ghp_" + "a" * 40 not in result["text"]


def test_slack_token_is_redacted() -> None:
    payload = {"text": "xoxb-1234567890-abcdefghij"}
    result = redact_payload(payload)
    assert "xoxb-1234567890-abcdefghij" not in result["text"]


def test_bearer_token_is_redacted() -> None:
    payload = {"header": "Authorization: Bearer abcdefghij1234567890"}
    result = redact_payload(payload)
    assert "abcdefghij1234567890" not in result["header"]


def test_a_bearer_token_that_opens_like_an_openai_key_is_replaced_whole() -> None:
    # The Hypothesis counterexample to the planted-secret property (#1886): the `sk-` pattern
    # used to run first and leave "Bearer [REDACTED]", after which the Bearer pattern could
    # no longer match, so the scheme word and anything past the `sk-` run stayed behind.
    text = "Bearer sk-" + "0" * 37 + " "
    assert redact_payload({"t": text}) == {"t": f"{REDACTED} "}


@pytest.mark.parametrize(
    "secret",
    [
        "Bearer sk-AAAAAAAAAAAAAAAA.tokenpart2",
        "Bearer AKIA0000000000000000moresecret",
        "Bearer eyJaaaaaaaaaa.bbbbbbbbbb.cccccccccc.dddd",
        "xoxb-abc-sk-AAAAAAAAAAAAAAAA-tail",
        "eyJaaaaaaaaaa.sk-AAAAAAAAAAAAAAAA.cccccccccc",
        "AIza" + "a" * 8 + "sk-" + "B" * 16 + "c" * 8,
    ],
)
def test_no_byte_of_a_secret_survives_a_shorter_pattern_matching_inside_it(secret: str) -> None:
    # Each credential holds a shorter vendor shape inside it. Replacing the shorter match
    # first used to break the longer pattern's match, so the bytes past it survived.
    assert redact_payload({"t": f"x {secret} y"}) == {"t": f"x {REDACTED} y"}


@pytest.mark.parametrize(
    "glued",
    [
        "sk-" + "A" * 16 + "sk-" + "B" * 16,
        "ghp_" + "a" * 36 + "ghp_" + "b" * 36,
        "AIza" + "x" * 31 + "AKIA" + "AKIA" + "C" * 16,
        "Bearer abcdefghijBearer klmnopqrstuv",
    ],
)
def test_a_secret_glued_to_the_one_before_it_is_redacted_to_its_last_byte(glued: str) -> None:
    # The second credential's prefix starts inside the first one's match, so scanning on
    # from where that match ended skipped it, and its body survived whole.
    assert redact_payload({"t": f"x {glued} y"}) == {"t": f"x {REDACTED} y"}


def test_secrets_that_only_touch_are_still_replaced_one_by_one() -> None:
    text = "AKIA" + "A" * 16 + "AKIA" + "B" * 16
    assert redact_payload({"t": text}) == {"t": REDACTED + REDACTED}


def test_the_secret_text_redactor_takes_its_patterns_as_configuration() -> None:
    redactor = SecretTextRedactor((re.compile(r"needle"),))
    assert isinstance(redactor, SecretTextRedactorInterface)
    key = "sk-" + "A" * 16
    assert redactor.redact(f"a needle, {key}") == f"a {REDACTED}, {key}"
    assert SecretTextRedactor(()).redact("Bearer abcdefghijkl") == "Bearer abcdefghijkl"
    assert SecretTextRedactor().redact(f"a needle, {key}") == f"a needle, {REDACTED}"
    assert SecretTextRedactor().spans(f"{key} and {key}{key}") == [(0, 19), (24, 62)]


def test_nested_mapping_is_redacted() -> None:
    payload = {"outer": {"password": "hunter2", "safe": "ok"}}
    result = redact_payload(payload)
    assert result["outer"]["password"] == REDACTED
    assert result["outer"]["safe"] == "ok"


def test_list_of_strings_is_redacted() -> None:
    payload = {"lines": ["clean line", "token is sk-" + "x" * 20]}
    result = redact_payload(payload)
    assert result["lines"][0] == "clean line"
    assert "sk-" + "x" * 20 not in result["lines"][1]


def test_non_string_values_pass_through_unchanged() -> None:
    payload = {"count": 5, "ok": True, "ratio": 1.5, "nothing": None}
    result = redact_payload(payload)
    assert result == payload


def test_clean_payload_is_unchanged() -> None:
    payload = {"summary": "added the outbox table", "cost_usd": 0.01}
    assert redact_payload(payload) == payload
    assert contains_secret(payload) is False


def test_contains_secret_detects_a_planted_secret() -> None:
    payload = {"detail": "sk-" + "y" * 20}
    assert contains_secret(payload) is True


def test_the_credential_redactor_is_redact_payload_behind_the_policys_seam() -> None:
    payload = {"note": "use sk-abcdefghijklmnopqrstuvwx", "token": "t"}
    assert isinstance(CREDENTIAL_REDACTOR, CredentialRedactorInterface)
    assert CredentialRedactor().redact(payload) == redact_payload(payload)
    assert CREDENTIAL_REDACTOR.redact(payload) == {"note": f"use {REDACTED}", "token": REDACTED}
