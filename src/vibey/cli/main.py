# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
# Armed FIRST, before typer and the rest of the tree are imported. Kubernetes deletes a
# pod by sending SIGTERM and waiting, and Linux discards a signal sent to PID 1 while its
# disposition is still SIG_DFL -- it is not queued for later. Everything imported below
# this line is time during which a scale-in would be thrown away, so the latch goes above
# it. See vibey.cli.early_signals.
from vibey.cli.early_signals import SIGTERM_LATCH

SIGTERM_LATCH.arm()

import asyncio
import json
import os
import signal
import subprocess  # nosec B404 - fixed argv, never shell=True
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, cast
from uuid import UUID, uuid4

import typer

from vibey import __version__
from vibey.application.design_acceptance import DesignAcceptanceService
from vibey.application.dto import GateAnswerOutcome, ProjectRecord
from vibey.application.project_kickoff import enqueue_design_interview
from vibey.application.visual_acceptance import VisualAcceptanceService
from vibey.bootstrap import (
    DesignProvider,
    SystemClock,
    VisualInventoryProducer,
    build_app,
    build_design_worker,
    build_visual_worker,
)
from vibey.cli.budget import budget_app
from vibey.cli.errors import EXIT_USAGE, guard
from vibey.cli.gates import GATES
from vibey.cli.ledger_publication import ledger_export, ledger_site
from vibey.cli.ledger_search import PRESENTER, ledger_search
from vibey.cli.loops import LOOPS
from vibey.cli.projects import PROJECTS
from vibey.cli.queue import queue_app
from vibey.domain.engine import EngineId
from vibey.domain.errors import (
    InvalidAnswer,
    UnknownProject,
    UnknownProvider,
    VibeyError,
    WrongPhase,
)
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, LedgerEventKind
from vibey.domain.ledger_query import EVENT_KINDS, InvalidLedgerQuery
from vibey.domain.phase import Phase, StoredPhase, VisualDecision
from vibey.domain.spec import (
    AcceptanceCriterion,
    Constraint,
    ConstraintKind,
    DesignSpec,
    NonFunctionalRequirement,
)
from vibey.domain.verbosity import resolve_log_plan
from vibey.infrastructure.config_loader import load_runtime_config_from_path
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.claudeloop_design import ClaudeLoopDesignProvider
from vibey.infrastructure.engines.claudeloop_process import (
    AsyncSubprocessExecutor,
    ClaudeLoopProcess,
    SpendRecorder,
)
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.engines.local_engines import LocalEngineSettings
from vibey.infrastructure.engines.ollama_chat import (
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_MODEL_ENV,
    OLLAMA_URL_ENV,
    OllamaChatClient,
)
from vibey.infrastructure.engines.qwenloop_design import QwenloopDesignProvider
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider
from vibey.infrastructure.logging import configure_logging
from vibey.infrastructure.postgres import POSTGRES_MIN_MAJOR, PostgresLocalService, PostgresStatus

app = typer.Typer(name="vibey", no_args_is_help=True)
design_app = typer.Typer(name="design", invoke_without_command=True)
app.add_typer(design_app, name="design")
visual_app = typer.Typer(name="visual", invoke_without_command=True)
app.add_typer(visual_app, name="visual")
deploy_app = typer.Typer(name="deploy", invoke_without_command=True)
app.add_typer(deploy_app, name="deploy")
ledger_app = typer.Typer(name="ledger", invoke_without_command=True)
app.add_typer(ledger_app, name="ledger")
ledger_app.command("search")(ledger_search)
ledger_app.command("export")(ledger_export)
ledger_app.command("site")(ledger_site)
app.add_typer(queue_app, name="queue")
app.add_typer(budget_app, name="budget")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"vibey {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_version_callback, is_eager=True),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="More detail: -v debug, -vv also third-party libraries, -vvv full payloads.",
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Warnings and errors only."),
    log_level: str | None = typer.Option(
        None, "--log-level", help="DEBUG, INFO, WARNING, ERROR or CRITICAL. Overrides -v."
    ),
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Also write redacted JSON lines to this file."),
    ] = None,
) -> None:
    """vibey: a queue-based, six-phase conductor for autonomous software delivery."""
    del version
    try:
        plan = resolve_log_plan(verbose=verbose, quiet=quiet, log_level=log_level)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    configure_logging(plan, log_file=log_file)


async def _enqueue_design(project_id: UUID, *, priority: bool = False) -> str:
    # The transition-and-enqueue logic lives in the application layer so the
    # Kubernetes operator starts projects through the same path this does.
    async with build_app() as resources:
        job_id = await enqueue_design_interview(
            projects=resources.projects,
            jobs=resources.jobs,
            project_id=project_id,
            priority=resources.queue_priority if priority else None,
        )
        return str(job_id)


def _build_spend_recorder(
    ledger: PostgresLedgerRepository, project_id: UUID, cycle: int, phase: Phase
) -> SpendRecorder:
    """Record a live run's spend where the budget brake can see it.

    LedgerBudgetSource sums TurnCompleted and BudgetSpent. The BUILD path
    gets TurnCompleted for free because LoopProcessAdapter tails the
    engine's events.jsonl into the ledger. The DESIGN path runs claudeloop
    directly and read that same file only for the last assistant message,
    so its spend reached nothing -- the brake computed $0 for DESIGN and
    could never trip, whatever cap the project carried. BudgetSpent with
    explicit dollars/turns is the vendor-neutral shape the brake already
    counts, so this needs no new event kind and no new counting logic.
    """
    from vibey.domain.ledger import Provenance, digest_event
    from vibey.infrastructure.engines.tailer import LedgerEventDraft

    async def record(turns: int, dollars: float) -> None:
        payload: dict[str, object] = {"turns": turns, "dollars": dollars}
        await ledger.append(
            LedgerEventDraft(
                project_id=project_id,
                cycle=cycle,
                phase=phase,
                kind=EventKind.BUDGET_SPENT,
                engine_id=EngineId.CLAUDELOOP,
                job_id=None,
                causation_id=None,
                correlation_id=uuid4(),
                provenance=Provenance.TRUSTED,
                produced_at=datetime.now(UTC),
                payload=payload,
                digest=digest_event(payload),
            )
        )

    return record


@app.command("new")
def new_project(
    name: str,
    repo: Annotated[Path, typer.Option("--repo")] = Path("."),
    max_cycles: Annotated[int, typer.Option("--max-cycles", min=1)] = 10,
    max_cycle_dollars: Annotated[
        float | None,
        typer.Option(
            "--max-cycle-dollars",
            min=0.01,
            help="Cap engine spend per cycle; exceeding it parks a "
            "budget_exhausted gate instead of starting more sessions",
        ),
    ] = None,
    max_cycle_turns: Annotated[
        int | None,
        typer.Option("--max-cycle-turns", min=1, help="Cap engine turns per cycle"),
    ] = None,
    skills_context_mode: Annotated[
        str,
        typer.Option(
            "--skills-context-mode",
            help="Skills retrieval mode: off, shadow (measure only), or inject",
        ),
    ] = "off",
    skills_context_budget: Annotated[
        int,
        typer.Option("--skills-context-budget", min=1_000, max=32_000),
    ] = 6_000,
) -> None:
    """Create a project and enqueue its first DESIGN interview."""

    async def create() -> tuple[str, str]:
        if skills_context_mode not in {"off", "shadow", "inject"}:
            raise typer.BadParameter(
                "must be off, shadow, or inject", param_hint="--skills-context-mode"
            )
        config: dict[str, object] = {"project": {"name": name, "repo": str(repo)}}
        try:
            config.update(load_runtime_config_from_path(repo.resolve() / "vibey.toml"))
        except ValueError as exc:
            # A forbidden [gates] or [engine_environment] entry is refused here, before
            # a project exists that the worker would then refuse to build.
            typer.echo(f"vibey.toml: {exc}")
            raise typer.Exit(EXIT_USAGE) from exc
        if max_cycle_dollars is not None:
            config["max_cycle_dollars"] = max_cycle_dollars
        if max_cycle_turns is not None:
            config["max_cycle_turns"] = max_cycle_turns
        if skills_context_mode != "off":
            config["skills_context"] = {
                "mode": skills_context_mode,
                "budget": skills_context_budget,
            }
        async with build_app() as resources:
            project = await resources.projects.create(
                name,
                repo,
                max_cycles=max_cycles,
                config=config,
            )
        return str(project.project_id), await _enqueue_design(project.project_id)

    with guard():
        project_id, job_id = asyncio.run(create())
    typer.echo(f"project {project_id}\ndesign job {job_id}")


