# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""OpenAI-compatible inference adapters.

Two kinds live here. Managed servers (llama.cpp, vLLM) are spawned on loopback with a
per-launch token, owned, and stopped by qwenloop. An attached server (openai-compat, Ollama
first) is somebody else's: qwenloop checks it, talks to it, and never starts or stops it.
"""

import asyncio
import fcntl
import json
import os
import re
import signal
import socket
import urllib.error
import urllib.request
from collections.abc import AsyncIterator, Sequence
from contextlib import suppress
from dataclasses import asdict, replace
from pathlib import Path
from typing import IO
from urllib.parse import urlsplit

from platformdirs import user_cache_path

from qwenloop.domain.model import (
    Backend,
    ChatChunk,
    ChatMessage,
    ModelProfile,
    ServerInfo,
    ToolCallParseError,
)

#: How Ollama words a model reply it could not parse as a tool call (#386).
_TOOL_CALL_PARSE_FAILURE = re.compile(r"error parsing tool call", re.IGNORECASE)

#: The llama-server `timings` keys a run records per turn (#382).
_SERVER_TIMING_KEYS = (
    "prompt_n",
    "cache_n",
    "prompt_ms",
    "predicted_n",
    "predicted_ms",
    "predicted_per_second",
)


def _message_payload(message: ChatMessage) -> dict[str, object]:
    """Serialize tool-call context so the next model turn can continue correctly."""
    payload: dict[str, object] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = list(message.tool_calls)
    if message.tool_call_id is not None:
        payload["tool_call_id"] = message.tool_call_id
    return payload


class OpenAIServer:
    binary: str
    backend: Backend
    #: How long one model request may take, in seconds; None waits indefinitely. The
    #: CLI sets it from `idle_timeout_seconds` (#345); 900 matches that key's default.
    request_timeout_seconds: float | None = 900

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or user_cache_path("qwenloop")

    def inspect(self, profile: ModelProfile) -> ServerInfo | None:
        state = self.cache_dir / "servers" / f"{profile.name}.json"
        if not state.is_file():
            return None
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
            return ServerInfo(
                backend=Backend(data["backend"]),
                profile=str(data["profile"]),
                endpoint=str(data["endpoint"]),
                owned=bool(data["owned"]),
                healthy=False,
                pid=int(data["pid"]),
                token=str(data.get("token", "")),
                model=str(data.get("model", "")),
                argv=tuple(str(item) for item in data.get("argv", ())),
                log_path=str(data.get("log_path", "")),
            )
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return None

    async def install(self, profile: ModelProfile) -> Path:
        raise RuntimeError(
            "model installation is explicit but network transfer is delegated to the runtime; "
            f"install {profile.repository}@{profile.revision} ({profile.filename or 'safetensors'})"
        )

    async def start(self, profile: ModelProfile) -> ServerInfo:
        lock = await asyncio.to_thread(_acquire_profile_lock, self.cache_dir, profile.name)
        try:
            existing = self.inspect(profile)
            if existing is not None and existing.pid is not None and _pid_alive(existing.pid):
                return existing
            port = _free_port()
            token = os.urandom(24).hex()
            argv = self._argv(profile, port, token)
            # The server's own load, memory and slot messages are evidence for tuning it
            # (#382); they go to a log beside its state instead of to /dev/null. The child
            # keeps its own descriptor, so ours closes as soon as it has started.
            log_path = self.cache_dir / "servers" / profile.name / "server.log"
            log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with log_path.open("ab") as log:
                process = await asyncio.create_subprocess_exec(
                    *argv,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
            info = ServerInfo(
                backend=self.backend,
                profile=profile.name,
                endpoint=f"http://127.0.0.1:{port}/v1",
                owned=True,
                healthy=False,
                pid=process.pid,
                token=token,
                model=profile.name,
                argv=self._redacted(argv, token),
                log_path=str(log_path),
            )
            state = self.cache_dir / "servers" / f"{profile.name}.json"
            state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            state.write_text(
                json.dumps({**asdict(info), "backend": info.backend.value}),
                encoding="utf-8",
            )
            return info
        finally:
            await asyncio.to_thread(_release_profile_lock, lock)

    async def health(self, info: ServerInfo) -> bool:
        request = urllib.request.Request(f"{info.endpoint}/models", headers=self._auth(info.token))
        try:
            response = await asyncio.to_thread(urllib.request.urlopen, request, timeout=2)
            return bool(response.status == 200)
        except (OSError, urllib.error.URLError):
            return False

    async def chat_stream(
        self, info: ServerInfo, messages: Sequence[ChatMessage]
    ) -> AsyncIterator[ChatChunk]:
        payload = json.dumps(
            {
                "model": info.model or info.profile,
                "messages": [_message_payload(item) for item in messages],
                "tools": _CODING_TOOLS,
                "tool_choice": "auto",
                "stream": False,
            }
        ).encode()
        request = urllib.request.Request(
            f"{info.endpoint}/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json", **self._auth(info.token)},
        )
        try:
            response = await asyncio.to_thread(
                urllib.request.urlopen, request, timeout=self.request_timeout_seconds
            )
        except urllib.error.HTTPError as exc:
            detail = _http_error_detail(exc)
            # A reply the server could not parse as a tool call is one bad turn, which the
            # runner retries (#386); every other HTTP error ends the run as before.
            if exc.code == 500 and _TOOL_CALL_PARSE_FAILURE.search(detail):
                raise ToolCallParseError(detail) from exc
            raise RuntimeError(detail) from exc
        data = json.loads(response.read())
        message = data["choices"][0]["message"]
        calls = message.get("tool_calls", [])
        content = message.get("content") or ""
        if not calls:
            parsed, content = _parse_text_tool_calls(content)
            calls = [
                {"function": {"name": call["name"], "arguments": call["arguments"]}}
                for call in parsed
            ]
        for call in calls:
            function = call.get("function", {})
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            tool_call = {"name": function.get("name", ""), "arguments": arguments}
            if call.get("id"):
                tool_call["id"] = str(call["id"])
            yield ChatChunk(tool_call=tool_call)
        usage = data.get("usage", {})
        yield ChatChunk(
            text=content,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
            timings=self._server_timings(data.get("timings")),
        )

    async def stop(self, info: ServerInfo) -> None:
        if not info.owned or info.pid is None:
            return
        try:
            os.killpg(info.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        else:
            for _ in range(100):
                if not _pid_alive(info.pid):
                    break
                await asyncio.sleep(0.1)
            else:
                with suppress(ProcessLookupError):
                    os.killpg(info.pid, signal.SIGKILL)
        state = self.cache_dir / "servers" / f"{info.profile}.json"
        current = self.inspect(
            ModelProfile(info.profile, info.backend, "", "", None, None, None, "")
        )
        if current is not None and current.pid == info.pid:
            state.unlink(missing_ok=True)

    def _argv(self, profile: ModelProfile, port: int, token: str) -> tuple[str, ...]:
        raise NotImplementedError

    @staticmethod
    def _redacted(argv: Sequence[str], token: str) -> tuple[str, ...]:
        """The argv as it may be recorded: the per-launch API key never leaves the process."""
        return tuple("<redacted>" if token and item == token else item for item in argv)

    @staticmethod
    def _server_timings(timings: object) -> dict[str, float] | None:
        """llama-server's own timings for one request, exactly as it reported them.

        Only the keys a run is tuned by pass through, and a key the server did not send is
        left out rather than invented. Anything that is not a mapping of numbers is no
        timing at all.
        """
        if not isinstance(timings, dict):
            return None
        kept = {
            key: float(timings[key])
            for key in _SERVER_TIMING_KEYS
            if isinstance(timings.get(key), int | float) and not isinstance(timings[key], bool)
        }
        return kept or None

    @staticmethod
    def _auth(token: str) -> dict[str, str]:
        """A bearer header when there is a token; none at all when there is not.

        Ollama needs no key, and `Authorization: Bearer ` with nothing after it is a
        malformed credential some gateways reject outright rather than ignore.
        """
        return {"Authorization": f"Bearer {token}"} if token else {}


class LlamaCppServer(OpenAIServer):
    binary = "llama-server"
    backend = Backend.LLAMA_CPP

    def _argv(self, profile: ModelProfile, port: int, token: str) -> tuple[str, ...]:
        model = self.cache_dir / "models" / profile.name / str(profile.filename)
        if not model.is_file():
            raise FileNotFoundError(f"model is not installed: {model}")
        return (
            self.binary,
            "--model",
            str(model),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--ctx-size",
            str(profile.context_window),
            "--api-key",
            token,
            "--jinja",
        )


class VllmServer(OpenAIServer):
    binary = "vllm"
    backend = Backend.VLLM

    def _argv(self, profile: ModelProfile, port: int, token: str) -> tuple[str, ...]:
        return (
            self.binary,
            "serve",
            profile.repository,
            "--revision",
            profile.revision,
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--api-key",
            token,
            "--enable-auto-tool-choice",
            "--tool-call-parser",
            "hermes",
            "--max-model-len",
            str(profile.context_window),
            # vLLM serves under the repository id unless told otherwise, and rejects a
            # request naming anything else; this makes the name every request sends
            # (the profile's) the name vLLM actually answers to.
            "--served-model-name",
            profile.name,
        )


class OpenAICompatServer(OpenAIServer):
    """An OpenAI-compatible server qwenloop attaches to and never starts or stops (ADR 0003).

    Ollama is the primary target, but anything serving `GET /models` and
    `POST /chat/completions` under its base URL qualifies: LM Studio, a vLLM somebody
    else runs, a hosted gateway. `owned` is always False, so `stop()` is a no-op, and
    `start()` spawns nothing: it proves the endpoint is up and serves the configured
    model, or fails saying which of the two it is not.
    """

    backend = Backend.OPENAI_COMPAT

    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        api_key: str = "",
        timeout_seconds: float = 5,
        context_window: int = 32_768,
        cache_dir: Path | None = None,
    ) -> None:
        super().__init__(cache_dir)
        base = base_url.rstrip("/")
        parts = urlsplit(base)
        if parts.scheme not in {"http", "https"} or not parts.hostname:
            raise ValueError(f"base_url must be an http:// or https:// URL, got {base!r}")
        if parts.username is not None or parts.password is not None:
            raise ValueError("base_url must not include credentials; use QWENLOOP_API_KEY")
        self.base_url = base
        self.model = model
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._context_window = context_window

    @property
    def profile(self) -> ModelProfile:
        """What a run records about the model: the endpoint serves it, so it pins nothing."""
        return ModelProfile(
            name=self.model,
            backend=Backend.OPENAI_COMPAT,
            repository=self.base_url,
            revision="endpoint-managed",
            filename=None,
            sha256=None,
            size=None,
            quantization="endpoint-managed",
            context_window=self._context_window,
        )

    def inspect(self, profile: ModelProfile) -> ServerInfo:
        return ServerInfo(
            backend=Backend.OPENAI_COMPAT,
            profile=profile.name,
            endpoint=self.base_url,
            owned=False,
            healthy=False,
            token=self._api_key,
            model=self.model,
        )

    async def install(self, profile: ModelProfile) -> Path:
        raise RuntimeError(
            f"an openai-compat endpoint installs its own models; pull {self.model!r} on "
            f"{self.base_url} (Ollama: `ollama pull {self.model}`)"
        )

    async def start(self, profile: ModelProfile) -> ServerInfo:
        await self.check()
        return replace(self.inspect(profile), healthy=True)

    async def health(self, info: ServerInfo) -> bool:
        try:
            await self.check()
        except RuntimeError:
            return False
        return True

    async def stop(self, info: ServerInfo) -> None:
        """Never stops a server qwenloop did not start."""
        del info

    async def check(self) -> str:
        """The served model id matching `model`, or RuntimeError saying what is wrong."""
        url = f"{self.base_url}/models"
        request = urllib.request.Request(url, headers=self._auth(self._api_key))
        try:
            body = await asyncio.to_thread(self._fetch, request)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"openai-compat endpoint {url} refused the model list: {_http_error_detail(exc)}"
            ) from exc
        except OSError as exc:
            reason = getattr(exc, "reason", None) or exc
            raise RuntimeError(
                f"openai-compat endpoint {url} is unreachable ({reason}); is the server "
                "running? (Ollama: `ollama serve`)"
            ) from exc
        served = self._served_models(body)
        if served is None:
            raise RuntimeError(
                f"openai-compat endpoint {url} did not answer with an OpenAI-compatible "
                'model list ({"data": [{"id": ...}]})'
            )
        match = self._matching(self.model, served)
        if match is None:
            listing = ", ".join(served) or "no models at all"
            raise RuntimeError(
                f"model {self.model!r} is not served by {self.base_url} (it serves: "
                f"{listing}); pull it first (Ollama: `ollama pull {self.model}`)"
            )
        return match

    def _fetch(self, request: urllib.request.Request) -> bytes:
        # The scheme was restricted to http/https in __init__, so this cannot open a file:
        # or ftp: URL, which is the whole of what B310 guards against.
        with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:  # nosec B310
            return bytes(response.read())

    @staticmethod
    def _served_models(body: bytes) -> tuple[str, ...] | None:
        try:
            parsed = json.loads(body)
        except ValueError:
            return None
        data = parsed.get("data") if isinstance(parsed, dict) else None
        if not isinstance(data, list):
            return None
        return tuple(str(item["id"]) for item in data if isinstance(item, dict) and "id" in item)

    @staticmethod
    def _matching(model: str, served: tuple[str, ...]) -> str | None:
        """Exact match, or Ollama's implicit `:latest` for an untagged name."""
        if model in served:
            return model
        if ":" not in model and f"{model}:latest" in served:
            return f"{model}:latest"
        return None


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _acquire_profile_lock(cache_dir: Path, profile: str) -> IO[str]:
    directory = cache_dir / "servers"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    stream = (directory / f"{profile}.lock").open("a+", encoding="utf-8")
    fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
    return stream


