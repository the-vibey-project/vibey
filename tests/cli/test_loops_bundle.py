# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey loops marketplace | plugin | mcp | skills | snapshots` (SP-LOOPS Task 7).

Every command reads and writes only the person's own `vibey.toml` and the store beside it; none
reaches the network but `marketplace update` of a git source, which here is a fake. A project's
`vibey.toml` in the folder the command runs in changes nothing.
"""

from __future__ import annotations

import json
import os
import stat
import tomllib
from collections.abc import Iterator
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner
from vibey_runners.common.capabilities.lock import CapabilityLock
from vibey_runners.common.capabilities.resolver import CapabilityResolver
from vibey_skills import marketplace_root

import vibey.cli.loops_bundle
from vibey.bootstrap import loops_bundle_settings
from vibey.cli.interfaces.loops_bundle_interface import LoopsBundleCommandsInterface
from vibey.cli.loops_bundle import LOOPS_BUNDLE, LoopsBundleCommands
from vibey.cli.main import app
from vibey.domain.marketplace_source import MarketplaceSource
from vibey.infrastructure.interfaces.trusted_table_writer_interface import (
    TrustedTableWriterInterface,
)
from vibey.infrastructure.loops.interfaces.marketplace_store_interface import (
    MarketplaceStoreInterface,
)
from vibey.infrastructure.loops.marketplace_fetch_error import MarketplaceFetchError
from vibey.infrastructure.loops.marketplace_store import MarketplaceStore
from vibey.infrastructure.loops.records import FetchResult
from vibey.infrastructure.loops.snapshot_pruner import SnapshotPruner
from vibey.infrastructure.trusted_table_reader import TomlTrustedTableReader
from vibey.infrastructure.trusted_table_writer import TomlTrustedTableWriter

runner = CliRunner()
SHIPPED_SOURCE = "vibey-engine 9.9.9"
COMMIT = "c" * 40
RESEARCH_SKILLS = {
    "research-search-and-source-quality",
    "research-currency-audit-method",
    "research-editing-a-reference-skill",
}


def _manifest(name: str, plugins: dict[str, str]) -> str:
    return json.dumps(
        {
            "name": name,
            "plugins": [
                {"name": p, "source": f"./plugins/{p}", "description": d}
                for p, d in plugins.items()
            ],
        }
    )


def _skill(name: str, description: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\nBody.\n"


class FakeFetcher:
    """Plays a fetch into the staging folder: a marketplace named `acme` with one plugin whose
    skill description carries terminal control sequences, or an error."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[MarketplaceSource] = []

    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        self.calls.append(source)
        if self.error is not None:
            raise self.error
        files = {
            ".claude-plugin/marketplace.json": _manifest("acme", {"linting": "Lints \x1b[2J"}),
            "plugins/linting/skills/lint/SKILL.md": _skill("lint", "Lints code.\x1b]0;pwned\x07"),
        }
        into.mkdir(mode=0o700)
        for relative, text in files.items():
            (into / relative).parent.mkdir(parents=True, exist_ok=True)
            (into / relative).write_text(text, encoding="utf-8")
        (into / "plugins/linting/link").symlink_to("../../..")
        return FetchResult(COMMIT if source.kind == "git" else None, ("plugins/linting/link",))


class NoNetwork(FakeFetcher):
    def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
        raise AssertionError("no command but `marketplace update` may fetch")


def _shipped(tmp_path: Path) -> Path:
    """A small stand-in for the wheel's marketplace, with the research plugin."""
    root = tmp_path / "wheel"
    files = {
        ".claude-plugin/marketplace.json": _manifest(
            "vibey", {"currency-research": "Research methods.", "other": "Other."}
        ),
        "plugins/currency-research/skills/research-currency-audit-method/SKILL.md": _skill(
            "research-currency-audit-method", "Audit how current a source is."
        ),
        "plugins/other/README.md": "# other\n",
    }
    for relative, text in files.items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text, encoding="utf-8")
    return root


