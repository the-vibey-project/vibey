# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the local stack catalogue."""

from __future__ import annotations

import pytest

from vibey.domain.interfaces.local_stack_interface import (
    DependencyReportInterface,
    DependencySpecInterface,
    LocalStackCatalogueInterface,
    LocalStackReportInterface,
)
from vibey.domain.local_stack import (
    CATALOGUE_ENTRIES,
    DEFAULT_LOCAL_MODEL,
    DependencyReport,
    DependencyState,
    HostOs,
    LocalStackCatalogue,
    LocalStackReport,
    UnknownDependency,
)

# 1. Constant


def test_default_local_model_is_gpt_oss_20b():
    assert DEFAULT_LOCAL_MODEL == "gpt-oss:20b"


# 2. Core entries have recipes for both default OSes


def test_core_entries_have_a_recipe_for_both_default_oses():
    for entry in CATALOGUE_ENTRIES:
        assert entry.recipe(HostOs.ARCH) is not None
        assert entry.recipe(HostOs.MACOS) is not None


# 3. Every entry has package names unless source is NONE


def test_every_entry_has_package_names_unless_its_source_is_none():
    for entry in CATALOGUE_ENTRIES:
        for recipe in (entry.arch, entry.macos):
            if recipe is None:
                continue
            pkg = recipe.package
            if pkg.source == "none":
                continue
            assert pkg.names, f"{entry.key} missing package names"


# 4. Resolve defaults keep declaration order


def test_resolve_defaults_keep_declaration_order():
    catalog = LocalStackCatalogue()
    resolved = catalog.resolve(HostOs.ARCH)
    assert [e.key for e in resolved] == [e.key for e in catalog.entries()]


# 5. Resolve only pulls in requirements


def test_resolve_only_pulls_in_requirements():
    catalog = LocalStackCatalogue()
    resolved = catalog.resolve(HostOs.ARCH, only=("model",))
    keys = {e.key for e in resolved}
    assert "model" in keys
    assert "ollama" in keys


# 6. Resolve exclude drops the model


def test_resolve_exclude_drops_the_model():
    catalog = LocalStackCatalogue()
    resolved = catalog.resolve(HostOs.ARCH, exclude=("model",))
    assert all(e.key != "model" for e in resolved)


# 7. Resolve expands a group name


def test_resolve_expands_a_group_name():
    catalog = LocalStackCatalogue()
    resolved = catalog.resolve(HostOs.ARCH, only=("services",))
    assert {e.key for e in resolved} == {"postgres", "ollama", "model"}


# 8. Resolve rejects unknown name and lists known ones


def test_resolve_rejects_an_unknown_name_and_lists_the_known_ones():
    catalog = LocalStackCatalogue()
    with pytest.raises(Exception) as exc:
        catalog.resolve(HostOs.ARCH, only=("nonexistent",))
    assert "nonexistent" in str(exc.value)


# 9. Unsupported host resolves to nothing unless named


def test_unsupported_host_resolves_to_nothing_unless_named():
    catalog = LocalStackCatalogue()
    assert catalog.resolve(None) == ()
    named = catalog.resolve(None, only=("postgres",))
    assert len(named) == 1


# 10. Catalogue rejects duplicate keys and forward requirements


def test_catalogue_rejects_duplicate_keys_and_forward_requirements():
    from vibey.domain.local_stack import DependencySpec, InstallerKind

    dup_entries = (
        DependencySpec(
            key="dup",
            title="dup",
            group="s",
            default=True,
            installer=InstallerKind.PACKAGE,
            arch=None,
            macos=None,
        ),
    )
    # `match=`, not a bare ValueError: this test passed for two months against a guard that
    # rejected every custom catalogue, so it never once reached the duplicate-key check the
    # spec requires. A bare `raises` asserts that something went wrong, not that the right
    # thing did.
    # `dup_entries * 2`, not `dup_entries + CATALOGUE_ENTRIES`: "dup" appears nowhere in the
    # catalogue, so prepending it created no duplicate at all. The fixture never built the
    # condition its name claims, and the assertion never checked which error it got -- two
    # independent faults that cancelled into a green test.
    with pytest.raises(ValueError, match="duplicate key"):
        LocalStackCatalogue(entries=dup_entries * 2 + CATALOGUE_ENTRIES)

    forward = (
        DependencySpec(
            key="needs-later",
            title="needs later",
            group="s",
            default=True,
            installer=InstallerKind.PACKAGE,
            arch=None,
            macos=None,
            requires=("ollama",),
        ),
    )
    with pytest.raises(ValueError, match="forward dependency"):
        LocalStackCatalogue(entries=forward + CATALOGUE_ENTRIES)


