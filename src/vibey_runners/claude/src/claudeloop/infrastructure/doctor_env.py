# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Real DoctorEnvironment — the only infrastructure adapter for the `doctor`
use case. Shells out to `claude` itself for version/MCP info rather than
re-implementing config-file parsing, since that surface is exactly the kind
the docs warn changes between Claude Code releases (see
docs/architecture/decisions/0002-agent-sdk-over-subprocess.md).

It looks for Claude Code in the order the SDK does — the CLI bundled inside
claude-agent-sdk first, then `claude` on PATH — so it checks the CLI a run will
actually launch, and a container with no global install still gets its MCP
servers and login checked. For a local backend profile it asks the
profile's endpoint directly whether it answers and which models it has."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess  # nosec B404 - fixed-argument calls to the `claude` CLI only, never shell=True
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

import claude_agent_sdk

from claudeloop.application.dto import BackendStatus, ToolCallStatus

# Tried in order: the Anthropic/OpenAI-style listing most compatible servers
# offer (Ollama answers it), then Ollama's native one.
_MODEL_LISTINGS = (("/v1/models", "data", "id"), ("/api/tags", "models", "name"))
DEFAULT_BACKEND_PROBE_TIMEOUT_SECONDS = 5.0
# Asking a model for a tool call may load it first; a 14B model took ~10s here.
DEFAULT_TOOL_PROBE_TIMEOUT_SECONDS = 180.0
_TOOL_PROBE_TOOL = {
    "name": "record_answer",
    "description": "Record the answer to the question.",
    "input_schema": {
        "type": "object",
        "properties": {"answer": {"type": "integer"}},
        "required": ["answer"],
    },
}
_TOOL_PROBE_PROMPT = "Call the record_answer tool with answer set to 42. Do not reply with text."

Opener = Callable[..., Any]