class Paths:
    def __init__(self, tmp_path: Path) -> None:
        self.config = tmp_path / "config" / "vibey.toml"
        self.store = tmp_path / "config" / "loops"

    def loops(self) -> dict[str, object]:
        document = tomllib.loads(self.config.read_text(encoding="utf-8"))
        table = document.get("loops", {})
        assert isinstance(table, dict)
        return table


def _commands(
    tmp_path: Path,
    fetcher: FakeFetcher | None = None,
    shipped: Path | None = None,
    echoed: list[str] | None = None,
) -> LoopsBundleCommands:
    paths = Paths(tmp_path)
    fake = fetcher or FakeFetcher()
    root = shipped or _shipped(tmp_path)

    def store(user_config: Path) -> MarketplaceStoreInterface:
        assert user_config == paths.config
        return MarketplaceStore(
            paths.store, fetchers={"git": fake, "local": fake}, shipped_root=lambda: root
        )

    def resolver(store: MarketplaceStoreInterface) -> CapabilityResolver:
        return CapabilityResolver(store.lock_path, store.snapshots, shipped_source=SHIPPED_SOURCE)

    echo = echoed.append if echoed is not None else typer.echo
    return LoopsBundleCommands(
        user_config=lambda: paths.config,
        settings=loops_bundle_settings(),
        reader=TomlTrustedTableReader(),
        writer=TomlTrustedTableWriter(),
        store=store,
        resolver=resolver,
        pruner=SnapshotPruner(clock=lambda: 10_000_000.0),
        shipped_source=lambda: SHIPPED_SOURCE,
        echo=echo,
    )


@pytest.fixture
def cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Paths]:
    """`vibey loops ...` through the real app, its commands pointed at `tmp_path`, run from a
    project folder of its own."""
    monkeypatch.setattr(vibey.cli.loops_bundle, "LOOPS_BUNDLE", _commands(tmp_path))
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.chdir(project)
    yield Paths(tmp_path)


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["loops", *args])
    return result.exit_code, result.output


def test_the_commands_satisfy_their_interface() -> None:
    assert isinstance(LOOPS_BUNDLE, LoopsBundleCommandsInterface)


# -- marketplace add / update / list -----------------------------------------------------------


def test_marketplace_add_writes_the_persons_config_and_no_lock(cli: Paths) -> None:
    code, out = _run("marketplace", "add", "acme", "https://example.test/acme.git", "--ref", "v1")
    assert code == 0, out
    assert "vibey loops marketplace update acme" in out
    assert cli.loops() == {
        "marketplaces": [{"name": "acme", "source": "https://example.test/acme.git", "ref": "v1"}]
    }
    assert stat.S_IMODE(cli.config.stat().st_mode) == 0o600
    assert not (cli.store / "lock.json").exists()


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["acme", "ext::sh -c x"], "transport helper"),
        (["acme", "file:///srv/x"], "is not a source vibey fetches"),
        (["--", "acme", "-x"], "must not start with '-'"),
        (["acme", "relative/folder"], "is not a source vibey fetches"),
        (["acme", "/srv/folder", "--ref", "v1"], "a local folder has no ref"),
        (["acme", "https://example.test/x.git", "--ref", "a..b"], "the ref"),
        (["bad name", "https://example.test/x.git"], "loops.marketplaces"),
        (["vibey", "https://example.test/x.git"], "reserved"),
    ],
)
def test_marketplace_add_refuses_what_it_would_not_fetch_with_exit_2(
    cli: Paths, args: list[str], reason: str
) -> None:
    code, out = _run("marketplace", "add", *args)
    assert code == 2, out
    assert reason in out
    assert not cli.config.exists()


def test_marketplace_add_twice_is_refused(cli: Paths) -> None:
    assert _run("marketplace", "add", "acme", "https://example.test/a.git")[0] == 0
    code, out = _run("marketplace", "add", "acme", "https://example.test/b.git")
    assert code == 2 and "declares the marketplace acme twice" in out


