# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each sovereign review request's timings: recorded, then read back as rates.

On GitHub's `ubuntu-24.04-arm` CPU runner the sovereign review either answered in minutes or
gave no verdict at about 160 minutes, its deadline scaled from another machine's rates. The
operator's call was to measure before changing anything. So pinned here: every request
attempt and every slot probe is recorded in the outcome record -- what it sent, its deadline
and how that was derived, how long it took, how it ended in the closed vocabulary, and
Ollama's own counters -- without changing anything the review decides or prints; a run
stopped mid-request still leaves the request it was waiting on; and `vibey-gh
review-timings` reads those records back into per-model, per-runner rates and suggests
deadline rates only from enough observations.

Module-level test functions rather than classes with interfaces beside them (ADR-0016): the
rule is about production code, and pytest collects functions.
"""

from __future__ import annotations

import io
import itertools
import json
import math
import pathlib
import urllib.error
from collections.abc import Mapping
from typing import Any

import pytest
from test_local_review import _answer, _diff, _outcome, _verdict  # type: ignore[import-not-found]

from vibey_gh import cli, local_review
from vibey_gh.fit import ContextSizer
from vibey_gh.interfaces.review_timings_interface import (
    RequestLogInterface,
    ReviewTimingsInterface,
    RunnerLabelInterface,
    TimingsGroupInterface,
    TimingsReportInterface,
)
from vibey_gh.review_timings import (
    MINIMUM_OBSERVATIONS,
    RequestLog,
    ReviewTimings,
    RunnerLabel,
    TimingsGroup,
    TimingsReport,
)

# The request flags every review here is run with, so what it records can be worked out
# exactly: a 65,536-token window, a 16,384-token reserve, three characters a token, and the
# deadline rates the hosted runner was declared to sustain.
FLAGS = [
    "--model",
    "gpt-oss:20b",
    "--timeout",
    "30",
    "--context-window",
    "65536",
    "--reasoning-reserve",
    "16384",
    "--chars-per-token",
    "3",
    "--prompt-tokens-per-second",
    "40",
    "--output-tokens-per-second",
    "2",
    "--retry-backoff-seconds",
    "7",
]
SIZER = ContextSizer(ceiling_tokens=65536, reserve_tokens=16384, chars_per_token=3)
HOSTED = {
    "RUNNER_ENVIRONMENT": "github-hosted",
    "RUNNER_OS": "Linux",
    "RUNNER_ARCH": "ARM64",
    "RUNNER_NAME": "GitHub Actions 1000000001",
}
SECOND = 1_000_000_000  # Ollama's durations are nanoseconds


class _Clock:
    """Monotonic time that moves only when a fake model spends it."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> _Clock:
    return _Clock()


