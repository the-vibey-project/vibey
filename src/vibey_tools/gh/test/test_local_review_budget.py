# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a review request may take: the slot it waits for, the time it is given, what it writes.

PR #1312's sovereign review gave no verdict. Read from the operator's host's Ollama log, the
model was free (nothing else asked it anything for twenty minutes); its first part, a
46,222-token prompt, took 145s to read, and the model then wrote ~9,950 tokens at 22.5/s --
past an 8,192-token reasoning reserve nothing enforced -- until a fixed 600s cut it off. The
retry, identical at temperature 0, wrote 10,017 tokens and was cut off the same way. And on
2026-09-30 a review queued ~10 minutes behind another client's request was cut off seconds
into its own work and reported in the same words, `model_timeout`.

So pinned here: the reserve is sent as `num_predict`; each request's deadline scales with
its size at declared rates, never under the fixed timeout; the model is waited for, bounded,
before a request is sent; a busy model is told apart from a slow one, and only the busy one
is retried; and a part that cannot be answered leaves no verdict at all.
"""

from __future__ import annotations

import json
import urllib.error
from collections.abc import Mapping
from typing import Any

import pytest
from test_local_review import (  # type: ignore[import-not-found]
    _answer,
    _diff,
    _documents,
    _file_diff,
    _outcome,
    _verdict,
    _whole_verdict,
)

from vibey_gh import local_review
from vibey_gh.config import PrAutomationFallbackConfig, load_config
from vibey_gh.fit import ContextSizer
from vibey_gh.review_outcome import REVIEW_OUTCOMES

WHOLE = ["--role", "sovereign", "--scope", "full"]


@pytest.fixture
def slept(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """The backoff, recorded rather than slept."""
    waits: list[float] = []
    monkeypatch.setattr(local_review.time, "sleep", waits.append)
    return waits


def _requests(monkeypatch: pytest.MonkeyPatch, answer: dict) -> list[tuple[dict, Any]]:
    """Every review request as sent, with the timeout it was sent with."""
    sent: list[tuple[dict, Any]] = []

    def fake_urlopen(request, timeout=None):
        sent.append((json.loads(request.data), timeout))
        return _answer(request, answer)

    monkeypatch.setattr(local_review.urllib.request, "urlopen", fake_urlopen)
    return sent


# --- the deadline ------------------------------------------------------------------------


def test_a_deadline_scales_with_what_a_request_reads_and_may_write():
    """PR #1312's first part: 46,222 prompt tokens, read at the declared 200/s, and up to a
    16,384-token reserve written at 20/s -- 1,051s, where a fixed 600 cut it off."""
    deadline = local_review.RequestDeadline(
        floor_seconds=600, prompt_tokens_per_second=200, output_tokens_per_second=20
    )

    assert deadline.scaled
    assert deadline.seconds(46222, 16384) == 1051  # ceil(231.11 + 819.2)
    assert deadline.seconds(92444, 16384) > deadline.seconds(46222, 16384)
    # Never under the fixed timeout it had before: a small request keeps it.
    assert deadline.seconds(100, 100) == 600
    said = deadline.explain(46222, 16384)
    assert "46222 prompt tokens read at 200/s (231s)" in said
    assert "16384 tokens of reasoning and answer written at 20/s (819s)" in said


def test_without_rates_the_deadline_is_the_fixed_timeout():
    fixed = local_review.RequestDeadline(floor_seconds=1800)

    assert not fixed.scaled
    assert fixed.seconds(10**6, 10**6) == 1800
    assert fixed.explain(1, 1) == "the fixed timeout_seconds (1800s)"


@pytest.mark.parametrize(
    "fields",
    [
        {"prompt_tokens_per_second": 200},  # half a deadline: the answer would be unscaled
        {"output_tokens_per_second": 20},
        {"prompt_tokens_per_second": -1, "output_tokens_per_second": 20},
        {"floor_seconds": 1.5},
    ],
)
def test_a_deadline_is_both_rates_or_neither(fields):
    with pytest.raises(ValueError):
        local_review.RequestDeadline(**fields)


def test_each_request_is_sent_with_the_deadline_for_its_own_size_and_the_reserve_as_its_cap(
    monkeypatch,
):
    """The reserve is the most the model may write (`num_predict`), and the time it is
    given grows with the request: a larger diff, a longer deadline."""
    sizer = ContextSizer(ceiling_tokens=65536, reserve_tokens=16384, chars_per_token=3)
    deadline = local_review.RequestDeadline(
        floor_seconds=30, prompt_tokens_per_second=200, output_tokens_per_second=20
    )
    sent = _requests(monkeypatch, _verdict())

    for diff in ("+ small\n", "+ larger\n" * 4000):
        local_review.call_ollama("http://h:1", "m", diff, 10**6, 30, sizer=sizer, deadline=deadline)

    (small, small_timeout), (large, large_timeout) = sent
    for payload in (small, large):
        assert payload["options"]["num_predict"] == 16384
    assert small_timeout < large_timeout
    system, user = (message["content"] for message in large["messages"])
    total = len(system) + len(user) + len(json.dumps(large["format"]))
    assert large_timeout == deadline.seconds(sizer.tokens(total), 16384)


def test_a_sizer_with_no_reserve_sends_no_cap(monkeypatch):
    """`num_predict: 0` is not "no reserve" to a runner, so none is sent: with nothing
    reserved there is nothing to enforce, and the request is what it was before."""
    sent = _requests(monkeypatch, _verdict())

    local_review.call_ollama(
        "http://h:1", "m", "+ a\n", 100, 5, sizer=ContextSizer(reserve_tokens=0)
    )

    ((payload, timeout),) = sent
    assert "num_predict" not in payload["options"] and timeout == 5


def test_a_model_that_writes_its_whole_reserve_is_named_not_waited_for():
    with pytest.raises(local_review.ReviewRefused) as refused:
        local_review.SIZED_CHAT.answer(
            {
                "prompt_eval_count": 10,
                "done_reason": "length",
                "message": {"thinking": "x" * 40, "content": ""},
            },
            num_ctx=65536,
            reserve=16384,
            codes=("a", "b"),
        )
    assert "done_reason=length" in str(refused.value)
    assert "its 16384-token reasoning reserve" in str(refused.value)
    assert refused.value.code == "answer_incomplete"


# --- the slot ------------------------------------------------------------------------------


class _Runner:
    """A model server, as `vibey_gh.slots.OllamaClient` speaks to one."""

    def __init__(self, *, version: str = "0.34.2", status: int = 200, took: float = 2.0):
        self.base_url = ""
        self._version = version
        self._status = status
        self.took = took
        self.now = 0.0
        self.probes: list[tuple[dict, float]] = []

    def clock(self) -> float:
        return self.now

    def version(self) -> str:
        return self._version

    def loaded(self) -> list[dict[str, Any]] | None:
        return []

    def digest(self, model: str) -> str:
        return ""

    def chat(self, body: Mapping[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
        self.probes.append((dict(body), timeout_s))
        self.now += self.took
        if self._status == 200:
            return 200, {"done_reason": "length"}
        if self._status == 0:
            return 0, {"error": "no answer"}
        return self._status, {"error": "model 'gpt-oss:20b' not found"}


def _slot(runner: _Runner, seconds: int = 900) -> local_review.SlotWait:
    return local_review.SlotWait(seconds, client=lambda base_url: runner, clock=runner.clock)


def test_a_free_model_is_asked_one_token_at_the_window_the_review_needs():
    """The probe asks for the review's own window, so the runner is loaded as the review
    will use it rather than reloaded between the two."""
    runner = _Runner(took=4.8)

    assert _slot(runner).wait("http://h:1", "gpt-oss:20b", 65536) == pytest.approx(4.8)
    ((probe, timeout),) = runner.probes
    assert probe["model"] == "gpt-oss:20b"
    assert probe["options"] == {"num_ctx": 65536, "num_predict": 1, "temperature": 0}
    assert probe["stream"] is False and timeout == 900


def test_a_model_serving_other_work_past_the_wait_is_busy_and_the_wait_is_bounded():
    runner = _Runner(status=0, took=900.0)

    with pytest.raises(local_review.ModelBusy) as busy:
        _slot(runner).wait("http://h:1", "gpt-oss:20b", 65536)

    assert busy.value.code == "model_busy"
    assert "did not come free within slot_wait_seconds (900s)" in str(busy.value)
    # One probe, bounded by the declared wait: it never waits again on its own.
    assert [timeout for _, timeout in runner.probes] == [900]


def test_a_runner_that_drops_the_probe_early_is_a_transport_failure_not_busy():
    runner = _Runner(status=0, took=3.0)

    with pytest.raises(urllib.error.URLError, match="stopped answering 3s into"):
        _slot(runner).wait("http://h:1", "m", 4096)


def test_a_runner_that_does_not_answer_at_all_is_unreachable():
    runner = _Runner(version="")

    with pytest.raises(urllib.error.URLError, match="did not answer"):
        _slot(runner).wait("http://h:1", "m", 4096)
    assert runner.probes == []


def test_a_runner_that_refuses_the_probe_is_refused():
    runner = _Runner(status=404)

    with pytest.raises(local_review.ReviewRefused) as refused:
        _slot(runner).wait("http://h:1", "gpt-oss:20b", 4096)
    assert refused.value.code == "model_refused"
    assert "HTTP 404" in str(refused.value) and "not found" in str(refused.value)


def test_no_wait_asks_nothing_and_a_non_http_endpoint_is_refused():
    runner = _Runner()

    assert _slot(runner, seconds=0).wait("http://h:1", "m", 4096) == 0.0
    assert runner.probes == []
    with pytest.raises(ValueError, match="non-HTTP"):
        _slot(runner).wait("file:///etc/passwd", "m", 4096)
    with pytest.raises(ValueError):
        local_review.SlotWait(-1)


def test_the_probe_speaks_through_the_familys_ollama_client():
    """Dogfooded (10.e): with no client injected, the probe is `vibey_gh.slots.OllamaClient`."""
    from vibey_gh.slots import OllamaClient

    client = local_review.SlotWait(5)._connect("http://h:1")
    assert isinstance(client, OllamaClient) and client.base_url == "http://h:1"


# --- busy and slow, through a review -------------------------------------------------------


def test_a_busy_model_is_retried_after_the_backoff_and_then_named(monkeypatch, tmp_path, slept):
    """A queue, not a verdict on the request: waiting and asking again can succeed. The
    review request itself is never sent while the model is busy."""
    asked: list[object] = []
    monkeypatch.setattr(local_review.urllib.request, "urlopen", lambda *a, **k: asked.append(a))

    def busy(self, base_url, model, num_ctx):
        raise local_review.ModelBusy("the local model did not come free within 900s")

    monkeypatch.setattr(local_review.SlotWait, "wait", busy)
    record = tmp_path / "outcome.json"

    argv = ["--diff", str(_diff(tmp_path)), "--outcome", str(record)]
    assert local_review.review([*argv, "--retry-backoff-seconds", "7"]) == 1

    assert asked == [] and slept == [7]
    said = _outcome(record)
    assert (said["code"], said["attempts"]) == ("model_busy", 2)
    assert said["reason"] == "the local model did not come free within 900s (2 attempts)"


def test_a_model_that_comes_free_on_the_retry_gives_its_verdict(monkeypatch, tmp_path, slept):
    waits: list[int] = []

    def busy_once(self, base_url, model, num_ctx):
        waits.append(num_ctx)
        if len(waits) == 1:
            raise local_review.ModelBusy("busy")
        return 12.0

    monkeypatch.setattr(local_review.SlotWait, "wait", busy_once)
    sent = _requests(monkeypatch, _verdict())
    record = tmp_path / "outcome.json"

    assert local_review.review(["--diff", str(_diff(tmp_path)), "--outcome", str(record)]) == 0
    assert len(sent) == 1 and slept == [30]
    # Each wait asks for the window the request it precedes will use.
    assert waits == [sent[0][0]["options"]["num_ctx"]] * 2
    assert (_outcome(record)["code"], _outcome(record)["attempts"]) == ("reviewed", 2)


def test_a_request_slow_on_its_own_input_is_not_retried_and_says_why(monkeypatch, tmp_path, slept):
    """The model came free, the request started, and the deadline still ran out: at
    temperature 0 the same request runs the same way again, so asking again only costs
    another deadline (#1312: 9,943 then 10,017 tokens, both cut off)."""
    monkeypatch.setattr(local_review.SlotWait, "wait", lambda self, *_: 3.0)
    calls: list[object] = []

    def times_out(request, timeout=None):
        calls.append(timeout)
        raise TimeoutError("timed out")

    monkeypatch.setattr(local_review.urllib.request, "urlopen", times_out)
    record = tmp_path / "outcome.json"

    argv = ["--diff", str(_diff(tmp_path)), "--outcome", str(record), "--timeout", "45"]
    argv += ["--prompt-tokens-per-second", "200", "--output-tokens-per-second", "20"]
    assert local_review.review(argv) == 1

    assert len(calls) == 1 and slept == []
    said = _outcome(record)
    assert (said["code"], said["attempts"]) == ("model_timeout", 1)
    assert said["reason"].startswith("the model came free 3s after asking")
    assert f"within its {calls[0]}s deadline" in said["reason"]
    assert "slow on this input, not unreachable or busy" in said["reason"]


def test_a_part_that_cannot_be_answered_leaves_no_verdict_at_all(monkeypatch, tmp_path, slept):
    """Part 1 passed; part 2 ran past its deadline. A pass needs every part, so there is no
    verdict -- never a pass on the half that answered -- and the record says how far it got."""
    monkeypatch.setattr(local_review.SlotWait, "wait", lambda self, *_: 0.0)
    files = [_file_diff(f"f{n}.py", ["+ changed\n" * 100]) for n in range(2)]
    diff = tmp_path / "big.diff"
    diff.write_text("".join(files), encoding="utf-8")
    calls: list[object] = []

    def second_part_is_slow(request, timeout=None):
        calls.append(request)
        if len(calls) > 1:
            raise TimeoutError("timed out")
        return _answer(request, _verdict())

    monkeypatch.setattr(local_review.urllib.request, "urlopen", second_part_is_slow)
    record = tmp_path / "outcome.json"

    argv = ["--diff", str(diff), "--max-chars", str(len(files[0]) + 10), "--outcome"]
    assert local_review.review([*argv, str(record)]) == 1

    said = _outcome(record)
    assert (said["code"], said["parts"], said["attempts"]) == ("model_timeout", 2, 2)
    assert said["reason"].startswith("part 2 of 2 (f1.py): the model came free")
    assert len(calls) == 2 and slept == []


def test_every_part_of_a_whole_review_fits_its_window_beside_the_reserve(
    monkeypatch, capsys, tmp_path
):
    """The planner sizes each part against the window less the reserve the model may now
    fill, the declared documents and the instructions: no request is sent that the window
    cannot hold beside everything the model may write."""
    monkeypatch.setattr(local_review.SlotWait, "wait", lambda self, *_: 0.0)
    context = _documents(tmp_path, **{"README.md": "r" * 9000})
    files = [_file_diff(f"f{n}.py", ["+ changed line\n" * 300]) for n in range(6)]
    diff = tmp_path / "big.diff"
    diff.write_text("".join(files), encoding="utf-8")
    sent = _requests(monkeypatch, _whole_verdict())
    window, reserve = 12288, 4096

    argv = ["--diff", str(diff), *WHOLE, "--context-dir", str(context)]
    argv += ["--context-paths", "README.md", "--max-chunks", "16"]
    argv += ["--context-window", str(window), "--reasoning-reserve", str(reserve)]
    assert local_review.review(argv) == 0

    sizer = ContextSizer(ceiling_tokens=window, reserve_tokens=reserve, chars_per_token=3)
    assert len(sent) > 1
    for payload, _ in sent:
        system, user = (message["content"] for message in payload["messages"])
        total = len(system) + len(user) + len(json.dumps(payload["format"]))
        assert sizer.tokens(total) + reserve <= window
        assert payload["options"]["num_ctx"] <= window
        assert payload["options"]["num_predict"] == reserve
        assert '<document path="README.md">' in user  # every part judged against it whole
    verdict = json.loads(capsys.readouterr().out)
    assert verdict["pass"] is True and len(verdict["review_parts"]) == len(sent)


# --- declared, not compiled in -------------------------------------------------------------


def test_the_rates_and_the_wait_are_configuration_with_measured_defaults(tmp_path):
    defaults = PrAutomationFallbackConfig()
    assert (
        defaults.prompt_tokens_per_second,
        defaults.output_tokens_per_second,
        defaults.slot_wait_seconds,
        defaults.reasoning_reserve_tokens,
    ) == (200, 20, 900, 16384)
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation.fallback]\nprompt_tokens_per_second = 0\noutput_tokens_per_second = 0\n"
        "slot_wait_seconds = 0\n",
        "utf-8",
    )
    loaded = load_config(tmp_path).pr_automation.fallback
    assert (
        loaded.prompt_tokens_per_second,
        loaded.output_tokens_per_second,
        loaded.slot_wait_seconds,
    ) == (0, 0, 0)


