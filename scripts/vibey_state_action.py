# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Any GitHub workflow's way into the synced state (ADR-0086), run by `.github/actions/vibey-state`.

    python scripts/vibey_state_action.py open                   # STATE_KEY, GH_TOKEN, PG_URL
    python scripts/vibey_state_action.py close --out DIR [--push true|false]
    python scripts/vibey_state_action.py write-back FILE        # the write job's step

`open` gives this job a PostgreSQL holding the repository's state: the one the job declared
(`PG_URL`, an owner's DSN, as from `services: postgres`), or else the runner's preinstalled
one, started for the job. It migrates it, restores the state into it with
`vibey state sync --no-push` (read the `vibey-state` branch, write nothing to it), and tells
the job's later steps where it is: `VIBEY_PG_URL` (the application role) and
`VIBEY_STATE_PG_URL` (the owner) in `$GITHUB_ENV`, and `opened=true` in `$GITHUB_OUTPUT`.

`close` exports the state, sealed, for a write job that alone holds `contents: write`
(`.github/workflows/vibey-state-write.yml`, which runs `write-back`); or, with `--push true`,
in a job that already holds `contents: write`, syncs it with the branch directly.

`write-back` is what the write job does: a fresh database, migrated, given the export with
`vibey state import`, then `vibey state sync`, which merges it with whatever moved on the
branch meanwhile and writes the result back. `scripts/vibey_remote.py` (`vibey -w`) uses the
same commands, the same gate and the same environments.

Who may open it (`StateGate`): a run with a non-empty `STATE_KEY`, on a private repository
(`REPOSITORY_PRIVATE == "true"`, or GitHub's answer when the event did not say), or on a
public one whose `.github/vibey-state.toml` declares `[state] public = true`. On a public
repository whatever a workflow prints from the decrypted state is public; the declaration is
the operator saying so. Absent, a public repository never decrypts it.

Every state command runs with the system basics vibey hands any child, `VIBEY_STATE_*`, the
key, the repository and `GH_TOKEN`: never the runner's whole environment.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
import tomllib
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit, urlunsplit

try:
    from scripts.interfaces.vibey_state_action_interface import (
        PostgresProvisionerInterface,
        ProcessRunnerInterface,
        StateActionInterface,
        StateCommandsInterface,
        StateDeclarationError,
        StateDeclarationInterface,
        StateGateInterface,
    )
except ModuleNotFoundError:  # Direct execution keeps the script directory on sys.path.
    from interfaces.vibey_state_action_interface import (  # type: ignore[import-not-found,no-redef]
        PostgresProvisionerInterface,
        ProcessRunnerInterface,
        StateActionInterface,
        StateCommandsInterface,
        StateDeclarationError,
        StateDeclarationInterface,
        StateGateInterface,
    )

#: The runner's own PostgreSQL: vibey-remote.yml's `services.postgres`, or the preinstalled
#: one `RunnerPostgres` starts, with the same owner.
EPHEMERAL_OWNER_URL: Final[str] = "postgresql://vibey:vibey@localhost:5432/vibey"
EPHEMERAL_APP_URL: Final[str] = "postgresql://vibey_app:vibey-remote-app@localhost:5432/vibey"
MIGRATE_TIMEOUT_S: Final[float] = 5 * 60.0
STATE_TIMEOUT_S: Final[float] = 10 * 60.0
POSTGRES_TIMEOUT_S: Final[float] = 2 * 60.0
VISIBILITY_TIMEOUT_S: Final[float] = 60.0
#: How many one-second waits the runner's PostgreSQL gets to answer after it was started.
READY_ATTEMPTS: Final[int] = 30
#: The sealed export a run hands its write job.
STATE_FILE: Final[str] = "state.vibey-export"
#: Where a repository declares whether a public run may open its state.
DECLARATION: Final[Path] = Path(".github") / "vibey-state.toml"
#: The keys the declaration may hold, per table.
DECLARED: Final[Mapping[str, frozenset[str]]] = {"state": frozenset({"public"})}
EXIT_SETTING: Final[int] = 2


class SubprocessRunner(ProcessRunnerInterface):
    """`subprocess.run` over an argument vector, its environment given whole."""

    def __init__(self, prefix: str = "vibey-state") -> None:
        self._prefix = prefix

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
                f"{self._prefix}: the command ran past {int(timeout_s)}s and was stopped\n",
            )
        return done.returncode, done.stdout, done.stderr


class StateDeclaration(StateDeclarationInterface):
    """Implements `StateDeclarationInterface` over one TOML file."""

    def __init__(self, path: Path = DECLARATION) -> None:
        self._path = path

    def public(self) -> bool:
        if not self._path.is_file():
            return False
        try:
            data = tomllib.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as unreadable:
            raise StateDeclarationError(f"{self._path}: {unreadable}") from unreadable
        unknown = sorted(set(data) - set(DECLARED))
        if unknown:
            raise StateDeclarationError(f"{self._path}: unknown table(s) {', '.join(unknown)}")
        state = data.get("state", {})
        if not isinstance(state, dict):
            raise StateDeclarationError(f"{self._path}: `state` must be a table")
        unknown = sorted(set(state) - DECLARED["state"])
        if unknown:
            raise StateDeclarationError(
                f"{self._path}: unknown key(s) state.{', state.'.join(unknown)}"
            )
        public = state.get("public", False)
        if not isinstance(public, bool):
            raise StateDeclarationError(
                f"{self._path}: `state.public` must be true or false, not {type(public).__name__}"
            )
        return public


class StateGate(StateGateInterface):
    """Implements `StateGateInterface`. The declaration is read on every decision, key or
    not, so a broken one is refused by name wherever it is read.

    Whether the repository is private is `REPOSITORY_PRIVATE` (the event's
    `repository.private`). An event whose payload names no repository, as a `schedule` run's
    does not, leaves it empty; given a runner, the gate then asks GitHub, with `gh` and the
    job's token. An answer it cannot get counts as public: closed, unless declared."""

    def __init__(
        self,
        environ: Mapping[str, str],
        declaration: StateDeclarationInterface,
        *,
        prefix: str = "vibey-state",
        runner: ProcessRunnerInterface | None = None,
    ) -> None:
        self._environ = environ
        self._declaration = declaration
        self._prefix = prefix
        self._runner = runner

    def _private(self) -> bool:
        given = self._environ.get("REPOSITORY_PRIVATE", "").strip()
        repository = self._environ.get("GITHUB_REPOSITORY", "").strip()
        if given or self._runner is None or not repository:
            return given == "true"
        from vibey.infrastructure.process import SYSTEM_ENVIRONMENT

        env = {k: v for k, v in self._environ.items() if SYSTEM_ENVIRONMENT.admits(k)}
        if self._environ.get("GH_TOKEN"):
            env["GH_TOKEN"] = self._environ["GH_TOKEN"]
        code, out, _ = self._runner.run(
            ["gh", "api", f"repos/{repository}", "--jq", ".private"], env, VISIBILITY_TIMEOUT_S
        )
        return code == 0 and out.strip() == "true"

    def decide(self) -> tuple[bool, str]:
        public = self._declaration.public()
        if not self._environ.get("STATE_KEY", "").strip():
            return False, ""
        if public or self._private():
            return True, ""
        return False, (
            f"{self._prefix}: the synced state is not restored: a public repository needs "
            f"`public = true` in {DECLARATION}\n"
        )


class StateCommands(StateCommandsInterface):
    """Implements `StateCommandsInterface`."""

    def __init__(
        self,
        runner: ProcessRunnerInterface,
        environ: Mapping[str, str],
        *,
        prefix: str = "vibey-state",
    ) -> None:
        self._runner = runner
        self._environ = environ
        self._prefix = prefix

    def _basics(self) -> dict[str, str]:
        from vibey.infrastructure.process import SYSTEM_ENVIRONMENT

        return {k: v for k, v in self._environ.items() if SYSTEM_ENVIRONMENT.admits(k)}

    def environment(self, app_url: str, owner_url: str, *, migrate: bool) -> dict[str, str]:
        env = self._basics()
        env["VIBEY_PG_URL"] = app_url
        if migrate and owner_url:
            env["VIBEY_PG_MIGRATE_URL"] = owner_url
        return env

    def state_environment(self, owner_url: str) -> dict[str, str]:
        env = self._basics()
        env.update(
            {k: v for k, v in self._environ.items() if k.startswith("VIBEY_STATE_") and v.strip()}
        )
        if self._environ.get("GH_TOKEN"):
            env["GH_TOKEN"] = self._environ["GH_TOKEN"]
        env["VIBEY_STATE_PG_URL"] = owner_url
        env["VIBEY_STATE_KEY"] = self._environ.get("STATE_KEY", "").strip()
        env["VIBEY_STATE_REPOSITORY"] = self._environ.get(
            "VIBEY_STATE_REPOSITORY", ""
        ).strip() or self._environ.get("GITHUB_REPOSITORY", "")
        return env

    def migrate(self, app_url: str, owner_url: str) -> str:
        code, _, err = self._runner.run(
            ["vibey", "migrate"],
            self.environment(app_url, owner_url, migrate=True),
            MIGRATE_TIMEOUT_S,
        )
        return f"{self._prefix}: migrating the runner's database failed:\n{err}" if code else ""

    def run(self, argv: Sequence[str], owner_url: str) -> tuple[int, str, str]:
        return self._runner.run(argv, self.state_environment(owner_url), STATE_TIMEOUT_S)

    def write_back(self, state: Path, app_url: str, owner_url: str) -> tuple[int, str]:
        if not state.is_file():
            return 1, f"{self._prefix}: no export at {state}\n"
        notes = self.migrate(app_url, owner_url)
        if notes:
            return 1, notes
        said = ""
        for argv in (["vibey", "state", "import", str(state)], ["vibey", "state", "sync"]):
            code, out, err = self.run(argv, owner_url)
            said += out + err
            if code:
                return code, said
        return 0, said


class RunnerPostgres(PostgresProvisionerInterface):
    """Implements `PostgresProvisionerInterface` for a GitHub-hosted Ubuntu runner, whose
    PostgreSQL is installed and stopped. Idempotent: a second start finds the role and the
    database there, sets the role's password again, and creates nothing twice."""

    def __init__(
        self,
        runner: ProcessRunnerInterface,
        environ: Mapping[str, str],
        *,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._runner = runner
        self._environ = environ
        self._sleep = sleep

    @staticmethod
    def _identifier(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    @staticmethod
    def _literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _run(self, argv: Sequence[str]) -> tuple[int, str, str]:
        from vibey.infrastructure.process import SYSTEM_ENVIRONMENT

        env = {k: v for k, v in self._environ.items() if SYSTEM_ENVIRONMENT.admits(k)}
        return self._runner.run(argv, env, POSTGRES_TIMEOUT_S)

    def start(self) -> str:
        owner = urlsplit(EPHEMERAL_OWNER_URL)
        role, password = owner.username or "", owner.password or ""
        database = owner.path.lstrip("/")
        code, _, err = self._run(["sudo", "systemctl", "start", "postgresql.service"])
        if code:
            return f"vibey-state: starting the runner's PostgreSQL failed:\n{err}"
        for _ in range(READY_ATTEMPTS):
            ready, _, _ = self._run(
                ["pg_isready", "-h", owner.hostname or "localhost", "-p", str(owner.port or 5432)]
            )
            if ready == 0:
                break
            self._sleep(1.0)
        else:
            return f"vibey-state: the runner's PostgreSQL did not answer within {READY_ATTEMPTS}s\n"
        psql = ["sudo", "-u", "postgres", "psql", "-v", "ON_ERROR_STOP=1"]
        # Every name and the password are this script's own constants, quoted all the same.
        grant = f"LOGIN SUPERUSER PASSWORD {self._literal(password)}"
        role_sql = (
            "DO $vibey$ BEGIN IF EXISTS (SELECT FROM pg_roles WHERE rolname = "
            f"{self._literal(role)}) THEN ALTER ROLE {self._identifier(role)} {grant}; "
            f"ELSE CREATE ROLE {self._identifier(role)} {grant}; END IF; END $vibey$"
        )
        code, _, err = self._run([*psql, "-c", role_sql])
        if code:
            return f"vibey-state: creating the {role} role failed:\n{err}"
        code, out, err = self._run(
            [*psql, "-tAc", f"SELECT 1 FROM pg_database WHERE datname = {self._literal(database)}"]
        )
        if code:
            return f"vibey-state: looking for the {database} database failed:\n{err}"
        if out.strip() != "1":
            code, _, err = self._run(["sudo", "-u", "postgres", "createdb", "-O", role, database])
            if code:
                return f"vibey-state: creating the {database} database failed:\n{err}"
        return ""


class StateAction(StateActionInterface):
    """Implements `StateActionInterface`. Reads its inputs from the environment the composite
    action gives it: `STATE_KEY`, `GH_TOKEN`, `REPOSITORY_PRIVATE`, `PG_URL`, `APP_PG_URL`
    and `ARTIFACT`, and GitHub's own `GITHUB_*`."""

    def __init__(
        self,
        environ: Mapping[str, str],
        *,
        gate: StateGateInterface,
        postgres: PostgresProvisionerInterface,
        commands: StateCommandsInterface,
    ) -> None:
        self._environ = environ
        self._gate = gate
        self._postgres = postgres
        self._commands = commands

    def _append(self, variable: str, **values: str) -> None:
        """`name=value` lines into the file GitHub names in `variable`, when it names one."""
        where = self._environ.get(variable, "")
        if where:
            with open(where, "a", encoding="utf-8") as handle:
                handle.writelines(f"{name}={value}\n" for name, value in values.items())

    @staticmethod
    def _say(out: str, err: str) -> None:
        print(out, end="")
        print(err, end="", file=sys.stderr)

    def _refused(self) -> int | None:
        """None when this run may open the state; otherwise the exit code of a step that may
        not: 2 for a declaration that cannot be read, 0 for a run that was not given it."""
        try:
            allowed, note = self._gate.decide()
        except StateDeclarationError as broken:
            print(f"vibey-state: {broken}", file=sys.stderr)
            return EXIT_SETTING
        if allowed:
            return None
        print(
            note
            or "vibey-state: no state key was given (the `key` input, from the "
            "VIBEY_STATE_KEY secret), so the state stays closed\n",
            end="",
            file=sys.stderr,
        )
        return 0

    @staticmethod
    def _app_url(owner_url: str) -> str:
        """The application role's DSN on the owner's server: the owner's, with the
        application role's name and password (`EPHEMERAL_APP_URL`)."""
        owner, app = urlsplit(owner_url), urlsplit(EPHEMERAL_APP_URL)
        host = owner.hostname or ""
        if ":" in host:
            host = f"[{host}]"
        port = f":{owner.port}" if owner.port else ""
        netloc = f"{app.username}:{app.password}@{host}{port}"
        return urlunsplit((owner.scheme, netloc, owner.path, owner.query, owner.fragment))

    def _database(self) -> tuple[str, str, str]:
        """The owner's DSN, the application's, and what went wrong (empty when nothing)."""
        given = self._environ.get("PG_URL", "").strip()
        if given:
            owner = given
            app = self._environ.get("APP_PG_URL", "").strip() or self._app_url(given)
            problem = ""
        else:
            owner, app = EPHEMERAL_OWNER_URL, EPHEMERAL_APP_URL
            problem = self._postgres.start()
        if any(c in owner + app for c in "\r\n"):
            problem = "vibey-state: a database URL cannot hold a line break\n"
        return owner, app, problem

    def open(self) -> int:
        refused = self._refused()
        if refused is not None:
            self._append("GITHUB_OUTPUT", opened="false")
            return refused
        owner, app, problem = self._database()
        problem = problem or self._commands.migrate(app, owner)
        if problem:
            print(problem, end="", file=sys.stderr)
            return 1
        code, out, err = self._commands.run(["vibey", "state", "sync", "--no-push"], owner)
        self._say(out, err)
        if code:
            print("vibey-state: restoring the synced state failed", file=sys.stderr)
            return code
        self._append("GITHUB_ENV", VIBEY_PG_URL=app, VIBEY_STATE_PG_URL=owner)
        self._append("GITHUB_OUTPUT", opened="true")
        return 0

    def _artifact(self) -> str:
        """The export's artifact name: `ARTIFACT`, or one unique to this run, attempt and job."""
        given = self._environ.get("ARTIFACT", "").strip()
        if given:
            return given
        parts = (
            self._environ.get(k, "") for k in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB")
        )
        return "-".join(["vibey-state", *(p for p in parts if p)])

    def close(self, out: Path, *, push: bool) -> int:
        refused = self._refused()
        if refused is not None:
            self._append("GITHUB_OUTPUT", state="false")
            return refused
        owner = self._environ.get("VIBEY_STATE_PG_URL", "").strip()
        artifact = self._artifact()
        if not owner:
            print(
                "vibey-state: nothing to close: open the state in this job first", file=sys.stderr
            )
            return 1
        if any(c in artifact for c in "\r\n"):
            print("vibey-state: an artifact name cannot hold a line break", file=sys.stderr)
            return EXIT_SETTING
        if push:
            code, said, err = self._commands.run(["vibey", "state", "sync"], owner)
            self._say(said, err)
            self._append("GITHUB_OUTPUT", state="false", pushed="true" if code == 0 else "false")
            return code
        sealed = out / STATE_FILE
        code, said, err = self._commands.run(
            ["vibey", "state", "export", "--out", str(sealed)], owner
        )
        self._say(said, err)
        if code:
            self._append("GITHUB_OUTPUT", state="false")
            return code
        self._append(
            "GITHUB_OUTPUT", state="true", path=str(sealed), dir=str(out), artifact=artifact
        )
        return 0

    def write_back(self, state: Path) -> int:
        refused = self._refused()
        if refused is not None:
            return refused or 1
        owner, app, problem = self._database()
        if problem:
            print(problem, end="", file=sys.stderr)
            return 1
        code, said = self._commands.write_back(state, app, owner)
        print(said, end="")
        return code


def main(argv: list[str]) -> int:
    """Entry point. Module-level as every script's is. Each step exits with its own code: a
    step that could not do what it was asked fails its job, visibly; a run that was not
    given the state (no key, or a public repository that did not declare it) exits 0."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    sub = parser.add_subparsers(dest="step", required=True)
    sub.add_parser("open")
    close = sub.add_parser("close")
    close.add_argument("--out", required=True, type=Path)
    close.add_argument("--push", choices=("true", "false"), default="false")
    back = sub.add_parser("write-back")
    back.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    environ = os.environ
    runner = SubprocessRunner()
    action = StateAction(
        environ,
        gate=StateGate(environ, StateDeclaration(), runner=runner),
        postgres=RunnerPostgres(runner, environ),
        commands=StateCommands(runner, environ),
    )
    if args.step == "open":
        return action.open()
    if args.step == "close":
        return action.close(args.out, push=args.push == "true")
    return action.write_back(args.file)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
