# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The marketplace lock: a content digest that does not depend on listing order and never
follows a symlink, written atomically and read whole or not at all (SP-LOOPS Task 5)."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import random
import stat
import tempfile
from collections.abc import Sequence
from pathlib import Path, PurePosixPath

import pytest
from fakes import unsearchable
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
from vibey_runners.common.capabilities.tree_record import TreeRecord

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


def _pinned_tree(root: Path) -> Path:
    _tree(root, {"a.txt": b"x", "d/b.txt": b"y", "run.sh": b"#!"})
    (root / "a.txt").chmod(0o644)
    (root / "d/b.txt").chmod(0o644)
    (root / "run.sh").chmod(0o755)
    (root / "d/link").symlink_to("../a.txt")
    return root


def test_the_digest_of_a_fixed_tree_is_pinned(tmp_path: Path) -> None:
    """Locks already on disk must keep matching: the framing never changes silently."""
    root = _pinned_tree(tmp_path)
    assert CapabilityLock().digest_tree(root) == (
        "sha256:28aa44f1935441a387186e2a6b72a48a4b274edacef18a249ef4040ce39f384d"
    )


def test_the_tree_records_are_what_the_digest_is_made_of(tmp_path: Path) -> None:
    root = _pinned_tree(tmp_path)
    lock = CapabilityLock()
    records = lock.tree_records(root)
    by_path = {record.path: record for record in records}
    assert sorted(by_path) == ["a.txt", "d", "d/b.txt", "d/link", "run.sh"]
    assert by_path["d"] == TreeRecord("d", "D", "")
    assert by_path["a.txt"].kind == "F"
    assert by_path["a.txt"].payload == hashlib.sha256(b"x").hexdigest()
    assert by_path["run.sh"].kind == "X"
    assert by_path["d/link"] == TreeRecord("d/link", "L", hashlib.sha256(b"../a.txt").hexdigest())
    assert lock.digest_records(records) == lock.digest_tree(root)
    assert lock.digest_records(tuple(reversed(records))) == lock.digest_tree(root)


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
def test_a_corrupted_or_hand_edited_lock_is_refused(
    tmp_path: Path, edit: object, reason: str
) -> None:
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
    seam = _stat_as(root, case_insensitive=case_insensitive)
    guard = GitFolderGuard(stat=seam)  # type: ignore[arg-type]
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


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this operating system")
def test_a_fifo_at_the_lock_path_is_refused_without_hanging(tmp_path: Path) -> None:
    fifo = tmp_path / "loops.lock"
    os.mkfifo(fifo)
    with pytest.raises(LockError, match="not a regular file"):
        CapabilityLock().read(fifo)


def test_a_write_fsyncs_the_file_and_then_its_folder(tmp_path: Path) -> None:
    kinds: list[str] = []

    def recording(descriptor: int) -> None:
        mode = os.fstat(descriptor).st_mode
        kinds.append("folder" if stat.S_ISDIR(mode) else "file")
        os.fsync(descriptor)

    CapabilityLock(fsync=recording).write(tmp_path / "loops.lock", ENTRIES)
    assert kinds == ["file", "folder"]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source", "-uupload-pack=evil"),
        ("source", "https://e.test/\x1b[2J"),
        pytest.param("source", "x" * 4097, id="source-overlong"),
        ("ref", "--force"),
        ("ref", "v1\n"),
    ],
)
def test_a_lock_entry_holds_its_source_and_ref_to_the_bundle_rule(
    tmp_path: Path, field: str, value: str
) -> None:
    path = tmp_path / "loops.lock"
    fields = {"marketplace": "acme", "source": "s", "ref": None, "digest": DIGEST, field: value}
    with pytest.raises(LockError, match=field):
        CapabilityLock().write(path, (LockEntry(**fields),))  # type: ignore[arg-type]
    assert not path.exists()
    CapabilityLock().write(path, ENTRIES)
    document = json.loads(path.read_text(encoding="utf-8"))
    document["entries"] = [fields]
    document["checksum"] = CapabilityLock.checksum(document["entries"])
    path.write_text(json.dumps(document) + "\n", encoding="utf-8")
    with pytest.raises(LockError, match=field):
        CapabilityLock().read(path)


