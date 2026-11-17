# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Audit `.github/` with zizmor and hold its finding count at a recorded baseline.

    python scripts/workflow_lint.py

Capability gap (the reason this exists rather than reusing the family): vibey ships no workflow
security auditor. `vibey-gh pin-actions` rewrites refs, and review reads YAML as text, but neither
understands how the Actions expression grammar, trigger model and token permissions combine.
zizmor's offline audits catch template injection, excessive permissions, unpinned action refs and
the like that a reader misses and that are expensive to find in CI or after an incident (CLAUDE.md,
"Dogfood the family": a new implementation needs a written reason; this is it).

`--offline` gives up zizmor's online audits (impostor-commit, ref-confusion, known-vulnerable
actions, stale action refs), and impostor-commit is exactly the risk SHA pinning introduces. That is
accepted because the count has to be reproducible without a token or network; the 13 pinned SHAs are
resolved through the forge's commits endpoint by `vibey-gh pin-actions` and were each checked
against the forge by hand in review.

The count is a ratchet, in both directions. Above the baseline fails naming the tool, so new
debt cannot arrive; below it fails telling you to lower the baseline, so a fix is locked in and
the file cannot keep claiming debt that is gone. A tool that crashes, or prints output that is
not findings, fails: a crash is never a clean pass (sub-doctrine 10.f). zizmor is read as JSON
and counted by finding, not by line; it runs `--offline` so the count needs no network or token and
is the same on every machine. Baselines live in `tests/meta/workflow_lint_baseline.toml`, keyed by
tool name with the version and the date measured beside each.

Another tool is another `ToolSpec` in `TOOLS` and another table in the baseline file.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

try:
    from scripts.interfaces.workflow_lint_interface import (
        ToolSpecInterface,
        WorkflowLintInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.workflow_lint_interface import (  # type: ignore[import-not-found,no-redef]
        ToolSpecInterface,
        WorkflowLintInterface,
    )

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "tests/meta/workflow_lint_baseline.toml"
Runner = Callable[[Sequence[str]], tuple[int, str, str]]


@dataclass(frozen=True)
class ToolSpec:
    """What a checker is: its name, its command, and how its output becomes a count."""

    name: str
    argv: tuple[str, ...]
    count: Callable[[str], int]


class ZizmorFindings:
    """Counts zizmor's JSON findings, leaving out any a `zizmor: ignore` comment suppressed."""

    @staticmethod
    def count(text: str) -> int:
        try:
            rows = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"not JSON: {exc}") from exc
        if not isinstance(rows, list):
            raise ValueError("JSON is not a list of findings")
        return sum(1 for row in rows if isinstance(row, dict) and not row.get("ignored"))


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="zizmor",
        argv=(
            "zizmor",
            "--offline",
            "--no-exit-codes",
            "--format",
            "json",
            ".github/workflows",
            ".github/actions",
        ),
        count=ZizmorFindings.count,
    ),
)


class WorkflowLint(WorkflowLintInterface):
    """Runs each tool over the repository and compares its count with the recorded baseline."""

    def __init__(
        self,
        baseline: Path = BASELINE,
        tools: Sequence[ToolSpecInterface] = TOOLS,
        runner: Runner | None = None,
        out: Callable[[str], None] = print,
    ) -> None:
        self.baseline = baseline
        self.tools = tools
        self.runner = runner or self._subprocess
        self.out = out

    @staticmethod
    def _subprocess(argv: Sequence[str]) -> tuple[int, str, str]:
        try:
            done = subprocess.run(  # noqa: S603 - argv is a fixed tuple above, never a shell
                list(argv), capture_output=True, text=True, cwd=REPO, check=False
            )
        except FileNotFoundError as exc:
            return 127, "", str(exc)
        return done.returncode, done.stdout, done.stderr

    def run(self) -> int:
        table = tomllib.loads(self.baseline.read_text(encoding="utf-8"))
        failed = 0
        for tool in self.tools:
            failed += self._check(tool, table.get(tool.name))
        return 1 if failed else 0

    def _check(self, tool: ToolSpecInterface, entry: dict[str, object] | None) -> int:
        recorded = entry.get("count") if entry else None
        if not isinstance(recorded, int):
            self.out(f"{tool.name}: no integer `count` in {self.baseline.name}; record one")
            return 1
        code, stdout, stderr = self.runner(tool.argv)
        if code != 0:
            self.out(f"{tool.name}: exited {code}, not a clean run: {stderr.strip()[:300]}")
            return 1
        try:
            found = tool.count(stdout)
        except ValueError as exc:
            self.out(f"{tool.name}: output is not findings ({exc})")
            return 1
        if found > recorded:
            self.out(f"{tool.name}: {found} findings, baseline {recorded}: fix the new ones")
            return 1
        if found < recorded:
            self.out(
                f"{tool.name}: {found} findings, baseline {recorded}: "
                f"lower the baseline to {found} in {self.baseline.name}"
            )
            return 1
        self.out(f"{tool.name}: {found} findings, at the baseline")
        return 0


def main() -> int:
    return WorkflowLint().run()


if __name__ == "__main__":
    sys.exit(main())