@app.command("projects")
def list_projects(
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print a JSON array instead: one object per project, newest first.",
        ),
    ] = False,
) -> None:
    """List every project, newest first: its id, phase, cycle, and open gates."""
    with guard():
        asyncio.run(PROJECTS.run(as_json=as_json))


@app.command("gates")
def list_gates(
    project_id: Annotated[
        UUID | None,
        typer.Argument(help="Only this project's gates; defaults to every project's."),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help='Print JSON instead: {"gates": [...]}, oldest first.',
        ),
    ] = False,
) -> None:
    """List open gates, oldest first, each with the `vibey answer` command that answers it."""
    with guard():
        asyncio.run(GATES.run(project_id, as_json=as_json))


@design_app.callback(invoke_without_command=True)
def design(ctx: typer.Context) -> None:
    """Enqueue or resume the project's DESIGN interview, or manage it via subcommands."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@design_app.command("resume")
def resume_design(
    project_id: UUID,
    priority: Annotated[
        bool,
        typer.Option(
            "--priority",
            help="Enqueue the interview bumped: it runs next, after whatever is "
            "running (`vibey queue bump`, ADR-0054).",
        ),
    ] = False,
) -> None:
    """Enqueue or resume the project's DESIGN interview."""
    with guard():
        typer.echo(f"design job {asyncio.run(_enqueue_design(project_id, priority=priority))}")


def _local_engines_from_toml(root: Path | None = None) -> LocalEngineSettings:
    """The local-engine settings `vibey doctor` reads: `./vibey.toml` under the environment.

    The same resolver the worker asks (ADR-0038), fed the file instead of the stored
    project record, so the health check and the dispatcher agree about which engines
    exist. They disagreed before: the worker ran qwenloop while `doctor` could not list
    it. Module-level, like the typer commands that call it, because it is the CLI's
    own reading of the working directory -- nothing else reads config from there.
    """
    return LocalEngineSettings.from_toml((root or Path.cwd()) / "vibey.toml", environ=os.environ)


async def _passwordless_reach_section() -> bool:
    """`vibey doctor`'s password-less-access line for the app DSN's database: FAIL, PASS
    or UNKNOWN (SECURITY.md §5). False on FAIL: sub-doctrine 10.j (ADR-0061) makes
    scram-sha-256 the only way in, so a password-less login is a failure, not a choice.

    A module-level function because it is `doctor`'s own step, shared by nothing else,
    like `_postgres_status_line` beside it; the check itself is
    `PasswordlessReachProbe`.
    """
    from vibey.infrastructure.db.passwordless_reach import PasswordlessReachProbe, ReachVerdict

    name = "db-passwordless"
    dsn = os.environ.get("VIBEY_PG_URL", "").strip()
    if not dsn:
        typer.echo(f"UNKNOWN {name:<20} VIBEY_PG_URL is not set; nothing to check")
        return True
    finding = await PasswordlessReachProbe().probe(dsn)
    typer.echo(f"{finding.verdict.mark} {name:<20} {finding.detail}")
    return finding.verdict is not ReachVerdict.FAIL


def _postgres_status_line(status: PostgresStatus) -> str:
    """Render the local database check in the same compact style as engine doctor."""
    if not status.installed:
        state = "NOT INSTALLED"
    elif not status.supported:
        state = "UNSUPPORTED"
    elif not status.running:
        state = "NOT READY"
    else:
        state = "READY"
    version = f"v{status.version}" if status.version is not None else "v?"
    return f"postgresql      {state:<14} {version:<8} {status.detail}"


def _parse_question_answers(items: tuple[str, ...]) -> dict[str, object]:
    answers: dict[str, str] = {}
    for item in items:
        question_id, separator, answer = item.partition("=")
        if not separator or not question_id.strip():
            raise InvalidAnswer("each answer must use QUESTION_ID=ANSWER")
        answers[question_id.strip()] = answer
    return {"answers": answers}


@app.command("answer")
def answer(
    gate_id: UUID,
    answers: Annotated[list[str] | None, typer.Argument()] = None,
    choice: Annotated[
        str | None,
        typer.Option("--choice", help='Answer a choice gate: sends {"choice": VALUE}'),
    ] = None,
    verdict: Annotated[
        str | None,
        typer.Option("--verdict", help='Answer a verdict gate: sends {"verdict": VALUE}'),
    ] = None,
    raw: Annotated[
        str | None,
        typer.Option("--raw", help="Answer with an arbitrary JSON object"),
    ] = None,
    defaults: Annotated[
        bool,
        typer.Option(
            "--defaults",
            help="Interview gates: accept every question's default "
            "(combinable with positional pairs, which win)",
        ),
    ] = False,
    by: Annotated[
        str | None,
        typer.Option(
            "--by",
            help="The name this answer is recorded under, for a tool that runs the command "
            "(the VS Code extension says vibey-vscode). Defaults to the account running it. "
            "A label for the record, not a permission: the account is recorded beside it.",
        ),
    ] = None,
    request_id: Annotated[
        str | None,
        typer.Option(
            "--request-id",
            help="Name this request so a retry is safe: the same id with the same answer "
            "is a no-op once it has landed. Without one, every run is a new request, and "
            "a gate already answered refuses it.",
        ),
    ] = None,
) -> None:
    """Answer a parked gate: QUESTION_ID=ANSWER pairs, --choice, --verdict, or --raw.

    Interview gates take the positional pairs or --defaults (question keys
    are model-minted and vary per run; --defaults needs none); review gates
    take --verdict (accept/changes/cancel/approve/request_changes);
    deployment and triage gates take --choice; --raw covers any other shape.

    A gate is answered once. A second answer is refused (exit 3) and the
    first stands; `--request-id` makes a retry of the same answer a no-op.
    """
    modes = [m for m in (answers, choice, verdict, raw) if m]
    if defaults and (choice or verdict or raw):
        typer.echo("--defaults only combines with positional QUESTION_ID=ANSWER pairs")
        raise typer.Exit(2)
    if len(modes) != 1 and not defaults:
        typer.echo("provide exactly one of: QUESTION_ID=ANSWER pairs, --choice, --verdict, --raw")
        raise typer.Exit(2)

    payload: dict[str, object]
    if choice is not None:
        payload = {"choice": choice}
    elif verdict is not None:
        payload = {"verdict": verdict}
    elif raw is not None:
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            typer.echo(f"--raw must be valid JSON: {exc}")
            raise typer.Exit(2) from exc
        if not isinstance(decoded, dict):
            typer.echo("--raw must be a JSON object")
            raise typer.Exit(2)
        payload = decoded
    else:
        payload = _parse_question_answers(tuple(answers or ()))
        if defaults:
            payload["accept_defaults"] = True

    async def submit() -> GateAnswerOutcome:
        async with build_app() as resources:
            return await resources.gate_answers.answer(
                gate_id, payload, by=by, request_id=request_id
            )

    with guard():
        outcome = asyncio.run(submit())
    if outcome.replayed:
        typer.echo(f"already answered {gate_id} by this request; nothing changed")
    else:
        typer.echo(f"answered {gate_id} as {outcome.record.answered_by}")


# One sentence for both commands' --ollama-model, so `work` and `worker` cannot drift.
_OLLAMA_MODEL_HELP = (
    "Local model for --provider qwenloop; ignored by the other providers. Default: "
    f"${OLLAMA_MODEL_ENV}, else {DEFAULT_OLLAMA_MODEL}. The server is ${OLLAMA_URL_ENV}."
)
_PROVIDERS = ("scripted", "claudeloop", "qwenloop")
# Built from _PROVIDERS so the message both commands print cannot fall behind the list.
_UNKNOWN_PROVIDER = (
    "provider must be "
    + ", ".join(f"'{name}'" for name in _PROVIDERS[:-1])
    + f", or '{_PROVIDERS[-1]}'"
)
# The same for --provider: its default is the one decision both commands must share.
_PROVIDER_HELP = (
    "DESIGN/DECOMPOSE provider: scripted, claudeloop, or qwenloop (the sovereign one, on "
    "Ollama). Default: qwenloop -- the sovereign default is always on (sub-doctrine 8.b). "
    "An explicit value always wins."
)


