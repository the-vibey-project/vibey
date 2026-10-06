# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner-side half of `vibey -w` (ADR-0085), run by .github/workflows/vibey-remote.yml.

    python scripts/vibey_remote.py run --out DIR [--state-out DIR]  # ARGV, REQUEST, DSNs from env
    python scripts/vibey_remote.py sync-back --state FILE             # STATE_KEY, GH_TOKEN from env

It reads the command line the caller dispatched (`ARGV`, a JSON array of strings), holds it to
the domain's own rules (`vibey.domain.remote_command.RemoteCommand`), points vibey at a
database, runs `vibey <argv>` as an argument vector, and writes `DIR/result.json`: the exit
code and what the command printed. Whatever goes wrong before the command runs is reported the
same way, with exit code 2 and the reason on stderr, so the caller always reads a report.

The database is the one the repository declares (`DECLARED_PG_URL`, and `DECLARED_PG_MIGRATE_URL`
to migrate it) when the repository is private, or else the runner's own empty PostgreSQL
service, migrated for the run with an owner and an application role (ADR-0055). The command
runs with the system basics vibey hands any child and its application DSN: never the runner's
whole environment, and never the owner's DSN unless the command is `vibey migrate`.

The synced state (ADR-0086). When this run may open it (`StateGate`: a `VIBEY_STATE_KEY`
secret, on a private repository or on a public one that declares `public = true` in
`.github/vibey-state.toml`) and declares no database, the runner's empty database is first
given the repository's state (`vibey state sync --no-push`: read the `vibey-state` branch,
write nothing to it), so the command reads the real queue; afterwards the database is
exported, sealed, for the workflow's `sync-back` job, which alone may write the branch: it
runs the reusable `vibey-state-write.yml`, which imports the export into its own empty
database and runs `vibey state sync`, merging the run's changes with whatever moved on the
branch meanwhile. The command itself never holds the key, the owner's DSN or a token. The
gate, the state commands and their environments are `scripts/vibey_state_action.py`'s, so
`vibey -w` and every other workflow that opens the state share one implementation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final