def test_marketplace_update_writes_the_lock_and_prints_the_digest(cli: Paths) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    code, out = _run("marketplace", "update", "acme")
    assert code == 0, out
    (entry,) = CapabilityLock().read(cli.store / "lock.json")
    assert (entry.marketplace, entry.source, entry.ref) == (
        "acme",
        "https://example.test/acme.git",
        None,
    )
    assert entry.digest in out
    assert COMMIT in out
    assert "left out plugins/linting/link" in out


def test_marketplace_update_with_no_name_relocks_the_shipped_one_and_fetches_each(
    cli: Paths,
) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    code, out = _run("marketplace", "update")
    assert code == 0, out
    names = [entry.marketplace for entry in CapabilityLock().read(cli.store / "lock.json")]
    assert sorted(names) == ["acme", "vibey"]
    assert SHIPPED_SOURCE in out


def test_marketplace_update_vibey_relocks_an_edited_shipped_marketplace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shipped = _shipped(tmp_path)
    echoed: list[str] = []
    commands = _commands(tmp_path, shipped=shipped, echoed=echoed)
    assert commands.marketplace_update("vibey") == 0
    before = CapabilityLock().read(Paths(tmp_path).store / "lock.json")
    (shipped / "plugins/currency-research/README.md").write_text("edited\n", encoding="utf-8")
    assert commands.skills_list(as_json=True) == 1  # the run refuses the changed tree ...
    assert "vibey loops marketplace update vibey" in "\n".join(echoed)
    assert commands.marketplace_update("vibey") == 0  # ... until the person accepts it
    after = CapabilityLock().read(Paths(tmp_path).store / "lock.json")
    assert before != after
    assert commands.skills_list(as_json=True) == 0


def test_a_failed_update_leaves_the_lock_and_exits_1(tmp_path: Path) -> None:
    echoed: list[str] = []
    good = _commands(tmp_path, echoed=echoed)
    good.marketplace_add("acme", "https://example.test/acme.git", None)
    assert good.marketplace_update("acme") == 0
    lock = (Paths(tmp_path).store / "lock.json").read_bytes()
    error = MarketplaceFetchError("git fetch failed (exit 128): remote: \x1b[31mgone")
    failing = _commands(tmp_path, fetcher=FakeFetcher(error=error), echoed=echoed)
    assert failing.marketplace_update("acme") == 1
    assert (Paths(tmp_path).store / "lock.json").read_bytes() == lock
    assert "\x1b" not in "\n".join(echoed)
    assert "acme not updated: git fetch failed" in echoed[-1]


def test_marketplace_update_of_an_undeclared_name_is_exit_2(cli: Paths) -> None:
    code, out = _run("marketplace", "update", "acme")
    assert code == 2 and "acme is not a marketplace in [loops]" in out


def test_marketplace_update_of_a_hand_edited_bad_source_is_exit_2(cli: Paths) -> None:
    cli.config.parent.mkdir(parents=True)
    cli.config.write_text(
        '[[loops.marketplaces]]\nname = "acme"\nsource = "file:///srv/x"\n', encoding="utf-8"
    )
    code, out = _run("marketplace", "update", "acme")
    assert code == 2 and "is not a source vibey fetches" in out


def test_marketplace_list_reports_lock_state_without_fetching(cli: Paths) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    _run("marketplace", "add", "beta", "https://example.test/beta.git")
    _run("marketplace", "update", "acme")
    document = cli.loops()
    document["marketplaces"][0]["ref"] = "v2"  # type: ignore[index]
    TomlTrustedTableWriter().write_table(cli.config, "loops", document)
    code, out = _run("marketplace", "list", "--json")
    assert code == 0, out
    listed = {row["name"]: row for row in json.loads(out)["marketplaces"]}
    assert listed["vibey"]["shipped"] is True
    assert listed["vibey"]["source"] == SHIPPED_SOURCE
    assert listed["vibey"]["state"] == "locks itself at first use"
    assert listed["acme"]["state"] == "lock pins another source or ref"
    assert listed["acme"]["ref"] == "v2"
    assert listed["acme"]["digest"].startswith("sha256:")
    assert listed["beta"] == {
        "name": "beta",
        "source": "https://example.test/beta.git",
        "ref": None,
        "shipped": False,
        "state": "not locked",
        "digest": None,
    }
    code, human = _run("marketplace", "list")
    assert code == 0 and "beta" in human and "not locked" in human