@pytest.fixture
def slept(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr(local_review.time, "sleep", waits.append)
    return waits


def _sent_size(payload: Mapping[str, Any]) -> tuple[int, int]:
    """`(characters, estimated tokens)` of a request as sent: what its entry records."""
    system, user = (message["content"] for message in payload["messages"])
    total = len(system) + len(user) + len(json.dumps(payload["format"]))
    return total, SIZER.tokens(total)


def _counters(payload: Mapping[str, Any], **extra: object) -> dict[str, object]:
    """Ollama's counters for an answer to `payload`: it read half of what the request was
    sized for, in 30.5 seconds, and wrote 412 tokens in 60."""
    options = payload["options"]
    return {
        "prompt_eval_count": (options["num_ctx"] - options["num_predict"]) // 2,
        "prompt_eval_duration": 30_500_000_000,
        "eval_count": 412,
        "eval_duration": 60 * SECOND,
        "load_duration": 1_250_000_000,
        "total_duration": 95 * SECOND,
    } | extra


def _model(monkeypatch, clock: _Clock, answer=None, took: float = 95.25, **extra) -> list[dict]:
    """A model that answers every review request after `took` seconds, with its counters."""
    sent: list[dict] = []

    def fake_urlopen(request, timeout=None):
        payload = json.loads(request.data)
        sent.append(payload | {"_timeout": timeout})
        clock.now += took
        return _answer(request, answer or _verdict(), **_counters(payload, **extra))

    monkeypatch.setattr(local_review.urllib.request, "urlopen", fake_urlopen)
    return sent


class _Server:
    """A model server as `vibey_gh.slots.OllamaClient` speaks to one, for the slot probe."""

    def __init__(self, clock: _Clock, *, status: int = 200, took: float = 4.0, up: bool = True):
        self.base_url = ""
        self._clock = clock
        self._status = status
        self._took = took
        self._up = up
        self.probes: list[dict] = []

    def version(self) -> str:
        return "0.34.2" if self._up else ""

    def loaded(self) -> list[dict[str, Any]] | None:
        return []

    def digest(self, model: str) -> str:
        return ""

    def chat(self, body: Mapping[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
        self.probes.append(dict(body))
        self._clock.now += self._took
        if self._status == 200:
            return 200, {
                "done_reason": "length",
                "prompt_eval_count": 12,
                "prompt_eval_duration": SECOND // 2,
                "eval_count": 1,
                "eval_duration": SECOND // 4,
                "load_duration": 3 * SECOND,
            }
        if self._status == 0:
            return 0, {"error": "no answer"}
        return self._status, {"error": "model 'gpt-oss:20b' not found"}


def _serve_probes(monkeypatch, server: _Server) -> None:
    monkeypatch.setattr(local_review.SlotWait, "_connect", lambda self, base_url: server)


def _review(tmp_path, clock, *extra: str, environ=None) -> tuple[int, dict]:
    record = tmp_path / "outcome.json"
    argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--outcome", str(record), *extra]
    status = local_review.review(argv, environ=HOSTED if environ is None else environ, clock=clock)
    return status, _outcome(record)


# --- what one review records ----------------------------------------------------------------


def test_an_answered_request_records_what_it_sent_its_deadline_its_time_and_ollamas_counters(
    monkeypatch, clock, tmp_path
):
    sent = _model(monkeypatch, clock)

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "0")

    assert status == 0
    assert record["model"] == "gpt-oss:20b"
    assert record["runner"] == {
        "environment": "github-hosted",
        "os": "Linux",
        "arch": "ARM64",
        "name": "GitHub Actions 1000000001",
    }
    ((payload,),) = [sent]
    chars, tokens = _sent_size(payload)
    seconds = local_review.RequestDeadline(30, 40, 2).seconds(tokens, 16384)
    read = (payload["options"]["num_ctx"] - 16384) // 2
    assert payload["_timeout"] == seconds  # the deadline recorded is the one it was sent with
    assert record["requests"] == [
        {
            "kind": "request",
            "part": 1,
            "of": 1,
            "attempt": 1,
            "at_seconds": 0.0,
            "finished": True,
            "elapsed_seconds": 95.25,
            "chars": chars,
            "prompt_tokens_estimated": tokens,
            "num_ctx": payload["options"]["num_ctx"],
            "num_predict": 16384,
            "slot_waited_seconds": None,
            "deadline_seconds": seconds,
            "deadline": {
                "scaled": True,
                "floor_seconds": 30,
                "prompt_tokens_per_second": 40,
                "output_tokens_per_second": 2,
                "prompt_tokens": tokens,
                "output_tokens": 16384,
            },
            "code": "reviewed",
            "answered": True,
            "ollama": {
                "prompt_eval_count": read,
                "eval_count": 412,
                "prompt_eval_seconds": 30.5,
                "eval_seconds": 60.0,
                "load_seconds": 1.25,
                "total_seconds": 95.0,
                "prompt_tokens_per_second": round(read / 30.5, 3),
                "output_tokens_per_second": round(412 / 60, 3),
                "done_reason": "stop",
            },
        }
    ]


def test_recording_changes_nothing_the_review_prints_or_decides(
    monkeypatch, clock, tmp_path, capsys
):
    """The verdict on standard output, and the exit status, are the same whether or not an
    outcome record -- and with it every request's timings -- is written."""
    _model(monkeypatch, clock, answer=_verdict(summary="fine", findings=[]))
    argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--slot-wait-seconds", "0"]

    assert local_review.review(argv, environ={}, clock=clock) == 0
    without = capsys.readouterr().out
    assert local_review.review([*argv, "--outcome", str(tmp_path / "o.json")], clock=clock) == 0
    assert capsys.readouterr().out == without


def test_the_runner_is_read_from_the_process_environment_by_default(monkeypatch, clock, tmp_path):
    _model(monkeypatch, clock)
    monkeypatch.setenv("RUNNER_OS", "Linux")
    monkeypatch.delenv("RUNNER_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RUNNER_ARCH", raising=False)
    monkeypatch.delenv("RUNNER_NAME", raising=False)
    record = tmp_path / "outcome.json"

    argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--slot-wait-seconds", "0"]
    assert local_review.review([*argv, "--outcome", str(record)], clock=clock) == 0

    assert _outcome(record)["runner"] == {"os": "Linux"}


def test_a_request_slow_on_its_input_is_recorded_with_its_slot_probe(monkeypatch, clock, tmp_path):
    """The case that cost the verdicts: the model came free, the request started, and its
    deadline ran out. The probe that waited for the model is recorded and marked as one,
    with its own counters -- the time to load the model among them."""
    server = _Server(clock, took=4.0)
    _serve_probes(monkeypatch, server)

    def times_out(request, timeout=None):
        clock.now += timeout
        raise TimeoutError("timed out")

    monkeypatch.setattr(local_review.urllib.request, "urlopen", times_out)

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "900")

    assert status == 1 and record["code"] == "model_timeout"
    probe, request = record["requests"]
    assert probe == {
        "kind": "slot_probe",
        "part": 1,
        "of": 1,
        "attempt": 1,
        "at_seconds": 0.0,
        "finished": True,
        "elapsed_seconds": 4.0,
        "num_ctx": request["num_ctx"],
        "num_predict": 1,
        "deadline_seconds": 900,
        "code": None,
        "answered": True,
        "ollama": {
            "prompt_eval_count": 12,
            "eval_count": 1,
            "prompt_eval_seconds": 0.5,
            "eval_seconds": 0.25,
            "load_seconds": 3.0,
            "prompt_tokens_per_second": 24.0,
            "output_tokens_per_second": 4.0,
            "done_reason": "length",
        },
    }
    assert request["kind"] == "request" and request["attempt"] == 1
    assert request["at_seconds"] == 4.0 and request["slot_waited_seconds"] is not None
    assert request["elapsed_seconds"] == request["deadline_seconds"]
    assert (request["code"], request["answered"], request["ollama"]) == (
        "model_timeout",
        False,
        None,
    )


def test_a_busy_model_records_each_probe_and_sends_no_request(monkeypatch, clock, tmp_path, slept):
    _serve_probes(monkeypatch, _Server(clock, status=0, took=1.0))
    sent: list[object] = []
    monkeypatch.setattr(local_review.urllib.request, "urlopen", lambda *a, **k: sent.append(a))

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "1")

    assert status == 1 and record["code"] == "model_busy" and sent == [] and slept == [7]
    assert [(e["kind"], e["attempt"], e["code"], e["answered"]) for e in record["requests"]] == [
        ("slot_probe", 1, "model_busy", False),
        ("slot_probe", 2, "model_busy", False),
    ]


