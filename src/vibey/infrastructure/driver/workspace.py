# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The worktree and the transcript, for the driver failover (ADR-0070).

Everything the driver writes lands under `<worktree>/.vibey/driver/`, on durable
storage beside the work (sub-doctrine 10.h), never in a temporary directory. Git is
read, never written: the sovereign engine commits, the driver only looks.
"""

import hashlib
import shutil
import subprocess  # nosec B404 -- fixed git argv, no shell
from pathlib import Path
from typing import Final

from vibey.application.dto import RepoSnapshot, TranscriptDigest

DRIVER_DIR: Final = Path(".vibey") / "driver"
GIT_TIMEOUT_SECONDS: Final = 30


class LocalDriverWorkspace:
    """Declared by `interfaces/workspace_interface.py`; satisfies `DriverWorkspacePort`."""

    def __init__(self, *, git: str = "git") -> None:
        self._git = git

    def digest(self, path: str) -> TranscriptDigest | None:
        try:
            data = Path(path).read_bytes()
        except OSError:
            return None
        return TranscriptDigest(sha256=hashlib.sha256(data).hexdigest(), lines=data.count(b"\n"))

    def copy_transcript(self, path: str, cwd: str, name: str) -> str:
        target = self._dir(cwd) / name
        shutil.copyfile(path, target)
        return str(target)

    def repo(self, cwd: str) -> RepoSnapshot:
        branch = self._git_out(cwd, "rev-parse", "--abbrev-ref", "HEAD")
        head = self._git_out(cwd, "rev-parse", "HEAD")
        status = self._git_out(cwd, "status", "--porcelain")
        dirty = tuple(
            line[3:]
            for line in status.splitlines()
            if line[3:] and not line[3:].startswith(str(DRIVER_DIR))
        )
        return RepoSnapshot(branch=branch, head_sha=head, dirty_paths=dirty)

    def commits_since(self, cwd: str, sha: str) -> tuple[str, ...]:
        if not sha:
            return ()
        out = self._git_out(cwd, "log", "--oneline", f"{sha}..HEAD")
        return tuple(line for line in out.splitlines() if line)

    def write_brief(self, cwd: str, name: str, text: str) -> str:
        target = self._dir(cwd) / name
        target.write_text(text, encoding="utf-8")
        return str(target)

    def _dir(self, cwd: str) -> Path:
        target = Path(cwd) / DRIVER_DIR
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _git_out(self, cwd: str, *args: str) -> str:
        """Git's stdout, stripped; empty when git fails, which the gate then refuses."""
        try:
            done = subprocess.run(  # nosec B603 -- fixed argv
                [self._git, *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT_SECONDS,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return done.stdout.strip() if done.returncode == 0 else ""
