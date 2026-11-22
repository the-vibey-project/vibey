# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`LlmToolingProbe`: what `vibey connect`, `vibey doctor` and `vibey acp` report per surface.

It reads client configs that may sit in a repository someone else wrote (Claude Code's
`.mcp.json`, VS Code's `.vscode/mcp.json`, read in the folder an editor opened) as well as the
user's own, so it reads them the way an untrusted file deserves: never through a symbolic link,
never anything but a regular file (a FIFO would hang a plain read), never more than a bound,
never outside the client's scope root. It only ever reads. Module-level test functions rather
than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

import pytest

from vibey.domain.llm_tooling import ToolingFinding
from vibey.infrastructure.mcp.interfaces.llm_tooling_probe_interface import (
    LlmToolingProbeInterface,
)
from vibey.infrastructure.mcp.llm_tooling_probe import LlmToolingProbe

PINNED = "/pinned/bin/vibey"
ZED_ENTRY = {"type": "custom", "command": PINNED, "args": ["acp"], "env": {}}


def probe(
    tmp_path: Path, *, launcher: str | None = PINNED, shipped: Path | None = None
) -> tuple[LlmToolingProbe, Path, Path]:
    home, project = tmp_path / "home", tmp_path / "project"
    home.mkdir(exist_ok=True)
    project.mkdir(exist_ok=True)
    return (
        LlmToolingProbe(
            launcher=lambda: launcher,
            home_dir=lambda: home,
            project_dir=lambda: project,
            platform="linux",
            python_executable="/usr/bin/python3",
            shipped_skill=lambda: shipped,
            environ={},
        ),
        home,
        project,
    )


def by_name(found: tuple[ToolingFinding, ...]) -> dict[str, ToolingFinding]:
    return {f.name: f for f in found}


def write_zed(home: Path, doc: object | str) -> Path:
    settings = home / ".config" / "zed" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(doc if isinstance(doc, str) else json.dumps(doc), encoding="utf-8")
    return settings


def test_the_probe_honours_its_interface(tmp_path: Path) -> None:
    assert isinstance(probe(tmp_path)[0], LlmToolingProbeInterface)


def test_only_clients_installed_here_are_reported_by_default(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    assert tooling.findings() == ()
    (home / ".config" / "zed").mkdir(parents=True)
    (home / ".codex").mkdir()
    found = tooling.findings()
    assert {f.client_id for f in found} == {"codex", "zed"}
    assert len(found) == 8


def test_named_clients_are_reported_whether_installed_or_not(tmp_path: Path) -> None:
    tooling, _, _ = probe(tmp_path)
    found = by_name(tooling.findings(["cursor"]))
    assert found["cursor:mcp-server"].state == "missing"
    assert found["cursor:mcp-server"].detail == (
        "no ~/.cursor/mcp.json; run `vibey connect --client cursor`"
    )


def test_the_zed_entry_with_the_pinned_launcher_is_present(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    write_zed(home, {"agent_servers": {"vibey": ZED_ENTRY}})
    found = by_name(tooling.findings())
    assert found["zed:acp-agent"].state == "present"
    assert found["zed:acp-agent"].detail == "in ~/.config/zed/settings.json"


def test_an_entry_running_some_other_vibey_is_missing(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    write_zed(home, {"agent_servers": {"vibey": {**ZED_ENTRY, "command": "vibey"}}})
    finding = by_name(tooling.findings())["zed:acp-agent"]
    assert finding.state == "missing"
    assert "vibey connect --client zed" in finding.detail


def test_without_a_launcher_the_python_fallback_is_what_counts(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path, launcher=None)
    fallback = {
        "type": "custom",
        "command": "/usr/bin/python3",
        "args": ["-c", "from vibey.cli.main import run; run(['acp'])"],
        "env": {},
    }
    write_zed(home, {"agent_servers": {"vibey": fallback}})
    assert by_name(tooling.findings())["zed:acp-agent"].state == "present"


def test_commented_zed_settings_are_reported_with_the_snippet(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    settings = write_zed(home, '// Zed settings\n{"theme": "x"}\n')
    finding = by_name(tooling.findings())["zed:acp-agent"]
    assert finding.state == "missing"
    assert finding.detail.startswith("~/.config/zed/settings.json: invalid JSON")
    assert finding.detail.endswith(
        f'"agent_servers": {{"vibey": {{"type": "custom", "command": "{PINNED}", '
        '"args": ["acp"], "env": {}}}'
    )
    assert settings.read_text() == '// Zed settings\n{"theme": "x"}\n'


def test_a_symlinked_config_is_never_read_through(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    real = tmp_path / "real.json"
    real.write_text(json.dumps({"agent_servers": {"vibey": ZED_ENTRY}}))
    (home / ".config" / "zed").mkdir(parents=True)
    (home / ".config" / "zed" / "settings.json").symlink_to(real)
    finding = by_name(tooling.findings())["zed:acp-agent"]
    assert finding.state == "missing"
    assert "symbolic link" in finding.detail


def test_a_fifo_in_place_of_a_config_is_refused_without_hanging(tmp_path: Path) -> None:
    tooling, home, project = probe(tmp_path)
    os.mkfifo(project / ".mcp.json")
    result: list[tuple[ToolingFinding, ...]] = []
    reader = threading.Thread(target=lambda: result.append(tooling.findings(["claude_code"])))
    reader.daemon = True
    reader.start()
    reader.join(timeout=5)
    assert result, "reading the project's .mcp.json hung on a FIFO"
    finding = by_name(result[0])["claude_code:mcp-server"]
    assert finding.state == "missing" and "not a regular file" in finding.detail


def test_an_oversized_config_is_refused_unread(tmp_path: Path) -> None:
    tooling, home, project = probe(tmp_path)
    (project / ".mcp.json").write_text(" " * (LlmToolingProbe.MAX_BYTES + 1))
    finding = by_name(tooling.findings(["claude_code"]))["claude_code:mcp-server"]
    assert finding.state == "missing" and "larger than" in finding.detail


def test_a_config_that_is_not_utf8_is_refused(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    (home / ".cursor").mkdir()
    (home / ".cursor" / "mcp.json").write_bytes(b"\xff\xfe{")
    finding = by_name(tooling.findings())["cursor:mcp-server"]
    assert finding.state == "missing" and "UTF-8" in finding.detail


def test_a_config_that_cannot_be_opened_says_why(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    (home / ".cursor").mkdir()
    blocked = home / ".cursor" / "mcp.json"
    blocked.write_text("{}")
    blocked.chmod(0)
    try:
        finding = by_name(tooling.findings())["cursor:mcp-server"]
    finally:
        blocked.chmod(0o600)
    if os.geteuid() == 0:  # root reads it anyway
        pytest.skip("runs as root")
    assert finding.state == "missing" and "cannot be read" in finding.detail


def test_a_project_config_resolving_outside_the_project_is_not_read(tmp_path: Path) -> None:
    tooling, _, project = probe(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "mcp.json").write_text("{}")
    (project / ".vscode").symlink_to(outside)
    finding = by_name(tooling.findings(["vscode"]))["vscode:mcp-server"]
    assert finding.state == "missing"
    assert "is not inside the project folder" in finding.detail


def test_the_codex_toml_entry_is_read_too(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text(
        f'[mcp_servers.vibey]\ncommand = "{PINNED}"\nargs = ["mcp"]\n'
    )
    assert by_name(tooling.findings())["codex:mcp-server"].state == "present"
    (home / ".codex" / "config.toml").write_text("[broken")
    assert "invalid TOML" in by_name(tooling.findings())["codex:mcp-server"].detail


def installed_plugins(home: Path, doc: object | str) -> None:
    path = home / ".claude" / "plugins" / "installed_plugins.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc if isinstance(doc, str) else json.dumps(doc))


def test_the_claude_code_plugin_is_read_from_its_installed_record(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    installed_plugins(home, {"version": 2, "plugins": {"vibey@vibey": [{"scope": "user"}]}})
    found = by_name(tooling.findings())
    assert found["claude_code:plugin"].state == "present"
    assert found["claude_code:skill"].state == "present"
    assert found["claude_code:mcp-server"].state == "present"


@pytest.mark.parametrize(
    "record",
    [
        {"version": 2, "plugins": {"vibey@someone-else": []}},
        {"version": 2, "plugins": []},
        [],
        "{not json",
    ],
)
def test_any_other_record_means_the_plugin_is_missing(tmp_path: Path, record: object) -> None:
    tooling, home, _ = probe(tmp_path)
    installed_plugins(home, record)
    assert by_name(tooling.findings())["claude_code:plugin"].state == "missing"


def test_a_symlinked_plugin_record_is_not_read(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    real = tmp_path / "plugins.json"
    real.write_text(json.dumps({"plugins": {"vibey@vibey": []}}))
    (home / ".claude" / "plugins").mkdir(parents=True)
    (home / ".claude" / "plugins" / "installed_plugins.json").symlink_to(real)
    assert by_name(tooling.findings())["claude_code:plugin"].state == "missing"


def test_a_skill_in_its_folder_is_found(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    for client in (".claude", ".codex"):
        skill = home / client / "skills" / "vibey-chat-driver"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("---\nname: vibey-chat-driver\n---\n")
    found = by_name(tooling.findings())
    assert found["claude_code:skill"].detail == "~/.claude/skills/vibey-chat-driver"
    assert found["codex:skill"].detail == "~/.codex/skills/vibey-chat-driver"


def test_codex_is_told_to_copy_the_skill_vibey_ships(tmp_path: Path) -> None:
    shipped = tmp_path / "site packages" / "vibey-chat-driver"
    tooling, home, _ = probe(tmp_path, shipped=shipped)
    (home / ".codex").mkdir()
    detail = by_name(tooling.findings())["codex:skill"].detail
    assert detail == (
        f"vibey-chat-driver: mkdir -p ~/.codex/skills && cp -R '{shipped}' ~/.codex/skills/"
    )


def test_without_a_shipped_skill_codex_is_pointed_at_the_repository(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path, shipped=None)
    (home / ".codex").mkdir()
    detail = by_name(tooling.findings())["codex:skill"].detail
    assert ".agents/skills/vibey-chat-driver" in detail and "~/.codex/skills" in detail


def test_the_shipped_skill_is_found_in_the_installed_package_or_the_source_tree() -> None:
    shipped = LlmToolingProbe.shipped_skill()
    assert shipped is not None
    assert (shipped / "SKILL.md").is_file()
    assert shipped.name == "vibey-chat-driver"


def test_the_probe_writes_nothing(tmp_path: Path) -> None:
    tooling, home, project = probe(tmp_path)
    write_zed(home, '// c\n{"a": 1,}')
    (home / ".codex").mkdir()
    (home / ".claude").mkdir()
    before = sorted((p, p.stat().st_mtime_ns) for p in tmp_path.rglob("*"))
    tooling.findings()
    tooling.findings(["claude_code", "vscode", "cursor", "gemini_cli", "claude_desktop"])
    assert sorted((p, p.stat().st_mtime_ns) for p in tmp_path.rglob("*")) == before


# ------------------------------------------------------------- fix round 1: never raises

DEEP = ["[" * 200_000, "// c\n" + "[" * 200_000]


@pytest.mark.parametrize("content", DEEP)
def test_a_project_config_nested_too_deeply_is_reported_never_raised(
    tmp_path: Path, content: str
) -> None:
    tooling, _, project = probe(tmp_path)
    (project / ".mcp.json").write_text(content)
    finding = by_name(tooling.findings(["claude_code"]))["claude_code:mcp-server"]
    assert finding.state == "missing" and "invalid JSON" in finding.detail


def test_a_codex_config_nested_too_deeply_is_reported_never_raised(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    (home / ".codex").mkdir()
    (home / ".codex" / "config.toml").write_text("x = " + "[" * 200_000)
    finding = by_name(tooling.findings())["codex:mcp-server"]
    assert finding.state == "missing" and "invalid TOML" in finding.detail


def test_a_plugin_record_nested_too_deeply_means_no_plugin(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    installed_plugins(home, "[" * 200_000)
    assert by_name(tooling.findings())["claude_code:plugin"].state == "missing"


def test_a_folder_that_cannot_be_looked_into_counts_as_absent(tmp_path: Path) -> None:
    if os.geteuid() == 0:
        pytest.skip("root can look into anything")
    tooling, home, _ = probe(tmp_path)
    (home / ".config" / "zed").mkdir(parents=True)
    (home / ".claude").mkdir()
    (home / ".config").chmod(0)
    try:
        found = by_name(tooling.findings())
        named = by_name(tooling.findings(["zed", "claude_code"]))
    finally:
        (home / ".config").chmod(0o700)
    assert "zed:acp-agent" not in found and "claude_code:skill" in found
    assert named["zed:acp-agent"].state == "missing"


def test_an_entry_with_the_persons_own_flags_and_env_is_present(tmp_path: Path) -> None:
    tooling, home, _ = probe(tmp_path)
    mine = {**ZED_ENTRY, "args": ["acp", "--no-bootstrap"], "env": {"A": "b"}}
    write_zed(home, {"agent_servers": {"vibey": mine}})
    assert by_name(tooling.findings())["zed:acp-agent"].state == "present"


def test_zed_on_linux_is_read_where_xdg_config_home_points(tmp_path: Path) -> None:
    home, project, xdg = tmp_path / "home", tmp_path / "project", tmp_path / "home" / ".xdg"
    project.mkdir()
    (xdg / "zed").mkdir(parents=True)
    (xdg / "zed" / "settings.json").write_text(json.dumps({"agent_servers": {"vibey": ZED_ENTRY}}))
    tooling = LlmToolingProbe(
        launcher=lambda: PINNED,
        home_dir=lambda: home,
        project_dir=lambda: project,
        platform="linux",
        shipped_skill=lambda: None,
        environ={"XDG_CONFIG_HOME": str(xdg)},
    )
    finding = by_name(tooling.findings())["zed:acp-agent"]
    assert finding.state == "present" and finding.detail == "in ~/.xdg/zed/settings.json"


def test_claude_codes_skill_in_the_projects_own_folder_counts(tmp_path: Path) -> None:
    tooling, _, project = probe(tmp_path)
    skill = project / ".claude" / "skills" / "vibey-chat-driver"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("x")
    finding = by_name(tooling.findings(["claude_code"]))["claude_code:skill"]
    assert finding.state == "present" and finding.detail.endswith(
        "project/.claude/skills/vibey-chat-driver"
    )


def test_a_catalogue_that_breaks_on_a_file_is_a_refusal_never_a_raise(tmp_path: Path) -> None:
    from vibey.domain.host_clients import HOST_CLIENT_CATALOG

    class _Breaking:
        def __getattr__(self, name: str) -> object:
            return getattr(HOST_CLIENT_CATALOG, name)

        def carries(self, *_args: object) -> bool:
            raise RecursionError("too deep")

    home, project = tmp_path / "home", tmp_path / "project"
    (home / ".cursor").mkdir(parents=True)
    project.mkdir()
    (home / ".cursor" / "mcp.json").write_text("{}")
    tooling = LlmToolingProbe(
        launcher=lambda: PINNED,
        catalog=_Breaking(),  # type: ignore[arg-type]
        home_dir=lambda: home,
        project_dir=lambda: project,
        platform="linux",
        shipped_skill=lambda: None,
        environ={},
    )
    finding = by_name(tooling.findings())["cursor:mcp-server"]
    assert finding.state == "missing" and "cannot be parsed" in finding.detail
