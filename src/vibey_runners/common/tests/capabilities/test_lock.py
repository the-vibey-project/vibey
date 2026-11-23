# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplace lock: a content digest that does not depend on listing order and never
follows a symlink, written atomically and read whole or not at all (SP-LOOPS Task 5)."""

from __future__ import annotations

import json
import os
import random
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from vibey_runners.common.capabilities.git_folder_guard import GitFolderGuard
from vibey_runners.common.capabilities.interfaces.lock_interface import CapabilityLockInterface
from vibey_runners.common.capabilities.lock import (
    LOCK_MAX_BYTES,
    MAX_TREE_ENTRIES,
    CapabilityLock,
)
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_error import LockError

DIGEST = "sha256:" + "a" * 64
ENTRIES = (
    LockEntry("vibey", "wheel", None, DIGEST),
    LockEntry("acme", "https://example.test/acme.git", "v1.2.0", "sha256:" + "b" * 64),
)


def _tree(root: Path, files: dict[str, bytes]) -> Path:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return root


class _Shuffled:
    """Lists a folder in a seeded random order: the digest must not notice."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    def __call__(self, folder: Path) -> Sequence[str]:
        names = os.listdir(folder)
        self._random.shuffle(names)
        return names


_SEGMENT = st.text(alphabet="abcdefgh-_.", min_size=1, max_size=6).filter(
    lambda s: s not in {".", ".."} and s != ".git"
)
_FILES = st.dictionaries(
    st.lists(_SEGMENT, min_size=1, max_size=3).map("/".join),
    st.binary(max_size=64),
    min_size=1,
    max_size=12,
)


def _consistent(files: dict[str, bytes]) -> bool:
    """No path is both a file and a folder."""
    return not any(other.startswith(path + "/") for path in files for other in files)


@settings(max_examples=60, deadline=None)
@given(files=_FILES.filter(_consistent), seed=st.integers(0, 2**32 - 1))
def test_the_digest_does_not_depend_on_listing_or_creation_order(
    files: dict[str, bytes], seed: int
) -> None:
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        forwards = _tree(Path(first), files)
        backwards = _tree(Path(second), dict(reversed(list(files.items()))))
        expected = CapabilityLock().digest_tree(forwards)
        assert CapabilityLock(lister=_Shuffled(seed)).digest_tree(forwards) == expected
        assert CapabilityLock(lister=_Shuffled(seed + 1)).digest_tree(backwards) == expected


def test_a_digest_is_a_sha256_name(tmp_path: Path) -> None:
    digest = CapabilityLock().digest_tree(_tree(tmp_path, {"a.txt": b"x"}))
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
    assert isinstance(CapabilityLock(), CapabilityLockInterface)


def test_changing_one_byte_changes_the_digest(tmp_path: Path) -> None:
    root = _tree(tmp_path, {"p/skills/s/SKILL.md": b"hello", "p/README.md": b"r"})
    before = CapabilityLock().digest_tree(root)
    (root / "p/skills/s/SKILL.md").write_bytes(b"hellp")
    assert CapabilityLock().digest_tree(root) != before


@pytest.mark.parametrize(
    "change",
    [
        lambda root: (root / "new.txt").write_bytes(b""),
        lambda root: (root / "a.txt").rename(root / "b.txt"),
        lambda root: (root / "empty").mkdir(),
        lambda root: (root / "a.txt").chmod(0o755),
    ],
)
def test_adding_renaming_or_making_executable_changes_the_digest(
    tmp_path: Path, change: object
) -> None:
    root = _tree(tmp_path, {"a.txt": b"x"})
    before = CapabilityLock().digest_tree(root)
    change(root)  # type: ignore[operator]
    assert CapabilityLock().digest_tree(root) != before


def test_a_symlink_is_hashed_by_its_target_text_and_never_followed(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"one")
    root = tmp_path / "market"
    root.mkdir()
    (root / "link").symlink_to(outside)
    (root / "file-link").symlink_to(outside / "secret.txt")
    lock = CapabilityLock()
    before = lock.digest_tree(root)
    (outside / "secret.txt").write_bytes(b"two")  # the target's content changes ...
    (outside / "more.txt").write_bytes(b"more")
    assert lock.digest_tree(root) == before  # ... and the digest does not
    (root / "link").unlink()
    (root / "link").symlink_to(tmp_path / "elsewhere")  # the link's own text changes ...
    assert lock.digest_tree(root) != before  # ... and the digest does


