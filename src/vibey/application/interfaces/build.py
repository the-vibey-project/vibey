# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase 2 collaborators: worktrees, provisioning, budget, gates, integration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.budget import BudgetLedger
from vibey.domain.plan import WorkItem
from vibey.domain.provision import ProvisionSpec
from vibey.domain.spec import DesignSpec


@dataclass(frozen=True, slots=True)
class MergeOutcome:
    ok: bool
    detail: str


@dataclass(frozen=True, slots=True)
class GateResult:
    """A verification gate's raw subprocess outcome.

    Distinct from `domain.handoff.GateResult`, which is the no-loss gate's
    verdict -- same word, unrelated concepts.
    """

    returncode: int
    stdout: str
    stderr: str


@runtime_checkable
class BudgetSource(Protocol):
    async def current(self, project_id: UUID, cycle: int) -> BudgetLedger: ...


@dataclass(frozen=True, slots=True)
class SkillsContextResult:
    """A context-packet attempt, with raw task text deliberately absent."""

    mode: str
    status: str
    markdown: str
    provenance: Mapping[str, object]

    @property
    def should_inject(self) -> bool:
        return self.mode == "inject" and self.status == "ok" and bool(self.markdown)


@runtime_checkable
class SkillsContextCompiler(Protocol):
    async def compile(self, *, job: object, worktree_path: Path) -> SkillsContextResult: ...


@runtime_checkable
class BuildProvisioner(Protocol):
    async def provision(self, worktree_path: Path, spec: ProvisionSpec) -> tuple[Path, ...]: ...


@runtime_checkable
class BuildWorktrees(Protocol):
    async def create(self, item_id: str, *, base_ref: str = "HEAD") -> Path: ...


@runtime_checkable
class BuildCheckpoint(Protocol):
    """Commits a worktree's work at an ULTRA checkpoint (ADR-0063)."""

    async def commit(self, worktree_path: Path, message: str) -> str | None:
        """Stages and commits everything; the new commit's id, or `None` when there was
        nothing to commit."""
        ...


@runtime_checkable
class GateRunner(Protocol):
    async def run(self, argv: tuple[str, ...], *, cwd: Path) -> GateResult: ...


@runtime_checkable
class IntegrationBranch(Protocol):
    async def ensure(self) -> Path: ...

    async def merge_item(self, item_id: str) -> MergeOutcome: ...


@runtime_checkable
class IntegrationLock(Protocol):
    """Serializes concurrent ``build.integrate`` jobs for one
    (project, cycle): the integration branch is a single shared git ref,
    so two workers merging into it at once corrupt each other. A failed
    ``try_acquire`` means another worker holds the branch -- the job
    defers and retries, it never blocks a worker thread waiting."""

    async def try_acquire(self, project_id: UUID, cycle: int) -> bool: ...

    async def release(self, project_id: UUID, cycle: int) -> None: ...


@runtime_checkable
class VerifyWorktrees(Protocol):
    def path_for(self, item_id: str) -> Path: ...


@runtime_checkable
class CheckoutView(Protocol):
    """A read-only view of a project's checkout, as DECOMPOSE may consult it."""

    def exists(self, path: str) -> bool:
        """Whether this checkout-relative path is a file or directory in the checkout.
        A path that escapes the checkout does not exist."""
        ...


@runtime_checkable
class CheckoutLocator(Protocol):
    """Finds the checkout a project's plan is verified against."""

    async def checkout(self, project_id: UUID) -> CheckoutView | None:
        """The project's checkout, or None when the project or its checkout is gone."""
        ...


@runtime_checkable
class WorkPlanProducer(Protocol):
    async def decompose(
        self, spec: DesignSpec, *, checkout: CheckoutView | None = None
    ) -> tuple[WorkItem, ...]:
        """A whole plan. Given a `checkout`, a producer that can re-ask its model should
        refuse a plan whose verification names files nothing provides; the handler
        judges the returned plan against the same checkout either way."""
        ...
