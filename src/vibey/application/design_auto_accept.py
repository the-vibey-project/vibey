# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Accepts a project's finished DESIGN spec for an operator who said to.

`vibey design accept` is the operator's decision that the spec is right. A worker started
with `--auto-accept-design` carries that decision in advance, for one project: the consent is
the flag, so nothing here reads silence as consent (sub-doctrine 12.d). It is deliberately
narrow:

- It acts only once DESIGN has really settled (no DESIGN job of the cycle unsettled, a spec
  present), and through `DesignAcceptanceService`, whose guards still apply: an open blocking
  question refuses it.
- With a spec file (`--accept-spec-json`) it imports that reviewed spec first, exactly as
  `vibey design accept --spec-json` does; without one it accepts what the synthesizer wrote.
- It never opts into VISUAL_DESIGN. That choice is explicit and never implicit, so here it is
  always declined.
- It accepts once. The ledger event for the visual choice names who accepted (`accepted_by`).
"""

import asyncio
from typing import Final
from uuid import UUID

from vibey.application.dto import DesignAutoAcceptReport
from vibey.application.interfaces import ProjectStore
from vibey.application.interfaces.design import DesignSpecRepository
from vibey.application.interfaces.design_auto_accept import DesignAcceptorInterface
from vibey.application.interfaces.observability import Logger
from vibey.application.ports import JobRepository
from vibey.domain.phase import Phase, VisualDecision
from vibey.domain.spec import DesignSpec

DESIGN_AUTO_ACCEPT_ACTOR: Final = "auto-accept-design"
"""Who the ledger says accepted a design this worker accepted."""


class DesignAutoAccept:
    """Declared by `interfaces/design_auto_accept.py::DesignAutoAcceptInterface`."""

    def __init__(
        self,
        *,
        projects: ProjectStore,
        jobs: JobRepository,
        specs: DesignSpecRepository,
        acceptor: DesignAcceptorInterface,
        logger: Logger,
        spec: DesignSpec | None = None,
    ) -> None:
        self._projects = projects
        self._jobs = jobs
        self._specs = specs
        self._acceptor = acceptor
        self._log = logger
        self._spec = spec
        self._finished: set[UUID] = set()
        self._imported: set[UUID] = set()
        self._said: dict[UUID, str] = {}
        # Parallel drive loops share one sweep: one at a time, so the design is accepted once.
        self._lock = asyncio.Lock()

    async def run(self, project_id: UUID | None = None) -> DesignAutoAcceptReport:
        if project_id is None or project_id in self._finished:
            return DesignAutoAcceptReport(project_id=project_id)
        async with self._lock:
            if project_id in self._finished:
                return DesignAutoAcceptReport(project_id=project_id)
            return await self._sweep(project_id)

    async def _sweep(self, project_id: UUID) -> DesignAutoAcceptReport:
        project = await self._projects.get(project_id)
        if project is None:
            self._finished.add(project_id)
            return self._report(project_id, "the project no longer exists; nothing to accept")
        if project.phase is not Phase.DESIGN:
            self._finished.add(project_id)
            return self._report(
                project_id,
                f"the project is in {project.phase.value}, not DESIGN; nothing to accept",
            )
        unsettled = await self._jobs.count_unsettled(
            project_id, cycle=project.cycle, phase=Phase.DESIGN
        )
        if unsettled:
            return self._report(project_id, f"waiting for {unsettled} DESIGN job(s) to finish")
        if self._spec is None and await self._specs.load(project_id, project.cycle) is None:
            return self._report(project_id, "waiting for the synthesized spec")
        if self._spec is not None and project_id not in self._imported:
            await self._specs.save(project_id, project.cycle, self._spec)
            self._imported.add(project_id)
        try:
            accepted = await self._acceptor.accept(
                project_id,
                visual_choice=VisualDecision.DECLINED,
                accepted_by=DESIGN_AUTO_ACCEPT_ACTOR,
            )
        except ValueError as exc:
            # The acceptance guard said not yet (an open blocking question, for one): the
            # next sweep asks again, and the reason is said once.
            return self._report(project_id, f"not accepted yet: {exc}")
        self._finished.add(project_id)
        self._log.info(
            "design.auto_accepted",
            project_id=str(project_id),
            phase=accepted.phase.value,
            imported_spec=self._spec is not None,
        )
        return DesignAutoAcceptReport(
            project_id=project_id,
            accepted=True,
            message=f"accepted the design; entered {accepted.phase.value}",
        )

    def _report(self, project_id: UUID, message: str) -> DesignAutoAcceptReport:
        """The report, with `message` only when it differs from the last one said."""
        if self._said.get(project_id) == message:
            return DesignAutoAcceptReport(project_id=project_id)
        self._said[project_id] = message
        return DesignAutoAcceptReport(project_id=project_id, message=message)
