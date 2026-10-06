# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner-side half of `vibey -w` (ADR-0085), run by .github/workflows/vibey-remote.yml.

    python scripts/vibey_remote.py run --out DIR    # reads ARGV, REQUEST and the DSNs from env

It reads the command line the caller dispatched (`ARGV`, a JSON array of strings), holds it to
the domain's own rules (`vibey.domain.remote_command.RemoteCommand`), points vibey at a
database, runs `vibey <argv>` as an argument vector, and writes `DIR/result.json`: the exit
code and what the command printed. Whatever goes wrong before the command runs is reported the
same way, with exit code 2 and the reason on stderr, so the caller always reads a report.

The database is the one the repository declares (`DECLARED_PG_URL`, and `DECLARED_PG_MIGRATE_URL`
to migrate it) or, when it declares none, the runner's own empty PostgreSQL service, migrated
for the run with an owner and an application role (ADR-0055).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

try:
    from scripts.interfaces.vibey_remote_interface import (
        ProcessRunnerInterface,
        VibeyRemoteRunnerInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.vibey_remote_interface import (  # type: ignore[import-not-found,no-redef]
        ProcessRunnerInterface,
        VibeyRemoteRunnerInterface,
    )

#: The runner's own PostgreSQL service (vibey-remote.yml `services.postgres`).
EPHEMERAL_OWNER_URL: Final[str] = "postgresql://vibey:vibey@localhost:5432/vibey"
EPHEMERAL_APP_URL: Final[str] = "postgresql://vibey_app:vibey-remote-app@localhost:5432/vibey"
#: Each stream is cut here, and says so, so a runaway command cannot fill the artifact.
MAX_STREAM: Final[int] = 1_000_000
#: The command's own limit, inside the job's 60 minutes.
COMMAND_TIMEOUT_S: Final[float] = 55 * 60.0
MIGRATE_TIMEOUT_S: Final[float] = 5 * 60.0


class SubprocessRunner(ProcessRunnerInterface):
    """`subprocess.run` over an argument vector, its environment given whole."""

    def run(
        self, argv: Sequence[str], env: Mapping[str, str], timeout_s: float
    ) -> tuple[int, str, str]:
        try:
            done = subprocess.run(  # nosec B603 - an argument vector, never a shell
                list(argv), env=dict(env), capture_output=True, text=True, timeout=timeout_s
            )
        except subprocess.TimeoutExpired:
            return (
                124,
                "",
                f"vibey-remote: the command ran past {int(timeout_s)}s and was stopped\n",
            )
        return done.returncode, done.stdout, done.stderr


class VibeyRemoteRunner(VibeyRemoteRunnerInterface):
    """Implements `VibeyRemoteRunnerInterface`."""

    def __init__(self, runner: ProcessRunnerInterface, environ: Mapping[str, str]) -> None:
        self._runner = runner
        self._environ = environ

    def _environment(self) -> tuple[dict[str, str], bool]:
        """vibey's environment for the run, and whether its database must be migrated first."""
        env = dict(self._environ)
        for name in ("ARGV", "REQUEST", "DECLARED_PG_URL", "DECLARED_PG_MIGRATE_URL"):
            env.pop(name, None)
        declared = self._environ.get("DECLARED_PG_URL", "").strip()
        if declared:
            env["VIBEY_PG_URL"] = declared
            owner = self._environ.get("DECLARED_PG_MIGRATE_URL", "").strip()
            if owner:
                env["VIBEY_PG_MIGRATE_URL"] = owner
            return env, False
        env["VIBEY_PG_URL"] = EPHEMERAL_APP_URL
        env["VIBEY_PG_MIGRATE_URL"] = EPHEMERAL_OWNER_URL
        return env, True

    @staticmethod
    def _cut(text: str) -> str:
        if len(text) <= MAX_STREAM:
            return text
        return (
            text[:MAX_STREAM] + f"\n[vibey-remote: cut at {MAX_STREAM} of {len(text)} characters]\n"
        )

    def run(self, raw_argv: str, request: str, out: Path) -> dict[str, object]:
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
            env, migrate = self._environment()
            notes = ""
            if migrate:
                code, _, err = self._runner.run(["vibey", "migrate"], env, MIGRATE_TIMEOUT_S)
                if code:
                    notes = f"vibey-remote: migrating the runner's database failed:\n{err}"
            code, stdout, stderr = self._runner.run(
                ["vibey", *command.argv], env, COMMAND_TIMEOUT_S
            )
            report = {
                "exit_code": code,
                "stdout": self._cut(stdout),
                "stderr": self._cut(notes + stderr),
            }
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(json.dumps(report) + "\n", encoding="utf-8")
        return report


def main(argv: list[str]) -> int:
    """Entry point. Module-level as every script's is. Exits 0 whenever a report was written:
    the command's own exit code is the report's, not the job's."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    report = VibeyRemoteRunner(SubprocessRunner(), os.environ).run(
        os.environ.get("ARGV", ""), os.environ.get("REQUEST", ""), args.out
    )
    print(f"vibey-remote: the command exited {report['exit_code']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
