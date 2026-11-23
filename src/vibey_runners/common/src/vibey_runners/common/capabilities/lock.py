# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplace lock: what each marketplace's tree hashed to when the person locked it
(SP-LOOPS Task 5; design Decision 1).

**The digest.** `digest_tree` lists the tree itself (never trusting listing order: every record is
collected, then sorted by its relative path's bytes), `lstat`s each entry and never follows a
symlink: a link is hashed by its target text, a file by its content (opened `O_NOFOLLOW`, so a link
swapped in after the `lstat` is refused, and so is anything not a regular file), a folder by its
presence, and an executable file differs from a plain one. Anything else -- a FIFO, a socket, a
device -- is refused rather than opened, since opening a FIFO blocks. The root's own `.git` (the
clone's folder, or a worktree's gitfile) is metadata git rewrites without the content changing -- a
`git fetch` touches nothing else -- so it alone is left out, decided by `GitFolderGuard.is_root_git`
(a name that folds to `.git` and the same file as `root/.git`), the rule the loaders refuse by. A
`.git` anywhere deeper is hashed like any other entry: content the digest skipped must never be
content a loader can read, and `MarketplaceManifest` and `SkillIndex` refuse anything that resolves
into the root's `.git` for the same reason.

The digest is made of `TreeRecord`s (`tree_records`, then `digest_records`), and both are public so
the run snapshot (`CapabilityResolver`) can compare its copy, record by record, against the very
records whose digest matched the lock.

**A scoped digest.** Given `within` (relative paths), only those entries, everything below them and
the folders above them are hashed, and Python's bytecode (`__pycache__` folders, `*.pyc` and `*.pyo`
files) is left out at every level. The shipped marketplace is locked this way, over its manifest and
the plugin folders the manifest lists: a source checkout (where the marketplace shares its folder
with sources and tests), an installed wheel and a tree where an import or an install wrote
`__pycache__` then all hash the same. Nothing left out may be loaded: a run loads only its verified
copy, and the copy holds only what the records hold. Without `within` the whole tree is hashed, as
before, bytecode included.

**Per machine.** A digest is of one file system's spelling of the tree: a name stored decomposed
(NFD, as HFS+ stores it) and the same name composed (NFC) hash differently, and so do file modes
another checkout gives differently. Under design Decision 5 a lock and the marketplace it pins live
on one machine; a lock is not meant to be carried to another.

**The file.** JSON, one object: `version`, the `entries`, and a `checksum` (sha256 of the entries'
canonical JSON). The checksum is unkeyed: it catches a corrupted or hand-edited lock, not a
deliberate one -- anyone who can write the file can recompute it, so it is no evidence of tampering.
The lock folder is the person's own and is protected by its permissions (0600). It is written to a
temporary file beside the lock, fsynced, renamed over it and the folder fsynced, with mode 0600 from
the moment it exists; a failure removes the temporary file and leaves the old lock. It is read whole
through the bounded reader (never through a symlink) and must end in the newline the writer puts
there, parse, carry exactly its keys, match its checksum and hold only well-formed entries -- or it
raises `LockError` and returns nothing. A missing lock is no entries: nothing has been locked yet.

Declared by `interfaces/lock_interface.py::CapabilityLockInterface`.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Final

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.bundle_error import BundleError
from vibey_runners.common.capabilities.file_reader import BoundedFileReader
from vibey_runners.common.capabilities.file_too_large_error import FileTooLargeError
from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.file_reader_interface import (
    FileReaderInterface,
)
from vibey_runners.common.capabilities.interfaces.git_folder_guard_interface import (
    GitFolderGuardInterface,
)
from vibey_runners.common.capabilities.interfaces.path_probe_interface import PathProbeInterface
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.names import NAME_PATTERN
from vibey_runners.common.capabilities.path_probe import PathProbe
from vibey_runners.common.capabilities.tree_record import TreeRecord

VERSION: Final = 1
LOCK_MAX_BYTES: Final = 1024 * 1024
"""The largest lock file read."""
MAX_TREE_ENTRIES: Final = 100_000
"""The most files, folders and links one marketplace tree may hold to be locked."""
DIGEST_PATTERN: Final = re.compile(r"sha256:[0-9a-f]{64}")
_KEYS: Final = frozenset({"version", "entries", "checksum"})
_ENTRY_KEYS: Final = frozenset({"marketplace", "source", "ref", "digest"})
_CHUNK: Final = 1024 * 1024
BYTECODE_FOLDER: Final = "__pycache__"
BYTECODE_SUFFIXES: Final = (".pyc", ".pyo")


