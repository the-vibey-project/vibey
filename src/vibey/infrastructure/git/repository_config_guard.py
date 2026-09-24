# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Refuse a repository whose own config names a program for vibey's git to run.

`CleanGitEnvSubprocessExecutor` switches hooks and the file-system monitor off for every
git call vibey makes. Filter and merge drivers cannot be switched off that way: git runs
the driver a `.gitattributes` line names (`* filter=x`, `* merge=x`), the driver is
defined in config under a name the repository chooses (`filter.x.smudge`,
`merge.x.driver`), and there is no single option that disables them all. An engine
session in a linked worktree can write both halves -- the attributes file in its
branch, the definition in the shared config.

So before vibey checks a branch out or merges one, this guard reads the config git will
use there (`git config --list --show-scope -z`, which follows includes) and refuses when
the REPOSITORY's own scopes -- `local` (the shared `.git/config`) and `worktree` --
declare a driver. The refusal is an error that fails the job, never a silent skip; the
operator moves a driver they really need into their global config, which the
repository cannot write. A config that cannot be read is refused too: a guard that
passes on an error guards nothing.

Declared by `interfaces/repository_config_guard_interface.py` (ADR-0016).
"""

import re
from pathlib import Path

from vibey.domain.errors import VibeyError
from vibey.infrastructure.interfaces import CommandExecutor

# The scopes a repository controls. `global` is the operator's own file; `system` is not
# read at all (GIT_CONFIG_NOSYSTEM); `command` is vibey's own `-c`.
REPOSITORY_SCOPES: frozenset[str] = frozenset({"local", "worktree"})

# Keys whose value is a program git runs during a checkout or a merge.
REFUSED_KEYS: tuple[re.Pattern[str], ...] = (
    re.compile(r"filter\..+\.(clean|smudge|process)", re.IGNORECASE),
    re.compile(r"merge\..+\.driver", re.IGNORECASE),
)


class RepositoryExecutionRefused(VibeyError):
    """The repository's own config names a program vibey's git would have run."""

    def __init__(self, directory: Path, keys: tuple[str, ...], *, reason: str = "") -> None:
        self.directory = directory
        self.keys = keys
        what = reason or f"its own config declares {', '.join(keys)}, a program git would run here"
        super().__init__(
            f"refusing to run git in {directory}: {what}. A repository's config may not "
            "name a filter or merge driver for vibey's own git calls; declare one you "
            "need in your global git config instead (SECURITY.md §5)."
        )


class RepositoryConfigGuard:
    """Checks the config git would use in a directory before vibey checks out or merges
    there. Declared by `interfaces/repository_config_guard_interface.py`."""

    __slots__ = ("_executor",)

    def __init__(self, executor: CommandExecutor) -> None:
        self._executor = executor

    async def check(self, directory: Path) -> None:
        result = await self._executor.execute(
            ("git", "-C", str(directory), "config", "--list", "--show-scope", "-z")
        )
        if result.returncode != 0:
            raise RepositoryExecutionRefused(
                directory,
                (),
                reason=f"its config could not be read ({result.stderr.strip()})",
            )
        offending = self.offending(result.stdout)
        if offending:
            raise RepositoryExecutionRefused(directory, offending)

    def offending(self, listing: str) -> tuple[str, ...]:
        # `-z` prints `scope NUL key LF value NUL` per entry (`key NUL` when valueless).
        tokens = listing.split("\0")
        refused: list[str] = []
        for scope, entry in zip(tokens[0::2], tokens[1::2], strict=False):
            key = entry.split("\n", 1)[0]
            if scope in REPOSITORY_SCOPES and any(p.fullmatch(key) for p in REFUSED_KEYS):
                refused.append(key)
        return tuple(dict.fromkeys(refused))
