# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One envelope, whichever forge was read (#1572, part of #136).

A GitHub capture and a Forgejo capture of the same logical repository must write records,
a manifest and manifest entries with exactly the same keys and the same schema values; the
only envelope value that names the forge is `forge`. The GitHub side runs the real command
line against the scripted `fake_gh`; the Forgejo side runs the real adapter over a scripted
transport. Nothing leaves the machine.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from test_forge_snapshot import REPO, World, lines, snapshot

from vibey_gh import forge_selector
from vibey_gh.cli import _adapter_reader, main
from vibey_gh.forge_adapter_reader import ForgeAdapterReader
from vibey_gh.forge_forgejo import ForgejoForge
from vibey_gh.forge_snapshot import (
    CLASS_ENTRY_FIELDS,
    CLASSES,
    ENVELOPE_FIELDS,
    MANIFEST_FIELDS,
    MANIFEST_NAME,
    MANIFEST_SCHEMA,
    RECORD_SCHEMA,
    ForgeSnapshot,
    JsonlSnapshotStore,
)
from vibey_gh.forgejo_transport import ForgejoTransport

FORGEJO_LISTS = ("issue", "change-request", "release", "label")


class ScriptedForgejo:
    """A Forgejo as the adapter reaches it: a table of path to JSON list, query ignored."""

    executable = "http (forgejo)"

    def __init__(self, listing: dict[str, list[dict[str, Any]]]) -> None:
        self.listing = listing
        self.calls: list[str] = []

    def survey(self, args: Sequence[str], *, cwd: Any = None, stdin: Any = None):
        del cwd, stdin
        path = args[0].split("?")[0]
        self.calls.append(path)
        return self.listing.get(path, []), ""


def forgejo_world() -> dict[str, list[dict[str, Any]]]:
    base = f"repos/{REPO}"
    return {
        f"{base}/issues": [
            {"id": 11, "number": 1, "title": "Broken", "updated_at": "2026-09-01T09:00:00Z"}
        ],
        f"{base}/pulls": [
            {"id": 21, "number": 2, "title": "Fix", "updated_at": "2026-09-02T09:00:00Z"}
        ],
        f"{base}/releases": [{"id": 31, "tag_name": "v1", "created_at": "2026-09-03T09:00:00Z"}],
        f"{base}/labels": [{"id": 41, "name": "bug"}],
    }


def forgejo_capture(out: Path) -> dict[str, Any]:
    adapter = ForgejoForge(root=out, repository=REPO, transport=ScriptedForgejo(forgejo_world()))
    reader = ForgeAdapterReader(forge="forgejo", repository=REPO, adapter=adapter)
    store = JsonlSnapshotStore(out, forge=reader.forge, repository=reader.repository)
    return ForgeSnapshot(reader, store).capture()


@pytest.fixture
def both(fake_gh, tmp_path):
    """The GitHub capture and the Forgejo capture, side by side: `(github, forgejo)` roots."""
    fake_gh.script(World.seeded().answers())
    github = tmp_path / "github"
    snapshot(github).capture()
    forgejo = tmp_path / "forgejo"
    forgejo_capture(forgejo)
    return github, forgejo


def records_of(root: Path) -> list[dict[str, Any]]:
    return [record for path in sorted(root.glob("*.jsonl")) for record in lines(path)]


def test_every_record_of_either_forge_has_exactly_the_envelope_fields(both):
    for root in both:
        found = records_of(root)
        assert found, f"{root.name} captured nothing"
        for record in found:
            assert set(record) == set(ENVELOPE_FIELDS)
            assert record["schema"] == RECORD_SCHEMA


def test_the_manifest_and_its_class_entries_have_one_shape_on_either_forge(both):
    for root in both:
        manifest = json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))
        assert set(manifest) == set(MANIFEST_FIELDS)
        assert manifest["schema"] == MANIFEST_SCHEMA and manifest["record_schema"] == RECORD_SCHEMA
        assert set(manifest["classes"]) == {spec.name for spec in CLASSES}
        for entry in manifest["classes"].values():
            assert set(entry) == set(CLASS_ENTRY_FIELDS)


