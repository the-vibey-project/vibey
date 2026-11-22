# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The "LLM tooling" lines of `vibey connect`, `vibey doctor` and `vibey acp` (SP-ACP).

One line per client and surface in doctor's own grammar, cleaned like any machine text, and a
section that never fails doctor. `vibey doctor --json` reads them as findings, with no new key
in its document."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from vibey.application.dto import PreflightResult
from vibey.cli.doctor_output import DoctorLineParser
from vibey.cli.interfaces.llm_tooling_interface import LlmToolingSectionInterface
from vibey.cli.llm_tooling import LLM_TOOLING_SECTION, LlmToolingSection
from vibey.cli.main import app
from vibey.domain.llm_tooling import ToolingFinding
from vibey.infrastructure.mcp.llm_tooling_probe import LlmToolingProbe

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
PREFLIGHT = "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight"


class _Probe:
    def __init__(self, found: tuple[ToolingFinding, ...]) -> None:
        self._found = found
        self.asked: list[Sequence[str] | None] = []

    def detected(self) -> tuple[()]:
        return ()

    def findings(self, client_ids: Sequence[str] | None = None) -> tuple[ToolingFinding, ...]:
        self.asked.append(client_ids)
        return self._found


FOUND = (
    ToolingFinding("zed", "acp-agent", "present", "in ~/.config/zed/settings.json"),
    ToolingFinding("claude_code", "plugin", "missing", "run /plugin install vibey@vibey"),
    ToolingFinding("cursor", "skill", "not-applicable", "no skills folder"),
)


def test_the_section_honours_its_interface() -> None:
    assert isinstance(LLM_TOOLING_SECTION, LlmToolingSectionInterface)


def test_each_surface_is_one_line_in_doctors_grammar() -> None:
    lines = LlmToolingSection(_Probe(FOUND)).lines()
    assert lines == [
        f"PASS {'zed:acp-agent':<26} present: in ~/.config/zed/settings.json",
        f"WARN {'claude_code:plugin':<26} missing: run /plugin install vibey@vibey",
        f"UNKNOWN {'cursor:skill':<26} not-applicable: no skills folder",
    ]
    parsed = [DoctorLineParser().parse(line) for line in lines]
    assert [(p.mark, p.name) for p in parsed] == [
        ("PASS", "zed:acp-agent"),
        ("WARN", "claude_code:plugin"),
        ("UNKNOWN", "cursor:skill"),
    ]


def test_the_clients_asked_for_are_passed_through() -> None:
    probe = _Probe(FOUND)
    LlmToolingSection(probe).lines(["zed"])
    assert probe.asked == [["zed"]]


def test_with_no_client_installed_one_line_says_so() -> None:
    assert LlmToolingSection(_Probe(())).lines() == [
        f"UNKNOWN {'llm-tooling':<26} no supported LLM client is installed here"
    ]


def test_a_detail_from_a_file_is_one_cleaned_line_and_a_snippet_survives_whole() -> None:
    snippet = '"agent_servers": {"vibey": {"type": "custom", "command": "' + "/x" * 120 + '"}}'
    dirty = (
        ToolingFinding("zed", "acp-agent", "missing", f"bad\x1b[2J‮ file\nsecond {snippet}"),
        ToolingFinding("cursor", "mcp-server", "missing", "https://me:pw@host/x " + snippet),
    )
    first, second = LlmToolingSection(_Probe(dirty)).lines()
    assert "\x1b" not in first and "‮" not in first and "second" not in first
    assert "pw@" not in second and "https://***@host/x" in second
    assert second.endswith(snippet)


def test_the_section_never_fails_doctor() -> None:
    missing = (ToolingFinding("zed", "acp-agent", "missing", "x"),)
    lines, ok = LlmToolingSection(_Probe(missing)).doctor_lines()
    assert ok is True and lines[0].startswith("WARN ")


def _doctor(args: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("VIBEY_PG_URL", raising=False)
    home = tmp_path / "home"
    (home / ".config" / "zed").mkdir(parents=True)
    section = LlmToolingSection(
        LlmToolingProbe(
            launcher=lambda: "/pinned/vibey",
            home_dir=lambda: home,
            project_dir=lambda: tmp_path,
            platform="linux",
            shipped_skill=lambda: None,
            environ={},
        )
    )
    with (
        patch(PREFLIGHT, new=AsyncMock(return_value=PreflightResult(True, "1", True))),
        patch("vibey.cli.main.LLM_TOOLING_SECTION", section),
    ):
        return runner.invoke(app, ["doctor", "--engine", "claudeloop", *args])


def test_doctor_prints_the_llm_tooling_section_last_without_failing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _doctor([], tmp_path, monkeypatch)
    lines = result.stdout.splitlines()
    tooling = [line for line in lines if len(line.split()) > 1 and line.split()[1][:4] == "zed:"]
    assert [line.split()[1] for line in tooling] == [
        "zed:acp-agent",
        "zed:mcp-server",
        "zed:skill",
        "zed:plugin",
    ]
    assert lines[-4:] == tooling
    assert (
        tooling[0].startswith("WARN zed:acp-agent") and "vibey connect --client zed" in (tooling[0])
    )


def test_doctor_json_carries_the_surfaces_as_checks_and_no_new_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document = json.loads(_doctor(["--json"], tmp_path, monkeypatch).stdout)
    assert set(document) == {"ok", "mode", "engines", "postgresql", "checks", "notes"}
    surfaces = {c["name"]: c["mark"] for c in document["checks"] if ":" in (c["name"] or "")}
    assert surfaces == {
        "zed:acp-agent": "WARN",
        "zed:mcp-server": "UNKNOWN",
        "zed:skill": "UNKNOWN",
        "zed:plugin": "UNKNOWN",
    }


class _Broken:
    def detected(self) -> tuple[()]:
        return ()

    def findings(self, client_ids: Sequence[str] | None = None) -> tuple[ToolingFinding, ...]:
        raise RecursionError("maximum recursion depth exceeded\x1b[2J")


def test_a_probe_that_breaks_is_one_unknown_line_and_never_fails_doctor() -> None:
    lines, ok = LlmToolingSection(_Broken()).doctor_lines()
    assert ok is True
    assert lines == [
        f"UNKNOWN {'llm-tooling':<26} could not read the clients' configurations "
        "(RecursionError: maximum recursion depth exceeded [2J)"
    ]


def test_doctor_in_a_folder_with_a_deeply_nested_mcp_json_still_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "home" / ".claude").mkdir(parents=True)
    (tmp_path / ".mcp.json").write_text("// c\n" + "[" * 200_000)
    result = _doctor([], tmp_path, monkeypatch)
    assert result.exit_code == 0, result.output
    line = next(x for x in result.stdout.splitlines() if "claude_code:mcp-server" in x)
    assert line.startswith("WARN ") and "invalid JSON" in line


def test_doctor_never_reports_a_planted_project_entry_as_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugins = tmp_path / "home" / ".claude" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "installed_plugins.json").write_text(json.dumps({"plugins": {"vibey@vibey": []}}))
    planted = {"command": "/pinned/vibey", "args": ["mcp"], "env": {"PYTHONPATH": "/repo/evil"}}
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"vibey": planted}}))
    result = _doctor([], tmp_path, monkeypatch)
    assert result.exit_code == 0, result.output
    line = next(x for x in result.stdout.splitlines() if "claude_code:mcp-server" in x)
    assert line.startswith("WARN ") and "vibey connect --client claude_code" in line
