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

import plistlib
import re
import shutil
import stat
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from vibey_gh.config import GhConfig

__all__ = [
    "PAT_PERMISSION",
    "TEMPLATES",
    "LaunchAgentUnit",
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
_RUNNERS_JQ = "'.runners[] | {name, status, busy, labels: [.labels[].name]}'"
_NO_AMBIENT_TOKEN = "env -u GH_TOKEN -u GITHUB_TOKEN"
# A token gh wrote into hosts.yml itself (`--insecure-storage`). Without the flag gh writes
# the user entry and keeps the token in the keyring, so this key is simply absent. The same
# pattern the supervisor greps for.
_STORED_TOKEN = re.compile(r"^[ \t]+oauth_token:[ \t]*\S", re.MULTILINE)

Launchctl = Callable[[tuple[str, ...]], tuple[int, str]]


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
    ) -> None:
        self._cfg = cfg
        self._runners = cfg.runners
        self._home = home
        self._uid = uid
        self._templates = templates or TEMPLATES
        self._launch = launchctl or self._launchctl

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

    def install(self, plan: RunnerPlan, *, load: bool) -> list[str]:
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
        return lines

    def next_steps(self, plan: RunnerPlan) -> list[str]:
        host = plan.repo_url.split("/")[2]
        gh = f"{_NO_AMBIENT_TOKEN} GH_CONFIG_DIR={self._gh_dir}"
        return [
            f"mkdir -m 700 -p {self._gh_dir}",
            f"{gh} gh auth login --hostname {host} --with-token --insecure-storage",
            (
                f"docker build --build-arg RUNNER_VERSION={self._runners.runner_version}"
                f" -t {self._runners.image} {self._install_dir}"
            ),
            (
                f"launchctl bootout gui/{self._uid}/{plan.label} 2>/dev/null;"
                f" launchctl bootstrap gui/{self._uid} {plan.plist}"
            ),
            "vibey-gh runner check",
            f"{gh} gh api repos/{plan.repository}/actions/runners --jq {_RUNNERS_JQ}",
        ]

    def check(self, plan: RunnerPlan) -> list[str]:
        problems = []
        for rendered in plan.files:
            if not rendered.path.is_file():
                problems.append(f"missing: {rendered.path}")
            elif rendered.path.read_text(encoding="utf-8") != rendered.text:
                problems.append(f"drift: {rendered.path}")
            elif rendered.executable and not rendered.path.stat().st_mode & stat.S_IXUSR:
                problems.append(f"not executable: {rendered.path}")
        return problems + [f"credential: {p}" for p in self.credential_problems()]

    def credential_problems(self) -> list[str]:
        """The same rule the supervisor enforces, read from Python for `runner check`."""
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
        return []

    # --- removal --------------------------------------------------------------------------

    def strays(self, plan: RunnerPlan) -> tuple[LaunchAgentUnit, ...]:
        prefix = self._runners.unit_prefix
        found = []
        agents = self._agents_dir
        for path in sorted(agents.iterdir()) if agents.is_dir() else []:
            name = path.name
            if path == plan.plist or path.suffix != ".plist" or not name.startswith(prefix):
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
            target = retired / unit.path.name
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
            shutil.move(unit.path, target)
            lines.append(f"moved {unit.path} to {target}")
        return lines

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

    # --- the default launchctl seam -------------------------------------------------------

    @staticmethod
    def _launchctl(argv: tuple[str, ...]) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 - a fixed argv, never a shell
                argv, capture_output=True, text=True, check=False, timeout=60
            )
        except OSError as exc:
            return 127, str(exc)
        return done.returncode, (done.stdout + done.stderr).strip()