def _release_profile_lock(stream: IO[str]) -> None:
    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    stream.close()


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    """Surface the server's own error body instead of urllib's generic reason phrase."""
    try:
        body = exc.read()
    except OSError:
        return f"HTTP {exc.code}: {exc.reason}"
    message: str | None = None
    try:
        parsed = json.loads(body)
        message = parsed.get("error", {}).get("message")
    except (json.JSONDecodeError, AttributeError, TypeError):
        message = None
    if message:
        return f"HTTP {exc.code}: {message}"
    text = body.decode("utf-8", errors="replace").strip()
    return f"HTTP {exc.code}: {text or exc.reason}"


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


_CODING_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file inside the assigned worktree.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Create a file, or REPLACE an existing file's entire content, inside the "
                "assigned worktree. To change part of an existing file, use edit_file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "allow_shrink": {"type": "boolean"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "Replace exactly one occurrence of old_string with new_string in an existing "
                "file inside the assigned worktree. Use this for every change to an existing "
                "file; copy old_string exactly from read_file output."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                },
                "required": ["path", "old_string", "new_string"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": "Run a bounded command in the assigned worktree.",
            "parameters": {
                "type": "object",
                "properties": {
                    "argv": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["argv"],
                "additionalProperties": False,
            },
        },
    },
]