def _resolve_provider(explicit: str | None) -> str:
    """The provider to run: the operator's explicit choice, else the sovereign default.

    Sub-doctrine 8.b keeps the sovereign default always on, never needing declaration, so
    with no `--provider` DESIGN and DECOMPOSE run on qwenloop (#322). Before, they fell
    back to the scripted fake unless a local engine was switched on. Paid (`claudeloop`)
    is always a stated choice. Module-level, like the typer commands that share it, so
    `work` and `worker` cannot disagree.
    """
    return explicit if explicit is not None else "qwenloop"


async def _work_once(
    project_id: UUID,
    provider_opt: str | None,
    max_turns: int,
    max_dollars: float,
    ollama_model: str | None = None,
) -> bool:
    async with build_app() as resources:
        project = await resources.projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        if not isinstance(project.phase, Phase):
            raise WrongPhase(f"project phase {project.phase.value!r} is unknown; upgrade vibey")
        owner = f"cli-{os.getpid()}"
        if project.phase is Phase.VISUAL_DESIGN:
            visual_provider: VisualInventoryProducer
            # No sovereign visual producer exists, so the sovereign default stops at
            # DESIGN and DECOMPOSE: an unstated provider here is still the scripted one.
            if provider_opt in (None, "scripted"):
                visual_provider = ScriptedVisualProvider()
            else:
                raise WrongPhase(
                    "no live VisualInventoryProducer is implemented yet; use --provider scripted"
                )
            worker = build_visual_worker(
                resources=resources,
                provider=visual_provider,
                owner=owner,
                project=project,
            )
            return await worker.run_once(project_id)

        provider = _resolve_provider(provider_opt)
        design_provider: DesignProvider
        if provider == "scripted":
            design_provider = ScriptedDesignProvider()
        elif provider == "claudeloop":
            claude_process = ClaudeLoopProcess(
                executor=AsyncSubprocessExecutor(
                    EngineEnvironmentPolicy.from_config(project.config).environment(CLAUDELOOP)
                ),
                max_turns=max_turns,
                max_dollars=max_dollars,
                spend_recorder=_build_spend_recorder(
                    resources.ledger, project.project_id, project.cycle, project.phase
                ),
            )
            design_provider = ClaudeLoopDesignProvider(
                process=claude_process,
                worktree_path=project.repo_path,
            )
        elif provider == "qwenloop":
            # Doctrine 8.a: the sovereign path is the preferred way to run, so it has to
            # be selectable here rather than reachable only through a paid engine.
            # VIBEY_OLLAMA_URL / VIBEY_OLLAMA_MODEL (or --ollama-model) choose the local
            # server and model. VIBEY_EVIDENCE_DIR is where the operator leaves reading
            # for the research stage; without it research parks a `research_evidence`
            # gate rather than inventing a source. `work` runs DESIGN only, so it has no
            # decomposer to choose -- `worker` does.
            design_provider = QwenloopDesignProvider.from_environment(
                os.environ, chat=OllamaChatClient.from_environment(os.environ, model=ollama_model)
            )
        else:
            raise UnknownProvider(_UNKNOWN_PROVIDER)
        worker = build_design_worker(
            resources=resources,
            project=project,
            provider=design_provider,
            owner=owner,
        )
        return await worker.run_once(project_id)


@app.command("work")
def work_once(
    project_id: UUID,
    provider: Annotated[str | None, typer.Option("--provider", help=_PROVIDER_HELP)] = None,
    max_turns: Annotated[int, typer.Option("--max-turns", min=1)] = 1,
    max_dollars: Annotated[float, typer.Option("--max-dollars", min=0.01, max=10)] = 0.25,
    ollama_model: Annotated[
        str | None,
        typer.Option("--ollama-model", help=_OLLAMA_MODEL_HELP),
    ] = None,
) -> None:
    """Process one ready DESIGN job; live ClaudeLoop use is explicit and capped."""
    with guard():
        processed = asyncio.run(
            _work_once(project_id, provider, max_turns, max_dollars, ollama_model)
        )
    typer.echo("processed one job" if processed else "no ready job")


def _load_spec(path: Path) -> DesignSpec:
    raw = json.loads(path.read_text())
    return DesignSpec(
        objective=str(raw["objective"]),
        constraints=tuple(
            Constraint(str(item["text"]), ConstraintKind(str(item["kind"])))
            for item in raw.get("constraints", [])
        ),
        non_goals=tuple(str(item) for item in raw.get("non_goals", [])),
        criteria=tuple(AcceptanceCriterion(**item) for item in raw["criteria"]),
        nfrs=tuple(NonFunctionalRequirement(**item) for item in raw.get("nfrs", [])),
        walking_skeleton=str(raw["walking_skeleton"]),
    )


@design_app.command("accept")
def accept_design(
    project_id: UUID,
    spec_json: Annotated[Path | None, typer.Option("--spec-json")] = None,
    visual: Annotated[
        bool,
        typer.Option(
            "--visual/--no-visual",
            help="Opt in to the VISUAL_DESIGN interstitial instead of going straight to BUILD.",
        ),
    ] = False,
) -> None:
    """Accept the synthesized spec, optionally importing JSON first.

    The visual-design choice is explicit and never defaults to yes: pass
    --visual to enter VISUAL_DESIGN, or omit it (or pass --no-visual) to
    decline and go straight to BUILD.
    """

    async def accept() -> tuple[Path, StoredPhase]:
        async with build_app() as resources:
            project = await resources.projects.get(project_id)
            if project is None:
                raise UnknownProject(f"unknown project {project_id}")
            if spec_json is not None:
                await resources.design_specs.save(project_id, project.cycle, _load_spec(spec_json))
            accepted = await DesignAcceptanceService(
                projects=resources.projects,
                ledger=resources.design_ledger,
                specs=resources.design_specs,
                jobs=resources.jobs,
                clock=SystemClock(),
            ).accept(
                project_id,
                visual_choice=VisualDecision.OPTED_IN if visual else VisualDecision.DECLINED,
            )
            return accepted.repo_path, accepted.phase

    with guard():
        repo_path, phase = asyncio.run(accept())
    typer.echo(
        f"accepted design for {project_id}; entered {phase.value}; context under {repo_path}"
    )


