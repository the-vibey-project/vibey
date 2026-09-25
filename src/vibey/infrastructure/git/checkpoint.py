# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ULTRA checkpoint (ADR-0063): after a done verdict, everything in the item's
worktree is committed on its branch, so the next pass -- which re-creates the worktree
from that branch -- starts from this pass's work rather than losing it.

Git runs through the clean-environment executor every worktree operation uses, as vibey
itself: the commit is vibey's record of the pass, whoever the engine was.
"""

from pathlib import Path
from typing import Final

from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.interfaces import CommandExecutor

_IDENTITY: Final = ("-c", "user.name=vibey", "-c", "user.email=vibey@localhost")


class GitCheckpointError(RuntimeError):
    """A git step of a checkpoint failed; its stderr is the message."""


class GitCheckpoint:
    """Declared by `interfaces/checkpoint_interface.py`."""

    def __init__(self, executor: CommandExecutor | None = None) -> None:
        self._executor = executor or CleanGitEnvSubprocessExecutor()

    async def commit(self, worktree_path: Path, message: str) -> str | None:
        where = ("git", "-C", str(worktree_path))
        await self._run((*where, "add", "--all"))
        staged = await self._executor.execute((*where, "diff", "--cached", "--quiet"))
        if staged.returncode == 0:
            return None
        # --no-verify: this is vibey's own record of a pass on the item's worktree branch,
        # never a protected branch; the pass's checks run next as build.verify (12.d).
        await self._run((*where, *_IDENTITY, "commit", "--no-verify", "-m", message))
        return (await self._run((*where, "rev-parse", "HEAD"))).strip()

    async def _run(self, argv: tuple[str, ...]) -> str:
        result = await self._executor.execute(argv)
        if result.returncode != 0:
            raise GitCheckpointError(f"{' '.join(argv[3:])}: {result.stderr.strip()}")
        return str(result.stdout)