def test_only_the_forge_name_distinguishes_the_two_envelopes(both):
    github, forgejo = both
    assert {r["forge"] for r in records_of(github)} == {"github"}
    assert {r["forge"] for r in records_of(forgejo)} == {"forgejo"}
    gh_manifest, fj_manifest = (
        json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8")) for root in both
    )
    assert (gh_manifest["forge"], fj_manifest["forge"]) == ("github", "forgejo")
    # Every class shares its name for the artifact on both forges.
    for name in FORGEJO_LISTS:
        assert (
            gh_manifest["classes"][name]["native_class"]
            == fj_manifest["classes"][name]["native_class"]
        )


def test_a_class_the_forgejo_adapter_cannot_list_is_not_looked_at_never_empty(both):
    _, forgejo = both
    manifest = json.loads((forgejo / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["complete"] is False
    for name in ("comment", "review-comment", "milestone", "tag"):
        entry = manifest["classes"][name]
        assert entry["status"] == "could-not-look"
        assert "does not support" in entry["problem"]
        assert not (forgejo / f"{name}.jsonl").exists()
    for name in FORGEJO_LISTS:
        assert manifest["classes"][name]["status"] == "captured"
    # Reviews are walked through the change requests; the Forgejo adapter returns none yet, so
    # the class is captured and empty, which the reference document says.
    assert manifest["classes"]["review"]["status"] == "captured"
    assert manifest["classes"]["review"]["observed"] == 0


# ----------------------------------------------------------------------------- the command


@pytest.fixture
def scripted_selector(monkeypatch):
    """`ForgeSelector.select` answers with the scripted Forgejo, whatever `[platform]` says."""
    transport = ScriptedForgejo(forgejo_world())

    def select(self, cfg):
        return ForgejoForge(root=cfg.root, repository=cfg.platform.repository, transport=transport)

    monkeypatch.setattr(forge_selector.ForgeSelector, "select", select)
    return transport


def test_the_command_captures_a_forgejo_repository_through_its_adapter(
    scripted_selector, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "snap"
    code = main(["forge-snapshot", "--out", str(out), "--repo", REPO, "--forge", "forgejo"])
    printed = capsys.readouterr()
    assert code == 1  # the classes this adapter cannot list make the capture incomplete
    assert f"vibey-gh forge-snapshot: forgejo {REPO} into {out}" in printed.out
    assert "  issue: 1 observed, 1 appended" in printed.out
    assert "  tag: COULD NOT LOOK" in printed.err
    assert {r["forge"] for r in records_of(out)} == {"forgejo"}
    assert "repos/acme/widgets/issues" in scripted_selector.calls


def test_another_forge_needs_a_repository_it_cannot_ask_gh_for(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = main(["forge-snapshot", "--out", str(tmp_path / "snap"), "--forge", "forgejo"])
    assert code == 1
    assert "name it with --repo, or with [platform] repository" in capsys.readouterr().err


def test_the_platform_repository_stands_in_for_repo(scripted_selector, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text(
        f'[platform]\nkind = "forgejo"\nrepository = "{REPO}"\n'
    )
    out = tmp_path / "snap"
    assert main(["forge-snapshot", "--out", str(out), "--forge", "forgejo"]) == 1
    assert {r["forge"] for r in records_of(out)} == {"forgejo"}


def test_the_platform_table_is_used_only_when_it_names_the_forge_asked_for(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "github"\nhost = "ghe.example.com"\n'
    )
    other = _adapter_reader("forgejo", REPO, 100)
    assert other.adapter.transport == ForgejoTransport()
    (tmp_path / ".vibey-gh.toml").write_text(
        '[platform]\nkind = "forgejo"\nhost = "git.example.com"\n'
    )
    same = _adapter_reader("forgejo", REPO, 100)
    assert same.adapter.transport.host == "git.example.com"
    assert same.repository == REPO and same.forge == "forgejo"


def test_a_bare_command_still_reads_github(fake_gh, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_gh.script(World.seeded().answers())
    out = tmp_path / "snap"
    assert main(["forge-snapshot", "--out", str(out), "--repo", REPO]) == 0
    assert f"vibey-gh forge-snapshot: github {REPO} into {out}" in capsys.readouterr().out