def test_a_deeply_nested_lock_is_a_lock_error(tmp_path: Path) -> None:
    path = tmp_path / "loops.lock"
    path.write_text("[" * 200_000 + "\n", encoding="utf-8")
    with pytest.raises(LockError, match="not a complete lock file"):
        CapabilityLock().read(path)


# -- a folder that cannot be searched: the same answer on Python 3.12, 3.13 and 3.14 ----------


def test_a_root_that_cannot_be_looked_at_raises_rather_than_reading_as_no_folder(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path / "outer" / "market", {"a.txt": b"x"})
    with unsearchable(tmp_path / "outer"), pytest.raises(PermissionError):
        CapabilityLock().tree_records(root)


def test_a_lock_in_a_folder_that_cannot_be_searched_is_refused_not_empty(tmp_path: Path) -> None:
    path = tmp_path / "state" / "loops.lock"
    CapabilityLock().write(path, ENTRIES)
    with unsearchable(path.parent), pytest.raises(LockError, match="cannot be read"):
        CapabilityLock().read(path)


# -- a scoped digest: the manifest and the plugin folders it lists, never bytecode ------------

SCOPE = (PurePosixPath(".claude-plugin/marketplace.json"), PurePosixPath("plugins/p"))


def _shipped(root: Path) -> Path:
    return _tree(
        root,
        {
            ".claude-plugin/marketplace.json": b"{}",
            "plugins/p/skills/s/SKILL.md": b"skill",
            "plugins/p/scripts/tool.py": b"print()",
            "plugins/unlisted/README.md": b"r",
            "src/module.py": b"code",
            "tests/test_module.py": b"test",
        },
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda root: _tree(root, {"plugins/p/scripts/__pycache__/tool.cpython-312.pyc": b"\0"}),
        lambda root: _tree(root, {"plugins/p/scripts/tool.pyc": b"\0", "plugins/p/x.pyo": b"\0"}),
        lambda root: _tree(root, {"__pycache__/x.pyc": b"\0", "tests/test_new.py": b"t"}),
        lambda root: _tree(root, {"src/module.py": b"edited", "plugins/unlisted/new": b"n"}),
        lambda root: _tree(root, {".claude-plugin/plugin.json": b"{}"}),
    ],
)
def test_a_scoped_digest_ignores_bytecode_and_everything_outside_it(
    tmp_path: Path, change: object
) -> None:
    root = _shipped(tmp_path)
    lock = CapabilityLock()
    before = lock.digest_tree(root, SCOPE)
    change(root)  # type: ignore[operator]
    assert lock.digest_tree(root, SCOPE) == before


@pytest.mark.parametrize(
    "change",
    [
        lambda root: _tree(root, {"plugins/p/skills/s/SKILL.md": b"changed"}),
        lambda root: _tree(root, {"plugins/p/new.md": b"new"}),
        lambda root: _tree(root, {".claude-plugin/marketplace.json": b'{"plugins": []}'}),
        lambda root: (root / "plugins/p/scripts/tool.py").chmod(0o755),
    ],
)
def test_a_scoped_digest_sees_every_change_inside_it(tmp_path: Path, change: object) -> None:
    root = _shipped(tmp_path)
    (root / "plugins/p/scripts/tool.py").chmod(0o644)
    lock = CapabilityLock()
    before = lock.digest_tree(root, SCOPE)
    change(root)  # type: ignore[operator]
    assert lock.digest_tree(root, SCOPE) != before


