# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every abandonment of a project takes (`vibey abandon`).

A project that is not going to finish -- built on the wrong spec, superseded, no longer
wanted -- is abandoned by a person, never by vibey. Until it is, anything waiting on it
waits forever: the triaged-delivery bridge holds its one delivery slot for a dispatched
project until that project is done or abandoned.

Checked here before anything is written: the reason, which must be one recordable line
or more of visible text, and who is abandoning it -- `by`, the name the caller gave, or
the account that ran the command when it gave none; `account` is recorded beside it
whatever the label. `by` is a label for the record, not an authority: whoever can run
vibey against this database can already stop a project's work. The store then decides,
under a lock on the project's row and through the phase machine's own guard, and writes
the move, its record and everything it stops in one transaction (see
`interfaces/project_abandonment.py`).
"""

from dataclasses import replace
from uuid import UUID

from vibey.application.dto import AbandonmentReport
from vibey.application.interfaces import CallerIdentity, ProjectAbandonmentStore
from vibey.domain.abandonment import ABANDONMENT_POLICY
from vibey.domain.interfaces.abandonment_interface import AbandonmentPolicyInterface


class ProjectAbandonment:
    """Declared by `interfaces/project_abandonment.py::ProjectAbandonmentInterface`."""

    def __init__(
        self,
        *,
        store: ProjectAbandonmentStore,
        caller: CallerIdentity,
        policy: AbandonmentPolicyInterface = ABANDONMENT_POLICY,
    ) -> None:
        self._store = store
        self._caller = caller
        self._policy = policy

    async def preview(
        self, project_id: UUID, *, reason: str, by: str | None = None
    ) -> AbandonmentReport:
        checked, actor, account = self._attribution(reason, by)
        report = await self._store.preview(project_id)
        return replace(report, reason=checked, by=actor, account=account)

    async def abandon(
        self, project_id: UUID, *, reason: str, by: str | None = None
    ) -> AbandonmentReport:
        checked, actor, account = self._attribution(reason, by)
        return await self._store.abandon(project_id, reason=checked, by=actor, account=account)

    def _attribution(self, reason: str, by: str | None) -> tuple[str, str, str]:
        account = self._caller.current().name
        return self._policy.reason(reason), self._policy.actor(by, account=account), account