# -- plugin add / remove -------------------------------------------------------------------------


def test_plugin_add_keeps_the_research_default_and_adds(cli: Paths) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    code, out = _run("plugin", "add", "linting@acme")
    assert code == 0, out
    assert cli.loops()["plugins"] == ["currency-research@vibey", "linting@acme"]
    assert _run("plugin", "add", "linting@acme")[0] == 0  # already there: nothing changes
    assert cli.loops()["plugins"] == ["currency-research@vibey", "linting@acme"]


@pytest.mark.parametrize(
    ("spec", "reason"),
    [
        ("linting@nowhere", "names the marketplace nowhere, which [loops] does not declare"),
        ("no-marketplace", "must be written name@marketplace"),
        ("bad name@vibey", "must be written name@marketplace"),
    ],
)
def test_plugin_add_refuses_with_exit_2(cli: Paths, spec: str, reason: str) -> None:
    code, out = _run("plugin", "add", spec)
    assert code == 2, out
    assert reason in out
    assert not cli.config.exists()


def test_plugin_remove_drops_it_and_an_absent_one_is_exit_1(cli: Paths) -> None:
    code, out = _run("plugin", "remove", "currency-research")
    assert code == 0, out
    assert cli.loops()["plugins"] == []
    code, out = _run("plugin", "remove", "currency-research")
    assert code == 1 and "currency-research is not in [loops] plugins" in out


# -- mcp add / list ------------------------------------------------------------------------------


def test_mcp_add_local_stores_the_argv_exactly(cli: Paths) -> None:
    argv = ["fake-mcp", "--stdio", "a b", "$HOME", "x;y", "`z`"]
    code, out = _run("mcp", "add", "files", "--local", "--env-allow", "HOME", "--", *argv)
    assert code == 0, out
    assert cli.loops()["mcp_servers"] == [
        {"name": "files", "trust": "local", "command": argv, "env_allow": ["HOME"]}
    ]


def test_mcp_add_remote_stores_the_url(cli: Paths) -> None:
    code, out = _run("mcp", "add", "tickets", "--remote", "https://mcp.example.test/v1")
    assert code == 0, out
    assert cli.loops()["mcp_servers"] == [
        {"name": "tickets", "trust": "remote", "url": "https://mcp.example.test/v1"}
    ]


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["t", "--remote", "http://mcp.example.test/v1"], "must be an https:// URL with a host"),
        (["t", "--remote", "https://user:pw@mcp.example.test/"], "must not carry credentials"),
        (["t", "--local"], "--local needs the command after --"),
        (["t", "--remote", "https://x.test/", "--", "cmd"], "--remote takes no command"),
        (["t", "--local", "--remote", "https://x.test/", "--", "cmd"], "exactly one of"),
        (["t", "--", "cmd"], "exactly one of"),
        (["bad name", "--local", "--", "cmd"], "loops.mcp_servers[0].name"),
        (["t", "--local", "--env-allow", "1BAD", "--", "cmd"], "environment variable names"),
    ],
)
def test_mcp_add_refuses_with_exit_2(cli: Paths, args: list[str], reason: str) -> None:
    code, out = _run("mcp", "add", *args)
    assert code == 2, out
    assert reason in out
    assert not cli.config.exists()


def test_mcp_list_prints_the_persons_servers(cli: Paths) -> None:
    _run("mcp", "add", "files", "--local", "--", "fake-mcp", "--stdio")
    _run("mcp", "add", "tickets", "--remote", "https://mcp.example.test/v1")
    code, out = _run("mcp", "list", "--json")
    assert code == 0, out
    assert json.loads(out) == {
        "mcp_servers": [
            {
                "name": "files",
                "trust": "local",
                "command": ["fake-mcp", "--stdio"],
                "url": None,
                "env_allow": [],
            },
            {
                "name": "tickets",
                "trust": "remote",
                "command": None,
                "url": "https://mcp.example.test/v1",
                "env_allow": [],
            },
        ]
    }
    code, human = _run("mcp", "list")
    assert (
        "files" in human and "fake-mcp --stdio" in human and "https://mcp.example.test/v1" in human
    )