class RealDoctorEnvironment:
    def __init__(
        self,
        *,
        sdk_package_dir: Path | None = None,
        backend_probe_timeout: float = DEFAULT_BACKEND_PROBE_TIMEOUT_SECONDS,
        tool_probe_timeout: float = DEFAULT_TOOL_PROBE_TIMEOUT_SECONDS,
        opener: Opener | None = None,
    ) -> None:
        self._sdk_package_dir = sdk_package_dir or Path(claude_agent_sdk.__file__).parent
        self._timeout = backend_probe_timeout
        self._tool_timeout = tool_probe_timeout
        self._open: Opener = opener or urllib.request.urlopen

    def find_claude_cli(self) -> str | None:
        return shutil.which("claude")

    def find_bundled_claude_cli(self) -> str | None:
        name = "claude.exe" if platform.system() == "Windows" else "claude"
        bundled = self._sdk_package_dir / "_bundled" / name
        return str(bundled) if bundled.is_file() else None

    def _resolved_cli(self) -> str | None:
        # The SDK's own order: its bundled CLI first, then PATH.
        return self.find_bundled_claude_cli() or self.find_claude_cli()

    def claude_cli_version(self, path: str) -> str | None:
        try:
            result = subprocess.run(  # nosec B603
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None

    def is_authenticated(self) -> bool:
        if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
            return True
        # `claude auth status` is the authoritative source — it reports true
        # for claude.ai/OAuth-profile logins (e.g. `ant auth login`) that
        # never touch ANTHROPIC_API_KEY or a .credentials.json file at all,
        # which the two checks above would otherwise miss entirely.
        cli_path = self._resolved_cli()
        if cli_path is not None:
            try:
                result = subprocess.run(  # nosec B603
                    [cli_path, "auth", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                status = json.loads(result.stdout)
                if isinstance(status, dict) and status.get("loggedIn") is True:
                    return True
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass
        credentials_path = Path.home() / ".claude" / ".credentials.json"
        return credentials_path.is_file()

    def configured_mcp_servers(self) -> list[str]:
        cli_path = self._resolved_cli()
        if cli_path is None:
            return []
        try:
            # `claude mcp list` actively health-checks every configured server
            # (observed ~14s for 37 servers) — doctor is an explicit
            # pre-flight command, not latency-sensitive, so this gets a
            # generous timeout rather than racing the check itself.
            result = subprocess.run(  # nosec B603
                [cli_path, "mcp", "list"],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []
        if result.returncode != 0:
            return []
        servers = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            servers.append(line.split(":", 1)[0].strip())
        return servers

    def anthropic_sdk_version(self) -> str | None:
        try:
            import anthropic
        except ImportError:
            return None
        return anthropic.__version__

    def api_surface_method_count(self) -> int | None:
        try:
            from claudeloop.infrastructure.api.introspect import discover_surface
        except ImportError:
            return None
        return len(discover_surface())

    @staticmethod
    def _headers(auth_token: str) -> dict[str, str]:
        return {
            "x-api-key": auth_token,
            "authorization": f"Bearer {auth_token}",
            "anthropic-version": "2023-06-01",
        }

    def probe_backend(self, base_url: str, auth_token: str) -> BackendStatus:
        base = base_url.strip().rstrip("/")
        headers = self._headers(auth_token)
        answered = f"{base} answered"
        for path, list_key, name_key in _MODEL_LISTINGS:
            url = f"{base}{path}"
            request = urllib.request.Request(url, headers=headers)
            try:
                # base_url is validated to http:// or https:// when the profile is
                # built (domain/backend.py), so no file: or custom scheme reaches here.
                with self._open(request, timeout=self._timeout) as response:  # nosec B310
                    body = response.read()
            except urllib.error.HTTPError as exc:
                answered = f"{url} answered HTTP {exc.code}"
                continue
            except (urllib.error.URLError, OSError, ValueError) as exc:
                reason = getattr(exc, "reason", None) or exc
                text = str(reason) or type(reason).__name__
                return BackendStatus(reachable=False, detail=f"cannot reach {base}: {text}")
            models = self._model_names(body, list_key=list_key, name_key=name_key)
            if models is None:
                answered = f"{url} answered, but not with a model list"
                continue
            return BackendStatus(
                reachable=True,
                detail=f"{base} answered and lists {len(models)} model(s)",
                models=models,
            )
        return BackendStatus(reachable=True, detail=answered, models=None)

    def probe_tool_calling(self, base_url: str, auth_token: str, model: str) -> ToolCallStatus:
        url = f"{base_url.strip().rstrip('/')}/v1/messages"
        payload = {
            "model": model,
            "max_tokens": 256,
            "tools": [_TOOL_PROBE_TOOL],
            "messages": [{"role": "user", "content": _TOOL_PROBE_PROMPT}],
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={**self._headers(auth_token), "content-type": "application/json"},
            method="POST",
        )
        try:
            # Same scheme guarantee as probe_backend: base_url is http(s) by validation.
            with self._open(request, timeout=self._tool_timeout) as response:  # nosec B310
                body = response.read()
        except urllib.error.HTTPError as exc:
            return ToolCallStatus(supported=None, detail=f"{url} answered HTTP {exc.code}")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            reason = getattr(exc, "reason", None) or exc
            text = str(reason) or type(reason).__name__
            return ToolCallStatus(supported=None, detail=f"no answer from {url}: {text}")
        return self._tool_call_verdict(body)

    @staticmethod
    def _tool_call_verdict(body: bytes) -> ToolCallStatus:
        try:
            data = json.loads(body)
        except ValueError:
            return ToolCallStatus(supported=None, detail="answered, but not with JSON")
        blocks = data.get("content") if isinstance(data, dict) else None
        if not isinstance(blocks, list):
            return ToolCallStatus(supported=None, detail="answered without a content list")
        kinds = [block.get("type") for block in blocks if isinstance(block, dict)]
        if "tool_use" in kinds:
            return ToolCallStatus(supported=True, detail="answered with a tool_use block")
        texts = [
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        snippet = " ".join(" ".join(texts).split())[:120]
        return ToolCallStatus(
            supported=False,
            detail=f"wrote its tool call as text instead of calling it ({snippet!r})",
        )

    @staticmethod
    def _model_names(body: bytes, *, list_key: str, name_key: str) -> tuple[str, ...] | None:
        try:
            data = json.loads(body)
        except ValueError:
            return None
        entries = data.get(list_key) if isinstance(data, dict) else None
        if not isinstance(entries, list):
            return None
        return tuple(
            str(entry[name_key])
            for entry in entries
            if isinstance(entry, dict) and isinstance(entry.get(name_key), str)
        )