def test_a_checkout_and_an_install_of_the_same_marketplace_hash_alike(tmp_path: Path) -> None:
    checkout = _shipped(tmp_path / "checkout")
    installed = _tree(
        tmp_path / "installed",
        {
            ".claude-plugin/marketplace.json": b"{}",
            "plugins/p/skills/s/SKILL.md": b"skill",
            "plugins/p/scripts/tool.py": b"print()",
            "plugins/p/scripts/__pycache__/tool.cpython-314.pyc": b"\0",
        },
    )
    for root in (checkout, installed):
        (root / "plugins/p/scripts/tool.py").chmod(0o644)
    lock = CapabilityLock()
    assert lock.digest_tree(checkout, SCOPE) == lock.digest_tree(installed, SCOPE)
    assert lock.digest_tree(checkout) != lock.digest_tree(installed)  # the whole tree differs


def test_a_scoped_record_set_holds_the_folders_above_each_item(tmp_path: Path) -> None:
    root = _shipped(tmp_path)
    paths = [record.path for record in CapabilityLock().tree_records(root, SCOPE)]
    assert paths == [
        ".claude-plugin",
        ".claude-plugin/marketplace.json",
        "plugins",
        "plugins/p",
        "plugins/p/scripts",
        "plugins/p/scripts/tool.py",
        "plugins/p/skills",
        "plugins/p/skills/s",
        "plugins/p/skills/s/SKILL.md",
    ]


def test_a_scope_of_the_whole_tree_still_leaves_bytecode_and_the_root_git_out(
    tmp_path: Path,
) -> None:
    root = _tree(tmp_path, {"a.txt": b"x", "__pycache__/a.pyc": b"\0", ".git/HEAD": b"ref"})
    paths = [record.path for record in CapabilityLock().tree_records(root, [PurePosixPath()])]
    assert paths == ["a.txt"]


def test_a_scope_through_a_symlink_stops_at_the_link(tmp_path: Path) -> None:
    root = _tree(tmp_path / "market", {"real/p/a.txt": b"x"})
    (root / "plugins").symlink_to("real")
    records = CapabilityLock().tree_records(root, [PurePosixPath("plugins/p")])
    assert [(record.path, record.kind) for record in records] == [("plugins", "L")]


def test_scoped_bytecode_items_and_overlaps_are_handled(tmp_path: Path) -> None:
    root = _shipped(tmp_path)
    lock = CapabilityLock()
    scope = [*SCOPE, PurePosixPath("plugins/p/skills"), PurePosixPath("plugins/__pycache__")]
    assert lock.tree_records(root, scope) == lock.tree_records(root, SCOPE)


@pytest.mark.parametrize("item", ["/etc", "../outside", "plugins/../.."])
def test_a_scope_that_leaves_the_tree_is_refused(tmp_path: Path, item: str) -> None:
    root = _shipped(tmp_path)
    with pytest.raises(LockError, match="not a path inside"):
        CapabilityLock().tree_records(root, [PurePosixPath(item)])


def test_a_scope_past_the_entry_limit_is_refused(tmp_path: Path) -> None:
    root = _shipped(tmp_path)
    lister = lambda folder: [f"n{i}" for i in range(MAX_TREE_ENTRIES + 1)]  # noqa: E731
    with pytest.raises(LockError, match="more than"):
        CapabilityLock(lister=lister).tree_records(root, [PurePosixPath("plugins/p")])


def test_a_listed_folder_inside_another_is_walked_once(tmp_path: Path) -> None:
    """A plugin listed inside another listed plugin is covered by the outer walk: walking it again
    would hash its files twice and count them twice against `MAX_TREE_ENTRIES`."""
    root = _shipped(tmp_path)
    _tree(root, {"plugins/p/nested/inner.md": b"i"})
    listed: list[str] = []

    def lister(folder: Path) -> Sequence[str]:
        listed.append(folder.relative_to(root).as_posix())
        return os.listdir(folder)

    scope = [*SCOPE, PurePosixPath("plugins/p/nested"), PurePosixPath("plugins/p")]
    records = CapabilityLock(lister=lister).tree_records(root, scope)
    assert sorted(listed) == sorted(set(listed))
    assert records == CapabilityLock().tree_records(root, SCOPE)


