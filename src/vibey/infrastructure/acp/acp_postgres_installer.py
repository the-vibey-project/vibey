# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The PostgreSQL install `vibey acp` may run once the client allowed it (SP-ACP, step 4).

`PostgresLocalService` -- the same class `vibey doctor --install-postgres` uses -- builds the
fixed argv; every command it runs goes through the ACP runner (stdin closed, output captured,
bounded, `sudo -n`). This adapter only translates for the application layer, and notices a
`sudo` that refused for want of a password: the service's own detail names the step that
failed, not why, and the bootstrap must tell the operator to run the install themselves.

Declared by `application/acp/interfaces/postgres_installer_interface.py`.
"""

from __future__ import annotations

from collections.abc import Callable

from vibey.application.acp.dto import PostgresInstallOutcome, PostgresReadiness
from vibey.infrastructure.acp.interfaces.acp_command_runner_interface import (
    AcpCommandRunnerInterface,
)
from vibey.infrastructure.interfaces.postgres_interface import PostgresLocalServiceInterface
from vibey.infrastructure.postgres import CommandRunner, PostgresCommandResult, PostgresLocalService

type ServiceFactory = Callable[[CommandRunner], PostgresLocalServiceInterface]


class AcpPostgresInstaller:
    """Declared by `application/acp/interfaces/postgres_installer_interface.py`."""

    def __init__(
        self,
        runner: AcpCommandRunnerInterface,
        *,
        service: ServiceFactory = lambda run: PostgresLocalService(command_runner=run),
    ) -> None:
        self._runner = runner
        self._service = service(self._observed)
        self._refused = False

    def status(self) -> PostgresReadiness:
        status = self._service.status()
        return PostgresReadiness(
            ready=status.ready,
            detail=status.detail,
            package_manager=self._service.package_manager(),
        )

    def install(self) -> PostgresInstallOutcome:
        self._refused = False
        result = self._service.install()
        return PostgresInstallOutcome(
            ok=result.ok, detail=result.detail, needs_password=self._refused and not result.ok
        )

    def _observed(self, argv: tuple[str, ...]) -> PostgresCommandResult:
        result = self._runner(argv)
        if self._runner.password_refused(argv, result):
            self._refused = True
        return result