@pytest.mark.parametrize(
    ("server", "code"),
    [
        ({"up": False}, "model_unreachable"),
        ({"status": 0, "took": 2.0}, "model_unreachable"),
        ({"status": 404}, "model_refused"),
    ],
)
def test_a_probe_that_fails_says_how_in_its_entry(
    monkeypatch, clock, tmp_path, slept, server, code
):
    _serve_probes(monkeypatch, _Server(clock, **server))

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "900", "--retries", "0")

    assert status == 1 and record["code"] == code
    ((probe,),) = [record["requests"]]
    assert (probe["kind"], probe["code"], probe["answered"], probe["ollama"]) == (
        "slot_probe",
        code,
        False,
        None,
    )


def test_a_probe_that_fails_unnamed_is_recorded_as_unknown(clock):
    class _Broken(_Server):
        def chat(self, body, timeout_s):
            raise RuntimeError("the client itself broke")

    log = RequestLog(clock=clock)
    wait = local_review.SlotWait(5, client=lambda base_url: _Broken(clock), log=log)

    with pytest.raises(RuntimeError):
        wait.wait("http://h:1", "m", 4096)
    ((probe,),) = [log.entries()]
    assert (probe["kind"], probe["finished"], probe["code"]) == ("slot_probe", True, "unknown")


@pytest.mark.parametrize(
    ("raised", "code"),
    [
        (urllib.error.URLError("connection refused"), "model_unreachable"),
        (TimeoutError("timed out"), "model_timeout"),
        (
            urllib.error.HTTPError(
                "http://h:1/api/chat",
                400,
                "Bad Request",
                {},
                io.BytesIO(b"{}"),  # type: ignore[arg-type]
            ),
            "model_refused",
        ),
    ],
)
def test_a_request_the_transport_failed_records_its_code_and_each_attempt(
    monkeypatch, clock, tmp_path, slept, raised, code
):
    """Sent at once, with nothing saying the model was free: a timeout is a transport failure
    and retried, so both attempts are recorded; a refusal is never retried."""

    def fail(request, timeout=None):
        clock.now += 3.0
        raise raised

    monkeypatch.setattr(local_review.urllib.request, "urlopen", fail)

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "0")

    assert status == 1 and record["code"] == code
    attempts = 1 if code == "model_refused" else 2
    assert [(e["attempt"], e["code"], e["answered"]) for e in record["requests"]] == [
        (n, code, False) for n in range(1, attempts + 1)
    ]
    assert all(e["elapsed_seconds"] == 3.0 for e in record["requests"])


def test_an_answer_that_is_no_verdict_still_records_the_models_counters(
    monkeypatch, clock, tmp_path
):
    """`done_reason=length`: the model wrote its whole reserve. No verdict -- and the rates it
    sustained while writing it are exactly what the deadline needs to know."""
    _model(monkeypatch, clock, done_reason="length")

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "0")

    assert status == 1 and record["code"] == "answer_incomplete"
    ((entry,),) = [record["requests"]]
    assert (entry["code"], entry["answered"]) == ("answer_incomplete", True)
    assert entry["ollama"]["done_reason"] == "length"
    assert entry["ollama"]["output_tokens_per_second"] == round(412 / 60, 3)


def test_a_reply_that_is_not_json_is_recorded_as_unusable(monkeypatch, clock, tmp_path):
    class _Garbled:
        def read(self) -> bytes:
            return b"<html>proxy error</html>"

        def __enter__(self):
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(local_review.urllib.request, "urlopen", lambda *a, **k: _Garbled())

    status, record = _review(tmp_path, clock, "--slot-wait-seconds", "0")

    assert status == 1 and record["code"] == "answer_unusable"
    ((entry,),) = [record["requests"]]
    assert (entry["code"], entry["answered"], entry["ollama"]) == ("answer_unusable", False, None)