@visual_app.callback(invoke_without_command=True)
def visual(ctx: typer.Context) -> None:
    """Settle the VISUAL_DESIGN interstitial via subcommands."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


async def _settle_visual(project_id: UUID, decision: VisualDecision) -> StoredPhase:
    async with build_app() as resources:
        settled = await VisualAcceptanceService(
            projects=resources.projects,
            ledger=resources.design_ledger,
            inventories=resources.visual_inventories,
            jobs=resources.jobs,
            clock=SystemClock(),
        ).settle(project_id, decision=decision)
        return settled.phase


@visual_app.command("accept")
def accept_visual(project_id: UUID) -> None:
    """Accept the reviewed visual plan and enter BUILD."""
    with guard():
        phase = asyncio.run(_settle_visual(project_id, VisualDecision.ACCEPTED))
    typer.echo(f"accepted visual design for {project_id}; entered {phase.value}")


@visual_app.command("waive")
def waive_visual(project_id: UUID) -> None:
    """Explicitly waive the visual plan (inventory must still be complete) and enter BUILD."""
    with guard():
        phase = asyncio.run(_settle_visual(project_id, VisualDecision.WAIVED))
    typer.echo(f"waived visual design for {project_id}; entered {phase.value}")


@app.command("watch")
def watch_dashboard(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
    replay: Annotated[
        bool, typer.Option("--replay", help="Replay historical ledger events")
    ] = False,
    speed: Annotated[float, typer.Option("--speed", help="Playback speed multiplier")] = 1.0,
) -> None:
    """Live dashboard monitoring current phase, queue, circuits, worktrees, and ledger tail."""
    from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository
    from vibey.tui.dashboard import (
        DashboardState,
        VibeyDashboardApp,
        VibeyReplayApp,
        build_replay_states,
        fetch_dashboard_state,
    )

    async def run_dashboard() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            if replay:
                events = await resources.ledger.all_for_project(project.project_id)
                states = build_replay_states(project, events)
                replay_app = VibeyReplayApp(states=states, playback_speed_hz=speed)
                await replay_app.run_async()
            else:
                health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
                initial_state = await fetch_dashboard_state(
                    projects=resources.projects,
                    jobs=resources.jobs,
                    health=health_repo,
                    ledger=resources.ledger,
                    project_id=project.project_id,
                )

                async def _fetch_state() -> DashboardState:
                    return await fetch_dashboard_state(
                        projects=resources.projects,
                        jobs=resources.jobs,
                        health=health_repo,
                        ledger=resources.ledger,
                        project_id=project.project_id,
                    )

                tui_app = VibeyDashboardApp(
                    initial_state=initial_state,
                    state_fetcher=_fetch_state,
                )
                await tui_app.run_async()

    asyncio.run(run_dashboard())


@app.command("recover")
def recover(
    project_id: Annotated[
        UUID | None, typer.Option("--project", help="Optional project ID to recover")
    ] = None,
    all_projects: Annotated[
        bool, typer.Option("--all", help="Recover jobs for all projects")
    ] = False,
) -> None:
    """Recover stuck leased jobs, setting them back to ready state."""
    import re

    import asyncpg

    from vibey.bootstrap import database_url

    async def run_recover() -> None:
        if not project_id and not all_projects:
            typer.echo("Must specify either --project <id> or --all")
            raise typer.Exit(1)

        conn = await asyncpg.connect(database_url())
        try:
            if all_projects:
                result = await conn.execute(
                    "UPDATE job SET state = 'ready', lease_owner = NULL, lease_expires_at = NULL, "
                    "assigned_engine = NULL WHERE state = 'leased'"
                )
            else:
                result = await conn.execute(
                    "UPDATE job SET state = 'ready', lease_owner = NULL, lease_expires_at = NULL, "
                    "assigned_engine = NULL WHERE state = 'leased' AND project_id = $1",
                    project_id,
                )

            # asyncpg hands back the command status tag -- "UPDATE 3". The
            # pattern here was once written r"UPDATE (\\d+)", which looks for a
            # literal backslash and so never matched: the count printed 0
            # however many rows had just been reset.
            match = re.search(r"UPDATE (\d+)", result)
            count = match.group(1) if match else "0"
            typer.echo(f"Recovered {count} stuck job(s).")
        finally:
            await conn.close()

    asyncio.run(run_recover())


@app.command("status")
def status(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Output status as JSON")] = False,
) -> None:
    """Show status of the project, queue, and engine circuits."""
    from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository
    from vibey.tui.dashboard import fetch_dashboard_state

    async def get_status() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                target_id = latest.project_id

            health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
            state = await fetch_dashboard_state(
                projects=resources.projects,
                jobs=resources.jobs,
                health=health_repo,
                ledger=resources.ledger,
                project_id=target_id,
            )

            if as_json:
                data = {
                    "project_id": str(state.project_id),
                    "name": state.project_name,
                    "phase": state.phase.value,
                    "cycle": state.cycle,
                    "max_cycles": state.max_cycles,
                    "repo_path": str(state.repo_path),
                    "visual_decision": state.visual_decision,
                    "deployment_decision": state.deployment_decision,
                    "queue_depth": {k.value: v for k, v in state.queue_depth.items()},
                    "circuits": [
                        {
                            "engine_id": c.engine_id.value,
                            "installed": c.installed,
                            "version": c.version,
                            "conformance_ok": c.conformance_ok,
                            "circuit": (
                                c.circuit.value if hasattr(c.circuit, "value") else str(c.circuit)
                            ),
                            "capacity_state": str(c.capacity_state) if c.capacity_state else None,
                            "consecutive_fail": c.consecutive_fail,
                            "cost_usd_cycle": c.cost_usd_cycle,
                            "selected_count": c.selected_count,
                        }
                        for c in state.circuits
                    ],
                    "active_worktrees": list(state.active_worktrees),
                }
                typer.echo(json.dumps(data, indent=2))
            else:
                vis = f" | Visual: {state.visual_decision}" if state.visual_decision else ""
                dep = f" | Deploy: {state.deployment_decision}" if state.deployment_decision else ""
                typer.echo(f"Project: {state.project_name} ({state.project_id})")
                typer.echo(
                    f"Phase: {state.phase_label} | Cycle: {state.cycle}/{state.max_cycles}{vis}{dep}"
                )
                typer.echo(f"Repo: {state.repo_path}")
                typer.echo("\nQueue Depth:")
                for k, v in state.queue_depth.items():
                    typer.echo(f"  {k.name if isinstance(k, JobState) else k.value}: {v}")
                typer.echo("\nCircuits:")
                if not state.circuits:
                    typer.echo("  (no engines recorded)")
                else:
                    for c in state.circuits:
                        st = c.circuit.value if hasattr(c.circuit, "value") else str(c.circuit)
                        summary = (
                            f"{c.engine_id}: {st} "
                            f"(fails={c.consecutive_fail}, cost=${c.cost_usd_cycle:.2f})"
                        )
                        typer.echo(f"  {summary}")

    asyncio.run(get_status())


@app.command("engines")
def engines(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Show engine health, circuit breakers, and selection metrics."""
    from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository

    async def list_engines() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                target_id = latest.project_id

            health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
            records = await health_repo.list_for_project(target_id)
            if not records:
                typer.echo("no engines recorded for project")
                return

            header = (
                f"{'ENGINE':<12} {'VERSION':<10} {'CIRCUIT':<10} "
                f"{'FAILS':<6} {'SELECTED':<10} {'COST':<8}"
            )
            typer.echo(header)
            typer.echo("-" * 60)
            for r in records:
                circuit_str = r.circuit.value if hasattr(r.circuit, "value") else str(r.circuit)
                typer.echo(
                    f"{r.engine_id:<12} {r.version or '-':<10} {circuit_str:<10} "
                    f"{r.consecutive_fail:<6} {r.selected_count:<10} ${r.cost_usd_cycle:<7.2f}"
                )

    asyncio.run(list_engines())


@app.command("loops")
def loops(
    as_json: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the full JSON document instead: every engine's efforts, "
            "capabilities, run, control and event facts, and environment names.",
        ),
    ] = False,
) -> None:
    """List the two loops, their engines at every effort, and what each engine can do.

    Needs no database and no network: the local switches are read as `vibey doctor`
    reads them, from the environment and then ./vibey.toml.
    """
    with guard():
        LOOPS.run(as_json=as_json)


