# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ask the forge again when it answered "not now", and never when it answered "no".

The delivery estimate's hourly issue triage failed twice in a day on one call out of
dozens: `gh issue edit` got `504 Gateway Timeout` (run 36985000010), and on another run
GraphQL's "Something went wrong while executing your query" (run 36939497192). The
estimate itself had landed; the job went red for a blip the next attempt would not hit.

What is transient is `[forge_retry]`'s to say (`ForgeRetryConfig`), not this module's: the
5xx statuses and messages it lists, and a secondary rate limit that says when to come back
(`Retry-After`). `gh` reports a GraphQL HTTP failure as `non-200 OK status code: 504 ...`
and a REST one as `HTTP 502`; `gh api --include` puts the response headers, `Retry-After`
among them, on stdout. Both streams are read.

Not `vibey_bootstrap`'s retry, which ADR-0017 would otherwise prefer: vibey-gh declares no
dependencies, `vibey_bootstrap` depends on vibey-gh, and the workflows that run this install
vibey-gh alone. Not `local_review.TransportRetry` either: that one retries exceptions from a
model call and turns the last into a `ReviewRefused`, while a `gh` failure is an exit status
and text, and must come back to its caller as exactly the answer it would have had.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from vibey_gh.config import ForgeRetryConfig
from vibey_gh.interfaces.gh_retry_interface import GhRetryInterface

__all__ = ["GhRetry"]

# `non-200 OK status code: 504 Gateway Timeout` (GraphQL), `HTTP 502` (REST), and the
# `HTTP/2.0 503` status line `--include` prints.
_STATUS = re.compile(r"(?:\bHTTP(?:/[0-9.]+)?|\bstatus code:?)\s+(?P<status>\d{3})\b")
_RETRY_AFTER = re.compile(r"^\s*retry-after:\s*(?P<seconds>\d+)\s*$", re.IGNORECASE | re.MULTILINE)


@dataclass(frozen=True)
class GhRetry(GhRetryInterface):
    """Implements `GhRetryInterface`. `sleep` and `report` are the seams; `None` means
    `time.sleep` and a line on stderr, looked up when called."""

    policy: ForgeRetryConfig = field(default_factory=ForgeRetryConfig)
    sleep: Callable[[float], None] | None = None
    report: Callable[[str], None] | None = None

    def wait(
        self, result: subprocess.CompletedProcess[str], attempt: int
    ) -> tuple[float, str] | None:
        if result.returncode == 0:
            return None
        text = f"{result.stdout or ''}\n{result.stderr or ''}"
        folded = text.casefold()
        after = _RETRY_AFTER.search(text)
        status = _STATUS.search(text)
        if any(message.casefold() in folded for message in self.policy.rate_limit_messages):
            if after is None:
                return None  # a rate limit that does not say when is not waited out blind
            reason = "secondary rate limit"
        elif status is not None and int(status["status"]) in self.policy.transient_statuses:
            reason = f"HTTP {status['status']}"
        else:
            listed = [m for m in self.policy.transient_messages if m.casefold() in folded]
            if not listed:
                return None
            reason = listed[0]
        if after is not None:
            seconds = float(after["seconds"])
            if seconds > self.policy.max_retry_after_seconds:
                return None
            return seconds, f"{reason}, Retry-After {seconds:g}s"
        backoff = self.policy.backoff_seconds * 2 ** (attempt - 1)
        return min(backoff, self.policy.max_backoff_seconds), reason

    def run(
        self, call: Callable[[], subprocess.CompletedProcess[str]], label: str
    ) -> subprocess.CompletedProcess[str]:
        attempt = 0
        while True:
            attempt += 1
            result = call()
            waited = self.wait(result, attempt)
            if waited is None:
                return result
            seconds, reason = waited
            if attempt > self.policy.retries:
                if attempt == 1:
                    return result  # no retries configured: the answer as it always was
                note = f"(gave up after {attempt} attempts; each failed transiently: {reason})"
                stderr = f"{(result.stderr or '').rstrip()}\n{note}"
                return subprocess.CompletedProcess(
                    result.args, result.returncode, result.stdout, stderr
                )
            (self.report or self._announce)(
                f"vibey-gh: `{label}` failed transiently ({reason}); retrying in {seconds:g}s"
                f" (attempt {attempt + 1} of {self.policy.retries + 1})"
            )
            (self.sleep or time.sleep)(seconds)

    @staticmethod
    def _announce(line: str) -> None:
        print(line, file=sys.stderr)