_EMPTY_FENCE_PATTERN = re.compile(r"```(?:json)?\s*```")
_EMPTY_TAG_PATTERN = re.compile(r"<(?:tools|tool_call)>\s*</(?:tools|tool_call)>")


def _parse_text_tool_calls(text: str) -> tuple[list[dict[str, object]], str]:
    """Recover a tool call the model wrote as text instead of a native tool_calls entry.

    Qwen2.5-Coder does this inconsistently and unpredictably: sometimes ``<tools>``/
    ``<tool_call>`` tags, sometimes a ```json fenced object, sometimes a bare JSON object
    with no wrapper at all. Rather than chase each new wrapper as a separate pattern, this
    scans for any valid JSON object with the tool call's "name"/"arguments" shape wherever
    it appears. Anything that isn't that exact shape is left as prose, so a real completion
    verdict is never mistaken for one.
    """
    calls: list[dict[str, object]] = []
    spans: list[tuple[int, int]] = []
    decoder = json.JSONDecoder()
    index = 0
    while (start := text.find("{", index)) != -1:
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        index = end
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            continue
        arguments = value.get("arguments", {})
        calls.append(
            {
                "name": value["name"],
                "arguments": arguments if isinstance(arguments, dict) else {},
            }
        )
        spans.append((start, end))
    if not calls:
        return calls, text
    remaining = text
    for start, end in reversed(spans):
        remaining = remaining[:start] + remaining[end:]
    remaining = _EMPTY_FENCE_PATTERN.sub("", remaining)
    remaining = _EMPTY_TAG_PATTERN.sub("", remaining)
    return calls, remaining.strip()
