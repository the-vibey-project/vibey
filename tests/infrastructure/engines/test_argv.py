# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import shlex
from pathlib import Path
from uuid import UUID

import pytest

from vibey.application.dto import RunSpec
from vibey.domain.effort import Effort
from vibey.domain.engine import IsolationLevel
from vibey.infrastructure.engines.argv import build_argv
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS

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


def test_opencode_resume_keeps_the_vibey_run_id() -> None:
    from vibey.infrastructure.engines.descriptors import OPENCODE

    spec = RunSpec(
        run_id=RUN_ID,
        worktree_path=Path(WORKTREE),
        prompt="continue",
        effort=Effort.STANDARD,
        isolation=IsolationLevel.WORKTREE,
        session_id="sess-abc123",
    )
    argv = build_argv(OPENCODE, spec)
    assert argv[:5] == (
        "opencodeloop",
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
    """cursorloop's `run` requires `--plan <path>`; the other three take a
    bare positional. Passing a positional to cursorloop killed every run at
    argument parsing (live finding: no run dir, no events, no snapshot)."""
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP, CURSORLOOP

    spec = _spec(Effort.STANDARD)

    cursor_argv = build_argv(CURSORLOOP, spec)
    assert cursor_argv[1:3] == ("run", "--plan")
    assert cursor_argv[3].endswith(".md")

    claude_argv = build_argv(CLAUDELOOP, spec)
    assert claude_argv[1] == "run"
    assert claude_argv[2].endswith(".md")
    assert "--plan" not in claude_argv