try:
    from scripts.interfaces.vibey_remote_interface import (
        ProcessRunnerInterface,
        VibeyRemoteRunnerInterface,
    )
    from scripts.interfaces.vibey_state_action_interface import StateDeclarationError
    from scripts.vibey_state_action import (
        DECLARATION,
        EPHEMERAL_APP_URL,
        EPHEMERAL_OWNER_URL,
        STATE_FILE,
        StateCommands,
        StateDeclaration,
        StateGate,
        SubprocessRunner,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.vibey_remote_interface import (  # type: ignore[import-not-found,no-redef]
        ProcessRunnerInterface,
        VibeyRemoteRunnerInterface,
    )
    from interfaces.vibey_state_action_interface import (  # type: ignore[import-not-found,no-redef]
        StateDeclarationError,
    )
    from vibey_state_action import (  # type: ignore[import-not-found,no-redef]
        DECLARATION,
        EPHEMERAL_APP_URL,
        EPHEMERAL_OWNER_URL,
        STATE_FILE,
        StateCommands,
        StateDeclaration,
        StateGate,
        SubprocessRunner,
    )

__all__ = [
    "EPHEMERAL_APP_URL",
    "EPHEMERAL_OWNER_URL",
    "STATE_FILE",
    "SubprocessRunner",
    "VibeyRemoteRunner",
    "main",
]

#: Each stream is cut here, and says so, so a runaway command cannot fill the artifact.
MAX_STREAM: Final[int] = 1_000_000
#: The command's own limit, inside the job's 60 minutes.
COMMAND_TIMEOUT_S: Final[float] = 55 * 60.0


class VibeyRemoteRunner(VibeyRemoteRunnerInterface):
    """Implements `VibeyRemoteRunnerInterface`."""

    def __init__(
        self,
        runner: ProcessRunnerInterface,
        environ: Mapping[str, str],
        declaration: Path = DECLARATION,
    ) -> None:
        self._runner = runner
        self._environ = environ
        self._commands = StateCommands(runner, environ, prefix="vibey-remote")
        self._gate = StateGate(environ, StateDeclaration(declaration), prefix="vibey-remote")

    def _database(self) -> tuple[str, str, str]:
        """The application DSN, the owner DSN, and a note for stderr. A declared database is
        used only on a private repository: on a public one the run's logs and its report can
        be read by others, so its contents would leave with them (ADR-0085)."""
        declared = self._environ.get("DECLARED_PG_URL", "").strip()
        if declared and self._environ.get("REPOSITORY_PRIVATE", "") == "true":
            return declared, self._environ.get("DECLARED_PG_MIGRATE_URL", "").strip(), ""
        note = (
            "vibey-remote: the declared database is not used on a public repository; "
            "this run used the runner's own, empty one\n"
            if declared
            else ""
        )
        return EPHEMERAL_APP_URL, EPHEMERAL_OWNER_URL, note

    def _state_wanted(self, owner_url: str) -> tuple[bool, str]:
        """Whether this run restores the synced state, and a note for stderr when it may
        not. Only into the runner's own database, and only when `StateGate` allows it."""
        if owner_url != EPHEMERAL_OWNER_URL:
            return False, ""
        try:
            return self._gate.decide()
        except StateDeclarationError as broken:
            return False, f"vibey-remote: the synced state is not restored: {broken}\n"

    def sync_back(self, state: Path) -> tuple[int, str]:
        """The `sync-back` step: the state action's write-back into the runner's database."""
        return self._commands.write_back(state, EPHEMERAL_APP_URL, EPHEMERAL_OWNER_URL)

    @staticmethod
    def _cut(text: str) -> str:
        if len(text) <= MAX_STREAM:
            return text
        return (
            text[:MAX_STREAM] + f"\n[vibey-remote: cut at {MAX_STREAM} of {len(text)} characters]\n"
        )

    def run(
        self, raw_argv: str, request: str, out: Path, state_out: Path | None = None
    ) -> dict[str, object]:
        from vibey.domain.remote_command import RemoteCommand, RemoteCommandRefused

        report: dict[str, object]
        try:
            argv = json.loads(raw_argv)
            if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
                raise RemoteCommandRefused("ARGV must be a JSON array of strings")
            command = RemoteCommand(tuple(argv), request)
        except (json.JSONDecodeError, RemoteCommandRefused) as refused:
            report = {"exit_code": 2, "stdout": "", "stderr": f"vibey-remote: {refused}\n"}
        else:
            app_url, owner_url, notes = self._database()
            restore, note = self._state_wanted(owner_url)
            notes += note
            if owner_url == EPHEMERAL_OWNER_URL:
                failed = self._commands.migrate(app_url, owner_url)
                notes += failed
                restore = restore and not failed and state_out is not None
            if restore:
                code, _, err = self._commands.run(
                    ["vibey", "state", "sync", "--no-push"], owner_url
                )
                if code:
                    notes += f"vibey-remote: restoring the synced state failed:\n{err}"
                    restore = False
            is_migrate = command.argv[:1] == ("migrate",)
            code, stdout, stderr = self._runner.run(
                ["vibey", *command.argv],
                self._commands.environment(app_url, owner_url, migrate=is_migrate),
                COMMAND_TIMEOUT_S,
            )
            exported = False
            if restore and state_out is not None:
                done, _, err = self._commands.run(
                    ["vibey", "state", "export", "--out", str(state_out / STATE_FILE)], owner_url
                )
                exported = done == 0
                if done:
                    stderr += f"vibey-remote: exporting the state for sync-back failed:\n{err}"
            report = {
                "exit_code": code,
                "stdout": self._cut(stdout),
                "stderr": self._cut(notes + stderr),
                "state_exported": exported,
            }
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
        return report


def main(argv: list[str]) -> int:
    """Entry point. Module-level as every script's is. `run` exits 0 whenever a report was
    written: the command's own exit code is the report's, not the job's. `sync-back` exits
    with the state commands' code: a failed write-back fails its job, visibly."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", required=True, type=Path)
    run.add_argument("--state-out", type=Path, default=None)
    back = sub.add_parser("sync-back")
    back.add_argument("--state", required=True, type=Path)
    args = parser.parse_args(argv)
    runner = VibeyRemoteRunner(SubprocessRunner("vibey-remote"), os.environ)
    if args.command == "sync-back":
        code, said = runner.sync_back(args.state)
        print(said, end="")
        return code
    report = runner.run(
        os.environ.get("ARGV", ""), os.environ.get("REQUEST", ""), args.out, args.state_out
    )
    print(f"vibey-remote: the command exited {report['exit_code']}")
    if report.get("state_exported") and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("state=true\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
