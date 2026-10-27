# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One command from a fresh clone to a working contributor environment (#1689).

`vibey-gh setup` replaces the order-dependent procedure CONTRIBUTING.md used to spell out:
sync the environment, install the pre-commit framework's hooks, then the provenance hooks, check
that the test database can be reached, and finish by running `vibey doctor`. The order rule
("`pre-commit install` refuses to run while `core.hooksPath` is set") is code here, not prose.

Every step reports what it **observed** afterwards, never what it ran (sub-doctrine 12.e): the
framework hooks are read back from the git common directory, and the wiring is read back through
`installed(local=True)`, the same check `vibey-gh check` makes.

What it deliberately does not do, because the judgement belongs to the person:

* It never overwrites a `core.hooksPath` it did not set. A global or system value, or a local one
  other than `.githooks`, is named and left alone.
* It never creates a PostgreSQL role, a password or `~/.pgpass`. It checks, and prints the
  commands from CONTRIBUTING.md when the check fails. `--postgres` installs the server only.
* `vibey doctor` is shown in full but is **advisory**: it also checks things only an operator has
  (the Sabbath location, the supervisor, host health), so its exit status is reported and not
  folded into setup's.

The tenant is stdlib-only and cannot import `vibey`, so the engine's own commands are reached by
subprocess through `CommandRunnerInterface`.
"""

from __future__ import annotations

import getpass
import os
import shutil
import socket
import subprocess  # nosec B404 - fixed argv, shell disabled
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from urllib.parse import unquote, urlsplit

from vibey_gh import install
from vibey_gh.config import GhConfig
from vibey_gh.hook_inspector import STAGES, HookInspector
from vibey_gh.interfaces.command_runner_interface import CommandResult, CommandRunnerInterface
from vibey_gh.interfaces.contributor_setup_interface import (
    ContributorSetupInterface,
    SetupReport,
    SetupStep,
)
from vibey_gh.interfaces.hook_inspector_interface import HookInspectorInterface

__all__ = ["ContributorSetup", "SetupReport", "SetupStep", "SubprocessRunner"]

MIN_PYTHON = (3, 12)
TEST_DSN_VARIABLE = "VIBEY_TEST_DATABASE_URL"

POSTGRES_HELP = (
    'createuser --createdb --createrole --pwprompt "$USER"   # run as a PostgreSQL superuser',
    'echo "localhost:5432:*:$USER:<the password you chose>" >> ~/.pgpass && chmod 600 ~/.pgpass',
    "createdb vibey_test",
    '(CONTRIBUTING.md, "Environment setup"; the server must authenticate with scram-sha-256)',
)

_UV_CHANGED = ("Installed", "Uninstalled", "Updated")


class SubprocessRunner(CommandRunnerInterface):
    """Runs a fixed argv with the shell disabled."""

    def run(
        self, argv: Sequence[str], cwd: Path, env: Mapping[str, str] | None = None
    ) -> CommandResult:
        try:
            done = subprocess.run(  # nosec B603 - fixed argv, shell disabled
                list(argv),
                cwd=cwd,
                env={**os.environ, **(env or {})},
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            return CommandResult(127, "", str(exc))
        return CommandResult(done.returncode, done.stdout, done.stderr)


class ContributorSetup(ContributorSetupInterface):
    """Implements `ContributorSetupInterface`."""

    def __init__(
        self,
        cfg: GhConfig,
        *,
        runner: CommandRunnerInterface | None = None,
        inspector: HookInspectorInterface | None = None,
        installer: Callable[[GhConfig], list[install.Action]] = install.install,
        checker: Callable[..., tuple[bool, list[str]]] = install.installed,
        which: Callable[[str], str | None] = shutil.which,
        connect: Callable[[str, int], bool] | None = None,
        environ: Mapping[str, str] | None = None,
        python: tuple[int, int] | None = None,
    ) -> None:
        self._cfg = cfg
        self._runner: CommandRunnerInterface = runner or SubprocessRunner()
        self._inspector: HookInspectorInterface = inspector or HookInspector()
        self._installer = installer
        self._checker = checker
        self._which = which
        self._connect = connect or self._tcp_open
        self._environ = os.environ if environ is None else environ
        self._python = python or (sys.version_info.major, sys.version_info.minor)

    # ------------------------------------------------------------------ the two entry points

    def run(self, *, postgres: bool = False, doctor: bool = True) -> SetupReport:
        steps = [self._prerequisites()]
        if steps[0].status == "failed":
            return SetupReport(tuple(steps))
        steps.append(self._sync())
        steps.append(self._framework_hooks())
        steps.append(self._provenance_hooks())
        steps.append(self._wiring())
        steps.append(self._postgres(install_server=postgres))
        steps.append(
            self._doctor()
            if doctor
            else SetupStep("vibey doctor", "skipped", "--skip-doctor was given")
        )
        return SetupReport(tuple(steps))

    def check(self) -> SetupReport:
        steps = [self._prerequisites()]
        states = self._inspector.stages(self._cfg)
        if not states:
            steps.append(self._no_framework())
        else:
            missing = [stage for stage, state in states.items() if state != "installed"]
            steps.append(
                SetupStep(
                    "pre-commit framework hooks",
                    "failed" if missing else "unchanged",
                    f"not installed: {', '.join(missing)}" if missing else "all three installed",
                )
            )
        steps.append(self._wiring())
        steps.append(self._postgres(install_server=False))
        steps.append(SetupStep("environment sync", "skipped", "--check changes nothing"))
        steps.append(SetupStep("vibey doctor", "skipped", "--check runs nothing"))
        return SetupReport(tuple(steps))

    def render(self, report: SetupReport) -> list[str]:
        lines: list[str] = []
        for step in report.steps:
            head, *rest = (step.detail or "").splitlines() or [""]
            lines.append(f"  [{step.status}] {step.name}" + (f": {head}" if head else ""))
            lines.extend(f"      {line}" for line in rest)
        lines.append(
            "vibey-gh setup: ready"
            if report.ok
            else "vibey-gh setup: not ready — see [failed] above"
        )
        return lines

    # ------------------------------------------------------------------------------- steps

    def _prerequisites(self) -> SetupStep:
        missing = [tool for tool in ("git", "uv") if self._which(tool) is None]
        if missing:
            hint = (
                " (https://docs.astral.sh/uv/getting-started/installation/)"
                if "uv" in missing
                else ""
            )
            return SetupStep(
                "prerequisites", "failed", f"not found on PATH: {', '.join(missing)}{hint}"
            )
        if self._python < MIN_PYTHON:
            return SetupStep(
                "prerequisites",
                "failed",
                f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required, this is "
                f"{self._python[0]}.{self._python[1]}",
            )
        return SetupStep("prerequisites", "unchanged", "git, uv and Python found")

    def _sync(self) -> SetupStep:
        done = self._runner.run(["uv", "sync", "--extra", "dev"], self._cfg.root)
        if done.returncode != 0:
            return SetupStep("environment sync", "failed", self._tail(done))
        changed = any(word in done.output for word in _UV_CHANGED)
        return SetupStep(
            "environment sync", "done" if changed else "unchanged", "uv sync --extra dev"
        )

    def _no_framework(self) -> SetupStep:
        return SetupStep(
            "pre-commit framework hooks",
            "skipped",
            "this repository declares no .pre-commit-config.yaml",
        )

    def _framework_hooks(self) -> SetupStep:
        name = "pre-commit framework hooks"
        states = self._inspector.stages(self._cfg)
        if not states:
            return self._no_framework()
        if all(state == "installed" for state in states.values()):
            return SetupStep(name, "unchanged", "all three stages already installed")
        local = self._git_config("--local")
        effective = self._git_config()
        # `pre-commit install` refuses to run while core.hooksPath is set. A value in this
        # clone's own config that is ours (.githooks, i.e. a re-run) is lifted for the
        # install and put back; anything else is someone's choice and is left alone.
        if effective and not local:
            return SetupStep(
                name,
                "failed",
                f"core.hooksPath is {effective!r} in your global or system git config, which "
                "`pre-commit install` refuses to run under. Unset it for this clone's sake "
                "(`git config --global --unset core.hooksPath`) and run setup again; nothing was changed.",
            )
        if local and local != install.HOOKS_DIR:
            return SetupStep(
                name,
                "failed",
                f"core.hooksPath is {local!r} in this clone, not {install.HOOKS_DIR!r}; "
                "setup does not overwrite a value it did not set. Nothing was changed.",
            )
        restore = local == install.HOOKS_DIR
        if restore:
            self._runner.run(
                ["git", "config", "--local", "--unset", "core.hooksPath"], self._cfg.root
            )
        try:
            argv = ["uv", "run", "pre-commit", "install"]
            for stage in STAGES:
                argv += ["--hook-type", stage]
            done = self._runner.run(argv, self._cfg.root)
        finally:
            if restore:
                self._runner.run(
                    ["git", "config", "--local", "core.hooksPath", install.HOOKS_DIR],
                    self._cfg.root,
                )
        remaining = [
            s for s, state in self._inspector.stages(self._cfg).items() if state != "installed"
        ]
        if remaining:
            detail = f"still not installed after `pre-commit install`: {', '.join(remaining)}"
            if done.returncode != 0:
                detail += f"\n{self._tail(done)}"
            return SetupStep(name, "failed", detail)
        return SetupStep(name, "done", "installed " + ", ".join(STAGES))

    def _provenance_hooks(self) -> SetupStep:
        name = "provenance hooks (vibey-gh install)"
        before = self._porcelain()
        actions = self._installer(self._cfg)
        after = self._porcelain()
        changed = [
            f"{action.hook}: {action.outcome}"
            for action in actions
            if action.outcome != "unchanged"
        ]
        touched = sorted(after - before)
        if not changed and not touched:
            return SetupStep(name, "unchanged", "")
        lines = changed[:]
        if touched:
            lines.append(
                "tracked files now differ from git (nothing was committed): " + ", ".join(touched)
            )
        return SetupStep(name, "done", "\n".join(lines))

    def _wiring(self) -> SetupStep:
        name = "wiring (vibey-gh check, hook half)"
        ok, problems = self._checker(self._cfg, local=True)
        if ok:
            return SetupStep(
                name,
                "unchanged",
                "verified: core.hooksPath and the hooks are as the repository declares",
            )
        return SetupStep(name, "failed", "\n".join(problems))

    def _postgres(self, *, install_server: bool) -> SetupStep:
        name = "PostgreSQL for the test suite"
        if install_server:
            done = self._runner.run(["uv", "run", "vibey", "install", "--postgres"], self._cfg.root)
            if done.returncode != 0:
                return SetupStep(
                    name, "failed", f"vibey install --postgres failed\n{self._tail(done)}"
                )
        dsn = self._environ.get(TEST_DSN_VARIABLE) or (
            f"postgresql://{self._environ.get('USER') or getpass.getuser()}@localhost:5432/vibey_test"
        )
        parts = urlsplit(dsn)
        host, port = parts.hostname or "localhost", parts.port or 5432
        if self._which("psql") is None:
            if not self._connect(host, port):
                return SetupStep(
                    name, "failed", self._postgres_help(f"nothing is listening on {host}:{port}")
                )
            return SetupStep(
                name,
                "unknown",
                f"{host}:{port} accepts connections, but psql was not found, so the role, its "
                "CREATEDB right and the vibey_test database were not checked",
            )
        env = {
            "PGHOST": host,
            "PGPORT": str(port),
            "PGDATABASE": (parts.path or "/vibey_test").lstrip("/") or "vibey_test",
            "PGCONNECT_TIMEOUT": "5",
        }
        if parts.username:
            env["PGUSER"] = unquote(parts.username)
        if parts.password:
            env["PGPASSWORD"] = unquote(parts.password)  # via the environment, never argv
        done = self._runner.run(
            [
                "psql",
                "-X",
                "-w",
                "-tA",
                "-c",
                "select rolcreatedb from pg_roles where rolname = current_user",
            ],
            self._cfg.root,
            env,
        )
        if done.returncode != 0:
            first = (done.output.splitlines() or ["psql failed"])[0]
            return SetupStep(name, "failed", self._postgres_help(first))
        if done.stdout.strip() == "t":
            return SetupStep(
                name,
                "done" if install_server else "unchanged",
                f"connected to {env['PGDATABASE']} on {host}:{port}; the role can create databases",
            )
        return SetupStep(
            name, "failed", self._postgres_help("connected, but the role cannot create databases")
        )

    def _doctor(self) -> SetupStep:
        done = self._runner.run(["uv", "run", "vibey", "doctor"], self._cfg.root)
        body = done.output or "(no output)"
        return SetupStep(
            "vibey doctor",
            "advisory",
            f"exit {done.returncode}; shown in full, not counted: lines about the Sabbath "
            f"location, the supervisor and host health concern an operator's machine\n{body}",
        )

    # ------------------------------------------------------------------------------ helpers

    def _git_config(self, *scope: str) -> str | None:
        done = self._runner.run(
            ["git", "config", *scope, "--get", "core.hooksPath"], self._cfg.root
        )
        value = done.stdout.strip()
        return value if done.returncode == 0 and value else None

    def _porcelain(self) -> set[str]:
        done = self._runner.run(
            ["git", "status", "--porcelain", "--untracked-files=no"], self._cfg.root
        )
        return {line[3:] for line in done.stdout.splitlines() if len(line) > 3}

    @staticmethod
    def _tail(done: CommandResult, lines: int = 8) -> str:
        return "\n".join(done.output.splitlines()[-lines:]) or f"exit {done.returncode}"

    @staticmethod
    def _postgres_help(reason: str) -> str:
        return "\n".join([reason, "To set it up:", *(f"  {line}" for line in POSTGRES_HELP)])

    @staticmethod
    def _tcp_open(host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=3):
                return True
        except OSError:
            return False
