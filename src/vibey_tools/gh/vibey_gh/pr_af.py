# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ask Agent-Field `pr-af` for a review, and read the verdict its own gate produced.

pr-af runs as an AgentField node behind a control plane. A review is one async execution:
POST the pull request's URL, then poll the execution's details until it settles. The
result is a `ReviewResult` whose `summary.blocking_count` is the only blocking signal --
pr-af's merge gate decides whether a finding must be fixed before merge, and severity is
only its badness label. A budget that ran out is not a verdict: the review stopped early,
so the gate falls back rather than treating a partial pass as a pass.

The workflow needs this as one value (`passed`), but it also needs the reason when there
is none. `PrAfVerdict` carries both; `PrAfCommand` writes them to `$GITHUB_OUTPUT` and a
human-readable table to `$GITHUB_STEP_SUMMARY`. Every failure to produce a verdict exits
0 with `passed=` empty: a reviewer that could not run is a reported gap, not a red job
that hides the reason in a traceback. Only a missing pull request URL refuses to run.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, TextIO, cast

from vibey_gh.config import GhConfig, load_config
from vibey_gh.interfaces.pr_af_interface import PrAfClientInterface, PrAfVerdictInterface

__all__ = ["PrAfClient", "PrAfCommand", "PrAfVerdict"]

# `urllib.request.urlopen`'s shape, minus the parts this client never uses. Tests inject a
# callable with the same two arguments; nothing else about the transport is assumed.
Transport = Callable[[urllib.request.Request, float], Any]

# The execution statuses AgentField reports. `succeeded` is the one its own CI runner waits
# for; the rest are terminal failures this module reports as "no verdict" with the reason.
_SUCCEEDED = frozenset({"succeeded", "success", "completed"})
_FAILED = frozenset({"failed", "cancelled", "canceled", "error", "timed_out", "timeout"})
# A node that is still registering with a fresh control plane answers 404/503 for a
# moment. Retry those while the dispatch window is open, rather than calling it a failure.
_RETRYABLE = frozenset({404, 409, 425, 429, 500, 502, 503, 504})


def _urlopen(request: urllib.request.Request, timeout: float) -> Any:
    return urllib.request.urlopen(request, timeout=timeout)


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _status(value: object) -> str:
    """The execution's status, from the top level or one `execution` wrapper."""
    if not isinstance(value, Mapping):
        return ""
    status = value.get("status")
    if isinstance(status, str):
        return status.lower()
    nested = value.get("execution")
    return _status(nested) if isinstance(nested, Mapping) else ""


def _find_result(value: object) -> dict[str, Any] | None:
    """The first `ReviewResult` anywhere in an execution-details document.

    The endpoint has carried the result at the top level, under `result` and under
    `output`, and as a JSON string inside one of those. Searching by shape, not by a path,
    keeps a control-plane upgrade from silently turning every review into "no verdict".
    """
    if isinstance(value, str):
        text = value.strip()
        if not text or text[0] not in "[{":
            return None
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        return _find_result(parsed)
    if isinstance(value, Mapping):
        if "review" in value and "summary" in value:
            return dict(value)
        for child in value.values():
            found = _find_result(child)
            if found is not None:
                return found
        return None
    if isinstance(value, list | tuple):
        for child in value:
            found = _find_result(child)
            if found is not None:
                return found
    return None


@dataclass(frozen=True)
class PrAfVerdict:
    """What one pr-af execution decided, or why it decided nothing."""

    passed: bool | None
    findings: int = 0
    event: str = ""
    reason: str = ""
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    budget_exhausted: bool = False

    @classmethod
    def from_result(cls, result: Mapping[str, Any]) -> PrAfVerdict:
        summary = result.get("summary")
        summary = summary if isinstance(summary, Mapping) else {}
        review = result.get("review")
        review = review if isinstance(review, Mapping) else {}
        event = str(review.get("event") or "")
        cost = _as_float(summary.get("cost_usd"))
        duration = _as_float(summary.get("duration_seconds"))
        exhausted = bool(summary.get("budget_exhausted", False))
        if "blocking_count" not in summary:
            return cls(
                None,
                0,
                event,
                "pr-af returned a summary without its blocking count",
                cost,
                duration,
                exhausted,
            )
        blocking = _as_int(summary.get("blocking_count"))
        if exhausted:
            return cls(
                None,
                blocking,
                event,
                "pr-af stopped at its budget cap before it could finish",
                cost,
                duration,
                True,
            )
        if blocking > 0 or event == "REQUEST_CHANGES":
            return cls(
                False,
                blocking,
                event,
                f"pr-af requested changes with {blocking} blocking finding(s)",
                cost,
                duration,
            )
        if event in ("APPROVE", "COMMENT"):
            return cls(
                True,
                0,
                event,
                "pr-af found nothing it judged blocking",
                cost,
                duration,
            )
        return cls(
            None,
            blocking,
            event,
            "pr-af returned a review without a GitHub event",
            cost,
            duration,
        )