@app.command("cost")
def cost(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Show the cycle's spend against the caps the budget brake enforces."""
    from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository

    async def show_cost() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            # The brake's own numbers, not a second opinion (issue #210): the
            # caps through the one parser the worker uses, and the spend from
            # the ledger sum the worker checks before every BUILD session --
            # which also carries DESIGN's spend, unlike engine_health. Read
            # through the one budget reader `vibey budget` shows, too.
            budget = (await resources.project_budgets.show(project.project_id)).budget
            max_dollars, max_turns = budget.max_dollars, budget.max_turns
            dollar_cap = f"${max_dollars:.2f}" if max_dollars is not None else "none (uncapped)"
            turn_cap = str(max_turns) if max_turns is not None else "none"

            typer.echo(f"Project: {project.name} (Cycle {project.cycle})")
            typer.echo(
                f"Cycle spend:      ${budget.dollars_spent:.2f} ({budget.turns_spent} turns)"
            )
            typer.echo(f"Cycle dollar cap: {dollar_cap}")
            typer.echo(f"Cycle turn cap:   {turn_cap}")
            if budget.any_exhausted:
                typer.echo("Cap reached: the next BUILD session parks a budget_exhausted gate.")

            # Per engine, from engine_health. Its cost column is each engine's
            # metered BUILD-session spend (issue #209), which accumulates across
            # cycles -- nothing resets it -- so it is labelled as such rather
            # than as this cycle's, and it leaves DESIGN out. The count is how
            # often rotation selected the engine, which is not a turn count.
            health_repo = PostgresEngineHealthRepository(resources.ledger._pool)
            records = await health_repo.list_for_project(project.project_id)
            typer.echo("\nPer-engine (BUILD sessions, all cycles):")
            for r in records:
                typer.echo(
                    f"  • {r.engine_id}: ${r.cost_usd_cycle:.2f} ({r.selected_count} selections)"
                )

    asyncio.run(show_cost())


@ledger_app.callback(invoke_without_command=True)
def ledger(ctx: typer.Context) -> None:
    """Inspect the append-only event ledger."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@ledger_app.command("show")
def ledger_show(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
    limit: Annotated[int, typer.Option("--limit", "-n", min=1)] = 50,
    phase: Annotated[str | None, typer.Option("--phase")] = None,
    kind: Annotated[str | None, typer.Option("--kind")] = None,
) -> None:
    """Show the append-only event ledger history."""
    # `--kind` reads a label the way `ledger search --kind` does, from the same
    # resolver: a known kind by value or name, any case; anything else matched
    # exactly as written, so a kind a newer vibey recorded is still findable
    # from this one (vibey#275).
    wanted: LedgerEventKind | None = None
    if kind is not None:
        try:
            wanted = EVENT_KINDS.resolve(kind)
        except InvalidLedgerQuery as exc:
            raise typer.BadParameter(str(exc)) from exc
        for note in PRESENTER.kind_notes((wanted,)):
            typer.echo(note, err=True)

    async def show_events() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                target_id = latest.project_id

            events = await resources.ledger.all_for_project(target_id)
            if phase is not None:
                # A phase a newer vibey wrote (vibey#287) has only its stored text,
                # so it matches by value; a member matches by value or by name.
                events = tuple(
                    e
                    for e in events
                    if e.phase.value.lower() == phase.lower()
                    or (isinstance(e.phase, Phase) and e.phase.name.lower() == phase.lower())
                )
            if wanted is not None:
                events = tuple(e for e in events if e.kind == wanted)

            displayed = events[-limit:] if len(events) > limit else events
            for e in displayed:
                ts = e.produced_at.strftime("%Y-%m-%d %H:%M:%S")
                eng = f" [{e.engine_id.value}]" if e.engine_id else ""
                shown = e.phase.name if isinstance(e.phase, Phase) else e.phase.value
                typer.echo(f"#{e.seq:<4} {ts} [{shown}] {e.kind.value}{eng}")

    asyncio.run(show_events())


@deploy_app.callback(invoke_without_command=True)
def deploy(ctx: typer.Context) -> None:
    """Manage and inspect Phase ④, ⑤, ⑥ deployments."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


@deploy_app.command("status")
def deploy_status(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Show deployment status, active phase, live endpoints, and verification state."""

    async def show_status() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            events = await resources.ledger.all_for_project(project.project_id)
            dep_events = [
                e
                for e in events
                if e.kind == EventKind.ARTIFACT_PRODUCED
                and e.payload.get("artifact_type") == "deployment_verification"
            ]
            endpoint = "(none)"
            if dep_events:
                outputs = dep_events[-1].payload.get("outputs", {})
                if isinstance(outputs, dict) and "endpoint" in outputs:
                    endpoint = str(outputs["endpoint"])

            typer.echo(f"Project:    {project.name} ({project.project_id})")
            phase_label = (
                project.phase.name if isinstance(project.phase, Phase) else project.phase.value
            )
            typer.echo(f"Phase:      {phase_label}")
            typer.echo(f"Cycle:      {project.cycle}/{project.max_cycles}")
            typer.echo(f"Endpoint:   {endpoint}")

    asyncio.run(show_status())


@deploy_app.command("inspect")
def deploy_inspect(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Inspect the active DeploymentSpec, scope digest, and topology configuration."""

    async def show_inspect() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            events = await resources.ledger.all_for_project(project.project_id)
            spec_events = [
                e
                for e in events
                if e.kind == EventKind.DECISION_RECORDED
                and e.payload.get("decision") == "deployment_spec_accepted"
            ]

            spec_id = "default"
            scope_digest = "none"
            budget = "$100.00"
            if spec_events:
                p = spec_events[-1].payload
                spec_id = str(p.get("spec_id", spec_id))
                scope_digest = str(p.get("scope_digest", scope_digest))
                mb = p.get("monthly_budget", 100.0)
                budget = f"${float(str(mb)):.2f}"

            typer.echo("Deployment Spec Inspection:")
            typer.echo(f"  • spec_id:        {spec_id}")
            typer.echo(f"  • scope_digest:   {scope_digest}")
            typer.echo(f"  • monthly_budget: {budget}")

    asyncio.run(show_inspect())


@deploy_app.command("plan")
def deploy_plan(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Print a placeholder plan evaluation (NOT YET IMPLEMENTED: does not call
    domain.deployment.evaluate_iac_plan or infrastructure.azure.iac.IacValidator
    against the real IaC changeset, budget, or destructive-operation checks)."""

    async def run_plan() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            typer.echo(f"Plan Evaluation for {project.name}:")
            typer.echo("  • Status: NOT EVALUATED — this command is a placeholder")
            typer.echo("  • Destructive Deletions: not checked (no real IaC plan was read)")
            typer.echo("  • Budget Adherence: not checked (no real cost boundary was evaluated)")

    asyncio.run(run_plan())


@deploy_app.command("cancel")
def deploy_cancel(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Print a placeholder cancellation notice (NOT YET IMPLEMENTED: does not
    call AzureClientPort.delete_resource or otherwise touch any real cloud
    resource, ledger event, or job/phase state)."""

    async def run_cancel() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            typer.echo(
                f"deploy cancel is not yet implemented — no cloud resources for "
                f"{project.name} were cancelled or cleaned up."
            )

    asyncio.run(run_cancel())


@deploy_app.command("rollback")
def deploy_rollback(
    project_id: Annotated[UUID | None, typer.Argument(help="Optional project ID")] = None,
) -> None:
    """Print a placeholder rollback notice (NOT YET IMPLEMENTED: does not call
    AzureClientPort.delete_resource or any other real rollback operation, and
    does not transition any job/phase state)."""

    async def run_rollback() -> None:
        async with build_app() as resources:
            target_id = project_id
            if target_id is None:
                latest = await resources.projects.get_latest()
                if latest is None:
                    typer.echo("no projects found; create one with `vibey new` first")
                    raise typer.Exit(1)
                project = latest
            else:
                proj = await resources.projects.get(target_id)
                if proj is None:
                    typer.echo(f"unknown project {target_id}")
                    raise typer.Exit(1)
                project = proj

            typer.echo(
                f"deploy rollback is not yet implemented — no rollback was "
                f"performed for {project.name}."
            )

    asyncio.run(run_rollback())


@app.command("install")
def install(
    postgres: Annotated[
        bool,
        typer.Option(
            "--postgres",
            help=(
                f"Install and start local PostgreSQL {POSTGRES_MIN_MAJOR}+ "
                "using the host package manager"
            ),
        ),
    ] = False,
) -> None:
    """Install local dependencies that vibey can manage explicitly."""
    if not postgres:
        typer.echo("choose an install target with `vibey install --postgres`")
        raise typer.Exit(EXIT_USAGE)

    service = PostgresLocalService()
    result = service.install()
    typer.echo(_postgres_status_line(result.status))
    typer.echo(result.detail)
    if not result.ok:
        raise typer.Exit(1)
    typer.echo(
        "Set VIBEY_PG_URL to a database you own, for example "
        "postgresql://$USER@localhost:5432/vibey"
    )


@app.command("doctor")
def doctor(
    conformance: Annotated[
        bool, typer.Option("--conformance", help="Run the 9-check conformance suite")
    ] = False,
    engine: Annotated[
        str | None,
        typer.Option("--engine", help="Specific engine to check (default: all installed)"),
    ] = None,
    record: Annotated[
        bool,
        typer.Option(
            "--record",
            help="Persist preflight (and conformance, with --conformance) to engine_health",
        ),
    ] = False,
    record_project: Annotated[
        UUID | None,
        typer.Option("--project", help="Project to record health for (default: latest)"),
    ] = None,
    cluster: Annotated[
        bool,
        typer.Option(
            "--cluster",
            help="In-cluster preflight instead: DSN, workspace, secrets, database, migrations",
        ),
    ] = False,
    worker_engines: Annotated[
        str | None,
        typer.Option(
            "--engines",
            help="With --cluster: the worker's --engines allow-list (chart worker.engines); "
            "engine-auth requires exactly these",
        ),
    ] = None,
    worker_provider: Annotated[
        str | None,
        typer.Option(
            "--provider",
            help="With --cluster: the worker's --provider (chart worker.provider)",
        ),
    ] = None,
    install_postgres: Annotated[
        bool,
        typer.Option(
            "--install-postgres",
            help="Install and start local PostgreSQL when it is missing or stopped",
        ),
    ] = False,
) -> None:
    """Check local PostgreSQL, engine health, auth status, and conformance."""
    from vibey.application.conformance import run_conformance
    from vibey.infrastructure.engines.classify import CREDITS_FIXTURES
    from vibey.infrastructure.engines.descriptors import DEFAULT_DESCRIPTORS
    from vibey.infrastructure.engines.local_engines import LocalEndpointEnvironment

    if cluster and install_postgres:
        typer.echo("--install-postgres applies only to the local doctor")
        raise typer.Exit(EXIT_USAGE)

    if cluster:
        postgres_status = None
    else:
        postgres_service = PostgresLocalService()
        postgres_status = (
            postgres_service.install().status if install_postgres else postgres_service.status()
        )

    async def run_doctor() -> None:
        import tempfile
        from uuid import uuid4

        local_postgres_status = cast(PostgresStatus, postgres_status)
        # The worker runs every local engine that is switched on; without this the
        # health check was the one place that could not see them, so the engine the
        # operator is actually depending on stayed invisible unless they knew to ask
        # for it by name. A preferred path you cannot inspect is not a preferred path.
        # The same resolver builds claudeloop-local from its configured profile and
        # gives qwenloop the endpoint the worker would, so doctor probes what runs.
        local = _local_engines_from_toml()
        endpoint = LocalEndpointEnvironment(os.environ)
        if engine is not None:
            from vibey.domain.engine import EngineId

            try:
                eids = [EngineId(engine)]
            except ValueError as exc:
                typer.echo(f"Unknown engine: {engine}")
                raise typer.Exit(1) from exc
        else:
            eids = [d.engine_id for d in DEFAULT_DESCRIPTORS] + list(local.enabled_engines)

        all_ok = True

        record_project_id: UUID | None = None
        # What the probes may see of this environment. With nothing recorded there is no
        # project to declare anything, so the defaults; with --record, the target
        # project's `engine_environment`, because the health written to that project must
        # be measured with what its sessions will receive -- a credential it declares
        # for agyloop included.
        engine_environment = EngineEnvironmentPolicy()
        if record:
            async with build_app() as resources:
                if record_project is not None:
                    target = await resources.projects.get(record_project)
                else:
                    target = await resources.projects.get_latest()
            if target is None:
                typer.echo("no projects found; create one with `vibey new` first")
                raise typer.Exit(1)
            record_project_id = target.project_id
            try:
                engine_environment = EngineEnvironmentPolicy.from_config(target.config)
            except ValueError as exc:
                typer.echo(f"project {record_project_id}: {exc}")
                raise typer.Exit(EXIT_USAGE) from exc

        for eid in eids:
            adapter = engine_environment.applied_to(local.adapter(eid, endpoint))
            desc = adapter.descriptor
            preflight = await adapter.preflight()

            status = "installed" if preflight.installed else "NOT INSTALLED"
            version = preflight.version or "?"
            auth = "auth OK" if preflight.auth_ok else "auth FAIL"
            typer.echo(f"{desc.engine_id.value:<16} {status:<14} v{version:<10} {auth}")

            if preflight.detail:
                typer.echo(f"  detail: {preflight.detail}")

            if conformance and preflight.installed:
                from vibey.domain.capacity import CreditsExhausted

                capacity_fixtures = [
                    ("credits", CREDITS_FIXTURES[desc.engine_id], CreditsExhausted)
                ]
                # Use a unique scratch directory per conformance run to avoid
                # session-lock collisions in shared state
                conformance_id = uuid4().hex[:8]
                unique_worktree = str(
                    Path(tempfile.gettempdir()) / f"vibey-conformance-{conformance_id}"
                )
                report = await run_conformance(
                    adapter,
                    capacity_fixtures=capacity_fixtures,
                    trivial_worktree=unique_worktree,
                )
                for check in report.checks:
                    mark = "PASS" if check.ok else "FAIL"
                    detail = f" — {check.detail}" if check.detail else ""
                    typer.echo(f"  {mark} {check.name}{detail}")
                if not report.ok:
                    all_ok = False

                if record_project_id is not None:
                    async with build_app() as resources:
                        await resources.engine_health_service.update_from_preflight(
                            record_project_id, desc.engine_id, preflight, conformance_ok=report.ok
                        )
                    typer.echo(f"  recorded engine_health for {desc.engine_id.value}")
            elif record_project_id is not None:
                async with build_app() as resources:
                    await resources.engine_health_service.record_preflight(
                        record_project_id, desc.engine_id, preflight
                    )
                typer.echo(f"  recorded preflight for {desc.engine_id.value}")

        typer.echo(_postgres_status_line(local_postgres_status))
        if install_postgres and not local_postgres_status.ready:
            typer.echo(f"  detail: {local_postgres_status.detail}")
            raise typer.Exit(1)
        # The database section. ADR-0055: whenever there is a database to ask, ask
        # whether the application's role could rewrite the ledger -- a single-DSN install
        # fails here until the roles are split, so the step cannot be forgotten silently
        # (12.e). Beside it: keeping VIBEY_PG_URL out of every model-driven process
        # protects nothing if the database lets the worker's OS user in without it.
        database_ok = await _database_security_section()
        # TODO: `db-passwordless` (below) overlaps ADR-0055's `local-auth` (above); both
        # now FAIL (sub-doctrine 10.j, ADR-0061); reviewers to decide whether to consolidate.
        reach_ok = await _passwordless_reach_section()
        if (conformance and not all_ok) or not database_ok or not reach_ok:
            raise typer.Exit(1)

    async def run_cluster_doctor() -> None:
        import shutil

        from vibey.bootstrap import database_url, migrations_dir
        from vibey.infrastructure.cluster_preflight import (
            ClusterPreflight,
            EngineAuthCheck,
            all_ok,
        )
        from vibey.infrastructure.interfaces.cluster_preflight_interface import (
            ClusterPreflightInterface,
        )

        # The engine check needs what the worker was TOLD to run, not what is on
        # PATH: every runner ships in the image (ADR-0037), so presence says nothing.
        try:
            engine_auth = EngineAuthCheck.for_worker(
                engines=worker_engines, provider=worker_provider, which=shutil.which
            )
        except ValueError as exc:
            typer.echo(f"Invalid worker flag: {exc}")
            raise typer.Exit(EXIT_USAGE) from exc
        preflight: ClusterPreflightInterface = ClusterPreflight(engine_auth=engine_auth)
        checks = await preflight.run(
            dsn=database_url(),
            workspace=Path.cwd(),
            migrations_dir=migrations_dir(),
            environ=os.environ,
            uid=os.getuid(),
        )
        for check in checks:
            typer.echo(f"{check.mark} {check.name:<20} {check.detail}")
        if not all_ok(checks):
            raise typer.Exit(1)

    if cluster:
        asyncio.run(run_cluster_doctor())
        return
    if worker_engines is not None or worker_provider is not None:
        typer.echo("--engines and --provider describe the worker; they apply only with --cluster")
        raise typer.Exit(EXIT_USAGE)

    asyncio.run(run_doctor())


async def _database_security_section() -> bool:
    """`vibey doctor`'s database section: the ledger guard and password-less access
    (ADR-0055), printed as PASS, FAIL or UNKNOWN. False when either check failed.

    A module-level function because it is `doctor`'s own step, shared by nothing
    else; the checks themselves live in `DatabaseSecurityChecks`.
    """
    from vibey.infrastructure.cluster_preflight import DatabaseSecurityChecks, check_database

    dsn = os.environ.get("VIBEY_PG_URL", "").strip()
    if not dsn:
        typer.echo(f"UNKNOWN {'ledger-guard':<20} VIBEY_PG_URL is not set; nothing to check")
        return True
    connected, conn = await check_database(dsn)
    if conn is None:
        typer.echo(f"FAIL {'ledger-guard':<20} {connected.detail}")
        return False
    try:
        checks = await DatabaseSecurityChecks().run(conn, dsn)
    finally:
        await conn.close()
    for check in checks:
        typer.echo(f"{check.mark} {check.name:<20} {check.detail}")
    return all(check.ok for check in checks)


@app.command("migrate")
def migrate() -> None:
    """Apply migrations as the owner and reconcile the application role's grants.

    Reads the owner's DSN from VIBEY_PG_MIGRATE_URL and the application's from
    VIBEY_PG_URL (ADR-0055). Creates the application role if it is missing and its
    DSN carries a password, revokes every privilege it holds, grants exactly the
    declared ones, then connects as it and reports whether the ledger guard is in
    force. Exits 1 when it is not, so an install still running as one role cannot
    pass this step silently.
    """
    from vibey.bootstrap import migrations_dir
    from vibey.infrastructure.db.database_setup import OwnerMigration
    from vibey.infrastructure.db.ledger_guard import (
        DatabaseEndpoints,
        DatabaseRoleReconciler,
        LedgerGuardInspector,
    )
    from vibey.infrastructure.db.migrator import PostgresMigrator, discover_migrations

    owner_url = os.environ.get(DatabaseEndpoints.MIGRATE_ENV, "").strip()
    if not owner_url:
        typer.echo(
            f"{DatabaseEndpoints.MIGRATE_ENV} is not set: `vibey migrate` runs as the "
            "schema's owner, and needs that role's DSN"
        )
        raise typer.Exit(EXIT_USAGE)
    app_url = os.environ.get(DatabaseEndpoints.APP_ENV, "").strip()
    runner = OwnerMigration(
        migrator=PostgresMigrator.from_environ(os.environ),
        reconciler=DatabaseRoleReconciler(),
        inspector=LedgerGuardInspector(),
    )
    try:
        report = asyncio.run(
            runner.run(
                owner_url=owner_url,
                app=DatabaseEndpoints(app_url=app_url) if app_url else None,
                migrations=discover_migrations(migrations_dir()),
            )
        )
    except VibeyError as exc:
        # A refusal (a missing role the owner may not create, an application role that
        # cannot be guarded) is the answer, said plainly -- not a traceback.
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from None
    typer.echo(
        f"applied {len(report.applied)} migration(s)"
        + (f": {', '.join(report.applied)}" if report.applied else "")
    )
    if report.reconciled_role is not None:
        typer.echo(f"granted {report.reconciled_role} exactly the declared privileges")
    if report.guard is None:
        typer.echo(
            f"{DatabaseEndpoints.APP_ENV} is not set: no application role reconciled, and "
            "the ledger guard was not checked"
        )
        raise typer.Exit(1)
    typer.echo(f"ledger guard {report.guard.describe()}")
    if not report.guard.in_force:
        raise typer.Exit(1)


@app.command("operator")
def operator(
    namespace: Annotated[
        str | None,
        typer.Option(
            "--namespace",
            help="Watch a single namespace (default: cluster-wide)",
        ),
    ] = None,
) -> None:
    """Run the Kubernetes operator: reconcile VibeyProject custom resources."""
    # Imported here, not at module scope: kopf and the Kubernetes client are
    # an optional extra, and `vibey worker` on a laptop should not require
    # them to start.
    try:
        from vibey.infrastructure.operator import run as run_operator
    except ImportError as exc:
        typer.echo("operator support is not installed: pip install 'vibey[operator]'")
        raise typer.Exit(1) from exc

    run_operator(namespace=namespace)


@app.command("worker")
def worker(
    engines_opt: Annotated[
        str | None,
        typer.Option("--engines", help="Comma-separated list of engines to use"),
    ] = None,
    parallelism: Annotated[int, typer.Option("--parallelism", "-j", min=1, max=16)] = 1,
    once: Annotated[
        bool,
        typer.Option("--once", help="Process one job and exit"),
    ] = False,
    provider_opt: Annotated[str | None, typer.Option("--provider", help=_PROVIDER_HELP)] = None,
    max_turns: Annotated[int, typer.Option("--max-turns", min=1)] = 25,
    max_dollars: Annotated[float, typer.Option("--max-dollars", min=0.01, max=10)] = 2.0,
    ollama_model: Annotated[
        str | None,
        typer.Option("--ollama-model", help=_OLLAMA_MODEL_HELP),
    ] = None,
    project_opt: Annotated[
        UUID | None,
        typer.Option("--project", help="Project id (default: the latest project)"),
    ] = None,
    wait_for_project: Annotated[
        float | None,
        typer.Option(
            "--wait-for-project",
            min=1.0,
            help=(
                "Poll every N seconds for a project instead of exiting when none "
                "exists. For long-lived deployments, where exiting means a "
                "restart loop until someone creates one."
            ),
        ),
    ] = None,
    azure: Annotated[
        str,
        typer.Option(
            "--azure",
            help="Azure client for the deploy stage set: 'memory' (safe default, "
            "no real infrastructure) or 'az' (the real Azure CLI; requires "
            "`az login` and mutates real resources on consented deploys)",
        ),
    ] = "memory",
) -> None:
    """Long-running worker: LISTEN vibey_job_ready, dispatch across all phases."""
    from datetime import timedelta

    from vibey.application.worker import WorkerLoop
    from vibey.bootstrap import build_full_worker, database_url
    from vibey.domain.engine import EngineId
    from vibey.infrastructure.db.notifier import PostgresJobReadyNotifier
    from vibey.infrastructure.engines.local_engines import LocalEndpointEnvironment
    from vibey.infrastructure.engines.scripted_decompose import ScriptedWorkPlanProducer

    allow_list: frozenset[EngineId] | None = None
    if engines_opt:
        try:
            allow_list = frozenset(EngineId(e.strip()) for e in engines_opt.split(","))
        except ValueError as exc:
            typer.echo(f"Invalid engine: {exc}")
            raise typer.Exit(2) from exc
    if provider_opt is not None and provider_opt not in _PROVIDERS:
        typer.echo(_UNKNOWN_PROVIDER)
        raise typer.Exit(2)
    if azure not in ("memory", "az"):
        typer.echo("--azure must be 'memory' or 'az'")
        raise typer.Exit(2)
    azure_client = None
    if azure == "az":
        from vibey.infrastructure.azure.az_cli import AzCliClientAdapter

        login_check = subprocess.run(  # nosec B603 B607 - fixed argv, never shell=True
            ["az", "account", "show", "-o", "none"], capture_output=True, text=True
        )
        if login_check.returncode != 0:
            typer.echo("--azure az requires a logged-in Azure CLI: run `az login` first")
            raise typer.Exit(1)
        azure_client = AzCliClientAdapter()

    async def run_worker() -> None:
        from vibey.application.interfaces import WorkPlanProducer
        from vibey.infrastructure.engines.claudeloop_decompose import ClaudeLoopWorkPlanProducer

        # Kubernetes scale-in is SIGTERM, a wait, then SIGKILL. A
        # worker that ignores SIGTERM keeps claiming jobs it cannot
        # possibly finish: the kill lands mid-session, the lease is
        # orphaned, and a paid turn is thrown away. Draining means
        # exactly one thing -- finish the job in hand, claim no more --
        # so the flag is read between jobs and nowhere else. Checking
        # it mid-job would be the very truncation it exists to avoid.
        #
        # SIGTERM only, deliberately. Ctrl-C keeps its immediate-abort
        # semantics: an operator who interrupts a foreground worker
        # means now, not "in up to two hours".
        #
        # Registered as the very first thing once the event loop is
        # running -- before any I/O (DB connect, project lookup). On a
        # freshly scaled pod, kubelet's SIGTERM can arrive within
        # milliseconds of the process starting, and PID 1 silently
        # drops an unhandled signal rather than queuing it: a handler
        # installed even one await later can lose the race and never
        # see the signal that was actually sent.
        draining = asyncio.Event()

        def _begin_drain() -> None:
            typer.echo("draining on SIGTERM: finishing in-flight job, claiming no more")
            draining.set()

        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, _begin_drain)

        # The handler above is installed as early as the event loop allows, and that is
        # still not early enough: everything before it -- interpreter start, imports,
        # argument parsing -- is time in which SIGTERM sent to PID 1 is DISCARDED rather
        # than queued, because its disposition was still SIG_DFL. A scale-in that lands in
        # that window is not delivered late; it is never delivered, and the pod then runs
        # until terminationGracePeriodSeconds expires. For a worker that is two hours.
        #
        # So ask the latch, armed at import time, whether it already happened. Observed on
        # minikube: a pod deleted 0.2s after its container started, which then sat through
        # the full grace period claiming jobs nobody was waiting for.
        SIGTERM_LATCH.release()
        if SIGTERM_LATCH.fired:
            typer.echo("SIGTERM arrived during startup; draining immediately", err=True)
            draining.set()

        typer.echo("sigterm handler registered", err=True)

        async with build_app() as resources:
            # ADR-0055: a worker whose role could rewrite the ledger says so at every
            # start, on stderr, and names the fix; it still runs, so an upgrade never
            # strands an install, and `vibey doctor` fails until the roles are split.
            guard = resources.ledger_guard
            if guard is not None and not guard.in_force:
                typer.echo(
                    f"error: ledger guard {guard.describe()} -- split the roles: "
                    "docs/reference/configuration.md#database-roles",
                    err=True,
                )

            async def _resolve_project() -> ProjectRecord | None:
                if project_opt is not None:
                    return await resources.projects.get(project_opt)
                return await resources.projects.get_latest()

            project = await _resolve_project()
            # A one-shot CLI run should fail fast when there is nothing to
            # work on. A long-lived deployment must not: exiting there is a
            # restart loop that ends only when a human creates a project,
            # and the crash counter makes a perfectly healthy worker look
            # broken. Waiting is opt-in so the CLI default stays honest.
            while project is None and wait_for_project is not None:
                typer.echo(f"no project yet; polling every {wait_for_project:g}s")
                await asyncio.sleep(wait_for_project)
                project = await _resolve_project()
            if project is None:
                typer.echo("no projects found; create one with `vibey new` first")
                raise typer.Exit(1)
            if not isinstance(project.phase, Phase):
                typer.echo(
                    f"project {project.project_id} has unknown phase {project.phase.value!r}; "
                    "refusing to dispatch; upgrade vibey",
                    err=True,
                )
                raise typer.Exit(1)

            # Sovereign by default (8.b, #322); an explicit --provider still wins.
            provider = _resolve_provider(provider_opt)
            design_provider: DesignProvider
            decomposer: WorkPlanProducer
            if provider == "claudeloop":
                claude_process = ClaudeLoopProcess(
                    executor=AsyncSubprocessExecutor(
                        EngineEnvironmentPolicy.from_config(project.config).environment(CLAUDELOOP)
                    ),
                    max_turns=max_turns,
                    max_dollars=max_dollars,
                    spend_recorder=_build_spend_recorder(
                        resources.ledger, project.project_id, project.cycle, project.phase
                    ),
                )
                design_provider = ClaudeLoopDesignProvider(
                    process=claude_process,
                    worktree_path=project.repo_path,
                )
                decomposer = ClaudeLoopWorkPlanProducer(
                    process=claude_process,
                    worktree_path=project.repo_path,
                )
            elif provider == "qwenloop":
                # Doctrine 8.a: the sovereign path is the preferred way to run, so the
                # long-running worker has to be able to select it too, not just the
                # one-shot `vibey work` -- and for DECOMPOSE as well as DESIGN. This used
                # to hand BUILD's plan to ScriptedWorkPlanProducer, the test fake, whose
                # items carry no verification commands. One client, so both providers
                # talk to the same server and model.
                from vibey.infrastructure.engines.qwenloop_decompose import (
                    QwenloopWorkPlanProducer,
                )

                chat = OllamaChatClient.from_environment(os.environ, model=ollama_model)
                design_provider = QwenloopDesignProvider.from_environment(os.environ, chat=chat)
                decomposer = QwenloopWorkPlanProducer(chat=chat)
            else:
                design_provider = ScriptedDesignProvider()
                decomposer = ScriptedWorkPlanProducer()

            # The pool has to be the one `build_full_worker` will actually run, so ask
            # the same resolver it does instead of keeping a second copy of the rule.
            # Without this a local engine was the one engine the startup sweep could
            # not see: it ran, but its conformance warning never appeared, so an
            # operator depending on it had no way to learn it would never be selected.
            # `--ollama-model` reaches qwenloop's process as QWENLOOP_MODEL too, so the
            # BUILD engine and the DESIGN/DECOMPOSE providers run the same model.
            local = LocalEngineSettings(environ=os.environ, config=project.config)
            adapters = dict(resources.engine_adapters)
            endpoint = LocalEndpointEnvironment(os.environ, model=ollama_model)
            for engine_id, local_adapter in local.adapters(endpoint).items():
                adapters.setdefault(engine_id, local_adapter)
            # The sweep probes each engine's auth, so it must probe with what the engine's
            # sessions will actually receive: the project's `engine_environment` on top of
            # the defaults. Without it a credential the project declares (agyloop's
            # Vertex credentials, say) was invisible to the auth check,
            # and the engine read "auth FAIL" although its sessions would authenticate.
            engine_environment = EngineEnvironmentPolicy.from_config(project.config)
            adapters = {
                engine_id: engine_environment.applied_to(adapter)
                for engine_id, adapter in adapters.items()
            }
            if allow_list is not None:
                allowed = {eid: a for eid, a in adapters.items() if eid in allow_list}
                # An allow-list matching nothing used to start a worker with zero
                # engines, which then deferred every engine-driven job every five
                # minutes, forever, saying nothing. Nothing downstream can recover from
                # that, so the only honest answer is to refuse at startup and say why.
                if not allowed:
                    available = ", ".join(sorted(e.value for e in adapters))
                    typer.echo(
                        f"--engines {engines_opt} matches none of this worker's engines "
                        f"({available}); a local engine joins them only with its switch "
                        "on -- VIBEY_FEATURE_QWENLOOP=1 or VIBEY_FEATURE_CLAUDELOOP_LOCAL=1, "
                        "or [features] qwenloop / claudeloop_local in the project's config "
                        "when that environment override is unset."
                    )
                    raise typer.Exit(EXIT_USAGE)
                adapters = allowed

            preflight_report = await resources.conductor_preflight.run(
                project_id=project.project_id,
                adapters=adapters,
            )
            ineligible = preflight_report.ineligible_engines
            if ineligible:
                names = ", ".join(sorted(e.value for e in ineligible))
                typer.echo(
                    f"warning: no recorded conformance for {names} -- engine-driven jobs "
                    "will not select them until `vibey doctor --conformance --record` passes"
                )

            feasibility = preflight_report.feasibility
            location = (
                ""
                if feasibility.blocked_at is None
                else f" — blocked at stage {feasibility.blocked_at!r}"
            )
            basis = (
                f"; first repair: {feasibility.first_repair}"
                if feasibility.first_repair is not None
                else (
                    f"; {feasibility.required_measured} of {feasibility.required} "
                    "required coordinates measured; no measured shortfall"
                )
            )
            typer.echo(
                f"preflight feasibility: {feasibility.status.upper()}{location}{basis}",
                err=feasibility.status == "infeasible",
            )

            count = max(1, min(parallelism, len(adapters) * 2, os.cpu_count() or 1))
            loops = [
                build_full_worker(
                    resources=resources,
                    project=project,
                    design_provider=design_provider,
                    visual_provider=ScriptedVisualProvider(),
                    decomposer=decomposer,
                    owner=f"worker-{os.getpid()}-{i}",
                    engine_adapters=adapters,
                    allow_list=allow_list,
                    azure_client=azure_client,
                )
                for i in range(count)
            ]

            notifier = PostgresJobReadyNotifier(database_url())
            await notifier.connect()

            typer.echo(
                f"worker started: project={project.name} "
                f"engines={engines_opt or 'all'} parallelism={count} provider={provider}"
            )

            # TEMPORARY: pinning down why a scaled-in pod isn't draining within
            # the expected ~60s on minikube (observed: stuck well past 5m, the
            # SIGTERM handler registered above never firing its own echo).
            # Cheap enough to leave on: one line per loop per iteration,
            # nothing per-job.
            async def drive(loop_: WorkerLoop, *, idx: int) -> None:
                iteration = 0
                while not draining.is_set():
                    iteration += 1
                    typer.echo(f"drive[{idx}] iter={iteration} calling run_once", err=True)
                    worked = await loop_.run_once(project.project_id)
                    typer.echo(
                        f"drive[{idx}] iter={iteration} run_once returned worked={worked}", err=True
                    )
                    if worked:
                        typer.echo("processed one job")
                        if once:
                            return
                        continue
                    if once:
                        typer.echo("no ready job")
                        return
                    await resources.jobs.reap()
                    # Stale ready work and the broker, at most once per interval across
                    # every drive loop (ADR-0056); the lease reap just ran above.
                    await resources.queue_reaper.run_if_due(project.project_id)
                    typer.echo(
                        f"drive[{idx}] iter={iteration} reap done, waiting for notify", err=True
                    )
                    await notifier.wait_for_job_ready(
                        project.project_id, timeout=timedelta(seconds=5)
                    )
                typer.echo(f"drive[{idx}] draining flag observed, exiting loop", err=True)

            try:
                if once or count == 1:
                    await drive(loops[0], idx=0)
                else:
                    await asyncio.gather(*(drive(loop_, idx=i) for i, loop_ in enumerate(loops)))
            finally:
                await notifier.close()

    with guard():
        asyncio.run(run_worker())
