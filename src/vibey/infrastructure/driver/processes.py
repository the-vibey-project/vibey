# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Starting and running the driver failover's processes (ADR-0070).

`spawn` detaches: a new session, stdin closed, output appended to a log under
`<worktree>/.vibey/driver/`, and it returns at once -- a hook never waits on the engine
it starts. `run` waits, with a timeout; a missing binary is exit 127 and a timeout
exit 124, the shell's own conventions, so the caller records a failure rather than
crashing on one.
"""

import subprocess  # nosec B404 -- argv lists from [failover] settings, no shell
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey.application.dto import ProcessResult
from vibey.infrastructure.driver.workspace import DRIVER_DIR

MISSING_BINARY_EXIT: Final = 127
TIMEOUT_EXIT: Final = 124


class SubprocessPort:
    """Declared by `interfaces/processes_interface.py`; satisfies `ProcessPort`."""

    def spawn(self, argv: Sequence[str], *, cwd: str) -> None:
        log_dir = Path(cwd) / DRIVER_DIR
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "processes.log").open("ab") as log:
            subprocess.Popen(  # nosec B603 -- argv from the operator's own settings
                list(argv),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    def run(self, argv: Sequence[str], *, cwd: str, timeout: float) -> ProcessResult:
        try:
            done = subprocess.run(  # nosec B603 -- argv from the operator's own settings
                list(argv),
                cwd=cwd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except FileNotFoundError:
            return ProcessResult(exit_code=MISSING_BINARY_EXIT, stdout="")
        except subprocess.TimeoutExpired:
            return ProcessResult(exit_code=TIMEOUT_EXIT, stdout="")
        return ProcessResult(exit_code=done.returncode, stdout=done.stdout)
