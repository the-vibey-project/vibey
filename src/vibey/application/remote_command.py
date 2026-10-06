# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Running a vibey command on the repository's GitHub-hosted runners (ADR-0085).

`vibey -w <command>` and the hub's `/api/v1/workflows/runs` routes both come here. The
service keeps no state of its own: the request id goes into the run's name on the forge, so
`poll` finds the run from the id alone. A CLI that waits, a hub that was restarted half-way,
and a phone asking an hour later all read the same run.

Status is evidence-bounded (10.f): a run the forge has not shown yet is `queued`, never
assumed started; a run that ended without handing back a report is `failed` with the forge's
own conclusion, never read as the command having succeeded.
"""

from collections.abc import Awaitable, Callable, Sequence

from vibey.application.interfaces.remote_command import (
    RemoteCommandServiceInterface,
    RemoteWorkflowForge,
)
from vibey.domain.remote_command import RemoteCommand, RemoteState, RemoteStatus

#: The forge's words for a run that has not started on a runner yet.
NOT_STARTED = frozenset({"queued", "requested", "waiting", "pending"})


class RemoteCommandService(RemoteCommandServiceInterface):
    """Implements `RemoteCommandServiceInterface` over one forge."""

    def __init__(
        self,
        forge: RemoteWorkflowForge,
        *,
        new_id: Callable[[], str],
        sleep: Callable[[float], Awaitable[None]],
        poll_seconds: float = 10.0,
        timeout_seconds: float = 3600.0,
    ) -> None:
        if poll_seconds <= 0 or timeout_seconds <= 0:
            raise ValueError("poll_seconds and timeout_seconds must be positive")
        self._forge = forge
        self._new_id = new_id
        self._sleep = sleep
        self._poll = poll_seconds
        self._timeout = timeout_seconds

    async def start(self, argv: Sequence[str], *, request_id: str | None = None) -> RemoteCommand:
        chosen = request_id if request_id is not None else self._new_id()
        command = RemoteCommand(tuple(argv), chosen)
        await self._forge.dispatch(command)
        return command

    async def poll(self, request_id: str) -> RemoteStatus:
        run = await self._forge.find(RemoteCommand.run_name_for(request_id))
        if run is None:
            return RemoteStatus(request_id, RemoteState.QUEUED)
        if run.status != "completed":
            state = RemoteState.QUEUED if run.status in NOT_STARTED else RemoteState.RUNNING
            return RemoteStatus(request_id, state, url=run.url)
        report = await self._forge.report(run.run_id)
        if report is None:
            return RemoteStatus(
                request_id,
                RemoteState.FAILED,
                url=run.url,
                detail=f"the run ended `{run.conclusion or 'unknown'}` and handed back no report",
            )
        return RemoteStatus(
            request_id,
            RemoteState.DONE,
            url=run.url,
            exit_code=report.exit_code,
            stdout=report.stdout,
            stderr=report.stderr,
        )

    async def run(self, argv: Sequence[str]) -> RemoteStatus:
        command = await self.start(argv)
        waited = 0.0
        while True:
            status = await self.poll(command.request_id)
            if status.finished:
                return status
            if waited >= self._timeout:
                return RemoteStatus(
                    status.request_id,
                    status.state,
                    url=status.url,
                    detail=f"stopped waiting after {int(waited)}s; the run carries on"
                    + (f" at {status.url}" if status.url else ""),
                )
            await self._sleep(self._poll)
            waited += self._poll