def test_a_request_interrupted_unnamed_is_closed_as_unknown_and_still_raised(monkeypatch, clock):
    """A runner cancelling the job interrupts the process while it waits on the model: the
    entry is closed, `unknown`, with how long it had waited, and the interruption goes on."""

    class _Cancelled(BaseException):
        pass

    def cancelled(request, timeout=None):
        clock.now += 120.0
        raise _Cancelled

    monkeypatch.setattr(local_review.urllib.request, "urlopen", cancelled)
    log = RequestLog(clock=clock)

    with pytest.raises(_Cancelled):
        local_review.call_ollama("http://h:1", "m", "+ a\n", 100, 45, sizer=SIZER, log=log)

    ((entry,),) = [log.entries()]
    assert (entry["finished"], entry["code"], entry["elapsed_seconds"]) == (True, "unknown", 120.0)
    # Without a scaled deadline, the fixed timeout is the basis it records.
    assert entry["deadline_seconds"] == 45
    assert entry["deadline"]["scaled"] is False and entry["deadline"]["floor_seconds"] == 45


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (local_review.ReviewRefused("x", code="prompt_truncated"), "prompt_truncated"),
        (local_review.ModelTooSlow("slow"), "model_timeout"),
        (TimeoutError(), "model_timeout"),
        (urllib.error.URLError(TimeoutError()), "model_timeout"),
        (OSError("socket died"), "model_unreachable"),
        (TypeError("expected a JSON object"), "answer_unusable"),
        (KeyError("message"), "answer_unusable"),
        (AttributeError("list has no get"), "answer_unusable"),
        (json.JSONDecodeError("x", "", 0), "answer_unusable"),
        (ValueError("refusing a non-HTTP model endpoint"), "unknown"),
    ],
)
def test_every_way_a_request_ends_is_a_code_in_the_closed_vocabulary(error, code):
    assert local_review.SIZED_CHAT.code(error) == code


def test_a_review_with_no_log_sends_exactly_what_one_with_a_log_sends(monkeypatch, clock):
    """The log is a witness, not a participant: the same diff, reviewed with and without one,
    sends the same request (but for its random check codes) and returns the same verdict."""
    sent = _model(monkeypatch, clock)
    log = RequestLog(clock=clock)
    verdicts = [
        local_review.SovereignReview("http://h:1", "m", 10**6, 30, SIZER, log=chosen).run("+ a\n")
        for chosen in (None, log)
    ]

    assert verdicts[0][0] == verdicts[1][0] and verdicts[0][2] == verdicts[1][2]
    for payload in sent:
        payload["messages"] = [len(message["content"]) for message in payload["messages"]]
    assert sent[0] == sent[1]
    assert [entry["code"] for entry in log.entries()] == ["reviewed"]


def test_each_part_of_a_chunked_review_is_recorded_by_part_and_attempt(
    monkeypatch, clock, tmp_path
):
    from test_local_review import _file_diff  # type: ignore[import-not-found]

    files = [_file_diff(f"f{n}.py", ["+ changed\n" * 100]) for n in range(2)]
    diff = tmp_path / "big.diff"
    diff.write_text("".join(files), encoding="utf-8")
    _model(monkeypatch, clock, took=10.0)
    record = tmp_path / "outcome.json"

    argv = ["--diff", str(diff), *FLAGS, "--max-chars", str(len(files[0]) + 10)]
    argv += ["--slot-wait-seconds", "0", "--outcome", str(record)]
    assert local_review.review(argv, environ={}, clock=clock) == 0

    said = _outcome(record)
    assert said["runner"] == {}
    assert [(e["part"], e["of"], e["attempt"], e["at_seconds"]) for e in said["requests"]] == [
        (1, 2, 1, 0.0),
        (2, 2, 1, 10.0),
    ]


# --- a record that outlives a stopped process ---------------------------------------------


def test_a_record_is_kept_on_disk_while_a_request_is_waited_on(monkeypatch, clock, tmp_path):
    """A job cancelled mid-request -- by a newer push, or killed -- never reaches the end of
    the review. The record on disk then already names the request it was waiting on, as
    unfinished, coded `unknown`; a review that ends writes over it."""
    record = tmp_path / "outcome.json"
    seen: list[dict] = []

    def look_while_waiting(request, timeout=None):
        seen.append(_outcome(record))
        clock.now += 5.0
        return _answer(request, _verdict(), **_counters(json.loads(request.data)))

    monkeypatch.setattr(local_review.urllib.request, "urlopen", look_while_waiting)

    argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--slot-wait-seconds", "0"]
    assert local_review.review([*argv, "--outcome", str(record)], environ={}, clock=clock) == 0

    ((during,),) = [seen]
    assert (during["code"], during["reason"]) == ("unknown", local_review.IN_PROGRESS_REASON)
    ((waiting,),) = [during["requests"]]
    assert (waiting["finished"], waiting["elapsed_seconds"], waiting["code"]) == (False, None, None)
    assert waiting["deadline_seconds"] > 0
    finished = _outcome(record)
    assert finished["code"] == "reviewed" and finished["requests"][0]["finished"] is True


