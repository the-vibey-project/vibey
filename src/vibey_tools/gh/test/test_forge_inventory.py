# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every class a forge's API exposes is captured or excluded, and the manifest says so (#1571).

The list under test is `vibey_gh/data/forge-api-classes.json`, read from the forges' API
descriptions. Nothing here asks a forge; the captures run over the scripted `fake_gh`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_forge_snapshot import REPO, Ticks, World

from vibey_gh import forge_inventory
from vibey_gh.cli import main
from vibey_gh.forge_inventory import INVENTORY_PATH, INVENTORY_SCHEMA, JsonForgeInventory
from vibey_gh.forge_snapshot import (
    CLASSES,
    EXCLUDED,
    ForgeSnapshot,
    GithubForgeReader,
    JsonlSnapshotStore,
    digest,
)
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.forge_snapshot_interface import ForgeInventoryInterface

HOMES = {spec.name for spec in CLASSES} | {name for name, _ in EXCLUDED}


class FakeInventory(ForgeInventoryInterface):
    def __init__(self, exposed: dict[str, tuple[str, ...]], verified: bool = True) -> None:
        self._exposed = exposed
        self._verified = verified

    @property
    def sha256(self) -> str:
        return "f" * 64

    def classes(self, forge: str) -> tuple[str, ...] | None:
        return self._exposed.get(forge)

    def verified(self, forge: str) -> bool:
        return self._verified


def capture(out: Path, inventory: ForgeInventoryInterface | None, **options) -> dict:
    reader = GithubForgeReader(GhTransport(), REPO)
    store = JsonlSnapshotStore(out, forge=reader.forge, repository=reader.repository)
    return ForgeSnapshot(reader, store, clock=Ticks(), inventory=inventory, **options).capture()


def write(path: Path, document: object) -> Path:
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def forge_entry(*pairs: tuple[str, str], verified: bool = True) -> dict:
    return {"verified": verified, "entries": [{"native": n, "class": c} for n, c in pairs]}


# ----------------------------------------------------------------------------- the shipped list


def test_the_inventory_satisfies_its_declared_seam():
    assert isinstance(JsonForgeInventory(), ForgeInventoryInterface)


@pytest.mark.parametrize("forge", ["github", "forgejo"])
def test_every_class_either_api_exposes_is_captured_or_excluded(forge):
    exposed = JsonForgeInventory().classes(forge)
    assert exposed
    assert sorted(set(exposed) - HOMES) == []


def test_an_exposed_class_with_no_home_is_found_by_the_same_rule():
    exposed = JsonForgeInventory().classes("github")
    dropped = [(n, r) for n, r in EXCLUDED if n != "webhook"]
    assert sorted(set(exposed) - ({s.name for s in CLASSES} | {n for n, _ in dropped})) == [
        "webhook"
    ]


def test_the_shipped_list_names_each_native_group_once_and_says_what_it_read():
    document = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert document["schema"] == INVENTORY_SCHEMA
    for name, forge in document["forges"].items():
        natives = [entry["native"] for entry in forge["entries"]]
        assert len(natives) == len(set(natives)), name
        assert forge["source"].startswith("https://") and forge["version"] and forge["read"]


def test_github_was_read_in_full_and_forgejo_was_not():
    inventory = JsonForgeInventory()
    assert inventory.verified("github") is True
    assert inventory.verified("forgejo") is False
    assert inventory.verified("gitlab") is False
    assert inventory.classes("gitlab") is None


def test_the_digest_is_over_the_document_not_its_whitespace(tmp_path):
    document = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    spaced = write(tmp_path / "spaced.json", document)
    spaced.write_text(json.dumps(document, indent=4), encoding="utf-8")
    assert JsonForgeInventory(spaced).sha256 == JsonForgeInventory().sha256 == digest(document)


# ----------------------------------------------------------------------------- the manifest


def test_the_manifest_carries_the_inventory_it_was_held_to(fake_gh, tmp_path):
    fake_gh.script(World.seeded().answers())
    manifest = capture(tmp_path / "snap", JsonForgeInventory())
    assert manifest["inventory"] == {
        "sha256": JsonForgeInventory().sha256,
        "verified": True,
        "unaccounted": [],
    }
    assert manifest["complete"] is True
    stored = json.loads((tmp_path / "snap" / "manifest.json").read_text(encoding="utf-8"))
    assert stored["inventory"] == manifest["inventory"]


def test_a_capture_without_an_inventory_says_it_was_held_to_none(fake_gh, tmp_path):
    fake_gh.script(World.seeded().answers())
    manifest = capture(tmp_path / "snap", None)
    assert manifest["inventory"] is None and manifest["complete"] is True


def test_an_exposed_class_with_no_home_is_reported_and_the_capture_is_not_complete(
    fake_gh, tmp_path
):
    fake_gh.script(World.seeded().answers())
    exposed = {"github": ("issue", "zebra", "aardvark")}
    manifest = capture(tmp_path / "snap", FakeInventory(exposed))
    assert manifest["inventory"]["unaccounted"] == ["aardvark", "zebra"]
    assert manifest["complete"] is False


