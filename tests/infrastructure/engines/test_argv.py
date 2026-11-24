# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import shlex
from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.dto import RunSpec
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.infrastructure.engines.argv import (
    BINARY,
    CWD,
    EFFORT_ARGV,
    PLAN,
    PLAN_FLAG,
    RUN_ARGV_TEMPLATE,
    build_argv,
)
from vibey.infrastructure.engines.argv import RUN_ID as RUN_ID_PLACEHOLDER
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS
from vibey.infrastructure.engines.interfaces.argv_interface import RunArgvTemplateInterface

GOLDEN_DIR = Path(__file__).parent / "golden"
RUN_ID = UUID("00000000-0000-0000-0000-000000000001")
WORKTREE = "/repo/.vibey/worktrees/c1-item-001"

ALL_EFFORTS = list(Effort)


def _spec(effort: Effort) -> RunSpec:
    return RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="implement the outbox relay",
        effort=effort,
        isolation=IsolationLevel.WORKTREE,
    )


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
@pytest.mark.parametrize("effort", ALL_EFFORTS, ids=lambda e: e.name)
def test_argv_matches_golden_file(descriptor, effort) -> None:  # type: ignore[no-untyped-def]
    argv = build_argv(descriptor, _spec(effort))
    golden_path = GOLDEN_DIR / f"{descriptor.engine_id.value}_{effort.name.lower()}.txt"

    expected = golden_path.read_text().strip()
    assert shlex.join(argv) == expected


def test_one_golden_file_per_engine_and_effort_exists() -> None:
    """Every descriptor has one golden per effort: a descriptor added without its goldens, or a
    golden left behind by a removed one, both fail here."""
    files = sorted(GOLDEN_DIR.glob("*.txt"))
    assert len(files) == len(ALL_DESCRIPTORS) * len(ALL_EFFORTS)


def test_claudeloop_local_passes_its_profile_and_a_preset_never_effort() -> None:
    """A local profile does not forward `--effort` (claudeloop's `pass_effort` is off
    there); the tier is picked by `--preset`, and the profile rides on every run."""
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    for effort in ALL_EFFORTS:
        argv = build_argv(CLAUDELOOP_LOCAL, _spec(effort))
        assert argv[0] == "claudeloop"
        assert "--effort" not in argv
        profile_at = argv.index("--profile")
        assert argv[profile_at + 1] == "local"
        assert argv[argv.index("--preset") + 1] in {"low", "medium", "high"}


def test_claudeloop_local_resumes_on_its_profile_too() -> None:
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP_LOCAL

    spec = RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="continue",
        effort=Effort.STANDARD,
        isolation=IsolationLevel.WORKTREE,
        session_id="sess-abc123",
    )
    argv = build_argv(CLAUDELOOP_LOCAL, spec)
    assert argv[:3] == ("claudeloop", "resume", "sess-abc123")
    assert argv[3:7] == ("--profile", "local", "--preset", "medium")


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_new_run_uses_a_positional_plan_file_and_includes_run_id_flag(
    descriptor,
) -> None:  # type: ignore[no-untyped-def]
    argv = build_argv(descriptor, _spec(Effort.LOW))
    plan_index = 3 if descriptor.plan_flag is not None else 2
    if descriptor.plan_flag is not None:
        assert argv[2] == descriptor.plan_flag
    assert argv[plan_index] == f"{WORKTREE}/.vibey/plans/{RUN_ID}.md"
    assert "--run-id" in argv
    run_id_index = argv.index("--run-id")
    assert argv[run_id_index + 1] == str(RUN_ID)


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_resume_verb_used_when_session_id_present(descriptor) -> None:  # type: ignore[no-untyped-def]
    spec = RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="continue",
        effort=Effort.LOW,
        isolation=IsolationLevel.WORKTREE,
        session_id="sess-abc123",
    )
    argv = build_argv(descriptor, spec)
    assert argv[1] == "resume"
    assert argv[2] == "sess-abc123"


