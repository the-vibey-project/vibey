# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A transient forge failure is asked again; every other failure fails exactly as before.

The two failures that turned the delivery estimate's triage job red are reproduced verbatim
(trimmed of GitHub's HTML error page): run 36985000010's 504 on `gh issue edit 344`, and run
36939497192's GraphQL "Something went wrong" on issue 511.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from vibey_gh import cli, issue_triage
from vibey_gh.config import ForgeRetryConfig, load_config
from vibey_gh.gh_retry import GhRetry
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_retry_interface import GhRetryInterface

URL = "https://github.com/the-vibey-project/vibey/issues"
GATEWAY_TIMEOUT = (
    f"failed to update {URL}/344: non-200 OK status code: 504 Gateway Timeout body: "
    '"<!DOCTYPE html>\\r\\n<html>\\r\\n  <head>\\r\\n    <title>Unicorn! &middot; GitHub</title>"\n'
    "failed to update 1 issue\n"
)
GRAPHQL_WRONG = (
    f"failed to update {URL}/511: GraphQL: Something went wrong while executing your query on "
    "2026-10-01T23:15:45Z. Please include `8044:CE2CF:4B3018:539C7B:6ABEE99F` when reporting "
    "this issue.\nfailed to update 1 issue\n"
)
SECONDARY = "gh: You have exceeded a secondary rate limit. (HTTP 403)\n"
WITH_RETRY_AFTER = "HTTP/2.0 403 Forbidden\nRetry-After: 42\nContent-Type: application/json\n"


def answer(code: int = 0, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["gh"], code, out, err)


class Script:
    """A `call` that hands back each scripted answer in turn and counts the attempts."""

    def __init__(self, *answers: subprocess.CompletedProcess[str]) -> None:
        self.answers = list(answers)
        self.calls = 0

    def __call__(self) -> subprocess.CompletedProcess[str]:
        self.calls += 1
        return self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]


def retry(**policy) -> tuple[GhRetry, list[float], list[str]]:
    slept: list[float] = []
    said: list[str] = []
    return GhRetry(ForgeRetryConfig(**policy), sleep=slept.append, report=said.append), slept, said


def test_it_implements_its_interface():
    assert isinstance(GhRetry(), GhRetryInterface)


@pytest.mark.parametrize(
    ("failure", "reason"),
    [
        (answer(1, err=GATEWAY_TIMEOUT), "HTTP 504"),
        (answer(1, err=GRAPHQL_WRONG), "Something went wrong while executing your query"),
        (answer(1, err="gh: Bad Gateway (HTTP 502)\n"), "HTTP 502"),
        (answer(1, out="HTTP/2.0 503 Service Unavailable\n", err="gh: (HTTP 503)\n"), "HTTP 503"),
    ],
)
def test_a_transient_failure_is_asked_again_and_the_success_is_what_comes_back(failure, reason):
    done = answer(0, out='{"ok": true}')
    call = Script(failure, done)
    retrying, slept, said = retry()
    assert retrying.run(call, "gh issue edit") is done
    assert call.calls == 2
    assert slept == [5]
    assert said == [
        f"vibey-gh: `gh issue edit` failed transiently ({reason}); retrying in 5s (attempt 2 of 4)"
    ]


def test_a_secondary_rate_limit_waits_exactly_as_long_as_retry_after_says():
    call = Script(answer(1, out=WITH_RETRY_AFTER, err=SECONDARY), answer(0))
    retrying, slept, said = retry()
    assert retrying.run(call, "gh api").returncode == 0
    assert slept == [42]
    assert "secondary rate limit, Retry-After 42s" in said[0]


@pytest.mark.parametrize(
    "failure",
    [
        answer(1, err=SECONDARY),  # a rate limit that does not say when is not waited out
        answer(1, out="Retry-After: 900\n", err=SECONDARY),  # nor one that asks too long
        answer(1, out="Retry-After: 900\n", err="gh: (HTTP 503)\n"),
        answer(1, err=f"failed to update {URL}/7: GraphQL: Could not resolve to an Issue\n"),
        answer(1, err="gh: Not Found (HTTP 404)\n"),
        answer(1, err="HTTP 403: Resource not accessible by integration\n"),
        answer(1, err="non-200 OK status code: 500 Internal Server Error\n"),  # not listed
        answer(4, err="To get started with GitHub CLI, please run:  gh auth login\n"),
    ],
)
def test_any_other_failure_comes_back_untouched_after_one_attempt(failure):
    call = Script(failure)
    retrying, slept, said = retry()
    assert retrying.run(call, "gh issue edit") is failure
    assert (call.calls, slept, said) == (1, [], [])


def test_attempts_are_bounded_backed_off_capped_and_the_last_failure_says_so():
    failure = answer(1, err=GATEWAY_TIMEOUT)
    call = Script(failure)
    retrying, slept, said = retry(retries=4, backoff_seconds=10, max_backoff_seconds=30)
    final = retrying.run(call, "gh issue edit")
    assert call.calls == 5
    assert slept == [10, 20, 30, 30]
    assert len(said) == 4 and said[-1].endswith("(attempt 5 of 5)")
    assert final.returncode == 1 and final.stdout == failure.stdout
    assert final.stderr.startswith(GATEWAY_TIMEOUT.rstrip())
    assert final.stderr.endswith("(gave up after 5 attempts; each failed transiently: HTTP 504)")


