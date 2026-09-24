# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The repository the heartbeat timer owns and pushes from (vibey ADR-0059).

The heartbeat used to be pushed from the operator's own checkout, through whatever pre-push
hook that checkout's branch happened to carry. On a branch without the scope rule that hook
chained straight to the full suite, which ran in the tree the operator was editing, every few
minutes, and timed out before a beat could land. A timer cannot depend on which branch a
person has checked out, so it owns a repository of its own:

- **no working tree** -- `git init`, nothing checked out -- so there is no code in it to
  judge, and nothing a lane ending or a `git clean` can take away;
- **the repository's remote**, as `[runners]` declares it, and **the runner's own
  credential**: `[runners] gh_config_dir` through `gh auth git-credential`, every ambient
  token stripped and every inherited credential helper reset, the file-based login a timer
  can read where a keyring cannot be;
- **its own pre-push gate**, rendered from the templates of the vibey-gh that installs it
  and running the interpreter the timer runs. `vibey-gh push-scope` -- the rule every
  checkout's gate applies -- decides whether a push is a heartbeat, and anything that is
  not is refused outright: there is no code here for the rest of the gate to test.
  `core.hooksPath` names the hook's directory, so no global hooks path can stand in for it;
- **the declaring checkout's `.vibey-gh.toml`**, copied at install, so a beat reads the same
  declared lane here that the tree declares, and `heartbeat status` calls it drift when the
  tree moves on.

Nothing in it is unique. `heartbeat install` creates or repairs every part from the tree;
`heartbeat status` checks every part, then hands the gate itself a synthetic heartbeat,
through the hook exactly as installed, and reports what it said.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from vibey_gh.config import CONFIG_NAME
from vibey_gh.interfaces.heartbeat_clone_interface import HeartbeatCloneInterface
from vibey_gh.push_scope import NO_CODE, NO_REPLACE_OBJECTS
from vibey_gh.sovereign_runner import AMBIENT_TOKENS

__all__ = ["GATE_PASSED", "HOOK_TEMPLATE", "HeartbeatClone"]

# The template, beside the timer's units, that the clone's pre-push gate is rendered from.
HOOK_TEMPLATE = "heartbeat-pre-push"
# What the clone's gate prints on standard error, and prints only, when its scope decision
# let a push through: the line `gate_check` looks for.
GATE_PASSED = f"pre-push: {NO_CODE}"

GitCommand = Callable[[Sequence[str], Path], tuple[int, str]]
HookRunner = Callable[[Sequence[str], Path, str, Mapping[str, str]], tuple[int, str]]

# The synthetic heartbeat the gate check hands the hook is made under this identity and never
# signed: it is never pushed, and a signing agent that prompts would hang the check.
_PROBE_IDENTITY = (
    "-c",
    "user.name=vibey-gh heartbeat check",
    "-c",
    "user.email=heartbeat-check@vibey-gh.invalid",
    "-c",
    "commit.gpgSign=false",
)
# Variables that choose which configuration git reads, not which repository it acts on: the
# only GIT_* variables a command addressed at the clone may inherit.
_CONFIG_VARIABLES = frozenset({"GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_CONFIG_NOSYSTEM"})
_COLOUR = re.compile(r"\x1b\[[0-9;]*m")
_HINT = (
    "the interpreter the timer runs must be a vibey-gh that knows `push-scope`; reinstall it"
    " from this tree (for example `uv tool install --force --from . vibey`) and install again"
)