def test_mcp_list_with_none_says_so(cli: Paths) -> None:
    code, out = _run("mcp", "list")
    assert code == 0 and "no MCP servers" in out


# -- skills list ---------------------------------------------------------------------------------


def test_skills_list_lists_the_research_skills_from_the_wheel_with_no_network(
    tmp_path: Path,
) -> None:
    """A fresh install: no `vibey.toml`, no lock, the real marketplace the wheel ships, and a
    fetcher that fails the test if anything asks it (Phase 2 acceptance)."""
    echoed: list[str] = []
    commands = _commands(tmp_path, fetcher=NoNetwork(), shipped=marketplace_root(), echoed=echoed)
    assert commands.skills_list(as_json=True) == 0
    document = json.loads(echoed[-1])
    skills = {row["name"]: row for row in document["skills"]}
    assert set(skills) >= RESEARCH_SKILLS
    assert {skills[name]["plugin"] for name in RESEARCH_SKILLS} == {"currency-research"}
    assert document["digest"].startswith("sha256:")
    snapshots = Paths(tmp_path).store / "snapshots"
    assert not snapshots.exists() or list(snapshots.iterdir()) == []  # the listing's copy is gone


def test_skills_list_escapes_marketplace_text_and_json_keeps_types(cli: Paths) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    _run("marketplace", "update", "acme")
    _run("plugin", "add", "linting@acme")
    code, out = _run("skills", "list")
    assert code == 0, out
    assert "\x1b" not in out and "\x07" not in out
    assert "lint" in out and "research-currency-audit-method" in out
    assert "a symlink, which a snapshot never copies" in out
    code, out = _run("skills", "list", "--json")
    document = json.loads(out)
    assert [row["name"] for row in document["skills"]] == ["research-currency-audit-method", "lint"]
    assert all(isinstance(row["reason"], str) for row in document["skipped"])
    assert document["skipped"][0]["path"].startswith("acme/")


def test_skills_list_of_an_unlocked_marketplace_names_the_command(cli: Paths) -> None:
    _run("marketplace", "add", "acme", "https://example.test/acme.git")
    _run("plugin", "add", "linting@acme")
    code, out = _run("skills", "list")
    assert code == 1
    assert "vibey loops marketplace update acme" in out


def test_skills_list_with_no_plugins_lists_nothing(cli: Paths) -> None:
    _run("plugin", "remove", "currency-research")
    code, out = _run("skills", "list", "--json")
    assert code == 0, out
    assert json.loads(out)["skills"] == []
    code, out = _run("skills", "list")
    assert "no skills" in out


# -- snapshots prune -----------------------------------------------------------------------------


def test_snapshots_prune_removes_old_runs_under_the_store_only(cli: Paths, tmp_path: Path) -> None:
    snapshots = cli.store / "snapshots"
    old, fresh = snapshots / "run-old", snapshots / "run-fresh"
    for folder, age in ((old, 9), (fresh, 1)):
        folder.mkdir(parents=True)
        stamp = 10_000_000.0 - age * 86_400
        os.utime(folder, (stamp, stamp))
    (snapshots / "run-link").symlink_to(tmp_path)
    code, out = _run("snapshots", "prune")
    assert code == 0, out
    assert not old.exists() and fresh.exists()
    assert "removed 1" in out and "run-link" in out and "never followed" in out
    code, out = _run("snapshots", "prune", "--older-than-days", "0")
    assert code == 2


def test_snapshots_prune_takes_an_age(cli: Paths) -> None:
    folder = cli.store / "snapshots" / "run-x"
    folder.mkdir(parents=True)
    stamp = 10_000_000.0 - 2 * 86_400
    os.utime(folder, (stamp, stamp))
    assert _run("snapshots", "prune", "--older-than-days", "3")[0] == 0 and folder.exists()
    assert _run("snapshots", "prune", "--older-than-days", "1")[0] == 0 and not folder.exists()


