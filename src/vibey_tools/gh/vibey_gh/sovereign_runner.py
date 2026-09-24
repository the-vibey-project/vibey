# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sovereign review runner, stood up from the tree (sub-doctrine 12.c).

`[pr_automation.fallback]` schedules the sovereign review onto a self-hosted runner, and
`vibey-gh sovereign` reads the heartbeat that says one is up. The runner itself -- its
supervisor, its image, the LaunchAgent that keeps it alive -- used to exist only in one
operator's home directory, hand-written, and it rotted there: every agent kept pointing at
repositories the monorepo had absorbed, and its credential lived in a keyring launchd
cannot read. This module is that machine declared: it renders every file from `[runners]`
and the templates beside it, and reconciles the host against them.

Three rules shape it:

- **Nothing is loaded or unloaded unasked.** `install` writes files; it touches launchd only
  with `load=True`. `remove` and `uninstall` only describe what they would do until
  `apply=True`. launchctl is a seam, so every path is exercised without a real launchd.
- **Removal never deletes a unit.** A retired agent is unloaded and its plist moved aside
  into `<install_dir>/retired-units/`, from where it can be put back. `uninstall` deletes
  only the files an install wrote, which the tree can render again.
- **The credential is checked, never read out.** `credential_problems` says why the runner's
  own gh login is unusable by launchd and never includes the token in what it says.
