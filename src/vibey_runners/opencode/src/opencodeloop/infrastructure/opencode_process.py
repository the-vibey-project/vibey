# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Subprocess adapter for the official OpenCode CLI."""

import json
import re
import shutil
import subprocess  # nosec B404
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from opencodeloop.domain.model import RunResult, RunStatus

# The documented `opencode run --help` surface this adapter follows.
# `--standalone` is deliberately absent: current OpenCode documentation and
# source do not advertise it, and requiring it would make real installs fail.
_REQUIRED_RUN_FLAGS = ("--format", "--auto", "--dir", "--session")
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
# `opencode auth list --format json` is the CLI's machine-readable credential
# inventory. An empty array/object means that no provider credential is saved.
_STEP_START = frozenset({"step_start", "message_start", "turn_start"})
_STEP_FINISH = frozenset({"step_finish", "message_finish", "turn_finish"})
_TOOL_EVENTS = frozenset({"tool_use", "tool_call", "tool_result"})
_ERROR_EVENTS = frozenset({"error", "session.error"})
# OpenCode serializes provider failures as a named error under `error.name`.
# `ProviderAuthError` and `APIError` are part of the official session schema.
# Only names/statuses that mean a capacity state are mapped; an unrecognized
# name stays Available rather than being guessed.
# vibey's classify.py reads the same names from the same shape.
_CAPACITY_BY_ERROR_NAME = {
    "providerautherror": "auth_failed",
}


class OpenCodeProcess:
    """Call only the documented OpenCode CLI surface and normalize its JSON stream."""

    def __init__(self, binary: str = "opencode") -> None:
        self._binary = binary

    def doctor(self) -> tuple[bool, str]:
        """Check the CLI contract and that at least one provider is authenticated.

        The binary and its JSON run interface are verified first, then
        `opencode auth list --format json` proves that at least one provider
        credential is saved. Model-level reachability remains the CLI's own
        concern: OpenCode is a provider multiplexer, so this check cannot prove
        which provider or model a given run will select.
        """
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
        help_text = self._clean(f"{help_result.stdout}\n{help_result.stderr}")
        missing_flags = tuple(flag for flag in _REQUIRED_RUN_FLAGS if flag not in help_text)
        if help_result.returncode != 0 or "json" not in help_text or missing_flags:
            missing = ", ".join(missing_flags) or "--format json"
            return False, f"OpenCode run does not advertise required flags: {missing}"
        # The auth probe runs only once the run contract is known good: a
        # missing flag means the adapter is unusable regardless of credentials.
        try:
            auth_result = subprocess.run(  # nosec B603
                [binary, "auth", "list", "--format", "json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return False, f"OpenCode preflight failed: {exc}"
        if auth_result.returncode != 0 or not self._has_credentials(auth_result.stdout):
            return False, "OpenCode has no configured provider; run `opencode auth login`"
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
        """Stream OpenCode JSON events into the runner contract as they arrive."""
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
        stderr_chunks: list[str] = []

        def _drain_stderr() -> None:
            # stderr is drained on its own thread so a chatty provider can never
            # fill the pipe and deadlock the run while stdout is being consumed.
            stream = process.stderr
            if stream is not None:
                for chunk in stream:
                    stderr_chunks.append(chunk)

        reader = threading.Thread(target=_drain_stderr, daemon=True)
        reader.start()
        discovered_session = session_id
        stdout = process.stdout
        if stdout is not None:
            for line in stdout:
                if not line.strip():
                    continue
                event = self._normalize(line)
                discovered_session = discovered_session or self._session_id(event)
                emit(event)
        returncode = process.wait()
        reader.join()
        stderr = "".join(stderr_chunks)
        if returncode == 0:
            emit(
                {
                    "event_type": "finished",
                    "success": True,
                    "session_id": discovered_session,
                }
            )
            return RunResult(RunStatus.FINISHED, 0, discovered_session)
        detail = stderr.strip()[-2000:] or f"OpenCode exited with {returncode}"
        emit({"event_type": "failed", "success": False, "detail": detail})
        return RunResult(RunStatus.FAILED, returncode or 1, discovered_session, detail)

    @classmethod
    def _normalize(cls, line: str) -> dict[str, object]:
        """Translate one real OpenCode JSON line into the loop's event vocabulary.

        The provider session boundary is not re-emitted as `run.started`: the
        application owns that boundary exactly once per run. OpenCode's
        `session.created` stays unmapped so a run can never seed the ledger twice.
        """
        try:
            raw: Any = json.loads(line)
        except json.JSONDecodeError:
            return {"event_type": "text_delta", "text": line, "raw": line}
        if not isinstance(raw, dict):
            return {"event_type": "text_delta", "text": str(raw), "raw": raw}
        raw_type = str(raw.get("type", ""))
        if raw_type in _STEP_START:
            return {"event_type": "turn.starting", "raw": raw}
        if raw_type in _STEP_FINISH:
            return {"event_type": "turn.completed", "raw": raw}
        if raw_type in _TOOL_EVENTS:
            return {"event_type": "tool_result", "raw": raw}
        if raw_type in _ERROR_EVENTS:
            return cls._error_event(raw)
        if raw_type in {"session.created", "session_started"}:
            return {"event_type": raw_type, "raw": raw}
        return {"event_type": "text_delta", "raw": raw}

    @classmethod
    def _error_event(cls, raw: Mapping[str, object]) -> dict[str, object]:
        """Surface a provider error's detail and any explicit capacity state.

        A capacity-shaped error becomes `capacity.rejected` with a
        `capacity_state`, the shape vibey's classifier and ledger read; every
        other provider error stays `failed`.
        """
        event: dict[str, object] = {"event_type": "failed", "raw": raw}
        detail = cls._error_detail(raw)
        if detail:
            event["detail"] = detail
        capacity = cls._capacity_state(raw)
        if capacity is not None:
            event["event_type"] = "capacity.rejected"
            event["capacity_state"] = capacity
        return event

    @classmethod
    def _capacity_state(cls, raw: Mapping[str, object]) -> str | None:
        error = raw.get("error")
        if not isinstance(error, Mapping):
            return None
        name = str(error.get("name", "")).lower()
        state = _CAPACITY_BY_ERROR_NAME.get(name)
        data = error.get("data")
        if state is not None or not isinstance(data, Mapping):
            return state
        status_code = data.get("statusCode")
        if name == "apierror" and status_code == 429:
            return "window_exhausted"
        if name == "apierror" and status_code == 402:
            return "credits_exhausted"
        if name == "apierror" and status_code in {401, 403}:
            return "auth_failed"
        return None

    @classmethod
    def _error_detail(cls, raw: Mapping[str, object]) -> str:
        error = raw.get("error")
        if not isinstance(error, Mapping):
            return ""
        data = error.get("data")
        if isinstance(data, Mapping):
            message = data.get("message")
            if isinstance(message, str) and message:
                return message
        name = error.get("name")
        return str(name) if name else ""

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

    @staticmethod
    def _clean(text: str) -> str:
        return _ANSI_ESCAPE.sub("", text)

    @classmethod
    def _has_credentials(cls, text: str) -> bool:
        """Return whether `auth list --format json` contains an account."""
        try:
            payload = json.loads(cls._clean(text))
        except json.JSONDecodeError:
            return False
        if isinstance(payload, Mapping | list):
            return bool(payload)
        return False
