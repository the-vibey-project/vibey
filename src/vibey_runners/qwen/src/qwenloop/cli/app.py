# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""qwenloop command line interface."""

import asyncio
import json
import os
import platform
import shutil
import subprocess  # nosec B404
import time
import uuid
from dataclasses import asdict, replace
from pathlib import Path
from typing import Annotated

import typer
from platformdirs import user_cache_path

from qwenloop import __version__
from qwenloop.application.backend_selection import BackendSelector, Hardware
from qwenloop.application.interfaces import InferenceServer
from qwenloop.application.runner import AutonomousRunner
from qwenloop.application.storm import build_item_plans
from qwenloop.domain.config import QwenConfig
from qwenloop.domain.model import (
    EXIT_CODE_WIND_DOWN,
    Backend,
    BackendChoice,
    ModelProfile,
    RunState,
    RunStatus,
    ServerInfo,
)
from qwenloop.infrastructure.clock import SystemClock
from qwenloop.infrastructure.desktop_notifications import DesktopNotifier
from qwenloop.infrastructure.github import (
    list_open_issues,
    list_open_pull_requests,
    list_repo_names,
)
from qwenloop.infrastructure.inference import LlamaCppServer, OpenAICompatServer, VllmServer
from qwenloop.infrastructure.model_cache import ModelCache
from qwenloop.infrastructure.profiles import NVIDIA_BF16, PORTABLE, PROFILES
from qwenloop.infrastructure.run_store import FileRunStore
from qwenloop.infrastructure.settings import SettingsLoader
from qwenloop.infrastructure.tools import SandboxTools

_DEFAULT_STORM_OWNER = "adammatthewsteinberger"
_DEFAULT_STORM_AUTHOR = "Adam Matthew Steinberger"
_DEFAULT_REPOS_ROOT = Path.home() / "git"
#: What `server start`/`status` print in place of an attached endpoint's API key.
_REDACTED = "<redacted>"

# The endpoint flags every command that picks a server shares. Each falls back to its
# environment variable, then to the config file, then to the default (ADR-0018).
BackendOption = Annotated[
    Backend | None,
    typer.Option(
        "--backend",
        help="auto, llama.cpp, vllm, or openai-compat. Unset: config `backend`, else auto.",
    ),
]
BaseUrlOption = Annotated[
    str | None,
    typer.Option(
        "--base-url",
        help="OpenAI-compatible base URL to attach to, /v1 included (e.g. Ollama's "
        "http://127.0.0.1:11434/v1). Unset: $QWENLOOP_BASE_URL, else config `base_url`.",
    ),
]
ModelOption = Annotated[
    str | None,
    typer.Option(
        "--model",
        help="Model name the endpoint serves. Unset: $QWENLOOP_MODEL, else config `model`, "
        "else qwen2.5-coder:14b.",
    ),
]

app = typer.Typer(name="qwenloop", no_args_is_help=True, add_completion=False)
model_app = typer.Typer(no_args_is_help=True)
server_app = typer.Typer(no_args_is_help=True)
tool_app = typer.Typer(no_args_is_help=True)
app.add_typer(model_app, name="model")
app.add_typer(server_app, name="server")
app.add_typer(tool_app, name="tool")


def _version(value: bool) -> None:
    if value:
        typer.echo(f"qwenloop {__version__}")
        raise typer.Exit()


@app.callback()
def root(
    version: Annotated[bool, typer.Option("--version", callback=_version, is_eager=True)] = False,
) -> None:
    del version


