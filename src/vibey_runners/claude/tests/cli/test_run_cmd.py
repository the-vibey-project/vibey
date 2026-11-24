# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for cli/commands/run.py — _parse_connector and run command logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import Result
from typer.testing import CliRunner

from claudeloop.cli.app import app
from claudeloop.cli.commands.run import _parse_connector
from claudeloop.domain.capabilities import CLAUDE_BUILTIN_WEB_TOOLS, AppliedCapabilities
from claudeloop.infrastructure.agent.gateway import ClaudeAgentGateway
from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
from tests.capability_documents import DIGEST, CapabilityDocumentWriter

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb"}


class TestParseConnector:
    def test_name_url(self) -> None:
        name, cfg = _parse_connector("myconn=https://example.com")
        assert name == "myconn"
        assert cfg == {"url": "https://example.com"}

    def test_name_json(self) -> None:
        spec = 'myconn={"url": "http://localhost:8080", "key": "val"}'
        name, cfg = _parse_connector(spec)
        assert name == "myconn"
        assert cfg["url"] == "http://localhost:8080"
        assert cfg["key"] == "val"

    def test_no_equals_raises(self) -> None:
        with pytest.raises(ValueError, match="connector must be NAME="):
            _parse_connector("noequals")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="connector name must not be blank"):
            _parse_connector("=value")

    def test_whitespace_trimmed(self) -> None:
        name, cfg = _parse_connector("  conn  =  http://x  ")
        assert name == "conn"
        assert cfg == {"url": "http://x"}

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_connector("conn={bad json}")


class TestRunCommandErrors:
    def test_run_bad_plan_file(self) -> None:
        result = runner.invoke(app, ["run", "/does/not/exist.md"], env=_ENV)
        assert result.exit_code != 0

    def test_run_invalid_slash(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", str(plan), "--slash", "no-prefix"],
            env=_ENV,
        )
        assert result.exit_code == 2
        assert "must start with" in result.output

    def test_run_invalid_connector(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", str(plan), "--connector", "noequalssign"],
            env=_ENV,
        )
        assert result.exit_code == 2
        assert "Invalid --connector" in result.output

    def test_run_invalid_wind_down_at(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", str(plan), "--wind-down-at", "not-a-valid-time"],
            env=_ENV,
        )
        assert result.exit_code == 2
        assert "Invalid --wind-down-at" in result.output


