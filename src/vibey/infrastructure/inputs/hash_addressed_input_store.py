# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The person's run inputs on disk, stored once by digest, added to by appending (SP-LOOPS Phase
3, Task 2; design Decision 6; fix round 1: R-A, R-D, R-E, R-F). Nothing enters Postgres.

**Where.** Under a root in the person's own state folder (`UserStateFolder.inputs()`), one
folder per project id -- never inside a project's checkout, so a cloned repository can neither
redirect the store through a committed symlink nor seed it with committed files (review
findings 1 and 2). Inputs do not follow a project to another machine (design Decision 5).

**Layout.** `<root>/<project id>/` (0700): `objects/<digest[:2]>/<digest>` holds each input's
bytes once (0600), and `index.jsonl` (0600) one JSON line per add -- digest, kind, name, size
and when, never the content.

**Writing.** The index line is built first. An object is written through `NoFollowFiles` (a
temporary name opened `O_EXCL | O_NOFOLLOW`, synced, renamed into place); an object already
there is kept only when its bytes still match its digest, and replaced otherwise, so adding an
input again repairs it (finding 5). Then the line is appended in one write, a newline first when
the index ends in a torn line (finding 3): the append is the commit, so a crash leaves at most an
object no row names. No lock and no thread.

**Reading.** Every folder is walked with `lstat`, and an object is refused from its size,
before it is read, when it is not the size its row says. Every refusal is an `InputStoreError`.
Declared by `interfaces/input_store_interface.py::HashAddressedInputStoreInterface`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final
from uuid import UUID

from vibey.application.interfaces.system import Clock
from vibey.domain.errors import InputStoreError
from vibey.domain.run_input import (
    RUN_INPUT_RULE,
    InputKind,
    InputListing,
    RunInput,
)
from vibey.infrastructure.inputs.interfaces.no_follow_files_interface import (
    NoFollowFilesInterface,
)
from vibey.infrastructure.inputs.no_follow_files import FOLDER_MODE, NoFollowFiles

MAX_INDEX_LINE_BYTES: Final = 4096
"""The longest index write appended: one `O_APPEND` write of a regular file this size is whole on
every filesystem vibey supports, so two adds at once can never interleave their lines."""
INDEX: Final = "index.jsonl"
OBJECTS: Final = "objects"


class HashAddressedInputStore:
    """Declared by `interfaces/input_store_interface.py::HashAddressedInputStoreInterface`."""

    def __init__(
        self,
        root: Path,
        clock: Clock,
        *,
        files: NoFollowFilesInterface | None = None,
        max_index_line_bytes: int = MAX_INDEX_LINE_BYTES,
    ) -> None:
        self._root = root
        self._clock = clock
        self._files = files or NoFollowFiles()
        self._max_line = max_index_line_bytes

    def put(self, project_id: UUID, kind: InputKind, name: str, data: bytes) -> RunInput:
        item = RunInput(digest=RUN_INPUT_RULE.digest_of(data), kind=kind, name=name, size=len(data))
        line = self._line(item)
        folder, shard = self._folders(project_id, item.digest)
        if not self._intact(shard / item.digest, item.digest):
            self._files.write(shard, item.digest, data)
        self._files.append(folder / INDEX, line, max_bytes=self._max_line)
        return item

    def restore(self, project_id: UUID, data: bytes) -> str:
        digest = RUN_INPUT_RULE.digest_of(data)
        _, shard = self._folders(project_id, digest)
        self._files.write(shard, digest, data)
        return digest

    @property
    def root(self) -> Path:
        return self._root

    def describe(self) -> str:
        return f"local store at {self._root}"

    def _folders(self, project_id: UUID, digest: str) -> tuple[Path, Path]:
        """The project's folder and the object's shard, made (0700) and lstat-checked."""
        try:
            os.makedirs(self._root, FOLDER_MODE, exist_ok=True)
        except OSError as exc:
            raise InputStoreError(f"{self._root}: the input store cannot be made: {exc}") from exc
        folder = self._files.made(self._root, (str(project_id),))
        return folder, self._files.made(folder, (OBJECTS, digest[:2]))

    def get(self, project_id: UUID, digest: str, *, size: int) -> bytes:
        if not RUN_INPUT_RULE.is_digest(digest):
            raise InputStoreError(f"{digest!r} is not a digest")
        shard = self._files.found(self._root, (str(project_id), OBJECTS, digest[:2]))
        data = self._files.read(shard / digest, max_bytes=size) if shard is not None else None
        if data is None:
            raise InputStoreError(f"{self._root / str(project_id)}: no stored input is {digest}")
        if len(data) != size or RUN_INPUT_RULE.digest_of(data) != digest:
            raise InputStoreError(
                f"{shard}/{digest}: the stored object does not match its digest; add that input "
                "again to store it afresh"
            )
        return data

    def listed(self, project_id: UUID) -> InputListing:
        folder = self._files.found(self._root, (str(project_id),))
        data = self._files.read(folder / INDEX) if folder is not None else None
        if data is None:
            return InputListing(items=(), skipped=0)
        *lines, tail = data.split(b"\n")
        items: list[RunInput] = []
        skipped = 1 if tail else 0  # a last line with no newline is one torn by a crash
        for line in lines:
            item = self._row(line)
            if item is None:
                skipped += 1
            else:
                items.append(item)
        return InputListing(items=tuple(items), skipped=skipped)

    def _intact(self, path: Path, digest: str) -> bool:
        """Whether a regular file at `path` holds the bytes `digest` names (a symlink or other
        non-regular file there is refused by the read)."""
        data = self._files.read(path)
        return data is not None and RUN_INPUT_RULE.digest_of(data) == digest

    def _line(self, item: RunInput) -> bytes:
        row = {
            "digest": item.digest,
            "kind": item.kind,
            "name": item.name,
            "size": item.size,
            "at": self._clock.now().isoformat(),
        }
        line = (json.dumps(row, ensure_ascii=True, separators=(",", ":")) + "\n").encode()
        if len(line) + 1 > self._max_line:  # + 1: the newline a torn index may need first
            raise InputStoreError(
                f"the index line for this input is {len(line)} bytes; at most "
                f"{self._max_line - 1} are appended in one write"
            )
        return line

    @staticmethod
    def _row(line: bytes) -> RunInput | None:
        """One index line as a run input, or None when it is not one this store writes (the
        one rule every store reads its index through: `RunInputRule.row_of`)."""
        return RUN_INPUT_RULE.row_of(line)