def test_a_resume_run_id_flag_keeps_the_vibey_run_id() -> None:
    """A runner that keeps the provider's session id and vibey's run id apart takes the
    run id on resume through its descriptor's `resume_run_id_flag`."""
    from dataclasses import replace

    from vibey.infrastructure.engines.descriptors import QWENLOOP

    descriptor = replace(QWENLOOP, resume_run_id_flag="--run-id")
    spec = RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="continue",
        effort=Effort.STANDARD,
        isolation=IsolationLevel.WORKTREE,
        session_id="sess-abc123",
    )
    argv = build_argv(descriptor, spec)
    assert argv[:5] == (
        "qwenloop",
        "resume",
        "sess-abc123",
        "--run-id",
        str(RUN_ID),
    )


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_cwd_flag_presence_matches_descriptor_capability(descriptor) -> None:  # type: ignore[no-untyped-def]
    """build_argv() must never append --cwd for an engine whose real CLI
    doesn't accept it (codexloop `run` rejects it at argument parsing) --
    regression test for a bug that made LoopProcessAdapter unable to spawn
    codexloop at all, caught by a real subprocess-level conformance test."""
    argv = build_argv(descriptor, _spec(Effort.LOW))
    assert ("--cwd" in argv) == descriptor.supports_cwd_flag


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
def test_isolation_flags_included_for_container(descriptor) -> None:  # type: ignore[no-untyped-def]
    spec = RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="implement",
        effort=Effort.LOW,
        isolation=IsolationLevel.CONTAINER,
    )
    argv = build_argv(descriptor, spec)
    for flag in descriptor.isolation_flags[IsolationLevel.CONTAINER]:
        assert flag in argv


def test_plan_flag_engines_pass_the_plan_as_a_flag_not_a_positional() -> None:
    """A runner whose `run` requires `--plan <path>` gets the flag; the others take a
    bare positional. Passing a positional to such a runner killed every run at argument
    parsing (live finding on an engine ADR-0078 later retired: no run dir, no events, no
    snapshot). No shipped descriptor takes a plan flag today, so one is made here."""
    from dataclasses import replace

    from vibey.infrastructure.engines.descriptors import CLAUDELOOP

    spec = _spec(Effort.STANDARD)

    flagged_argv = build_argv(replace(CLAUDELOOP, plan_flag="--plan"), spec)
    assert flagged_argv[1:3] == ("run", "--plan")
    assert flagged_argv[3].endswith(".md")

    claude_argv = build_argv(CLAUDELOOP, spec)
    assert claude_argv[1] == "run"
    assert claude_argv[2].endswith(".md")
    assert "--plan" not in claude_argv


# -- the run template `vibey loops` reports ------------------------------------------------


def _filled(template: tuple[str, ...], descriptor, effort: Effort) -> tuple[str, ...]:  # type: ignore[no-untyped-def]
    """The template with one run's values in it, as a caller that launches the runner
    itself would fill it."""
    values = {
        BINARY: [descriptor.binary],
        PLAN_FLAG: [descriptor.plan_flag],
        PLAN: [f"{WORKTREE}/.vibey/plans/{RUN_ID}.md"],
        RUN_ID_PLACEHOLDER: [str(RUN_ID)],
        EFFORT_ARGV: list(descriptor.invoke(effort).argv),
        CWD: [WORKTREE],
    }
    return tuple(word for token in template for word in values.get(token, [token]))


def test_the_shared_template_satisfies_its_interface() -> None:
    assert isinstance(RUN_ARGV_TEMPLATE, RunArgvTemplateInterface)


@pytest.mark.parametrize("descriptor", ALL_DESCRIPTORS, ids=lambda d: d.engine_id.value)
@pytest.mark.parametrize("effort", ALL_EFFORTS, ids=lambda e: e.name)
def test_the_run_template_filled_is_exactly_what_build_argv_runs(descriptor, effort) -> None:  # type: ignore[no-untyped-def]
    """The template can never drift from the one place argv is built: filled with a run's
    values it is that run's argv, for every engine at every effort."""
    template = RUN_ARGV_TEMPLATE.template(descriptor)
    assert _filled(template, descriptor, effort) == build_argv(descriptor, _spec(effort))


