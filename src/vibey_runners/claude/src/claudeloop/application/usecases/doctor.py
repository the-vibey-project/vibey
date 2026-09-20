# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Use case: pre-flight checks before starting a long unattended run.

Deliberately checks BEFORE a run starts, not during — an MCP OAuth prompt or a
missing `claude` binary discovered three hours into an unattended run is much
worse than the same failure at `claudeloop doctor` time. See
docs/architecture/decisions/0007-ask-user-question-denied-with-guidance.md for
why MCP OAuth specifically can never be mitigated mid-run.

With a local backend profile selected (one with ``base_url``), the Anthropic
authentication check is replaced by four that matter there instead: a token is
resolvable, the endpoint answers, every model the profile names is present, and
each tier answers a one-tool request with a real tool call.
See docs/guides/local-backend.md."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from claudeloop.application.interfaces import DoctorEnvironment
from claudeloop.domain.interfaces import BackendProfileInterface


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    passed: bool
    detail: str


def run_doctor(
    env: DoctorEnvironment,
    *,
    cwd: Path,
    backend: BackendProfileInterface | None = None,
    auth_token: str | None = None,
) -> list[DoctorCheck]:
    """``backend`` is the selected profile, or None for the default Anthropic
    backend. ``auth_token`` is its resolved token, or None when it could not be
    resolved (``auth_token_env`` names an unset variable)."""
    checks: list[DoctorCheck] = [_cli_check(env, backend)]

    if backend is not None and backend.is_local:
        checks.extend(_local_backend_checks(env, backend, auth_token))
    else:
        authed = env.is_authenticated()
        checks.append(
            DoctorCheck(
                name="authentication",
                passed=authed,
                detail="credentials present" if authed else "no credentials found",
            )
        )

    mcp_servers = env.configured_mcp_servers()
    if mcp_servers:
        checks.append(
            DoctorCheck(
                name="mcp-servers",
                passed=False,
                detail=(
                    f"{len(mcp_servers)} MCP server(s) configured ({', '.join(mcp_servers)}) — "
                    "MCP OAuth cannot complete unattended; verify these are already "
                    "authorized before starting a long run."
                ),
            )
        )
    else:
        checks.append(DoctorCheck(name="mcp-servers", passed=True, detail="none configured"))

    sdk_version = env.anthropic_sdk_version()
    checks.append(
        DoctorCheck(
            name="anthropic-sdk",
            passed=sdk_version is not None,
            detail=(
                f"anthropic {sdk_version}" if sdk_version else "anthropic package not importable"
            ),
        )
    )

    api_count = env.api_surface_method_count()
    if api_count is None:
        checks.append(
            DoctorCheck(
                name="api-surface",
                passed=False,
                detail="could not verify generated REST surface baseline",
            )
        )
    else:
        checks.append(
            DoctorCheck(
                name="api-surface",
                passed=True,
                detail=f"{api_count} SDK methods bound under `claudeloop api`",
            )
        )

    is_git_repo = (cwd / ".git").is_dir()
    checks.append(
        DoctorCheck(
            name="working-directory",
            passed=is_git_repo,
            detail=(
                f"{cwd} is a git repository"
                if is_git_repo
                else f"{cwd} is NOT a git repository — bypassing permissions here is riskier"
            ),
        )
    )

    return checks


def _cli_check(env: DoctorEnvironment, backend: BackendProfileInterface | None) -> DoctorCheck:
    """Which Claude Code CLI a run would launch, and whether it answers.

    Module-level, like ``run_doctor`` itself: this use case is still in function
    form, and turning it into a class is its own ADR-0016 convergence change, not
    something to half-do inside a feature.

    The same order the SDK resolves it in: a profile's ``cli_path``, then the CLI
    bundled inside claude-agent-sdk, then `claude` on PATH. Checking PATH first
    reported a CLI the run never launches (observed: 2.1.229 on PATH while every
    turn ran the bundled 2.1.259), and failed a machine with no global install
    that runs perfectly well (issue #121, S1b).
    """
    configured = backend.cli_path.strip() if backend is not None else ""
    if configured:
        version = env.claude_cli_version(configured)
        return DoctorCheck(
            name="claude-cli",
            passed=version is not None,
            detail=(
                f"profile cli_path {configured} ({version})"
                if version is not None
                else f"profile cli_path {configured} did not answer `--version`"
            ),
        )
    cli_path = env.find_bundled_claude_cli()
    origin = "bundled with claude-agent-sdk (what a run launches) at"
    if cli_path is None:
        cli_path = env.find_claude_cli()
        origin = "found at"
    if cli_path is None:
        return DoctorCheck(
            name="claude-cli",
            passed=False,
            detail=(
                "`claude` not found on PATH and claude-agent-sdk bundles no CLI for this "
                "platform. Install Claude Code first."
            ),
        )
    version = env.claude_cli_version(cli_path)
    return DoctorCheck(
        name="claude-cli",
        passed=version is not None,
        detail=f"{origin} {cli_path} ({version or 'version unknown'})",
    )


