# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Subprocess adapter for the official OpenCode CLI."""

import json
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from pathlib import Path
from typing import Any

from opencodeloop.domain.model import RunResult, RunStatus


class OpenCodeProcess:
    """Call only the documented OpenCode CLI surface and normalize its JSON stream."""

    def __init__(self, binary: str = "opencode") -> None:
        self._binary = binary

    def doctor(self) -> tuple[bool, str]:
        """Check binary presence and the JSON run option before declaring readiness."""
        binary = shutil.which(self._binary)
        if binary is None:
            return False, f"{self._binary!r} was not found on PATH"
        try:
            version = subprocess.run(  # nosec B603
                [binary, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            help_result = subprocess.run(  # nosec B603
                [binary, "run", "--help"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"OpenCode preflight failed: {exc}"
        if version.returncode != 0:
            return False, "OpenCode --version failed"
        help_text = f"{help_result.stdout}\n{help_result.stderr}"
        required_flags = ("--format", "--standalone", "--auto", "--dir", "--session")
        missing_flags = tuple(flag for flag in required_flags if flag not in help_text)
        if help_result.returncode != 0 or "json" not in help_text or missing_flags:
            missing = ", ".join(missing_flags) or "--format json"
            return False, f"OpenCode run does not advertise required flags: {missing}"
        version_text = (
            version.stdout.strip().splitlines()[0] if version.stdout.strip() else "unknown"
        )
        return True, f"{version_text}; run --format json available"

    def execute(
        self,
        *,
        prompt: str,
        cwd: Path,
        session_id: str | None,
        emit: Callable[[dict[str, object]], None],
    ) -> RunResult:
        """Stream OpenCode JSON events into the runner contract."""
        binary = shutil.which(self._binary)
        if binary is None:
            raise OSError(f"{self._binary!r} was not found on PATH")
        # The official CLI accepts the message as the positional payload.  The
        # adapter also enables its documented unattended permission mode so a
        # worker never waits for an interactive approval inside a worktree.
        command = [
            binary,
            "run",
            "--format",
            "json",
            "--standalone",
            "--auto",
            "--dir",
            str(cwd),
        ]
        if session_id:
            command.extend(["--session", session_id])
        command.append(prompt)
        process = subprocess.Popen(  # nosec B603
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()
        discovered_session = session_id
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = self._normalize(line)
            discovered_session = discovered_session or self._session_id(event)
            emit(event)
        if process.returncode == 0:
            emit(
                {
                    "event_type": "finished",
                    "success": True,
                    "session_id": discovered_session,
                }
            )
            return RunResult(RunStatus.FINISHED, 0, discovered_session)
        detail = stderr.strip()[-2000:] or f"OpenCode exited with {process.returncode}"
        emit({"event_type": "failed", "success": False, "detail": detail})
        return RunResult(RunStatus.FAILED, process.returncode or 1, discovered_session, detail)

    @classmethod
    def _normalize(cls, line: str) -> dict[str, object]:
        try:
            raw: Any = json.loads(line)
        except json.JSONDecodeError:
            return {"event_type": "text_delta", "text": line, "raw": line}
        if not isinstance(raw, dict):
            return {"event_type": "text_delta", "text": str(raw), "raw": raw}
        raw_type = str(raw.get("type", ""))
        if raw_type in {"step_start", "message_start", "turn_start"}:
            event_type = "turn.starting"
        elif raw_type in {"step_finish", "message_finish", "turn_finish"}:
            event_type = "turn.completed"
        elif raw_type in {"tool_use", "tool_call", "tool_result"}:
            event_type = "tool_result"
        elif raw_type in {"error", "session.error"}:
            event_type = "failed"
        elif raw_type in {"session.created", "session_started"}:
            event_type = "run.started"
        else:
            event_type = "text_delta"
        return {"event_type": event_type, "raw": raw}

    @staticmethod
    def _session_id(event: dict[str, object]) -> str | None:
        raw = event.get("raw")
        if not isinstance(raw, dict):
            return None
        for key in ("sessionID", "sessionId", "session_id"):
            value = raw.get(key)
            if isinstance(value, str) and value:
                return value
        return None
