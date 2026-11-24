# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Resolving a bundle into a locked, run-scoped snapshot (SP-LOOPS Task 6; design Decisions 1, 3
and 10; Review Focus 3).

A marketplace is used only as it was locked: its tree must hash to the lock's digest, the selected
plugins are copied into the run's own folder, and the copy is compared, record by record, with the
records that matched the lock -- so a file swapped after the check is caught, not loaded. The
shipped marketplace locks itself on first use; a person-added one never does.
"""

from __future__ import annotations

import json
import os
import stat
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path, PurePosixPath

import pytest
from fakes import symlink_loop

from vibey_runners.common.capabilities.bundle import BundleSpec
from vibey_runners.common.capabilities.capability_resolution_error import (
    CapabilityResolutionError,
)
from vibey_runners.common.capabilities.defaults import DEFAULT_MARKETPLACE_NAME
from vibey_runners.common.capabilities.interfaces.resolver_interface import (
    CapabilityResolverInterface,
)
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.lock_entry import LockEntry
from vibey_runners.common.capabilities.lock_mismatch_error import LockMismatchError
from vibey_runners.common.capabilities.manifest import MANIFEST_PATH
from vibey_runners.common.capabilities.marketplace_catalog import MarketplaceCatalog
from vibey_runners.common.capabilities.marketplace_spec import MarketplaceSpec
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.plugin_entry import PluginEntry
from vibey_runners.common.capabilities.plugin_spec import PluginSpec
from vibey_runners.common.capabilities.resolver import (
    DESCRIPTION_MAX_CHARS,
    LINK_NOT_COPIED,
    UNPLAIN_NAME,
    CapabilityResolver,
)
from vibey_runners.common.capabilities.safe_text import ELLIPSIS
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
from vibey_runners.common.capabilities.skill_entry import SkillEntry
from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot
from vibey_runners.common.capabilities.tree_record import TreeRecord
from vibey_runners.common.capabilities.unlocked_marketplace_error import (
    UnlockedMarketplaceError,
)

SHIPPED = Path(__file__).resolve().parents[4] / "vibey_tools" / "skills"
ACME_SOURCE = "https://example.test/acme.git"
RESEARCH = "currency-research"
SHIPPED_SOURCE = "vibey-engine 0.0.0+test"


def _skill_text(name: str, description: str | None = None) -> str:
    return f"---\nname: {name}\ndescription: {description or f'Does {name}.'}\n---\n\n# {name}\n"


def _market(root: Path, plugins: Mapping[str, Mapping[str, str]]) -> Path:
    """A marketplace at `root`: each plugin a folder of `skills/<folder>/SKILL.md`."""
    manifest = {
        "name": root.name,
        "plugins": [
            {"name": name, "source": f"./plugins/{name}", "description": f"The {name} plugin."}
            for name in plugins
        ],
    }
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin/marketplace.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name, skills in plugins.items():
        (root / "plugins" / name).mkdir(parents=True)
        (root / "plugins" / name / "README.md").write_text(f"# {name}\n", encoding="utf-8")
        for folder, text in skills.items():
            path = root / "plugins" / name / "skills" / folder / "SKILL.md"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
    return root


def _shipped(tmp_path: Path) -> Path:
    return _market(
        tmp_path / "shipped",
        {RESEARCH: {"audit": _skill_text("research-currency-audit-method")}},
    )


def _acme(tmp_path: Path, name: str = "acme") -> Path:
    return _market(tmp_path / name, {"linting": {"lint": _skill_text("lint")}})


def _bundle(raw: Mapping[str, object] | None = None) -> BundleSpec:
    return BundleSpec.from_mapping(raw or {})


def _acme_bundle(**extra: object) -> BundleSpec:
    return _bundle(
        {
            "marketplaces": [{"name": "acme", "source": ACME_SOURCE}],
            "plugins": ["linting@acme"],
            **extra,
        }
    )


def _shipped_digest(root: Path) -> str:
    """The shipped marketplace's scoped digest: its manifest and every plugin folder it lists."""
    listed = [PurePosixPath("plugins") / plugin.name for plugin in (root / "plugins").iterdir()]
    return CapabilityLock().digest_tree(root, [MANIFEST_PATH, *listed])


def _locked(name: str, root: Path, source: str = ACME_SOURCE, ref: str | None = None) -> LockEntry:
    return LockEntry(name, source, ref, CapabilityLock().digest_tree(root))


class CountingLock(CapabilityLock):
    """The real lock, counting how often it writes the lock file."""

    def __init__(self) -> None:
        super().__init__()
        self.writes = 0

    def write(self, path: Path, entries: Sequence[LockEntry]) -> None:
        self.writes += 1
        super().write(path, entries)


class SwappingLock(CapabilityLock):
    """The real lock, but the tree changes right after it is first hashed: a writer racing the
    run, between the lock check and the copy."""

    def __init__(self, swap: Callable[[], None]) -> None:
        super().__init__()
        self._swap: Callable[[], None] | None = swap

    def tree_records(
        self, root: Path, within: Sequence[PurePosixPath] | None = None
    ) -> tuple[TreeRecord, ...]:
        records = super().tree_records(root, within)
        if self._swap is not None:
            swap, self._swap = self._swap, None
            swap()
        return records


class FixedSkills:
    """A skill index that returns what it was given, to drive the resolver's own filtering."""

    def __init__(self, catalog: SkillCatalog) -> None:
        self._catalog = catalog

    def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
        return self._catalog


