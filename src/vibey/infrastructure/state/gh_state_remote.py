# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""GhStateRemote: the sealed state on a branch of the repository, over `gh api` (ADR-0086).

The branch holds one file and nothing else: no workflow runs on a push to it, and its
history is the state's history, one commit per sync that changed something. It is read
and written through git's data API -- ref, commit, tree, blob -- so no checkout is needed
and nothing touches the working tree. A push creates the blob, a one-file tree and a
commit whose parent is the head the merge read, then moves the branch with `force: false`:
GitHub moves it only if it is still at that head, so two syncs racing never lose one
another's rows -- the loser is told the branch moved, and merges again.

`gh` runs with an environment built from its own declaration (`GhCliSubprocessExecutor`):
the database's DSN and the state key never reach it.
"""

import base64
import json
import tempfile
from pathlib import Path
from typing import Final

from vibey.application.interfaces.state_sync import StateRemote
from vibey.domain.errors import VibeyError
from vibey.domain.state_sync import RemoteHead, RemoteMoved
from vibey.infrastructure.engines.claudeloop_process import CommandResult
from vibey.infrastructure.interfaces import CommandExecutor
from vibey.infrastructure.state.interfaces.settings_interface import StateSyncSettingsInterface
from vibey.infrastructure.workflows.gh_workflows import GhCliSubprocessExecutor

#: The commit message of every sync: it says what the branch is, and nothing of the rows.
MESSAGE: Final[str] = "chore(state): sync vibey's database, sealed (ADR-0086)"
#: What GitHub answers when a ref did not move because it was no longer at the parent.
_MOVED: Final[tuple[str, ...]] = ("HTTP 409", "HTTP 422")


class GhStateError(VibeyError):
    """GitHub refused a read or a write of the state branch."""


class GhStateRemote(StateRemote):
    """Implements `application/interfaces/state_sync.py::StateRemote` over `gh api`."""

    def __init__(
        self,
        settings: StateSyncSettingsInterface,
        repository: str,
        *,
        executor: CommandExecutor | None = None,
        gh: str = "gh",
    ) -> None:
        if repository.count("/") != 1 or repository.startswith("/") or repository.endswith("/"):
            raise ValueError(f"the state repository is OWNER/NAME, not {repository!r}")
        self._settings = settings
        self._repository = repository
        self._executor: CommandExecutor = executor or GhCliSubprocessExecutor()
        self._gh = gh

    @classmethod
    async def resolve(
        cls,
        settings: StateSyncSettingsInterface,
        *,
        executor: CommandExecutor | None = None,
        gh: str = "gh",
    ) -> "GhStateRemote":
        """The remote for the declared repository, or for the working directory's."""
        runner: CommandExecutor = executor or GhCliSubprocessExecutor()
        repository = settings.repository
        if not repository:
            result = await runner.execute(
                (gh, "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner")
            )
            repository = result.stdout.strip()
            if result.returncode or not repository:
                raise GhStateError(
                    "no repository for the state: set VIBEY_STATE_REPOSITORY=OWNER/NAME, or "
                    "run from a checkout of one (" + result.stderr.strip()[:300] + ")"
                )
        return cls(settings, repository, executor=runner, gh=gh)

    @property
    def name(self) -> str:
        return f"{self._repository}:{self._settings.branch}"

    async def _api(self, path: str, *, method: str = "GET", body: object = None) -> CommandResult:
        argv = [self._gh, "api", "-X", method, f"repos/{self._repository}/{path}"]
        if body is None:
            return await self._executor.execute(tuple(argv))
        with tempfile.TemporaryDirectory(prefix="vibey-state-") as scratch:
            request = Path(scratch) / "body.json"
            request.write_text(json.dumps(body), encoding="utf-8")
            return await self._executor.execute((*argv, "--input", str(request)))

    async def _json(
        self, path: str, *, method: str = "GET", body: object = None, ref: bool = False
    ) -> dict[str, object] | None:
        """The answer, or None when there is nothing there (404). Only a ref's update says
        the branch moved: a refused blob, tree or commit is a refusal, not a race."""
        result = await self._api(path, method=method, body=body)
        if result.returncode:
            reason = (result.stderr.strip() or result.stdout.strip())[:500]
            if "HTTP 404" in reason:
                return None
            if ref and any(code in reason for code in _MOVED):
                raise RemoteMoved(f"{self.name} moved: {reason}")
            raise GhStateError(f"GitHub refused {method} {path}: {reason}")
        loaded = json.loads(result.stdout or "{}")
        if not isinstance(loaded, dict):
            raise GhStateError(f"GitHub answered {method} {path} with something not an object")
        return loaded

    @staticmethod
    def _sha(document: dict[str, object] | None, *path: str) -> str | None:
        value: object = document
        for step in path:
            value = value.get(step) if isinstance(value, dict) else None
        return value if isinstance(value, str) else None

    async def _read(self, commit: str) -> bytes | None:
        tree = self._sha(await self._json(f"git/commits/{commit}"), "tree", "sha")
        if tree is None:
            return None
        listing = await self._json(f"git/trees/{tree}")
        entries = listing.get("tree") if listing else None
        blob = next(
            (
                entry.get("sha")
                for entry in (entries if isinstance(entries, list) else [])
                if isinstance(entry, dict) and entry.get("path") == self._settings.path
            ),
            None,
        )
        if not isinstance(blob, str):
            raise GhStateError(f"{self.name} at {commit[:12]} holds no {self._settings.path}")
        content = self._sha(await self._json(f"git/blobs/{blob}"), "content")
        if content is None:
            raise GhStateError(f"{self.name}: the blob {blob[:12]} has no content")
        return base64.b64decode(content)

    async def head(self) -> RemoteHead | None:
        ref = await self._json(f"git/ref/heads/{self._settings.branch}")
        commit = self._sha(ref, "object", "sha")
        if commit is None:
            return None
        data = await self._read(commit)
        if data is None:
            raise GhStateError(f"{self.name}'s head {commit[:12]} cannot be read")
        return RemoteHead(commit, data)

    async def at(self, commit: str) -> bytes | None:
        return await self._read(commit)

    async def push(self, data: bytes, parent: str | None) -> str:
        blob = self._sha(
            await self._json(
                "git/blobs",
                method="POST",
                body={"content": base64.b64encode(data).decode(), "encoding": "base64"},
            ),
            "sha",
        )
        tree = self._sha(
            await self._json(
                "git/trees",
                method="POST",
                body={
                    "tree": [
                        {"path": self._settings.path, "mode": "100644", "type": "blob", "sha": blob}
                    ]
                },
            ),
            "sha",
        )
        commit = self._sha(
            await self._json(
                "git/commits",
                method="POST",
                body={"message": MESSAGE, "tree": tree, "parents": [parent] if parent else []},
            ),
            "sha",
        )
        if blob is None or tree is None or commit is None:
            raise GhStateError(f"GitHub did not make the commit for {self.name}")
        if parent is None:
            created = await self._json(
                "git/refs",
                method="POST",
                body={"ref": f"refs/heads/{self._settings.branch}", "sha": commit},
                ref=True,
            )
            if created is None:
                raise GhStateError(f"GitHub could not start {self.name}")
        else:
            moved = await self._json(
                f"git/refs/heads/{self._settings.branch}",
                method="PATCH",
                body={"sha": commit, "force": False},
                ref=True,
            )
            if moved is None:
                raise RemoteMoved(f"{self.name} is gone")
        return commit