# 12. No recipe pipes a remote script into a shell


def test_no_recipe_pipes_a_remote_script_into_a_shell():
    danger = {"curl", "wget", "sh", "bash", "zsh"}
    for entry in CATALOGUE_ENTRIES:
        for recipe in (entry.arch, entry.macos):
            if recipe is None:
                continue
            probe = recipe.probe
            if probe:
                assert probe.argv[0] not in danger
            for cmd in recipe.post_install:
                assert cmd[0] not in danger


# 13. Reports are ok only when ready and a stack is ok when all are


def test_reports_are_ok_only_when_ready_and_a_stack_is_ok_when_all_are():
    rep_ready = DependencyReport(key="a", state=DependencyState.READY, detail="")
    stack = LocalStackReport(host_label="x", reports=(rep_ready,))
    assert stack.ok
    rep_missing = DependencyReport(key="b", state=DependencyState.MISSING, detail="")
    stack = LocalStackReport(host_label="x", reports=(rep_ready, rep_missing))
    assert not stack.ok


# 14. Implementations satisfy their interfaces


def test_implementations_satisfy_their_interfaces():
    catalog = LocalStackCatalogue()
    assert isinstance(catalog, LocalStackCatalogueInterface)
    assert isinstance(catalog.entries()[0], DependencySpecInterface)
    rep = DependencyReport(key="k", state=DependencyState.READY, detail="")
    assert isinstance(rep, DependencyReportInterface)
    stack = LocalStackReport(host_label="h", reports=(rep,))
    assert isinstance(stack, LocalStackReportInterface)


# 15. The paths the spec's 100% domain floor requires and the lane never exercised


def test_recipe_is_none_for_a_host_the_entry_does_not_support():
    entry = LocalStackCatalogue().get("ollama")
    assert entry.recipe(None) is None


def test_get_returns_the_entry_and_names_what_it_knows_when_it_cannot():
    catalog = LocalStackCatalogue()
    assert catalog.get("ollama").key == "ollama"
    with pytest.raises(UnknownDependency, match="unknown dependency or group 'nope'"):
        catalog.get("nope")


def test_a_stack_report_is_changed_when_any_of_its_reports_changed():
    unchanged = DependencyReport(key="a", state=DependencyState.READY, detail="")
    changed = DependencyReport(key="b", state=DependencyState.READY, detail="", changed=True)
    assert not LocalStackReport(host_label="h", reports=(unchanged,)).changed
    assert LocalStackReport(host_label="h", reports=(unchanged, changed)).changed


def test_resolve_expands_a_group_and_honours_extra():
    catalog = LocalStackCatalogue()
    groups = catalog.groups()
    assert groups, "the catalogue defines at least one group"
    by_group = catalog.resolve(HostOs.ARCH, only=(groups[0],))
    assert by_group, "resolving a group name yields its members"
    with_extra = catalog.resolve(HostOs.ARCH, extra=("postgres",))
    assert any(spec.key == "postgres" for spec in with_extra)


def test_expanding_a_group_skips_entries_in_other_groups():
    # The shipped catalogue has one group holding every entry, so the "this entry is not in
    # the group" branch can never be taken against it. A two-group catalogue is the only way
    # to exercise it -- and constructing one is possible precisely because the guard that
    # rejected every custom catalogue has been removed.
    from vibey.domain.local_stack import DependencySpec, InstallerKind

    def spec(key: str, group: str) -> DependencySpec:
        return DependencySpec(
            key=key,
            title=key,
            group=group,
            default=True,
            installer=InstallerKind.PACKAGE,
            arch=None,
            macos=None,
        )

    catalog = LocalStackCatalogue(entries=(spec("a", "one"), spec("b", "two")))
    assert {s.key for s in catalog.resolve(HostOs.ARCH, only=("one",))} == {"a"}
