# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fetches a git marketplace into a staging folder, git held on a short lead (SP-LOOPS Task 7).

Only `vibey loops marketplace update` calls this, on the person's word; a run never fetches. The
source was classified by `MarketplaceSourceRule` (https, or ssh as `ssh://` or scp-like
`user@host:path`; never `git://`, a transport helper, a local path or an option), and git is held to that again here:

- **Four commands, nothing else.** `git init --template=` (no hooks or other template files), a
  shallow `git fetch --depth=1 --no-tags --no-recurse-submodules -- <source> <ref>` of the one pinned
  ref (or `HEAD`), `git checkout --detach FETCH_HEAD --` and `git rev-parse --verify HEAD`. The
  source and the ref always come after `--`, and a ref is checked again (`check_ref`), so neither
  can be read as an option. A full commit id as the ref must be the commit fetched.
- **Only two protocols.** Every call carries `-c protocol.allow=never` with `https` and `ssh`
  allowed one by one, and `GIT_ALLOW_PROTOCOL=https:ssh` (which git puts above any
  configuration): `git://`, `ext::`, `file://`, `fd::` and every other helper are refused by git
  as well.
- **As little of the person's configuration as works.** `GIT_CONFIG_GLOBAL` and
  `GIT_CONFIG_SYSTEM` are the null device and `GIT_CONFIG_NOSYSTEM` is set, so on git 2.32 or later
  (where `GIT_CONFIG_GLOBAL` exists) no `url.<base>.insteadOf` can rewrite the source and no
  credential helper or alias applies. For an https source `HOME` is also an empty 0700 folder made
  for the fetch, so neither `~/.gitconfig` (on any git) nor `~/.netrc` (which git's HTTP transport
  reads) is read: a private repository needs ssh. An ssh source keeps the person's `HOME` and
  `SSH_AUTH_SOCK`, which ssh needs for its keys and known hosts; a git older than 2.32 then still
  reads `~/.gitconfig`, though the protocol limits above hold whatever it says. Hooks point at the
  null device, submodules are never recursed, `core.fsmonitor` is off, LFS never smudges, received
  objects are checked (`transfer.fsckObjects`).
- **A scrubbed environment.** git sees `PATH`, and for ssh `HOME` and `SSH_AUTH_SOCK`, from this
  process and nothing else -- no `GIT_*` variable, no token, no key -- plus the fixed settings
  above, `GIT_TERMINAL_PROMPT=0` and ssh in batch mode, so nothing waits on a prompt.
- **One deadline, bounded output.** The four calls share `timeout_seconds` (300 by default) by a
  monotonic clock; a call that would start past it does not start. Each call runs through
  `BoundedProcessRunner`: in a process group of its own, killed whole on a timeout, its output read
  back capped at 64 KiB.

The checkout's `.git` is removed before the tree is handed back: the store keeps content only.
Declared by `interfaces/marketplace_fetcher_interface.py::MarketplaceFetcherInterface`.
"""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404 - names the timeout and result types; BoundedProcessRunner runs git
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final

from vibey.domain.interfaces.marketplace_source_interface import MarketplaceSourceRuleInterface
from vibey.domain.marketplace_source import (
    GIT_PROTOCOLS,
    MARKETPLACE_SOURCE_RULE,
    MarketplaceSource,
    MarketplaceSourceError,
)
from vibey.infrastructure.loops.bounded_process_runner import BoundedProcessRunner
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.records import FetchResult

GitRunner = Callable[
    [Sequence[str], Mapping[str, str], Path, float], subprocess.CompletedProcess[str]
]
ALLOWED_PROTOCOLS: Final = GIT_PROTOCOLS
TIMEOUT_SECONDS: Final = 300.0
"""How long one `marketplace update` may spend in git, all four calls together."""
STDERR_CHARS: Final = 500
"""The most of git's last words an error quotes."""
SSH_PASSED_THROUGH: Final = ("HOME", "SSH_AUTH_SOCK")
"""The only variables of this process git sees for an ssh source, besides `PATH`; an https source
sees only `PATH` and an empty `HOME` of its own."""