def _resolver(tmp_path: Path, **options: object) -> CapabilityResolver:
    state = tmp_path / "state"
    options.setdefault("shipped_source", SHIPPED_SOURCE)
    return CapabilityResolver(state / "loops.lock", state / "snapshots", **options)  # type: ignore[arg-type]


def _runs(tmp_path: Path) -> list[Path]:
    snapshots = tmp_path / "state" / "snapshots"
    return sorted(snapshots.iterdir()) if snapshots.exists() else []


# -- the shipped marketplace locks itself; nothing else does -------------------------------------


def test_the_default_bundle_resolves_from_the_shipped_marketplace(tmp_path: Path) -> None:
    shipped = _shipped(tmp_path)
    resolver = _resolver(tmp_path)
    snapshot = resolver.resolve(_bundle(), (), {DEFAULT_MARKETPLACE_NAME: shipped})
    assert isinstance(snapshot, CapabilitySnapshot)
    assert isinstance(resolver, CapabilityResolverInterface)
    assert [entry.name for entry in snapshot.skills.skills] == ["research-currency-audit-method"]
    assert snapshot.skills.skipped == ()
    assert [d.name for d in snapshot.plugin_dirs] == [RESEARCH]
    assert snapshot.mcp_servers == ()
    assert snapshot.digest.startswith("sha256:")


def test_the_shipped_marketplace_locks_itself_on_first_use_and_not_again(tmp_path: Path) -> None:
    shipped = _shipped(tmp_path)
    lock_path = tmp_path / "state" / "loops.lock"
    locker = CountingLock()
    resolver = _resolver(tmp_path, locker=locker)
    resolver.resolve(_bundle(), CapabilityLock().read(lock_path), {"vibey": shipped})
    entries = CapabilityLock().read(lock_path)
    assert entries == (LockEntry("vibey", SHIPPED_SOURCE, None, _shipped_digest(shipped)),)
    assert locker.writes == 1
    before = lock_path.read_bytes()
    resolver.resolve(_bundle(), entries, {"vibey": shipped})
    assert locker.writes == 1
    assert lock_path.read_bytes() == before


def test_locking_the_shipped_marketplace_keeps_every_other_entry(tmp_path: Path) -> None:
    shipped, acme = _shipped(tmp_path), _acme(tmp_path)
    lock_path = tmp_path / "state" / "loops.lock"
    CapabilityLock().write(lock_path, [_locked("acme", acme)])
    _resolver(tmp_path).resolve(_bundle(), CapabilityLock().read(lock_path), {"vibey": shipped})
    assert [entry.marketplace for entry in CapabilityLock().read(lock_path)] == ["acme", "vibey"]


def test_a_new_shipped_copy_locks_itself_again(tmp_path: Path) -> None:
    """An upgrade ships new content under a new source name: it is still the shipped copy, so it
    locks itself; the same name with different content is a mismatch (the next test)."""
    shipped = _shipped(tmp_path)
    lock_path = tmp_path / "state" / "loops.lock"
    old = _resolver(tmp_path, shipped_source="vibey-engine 1.0.0")
    first = old.resolve(_bundle(), (), {"vibey": shipped})
    (shipped / "plugins" / RESEARCH / "README.md").write_text("new release\n", encoding="utf-8")
    new = _resolver(tmp_path, shipped_source="vibey-engine 1.1.0")
    second = new.resolve(_bundle(), CapabilityLock().read(lock_path), {"vibey": shipped})
    (entry,) = CapabilityLock().read(lock_path)
    assert entry.source == "vibey-engine 1.1.0"
    assert entry.digest == _shipped_digest(shipped)
    assert first.digest != second.digest


def test_the_shipped_marketplace_changed_since_it_was_locked_is_refused(tmp_path: Path) -> None:
    shipped = _shipped(tmp_path)
    locker = CountingLock()
    entry = LockEntry("vibey", SHIPPED_SOURCE, None, _shipped_digest(shipped))
    (shipped / "plugins" / RESEARCH / "README.md").write_text("edited\n", encoding="utf-8")
    with pytest.raises(LockMismatchError, match="vibey loops marketplace update vibey") as error:
        _resolver(tmp_path, locker=locker).resolve(_bundle(), (entry,), {"vibey": shipped})
    assert error.value.name == "vibey"
    assert locker.writes == 0


def test_the_installed_release_must_be_named(tmp_path: Path) -> None:
    """No default: a caller that names no release would keep a stale lock across upgrades."""
    with pytest.raises(TypeError, match="shipped_source"):
        CapabilityResolver(tmp_path / "loops.lock", tmp_path / "snapshots")  # type: ignore[call-arg]


@pytest.mark.parametrize(
    "noise",
    [
        f"plugins/{RESEARCH}/scripts/__pycache__/tool.cpython-312.pyc",
        f"plugins/{RESEARCH}/scripts/tool.pyc",
        "__pycache__/x.cpython-314.pyc",
        "tests/test_sources.py",
        "src/vibey_skills/__init__.py",
        "README.md",
    ],
)
def test_the_shipped_lock_ignores_bytecode_and_what_sits_beside_the_marketplace(
    tmp_path: Path, noise: str
) -> None:
    """A source checkout shares the marketplace folder with sources and tests, and an import or
    an install writes bytecode into it: neither is a change to what the lock pins."""
    shipped = _shipped(tmp_path)
    (shipped / "plugins" / RESEARCH / "scripts").mkdir()
    (shipped / "plugins" / RESEARCH / "scripts" / "tool.py").write_text("print()\n")
    lock_path = tmp_path / "state" / "loops.lock"
    locker = CountingLock()
    resolver = _resolver(tmp_path, locker=locker)
    resolver.resolve(_bundle(), (), {"vibey": shipped})
    path = shipped / noise
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\0noise")
    snapshot = resolver.resolve(_bundle(), CapabilityLock().read(lock_path), {"vibey": shipped})
    assert locker.writes == 1
    (plugin,) = snapshot.plugin_dirs
    assert not any(
        part.name == "__pycache__" or part.suffix == ".pyc" for part in plugin.rglob("*")
    )