# -- trust: only the person's own file -------------------------------------------------------


def test_a_hostile_project_vibey_toml_changes_nothing(cli: Paths) -> None:
    """The folder a command runs in may be a cloned repository; its `[loops]` is never read by
    these commands, and never written."""
    hostile = Path.cwd() / "vibey.toml"
    text = (
        '[loops]\nplugins = ["evil@evil"]\ndisable = ["currency-research"]\n'
        '[[loops.marketplaces]]\nname = "evil"\nsource = "https://evil.test/x.git"\n'
        '[[loops.mcp_servers]]\nname = "evil"\ntrust = "local"\ncommand = ["sh", "-c", "x"]\n'
    )
    hostile.write_text(text, encoding="utf-8")
    assert json.loads(_run("mcp", "list", "--json")[1]) == {"mcp_servers": []}
    names = [
        row["name"] for row in json.loads(_run("marketplace", "list", "--json")[1])["marketplaces"]
    ]
    assert names == ["vibey"]
    assert _run("plugin", "add", "evil@evil")[0] == 2
    assert _run("mcp", "add", "files", "--local", "--", "fake")[0] == 0
    skills = json.loads(_run("skills", "list", "--json")[1])["skills"]
    assert [row["plugin"] for row in skills] == ["currency-research"]
    assert hostile.read_text(encoding="utf-8") == text
    assert "evil" not in cli.config.read_text(encoding="utf-8")