class PrAfClient:
    """One control plane, one execution at a time, with every wait bounded."""

    def __init__(
        self,
        server: str,
        *,
        transport: Transport = _urlopen,
        poll_seconds: float = 30,
        request_timeout: float = 60,
        startup_seconds: float = 300,
        timeout_seconds: float = 7200,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.server = server.rstrip("/")
        self._transport = transport
        self._poll_seconds = poll_seconds
        self._request_timeout = request_timeout
        self._startup_seconds = startup_seconds
        self._timeout_seconds = timeout_seconds
        self._sleep = sleep
        self._clock = clock

    def review(
        self,
        pr_url: str,
        *,
        depth: str,
        dry_run: bool,
        max_cost_usd: float,
        max_duration_seconds: int,
    ) -> PrAfVerdict:
        started = self._clock()
        execution_id = self._dispatch(
            {
                "input": {
                    "pr_url": pr_url,
                    "depth": depth,
                    "dry_run": dry_run,
                    "max_cost_usd": max_cost_usd,
                    "max_duration_seconds": max_duration_seconds,
                }
            },
            started,
        )
        if execution_id is None:
            return PrAfVerdict(
                None, reason="pr-af did not accept the review request; see the job log"
            )
        return self._wait(execution_id, started)

    def _dispatch(self, payload: Mapping[str, Any], started: float) -> str | None:
        body = json.dumps(payload).encode("utf-8")
        deadline = min(started + self._startup_seconds, started + self._timeout_seconds)
        last = "no answer"
        while True:
            request = urllib.request.Request(
                f"{self.server}/api/v1/execute/async/pr-af.review",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            try:
                document = self._json(request)
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code} from the control plane"
                if exc.code not in _RETRYABLE or self._clock() >= deadline:
                    print(f"pr-af: {last}", file=sys.stderr)
                    return None
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last = f"the control plane could not be reached: {exc}"
                if self._clock() >= deadline:
                    print(f"pr-af: {last}", file=sys.stderr)
                    return None
            else:
                execution_id = (
                    document.get("execution_id") if isinstance(document, Mapping) else None
                )
                if isinstance(execution_id, str) and execution_id:
                    print(f"pr-af: dispatched execution {execution_id}", file=sys.stderr)
                    return execution_id
                last = "the control plane returned no execution_id"
                if self._clock() >= deadline:
                    print(f"pr-af: {last}", file=sys.stderr)
                    return None
            remaining = deadline - self._clock()
            self._sleep(min(self._poll_seconds, max(0.0, remaining)))

    def _wait(self, execution_id: str, started: float) -> PrAfVerdict:
        deadline = started + self._timeout_seconds
        last = "the execution did not settle"
        while True:
            remaining = deadline - self._clock()
            if remaining <= 0:
                return PrAfVerdict(None, reason=f"pr-af produced no verdict: {last}")
            self._sleep(min(self._poll_seconds, remaining))
            request = urllib.request.Request(
                f"{self.server}/api/ui/v1/executions/{execution_id}/details"
            )
            try:
                document = self._json(request)
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
                last = f"the execution details could not be read: {exc}"
                continue
            status = _status(document)
            if status in _SUCCEEDED:
                result = _find_result(document)
                if result is None:
                    return PrAfVerdict(
                        None,
                        reason=(
                            "pr-af finished, but its execution details carried no review result"
                        ),
                    )
                return PrAfVerdict.from_result(result)
            if status in _FAILED:
                # `_status` only returns a status from a mapping, so the document is one.
                error = cast(Mapping[str, Any], document).get("error") or cast(
                    Mapping[str, Any], document
                ).get("error_message")
                detail = f": {error}" if isinstance(error, str) and error else ""
                return PrAfVerdict(None, reason=f"pr-af ended '{status}' without a verdict{detail}")
            last = f"the execution was still '{status or 'unknown'}'"

    def _json(self, request: urllib.request.Request) -> Any:
        with self._transport(request, self._request_timeout) as response:
            return json.loads(response.read().decode("utf-8"))


class PrAfCommand:
    """The workflow's entry point: one review, its outputs, and a summary a person reads."""

    def __init__(
        self,
        cfg: GhConfig | None = None,
        *,
        client: PrAfClientInterface | None = None,
        env: Mapping[str, str] | None = None,
        out: TextIO = sys.stdout,
    ) -> None:
        self._cfg = cfg or load_config()
        self._client = client
        self._env = env if env is not None else os.environ
        self._out = out

    def run(self) -> int:
        cfg = self._cfg.pr_automation.pr_af
        venue = self._env.get("PR_AF_VENUE", "hosted")
        if not cfg.enabled:
            return self._finish(PrAfVerdict(None, reason="pr-af is not declared"), venue)
        pr_url = self._pr_url()
        if not pr_url:
            print(
                "pr-af: PR_URL, or PR plus GITHUB_REPOSITORY, is required",
                file=sys.stderr,
            )
            self._write_outputs(
                {
                    "passed": "",
                    "findings": "",
                    "event": "",
                    "reason": "no pull request URL was supplied",
                    "model": cfg.model,
                    "venue": venue,
                }
            )
            return 1
        client = self._client or PrAfClient(
            self._env.get("PR_AF_SERVER", "http://127.0.0.1:8080"),
            poll_seconds=_as_float(self._env.get("PR_AF_POLL_SECONDS", "30"), 30),
            timeout_seconds=_as_float(
                self._env.get("PR_AF_TIMEOUT_SECONDS", ""),
                max(60.0, float(cfg.timeout_minutes * 60 - 900)),
            ),
        )
        verdict = client.review(
            pr_url,
            depth=self._env.get("PR_AF_DEPTH", cfg.depth),
            dry_run=_truthy(self._env.get("PR_AF_DRY_RUN", "")),
            max_cost_usd=_as_float(self._env.get("PR_AF_MAX_COST_USD", ""), cfg.max_cost_usd),
            max_duration_seconds=_as_int(
                self._env.get("PR_AF_MAX_DURATION_SECONDS", ""), cfg.max_duration_seconds
            ),
        )
        return self._finish(verdict, venue)

    def _pr_url(self) -> str:
        explicit = self._env.get("PR_URL", "").strip()
        if explicit:
            return explicit
        number = self._env.get("PR", "").strip()
        repository = self._env.get("GITHUB_REPOSITORY", "").strip()
        server = self._env.get("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
        if number.isdigit() and repository:
            return f"{server}/{repository}/pull/{number}"
        return ""

    def _finish(self, verdict: PrAfVerdictInterface, venue: str) -> int:
        cfg = self._cfg.pr_automation.pr_af
        self._write_outputs(
            {
                "passed": "" if verdict.passed is None else ("true" if verdict.passed else "false"),
                "findings": str(verdict.findings),
                "event": verdict.event,
                "reason": verdict.reason,
                "model": cfg.model,
                "venue": venue,
                "cost_usd": f"{verdict.cost_usd:.4f}",
                "duration_seconds": f"{verdict.duration_seconds:.1f}",
            }
        )
        self._write_summary(verdict, venue)
        print(
            json.dumps(
                {
                    "passed": verdict.passed,
                    "findings": verdict.findings,
                    "event": verdict.event,
                    "reason": verdict.reason,
                    "budget_exhausted": verdict.budget_exhausted,
                }
            ),
            file=self._out,
        )
        return 0

    def _write_outputs(self, values: Mapping[str, str]) -> None:
        target = self._env.get("GITHUB_OUTPUT")
        if target:
            with open(target, "a", encoding="utf-8") as handle:
                handle.writelines(f"{name}={value}\n" for name, value in values.items())

    def _write_summary(self, verdict: PrAfVerdictInterface, venue: str) -> None:
        target = self._env.get("GITHUB_STEP_SUMMARY")
        if not target:
            return
        if verdict.passed is None:
            outcome = "no verdict"
        elif verdict.passed:
            outcome = "passed"
        else:
            outcome = f"blocked ({verdict.findings} blocking finding(s))"
        lines = [
            "### pr-af review",
            "",
            f"- Venue: `{venue}`",
            f"- Model: `{self._cfg.pr_automation.pr_af.model}`",
            f"- Outcome: **{outcome}**",
            f"- Review event: `{verdict.event or 'none'}`",
            f"- Reason: {verdict.reason}",
        ]
        if verdict.cost_usd:
            lines.append(f"- Cost: ${verdict.cost_usd:.2f}")
        if verdict.duration_seconds:
            lines.append(f"- Duration: {verdict.duration_seconds / 60:.1f} min")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def _truthy(value: object) -> bool:
    return isinstance(value, str) and value.strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    raise SystemExit(PrAfCommand().run())