def test_a_symlink_and_a_file_with_the_same_text_differ(tmp_path: Path) -> None:
    as_file = _tree(tmp_path / "f", {"x": b"target"})
    as_link = tmp_path / "l"
    as_link.mkdir()
    (as_link / "x").symlink_to("target")
    assert CapabilityLock().digest_tree(as_file) != CapabilityLock().digest_tree(as_link)


def test_the_root_git_metadata_is_not_content(tmp_path: Path) -> None:
    root = _tree(tmp_path / "clone", {"a.txt": b"x"})
    before = CapabilityLock().digest_tree(root)
    _tree(root, {".git/index": b"changes on every git status", ".git/FETCH_HEAD": b"fetched"})
    assert CapabilityLock().digest_tree(root) == before
    worktree = _tree(tmp_path / "worktree", {"a.txt": b"x", ".git": b"gitdir: ../x"})
    assert CapabilityLock().digest_tree(worktree) == before  # a gitfile at the root too


@pytest.mark.parametrize(
    "nested",
    ["sub/.git", "plugins/x/.git/SKILL.md", "plugins/x/skills/foo/.git/SKILL.md"],
)
def test_a_nested_git_entry_is_content_like_any_other(tmp_path: Path, nested: str) -> None:
    root = _tree(tmp_path, {"a.txt": b"x", "sub/b.txt": b"y", "plugins/x/skills/foo/f": b"z"})
    before = CapabilityLock().digest_tree(root)
    _tree(root, {nested: b"a loader could read this"})
    assert CapabilityLock().digest_tree(root) != before


def test_a_fifo_is_refused_and_never_opened(tmp_path: Path) -> None:
    root = tmp_path / "market"
    root.mkdir()
    os.mkfifo(root / "pipe")
    with pytest.raises(LockError, match="not a file, folder or symlink"):
        CapabilityLock().digest_tree(root)


def test_a_missing_root_is_refused(tmp_path: Path) -> None:
    with pytest.raises(LockError, match="is not a folder"):
        CapabilityLock().digest_tree(tmp_path / "absent")


def test_a_tree_past_the_entry_limit_is_refused(tmp_path: Path) -> None:
    def many(folder: Path) -> Sequence[str]:
        return [f"f{i}" for i in range(MAX_TREE_ENTRIES + 1)] if folder == tmp_path else []

    _tree(tmp_path, {"f0": b""})
    with pytest.raises(LockError, match=f"more than {MAX_TREE_ENTRIES}"):
        CapabilityLock(lister=many).digest_tree(tmp_path)


def test_write_then_read_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "state" / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    assert CapabilityLock().read(path) == ENTRIES
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert [p.name for p in path.parent.iterdir()] == ["loops.lock"]


