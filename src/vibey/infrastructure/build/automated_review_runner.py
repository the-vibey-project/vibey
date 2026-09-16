# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Infrastructure runner for automated security and code review checks."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from uuid import UUID

from vibey.application.build_verify_handler import GateRunner
from vibey.application.interfaces import (
    ProjectStore,
)
from vibey.application.review_demo_handler import AutomatedFinding
from vibey.domain.review import Ambiguity, Severity

# vibey's own machinery inside the project repo -- worktrees under .vibey/
# and the engines' state dirs. Reviewing them reviews dead attempt branches
# and run transcripts, not the product: caught live when a stale cycle's
# worktree raised a lint finding against code that no longer existed,
# looping REVIEW back into BUILD.
_MACHINERY_DIRS = (".vibey", ".claudeloop", ".codexloop", ".cursorloop", ".agyloop")

_DEFAULT_CODE_REVIEW: tuple[tuple[str, ...], ...] = (
    ("ruff", "check", ".")
    + tuple(part for name in _MACHINERY_DIRS for part in ("--exclude", name)),
)

# No security check runs unless the project configures one. That is the honest
# default and it was a deliberate call, not an omission.
#
# Any baked-in command names both a tool and a layout. The previous default,
# `bandit -q -r src`, walked this repository's absorbed runner and tool subtrees
# -- separate workspace members with gates of their own -- and exited non-zero
# on every cycle, which became a Severity.HIGH finding that looped REVIEW back
# into BUILD forever. Narrowing it to `src/vibey` fixed vibey and broke everyone
# else worse: `bandit -q -r <path that does not exist>` exits 0 (measured), so
# every project without that exact directory would report a passing automated
# security check having examined zero files, forever. A green gate is trusted; a
# red one gets investigated. A vacuous green is the worse failure.
#
# `()` claims nothing instead. A project that wants the check configures
# `review.security_commands` (ADR-0018); this repository's REVIEW-phase scan is
# a convenience, and `bandit -q -r src/vibey` remains enforced for real as gate 6
# of `ci.yml` on every pull request.
_DEFAULT_SECURITY: tuple[tuple[str, ...], ...] = ()


class SubprocessAutomatedReviewRunner:
    def __init__(
        self,
        *,
        projects: ProjectStore | object,
        gates: GateRunner,
        security_commands: Sequence[tuple[str, ...]] = _DEFAULT_SECURITY,
        code_review_commands: Sequence[tuple[str, ...]] = _DEFAULT_CODE_REVIEW,
    ) -> None:
        self._projects = projects
        self._gates = gates
        self._security_commands = tuple(security_commands)
        self._code_review_commands = tuple(code_review_commands)

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, object],
        *,
        projects: ProjectStore | object,
        gates: GateRunner,
    ) -> "SubprocessAutomatedReviewRunner":
        """Build a runner whose checks come from the project's stored config.

        Read the same way `max_cycle_dollars` and `skills_context` are: off the
        project record's `config` JSON, written by `vibey new` or the operator's
        VibeyProject spec. `vibey.toml` is never loaded at runtime, so it is not
        a route for this.
        """
        raw = config.get("review")
        if raw is None:
            return cls(projects=projects, gates=gates)
        if not isinstance(raw, Mapping):
            raise ValueError("review project config must be an object")
        return cls(
            projects=projects,
            gates=gates,
            security_commands=cls._commands(raw, "security_commands", _DEFAULT_SECURITY),
            code_review_commands=cls._commands(raw, "code_review_commands", _DEFAULT_CODE_REVIEW),
        )

    @staticmethod
    def _commands(
        raw: Mapping[str, object],
        key: str,
        default: tuple[tuple[str, ...], ...],
    ) -> tuple[tuple[str, ...], ...]:
        """Validate one configured command list, or fall back to the default.

        An explicitly empty list is honoured: a project that gates a check
        elsewhere says so by configuring `[]`, which is not the same as saying
        nothing and inheriting the default.
        """
        value = raw.get(key)
        if value is None:
            return default
        if not isinstance(value, list):
            raise ValueError(f"review.{key} must be a list of command arrays")
        commands: list[tuple[str, ...]] = []
        for entry in value:
            if not isinstance(entry, list) or not entry:
                raise ValueError(f"review.{key} entries must be non-empty command arrays")
            if not all(isinstance(part, str) and part for part in entry):
                raise ValueError(f"review.{key} arguments must be non-empty strings")
            commands.append(tuple(entry))
        return tuple(commands)

    async def _get_repo_path(self, project_id: UUID) -> Path:
        if hasattr(self._projects, "get"):
            proj = await self._projects.get(project_id)
            if proj is None:
                raise LookupError(f"unknown project {project_id}")
            return Path(proj.repo_path)
        raise LookupError(f"cannot resolve repo path for {project_id}")

    async def run_automated_reviews(
        self, project_id: UUID, cycle: int
    ) -> tuple[AutomatedFinding, ...]:
        repo_path = await self._get_repo_path(project_id)
        findings: list[AutomatedFinding] = []

        for cmd in self._security_commands:
            result = await self._gates.run(cmd, cwd=repo_path)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                findings.append(
                    AutomatedFinding(
                        category="security",
                        text=f"Security check failed ({' '.join(cmd)}): {detail}",
                        severity=Severity.HIGH,
                        ambiguity=Ambiguity.CLEAR,
                    )
                )

        for cmd in self._code_review_commands:
            result = await self._gates.run(cmd, cwd=repo_path)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                findings.append(
                    AutomatedFinding(
                        category="code_review",
                        text=f"Code review check failed ({' '.join(cmd)}): {detail}",
                        severity=Severity.MEDIUM,
                        ambiguity=Ambiguity.CLEAR,
                    )
                )

        return tuple(findings)