def test_the_template_names_the_plan_flag_only_where_the_runner_takes_one() -> None:
    from dataclasses import replace

    by_id = {d.engine_id.value: d for d in ALL_DESCRIPTORS}
    flagged = replace(by_id["claudeloop"], plan_flag="--plan")
    assert _filled(RUN_ARGV_TEMPLATE.template(flagged), flagged, Effort.STANDARD) == build_argv(
        flagged, _spec(Effort.STANDARD)
    )
    assert RUN_ARGV_TEMPLATE.template(flagged) == (
        "{binary}", "run", "{plan_flag?}", "{plan}", "--run-id", "{run_id}", "{effort_argv...}",
        "--cwd", "{cwd}",
    )  # fmt: skip
    assert RUN_ARGV_TEMPLATE.template(by_id["claudeloop"]) == (
        "{binary}", "run", "{plan}", "--run-id", "{run_id}", "{effort_argv...}", "--cwd", "{cwd}",
    )  # fmt: skip


def test_the_template_drops_the_cwd_pair_where_the_runner_has_no_such_flag() -> None:
    codexloop = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == "codexloop")
    assert RUN_ARGV_TEMPLATE.template(codexloop) == (
        "{binary}", "run", "{plan}", "--run-id", "{run_id}", "{effort_argv...}",
    )  # fmt: skip


def test_worktree_isolation_adds_no_flags_for_any_engine() -> None:
    """Why the template carries no isolation flags: vibey runs BUILD at worktree isolation,
    and there no descriptor has any."""
    assert all(d.isolation_flags.get(IsolationLevel.WORKTREE, ()) == () for d in ALL_DESCRIPTORS)


CLAUDE_ENGINES = ("claudeloop", "claudeloop-local")


@pytest.mark.parametrize("engine", CLAUDE_ENGINES)
@pytest.mark.parametrize("effort", ALL_EFFORTS, ids=lambda e: e.name)
def test_launch_flags_no_longer_carry_web_search(engine: str, effort: Effort) -> None:
    """vibey asks no claudeloop run for the built-in web tools (SP-LOOPS Phase 4, R4): whether
    they are on is the snapshot's `[loops] builtin_web`, and claudeloop refuses `--web-search`
    beside a snapshot that switches them off (R12). A local backend refuses it outright too
    (claudeloop domain/backend.py `check_tools`). New, with a document, or resumed: never."""
    from dataclasses import replace

    descriptor = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == engine)
    assert descriptor.launch_flags == ()
    resumed = replace(_spec(effort), session_id="sess-abc123")
    for spec in (_spec(effort), replace(_spec(effort), capabilities_file=DOCUMENT), resumed):
        argv = build_argv(descriptor, spec)
        assert "--web-search" not in argv and "--deep-research" not in argv, spec


def _claudeloop_run_params(argv: tuple[str, ...]) -> dict[str, object]:
    """`argv` read by claudeloop's own `run` command, as click would parse it. Resilient, so the
    plan file need not exist: only the flags are read."""
    import typer
    from claudeloop.cli.app import app

    run = typer.main.get_command(app).commands["run"]  # type: ignore[attr-defined]
    assert argv[:2] == ("claudeloop", "run")
    context = run.make_context("run", list(argv[2:]), resilient_parsing=True)
    return dict(context.params)


def _check_flags_against_a_web_off_snapshot(params: dict[str, object], *, local: bool) -> None:
    """claudeloop's own check of `run`'s flags against a snapshot with `[loops] builtin_web =
    false`, the default (claudeloop bootstrap.py runs it before any run folder exists)."""
    from claudeloop.domain.capabilities import CLAUDE_BUILTIN_WEB_TOOLS, AppliedCapabilities
    from claudeloop.domain.mcp_config import McpConfigTranslator
    from claudeloop.infrastructure.capabilities.snapshot_applier import CapabilitySnapshotApplier
    from claudeloop.infrastructure.logging import StructlogAppLogger
    from vibey_runners.common.capabilities.instruction_files import InstructionFileReader
    from vibey_runners.common.capabilities.snapshot_document_store import SnapshotDocumentStore

    web_off = AppliedCapabilities(
        digest="sha256:" + "0" * 64,
        plugin_dirs=(),
        skills=(),
        mcp_servers={},
        disallowed_tools=CLAUDE_BUILTIN_WEB_TOOLS,
        add_dirs=(),
        system_prompt_append="",
        notices=(),
    )
    applier = CapabilitySnapshotApplier(
        SnapshotDocumentStore(),
        local_backend=local,
        mcp=McpConfigTranslator(("python",)),
        environ={},
        logger=StructlogAppLogger(component="test"),
        instructions=InstructionFileReader(),
    )
    connectors = params["connector"] or []
    assert isinstance(connectors, list)
    applier.check_flags(web_off, connectors=connectors, web_search=bool(params["web_search"]))