class GitMarketplaceFetcher:
    """Declared by `interfaces/marketplace_fetcher_interface.py::MarketplaceFetcherInterface`."""

    def __init__(
        self,
        *,
        runner: GitRunner | None = None,
        environ: Mapping[str, str] | None = None,
        git: str = "git",
        timeout_seconds: float = TIMEOUT_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        rule: MarketplaceSourceRuleInterface = MARKETPLACE_SOURCE_RULE,
    ) -> None:
        self._runner = runner or BoundedProcessRunner().run
        self._environ = os.environ if environ is None else environ
        self._git = git
        self._timeout = timeout_seconds
        self._clock = clock
        self._rule = rule

    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        if source.kind != "git":
            raise MarketplaceFetchError(f"{source.text} is not a git source")
        try:
            wanted = "HEAD" if ref is None else self._rule.check_ref(ref)
        except MarketplaceSourceError as exc:
            raise MarketplaceFetchError(str(exc)) from exc
        try:
            into.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise MarketplaceFetchError(f"the staging folder {into} already exists") from exc
        home = None
        if source.protocol != "ssh":  # an https fetch reads no ~/.gitconfig and no ~/.netrc
            home = Path(tempfile.mkdtemp(prefix=".git-home-", dir=into.parent))
        try:
            return self._fetch(source, ref, wanted, into, self._environment(home))
        finally:
            if home is not None:
                shutil.rmtree(home, ignore_errors=True)

    def _fetch(
        self,
        source: MarketplaceSource,
        ref: str | None,
        wanted: str,
        into: Path,
        env: Mapping[str, str],
    ) -> FetchResult:
        deadline = self._clock() + self._timeout
        self._call(["init", "--quiet", "--template=", "."], into, env, deadline)
        self._call(
            [
                "fetch",
                "--quiet",
                "--depth=1",
                "--no-tags",
                "--no-recurse-submodules",
                "--",
                source.text,
                wanted,
            ],
            into,
            env,
            deadline,
        )
        self._call(["checkout", "--quiet", "--detach", "FETCH_HEAD", "--"], into, env, deadline)
        answer = self._call(["rev-parse", "--verify", "HEAD"], into, env, deadline)
        commit = answer.stdout.strip()
        if not self._rule.is_commit(commit):
            raise MarketplaceFetchError(f"git answered {commit[:80]!r}, which is not a commit id")
        if ref is not None and self._rule.is_commit(ref) and commit != ref:
            raise MarketplaceFetchError(f"git fetched {commit}, not the pinned {ref}")
        shutil.rmtree(into / ".git")
        return FetchResult(commit, ())

    def _call(
        self, arguments: Sequence[str], cwd: Path, env: Mapping[str, str], deadline: float
    ) -> subprocess.CompletedProcess[str]:
        left = deadline - self._clock()
        if left <= 0:
            raise self._late()
        argv = [self._git, *self._settings(), *arguments]
        try:
            result = self._runner(argv, env, cwd, left)
        except subprocess.TimeoutExpired as exc:
            raise self._late() from exc
        except FileNotFoundError as exc:
            raise MarketplaceFetchError(f"git is not installed ({self._git}: {exc})") from exc
        if result.returncode != 0:
            words = result.stderr.strip()[-STDERR_CHARS:]
            raise MarketplaceFetchError(
                f"git {arguments[0]} failed (exit {result.returncode}): {words}"
            )
        return result

    def _late(self) -> MarketplaceFetchError:
        return MarketplaceFetchError(f"git did not finish within {self._timeout:g} seconds")

    @staticmethod
    def _settings() -> list[str]:
        pairs = [
            "protocol.allow=never",
            *(f"protocol.{name}.allow=always" for name in ALLOWED_PROTOCOLS),
            f"core.hooksPath={os.devnull}",
            "core.fsmonitor=false",
            "submodule.recurse=false",
            "fetch.recurseSubmodules=false",
            "transfer.fsckObjects=true",
            "init.defaultBranch=main",
            "advice.detachedHead=false",
        ]
        return [part for pair in pairs for part in ("-c", pair)]

    def _environment(self, home: Path | None) -> dict[str, str]:
        environment = {"PATH": self._environ.get("PATH", os.defpath)}
        if home is None:
            environment.update(
                {n: self._environ[n] for n in SSH_PASSED_THROUGH if n in self._environ}
            )
        else:
            environment["HOME"] = str(home)
        environment.update(
            {
                "LANG": "C",
                "LC_ALL": "C",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_ALLOW_PROTOCOL": ":".join(ALLOWED_PROTOCOLS),
                "GIT_LFS_SKIP_SMUDGE": "1",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_SSH_COMMAND": "ssh -o BatchMode=yes",
            }
        )
        return environment