def test_a_record_that_cannot_be_kept_while_waiting_changes_nothing(monkeypatch, clock, tmp_path):
    """Best effort only: the directory is missing when the request starts, so the record
    cannot be written then. The review goes on, and its own last word is written as before."""
    record = tmp_path / "late" / "outcome.json"

    def make_room(request, timeout=None):
        record.parent.mkdir()
        return _answer(request, _verdict(), **_counters(json.loads(request.data)))

    monkeypatch.setattr(local_review.urllib.request, "urlopen", make_room)

    argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--slot-wait-seconds", "0"]
    assert local_review.review([*argv, "--outcome", str(record)], environ={}, clock=clock) == 0
    assert _outcome(record)["code"] == "reviewed"


# --- the log itself ---------------------------------------------------------------------------


def test_the_log_stamps_part_attempt_and_time_and_reports_every_change(clock):
    changes: list[list[dict]] = []
    log = RequestLog(clock=clock, on_change=changes.append)

    log.part(2, 3)
    assert (log.attempt(), log.attempt()) == (1, 2)
    clock.now += 1.5
    index = log.open("request", chars=10)
    clock.now += 2.25
    log.close(index, code="reviewed")
    log.part(3, 3)
    log.attempt()
    log.open("slot_probe")

    first, second = log.entries()
    assert first == {
        "kind": "request",
        "part": 2,
        "of": 3,
        "attempt": 2,
        "at_seconds": 1.5,
        "finished": True,
        "elapsed_seconds": 2.25,
        "chars": 10,
        "code": "reviewed",
        "answered": False,
        "ollama": None,
    }
    # Unfinished, it already carries every field an entry has.
    assert second == {
        "kind": "slot_probe",
        "part": 3,
        "of": 3,
        "attempt": 1,
        "at_seconds": 3.75,
        "finished": False,
        "elapsed_seconds": None,
        "code": None,
        "answered": False,
        "ollama": None,
    }
    assert len(changes) == 3 and changes[0][0]["finished"] is False
    # What it hands out is a copy: changing it changes nothing recorded.
    log.entries()[0]["code"] = "tampered"
    assert log.entries()[0]["code"] == "reviewed"


def test_the_log_reads_the_monotonic_clock_without_one(monkeypatch):
    ticks = itertools.chain([10.0, 10.0], itertools.repeat(13.0))
    monkeypatch.setattr("vibey_gh.review_timings.time.monotonic", lambda: next(ticks))
    log = RequestLog()

    log.close(log.open("request"))

    assert log.entries()[0]["elapsed_seconds"] == 3.0


@pytest.mark.parametrize(
    ("body", "figures"),
    [
        ("not a reply", None),
        (None, None),
        ({}, {"prompt_tokens_per_second": None, "output_tokens_per_second": None}),
        (
            {
                "prompt_eval_count": True,  # a bool is not a count
                "eval_count": -3,
                "prompt_eval_duration": float("nan"),
                "eval_duration": "60s",
                "load_duration": 0,
                "done_reason": 7,
            },
            {
                "load_seconds": 0.0,
                "prompt_tokens_per_second": None,
                "output_tokens_per_second": None,
            },
        ),
        (
            {"prompt_eval_count": 100, "prompt_eval_duration": 0, "eval_count": 5},
            {
                "prompt_eval_count": 100,
                "eval_count": 5,
                "prompt_eval_seconds": 0.0,
                "prompt_tokens_per_second": None,
                "output_tokens_per_second": None,
            },
        ),
    ],
)
def test_a_malformed_reply_is_never_read_as_a_figure(body, figures):
    assert RequestLog().figures(body) == figures


def test_a_deadline_records_the_basis_it_was_derived_from():
    scaled = local_review.RequestDeadline(600, 40, 2)
    assert scaled.basis(41152, 16384) == {
        "scaled": True,
        "floor_seconds": 600,
        "prompt_tokens_per_second": 40,
        "output_tokens_per_second": 2,
        "prompt_tokens": 41152,
        "output_tokens": 16384,
    }
    assert local_review.RequestDeadline(600).basis(1, 1)["scaled"] is False


# --- the runner -------------------------------------------------------------------------------


def test_the_runner_label_says_only_what_the_runner_stated():
    label = RunnerLabel.from_environ({"RUNNER_OS": "Linux", "RUNNER_ARCH": "ARM64", "HOME": "/"})

    assert label.as_json() == {"os": "Linux", "arch": "ARM64"}
    assert label.describe() == "Linux ARM64"
    assert RunnerLabel.from_environ(HOSTED).describe(with_name=True) == (
        "github-hosted Linux ARM64 GitHub Actions 1000000001"
    )
    assert RunnerLabel().describe() == "a runner that stated nothing about itself"
    assert RunnerLabel.from_record({"os": "Linux", "arch": 64}) == RunnerLabel(os="Linux")
    assert RunnerLabel.from_record("Linux") == RunnerLabel()


# --- the report -------------------------------------------------------------------------------