"""

from __future__ import annotations

import json
import os
import plistlib
import re
import shlex
import stat
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from vibey_gh.config import GhConfig

__all__ = [
    "PAT_PERMISSION",
    "RETIRED_DIR",
    "TEMPLATES",
    "LaunchAgentUnit",
    "RegisteredRunner",
    "RunnerFile",
    "RunnerPlan",
    "SovereignRunner",
]

TEMPLATES = Path(__file__).parent / "templates" / "runner"
# The one repository permission the runner's fine-grained token needs: minting a
# registration token and deleting a stale runner are Administration write, and listing
# runners is Administration read (GitHub's "Permissions required for fine-grained personal
# access tokens"). Named once, so the CLI, the refusal and the runbook cannot disagree.
PAT_PERMISSION = "Administration: Read and write"
RETIRED_DIR = "retired-units"
_RUNNERS_JQ = ".runners[] | {name, status, busy, labels: [.labels[].name]}"
# The same listing, one JSON object per line, for a program to read rather than a person.
_RUNNER_LINES_JQ = f"{_RUNNERS_JQ} | tojson"
_NO_AMBIENT_TOKEN = "env -u GH_TOKEN -u GITHUB_TOKEN"
# A token gh wrote into hosts.yml itself (`--insecure-storage`). Without the flag gh writes
# the user entry and keeps the token in the keyring, so this key is simply absent. The same
# pattern the supervisor greps for.
_STORED_TOKEN = re.compile(r"^[ \t]+oauth_token:[ \t]*\S", re.MULTILINE)

# The environment variables gh prefers over any stored login. Stripped from every gh call
# made on the runner's behalf, so the answer is about the dedicated login and nothing else.
_AMBIENT_TOKENS = ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN")

Launchctl = Callable[[tuple[str, ...]], tuple[int, str]]
GhStatus = Callable[[tuple[str, ...], dict[str, str]], int]
GhRead = Callable[[tuple[str, ...], dict[str, str]], tuple[int, str]]


@dataclass(frozen=True)
class RunnerFile:
    """One file an install writes."""

    path: Path
    text: str
    executable: bool = False


@dataclass(frozen=True)
class RunnerPlan:
    """Everything one install writes, resolved against one home directory."""

    label: str
    repository: str
    repo_url: str
    plist: Path
    files: tuple[RunnerFile, ...]


@dataclass(frozen=True)
class RegisteredRunner:
    """One self-hosted runner as GitHub lists it for the repository."""

    name: str
    online: bool
    busy: bool
    labels: tuple[str, ...]


@dataclass(frozen=True)
class LaunchAgentUnit:
    """An installed LaunchAgent as its own plist describes it."""

    path: Path
    label: str
    repo_url: str


class SovereignRunner:
    """Renders, installs, checks and removes the runner `[runners]` declares."""

    def __init__(
        self,
        cfg: GhConfig,
        *,
        home: Path,
        uid: int,
        templates: Path | None = None,
        launchctl: Launchctl | None = None,
        gh: GhStatus | None = None,
        gh_read: GhRead | None = None,
    ) -> None:
        self._cfg = cfg
        self._runners = cfg.runners
        self._home = home
        self._uid = uid
        self._templates = templates or TEMPLATES
        self._launch = launchctl or self._launchctl
        self._gh = gh or self._gh_status
        self._gh_read = gh_read or self._gh_output

    # --- paths ----------------------------------------------------------------------------

    def _expand(self, declared: str) -> Path:
        return self._home / declared[2:] if declared.startswith("~/") else Path(declared)

    @property
    def _install_dir(self) -> Path:
        return self._expand(self._runners.install_dir)

    @property
    def _gh_dir(self) -> Path:
        return self._expand(self._runners.gh_config_dir)

    @property
    def _agents_dir(self) -> Path:
        return self._expand(self._runners.launch_agents_dir)

    # --- rendering ------------------------------------------------------------------------

    def render(self) -> tuple[RunnerPlan | None, str]:
        fallback = self._cfg.pr_automation.fallback
        if not fallback.enabled:
            return None, (
                "[pr_automation.fallback] is disabled, so no workflow schedules onto a"
                " sovereign runner; enable it before installing one"
            )
        slug, url, problem = self._runners.registration(self._cfg.platform)
        if problem:
            return None, problem
        if self._runners.shares_operator_gh_dir(self._home, os.environ):
            return None, (
                f"runners.gh_config_dir resolves to gh's default directory"
                f" ({self._runners.resolved_gh_config_dir(self._home)}), the operator's own"
                " login; give the runner a directory of its own"
            )
        label = f"{self._runners.unit_prefix}-{slug.split('/')[1]}"
        install = self._install_dir
        plist = self._agents_dir / f"{label}.plist"
        values = {
            "__LABEL__": label,
            "__SUPERVISOR__": str(install / "vibey-runner.sh"),
            "__INSTALL_DIR__": str(install),
            "__REPO_URL__": url,
            "__RUNNER_LABEL__": fallback.runner_label,
            "__IMAGE__": self._runners.image,
            "__MODEL_URL__": fallback.base_url,
            "__CONTAINER_MODEL_URL__": self._runners.container_model_url,
            "__REQUIRE_AC__": "1" if self._runners.require_ac else "0",
            "__MAX_FAILURES__": str(self._runners.max_failures),
            "__GH_CONFIG_DIR__": str(self._gh_dir),
            "__PATH__": self._runners.path,
            "__THROTTLE__": str(self._runners.throttle_seconds),
            "__LOG__": str(self._expand(self._runners.log_dir) / f"{label}.log"),
        }
        agent = self._read("launch-agent.plist")
        for placeholder, value in values.items():
            agent = agent.replace(placeholder, escape(value))
        files = (
            RunnerFile(plist, agent),
            RunnerFile(install / "Dockerfile", self._read("Dockerfile")),
            RunnerFile(install / "entrypoint.sh", self._read("entrypoint.sh"), True),
            RunnerFile(install / "vibey-runner.sh", self._read("vibey-runner.sh"), True),
        )
        return RunnerPlan(label, slug, url, plist, files), ""

    def _read(self, name: str) -> str:
        return (self._templates / name).read_text(encoding="utf-8")

    # --- install and verify ---------------------------------------------------------------

    def install(self, plan: RunnerPlan, *, load: bool) -> tuple[list[str], bool]:
        lines = []
        for rendered in plan.files:
            rendered.path.parent.mkdir(parents=True, exist_ok=True)
            rendered.path.write_text(rendered.text, encoding="utf-8")
            rendered.path.chmod(0o755 if rendered.executable else 0o644)
            lines.append(f"wrote {rendered.path}")
        if load:
            # Unloading first makes a re-install pick up the new plist; "not loaded" is the
            # expected answer on a first install, so its status is not a failure.
            self._launch(("launchctl", "bootout", f"gui/{self._uid}/{plan.label}"))
            code, output = self._launch(
                ("launchctl", "bootstrap", f"gui/{self._uid}", str(plan.plist))
            )
            lines.append(
                f"loaded {plan.label} from {plan.plist}"
                if code == 0
                else f"launchctl bootstrap failed (exit {code}): {output}"
            )
            return lines, code == 0
        return lines, True

    def next_steps(self, plan: RunnerPlan) -> list[str]:
        """Shell commands, every path and value quoted: `[runners]` paths may hold spaces."""
        q = shlex.quote
        host = q(self._host(plan))
        gh_dir = q(str(self._gh_dir))
        gh = f"{_NO_AMBIENT_TOKEN} GH_CONFIG_DIR={gh_dir}"
        version = q(self._runners.runner_version)
        target = f"gui/{self._uid}"
        return [
            f"mkdir -m 700 -p {gh_dir}",
            f"{gh} gh auth login --hostname {host} --with-token --insecure-storage",
            (
                f"docker build --build-arg RUNNER_VERSION={version}"
                f" -t {q(self._runners.image)} {q(str(self._install_dir))}"
            ),
            (
                f"launchctl bootout {q(f'{target}/{plan.label}')} 2>/dev/null;"
                f" launchctl bootstrap {target} {q(str(plan.plist))}"
            ),
            "vibey-gh runner check",
            (
                f"{gh} gh api --hostname {host}"
                f" {q(f'repos/{plan.repository}/actions/runners')} --jq {q(_RUNNERS_JQ)}"
            ),
        ]

    @staticmethod
    def _host(plan: RunnerPlan) -> str:
        return plan.repo_url.split("/")[2]

    def check(self, plan: RunnerPlan) -> list[str]:
        problems = []
        for rendered in plan.files:
            if not rendered.path.is_file():
                problems.append(f"missing: {rendered.path}")
            elif rendered.path.read_text(encoding="utf-8") != rendered.text:
                problems.append(f"drift: {rendered.path}")
            elif rendered.executable and not rendered.path.stat().st_mode & stat.S_IXUSR:
                problems.append(f"not executable: {rendered.path}")
        return problems + [f"credential: {p}" for p in self.credential_problems(plan)]

    def credential_problems(self, plan: RunnerPlan) -> list[str]:
        """The supervisor's rule, ending as it does: GitHub itself must accept the token.

        The last step runs `gh auth status --hostname <host>` under the dedicated
        `GH_CONFIG_DIR` with every ambient token stripped. Its output is captured and
        discarded, so neither the token nor gh's description of it reaches the caller.
        """
        directory = self._gh_dir
        if not directory.is_dir():
            return [f"{directory} does not exist; create it and log in (vibey-gh runner install)"]
        hosts = directory / "hosts.yml"
        if not hosts.is_file():
            return [f"{directory} holds no gh login (no hosts.yml)"]
        if not _STORED_TOKEN.search(hosts.read_text(encoding="utf-8")):
            keyring = (
                f"{hosts} holds no token of its own: it went to the macOS keyring, which a"
                " LaunchAgent cannot read; log in again with --insecure-storage"
            )
            return [keyring]
        if hosts.stat().st_mode & (stat.S_IRGRP | stat.S_IROTH):
            return [f"{hosts} is readable by other users; run: chmod 600 {hosts}"]
        host = self._host(plan)
        env = {k: v for k, v in os.environ.items() if k not in _AMBIENT_TOKENS}
        env["GH_CONFIG_DIR"] = str(directory)
        if self._gh(("gh", "auth", "status", "--hostname", host), env) != 0:
            rejected = (
                f"the token in {directory} is not accepted by {host} (expired, revoked, or"
                " stored for another host); log in again"
            )
            return [rejected]
        return []

    def _runner_env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in _AMBIENT_TOKENS}
        env["GH_CONFIG_DIR"] = str(self._gh_dir)
        return env

    def registered_runners(self, plan: RunnerPlan) -> tuple[tuple[RegisteredRunner, ...], str]:
        """Every runner GitHub lists for the plan's repository, read with the runner's OWN
        login: `GH_CONFIG_DIR` is `gh_config_dir` and every ambient token is stripped, so the
        answer is about the credential the runner itself uses -- the one that holds the
        Administration permission the runners API needs. Only gh's exit status and standard
        output are read; its standard error, which may describe the credential, never is.
        """
        repository = plan.repository
        argv = (
            "gh",
            "api",
            "--hostname",
            self._host(plan),
            "--paginate",
            f"repos/{repository}/actions/runners",
            "--jq",
            _RUNNER_LINES_JQ,
        )
        code, out = self._gh_read(argv, self._runner_env())
        if code != 0:
            return (), (
                f"could not list the runners registered with {repository} using the runner's"
                f" own login in {self._gh_dir} (gh exited {code}); vibey-gh runner check says why"
            )
        runners = []
        for line in out.splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                runners.append(
                    RegisteredRunner(
                        str(entry["name"]),
                        entry["status"] == "online",
                        bool(entry["busy"]),
                        tuple(str(label) for label in entry["labels"]),
                    )
                )
            except (ValueError, KeyError, TypeError):
                return (), f"the runner listing for {repository} was not the JSON asked for"
        return tuple(runners), ""

    @staticmethod
    def heartbeat_label(unit_prefix: str, repository: str) -> str:
        """The heartbeat timer's unit label for `owner/name`: under the same prefix as the
        runner's, so `cleanup` retires the timer of a repository the tree stopped declaring,
        and never the one it still declares."""
        return f"{unit_prefix}-heartbeat-{repository.split('/')[1]}"

    # --- removal --------------------------------------------------------------------------

    def strays(self, plan: RunnerPlan) -> tuple[LaunchAgentUnit, ...]:
        prefix = self._runners.unit_prefix
        found = []
        agents = self._agents_dir
        for path in sorted(agents.iterdir()) if agents.is_dir() else []:
            name = path.name
            if path.suffix != ".plist" or not name.startswith(prefix):
                continue
            if path in (
                plan.plist,
                agents / f"{self.heartbeat_label(prefix, plan.repository)}.plist",
            ):
                continue
            if name[len(prefix)] not in "-.":
                continue  # a different prefix that merely starts the same way
            found.append(self._describe(path))
        return tuple(found)

    @staticmethod
    def _describe(path: Path) -> LaunchAgentUnit:
        try:
            body = plistlib.loads(path.read_bytes())
        except (plistlib.InvalidFileException, ValueError):
            body = {}
        env = body.get("EnvironmentVariables", {})
        return LaunchAgentUnit(
            path, str(body.get("Label", path.stem)), env.get("VIBEY_REPO_URL", "")
        )

    def remove(self, units: Sequence[LaunchAgentUnit], *, apply: bool) -> list[str]:
        if not units:
            return ["nothing to remove"]
        retired = self._install_dir / RETIRED_DIR
        lines = []
        for unit in units:
            target = self.free_name(retired, unit.path)
            serves = f" [serves {unit.repo_url}]" if unit.repo_url else ""
            if not apply:
                lines.append(
                    f"would unload {unit.label} (launchctl bootout gui/{self._uid}/{unit.label})"
                    f" and move {unit.path} to {target}{serves}"
                )
                continue
            code, output = self._launch(("launchctl", "bootout", f"gui/{self._uid}/{unit.label}"))
            lines.append(
                f"unloaded {unit.label}"
                if code == 0
                else f"{unit.label} was not loaded (launchctl: {output})"
            )
            retired.mkdir(parents=True, exist_ok=True)
            os.rename(unit.path, target)
            lines.append(f"moved {unit.path} to {target}")
        return lines

    @staticmethod
    def free_name(retired: Path, path: Path) -> Path:
        """The first name under `retired` nothing holds yet: an earlier copy is never replaced.

        Re-running cleanup after an agent was restored and retired again must keep the
        first copy, because that copy may be the only way back.
        """
        target = retired / path.name
        n = 0
        while target.exists():
            n += 1
            target = retired / f"{path.stem}.{n}{path.suffix}"
        return target

    def uninstall(self, plan: RunnerPlan, *, apply: bool) -> list[str]:
        lines = []
        if plan.plist.is_file():
            lines += self.remove((self._describe(plan.plist),), apply=apply)
        for rendered in plan.files[1:]:
            if not rendered.path.is_file():
                continue
            if apply:
                rendered.path.unlink()
                lines.append(f"deleted {rendered.path}")
            else:
                lines.append(f"would delete {rendered.path}")
        return lines or ["nothing to remove"]

    # --- the default seams ----------------------------------------------------------------

    @staticmethod
    def _gh_status(argv: tuple[str, ...], env: dict[str, str]) -> int:
        """Run gh with its output captured and dropped; only the exit status leaves."""
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                argv, capture_output=True, text=True, check=False, timeout=60, env=env
            )
        except OSError:
            return 127
        return done.returncode

    @staticmethod
    def _gh_output(argv: tuple[str, ...], env: dict[str, str]) -> tuple[int, str]:
        """Run gh and keep its exit status and standard output; standard error is dropped."""
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                argv, capture_output=True, text=True, check=False, timeout=60, env=env
            )
        except (OSError, subprocess.TimeoutExpired):
            return 127, ""
        return done.returncode, done.stdout

    @staticmethod
    def _launchctl(argv: tuple[str, ...]) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                argv, capture_output=True, text=True, check=False, timeout=60
            )
        except OSError as exc:
            return 127, str(exc)
        return done.returncode, (done.stdout + done.stderr).strip()