@app.command()
def run(
    plan: Annotated[Path | None, typer.Argument()] = None,
    run_id: str = typer.Option("", "--run-id"),
    cwd: Path = typer.Option(Path("."), "--cwd"),
    preset: str = typer.Option("standard", "--preset"),
    effort: str = typer.Option("standard", "--effort"),
    backend: BackendOption = None,
    max_turns: int | None = typer.Option(
        None, "--max-turns", help="Turn limit. Unset: config `max_turns`, else 40."
    ),
    max_attempts: int = typer.Option(
        3,
        "--max-attempts",
        min=1,
        max=10,
        help="CDD repair iterations per storm item before reporting a blocker.",
    ),
    base_url: BaseUrlOption = None,
    model: ModelOption = None,
    storm: bool = typer.Option(
        False,
        "--storm",
        help="Sweep every repo's open backlog through qwenloop instead of running PLAN.",
    ),
    owner: str = typer.Option(
        _DEFAULT_STORM_OWNER, "--owner", help="GitHub owner --storm discovers repos under."
    ),
    repos_root: Path = typer.Option(
        _DEFAULT_REPOS_ROOT, "--repos-root", help="Directory --storm looks for cloned repos in."
    ),
    repo: list[str] = typer.Option(
        [], "--repo", help="Restrict --storm to this repo (repeatable); overrides discovery."
    ),
    author: str = typer.Option(
        _DEFAULT_STORM_AUTHOR, "--author", help="Author name --storm passes to vibey-gh paper/book."
    ),
    desktop_notifications: bool = typer.Option(
        True,
        "--desktop-notifications/--no-desktop-notifications",
        help="Send lifecycle desktop alerts; macOS alerts use the Ping sound.",
    ),
) -> None:
    del preset, effort
    if storm:
        if plan is not None:
            raise typer.BadParameter("pass either PLAN or --storm, not both")
        config = _load_config(backend=backend, max_turns=max_turns, base_url=base_url, model=model)
        _run_storm(
            owner=owner,
            repos_root=repos_root,
            repos=list(repo),
            author=author,
            config=config,
            desktop_notifications=desktop_notifications,
            max_attempts=max_attempts,
        )
        return
    if plan is None:
        raise typer.BadParameter("PLAN is required unless --storm is set")
    config = _load_config(backend=backend, max_turns=max_turns, base_url=base_url, model=model)
    _run_single(plan, run_id, cwd, config, desktop_notifications=desktop_notifications)


def _load_config(**overrides: object) -> QwenConfig:
    """Layer the config file, the environment, and this command's flags into one config.

    Module-level for the reason every helper in this module is: typer commands are plain
    functions, and this is the step they share. A bad file or value exits 2 naming it.
    """
    try:
        return SettingsLoader(os.environ).load(overrides)
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(f"qwenloop configuration: {exc}") from exc


def _select(config: QwenConfig) -> BackendChoice:
    """The backend `config` resolves to on this machine (see `BackendSelector`)."""
    return BackendSelector().select(
        config.backend,
        Hardware(platform.system(), _nvidia_vram()),
        vllm_installed=shutil.which("vllm") is not None,
        endpoint_configured=config.endpoint_configured,
    )


def _attach(config: QwenConfig) -> OpenAICompatServer:
    """The openai-compat endpoint `config` names, or Ollama's default address if none."""
    return OpenAICompatServer(
        config.endpoint_url,
        config.model,
        api_key=SettingsLoader(os.environ).api_key,
        timeout_seconds=config.endpoint_timeout_seconds,
        context_window=config.context_window,
    )


def _request_timeout(config: QwenConfig) -> float | None:
    """`idle_timeout_seconds` as a request timeout: 0 means wait indefinitely (#345).

    Module-level for the reason every helper here is: the typer commands share it.
    """
    return None if config.idle_timeout_seconds == 0 else float(config.idle_timeout_seconds)


def _server_for(config: QwenConfig) -> tuple[InferenceServer, ModelProfile]:
    """The server and profile a run uses. The composition step `run`, `--storm`, and
    `server start` share, so an endpoint reaches all three through one abstraction."""
    selected = _select(config).backend
    timeout = _request_timeout(config)
    if selected is Backend.OPENAI_COMPAT:
        attached = _attach(config)
        attached.request_timeout_seconds = timeout
        return attached, attached.profile
    if selected is Backend.VLLM:
        vllm = VllmServer()
        vllm.request_timeout_seconds = timeout
        return vllm, replace(NVIDIA_BF16, context_window=config.context_window)
    llama = LlamaCppServer()
    llama.request_timeout_seconds = timeout
    return llama, replace(PORTABLE, context_window=config.context_window)


