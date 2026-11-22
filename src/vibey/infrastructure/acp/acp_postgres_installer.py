# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The PostgreSQL install `vibey acp` may run once the client allowed it (SP-ACP, step 4).

`PostgresLocalService` -- the same class `vibey doctor --install-postgres` uses -- builds the
fixed argv; every command it runs goes through an ACP runner (process group of its own, stdin
closed, output captured, bounded, `sudo -n`). `status()` runs its read-only probes through
`probe_runner`, bounded short (`[acp] bootstrap_timeout_seconds`); `install()` runs through
`runner`, bounded for a real install (`[acp] install_timeout_seconds`).

This adapter translates for the application layer and watches each command's result, because the
service's own detail names the step that failed, not why: a `sudo` that refused for want of a
password (the operator runs the install instead), and a command that overran and could not be
confirmed stopped (the install may still be running, so it is not reported as failed). Each call
builds its own service, so two calls on two threads never share what they observed.

Declared by `application/acp/interfaces/postgres_installer_interface.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from vibey.application.acp.dto import PostgresInstallOutcome, PostgresReadiness
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.interfaces.postgres_interface import PostgresLocalServiceInterface
from vibey.infrastructure.postgres import CommandRunner, PostgresCommandResult, PostgresLocalService

type ServiceFactory = Callable[[CommandRunner], PostgresLocalServiceInterface]


@dataclass
class _Observed:
    """What one call's commands showed. A value type (ADR-0016 exempts it)."""

    refused: bool = False
    unconfirmed: bool = False


class AcpPostgresInstaller:
    """Declared by `application/acp/interfaces/postgres_installer_interface.py`."""

    def __init__(
        self,
        runner: AcpCommandRunnerInterface,
        *,
        probe_runner: AcpCommandRunnerInterface | None = None,
        service: ServiceFactory = lambda run: PostgresLocalService(command_runner=run),
    ) -> None:
        self._runner = runner
        self._probe_runner = probe_runner or runner
        self._service = service

    def status(self) -> PostgresReadiness:
        service = self._service(self._observing(self._probe_runner, _Observed()))
        status = service.status()
        return PostgresReadiness(
            ready=status.ready, detail=status.detail, package_manager=service.package_manager()
        )

    def install(self) -> PostgresInstallOutcome:
        seen = _Observed()
        result = self._service(self._observing(self._runner, seen)).install()
        return PostgresInstallOutcome(
            ok=result.ok,
            detail=result.detail,
            needs_password=seen.refused and not result.ok,
            still_running=seen.unconfirmed and not result.ok,
        )

    @staticmethod
    def _observing(runner: AcpCommandRunnerInterface, seen: _Observed) -> CommandRunner:
        def run(argv: tuple[str, ...]) -> PostgresCommandResult:
            result = runner(argv)
            seen.refused = seen.refused or runner.password_refused(argv, result)
            seen.unconfirmed = seen.unconfirmed or runner.still_running(result)
            return result

        return run
