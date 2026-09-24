# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure model, capacity, and run state."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

EXIT_CODE_WIND_DOWN = 75
DONE_MARKER = "QWENLOOP_TASK_FULLY_COMPLETE"
#: Every tool a run can call, in the order the model is told them. The one list the tool
#: schema, the dispatcher and the prompts are all checked against, so a tool cannot be
#: advertised without being callable or callable without being advertised. `search`,
#: `find` and `open_file` exist because gpt-oss:20b called them 431 times across 82 storm
#: runs while the dispatcher answered "unknown tool" (18% of every tool call it made).
CODING_TOOL_NAMES: tuple[str, ...] = (
    "read_file",
    "write_file",
    "edit_file",
    "shell",
    "search",
    "find",
    "open_file",
)


class Backend(StrEnum):
    AUTO = "auto"
    LLAMA_CPP = "llama.cpp"
    VLLM = "vllm"
    # Attach to an OpenAI-compatible server someone else runs (Ollama is the primary
    # target) instead of spawning llama-server or vllm. See ADR 0003.
    OPENAI_COMPAT = "openai-compat"


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WINDING_DOWN = "winding_down"
    COMPLETED = "completed"
    FAILED = "failed"


class CapacityKind(StrEnum):
    AVAILABLE = "available"
    LOCAL_BUSY = "local_busy"
    CONFIGURATION = "configuration"


@dataclass(frozen=True, slots=True)
class ModelProfile:
    name: str
    backend: Backend
    repository: str
    revision: str
    filename: str | None
    sha256: str | None
    size: int | None
    quantization: str
    context_window: int = 32_768


@dataclass(frozen=True, slots=True)
class ServerInfo:
    backend: Backend
    profile: str
    endpoint: str
    owned: bool
    healthy: bool
    pid: int | None = None
    # Kept out of repr: for an attached endpoint this is the operator's own API key.
    token: str = field(default="", repr=False)
    # The model name every request sends. Explicit rather than derived from `profile`,
    # because an attached endpoint names its models its own way (Ollama: `qwen2.5-coder:14b`).
    # Empty means "send the profile name", which is what a managed server serves.
    model: str = ""
    # What a managed server was started with, its API key already redacted, and where its
    # own output goes -- so a run records the settings it measured (#382). Both stay empty
    # for an attached endpoint, which qwenloop never starts.
    argv: tuple[str, ...] = ()
    log_path: str = ""


@dataclass(frozen=True, slots=True)
class Hardware:
    system: str
    nvidia_vram_bytes: int = 0


@dataclass(frozen=True, slots=True)
class BackendChoice:
    backend: Backend
    reason: str


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: str
    content: str
    tool_calls: tuple[dict[str, Any], ...] = ()
    tool_call_id: str | None = None


@dataclass(frozen=True, slots=True)
class RepoItem:
    """One open issue or pull request, as reported by `gh`."""

    number: int
    title: str
    body: str


@dataclass(frozen=True, slots=True)
class ChatChunk:
    text: str = ""
    tool_call: dict[str, Any] | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    # llama-server's own per-request timings (prompt_n, cache_n, prompt_ms, predicted_n,
    # predicted_ms, predicted_per_second); None when the server sent none.
    timings: Mapping[str, float] | None = None
    # Why the model stopped (`stop`, `length`, `tool_calls`, ...); None when not reported.
    finish_reason: str | None = None
    # The reply's separate reasoning text (gpt-oss on Ollama sends one); None when the
    # server sent none. Model output: the runner records a capped excerpt of it as data and
    # never feeds it back to the model. Kept out of repr, which could otherwise be huge.
    reasoning: str | None = field(default=None, repr=False)


class ToolCallParseError(RuntimeError):
    """The model server could not parse the model's reply as a tool call (#386).

    Ollama answers HTTP 500 "error parsing tool call" when a model writes prose where a
    tool call was due. That fails one turn, not the run: the runner asks for a valid tool
    call and retries. It stays a RuntimeError, so a caller that does not retry sees
    exactly the error it saw before.
    """

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(slots=True)
class RunState:
    run_id: str
    status: RunStatus = RunStatus.CREATED
    turns: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    transcript: list[ChatMessage] = field(default_factory=list)


def terminal_status(capacity: CapacityKind, completion_claimed: bool) -> RunStatus:
    """Capacity rejection always outranks a completion claim."""
    if capacity is not CapacityKind.AVAILABLE:
        return RunStatus.FAILED
    return RunStatus.COMPLETED if completion_claimed else RunStatus.RUNNING