def _public(info: ServerInfo) -> dict[str, object]:
    """`info` for printing. An attached endpoint's token is the operator's own API key,
    so it is never echoed; a managed server's is the per-launch one qwenloop minted."""
    data = asdict(info)
    if not info.owned and info.token:
        data["token"] = _REDACTED
    return data


def _run_single(
    plan: Path,
    run_id: str,
    cwd: Path,
    config: QwenConfig,
    *,
    desktop_notifications: bool,
) -> None:
    actual_id = run_id or str(uuid.uuid4())
    server, profile = _server_for(config)
    try:
        state = asyncio.run(
            _run_plan(
                server,
                profile,
                cwd,
                actual_id,
                plan.read_text(encoding="utf-8"),
                config.max_turns,
                startup_timeout_seconds=config.startup_timeout_seconds,
                desktop_notifications=desktop_notifications,
            )
        )
    except (OSError, RuntimeError) as exc:
        typer.echo(f"qwenloop unavailable: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if state.status is RunStatus.WINDING_DOWN:
        raise typer.Exit(code=EXIT_CODE_WIND_DOWN)
    if state.status is not RunStatus.COMPLETED:
        raise typer.Exit(code=1)


async def _run_plan(
    server: InferenceServer,
    profile: ModelProfile,
    cwd: Path,
    run_id: str,
    plan_text: str,
    max_turns: int,
    *,
    startup_timeout_seconds: int,
    desktop_notifications: bool = True,
) -> RunState:
    """Start (or, for an attached endpoint, check) the server if it is not healthy, then
    drive one AutonomousRunner run to a verdict."""
    info = server.inspect(profile)
    if info is None or not await server.health(info):
        info = await server.start(profile)
        info = await _wait_until_ready(server, info, timeout_seconds=startup_timeout_seconds)
    runner = AutonomousRunner(
        server,
        FileRunStore(cwd),
        SandboxTools(cwd),
        DesktopNotifier(enabled=desktop_notifications),
        clock=SystemClock(),
    )
    return await runner.run(
        run_id=run_id,
        plan=plan_text,
        cwd=cwd.resolve(),
        profile=profile,
        server_info=info,
        max_turns=max_turns,
    )


def _discover_storm_repos(owner: str, repos_root: Path) -> list[str]:
    """`gh`'s repos for `owner`, filtered to the ones actually cloned under `repos_root`."""
    names = list_repo_names(owner) or []
    return [name for name in names if (repos_root / name / ".git").is_dir()]


def _tracked_repository_context(repo_dir: Path) -> str:
    """Describe the actual tracked stack before a storm asks a model to edit it.

    Storm planning needs repository facts, not assumptions from an issue title. This
    helper is deliberately a fixed-argv, read-only `git ls-files` probe so the model
    sees manifests and source roots without receiving network access or a second
    implementation of repository discovery.
    """
    git_path = shutil.which("git")
    if git_path is None:
        return "- tracked-file probe unavailable: git is not installed; inspect the repository before editing."
    try:
        result = subprocess.run(  # nosec B603 - fixed git argv, read-only probe
            [git_path, "ls-files", "-z"],
            cwd=repo_dir,
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"- tracked-file probe unavailable: {exc}; inspect the repository before editing."
    if result.returncode != 0:
        detail = result.stderr.strip() or "git ls-files failed"
        return f"- tracked-file probe failed: {detail}; inspect the repository before editing."
    files = [path for path in result.stdout.split("\0") if path]
    if not files:
        return "- no tracked files were reported; do not invent a platform or source tree."
    manifests = [
        path
        for path in files
        if Path(path).name in {"pyproject.toml", "uv.lock", "package.json", "go.mod", "Cargo.toml"}
    ]
    roots = sorted({path.split("/", 1)[0] for path in files if "/" in path})
    suffixes = sorted({Path(path).suffix for path in files if Path(path).suffix})
    context = [
        f"- tracked manifests: {', '.join(manifests) or '(none)'}",
        f"- tracked top-level roots: {', '.join(roots) or '(root files only)'}",
        f"- tracked file types: {', '.join(suffixes) or '(none)'}",
    ]
    if not any(path == "go.mod" or path.endswith(".go") for path in files):
        context.append(
            "- no tracked Go manifest or Go source exists; do not invent a Go platform tree"
        )
    if any(path == "pyproject.toml" or path.endswith(".py") for path in files):
        context.append(
            "- Python is part of the tracked implementation; preserve its existing package and test layout"
        )
    return "\n".join(context)


def _run_storm(
    *,
    owner: str,
    repos_root: Path,
    repos: list[str],
    author: str,
    config: QwenConfig,
    desktop_notifications: bool,
    max_attempts: int,
) -> None:
    """Sweep each target repo one backlog item per bounded qwenloop run."""
    targets = repos or _discover_storm_repos(owner, repos_root)
    server, profile = _server_for(config)

    attempted = 0
    completed = 0
    attempted_items = 0
    completed_items = 0
    for name in targets:
        repo_dir = repos_root / name
        if not (repo_dir / ".git").is_dir():
            typer.echo(f"skip {name}: not cloned at {repo_dir}")
            continue
        plans = build_item_plans(
            repo=name,
            issues=list_open_issues(owner, name),
            pull_requests=list_open_pull_requests(owner, name),
            author=author,
            repository_context=_tracked_repository_context(repo_dir),
        )
        attempted += 1
        if not plans:
            completed += 1
            typer.echo(f"{name}\tno-open-items\t0")
            continue
        repo_success = True
        repo_failure: str | None = None
        repo_turns = 0
        for label, plan_text in plans:
            attempted_items += 1
            item_completed = False
            item_turns = 0
            for attempt in range(1, max_attempts + 1):
                attempt_plan = plan_text
                if attempt > 1:
                    attempt_plan += (
                        "\n## CDD repair iteration\n"
                        f"This is repair attempt {attempt} of {max_attempts} for the same item. "
                        "Inspect the current worktree and the prior evidence, preserve sound "
                        "changes, diagnose the failed criterion, and redirect any divergence "
                        "towards convergence. Do not abandon this item for another backlog item.\n"
                    )
                try:
                    state = asyncio.run(
                        _run_plan(
                            server,
                            profile,
                            repo_dir,
                            str(uuid.uuid4()),
                            attempt_plan,
                            config.max_turns,
                            startup_timeout_seconds=config.startup_timeout_seconds,
                            desktop_notifications=desktop_notifications,
                        )
                    )
                except (OSError, RuntimeError) as exc:
                    repo_success = False
                    repo_failure = str(exc)
                    typer.echo(f"{name} {label}\tunavailable\t{exc}")
                    break
                repo_turns += state.turns
                item_turns += state.turns
                if state.status is RunStatus.COMPLETED:
                    completed_items += 1
                    item_completed = True
                    typer.echo(
                        f"{name} {label}\tcompleted\t{state.turns} "
                        f"(attempt {attempt}/{max_attempts})"
                    )
                    break
                typer.echo(
                    f"{name} {label}\tattempt {attempt}/{max_attempts}\t"
                    f"{state.status.value}\t{state.turns}"
                )
            if repo_failure is not None:
                break
            if not item_completed:
                repo_success = False
                typer.echo(f"{name} {label}\tfailed\t{item_turns}")
                break
        if repo_failure is not None:
            typer.echo(f"{name}\tunavailable\t{repo_failure}")
        elif repo_success:
            completed += 1
            typer.echo(f"{name}\tcompleted\t{repo_turns}")
        else:
            typer.echo(f"{name}\tfailed\t{repo_turns}")
    typer.echo(
        f"qwenstorm complete: {completed}/{attempted} repos completed "
        f"({completed_items}/{attempted_items} items completed)"
    )


@model_app.command("list")
def model_list() -> None:
    for profile in PROFILES.values():
        typer.echo(f"{profile.name}\t{profile.backend.value}\t{profile.quantization}")


@model_app.command()
def inspect(profile: str = PORTABLE.name) -> None:
    selected = PROFILES[profile]
    typer.echo(json.dumps(asdict(selected), default=str, indent=2))


@model_app.command()
def verify(profile: str = PORTABLE.name) -> None:
    selected = PROFILES[profile]
    try:
        typer.echo(str(ModelCache().verify(selected)))
    except (FileNotFoundError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@model_app.command()
def install(profile: str = typer.Option("portable", "--profile")) -> None:
    selected = PORTABLE if profile == "portable" else NVIDIA_BF16
    if selected.filename is None:
        typer.echo(
            "Install the pinned BF16 snapshot through vLLM/Hugging Face, then run model verify."
        )
        return
    typer.echo(f"Installing explicit profile {selected.name}...")
    try:
        typer.echo(str(ModelCache().install(selected)))
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@model_app.command()
def remove(profile: str, yes: bool = typer.Option(False, "--yes")) -> None:
    if not yes:
        raise typer.BadParameter("pass --yes to remove a model profile")
    target = user_cache_path("qwenloop") / "models" / profile
    if target.exists():
        raise typer.BadParameter(
            f"recoverable deletion is required; move this directory to Trash: {target}"
        )


@app.command()
def doctor(
    backend: BackendOption = None,
    base_url: BaseUrlOption = None,
    model: ModelOption = None,
) -> None:
    """Exit 0 only when a run could start. With an endpoint configured that means it
    answers and serves the model; otherwise that llama-server or vllm is installed."""
    config = _load_config(backend=backend, base_url=base_url, model=model)
    choice = _select(config)
    if choice.backend is Backend.OPENAI_COMPAT:
        _doctor_endpoint(_attach(config), choice)
        return
    portable = shutil.which("llama-server") is not None
    nvidia = shutil.which("vllm") is not None
    typer.echo(f"llama-server: {'ok' if portable else 'missing'}")
    typer.echo(f"vllm: {'ok' if nvidia else 'missing'}")
    typer.echo("Models are never downloaded by doctor; run qwenloop model install explicitly.")
    if not portable and not nvidia:
        raise typer.Exit(code=1)


def _doctor_endpoint(server: OpenAICompatServer, choice: BackendChoice) -> None:
    """Prove an attached endpoint is reachable and serves the model, or fail naming which."""
    typer.echo(f"backend: {choice.backend.value} ({choice.reason})")
    typer.echo(f"endpoint: {server.base_url}")
    try:
        served = asyncio.run(server.check())
    except RuntimeError as exc:
        typer.echo(f"model: {server.model} unavailable")
        typer.echo(f"qwenloop doctor: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"model: {served} ok")
    typer.echo("Models are never downloaded by doctor; the endpoint serves its own.")


@app.command()
def whoami() -> None:
    typer.echo(json.dumps({"identity": "local", "provider_dollars": 0, "owner": os.getuid()}))


@app.command()
def usage(cwd: Path = Path(".")) -> None:
    runs = cwd / ".qwenloop" / "runs"
    typer.echo(
        json.dumps(
            {"runs": len(list(runs.glob("*"))) if runs.exists() else 0, "provider_dollars": 0}
        )
    )


def _control(run_id: str, kind: str, cwd: Path) -> None:
    inbox = cwd / ".qwenloop" / "runs" / run_id / "control" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    target = inbox / f"{uuid.uuid4()}.json"
    target.write_text(json.dumps({"type": kind}) + "\n", encoding="utf-8")


@app.command()
def stop(run_id: str, cwd: Path = Path(".")) -> None:
    _control(run_id, "stop", cwd)


@app.command("wind-down")
def wind_down(run_id: str, cwd: Path = Path(".")) -> None:
    _control(run_id, "wind_down", cwd)


@app.command()
def prompt(run_id: str, text: str, cwd: Path = Path(".")) -> None:
    inbox = cwd / ".qwenloop" / "runs" / run_id / "control" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / f"{uuid.uuid4()}.json").write_text(
        json.dumps({"type": "prompt", "text": text}) + "\n", encoding="utf-8"
    )


def _local_equivalent(name: str):  # type: ignore[no-untyped-def]
    def command() -> None:
        typer.echo(f"{name}: local qwenloop equivalent; see qwenloop status and run artifacts")

    command.__name__ = name.replace("-", "_")
    return command


for _name in (
    "resume",
    "status",
    "logs",
    "watch",
    "snapshot",
    "reset",
    "runs",
    "sessions",
    "threads",
    "agents",
    "savepoints",
    "unwind",
    "capacity",
    "models",
    "effort",
    "preset",
    "permission-mode",
    "approval",
    "sandbox",
    "cwd",
    "slash",
    "hooks",
    "config",
    "attach",
    "unattach",
    "folder",
    "skill",
    "plugin",
    "connector",
    "memory",
    "artifact",
    "github",
    "research",
    "web-search",
    "chat",
    "response",
    "voice",
    "speak",
    "cloud",
    "api",
):
    app.command(_name)(_local_equivalent(_name))


@server_app.command("status")
def server_status(
    backend: BackendOption = None,
    base_url: BaseUrlOption = None,
    model: ModelOption = None,
) -> None:
    config = _load_config(backend=backend, base_url=base_url, model=model)
    if _select(config).backend is Backend.OPENAI_COMPAT:
        attached = _attach(config)
        info = attached.inspect(attached.profile)
        healthy = asyncio.run(attached.health(info))
        typer.echo(json.dumps(_public(replace(info, healthy=healthy)), default=str))
        return
    managed = LlamaCppServer().inspect(PORTABLE) or VllmServer().inspect(NVIDIA_BF16)
    typer.echo(json.dumps(_public(managed) if managed else {"running": False}, default=str))


@server_app.command("start")
def server_start(
    backend: BackendOption = None,
    base_url: BaseUrlOption = None,
    model: ModelOption = None,
) -> None:
    """Start the managed server, or check that the configured endpoint is ready."""
    config = _load_config(backend=backend, base_url=base_url, model=model)
    server, profile = _server_for(config)

    async def execute() -> None:
        info = await server.start(profile)
        ready = await _wait_until_ready(
            server, info, timeout_seconds=config.startup_timeout_seconds
        )
        typer.echo(json.dumps(_public(ready), default=str))

    try:
        asyncio.run(execute())
    except (OSError, RuntimeError, TimeoutError) as exc:
        typer.echo(f"qwenloop server unavailable: {exc}", err=True)
        raise typer.Exit(code=1) from exc


@server_app.command("stop")
def server_stop() -> None:
    async def execute() -> bool:
        stopped = False
        for server, profile in (
            (LlamaCppServer(), PORTABLE),
            (VllmServer(), NVIDIA_BF16),
        ):
            info = server.inspect(profile)
            if info is not None:
                await server.stop(info)
                stopped = True
        return stopped

    typer.echo("stopped" if asyncio.run(execute()) else "not running")


@tool_app.command("approve")
def tool_approve(name: str) -> None:
    typer.echo(f"approved for the active run: {name}")


@tool_app.command("deny")
def tool_deny(name: str) -> None:
    typer.echo(f"denied for the active run: {name}")


def _nvidia_vram() -> int:
    nvidia_smi = shutil.which("nvidia-smi")
    if platform.system() != "Linux" or nvidia_smi is None:
        return 0
    try:
        # The executable is resolved to an absolute path and all arguments are fixed.
        result = subprocess.run(  # nosec B603
            [
                nvidia_smi,
                "--query-gpu=memory.free",
                "--format=csv,noheader,nounits",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        free_mib = [int(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0
    return max(free_mib, default=0) * 1024 * 1024


async def _wait_until_ready(
    server: InferenceServer, info: ServerInfo, *, timeout_seconds: int
) -> ServerInfo:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if await server.health(info):
            return info
        if info.pid is not None:
            try:
                os.kill(info.pid, 0)
            except ProcessLookupError as exc:
                raise RuntimeError("inference server exited during startup") from exc
        await asyncio.sleep(0.25)
    raise TimeoutError(f"inference server did not become ready within {timeout_seconds}s")


def main() -> None:
    app()