def _request(
    *,
    code: str = "reviewed",
    prompt: float | None = None,
    output: float | None = None,
    tokens: int | None = 20000,
    deadline: object = None,
    finished: bool = True,
    counted: int | None = 16000,
    load: float | None = None,
    elapsed: float = 600.0,
) -> dict[str, Any]:
    """One request entry as a review records it, with only what a test needs."""
    figures: dict[str, Any] | None = None
    if prompt is not None or output is not None or load is not None:
        figures = {"prompt_tokens_per_second": prompt, "output_tokens_per_second": output}
        if counted is not None:
            figures["prompt_eval_count"] = counted
        if load is not None:
            figures["load_seconds"] = load
    return {
        "kind": "request",
        "finished": finished,
        "code": code if finished else None,
        "prompt_tokens_estimated": tokens,
        "deadline_seconds": 9000,
        "elapsed_seconds": elapsed,
        "deadline": (
            {"prompt_tokens_per_second": 40, "output_tokens_per_second": 2, "floor_seconds": 600}
            if deadline is None
            else deadline
        ),
        "ollama": figures,
    }


def _probe(code: str | None = None, load: float | None = 90.0) -> dict[str, Any]:
    return {
        "kind": "slot_probe",
        "finished": True,
        "code": code,
        "ollama": None if load is None else {"load_seconds": load},
    }


def _record(requests: object, *, model: str = "gpt-oss:20b", runner=None) -> dict[str, Any]:
    record: dict[str, Any] = {
        "schema": "vibey-gh.local-review/1",
        "code": "reviewed",
        "reason": "reviewed in one request",
        "scope": "full",
        "role": "sovereign",
        "head_sha": "abc",
        "parts": 1,
        "attempts": 1,
        "model": model,
        "runner": HOSTED_JSON if runner is None else runner,
    }
    if requests is not None:
        record["requests"] = requests
    return record


HOSTED_JSON = RunnerLabel.from_environ(HOSTED).as_json()


def _write(path: pathlib.Path, value: object) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
    return path


READ_AT = 1_790_000_000.0  # 2026-09-21T14:13:20Z


@pytest.fixture
def artifacts(tmp_path) -> pathlib.Path:
    """Downloaded review artifacts: two hosted runs with timings, a self-hosted one, an old
    record with none, and the files beside them that are not outcome records."""
    root = tmp_path / "artifacts"
    hosted = [
        _request(prompt=rate, output=out, load=load)
        for rate, out, load in [(52.0, 3.4, None), (41.0, 2.9, None), (60.5, 3.9, None)]
    ]
    _write(
        root / "run-1" / "outcome.json",
        _record([_probe(), *hosted, _request(code="model_timeout", tokens=41152, elapsed=9221.0)]),
    )
    _write(
        root / "run-2" / "deep" / "outcome.json",
        _record(
            [
                _probe("model_busy", load=None),
                _request(prompt=48.0, output=3.1),
                _request(prompt=44.0, output=3.0, counted=None),
                _request(code="model_timeout", tokens=30000, elapsed=8000.0),
                _request(code="answer_incomplete", prompt=50.0, output=None),
                _request(finished=False, tokens=50000),
                _request(deadline="not a basis", tokens=None, code="model_timeout"),
                "not an entry",
            ],
            runner=HOSTED_JSON | {"name": "GitHub Actions 1000000002"},
        ),
    )
    _write(
        root / "self" / "outcome.json",
        _record(
            [_request(prompt=210.0, output=22.0, deadline={"floor_seconds": 600})],
            runner={"environment": "self-hosted", "os": "macOS", "arch": "ARM64", "name": "m5"},
        ),
    )
    _write(root / "old" / "outcome.json", _record(None, model="", runner={}))
    _write(root / "run-1" / "verdict.json", {"pass": True, "summary": "fine", "findings": []})
    _write(root / "run-1" / "broken.json", "{not json")
    _write(root / "run-1" / "list.json", [1, 2, 3])
    _write(root / "run-1" / "notes.txt", "not even JSON, and not named so")
    return root


