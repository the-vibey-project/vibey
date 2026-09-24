# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The executor every one of vibey's own `git` calls goes through.

vibey runs git on repositories that engine sessions write to: an engine works in a
LINKED worktree of the project's repository, so it can write the repository's shared
plumbing -- `$(git rev-parse --git-common-dir)/hooks/*`, and the shared config's
`core.hooksPath`, `core.fsmonitor`, `filter.*` and `merge.*.driver`. Every git call vibey
makes afterwards (`git worktree add` runs post-checkout; the integration `git merge`
runs pre-merge-commit, prepare-commit-msg, commit-msg and post-merge) would run what the
engine planted, as the worker, with whatever the worker's environment holds. Until this
executor, that was `os.environ` minus `GIT_*`: `VIBEY_PG_URL` included.

**What this executor does, for every git call it runs:**

1. **The environment is allow-listed, never copied.** The system basics every process
   needs (`SYSTEM_ENVIRONMENT`: PATH, HOME, locale, temp directory, CA bundle, proxy,
   XDG directories) and nothing else -- no `VIBEY_*`, no libpq `PG*`, no token or cloud
   credential, no `GIT_*` from a surrounding hook (GIT_DIR et al. override `-C`
   outright and aim the call at the wrong repository). vibey's own Python environment
   is stripped from PATH, as for every other child. `GIT_CONFIG_NOSYSTEM=1` is set, so
   the machine-wide config is not read either.
2. **No hook runs.** `-c core.hooksPath=/dev/null` precedes every subcommand. Command-line
   config outranks every file scope, so this covers hooks planted in the common
   directory, in a worktree's own directory and behind a `core.hooksPath` set in any
   config file -- and git passes it on to every git process it starts itself (auto-gc
   included).
3. **No file-system monitor runs.** `-c core.fsmonitor=false`, for the same reason.

`IntegrationBranch` additionally merges with `--no-verify`. That is NOT skipping a gate:
vibey's gates run separately, in `SubprocessGateRunner`, before an item is integrated.
It switches off hooks the REPOSITORY planted in vibey's own internal merge plumbing --
the opposite of gate avoidance, and redundant with (2) on purpose.

**What `RepositoryConfigGuard` adds.** Filter drivers (`filter.<x>.clean|smudge|process`)
and merge drivers (`merge.<x>.driver`) cannot be switched off generically, because
their names are chosen by the repository. So before vibey checks a branch out
(`GitWorktreeManager.create`) or merges one (`IntegrationBranch.merge_item`), the guard
reads the config git will use there, and refuses -- loudly, failing the job -- when the
REPOSITORY's own scopes (`local`, `worktree`, and anything they include) declare one.
The operator's global config is left alone: `git lfs install` puts its filter there.

**What is not covered.**

- A program declared in the operator's global config (`~/.gitconfig`) still runs. An
  engine session runs as the same OS user and has HOME, so it can write that file; the
  same-user boundary is not a boundary (SECURITY.md §5). What it would run gets no
  vibey secret from this executor's environment, but it runs as the operator.
- `git diff HEAD` in BUILD verify runs through the gate runner, not here. It honours the
  repository's config like any gate command, with the gate environment (no DSN).
- `application/conformance.py`'s scratch-repository git calls (`vibey doctor
  --conformance`) are started by the application layer with the doctor's environment.
  The scratch repository is vibey's own, fresh, and operator-run; a global
  `core.hooksPath` would still apply there.

Declared by `interfaces/clean_env_interface.py` (ADR-0016).
"""

import asyncio
import os
from collections.abc import Mapping
from pathlib import PurePath

from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT, ChildEnvironment
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface

# git's own options that switch off what a repository can make vibey's git calls run.
# Placed before the subcommand, where they outrank every config file.
NEUTRALISING_OPTIONS: tuple[str, ...] = (
    "-c",
    f"core.hooksPath={os.devnull}",
    "-c",
    "core.fsmonitor=false",
)

# Set for every call on top of the system basics: the machine-wide config is not read.
GIT_ENVIRONMENT_OVERLAY: Mapping[str, str] = {"GIT_CONFIG_NOSYSTEM": "1"}


class CleanGitEnvSubprocessExecutor:
    """Runs one of vibey's own `git` commands. Satisfies
    `infrastructure/interfaces.CommandExecutor`; declared by
    `interfaces/clean_env_interface.py`.

    `environment` is the builder for the child's environment; the default is the system
    basics plus `GIT_ENVIRONMENT_OVERLAY`.
    """

    __slots__ = ("_environment",)

    def __init__(self, environment: ChildEnvironmentInterface | None = None) -> None:
        self._environment = (
            ChildEnvironment(SYSTEM_ENVIRONMENT, overlay=GIT_ENVIRONMENT_OVERLAY)
            if environment is None
            else environment
        )

    def neutralised(self, argv: tuple[str, ...]) -> tuple[str, ...]:
        if not argv or PurePath(argv[0]).name != "git":
            raise ValueError(
                f"the git executor runs git only, not {argv[:1]!r}; "
                "give another program an executor that declares its own environment"
            )
        return (argv[0], *NEUTRALISING_OPTIONS, *argv[1:])

    async def execute(self, argv: tuple[str, ...]) -> CommandResult:
        process = await asyncio.create_subprocess_exec(
            *self.neutralised(argv),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._environment.build(),
        )
        try:
            stdout, stderr = await process.communicate()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            raise
        return CommandResult(process.returncode or 0, stdout.decode(), stderr.decode())