class HeartbeatClone(HeartbeatCloneInterface):
    """Creates, repairs and checks the heartbeat's own repository; see the module docstring.

    `git` runs git in the clone and returns the exit status and the stripped standard
    output; `hook` runs the clone's pre-push hook with a standard input and an environment
    and returns its exit status and everything it printed. Both are seams for tests.
    """

    def __init__(
        self,
        path: Path,
        *,
        remote_url: str,
        gh_config_dir: Path,
        heartbeat_ref: str,
        path_env: str,
        git: GitCommand | None = None,
        hook: HookRunner | None = None,
    ) -> None:
        self._path = path
        self._remote_url = remote_url
        self._gh_dir = gh_config_dir
        self._ref = heartbeat_ref
        self._path_env = path_env
        self._git_seam = git or self._run_git
        self._hook_seam = hook or self._run_hook

    @property
    def path(self) -> Path:
        return self._path

    @property
    def hook_path(self) -> Path:
        return self._path / ".git" / "hooks" / "pre-push"

    @property
    def config_path(self) -> Path:
        return self._path / CONFIG_NAME

    def settings(self) -> dict[str, tuple[str, ...]]:
        unset = " ".join(f"-u {name}" for name in AMBIENT_TOKENS)
        directory = shlex.quote(str(self._gh_dir))
        helper = f"!env {unset} GH_CONFIG_DIR={directory} gh auth git-credential"
        return {
            "remote.origin.url": (self._remote_url,),
            "core.hooksPath": (str(self.hook_path.parent),),
            # The empty value first resets every helper the global and system configurations
            # named, URL-scoped ones included, so the push can use no credential but this.
            "credential.helper": ("", helper),
        }

    # --- create and repair ----------------------------------------------------------------

    def ensure(self) -> tuple[list[str], str]:
        lines: list[str] = []
        if not self._exists():
            self._path.mkdir(parents=True, exist_ok=True)
            code, _ = self._git("init", "-q")
            if code != 0:
                return lines, (
                    f"could not create the heartbeat's clone at {self._path} (git init exited"
                    f" {code})"
                )
            lines.append(f"created the heartbeat's clone at {self._path}")
        for key, values in self.settings().items():
            if self._local(key) == values:
                continue
            # Exit 5 is "nothing to unset", the ordinary answer on a first install.
            self._git("config", "--local", "--unset-all", key)
            for value in values:
                code, _ = self._git("config", "--local", "--add", key, value)
                if code != 0:
                    return lines, (
                        f"could not set {key} in {self._path} (git config exited {code})"
                    )
            lines.append(f"set {key} in {self._path}")
        return lines, ""

    # --- check ----------------------------------------------------------------------------

    def problems(self) -> list[str]:
        if not self._exists():
            missing = (
                f"missing: the heartbeat's clone {self._path} (vibey-gh heartbeat install"
                " creates it)"
            )
            return [missing]
        found = []
        for key, values in self.settings().items():
            held = self._local(key)
            if held != values:
                found.append(f"drift: {key} in {self._path} is {list(held)}, not {list(values)}")
        return found

    def gate_check(self) -> str:
        code, tree = self._git(NO_REPLACE_OBJECTS, "hash-object", "-t", "tree", "/dev/null")
        if code != 0 or not tree:
            return f"could not compute the empty tree in {self._path}"
        code, commit = self._git(
            *_PROBE_IDENTITY,
            "commit-tree",
            tree,
            "-m",
            "vibey-gh heartbeat check: a synthetic heartbeat, never pushed",
        )
        if code != 0 or not commit:
            return f"could not make a synthetic heartbeat in {self._path}"
        line = f"{commit} {commit} {self._ref} {'0' * len(commit)}\n"
        env = {key: value for key, value in self._environment().items() if key != "PYTHONPATH"}
        env["PATH"] = self._path_env
        argv = (str(self.hook_path), "origin", self._remote_url)
        code, said = self._hook_seam(argv, self._path, line, env)
        if code == 0 and GATE_PASSED in said.splitlines():
            return ""
        heard = " | ".join(
            text for text in (_COLOUR.sub("", raw).strip() for raw in said.splitlines()) if text
        )
        return (
            f"the clone's own pre-push gate did not let a synthetic heartbeat through (exit"
            f" {code}){': ' + heard[-400:] if heard else ''}; {_HINT}"
        )

    # --- git in the clone -----------------------------------------------------------------

    def _exists(self) -> bool:
        return (self._path / ".git").is_dir()

    def _git(self, *args: str) -> tuple[int, str]:
        return self._git_seam(args, self._path)

    def _local(self, key: str) -> tuple[str, ...]:
        """What the clone's own configuration holds for `key`, in order, empty values kept:
        `-z` ends each value with a NUL, so an empty one survives as an empty string."""
        code, held = self._git("config", "--local", "--get-all", "-z", key)
        if code != 0:
            return ()
        return tuple(held.split("\0")[:-1])

    @staticmethod
    def _environment() -> dict[str, str]:
        """This process's environment with every variable that would point git at another
        repository removed: the clone is addressed by its path and nothing else."""
        return {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("GIT_") or key in _CONFIG_VARIABLES
        }

    # --- the default seams ----------------------------------------------------------------

    @classmethod
    def _run_git(cls, args: Sequence[str], cwd: Path) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 B607 - a fixed argv, never a shell
                ["git", *args],
                cwd=cwd,
                env=cls._environment(),
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired):
            return 127, ""
        return done.returncode, done.stdout.strip()

    @staticmethod
    def _run_hook(
        argv: Sequence[str], cwd: Path, stdin: str, env: Mapping[str, str]
    ) -> tuple[int, str]:
        try:
            done = subprocess.run(  # nosec B603 - the clone's own hook, never a shell string
                list(argv),
                cwd=cwd,
                env=dict(env),
                input=stdin,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return 127, str(exc)
        return done.returncode, done.stdout + done.stderr