def test_the_report_groups_by_model_and_runner_and_reads_ollamas_rates(artifacts):
    report = ReviewTimings(clock=lambda: READ_AT).report([artifacts])
    said = report.as_json()

    assert said["read_at"] == "2026-09-21T14:13:20Z"
    assert [pathlib.Path(path).parent.name for path in said["read"]] == [
        "old",
        "run-1",
        "deep",
        "self",
    ]
    skipped = {pathlib.Path(s["path"]).name: s["why"] for s in said["skipped"]}
    assert skipped.pop("broken.json").startswith("unreadable: ")
    assert skipped == {
        "list.json": (
            "not a local-review outcome record (schema None, expected 'vibey-gh.local-review/1')"
        ),
        "verdict.json": (
            "not a local-review outcome record (schema None, expected 'vibey-gh.local-review/1')"
        ),
    }

    old, hosted, own = said["groups"]
    assert (old["model"], old["runner"], old["records_without_timings"]) == (
        "(model not recorded)",
        {},
        1,
    )
    assert old["suggestion"]["enough"] is False and old["prompt_tokens_per_second"] is None

    assert hosted["model"] == "gpt-oss:20b"
    assert hosted["runner"] == {"environment": "github-hosted", "os": "Linux", "arch": "ARM64"}
    assert hosted["runner_names"] == ["GitHub Actions 1000000001", "GitHub Actions 1000000002"]
    assert (hosted["records"], hosted["requests"], hosted["unfinished"]) == (2, 10, 1)
    assert hosted["request_codes"] == {"model_timeout": 3, "reviewed": 5, "answer_incomplete": 1}
    assert (hosted["slot_probes"], hosted["slot_probe_codes"]) == (
        2,
        {"answered": 1, "model_busy": 1},
    )
    # Five answered requests with both rates; the incomplete one had no output rate.
    assert hosted["answered"] == 5
    assert hosted["prompt_tokens_per_second"] == {"n": 5, "median": 48.0, "p10": 41.0, "p90": 60.5}
    assert hosted["output_tokens_per_second"] == {"n": 5, "median": 3.1, "p10": 2.9, "p90": 3.9}
    assert hosted["prompt_tokens_counted_per_estimated"] == {
        "n": 4,
        "median": 0.8,
        "p10": 0.8,
        "p90": 0.8,
    }
    assert hosted["load_seconds"] == {"n": 1, "median": 90.0, "p10": 90.0, "p90": 90.0}
    assert hosted["timed_out"] == [
        {"prompt_tokens_estimated": None, "deadline_seconds": 9000, "elapsed_seconds": 600.0},
        {"prompt_tokens_estimated": 30000, "deadline_seconds": 9000, "elapsed_seconds": 8000.0},
        {"prompt_tokens_estimated": 41152, "deadline_seconds": 9000, "elapsed_seconds": 9221.0},
    ]
    assert hosted["declared"] == [
        {"prompt_tokens_per_second": 40, "output_tokens_per_second": 2, "floor_seconds": 600}
    ]
    assert hosted["suggestion"] == {
        "enough": True,
        "observations": 5,
        "minimum": MINIMUM_OBSERVATIONS,
        "prompt_tokens_per_second": 41,
        "output_tokens_per_second": 2,
    }

    assert own["runner"] == {"environment": "self-hosted", "os": "macOS", "arch": "ARM64"}
    assert own["runner_names"] == ["m5"]
    assert own["declared"] == [
        {"prompt_tokens_per_second": None, "output_tokens_per_second": None, "floor_seconds": 600}
    ]
    assert own["suggestion"]["enough"] is False and own["suggestion"]["observations"] == 1


def test_the_report_in_words_names_what_it_read_suggests_and_skipped(artifacts):
    text = ReviewTimings(clock=lambda: READ_AT, minimum=1).report([artifacts]).render()

    assert text.startswith(
        "Sovereign review request timings: 4 local-review outcome record(s) from 1 path(s),"
        " 3 file(s) skipped; read 2026-09-21T14:13:20Z\n"
    )
    assert "percentiles are nearest-rank" in text
    assert "gpt-oss:20b on github-hosted Linux ARM64 (2 runner name(s))" in text
    assert "  prompt tokens/s: median 48.0, p10 41.0, p90 60.5 (from 5)" in text
    assert "  slot probe outcomes: answered 1, model_busy 1" in text
    assert "    ~41152 estimated prompt tokens (deadline 9000s, ran 9221.0s)" in text
    assert (
        "  deadlines were scaled at --prompt-tokens-per-second 40 --output-tokens-per-second 2,"
        " never under 600s" in text
    )
    assert (
        "  suggested: --prompt-tokens-per-second 41 --output-tokens-per-second 2 (a suggestion"
        " from 5 answered request(s): the 10th percentile of each observed rate, rounded down)"
        in text
    )
    # The self-hosted run: one observation, enough for a minimum of 1; a fixed deadline.
    assert "  deadlines were the fixed timeout of 600s" in text
    assert "--prompt-tokens-per-second 210 --output-tokens-per-second 22" in text
    # The old record: nothing observed, said as such rather than as zeroes.
    assert "(model not recorded) on a runner that stated nothing about itself" in text
    assert "  prompt tokens/s: none observed" in text
    assert "  timed out: none" in text
    assert "Skipped, never counted:" in text and "verdict.json: not a local-review" in text


def test_below_the_minimum_there_is_no_suggestion_only_the_count(tmp_path):
    _write(tmp_path / "o.json", _record([_request(prompt=50.0, output=3.0)] * 4))

    report = ReviewTimings(clock=lambda: READ_AT).report([tmp_path / "o.json"])

    ((group,),) = [report.as_json()["groups"]]
    assert group["suggestion"] == {
        "enough": False,
        "observations": 4,
        "minimum": 5,
        "prompt_tokens_per_second": None,
        "output_tokens_per_second": None,
    }
    assert (
        "  suggested: not enough data -- 4 answered request(s), at least 5 needed"
        in report.render()
    )


def test_a_suggestion_is_never_under_one_token_a_second(tmp_path):
    _write(tmp_path / "o.json", _record([_request(prompt=0.4, output=0.2)]))

    report = ReviewTimings(minimum=1).report([tmp_path])

    suggestion = report.as_json()["groups"][0]["suggestion"]
    assert (suggestion["prompt_tokens_per_second"], suggestion["output_tokens_per_second"]) == (
        1,
        1,
    )