@pytest.mark.parametrize(
    "change",
    [
        f"plugins/{RESEARCH}/skills/audit/SKILL.md",
        "plugins/unselected/README.md",
        ".claude-plugin/marketplace.json",
    ],
)
def test_the_shipped_lock_sees_a_change_to_the_manifest_or_any_listed_plugin(
    tmp_path: Path, change: str
) -> None:
    shipped = _market(
        tmp_path / "shipped",
        {RESEARCH: {"audit": _skill_text("research-currency-audit-method")}, "unselected": {}},
    )
    lock_path = tmp_path / "state" / "loops.lock"
    _resolver(tmp_path).resolve(_bundle(), (), {"vibey": shipped})
    path = shipped / change
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(LockMismatchError, match="vibey loops marketplace update vibey"):
        _resolver(tmp_path).resolve(_bundle(), CapabilityLock().read(lock_path), {"vibey": shipped})


def test_no_plain_value_error_escapes_resolve(tmp_path: Path) -> None:
    """A plugin folder outside the root (a root retargeted between two reads) is a resolution
    error, not a bare `ValueError` from `relative_to`."""
    acme = _acme(tmp_path)

    class Elsewhere:
        def read(self, root: Path) -> MarketplaceCatalog:
            entry = PluginEntry("linting", tmp_path / "elsewhere", "")
            return MarketplaceCatalog({"linting": entry}, ())

    with pytest.raises(CapabilityResolutionError, match="outside") as error:
        _resolver(tmp_path, manifest=Elsewhere()).resolve(
            _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
        )
    assert type(error.value) is CapabilityResolutionError


def test_a_recursion_error_from_a_collaborator_becomes_a_resolution_error(
    tmp_path: Path,
) -> None:
    acme = _acme(tmp_path)

    class TooDeep:
        def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
            raise RecursionError("maximum recursion depth exceeded")

    with pytest.raises(CapabilityResolutionError, match="maximum recursion depth") as error:
        _resolver(tmp_path, skills=TooDeep()).resolve(
            _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
        )
    assert type(error.value) is CapabilityResolutionError
    assert _runs(tmp_path) == []


def test_a_value_error_from_a_collaborator_becomes_a_resolution_error(tmp_path: Path) -> None:
    acme = _acme(tmp_path)

    class Broken:
        def build(self, plugin_dirs: Sequence[Path]) -> SkillCatalog:
            raise ValueError("an index that could not be built")

    with pytest.raises(CapabilityResolutionError, match="could not be built"):
        _resolver(tmp_path, skills=Broken()).resolve(
            _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
        )
    assert _runs(tmp_path) == []


def test_a_shipped_root_that_is_a_symlink_loop_is_the_same_error_on_every_python(
    tmp_path: Path,
) -> None:
    root = symlink_loop(tmp_path / "shipped")
    with pytest.raises(CapabilityResolutionError) as error:
        _resolver(tmp_path).resolve(_bundle(), (), {"vibey": root})
    assert type(error.value) is CapabilityResolutionError
    assert (
        str(error.value) == f"the marketplace vibey: the marketplace folder {root} does not exist"
    )
    assert _runs(tmp_path) == []


def test_a_locked_root_that_is_a_symlink_loop_is_the_same_error_on_every_python(
    tmp_path: Path,
) -> None:
    acme = _acme(tmp_path)
    entry = _locked("acme", acme)
    loop = symlink_loop(tmp_path / "loop")
    with pytest.raises(CapabilityResolutionError) as error:
        _resolver(tmp_path).resolve(_acme_bundle(), (entry,), {"acme": loop})
    assert type(error.value) is CapabilityResolutionError
    assert str(error.value) == f"the marketplace acme cannot be read: {loop} is not a folder"


def test_a_locked_plugin_source_that_is_a_symlink_loop_is_the_same_error_on_every_python(
    tmp_path: Path,
) -> None:
    acme = _acme(tmp_path)
    manifest = acme / ".claude-plugin/marketplace.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["plugins"][0]["source"] = "./plugins/loop"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    symlink_loop(acme / "plugins" / "loop")
    with pytest.raises(CapabilityResolutionError) as error:
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    assert type(error.value) is CapabilityResolutionError
    assert (
        str(error.value) == "the marketplace acme has no plugin linting: its folder does not exist"
    )
    assert _runs(tmp_path) == []


def test_a_damaged_lock_file_stops_the_shipped_marketplace_locking_itself(tmp_path: Path) -> None:
    lock_path = tmp_path / "state" / "loops.lock"
    lock_path.parent.mkdir()
    lock_path.write_text('{"version": 1', encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="vibey cannot lock itself"):
        _resolver(tmp_path).resolve(_bundle(), (), {"vibey": _shipped(tmp_path)})
    assert lock_path.read_text(encoding="utf-8") == '{"version": 1'