@pytest.mark.parametrize(
    "bad",
    [
        {"prompt_tokens_per_second": 0},
        {"output_tokens_per_second": 0},
        {"prompt_tokens_per_second": 2.5},
        {"output_tokens_per_second": -1},
        {"slot_wait_seconds": 3601},
        {"slot_wait_seconds": True},
    ],
)
def test_a_rate_or_wait_the_configuration_cannot_honour_is_refused(bad):
    with pytest.raises(ValueError):
        PrAutomationFallbackConfig(**bad)  # type: ignore[arg-type]


def test_the_review_step_is_rendered_with_the_declared_rates_and_wait(tmp_path):
    import dataclasses

    from vibey_gh.config import GhConfig, PrAutomationConfig
    from vibey_gh.install import WORKFLOWS, render_workflow

    fallback = dataclasses.replace(
        PrAutomationFallbackConfig(),
        prompt_tokens_per_second=310,
        output_tokens_per_second=21,
        slot_wait_seconds=420,
    )
    cfg = GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(fallback=fallback))
    rendered = render_workflow(WORKFLOWS / "pr-review.yml", cfg)

    assert "--prompt-tokens-per-second 310 \\" in rendered
    assert "--output-tokens-per-second 21 \\" in rendered
    assert "--slot-wait-seconds 420 \\" in rendered
    assert "__VIBEY_GH_FALLBACK_" not in rendered


def test_the_cli_forwards_the_rates_and_the_wait(monkeypatch):
    from vibey_gh import cli

    seen: list[list[str]] = []
    monkeypatch.setattr(local_review, "review", lambda argv: seen.append(argv) or 0)

    argv = ["local-review", "--prompt-tokens-per-second", "250"]
    argv += ["--output-tokens-per-second", "18", "--slot-wait-seconds", "0"]
    assert cli.main(argv) == 0
    assert seen == [
        ["--prompt-tokens-per-second", "250", "--output-tokens-per-second", "18"]
        + ["--slot-wait-seconds", "0"]
    ]


def test_busy_is_a_code_in_the_closed_vocabulary():
    assert REVIEW_OUTCOMES.describe("model_busy").startswith("the local model was serving")