def test_each_runner_name_can_be_kept_apart(artifacts):
    report = ReviewTimings(by_name=True).report([artifacts / "run-1", artifacts / "run-2"])

    groups = report.as_json()["groups"]
    assert [group["runner"].get("name") for group in groups] == [
        "GitHub Actions 1000000001",
        "GitHub Actions 1000000002",
    ]
    assert all(group["runner_names"] == [] for group in groups)
    assert "github-hosted Linux ARM64 GitHub Actions 1000000001\n" in report.render()


def test_a_path_that_does_not_exist_is_named_never_guessed_at(tmp_path):
    report = ReviewTimings(clock=lambda: READ_AT).report([tmp_path / "nowhere"])

    assert report.as_json()["skipped"] == [
        {"path": str(tmp_path / "nowhere"), "why": "no such file or directory"}
    ]
    assert report.render().endswith(
        "No local-review outcome records were found, so nothing is reported.\n\n"
        "Skipped, never counted:\n"
        f"  {tmp_path / 'nowhere'}: no such file or directory\n"
    )


def test_percentiles_are_nearest_rank_and_always_a_value_observed():
    assert TimingsGroup.percentile([5.0, 1.0, 3.0, 2.0, 4.0], 0.10) == 1.0
    assert TimingsGroup.percentile([5.0, 1.0, 3.0, 2.0, 4.0], 0.90) == 5.0
    assert TimingsGroup.percentile([float(n) for n in range(1, 21)], 0.10) == 2.0
    assert TimingsGroup.percentile([7.0], 0.10) == 7.0
    assert TimingsGroup.spread([]) is None


@pytest.mark.parametrize("minimum", [0, -1, 2.5, True])
def test_a_minimum_under_one_is_refused(minimum):
    with pytest.raises(ValueError, match="at least 1"):
        ReviewTimings(minimum=minimum)


def test_the_report_reads_the_wall_clock_without_one(monkeypatch, tmp_path):
    monkeypatch.setattr("vibey_gh.review_timings.time.time", lambda: READ_AT)

    assert ReviewTimings().report([tmp_path]).read_at == "2026-09-21T14:13:20Z"


def test_every_class_stands_behind_its_interface():
    group = TimingsGroup("m", RunnerLabel(), 0, 0, ())
    assert isinstance(RequestLog(), RequestLogInterface)
    assert isinstance(RunnerLabel(), RunnerLabelInterface)
    assert isinstance(group, TimingsGroupInterface)
    assert isinstance(TimingsReport("", (), (), (), (group,)), TimingsReportInterface)
    assert isinstance(ReviewTimings(), ReviewTimingsInterface)


# --- the command ------------------------------------------------------------------------------


def test_the_command_prints_the_report_and_its_json(artifacts, capsys):
    assert cli.main(["review-timings", str(artifacts / "run-1")]) == 0
    assert "gpt-oss:20b on github-hosted Linux ARM64" in capsys.readouterr().out

    assert cli.main(["review-timings", str(artifacts), "--json", "--minimum", "1"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert len(said["groups"]) == 3
    assert all(group["suggestion"]["minimum"] == 1 for group in said["groups"])

    assert cli.main(["review-timings", str(artifacts), "--by-runner-name", "--json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["groups"]) == 4


def test_the_command_fails_when_it_read_no_record_and_refuses_a_bad_minimum(tmp_path, capsys):
    _write(tmp_path / "verdict.json", {"pass": True})

    assert cli.main(["review-timings", str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert "no local-review outcome record was read" in captured.err
    assert "verdict.json: not a local-review outcome record" in captured.out

    assert cli.main(["review-timings", str(tmp_path), "--minimum", "0"]) == 2
    assert "at least 1" in capsys.readouterr().err


# --- recorded, then read back ---------------------------------------------------------------


def test_what_a_review_records_is_what_the_report_reads(monkeypatch, clock, tmp_path, capsys):
    """End to end: five reviews on a fake hosted runner, their records in an artifact tree,
    and the report's rates are the model's own counters."""
    _model(monkeypatch, clock)
    for run in range(5):
        record = tmp_path / "artifacts" / f"run-{run}" / "outcome.json"
        record.parent.mkdir(parents=True)
        argv = ["--diff", str(_diff(tmp_path)), *FLAGS, "--slot-wait-seconds", "0"]
        argv += ["--outcome", str(record)]
        assert local_review.review(argv, environ=HOSTED, clock=clock) == 0
    capsys.readouterr()

    ((group,),) = [ReviewTimings().report([tmp_path / "artifacts"]).as_json()["groups"]]

    assert group["answered"] == 5 and group["request_codes"] == {"reviewed": 5}
    assert group["output_tokens_per_second"]["median"] == round(412 / 60, 3)
    assert group["suggestion"]["output_tokens_per_second"] == math.floor(412 / 60)
    assert group["declared"] == [
        {"prompt_tokens_per_second": 40, "output_tokens_per_second": 2, "floor_seconds": 30}
    ]