def test_a_whole_tree_scope_covers_every_other_item(tmp_path: Path) -> None:
    root = _shipped(tmp_path)
    listed: list[str] = []

    def lister(folder: Path) -> Sequence[str]:
        listed.append(folder.relative_to(root).as_posix())
        return os.listdir(folder)

    whole = CapabilityLock(lister=lister).tree_records(root, [*SCOPE, PurePosixPath()])
    assert sorted(listed) == sorted(set(listed))
    assert whole == CapabilityLock().tree_records(root, [PurePosixPath()])


def test_a_scope_item_does_not_swallow_a_sibling_that_shares_its_name_prefix(
    tmp_path: Path,
) -> None:
    """`plugins/a` is not an ancestor of `plugins/ab`: the outermost walk compares path parts,
    never string prefixes, so both are walked and nothing under `plugins/ab` is lost."""
    root = _tree(
        tmp_path,
        {
            ".claude-plugin/marketplace.json": b"{}",
            "plugins/a/one.md": b"1",
            "plugins/ab/two.md": b"2",
        },
    )
    scope = [PurePosixPath("plugins/a"), PurePosixPath("plugins/ab")]
    paths = [record.path for record in CapabilityLock().tree_records(root, scope)]
    assert paths == ["plugins", "plugins/a", "plugins/a/one.md", "plugins/ab", "plugins/ab/two.md"]


# -- update: a read-modify-write under a file lock ----------------------------------------------


class _RecordingFlock:
    """Stands in for `fcntl.flock`, recording each call (no second process is needed)."""

    def __init__(self) -> None:
        self.calls: list[int] = []

    def __call__(self, descriptor: int, operation: int) -> None:
        os.fstat(descriptor)  # the descriptor is open while it is locked
        self.calls.append(operation)


def test_update_replaces_in_place_adds_at_the_end_and_drops(tmp_path: Path) -> None:
    lock_path = tmp_path / "state" / "loops.lock"
    CapabilityLock().write(lock_path, ENTRIES)
    flock = _RecordingFlock()
    newer = LockEntry("vibey", "vibey-engine 9.9.9", None, "sha256:" + "c" * 64)
    added = LockEntry("zeta", "https://example.test/zeta.git", None, "sha256:" + "d" * 64)
    result = CapabilityLock(flock=flock).update(lock_path, put=[added, newer], drop=["acme"])
    assert result == (newer, added)
    assert CapabilityLock().read(lock_path) == (newer, added)
    assert flock.calls == [fcntl.LOCK_EX]
    sidecar = lock_path.with_name(".loops.lock.flock")
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600


def test_update_of_a_missing_lock_makes_its_folder_and_the_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "new" / "loops.lock"
    assert CapabilityLock().update(lock_path, put=ENTRIES[:1]) == ENTRIES[:1]
    assert CapabilityLock().read(lock_path) == ENTRIES[:1]


def test_a_failed_update_leaves_the_lock_and_releases_the_file_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "loops.lock"
    CapabilityLock().write(lock_path, ENTRIES)
    before = lock_path.read_bytes()
    opened: list[int] = []

    def flock(descriptor: int, operation: int) -> None:
        opened.append(descriptor)

    bad = LockEntry("bad name!", "x", None, DIGEST)
    with pytest.raises(LockError):
        CapabilityLock(flock=flock).update(lock_path, put=[bad])
    assert lock_path.read_bytes() == before
    with pytest.raises(OSError):  # the sidecar's descriptor was closed, so its lock is gone
        os.fstat(opened[0])


def test_update_never_opens_its_sidecar_through_a_symlink(tmp_path: Path) -> None:
    lock_path = tmp_path / "loops.lock"
    target = tmp_path / "elsewhere"
    target.write_text("not the sidecar", encoding="utf-8")
    lock_path.with_name(".loops.lock.flock").symlink_to(target)
    with pytest.raises(OSError):
        CapabilityLock().update(lock_path, put=ENTRIES[:1])
    assert target.read_text(encoding="utf-8") == "not the sidecar"
    assert not lock_path.exists()