@pytest.mark.parametrize("engine", CLAUDE_ENGINES)
@pytest.mark.parametrize("effort", ALL_EFFORTS, ids=lambda e: e.name)
def test_a_build_argv_passes_claudeloops_own_flag_check(engine: str, effort: Effort) -> None:
    """The argv a BUILD run is started with, read by claudeloop's `run` and checked by its own
    applier against a snapshot with `[loops] builtin_web = false`: no refusal, which `claudeloop
    run` would exit 2 on (R12). Before Phase 4 Task 9 the descriptor's `--web-search` made every
    real claudeloop BUILD run fail here."""
    from dataclasses import replace

    descriptor = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == engine)
    params = _claudeloop_run_params(
        build_argv(descriptor, replace(_spec(effort), capabilities_file=DOCUMENT))
    )
    assert str(params["capabilities"]) == str(DOCUMENT)
    assert params["web_search"] is False and params["deep_research"] is False
    _check_flags_against_a_web_off_snapshot(params, local=engine == "claudeloop-local")


def test_the_flag_check_refuses_the_web_search_flag_a_descriptor_used_to_pass() -> None:
    """The check above can fail: `--web-search` beside a web-off snapshot is refused."""
    from claudeloop.domain.errors import CapabilityFlagConflict

    params = _claudeloop_run_params(
        ("claudeloop", "run", "/plan.md", "--web-search", "--capabilities", str(DOCUMENT))
    )
    assert params["web_search"] is True
    with pytest.raises(CapabilityFlagConflict, match="--web-search"):
        _check_flags_against_a_web_off_snapshot(params, local=False)


# -- the run's capability document (SP-LOOPS Phase 4, Task 8; R1) ------------------------------

DOCUMENT = Path("/person/loops/snapshots/run-abc/capabilities.json")


def _with_document(session_id: str | None = None) -> RunSpec:
    return RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="implement the outbox relay",
        effort=Effort.STANDARD,
        isolation=IsolationLevel.WORKTREE,
        session_id=session_id,
        capabilities_file=DOCUMENT,
    )


@pytest.mark.parametrize("engine", ["claudeloop", "claudeloop-local"])
def test_a_new_run_carries_the_document_right_after_the_launch_flags(engine: str) -> None:
    from dataclasses import replace

    descriptor = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == engine)
    assert descriptor.capabilities_flag == "--capabilities"
    argv = build_argv(descriptor, _with_document())
    without = build_argv(descriptor, replace(_with_document(), capabilities_file=None))
    after_flags = without.index("--run-id") + 2 + len(descriptor.launch_flags)
    assert argv == (
        *without[:after_flags],
        "--capabilities",
        str(DOCUMENT),
        *without[after_flags:],
    )


@pytest.mark.parametrize("engine", ["codexloop", "gptossloop", "qwenloop"])
def test_a_document_on_a_descriptor_without_the_flag_is_refused(engine: str) -> None:
    descriptor = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == engine)
    assert descriptor.capabilities_flag is None
    with pytest.raises(ValueError, match=f"{engine} takes no capability document"):
        build_argv(descriptor, _with_document())


@pytest.mark.parametrize("engine", ["claudeloop", "codexloop"])
def test_a_resumed_session_never_carries_the_document(engine: str) -> None:
    descriptor = next(d for d in ALL_DESCRIPTORS if d.engine_id.value == engine)
    argv = build_argv(descriptor, _with_document(session_id="sess-abc123"))
    assert "--capabilities" not in argv
    assert str(DOCUMENT) not in argv
