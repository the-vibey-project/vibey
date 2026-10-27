# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a red CI job says about itself: the failed step, the first failing test, a command.

`branch-health` used to name the failed *check* and link the run, so learning that the cause
was one test meant opening the run and reading the log. This reads what the forge already
reports (the job's steps) and what the job log makes available (a pytest `FAILED` line), and
looks the reproduction command up in the repository's own `[branch_health] reproduce` map.
Anything that cannot be established is reported as unknown by the caller, never guessed.

A test id comes out of a log, so it is untrusted text (SD-01 §4): it is shell-quoted when it
is placed in a command, and nothing here executes it.
"""

from __future__ import annotations

import re
import shlex
from collections.abc import Mapping, Sequence
from typing import Any

from vibey_gh.interfaces.failure_evidence_interface import (
    FailingTest,
    FailureEvidenceInterface,
    Reproduction,
    StepFailure,
)

__all__ = ["RED", "FailureEvidence"]

RED = frozenset({"failure", "timed_out", "startup_failure"})
PLACEHOLDER = "{test}"


class FailureEvidence(FailureEvidenceInterface):
    """Implements `FailureEvidenceInterface`."""

    # GitHub prefixes every log line with a timestamp; the patterns are written without it.
    TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z ")

    def failed_steps(self, job: Mapping[str, Any]) -> tuple[StepFailure, ...]:
        steps = job.get("steps") or ()
        return tuple(
            StepFailure(str(step.get("name") or ""), int(step.get("number") or 0))
            for step in steps
            if step.get("conclusion") in RED
        )

    def first_failing_test(
        self, log: str, pattern: str, truncated: bool = False
    ) -> FailingTest | None:
        compiled = re.compile(pattern)
        for index, raw in enumerate(log.splitlines(), start=1):
            found = compiled.search(self.TIMESTAMP.sub("", raw))
            if found:
                test_id = found.group(1) if compiled.groups else found.group(0)
                return FailingTest(test_id, None if truncated else index)
        return None

    def first_error_line(self, log: str, truncated: bool = False) -> int | None:
        if truncated:
            return None
        for index, line in enumerate(log.splitlines(), start=1):
            if "##[error]" in line:
                return index
        return None

    def reproduction(
        self,
        check: str,
        step: str | None,
        test_id: str | None,
        mapping: Sequence[tuple[str, str]],
    ) -> Reproduction:
        table = dict(mapping)
        template = table.get(f"{check} :: {step}") if step else None
        if template is None:
            template = table.get(check)
        if template is None:
            return Reproduction(None, "no reproduction command is declared for this check")
        if PLACEHOLDER not in template:
            return Reproduction(template, "declared")
        if test_id is None:
            return Reproduction(None, "the declared command needs a test id the log did not give")
        return Reproduction(template.replace(PLACEHOLDER, shlex.quote(test_id)), "declared")