def test_the_account_uses_the_exclusions_the_capture_was_given(fake_gh, tmp_path):
    fake_gh.script(World.seeded().answers())
    exposed = {"github": ("issue", "webhook")}
    held = capture(tmp_path / "a", FakeInventory(exposed))
    assert held["inventory"]["unaccounted"] == []
    narrowed = capture(tmp_path / "b", FakeInventory(exposed), excluded=[("secret", "Kept.")])
    assert narrowed["inventory"]["unaccounted"] == ["webhook"]


def test_a_forge_nobody_listed_is_unknown_not_covered(fake_gh, tmp_path):
    fake_gh.script(World.seeded().answers())
    manifest = capture(tmp_path / "snap", FakeInventory({}, verified=False))
    assert manifest["inventory"] == {"sha256": "f" * 64, "verified": False, "unaccounted": None}
    assert manifest["complete"] is False


# ----------------------------------------------------------------------------- the command


def test_the_command_holds_a_github_capture_to_the_inventory(
    fake_gh, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    fake_gh.script(World.seeded().answers())
    out = tmp_path / "snap"
    assert main(["forge-snapshot", "--out", str(out), "--repo", REPO]) == 0
    printed = capsys.readouterr()
    assert "neither captured nor excluded" not in printed.err
    assert "inventory was not read in full" not in printed.err
    assert (
        json.loads((out / "manifest.json").read_text(encoding="utf-8"))["inventory"]["unaccounted"]
        == []
    )


def test_the_command_names_the_classes_with_no_home(fake_gh, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_gh.script(World.seeded().answers())
    fake = FakeInventory({"github": ("zebra", "aardvark")}, verified=False)
    monkeypatch.setattr(forge_inventory, "JsonForgeInventory", lambda: fake)
    out = tmp_path / "snap"
    assert main(["forge-snapshot", "--out", str(out), "--repo", REPO]) == 1
    err = capsys.readouterr().err
    assert "API class(es) neither captured nor excluded: aardvark, zebra" in err
    assert "the github inventory was not read in full" in err


def test_the_command_says_when_a_forge_has_no_inventory(fake_gh, tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    fake_gh.script(World.seeded().answers())
    monkeypatch.setattr(forge_inventory, "JsonForgeInventory", lambda: FakeInventory({}))
    assert main(["forge-snapshot", "--out", str(tmp_path / "snap"), "--repo", REPO]) == 1
    assert "no inventory of what the github API exposes, so no account" in capsys.readouterr().out


# ----------------------------------------------------------------------------- reading the file


def test_a_file_that_is_not_an_inventory_is_refused(tmp_path):
    with pytest.raises(ValueError, match="is not a vibey.forge-api-classes/1 inventory"):
        JsonForgeInventory(write(tmp_path / "a.json", {"schema": "other"}))
    with pytest.raises(ValueError, match="is not a vibey.forge-api-classes/1 inventory"):
        JsonForgeInventory(write(tmp_path / "b.json", ["not", "an", "object"]))


def test_an_inventory_of_no_forge_is_refused(tmp_path):
    with pytest.raises(ValueError, match="inventories no forge"):
        JsonForgeInventory(write(tmp_path / "a.json", {"schema": INVENTORY_SCHEMA, "forges": {}}))
    with pytest.raises(ValueError, match="inventories no forge"):
        JsonForgeInventory(write(tmp_path / "b.json", {"schema": INVENTORY_SCHEMA}))


@pytest.mark.parametrize(
    "forge, message",
    [
        ("not an object", "lists no entries"),
        ({"entries": []}, "lists no entries"),
        ({"entries": ["issues"]}, "without a native and a class"),
        ({"entries": [{"native": "", "class": "issue"}]}, "without a native and a class"),
        ({"entries": [{"native": "issues", "class": ""}]}, "without a native and a class"),
        ({"entries": [{"native": "issues", "class": 7}]}, "without a native and a class"),
        (
            forge_entry(("issues", "issue"), ("issues", "comment")),
            "names a native group twice",
        ),
    ],
)
def test_a_damaged_forge_entry_is_refused_by_name(tmp_path, forge, message):
    document = {"schema": INVENTORY_SCHEMA, "forges": {"github": forge}}
    with pytest.raises(ValueError, match=f"github.*{message}"):
        JsonForgeInventory(write(tmp_path / "a.json", document))


def test_verified_is_true_only_when_the_file_says_true(tmp_path):
    document = {
        "schema": INVENTORY_SCHEMA,
        "forges": {
            "a": forge_entry(("issues", "issue")),
            "b": {**forge_entry(("issues", "issue")), "verified": "yes"},
            "c": {"entries": [{"native": "issues", "class": "issue"}]},
        },
    }
    inventory = JsonForgeInventory(write(tmp_path / "a.json", document))
    assert [inventory.verified(name) for name in "abc"] == [True, False, False]