def test_with_no_retries_a_transient_failure_is_the_answer_it_always_was():
    failure = answer(1, err=GRAPHQL_WRONG)
    retrying, slept, said = retry(retries=0)
    assert retrying.run(Script(failure), "gh issue edit") is failure
    assert (slept, said) == ([], [])


def test_success_is_never_retried():
    retrying, _, _ = retry()
    assert retrying.wait(answer(0, err=GATEWAY_TIMEOUT), 1) is None


def test_the_default_seams_sleep_for_real_and_announce_on_stderr(capsys):
    call = Script(answer(1, err=GATEWAY_TIMEOUT), answer(0))
    with patch("vibey_gh.gh_retry.time.sleep") as sleep:
        GhRetry(ForgeRetryConfig(backoff_seconds=0.5)).run(call, "gh issue edit")
    sleep.assert_called_once_with(0.5)
    assert "`gh issue edit` failed transiently (HTTP 504)" in capsys.readouterr().err


def test_the_transport_retries_a_real_gh_and_its_caller_sees_the_success(fake_gh):
    key = "issue edit 344 --add-label vibey-gh:triaged"
    fake_gh.script({key: {"code": 1, "err": GATEWAY_TIMEOUT}})

    def recover(_seconds: float) -> None:
        # Between attempts GitHub recovers: the second `gh` answers.
        fake_gh.script({key: {"out": f"{URL}/344\n"}})

    transport = GhTransport(retry=GhRetry(sleep=recover, report=lambda _line: None))
    issue_triage._run(*key.split(), transport=transport)
    assert fake_gh.calls() == [key, key]


def test_through_the_transport_a_permanent_failure_raises_exactly_as_before(fake_gh):
    key = "issue edit 7 --add-label vibey-gh:triaged"
    fake_gh.script({key: {"code": 1, "err": "GraphQL: Could not resolve to an Issue\n"}})
    transport = GhTransport(retry=GhRetry(sleep=lambda _s: None))
    with pytest.raises(RuntimeError) as raised:
        issue_triage._run(*key.split(), transport=transport)
    assert str(raised.value) == "GraphQL: Could not resolve to an Issue"
    assert fake_gh.calls() == [key]


def test_through_the_transport_a_failure_that_stays_transient_still_fails(fake_gh):
    key = "issue edit 511 --add-label vibey-gh:triaged"
    fake_gh.script({key: {"code": 1, "err": GRAPHQL_WRONG}})
    transport = GhTransport(retry=GhRetry(sleep=lambda _s: None, report=lambda _line: None))
    with pytest.raises(RuntimeError, match="gave up after 4 attempts") as raised:
        issue_triage._run(*key.split(), transport=transport)
    assert str(raised.value).startswith(GRAPHQL_WRONG.strip())
    assert fake_gh.calls() == [key] * 4


def test_without_a_retry_the_transport_runs_each_call_once(fake_gh):
    fake_gh.script({"issue list": {"code": 1, "err": GATEWAY_TIMEOUT}})
    assert GhTransport().run(["issue", "list"]).returncode == 1
    assert fake_gh.calls() == ["issue list"]


def test_the_triage_command_retries_with_the_repository_policy():
    with patch.object(issue_triage, "ensure_labels") as ensure_labels:
        assert cli._issue_triage(Namespace(action="ensure-labels", issue=None)) == 0
    transport = ensure_labels.call_args.args[0]
    assert isinstance(transport, GhTransport) and isinstance(transport.retry, GhRetry)
    assert transport.retry.policy == load_config().forge_retry


# --- `[forge_retry]` -------------------------------------------------------------------


def test_forge_retry_defaults_name_the_failures_seen_in_ci():
    policy = ForgeRetryConfig()
    assert policy.transient_statuses == (502, 503, 504)
    assert "Something went wrong while executing your query" in policy.transient_messages
    assert ForgeRetryConfig.from_table({}) == policy


def test_forge_retry_is_read_from_the_repository_configuration(tmp_path: Path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[forge_retry]\nretries = 1\nbackoff_seconds = 2.5\ntransient_statuses = [503]\n"
        'transient_messages = ["try again"]\nrate_limit_messages = ["abuse detection"]\n'
    )
    policy = load_config(tmp_path).forge_retry
    assert (policy.retries, policy.backoff_seconds, policy.transient_statuses) == (1, 2.5, (503,))
    assert policy.transient_messages == ("try again",)
    assert policy.rate_limit_messages == ("abuse detection",)


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ({"retry": 3}, "unknown key"),
        ({"transient_statuses": 504}, "transient_statuses must be a list"),
        ({"retries": True}, "retries must be a whole number"),
        ({"retries": 11}, "retries must be a whole number"),
        ({"backoff_seconds": "5"}, "backoff_seconds must be a number"),
        ({"max_retry_after_seconds": -1}, "max_retry_after_seconds must be a number"),
        ({"backoff_seconds": 90}, "must not exceed max_backoff_seconds"),
        ({"transient_statuses": [404]}, "must be 5xx status codes"),
        ({"transient_statuses": ["504"]}, "must be 5xx status codes"),
        ({"transient_statuses": [504, 504]}, "entries must be unique"),
        ({"transient_messages": [5]}, "transient_messages entries must be strings"),
        ({"rate_limit_messages": [" "]}, "rate_limit_messages entries must be non-empty"),
    ],
)
def test_a_forge_retry_table_that_could_misbehave_is_refused(table, message):
    with pytest.raises(ValueError, match=message):
        ForgeRetryConfig.from_table(table)