def test_a_lock_folder_that_cannot_be_written_is_a_resolution_error(tmp_path: Path) -> None:
    (tmp_path / "state").write_text("a file where the lock folder should be", encoding="utf-8")
    resolver = CapabilityResolver(
        tmp_path / "state" / "loops.lock", tmp_path / "snapshots", shipped_source=SHIPPED_SOURCE
    )
    with pytest.raises(CapabilityResolutionError, match="cannot lock itself"):
        resolver.resolve(_bundle(), (), {"vibey": _shipped(tmp_path)})


def test_a_tree_the_file_system_refuses_is_a_resolution_error(tmp_path: Path) -> None:
    class Refusing(CapabilityLock):
        def tree_records(
            self, root: Path, within: Sequence[PurePosixPath] | None = None
        ) -> tuple[TreeRecord, ...]:
            raise PermissionError(13, "Permission denied", str(root))

    acme = _acme(tmp_path)
    with pytest.raises(CapabilityResolutionError, match="acme cannot be read: .*Permission denied"):
        _resolver(tmp_path, locker=Refusing()).resolve(
            _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
        )


def test_an_unlocked_network_marketplace_names_the_command_to_run(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    locker = CountingLock()
    missing_lock = CapabilityLock().read(tmp_path / "no-such.lock")
    assert missing_lock == ()  # a missing lock file is no entries ...
    with pytest.raises(UnlockedMarketplaceError) as error:  # ... and never locks itself
        _resolver(tmp_path, locker=locker).resolve(_acme_bundle(), missing_lock, {"acme": acme})
    assert error.value.name == "acme"
    assert "run `vibey loops marketplace update acme`" in str(error.value)
    assert locker.writes == 0
    assert not (tmp_path / "state" / "loops.lock").exists()
    assert _runs(tmp_path) == []


def test_a_network_marketplace_changed_after_it_was_locked_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    entry = _locked("acme", acme)
    (acme / "plugins/linting/skills/lint/SKILL.md").write_text(_skill_text("lint", "Evil."))
    with pytest.raises(LockMismatchError, match="vibey loops marketplace update acme") as error:
        _resolver(tmp_path).resolve(_acme_bundle(), (entry,), {"acme": acme})
    assert error.value.name == "acme"
    assert "changed" in str(error.value)


def test_a_lock_for_another_source_or_ref_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    for entry in (
        _locked("acme", acme, source="https://example.test/other.git"),
        _locked("acme", acme, ref="v2"),
    ):
        with pytest.raises(LockMismatchError, match="pins") as error:
            _resolver(tmp_path).resolve(_acme_bundle(), (entry,), {"acme": acme})
        assert error.value.name == "acme"


def test_a_locked_network_marketplace_resolves(tmp_path: Path) -> None:
    shipped, acme = _shipped(tmp_path), _acme(tmp_path)
    bundle = _acme_bundle(plugins=[f"{RESEARCH}@vibey", "linting@acme"])
    snapshot = _resolver(tmp_path).resolve(
        bundle, (_locked("acme", acme),), {"vibey": shipped, "acme": acme}
    )
    assert [d.name for d in snapshot.plugin_dirs] == [RESEARCH, "linting"]
    assert [(s.plugin, s.name) for s in snapshot.skills.skills] == [
        (RESEARCH, "research-currency-audit-method"),
        ("linting", "lint"),
    ]


# -- the snapshot is a verified copy ----------------------------------------------------------------


def test_the_snapshot_is_a_private_copy_with_no_links(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    snapshot = _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    (plugin,) = snapshot.plugin_dirs
    (run,) = _runs(tmp_path)
    assert plugin.is_relative_to(run)
    assert not plugin.is_relative_to(acme)
    assert stat.S_IMODE(os.stat(run).st_mode) == 0o700
    for folder, folders, files in os.walk(run):
        for name in folders:
            assert stat.S_IMODE(os.lstat(Path(folder, name)).st_mode) == 0o700
        for name in files:
            status = os.lstat(Path(folder, name))
            assert stat.S_ISREG(status.st_mode)
            assert status.st_nlink == 1
    (skill,) = snapshot.skills.skills
    assert skill.path.is_relative_to(run)
    (acme / "plugins/linting/skills/lint/SKILL.md").write_text("changed later\n")
    assert skill.path.read_text(encoding="utf-8") == _skill_text("lint")


def test_a_file_swapped_after_the_lock_check_is_caught_and_never_loaded(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    entry = _locked("acme", acme)
    skill = acme / "plugins/linting/skills/lint/SKILL.md"
    locker = SwappingLock(lambda: skill.write_text(_skill_text("lint", "Swapped in.")))
    with pytest.raises(LockMismatchError, match="while it was copied") as error:
        _resolver(tmp_path, locker=locker).resolve(_acme_bundle(), (entry,), {"acme": acme})
    assert error.value.name == "acme"
    assert _runs(tmp_path) == []  # the unverified copy is removed


def test_a_folder_swapped_for_a_symlink_after_the_check_is_caught(tmp_path: Path) -> None:
    """`O_NOFOLLOW` guards only the last path component; the copy's verification guards the
    rest."""
    acme = _acme(tmp_path)
    entry = _locked("acme", acme)
    decoy = _market(tmp_path / "decoy", {"linting": {"lint": _skill_text("lint", "Decoy.")}})

    def swap() -> None:
        skills = acme / "plugins/linting/skills"
        skills.rename(tmp_path / "moved-away")
        skills.symlink_to(decoy / "plugins/linting/skills")

    with pytest.raises(LockMismatchError, match="while it was copied"):
        _resolver(tmp_path, locker=SwappingLock(swap)).resolve(
            _acme_bundle(), (entry,), {"acme": acme}
        )


def test_a_symlink_in_a_plugin_is_never_copied_and_is_named(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    outside = _market(tmp_path / "outside", {"x": {"other": _skill_text("other")}})
    (acme / "plugins/linting/skills/linked").symlink_to(outside / "plugins/x/skills/other")
    snapshot = _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    (plugin,) = snapshot.plugin_dirs
    assert [s.name for s in snapshot.skills.skills] == ["lint"]
    assert not os.path.lexists(plugin / "skills/linked")
    assert (plugin / "skills/linked", LINK_NOT_COPIED) in snapshot.skills.skipped


def test_an_entry_whose_name_is_not_plain_is_never_copied_and_renders_safely(
    tmp_path: Path,
) -> None:
    """A skipped row keeps a real `Path`, and every path a row can carry is renderable: an
    entry named with ESC/CSI, a newline or a bidi override is not copied, and the row naming it
    is its (plain) parent folder with the name escaped in the reason."""
    acme = _acme(tmp_path)
    hostile_file = "\x1b[31mred\nline\u202e.md"
    hostile_folder = "\x1b[2Jwipe\u202e"
    skills = acme / "plugins/linting/skills"
    (skills / "lint" / hostile_file).write_text("hidden\n", encoding="utf-8")
    (skills / hostile_folder).mkdir()
    (skills / hostile_folder / "SKILL.md").write_text(_skill_text("evil"), encoding="utf-8")
    snapshot = _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    (plugin,) = snapshot.plugin_dirs
    assert [s.name for s in snapshot.skills.skills] == ["lint"]
    assert not (plugin / "skills/lint" / hostile_file).exists()
    assert not (plugin / "skills" / hostile_folder).exists()
    rows = dict(snapshot.skills.skipped)
    assert rows[plugin / "skills/lint"] == UNPLAIN_NAME.format(ascii(hostile_file))
    assert rows[plugin / "skills"] == UNPLAIN_NAME.format(ascii(hostile_folder))
    for path, reason in snapshot.skills.skipped:
        assert isinstance(path, Path)
        assert str(path).isprintable() and reason.isprintable()


def test_a_snapshot_past_its_entry_cap_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    with pytest.raises(CapabilityResolutionError, match="more than 3 entries"):
        _resolver(tmp_path, max_snapshot_entries=3).resolve(
            _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
        )
    assert _runs(tmp_path) == []


def test_a_snapshot_past_its_byte_cap_is_refused(tmp_path: Path) -> None:
    shipped, acme = _shipped(tmp_path), _acme(tmp_path)
    bundle = _acme_bundle(plugins=[f"{RESEARCH}@vibey", "linting@acme"])
    first = sum(
        len(p.read_bytes()) for p in [*(shipped / "plugins" / RESEARCH).rglob("*.md")]
    ) + len((shipped / ".claude-plugin/marketplace.json").read_bytes())
    with pytest.raises(CapabilityResolutionError, match="bytes"):
        _resolver(tmp_path, max_snapshot_bytes=first + 1).resolve(
            bundle, (_locked("acme", acme),), {"vibey": shipped, "acme": acme}
        )
    assert _runs(tmp_path) == []


# -- what a model or a terminal will see -----------------------------------------------------------


def test_skill_descriptions_are_capped_and_stripped_of_control_characters(tmp_path: Path) -> None:
    raw = "Paints \x1b[31mred\x1b[0m and \u202ereverses\u202c " + "very " * 400
    acme = _market(tmp_path / "acme", {"linting": {"lint": _skill_text("lint", json.dumps(raw))}})
    snapshot = _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    (skill,) = snapshot.skills.skills
    assert skill.description.startswith("Paints [31mred[0m and reverses very")
    assert "\x1b" not in skill.description and "\u202e" not in skill.description
    assert DESCRIPTION_MAX_CHARS - 5 <= len(skill.description) <= DESCRIPTION_MAX_CHARS
    assert skill.description.endswith(ELLIPSIS)


def test_the_description_cap_is_configurable(tmp_path: Path) -> None:
    acme = _market(
        tmp_path / "acme", {"linting": {"lint": _skill_text("lint", "a b c d e f g h i j k")}}
    )
    snapshot = _resolver(tmp_path, description_limit=8).resolve(
        _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
    )
    assert snapshot.skills.skills[0].description == "a b c" + ELLIPSIS


def test_skipped_reasons_are_stripped_of_control_characters(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    where = tmp_path / "x"
    catalog = SkillCatalog((), ((where, "cannot be read: \x1b]0;pwned\x07 \u202eok"),))
    snapshot = _resolver(tmp_path, skills=FixedSkills(catalog)).resolve(
        _acme_bundle(), (_locked("acme", acme),), {"acme": acme}
    )
    assert snapshot.skills.skipped == ((where, "cannot be read: ]0;pwned ok"),)


def test_a_skill_name_two_plugins_share_goes_to_the_first_in_bundle_order(tmp_path: Path) -> None:
    shipped = _market(tmp_path / "shipped", {RESEARCH: {"s": _skill_text("shared")}})
    acme = _market(tmp_path / "acme", {"linting": {"s": _skill_text("shared", "Second.")}})
    bundle = _acme_bundle(plugins=["linting@acme", f"{RESEARCH}@vibey"])
    snapshot = _resolver(tmp_path).resolve(
        bundle, (_locked("acme", acme),), {"vibey": shipped, "acme": acme}
    )
    (kept,) = snapshot.skills.skills
    assert (kept.plugin, kept.description) == ("linting", "Second.")
    ((path, reason),) = snapshot.skills.skipped
    assert path.is_relative_to(snapshot.plugin_dirs[1])
    assert reason == "names the skill shared, which the plugin linting already provides"


# -- disabled names, the digest -------------------------------------------------------------------


def test_disabled_names_are_absent_from_the_snapshot(tmp_path: Path) -> None:
    shipped = _market(
        tmp_path / "shipped",
        {RESEARCH: {"a": _skill_text("keep-me"), "b": _skill_text("drop-me")}},
    )
    bundle = _bundle(
        {
            "marketplaces": [{"name": "acme", "source": ACME_SOURCE}],
            "plugins": [f"{RESEARCH}@vibey", "linting@acme"],
            "mcp_servers": [
                {"name": "files", "trust": "local", "command": ["fake-mcp"]},
                {"name": "tickets", "trust": "remote", "url": "https://mcp.example.test/"},
            ],
            "disable": ["linting", "files", "drop-me"],
        }
    )
    # `linting` is disabled, so `acme` is not needed: no lock and no root for it are asked for.
    snapshot = _resolver(tmp_path).resolve(bundle, (), {"vibey": shipped})
    assert [d.name for d in snapshot.plugin_dirs] == [RESEARCH]
    assert [s.name for s in snapshot.skills.skills] == ["keep-me"]
    assert all("drop-me" not in reason for _, reason in snapshot.skills.skipped)
    assert [s.name for s in snapshot.mcp_servers] == ["tickets"]


def test_a_bundle_built_by_hand_is_narrowed_by_its_disabled_names_too(tmp_path: Path) -> None:
    server = McpServerSpec("files", "local", ("fake-mcp",), None, ())
    bundle = BundleSpec(
        (), (PluginSpec(RESEARCH, "vibey"),), (server,), (), frozenset({RESEARCH, "files"})
    )
    snapshot = _resolver(tmp_path).resolve(bundle, (), {})
    assert snapshot.plugin_dirs == () and snapshot.mcp_servers == ()


def test_the_same_inputs_give_the_same_digest(tmp_path: Path) -> None:
    shipped, acme = _shipped(tmp_path), _acme(tmp_path)
    bundle = _acme_bundle(plugins=[f"{RESEARCH}@vibey", "linting@acme"])
    lock_path = tmp_path / "state" / "loops.lock"
    roots = {"vibey": shipped, "acme": acme}
    resolver = _resolver(tmp_path)
    first = resolver.resolve(bundle, (_locked("acme", acme),), roots)
    entries = CapabilityLock().read(lock_path) + (_locked("acme", acme),)
    second = resolver.resolve(bundle, entries, roots)
    assert first.digest == second.digest
    assert first.plugin_dirs != second.plugin_dirs  # two runs, two folders, one digest
    other = resolver.resolve(_acme_bundle(skills=["lint"]), entries, roots)
    assert other.digest != first.digest


def test_the_digest_covers_the_lock_entries_it_used(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    resolver = _resolver(tmp_path)
    first = resolver.resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    (acme / "plugins/linting/README.md").write_text("an update\n", encoding="utf-8")
    second = resolver.resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    assert first.digest != second.digest
    unrelated = LockEntry("other", ACME_SOURCE, None, "sha256:" + "c" * 64)
    third = resolver.resolve(_acme_bundle(), (_locked("acme", acme), unrelated), {"acme": acme})
    assert third.digest == second.digest


def test_a_bundle_with_no_plugins_still_gets_a_run_folder(tmp_path: Path) -> None:
    """The run's capability document is written into the run's folder, so every resolve makes
    one, even when the bundle enables no plugin (SP-LOOPS Phase 4, Task 2)."""
    snapshot = _resolver(tmp_path).resolve(_bundle({"plugins": []}), (), {})
    assert snapshot.plugin_dirs == ()
    assert snapshot.skills == SkillCatalog((), ())
    assert snapshot.digest.startswith("sha256:")
    assert _runs(tmp_path) == [snapshot.folder]
    assert stat.S_IMODE(os.stat(snapshot.folder).st_mode) == 0o700
    assert list(snapshot.folder.iterdir()) == []


def test_the_snapshot_names_its_run_folder_and_every_plugin_is_inside_it(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    snapshot = _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    assert _runs(tmp_path) == [snapshot.folder]
    assert all(plugin.is_relative_to(snapshot.folder) for plugin in snapshot.plugin_dirs)


def test_a_failed_resolve_leaves_no_run_folder(tmp_path: Path) -> None:
    """The guarantee holds for the folder every resolve now makes: a refusal before any
    marketplace is read (an undeclared marketplace, an unlocked one) leaves nothing behind."""
    acme = _acme(tmp_path)
    undeclared = BundleSpec((), (PluginSpec("linting", "acme"),), (), (), frozenset())
    with pytest.raises(CapabilityResolutionError, match="does not declare"):
        _resolver(tmp_path).resolve(undeclared, (), {"acme": acme})
    assert _runs(tmp_path) == []
    with pytest.raises(UnlockedMarketplaceError):
        _resolver(tmp_path).resolve(_acme_bundle(), (), {"acme": acme})
    assert _runs(tmp_path) == []


def test_a_snapshot_folder_that_cannot_be_made_is_a_resolution_error(tmp_path: Path) -> None:
    (tmp_path / "state").mkdir()
    (tmp_path / "state" / "snapshots").write_text("a file, not a folder", encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="snapshot folder cannot be made"):
        _resolver(tmp_path).resolve(_bundle({"plugins": []}), (), {})


def test_the_digest_changes_when_builtin_web_changes_and_not_when_the_max_age_does(
    tmp_path: Path,
) -> None:
    resolver = _resolver(tmp_path)

    def digest(**raw: object) -> str:
        return resolver.resolve(_bundle({"plugins": [], **raw}), (), {}).digest

    base = digest()
    assert digest(builtin_web=True) != base
    assert digest(instruction_files=["CLAUDE.md"]) != base
    assert digest(instruction_max_bytes=1024) != base
    assert digest(snapshot_max_age_days=30) == base
    assert digest(builtin_web=False) == base


def test_the_digest_changes_with_either_token_budget(tmp_path: Path) -> None:
    """Both budgets shape what a loop is given (R8), so each enters the digest; naming the
    default changes nothing."""
    resolver = _resolver(tmp_path)

    def digest(**raw: object) -> str:
        return resolver.resolve(_bundle({"plugins": [], **raw}), (), {}).digest

    base = digest()
    prompt = digest(capability_prompt_tokens=4096)
    answer = digest(capability_answer_tokens=256)
    assert len({base, prompt, answer}) == 3
    assert digest(capability_prompt_tokens=3072, capability_answer_tokens=3000) == base


# -- where things are read from: never the project -------------------------------------------------


def test_a_source_is_never_read_as_a_folder(tmp_path: Path) -> None:
    """The bundle's `source` says where `update` fetches from; a run reads only the root it is
    handed, from the person's own lock folder, never a folder the source names."""
    acme = _acme(tmp_path)
    elsewhere = _market(tmp_path / "project", {"linting": {"lint": _skill_text("lint", "Evil.")}})
    bundle = _bundle(
        {"marketplaces": [{"name": "acme", "source": str(elsewhere)}], "plugins": ["linting@acme"]}
    )
    entry = _locked("acme", acme, source=str(elsewhere))
    snapshot = _resolver(tmp_path).resolve(bundle, (entry,), {"acme": acme})
    assert snapshot.skills.skills[0].description == "Does lint."


def test_a_used_marketplace_with_no_root_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    with pytest.raises(CapabilityResolutionError, match="no folder"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {})


def test_a_relative_root_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    relative = Path(os.path.relpath(acme))
    with pytest.raises(CapabilityResolutionError, match="absolute"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": relative})


@pytest.mark.parametrize("which", ["lock", "snapshots"])
def test_relative_lock_and_snapshot_folders_are_refused(tmp_path: Path, which: str) -> None:
    lock_path, snapshots = tmp_path / "loops.lock", tmp_path / "snapshots"
    if which == "lock":
        lock_path = Path("loops.lock")
    else:
        snapshots = Path("snapshots")
    with pytest.raises(CapabilityResolutionError, match="absolute"):
        CapabilityResolver(lock_path, snapshots, shipped_source=SHIPPED_SOURCE)


@pytest.mark.parametrize("source", ["", "-oops", "bad\nsource"])
def test_a_shipped_source_name_is_held_to_the_lock_rule(tmp_path: Path, source: str) -> None:
    with pytest.raises(CapabilityResolutionError, match="shipped_source"):
        _resolver(tmp_path, shipped_source=source)


@pytest.mark.parametrize(
    "option", ["description_limit", "max_snapshot_entries", "max_snapshot_bytes"]
)
def test_a_limit_below_one_is_refused(tmp_path: Path, option: str) -> None:
    with pytest.raises(ValueError, match=option):
        _resolver(tmp_path, **{option: 0})


# -- bundles and locks that do not add up ----------------------------------------------------------


def test_a_network_marketplace_may_not_take_the_shipped_name(tmp_path: Path) -> None:
    shipped = _shipped(tmp_path)
    bundle = BundleSpec(
        (MarketplaceSpec("vibey", ACME_SOURCE, None),),
        (PluginSpec(RESEARCH, "vibey"),),
        (),
        (),
        frozenset(),
    )
    locker = CountingLock()
    with pytest.raises(CapabilityResolutionError, match="reserved"):
        _resolver(tmp_path, locker=locker).resolve(bundle, (), {"vibey": shipped})
    assert locker.writes == 0


def test_a_plugin_from_an_undeclared_marketplace_is_refused(tmp_path: Path) -> None:
    bundle = BundleSpec((), (PluginSpec("linting", "acme"),), (), (), frozenset())
    with pytest.raises(CapabilityResolutionError, match="does not declare"):
        _resolver(tmp_path).resolve(bundle, (), {"acme": _acme(tmp_path)})


def test_a_marketplace_name_that_is_not_a_plain_name_is_refused(tmp_path: Path) -> None:
    bundle = BundleSpec(
        (MarketplaceSpec("../up", ACME_SOURCE, None),),
        (PluginSpec("linting", "../up"),),
        (),
        (),
        frozenset(),
    )
    with pytest.raises(CapabilityResolutionError, match="plain name"):
        _resolver(tmp_path).resolve(bundle, (), {"../up": _acme(tmp_path)})


def test_a_lock_naming_a_marketplace_twice_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    twice = (_locked("acme", acme), _locked("acme", acme))
    with pytest.raises(CapabilityResolutionError, match="twice"):
        _resolver(tmp_path).resolve(_acme_bundle(), twice, {"acme": acme})


def test_a_plugin_the_marketplace_does_not_list_is_refused(tmp_path: Path) -> None:
    acme = _market(tmp_path / "acme", {"formatting": {}})
    with pytest.raises(CapabilityResolutionError, match="acme has no plugin linting"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})


def test_a_plugin_the_marketplace_cannot_use_here_names_why(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    manifest = acme / ".claude-plugin/marketplace.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["plugins"][0]["source"] = {"source": "github", "repo": "acme/linting"}
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="not a folder in the marketplace"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})


def test_a_plugin_folder_reached_through_a_symlink_is_not_in_the_snapshot(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    (acme / "plugins/alias").symlink_to("linting")
    manifest = acme / ".claude-plugin/marketplace.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["plugins"][0]["source"] = "./plugins/alias"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="linting is not in the snapshot"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})


def test_a_manifest_reached_through_a_symlink_is_not_in_the_snapshot(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    (acme / ".claude-plugin").rename(acme / "meta")
    (acme / ".claude-plugin").symlink_to("meta")
    with pytest.raises(CapabilityResolutionError, match="has no .claude-plugin"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})
    assert _runs(tmp_path) == []


def test_a_manifest_that_leaves_the_marketplace_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    manifest = acme / ".claude-plugin/marketplace.json"
    document = json.loads(manifest.read_text(encoding="utf-8"))
    document["plugins"][0]["source"] = "../elsewhere"
    manifest.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(CapabilityResolutionError, match="climbs out"):
        _resolver(tmp_path).resolve(_acme_bundle(), (_locked("acme", acme),), {"acme": acme})


def test_a_root_that_is_gone_is_refused(tmp_path: Path) -> None:
    acme = _acme(tmp_path)
    entry = _locked("acme", acme)
    with pytest.raises(CapabilityResolutionError, match="not a folder"):
        _resolver(tmp_path).resolve(_acme_bundle(), (entry,), {"acme": tmp_path / "gone"})


# -- the real shipped marketplace, from this checkout ----------------------------------------------


def test_the_research_skills_resolve_from_the_marketplace_this_checkout_ships(
    tmp_path: Path,
) -> None:
    snapshot = _resolver(tmp_path).resolve(_bundle(), (), {"vibey": SHIPPED})
    names = {skill.name for skill in snapshot.skills.skills}
    assert {
        "research-search-and-source-quality",
        "research-currency-audit-method",
        "research-editing-a-reference-skill",
    } <= names
    assert all(skill.plugin == RESEARCH for skill in snapshot.skills.skills)
    assert all(isinstance(skill, SkillEntry) for skill in snapshot.skills.skills)


# -- lock_shipped: what `vibey loops marketplace update vibey` does ------------------------------


def test_lock_shipped_relocks_the_shipped_marketplace_whatever_the_lock_held(
    tmp_path: Path,
) -> None:
    """The same release with other content is a mismatch for a run, so the person needs a way to
    accept it: `lock_shipped` re-hashes the shipped tree and writes it, keeping every other
    entry."""
    shipped = _shipped(tmp_path)
    lock_path = tmp_path / "state" / "loops.lock"
    acme = _acme(tmp_path)
    CapabilityLock().write(
        lock_path,
        [LockEntry("vibey", SHIPPED_SOURCE, None, "sha256:" + "0" * 64), _locked("acme", acme)],
    )
    (shipped / "plugins" / RESEARCH / "README.md").write_text("edited\n", encoding="utf-8")
    entry = _resolver(tmp_path).lock_shipped(shipped)
    assert entry == LockEntry("vibey", SHIPPED_SOURCE, None, _shipped_digest(shipped))
    assert CapabilityLock().read(lock_path) == (entry, _locked("acme", acme))
    snapshot = _resolver(tmp_path).resolve(_bundle(), (entry,), {"vibey": shipped})
    assert [d.name for d in snapshot.plugin_dirs] == [RESEARCH]


def test_lock_shipped_needs_an_absolute_root(tmp_path: Path) -> None:
    with pytest.raises(CapabilityResolutionError, match="absolute"):
        _resolver(tmp_path).lock_shipped(Path("relative/shipped"))


def test_lock_shipped_of_an_unreadable_tree_writes_nothing(tmp_path: Path) -> None:
    root = symlink_loop(tmp_path / "shipped")
    with pytest.raises(CapabilityResolutionError, match="does not exist"):
        _resolver(tmp_path).lock_shipped(root)
    assert not (tmp_path / "state" / "loops.lock").exists()


def test_lock_shipped_wraps_a_value_or_recursion_error(tmp_path: Path) -> None:
    class TooDeep:
        def read(self, root: Path) -> MarketplaceCatalog:
            raise RecursionError("maximum recursion depth exceeded")

    with pytest.raises(CapabilityResolutionError, match="cannot lock: maximum recursion") as error:
        _resolver(tmp_path, manifest=TooDeep()).lock_shipped(_shipped(tmp_path))
    assert type(error.value) is CapabilityResolutionError