def test_the_default_commands_read_the_persons_own_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Wiring: the module's own commands find the person's file through `acp_user_config` (the
    one `UserConfigFolder.vibey_toml()`), never the current folder."""
    own = tmp_path / "own" / "vibey.toml"
    own.parent.mkdir()
    own.write_text(
        '[[loops.mcp_servers]]\nname = "mine"\ntrust = "remote"\nurl = "https://m.test/"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(vibey.cli.loops_bundle, "acp_user_config", lambda: own)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "vibey.toml").write_text("[loops\nbroken", encoding="utf-8")
    code, out = _run("mcp", "list", "--json")
    assert code == 0, out
    assert [row["name"] for row in json.loads(out)["mcp_servers"]] == ["mine"]


# -- the person's file cannot be read or rewritten -------------------------------------------


def test_an_unreadable_config_is_exit_78(cli: Paths) -> None:
    cli.config.parent.mkdir(parents=True)
    cli.config.write_text("[loops\n", encoding="utf-8")
    for args in (
        ["mcp", "list"],
        ["marketplace", "list"],
        ["skills", "list"],
        ["plugin", "remove", "x"],
    ):
        code, out = _run(*args)
        assert code == 78, (args, out)
        assert "is not valid TOML" in out


def test_a_config_it_cannot_rewrite_prints_the_table_to_paste_and_exits_78(cli: Paths) -> None:
    cli.config.parent.mkdir(parents=True)
    original = '[loops]\n# my research plugins\nplugins = ["currency-research@vibey"]\n'
    cli.config.write_text(original, encoding="utf-8")
    code, out = _run("mcp", "add", "tickets", "--remote", "https://mcp.example.test/v1")
    assert code == 78, out
    assert "comments inside [loops]" in out
    assert '[[loops.mcp_servers]]\nname = "tickets"' in out
    assert cli.config.read_text(encoding="utf-8") == original


def test_a_bundle_the_person_wrote_wrong_is_exit_78_for_the_listings(cli: Paths) -> None:
    cli.config.parent.mkdir(parents=True)
    cli.config.write_text("[loops]\nunknown = 1\n", encoding="utf-8")
    code, out = _run("mcp", "list")
    assert code == 78 and "loops.unknown" in out


def test_a_damaged_lock_is_exit_1(cli: Paths) -> None:
    (cli.store).mkdir(parents=True)
    (cli.store / "lock.json").write_text('{"version": 1', encoding="utf-8")
    for args in (["marketplace", "list"], ["skills", "list"], ["marketplace", "update", "vibey"]):
        code, out = _run(*args)
        assert code == 1, (args, out)
        assert "lock.json" in out


def test_the_writer_seam_is_the_trusted_table_writer() -> None:
    assert isinstance(TomlTrustedTableWriter(), TrustedTableWriterInterface)


def test_the_loops_group_still_lists_the_loops(cli: Paths) -> None:
    code, out = _run("--json")
    assert code == 0 and json.loads(out)["default_loop"] == "sovereignloop"
    assert isinstance(app, typer.Typer)


def test_marketplace_list_says_locked_and_relocking_for_each_kind(tmp_path: Path) -> None:
    echoed: list[str] = []
    commands = _commands(tmp_path, echoed=echoed)
    commands.marketplace_add("acme", "https://example.test/acme.git", None)
    assert commands.marketplace_update(None) == 0
    assert commands.marketplace_list(as_json=True) == 0
    states = {row["name"]: row["state"] for row in json.loads(echoed[-1])["marketplaces"]}
    assert states == {"vibey": "locked", "acme": "locked"}
    upgraded = LoopsBundleCommands(
        user_config=lambda: Paths(tmp_path).config,
        store=lambda user: MarketplaceStore(
            Paths(tmp_path).store, fetchers={}, shipped_root=lambda: tmp_path / "wheel"
        ),
        shipped_source=lambda: "vibey-engine 10.0.0",
        echo=echoed.append,
    )
    assert upgraded.marketplace_list(as_json=True) == 0
    rows = json.loads(echoed[-1])["marketplaces"]
    assert rows[0]["state"] == "locks itself again at next use (a new release)"


def test_a_change_to_a_bundle_the_person_wrote_wrong_is_exit_78(cli: Paths) -> None:
    cli.config.parent.mkdir(parents=True)
    cli.config.write_text("[loops]\nunknown = 1\n", encoding="utf-8")
    code, out = _run("plugin", "remove", "currency-research")
    assert code == 78 and "loops.unknown: is not a known key" in out


def test_snapshots_prune_refuses_an_age_under_a_day(tmp_path: Path) -> None:
    echoed: list[str] = []
    assert _commands(tmp_path, echoed=echoed).snapshots_prune(0) == 2
    assert "at least 1" in echoed[-1]


def test_a_path_outside_the_snapshots_is_shown_as_it_is(tmp_path: Path) -> None:
    outside = tmp_path / "elsewhere" / "x"
    assert LoopsBundleCommands._inside_run(outside, tmp_path / "snapshots") == str(outside)


def test_discarding_touches_only_run_folders_inside_the_snapshots(tmp_path: Path) -> None:
    from vibey_runners.common.capabilities.skill_catalog import SkillCatalog
    from vibey_runners.common.capabilities.snapshot import CapabilitySnapshot

    snapshots = tmp_path / "snapshots"
    run = snapshots / "run-1" / "vibey" / "plugins" / "p"
    run.mkdir(parents=True)
    outside = tmp_path / "outside" / "p"
    outside.mkdir(parents=True)
    empty = SkillCatalog((), ())
    snapshot = CapabilitySnapshot((outside, snapshots, run), empty, (), "sha256:" + "0" * 64)
    LoopsBundleCommands._discard(snapshot, snapshots)
    assert outside.is_dir() and snapshots.is_dir()
    assert not (snapshots / "run-1").exists()


# -- review 1 -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (["acme", "git://example.test/acme.git"], "is not a source vibey fetches"),
        (["acme", "ssh://-oProxyCommand=x@host/p"], "plain user"),
        (["acme", "ssh://u%2d@host/p"], "plain user"),
    ],
)
def test_marketplace_add_refuses_plaintext_git_and_an_option_shaped_user(
    cli: Paths, args: list[str], reason: str
) -> None:
    code, out = _run("marketplace", "add", *args)
    assert code == 2 and reason in out
    assert not cli.config.exists()


@pytest.mark.parametrize("name", ["VIBEY_HUB_TOKEN", "VIBEY_BRAVE_API_KEY", "GITHUB_TOKEN"])
def test_mcp_add_refuses_to_hand_a_server_a_secret(cli: Paths, name: str) -> None:
    code, out = _run("mcp", "add", "files", "--local", "--env-allow", name, "--", "srv")
    assert code == 2 and "carries a secret" in out
    assert not cli.config.exists()


def test_success_lines_show_the_persons_text_as_one_safe_line(tmp_path: Path) -> None:
    echoed: list[str] = []
    commands = _commands(tmp_path, echoed=echoed)
    source = "https://example.test/acme‮.git"
    assert commands.marketplace_add("acme", source, None) == 0
    assert commands.marketplace_update("acme") == 0
    assert all("‮" not in line for line in echoed)
    assert any(line.startswith("acme locked sha256:") for line in echoed)


def test_a_bare_update_reports_each_marketplace_and_goes_on_after_a_failure(
    tmp_path: Path,
) -> None:
    class FailingFor(FakeFetcher):
        def fetch(self, source: MarketplaceSource, ref: str | None, into: Path) -> FetchResult:
            if "first" in source.text:
                raise PermissionError(13, "Permission denied", str(into))
            return super().fetch(source, ref, into)

    echoed: list[str] = []
    commands = _commands(tmp_path, fetcher=FailingFor(), echoed=echoed)
    commands.marketplace_add("first", "https://example.test/first.git", None)
    commands.marketplace_add("second", "https://example.test/second.git", None)
    assert commands.marketplace_update(None) == 1
    text = "\n".join(echoed)
    assert "first not updated: first cannot be updated: [Errno 13] Permission denied" in text
    assert "second locked sha256:" in text and "vibey locked sha256:" in text
    names = [
        entry.marketplace for entry in CapabilityLock().read(Paths(tmp_path).store / "lock.json")
    ]
    assert sorted(names) == ["second", "vibey"]


def test_a_change_holds_the_lock_beside_vibey_toml_while_it_writes(tmp_path: Path) -> None:
    import fcntl

    paths = Paths(tmp_path)
    sidecar = paths.config.with_name(".vibey.toml.flock")
    held: list[bool] = []

    class Checking(TomlTrustedTableWriter):
        def write_table(self, path: Path, table: str, values: object) -> None:  # type: ignore[override]
            descriptor = os.open(sidecar, os.O_RDWR)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                held.append(False)
            except BlockingIOError:
                held.append(True)
            finally:
                os.close(descriptor)
            super().write_table(path, table, values)  # type: ignore[arg-type]

    commands = _commands(tmp_path)
    commands._writer = Checking()  # noqa: SLF001 - the one seam this test swaps
    assert commands.plugin_remove("currency-research") == 0
    assert held == [True]


def test_a_change_while_another_holds_the_lock_waits_then_exits_1(tmp_path: Path) -> None:
    from vibey_runners.common.capabilities.sidecar_lock import SidecarLock

    paths = Paths(tmp_path)
    now = [0.0]

    def sleep(seconds: float) -> None:
        now[0] += seconds

    echoed: list[str] = []
    commands = _commands(tmp_path, echoed=echoed)
    commands._config_lock = SidecarLock(clock=lambda: now[0], sleep=sleep, timeout_seconds=1.0)  # noqa: SLF001
    with SidecarLock().held(paths.config):
        assert commands.plugin_remove("currency-research") == 1
    assert "being changed by another vibey" in echoed[-1]
    assert not paths.config.exists()


def test_a_lock_beside_vibey_toml_that_cannot_be_made_is_exit_78(tmp_path: Path) -> None:
    paths = Paths(tmp_path)
    paths.config.parent.mkdir(parents=True)
    paths.config.with_name(".vibey.toml.flock").symlink_to(tmp_path / "elsewhere")
    echoed: list[str] = []
    assert _commands(tmp_path, echoed=echoed).plugin_remove("currency-research") == 78
    assert "cannot be locked for a change" in echoed[-1]