class CapabilityLock:
    """Declared by `interfaces/lock_interface.py::CapabilityLockInterface`."""

    def __init__(
        self,
        reader: FileReaderInterface | None = None,
        lister: Callable[[Path], Sequence[str]] = os.listdir,
        fsync: Callable[[int], None] = os.fsync,
        guard: GitFolderGuardInterface | None = None,
        probe: PathProbeInterface | None = None,
    ) -> None:
        self._reader = reader or BoundedFileReader()
        self._guard = guard or GitFolderGuard()
        self._probe = probe or PathProbe()
        self._lister = lister
        self._fsync = fsync

    # -- the digest --------------------------------------------------------------------------

    def digest_tree(self, root: Path, within: Sequence[PurePosixPath] | None = None) -> str:
        return self.digest_records(self.tree_records(root, within))

    def tree_records(
        self, root: Path, within: Sequence[PurePosixPath] | None = None
    ) -> tuple[TreeRecord, ...]:
        if not self._probe.is_dir(root):  # a root that cannot be looked at raises, on any Python
            raise LockError(f"{root} is not a folder")
        records: dict[str, TreeRecord] = {}
        if within is None:
            self._walk(root, [PurePosixPath()], records, scoped=False)
        else:
            self._walk(root, self._scope(root, within, records), records, scoped=True)
        return tuple(sorted(records.values(), key=self._order))

    def _scope(
        self, root: Path, within: Sequence[PurePosixPath], records: dict[str, TreeRecord]
    ) -> list[PurePosixPath]:
        """Records each item of `within` and the folders above it; returns the folders to walk."""
        starts: list[PurePosixPath] = []
        for item in within:
            if item.is_absolute() or ".." in item.parts:
                raise LockError(f"{item} is not a path inside {root}")
            if not item.parts:
                starts.append(item)  # the whole tree, still without bytecode
                continue
            if any(self._bytecode(part) for part in item.parts):
                continue
            for path in [*reversed(item.parents[:-1]), item]:
                kind, payload = self._record(root / path)
                records[path.as_posix()] = TreeRecord(path.as_posix(), kind, payload)
                if kind != "D":
                    break  # a file, or a symlink never followed: nothing below it is reached
            else:
                starts.append(item)
        return starts

    def _walk(
        self,
        root: Path,
        starts: Sequence[PurePosixPath],
        records: dict[str, TreeRecord],
        *,
        scoped: bool,
    ) -> None:
        pending = list(starts)
        while pending:
            folder = pending.pop()
            names = list(self._lister(root / folder))
            if folder == PurePosixPath():
                names = [name for name in names if not self._guard.is_root_git(root, root / name)]
            if scoped:
                names = [name for name in names if not self._bytecode(name)]
            if len(records) + len(names) > MAX_TREE_ENTRIES:
                raise LockError(f"{root} holds more than {MAX_TREE_ENTRIES} entries")
            for name in names:
                relative = folder / name
                kind, payload = self._record(root / relative)
                records[relative.as_posix()] = TreeRecord(relative.as_posix(), kind, payload)
                if kind == "D":
                    pending.append(relative)

    @staticmethod
    def _bytecode(name: str) -> bool:
        """Python's own cache, which an import or an install writes inside a shipped tree."""
        return name == BYTECODE_FOLDER or name.endswith(BYTECODE_SUFFIXES)

    def digest_records(self, records: Sequence[TreeRecord]) -> str:
        digest = hashlib.sha256()
        for key, kind, payload in sorted(self._order(record) for record in records):
            digest.update(kind + b"\0" + key + b"\0" + payload + b"\0")
        return f"sha256:{digest.hexdigest()}"

    @staticmethod
    def _order(record: TreeRecord) -> tuple[bytes, bytes, bytes]:
        """The bytes a record is sorted and framed by: the path as the file system spells it."""
        return os.fsencode(record.path), record.kind.encode(), record.payload.encode()

    def _record(self, path: Path) -> tuple[str, str]:
        mode = os.lstat(path).st_mode
        if stat.S_ISLNK(mode):
            target = os.fsencode(os.readlink(path))
            return "L", hashlib.sha256(target).hexdigest()
        if stat.S_ISDIR(mode):
            return "D", ""
        if stat.S_ISREG(mode):
            return ("X" if mode & stat.S_IXUSR else "F"), self._file_digest(path)
        raise LockError(f"{path} is not a file, folder or symlink")

    def _file_digest(self, path: Path) -> str:
        digest = hashlib.sha256()
        with os.fdopen(self._reader.open_regular(path), "rb") as handle:
            for chunk in iter(lambda: handle.read(_CHUNK), b""):
                digest.update(chunk)
        return digest.hexdigest()

    # -- the file ----------------------------------------------------------------------------

    @staticmethod
    def checksum(entries: object) -> str:
        """sha256 of the entries' canonical JSON: what the lock's `checksum` must equal."""
        canonical = json.dumps(entries, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return f"sha256:{hashlib.sha256(canonical.encode('ascii')).hexdigest()}"

    def write(self, path: Path, entries: Sequence[LockEntry]) -> None:
        raw = [asdict(entry) for entry in entries]
        document = {"version": VERSION, "entries": raw, "checksum": self.checksum(raw)}
        self._entries(document, str(path))  # refuse a malformed entry before touching disk
        data = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                os.fchmod(handle.fileno(), 0o600)
                handle.write(data)
                handle.flush()
                self._fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        folder = os.open(path.parent, os.O_RDONLY)
        try:
            self._fsync(folder)
        finally:
            os.close(folder)

    def read(self, path: Path) -> tuple[LockEntry, ...]:
        try:
            # Only a lock that is not there is "nothing locked yet": a lock folder that cannot be
            # searched is a failure to name, on every Python (`os.path.lexists` says False).
            if self._probe.kind(path, follow=False) is None:
                return ()
            text = self._reader.read_text(path, LOCK_MAX_BYTES)
        except FileTooLargeError as exc:
            raise LockError(str(exc)) from exc
        except UnicodeDecodeError as exc:
            raise LockError(f"{path} is not UTF-8 text") from exc
        except OSError as exc:
            raise LockError(f"{path} cannot be read: {exc}") from exc
        if not text.endswith("\n"):
            raise LockError(f"{path} is truncated: a complete lock ends with a newline")
        try:
            document = json.loads(text)
        except ValueError as exc:
            raise LockError(f"{path} is not a complete lock file: {exc}") from exc
        except RecursionError as exc:  # deep enough nesting exhausts json's recursion
            raise LockError(f"{path} is not a complete lock file: nested too deeply") from exc
        return self._entries(document, str(path))

    def _entries(self, document: object, where: str) -> tuple[LockEntry, ...]:
        if not isinstance(document, dict):
            raise LockError(f"{where} must hold a JSON object")
        if set(document) != _KEYS:
            raise LockError(f"{where} must hold exactly the keys {', '.join(sorted(_KEYS))}")
        version = document["version"]
        if type(version) is not int or version != VERSION:
            raise LockError(f"{where}: version {version!r} is not {VERSION}")
        raw = document["entries"]
        if not isinstance(raw, list):
            raise LockError(f"{where}: entries must be a list")
        if document["checksum"] != self.checksum(raw):
            raise LockError(f"{where}: checksum does not match its entries")
        entries = tuple(self._entry(item, f"{where}: entries[{i}]") for i, item in enumerate(raw))
        names = [entry.marketplace for entry in entries]
        if len(set(names)) != len(names):
            raise LockError(f"{where}: a marketplace is locked twice")
        return entries

    @staticmethod
    def _entry(item: object, where: str) -> LockEntry:
        if not isinstance(item, dict) or set(item) != _ENTRY_KEYS:
            raise LockError(f"{where} must hold exactly {', '.join(sorted(_ENTRY_KEYS))}")
        marketplace, source = item["marketplace"], item["source"]
        ref, digest = item["ref"], item["digest"]
        if not isinstance(marketplace, str) or NAME_PATTERN.fullmatch(marketplace) is None:
            raise LockError(f"{where}: marketplace must be a plain name")
        try:
            # The bundle's own rule for a source and a ref: what `[loops]` refuses, the lock
            # cannot carry either (a later git call may be handed either).
            source = BundleSpec.option_safe_text(source, f"{where}: source")
            if ref is not None:
                ref = BundleSpec.option_safe_text(ref, f"{where}: ref")
        except BundleError as exc:
            raise LockError(str(exc)) from exc
        if not isinstance(digest, str) or DIGEST_PATTERN.fullmatch(digest) is None:
            raise LockError(f"{where}: digest must be sha256:<64 hex digits>")
        return LockEntry(marketplace, source, ref, digest)