class TestRunSuccess:
    def test_run_success_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.events_path = tmp_path / "events.jsonl"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reason = "done"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 0
            assert "Done:" in result.output

    def test_run_failure_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "credits exhausted"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 1

    def test_run_wind_down_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.root = tmp_path
        (tmp_path / "HANDOFF.md").write_text("handoff info", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "wind-down: operator requested"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
            patch("claudeloop.cli.commands.run.HANDOFF_MARKER_FILENAME", "HANDOFF.md"),
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code != 0

    def test_run_stopped_path(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.stop_summary_path = tmp_path / "stop.json"

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "stopped by operator"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 130

    def test_run_build_runner_value_error(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.side_effect = ValueError("bad config")

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 2

    def test_run_build_runner_file_exists(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.side_effect = FileExistsError("exists")

            result = runner.invoke(
                app,
                ["run", str(plan), "--run-id", "dupe"],
                env=_ENV,
            )
            assert result.exit_code == 2
            assert "already exists" in result.output

    def test_run_invalid_plan_error(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            from claudeloop.domain.errors import InvalidPlanError

            mock_parse.side_effect = InvalidPlanError("no heading")

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 1
            assert "Invalid plan" in result.output

    def test_run_with_valid_connector_success(self, tmp_path: Path) -> None:
        """A --connector spec that parses cleanly exercises the for-loop's
        non-exception path (lines 195->202, 201) all the way to the end."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.events_path = tmp_path / "events.jsonl"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reason = "done"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan), "--connector", "myconn=http://localhost"],
                env=_ENV,
            )
            assert result.exit_code == 0
            assert "Done:" in result.output
            _, kwargs = mock_bootstrap.build_runner.call_args
            assert kwargs["connectors"] == {"myconn": {"url": "http://localhost"}}

    def test_run_stream_ui_thread_runs_and_handles_runtime_error(self, tmp_path: Path) -> None:
        """--stream-ui spawns a daemon thread that runs the Textual app and
        swallows a RuntimeError (e.g. no TTY) — lines 271-287."""
        import threading as real_threading

        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.events_path = tmp_path / "events.jsonl"

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.reason = "done"

        class _SyncThread:
            def __init__(self, target=None, daemon=None) -> None:
                self._target = target

            def start(self) -> None:
                if self._target is not None:
                    self._target()

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
            patch(
                "claudeloop.cli.commands.run.run_textual_app",
                side_effect=RuntimeError("no tty available"),
            ),
            patch.object(real_threading, "Thread", _SyncThread),
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan), "--stream-ui"],
                env=_ENV,
            )
            assert result.exit_code == 0
            assert "no tty available" in result.output

    def test_run_from_plan_file_invalid_plan_at_runtime(self, tmp_path: Path) -> None:
        """InvalidPlanError raised from run_from_plan_file itself (as
        opposed to parse_plan_file) — lines 296-298."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.events_path = tmp_path / "events.jsonl"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            from claudeloop.domain.errors import InvalidPlanError

            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.side_effect = InvalidPlanError("bad plan at runtime")

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 1
            assert "Invalid plan" in result.output

    def test_run_wind_down_without_handoff_marker(self, tmp_path: Path) -> None:
        """Wind-down completes but no handoff marker file exists on disk —
        the marker.is_file() branch takes the False arm (307->309)."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        mock_context.run_dir.root = tmp_path / "run-root"
        (tmp_path / "run-root").mkdir()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "wind-down: operator requested"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
            patch("claudeloop.cli.commands.run.HANDOFF_MARKER_FILENAME", "HANDOFF.md"),
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code != 0
            assert "Handoff:" not in result.output

    def test_run_stopped_path_with_summary_file(self, tmp_path: Path) -> None:
        """A stopped run whose stop-summary file actually exists on disk —
        the summary.is_file() branch takes the True arm (line 314)."""
        plan = tmp_path / "plan.md"
        plan.write_text("# Test Plan\nDo something\n", encoding="utf-8")

        mock_context = MagicMock()
        mock_context.run_id = "test-run-1"
        mock_context.trace_id = "test-trace-1"
        mock_context.run_dir = MagicMock()
        summary_path = tmp_path / "stop-summary.md"
        summary_path.write_text("stopped early", encoding="utf-8")
        mock_context.run_dir.stop_summary_path = summary_path

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.reason = "stopped by operator"

        with (
            patch("claudeloop.cli.commands.run.load_config") as mock_config,
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.parse_plan_file") as mock_parse,
            patch("claudeloop.cli.commands.run.bootstrap") as mock_bootstrap,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock
            ) as mock_run,
        ):
            mock_config.return_value = MagicMock(
                log_file=None,
                log_level="INFO",
                done_marker=None,
            )
            mock_parse.return_value = MagicMock()
            mock_bootstrap.build_runner.return_value = mock_context
            mock_run.return_value = mock_result

            result = runner.invoke(
                app,
                ["run", str(plan)],
                env=_ENV,
            )
            assert result.exit_code == 130
            assert "Stop summary:" in result.output


class TestRunWithCapabilities:
    """`--capabilities PATH`: the run's locked capability snapshot (SP-LOOPS Phase 4, Task 4;
    R9, R12; Review Focus 5). These go through the real composition root; only the logging setup
    and the run itself are stubbed, so no session ever starts."""

    gateway: MagicMock

    def _invoke(
        self, tmp_path: Path, document: Path, *extra: str
    ) -> tuple[Result, Path, AsyncMock, MagicMock]:
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        home = tmp_path / "home"
        home.mkdir(exist_ok=True)
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something\n", encoding="utf-8")
        done = MagicMock(success=True, reason="done")
        with (
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file",
                new_callable=AsyncMock,
                return_value=done,
            ) as session,
            patch("claudeloop.bootstrap.resolve_test_agent_from_env") as scripted,
            patch("claudeloop.bootstrap.ClaudeAgentGateway", wraps=ClaudeAgentGateway) as gateway,
        ):
            self.gateway = gateway
            # None: the real gateway is built (it connects only on a first turn, which the stubbed
            # run never sends), so the composition root's wiring of the snapshot is exercised.
            scripted.return_value = None
            result = runner.invoke(
                app,
                [
                    "run",
                    str(plan),
                    "--cwd",
                    str(repo),
                    "--run-id",
                    "r1",
                    "--capabilities",
                    str(document),
                    *extra,
                ],
                env={**_ENV, "HOME": str(home)},
            )
        return result, repo, session, scripted

    def test_a_refused_document_exits_78_before_any_session(self, tmp_path: Path) -> None:
        document = CapabilityDocumentWriter(tmp_path).write()
        raw = json.loads(document.read_text(encoding="utf-8"))
        raw["version"] = 99
        document.write_text(json.dumps(raw), encoding="utf-8")
        result, repo, session, scripted = self._invoke(tmp_path, document)
        assert result.exit_code == 78
        assert str(document) in result.output
        session.assert_not_called()
        scripted.assert_not_called()
        assert not (repo / ".claudeloop" / "runs").exists()

    def test_a_missing_document_exits_78(self, tmp_path: Path) -> None:
        result, _, session, _ = self._invoke(tmp_path, tmp_path / "nowhere" / "capabilities.json")
        assert result.exit_code == 78
        session.assert_not_called()

    def test_web_search_with_builtin_web_off_exits_2(self, tmp_path: Path) -> None:
        document = CapabilityDocumentWriter(tmp_path).write(builtin_web=False)
        result, repo, session, _ = self._invoke(tmp_path, document, "--web-search")
        assert result.exit_code == 2
        assert "--web-search" in result.output
        session.assert_not_called()
        assert not (repo / ".claudeloop" / "runs").exists()

    def test_a_connector_named_like_a_snapshot_server_exits_2(self, tmp_path: Path) -> None:
        document = CapabilityDocumentWriter(tmp_path).write()
        applied = AppliedCapabilities(
            digest=DIGEST,
            plugin_dirs=(),
            skills=(),
            mcp_servers={"docs": {"type": "http", "url": "https://example.invalid/mcp"}},
            disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS,
            add_dirs=(),
            system_prompt_append="",
            notices=(),
        )
        with patch.object(CapabilitySnapshotApplier, "load", return_value=applied):
            result, _, session, _ = self._invoke(
                tmp_path, document, "--connector", "docs=https://other.invalid"
            )
        assert result.exit_code == 2
        assert "'docs'" in result.output
        session.assert_not_called()

    def test_capabilities_applied_is_in_the_runs_events_with_counts_only(
        self, tmp_path: Path
    ) -> None:
        writer = CapabilityDocumentWriter(tmp_path)
        document = writer.write(folders=[tmp_path / "inputs"])
        result, repo, session, _ = self._invoke(tmp_path, document)
        assert result.exit_code == 0, result.output
        session.assert_awaited_once()
        events = next((repo / ".claudeloop" / "runs").rglob("events.jsonl"))
        text = events.read_text(encoding="utf-8")
        entries = [json.loads(line) for line in text.splitlines()]
        applied = [e for e in entries if e["event_type"] == "capabilities.applied"]
        assert len(applied) == 1
        assert applied[0]["run_id"] == "r1"
        assert applied[0]["payload"] == {
            "digest": DIGEST,
            "plugins": 2,
            "skills": 2,
            "mcp_servers": 0,
            "disallowed_tools": ["WebSearch", "WebFetch"],
            "instruction_files": [],
            "notices": [],
        }
        assert str(writer.run) not in text
        assert str(tmp_path / "inputs") not in text
        given = self.gateway.call_args.kwargs["applied"]
        assert given.digest == DIGEST
        assert given.plugin_dirs == (
            str(writer.run / "plugins" / "alpha"),
            str(writer.run / "plugins" / "beta"),
        )

    def test_the_document_reaches_the_composition_root_and_notices_are_said(
        self, tmp_path: Path
    ) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something\n", encoding="utf-8")
        document = tmp_path / "capabilities.json"
        context = MagicMock(run_id="r1", trace_id="t1")
        context.run_dir.events_path = tmp_path / "events.jsonl"
        context.applied = AppliedCapabilities(
            digest=DIGEST,
            plugin_dirs=(),
            skills=(),
            mcp_servers={},
            disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS,
            add_dirs=(),
            system_prompt_append="",
            notices=("builtin_web = true is not applied on a local backend",),
        )
        with (
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.bootstrap") as composition,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file",
                new_callable=AsyncMock,
                return_value=MagicMock(success=True, reason="done"),
            ),
        ):
            composition.build_runner.return_value = context
            result = runner.invoke(
                app,
                ["run", str(plan), "--capabilities", str(document)],
                env={**_ENV, "HOME": str(tmp_path)},
            )
        assert result.exit_code == 0, result.output
        assert composition.build_runner.call_args.kwargs["capabilities"] == document
        assert "builtin_web = true is not applied on a local backend" in result.output
        assert "capabilities.applied" in (tmp_path / "events.jsonl").read_text(encoding="utf-8")

    def test_without_capabilities_nothing_is_recorded(self, tmp_path: Path) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\nDo something\n", encoding="utf-8")
        context = MagicMock(run_id="r1", trace_id="t1")
        context.run_dir.events_path = tmp_path / "events.jsonl"
        with (
            patch("claudeloop.cli.commands.run.configure_logging"),
            patch("claudeloop.cli.commands.run.bootstrap") as composition,
            patch(
                "claudeloop.cli.commands.run.run_from_plan_file",
                new_callable=AsyncMock,
                return_value=MagicMock(success=True, reason="done"),
            ),
        ):
            composition.build_runner.return_value = context
            result = runner.invoke(app, ["run", str(plan)], env={**_ENV, "HOME": str(tmp_path)})
        assert result.exit_code == 0, result.output
        assert composition.build_runner.call_args.kwargs["capabilities"] is None
        assert not (tmp_path / "events.jsonl").exists()