def _local_backend_checks(
    env: DoctorEnvironment,
    backend: BackendProfileInterface,
    auth_token: str | None,
) -> list[DoctorCheck]:
    """Token, reachability, and models for a local profile. Module-level for the
    same reason as ``_cli_check``."""
    base_url = backend.base_url.strip()
    if auth_token is None:
        auth = DoctorCheck(
            name="backend-auth",
            passed=False,
            detail=(
                f"profile {backend.name!r} reads its token from ${backend.auth_token_env}, "
                "which is unset or empty"
            ),
        )
    else:
        source = (
            f"${backend.auth_token_env}" if backend.auth_token_env else "the profile's auth_token"
        )
        auth = DoctorCheck(
            name="backend-auth",
            passed=True,
            detail=f"token from {source}; ANTHROPIC_API_KEY is blanked for this backend",
        )

    status = env.probe_backend(base_url, auth_token or "")
    reach = DoctorCheck(
        name="backend",
        passed=status.reachable,
        detail=f"profile {backend.name!r}: {status.detail}",
    )

    required = backend.required_models()
    if not status.reachable:
        models = DoctorCheck(
            name="backend-models",
            passed=False,
            detail=f"not checked — {base_url} is not answering",
        )
    elif status.models is None:
        models = DoctorCheck(
            name="backend-models",
            passed=True,
            detail=(
                f"{base_url} lists no models in a form doctor understands; "
                f"verify by hand that it serves {', '.join(required)}"
            ),
        )
    else:
        available = set(status.models)
        missing = [m for m in required if m not in available and f"{m}:latest" not in available]
        models = DoctorCheck(
            name="backend-models",
            passed=not missing,
            detail=(
                f"all present: {', '.join(required)}"
                if not missing
                else (
                    f"missing on {base_url}: {', '.join(missing)} — pull or load them "
                    f"first (for Ollama: `ollama pull {missing[0]}`)"
                )
            ),
        )
    return [auth, reach, models, _tool_check(env, backend, auth_token, ready=models.passed)]


def _tool_check(
    env: DoctorEnvironment,
    backend: BackendProfileInterface,
    auth_token: str | None,
    *,
    ready: bool,
) -> DoctorCheck:
    """Whether each model tier makes real tool calls through the backend.

    Claude Code acts only through tool calls — and delivers the completion verdict
    through one. A model that writes its tool calls out as text does nothing at
    all; observed live with qwen2.5-coder:14b on Ollama 0.34.2. Module-level for
    the same reason as ``_cli_check``.
    """
    if not ready:
        return DoctorCheck(
            name="backend-tools",
            passed=False,
            detail="not checked — the backend or its models are not ready",
        )
    base_url = backend.base_url.strip()
    tiers = backend.tier_models(low="", medium="", high="")
    problems: list[str] = []
    for model in dict.fromkeys(tiers):
        result = env.probe_tool_calling(base_url, auth_token or "", model)
        if result.supported is not True:
            problems.append(f"{model}: {result.detail}")
    if problems:
        return DoctorCheck(
            name="backend-tools",
            passed=False,
            detail=(
                "Claude Code acts only through tool calls, and these tiers do not make "
                "them — runs will change nothing: " + "; ".join(problems)
            ),
        )
    return DoctorCheck(
        name="backend-tools",
        passed=True,
        detail=f"real tool calls from {', '.join(dict.fromkeys(tiers))}",
    )


def all_passed(checks: list[DoctorCheck]) -> bool:
    return all(c.passed for c in checks)