def test_a_rewrite_replaces_the_whole_lock(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    CapabilityLock().write(path, ENTRIES[:1])
    assert CapabilityLock().read(path) == ENTRIES[:1]


def test_a_failed_write_leaves_the_old_lock_and_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    CapabilityLock().write(path, ENTRIES)

    def broken_fsync(descriptor: int) -> None:
        raise OSError("disk full")

    with pytest.raises(OSError, match="disk full"):
        CapabilityLock(fsync=broken_fsync).write(path, ENTRIES[:1])
    assert CapabilityLock().read(path) == ENTRIES
    assert [p.name for p in tmp_path.iterdir()] == ["loops.lock"]


def test_a_missing_lock_is_no_entries(tmp_path: Path) -> None:
    assert CapabilityLock().read(tmp_path / "absent.lock") == ()


def test_a_truncated_lock_raises_and_returns_nothing(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    whole = path.read_bytes()
    for size in range(len(whole)):
        path.write_bytes(whole[:size])
        with pytest.raises(LockError):
            CapabilityLock().read(path)


def _rewrite(path: Path, edit: object) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    edit(document)  # type: ignore[operator]
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("edit", "reason"),
    [
        (lambda d: d.update(version=2), "version"),
        (lambda d: d.update(entries="x"), "entries"),
        (lambda d: d.update(extra=1), "keys"),
        (lambda d: d["entries"][0].update(digest="md5:0"), "checksum"),
        (lambda d: d.update(checksum="sha256:" + "0" * 64), "checksum"),
    ],
)
def test_a_tampered_lock_is_refused(tmp_path: Path, edit: object, reason: str) -> None:
    path = tmp_path / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    _rewrite(path, edit)
    with pytest.raises(LockError, match=reason):
        CapabilityLock().read(path)


@pytest.mark.parametrize(
    "entry",
    [
        {"marketplace": "../x", "source": "s", "ref": None, "digest": DIGEST},
        {"marketplace": "a", "source": "", "ref": None, "digest": DIGEST},
        {"marketplace": "a", "source": "s", "ref": 3, "digest": DIGEST},
        {"marketplace": "a", "source": "s", "ref": None, "digest": "sha256:short"},
        {"marketplace": "a", "source": "s", "ref": None},
        "not-an-object",
    ],
)
def test_a_lock_with_a_malformed_entry_is_refused(tmp_path: Path, entry: object) -> None:
    path = tmp_path / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"] = [entry]
    document["checksum"] = CapabilityLock.checksum(document["entries"])
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    with pytest.raises(LockError):
        CapabilityLock().read(path)


@pytest.mark.parametrize(
    "entries",
    [
        (LockEntry("../x", "s", None, DIGEST),),
        (LockEntry("a", "s", None, "sha1:abc"),),
        (LockEntry("a", "s", None, DIGEST), LockEntry("a", "t", None, DIGEST)),
    ],
)
def test_writing_a_malformed_entry_is_refused_and_writes_nothing(
    tmp_path: Path, entries: tuple[LockEntry, ...]
) -> None:
    path = tmp_path / "loops.lock"
    with pytest.raises(LockError):
        CapabilityLock().write(path, entries)
    assert not path.exists()


def test_a_lock_that_is_not_json_text_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(LockError, match="UTF-8"):
        CapabilityLock().read(path)


def test_an_oversized_lock_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    path.write_bytes(b" " * (LOCK_MAX_BYTES + 1))
    with pytest.raises(LockError, match="bytes"):
        CapabilityLock().read(path)


def test_a_lock_that_is_a_symlink_is_refused(tmp_path: Path) -> None:
    real = tmp_path / "real.lock"
    CapabilityLock().write(real, ENTRIES)
    link = tmp_path / "loops.lock"
    link.symlink_to(real)
    with pytest.raises(LockError, match="cannot be read"):
        CapabilityLock().read(link)


def test_a_lock_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(LockError, match="JSON object"):
        CapabilityLock().read(path)


def _stat_as(root: Path, *, case_insensitive: bool) -> object:
    """The identity seam: whether `.git` and `.GIT` at `root` are one folder (a case-insensitive
    file system) or two (a case-sensitive one), the same on every operating system."""

    def fake(path: Path) -> os.stat_result:
        if path == root / ".git":
            if not case_insensitive:
                raise FileNotFoundError(path)
            return os.stat(root / ".GIT")
        return os.stat(path)

    return fake


@pytest.mark.parametrize(("case_insensitive", "skipped"), [(True, True), (False, False)])
def test_the_root_git_skip_follows_file_identity(
    tmp_path: Path, case_insensitive: bool, skipped: bool
) -> None:
    bare = _tree(tmp_path / "bare", {"a.txt": b"x"})
    root = _tree(tmp_path / "clone", {"a.txt": b"x", ".GIT/index": b"metadata or content"})
    guard = GitFolderGuard(stat=_stat_as(root, case_insensitive=case_insensitive))  # type: ignore[arg-type]
    digest = CapabilityLock(guard=guard).digest_tree(root)
    assert (digest == CapabilityLock().digest_tree(bare)) is skipped


def test_a_root_entry_sharing_the_git_identity_under_another_name_is_hashed(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path / "clone", {"a.txt": b"x", ".git/index": b"i"})
    (root / "alias").symlink_to(root / ".git", target_is_directory=True)
    without = _tree(tmp_path / "bare", {"a.txt": b"x"})
    # Only a name that folds to `.git` is a candidate; the alias is content (a link, by its text).
    assert CapabilityLock().digest_tree(root) != CapabilityLock().digest_tree(without)
