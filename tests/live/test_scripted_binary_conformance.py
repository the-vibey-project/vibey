# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Faked-mode conformance against REAL installed binaries, not ScriptedEngine.

test_faked_conformance.py only ever exercises the in-memory ScriptedEngine
double -- it never spawns a real subprocess, so it can't catch a bug in
argv construction, real events.jsonl production, or LOOP_EVENT_MAP
translation the way a real (even if scripted-mode) engine run can. This
file closes that gap for the engines that ship their own env-gated
scripted/offline agent (claudeloop, codexloop): `LoopProcessAdapter` drives
the real installed binary, which runs its own scripted agent instead of
calling a real model -- no network, no API key, no cost, but a genuine
subprocess spawn through the real production code path `vibey doctor
--conformance` and `vibey worker` both use.

codexloop was a strict xfail here, and is expected to PASS as of PR #72. The
upstream gap it named is still real -- `infrastructure/rundir.py` writes
meta.json exactly once, at run-directory creation, and never a terminal
status, so `process_exited_without_terminal_status` still appears in this
test's own logs and docs/plans/fleet/d0-meta-status-codexloop.md is still
queued. What changed is that vibey stopped depending on it: codexloop#35
added a `run.verdict` event and #72 maps it, so completion is detected
through the verdict path instead of meta.json. The strict xfail is what
surfaced the drift, turning into a failure the moment its premise stopped
holding -- which is why every `_KNOWN_BROKEN_UPSTREAM` entry is marked
`strict=True`.

Every test here skips (not fails) when its binary or fixture script isn't
present on this machine -- mirroring test_paid_preflight.py's pattern --
since these tests depend on sibling repo checkouts at ~/git/<engine> that
won't exist in every environment (e.g. a clean CI runner that only checks
out vibey).
"""

import shutil
from pathlib import Path

import pytest

from vibey.application.conformance import run_conformance
from vibey.domain.capacity import CreditsExhausted
from vibey.domain.engine import EngineId
from vibey.infrastructure.engines.classify import CREDITS_FIXTURES
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter

_SCRIPTED_ENGINES: dict[EngineId, tuple[str, str]] = {
    EngineId.CLAUDELOOP: ("CLAUDELOOP_ALLOW_TEST_AGENT", "CLAUDELOOP_TEST_AGENT_SCRIPT"),
    EngineId.CODEXLOOP: ("CODEXLOOP_ALLOW_TEST_AGENT", "CODEXLOOP_TEST_AGENT_SCRIPT"),
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_FIXTURE_ROOTS = {
    EngineId.CLAUDELOOP: _REPO_ROOT / "src" / "vibey_runners" / "claude",
    EngineId.CODEXLOOP: _REPO_ROOT / "src" / "vibey_runners" / "codex",
}

# An engine whose own scripted agent is known broken upstream, with the reason; its case
# is a strict xfail until the fix lands. None today.
_KNOWN_BROKEN_UPSTREAM: dict[EngineId, str] = {}


def _done_script_for(engine_id: EngineId) -> Path:
    return _FIXTURE_ROOTS[engine_id] / "tests" / "live" / "fixtures" / "agent_scripts" / "done.json"


def _param(engine_id: EngineId) -> object:
    reason = _KNOWN_BROKEN_UPSTREAM.get(engine_id)
    marks = () if reason is None else (pytest.mark.xfail(reason=reason, strict=True),)
    return pytest.param(engine_id, marks=marks, id=engine_id.value)


_SCRIPTED_ENGINE_PARAMS = [_param(e) for e in sorted(_SCRIPTED_ENGINES, key=lambda e: e.value)]


@pytest.mark.live
@pytest.mark.xdist_group("real-engine-binaries")
@pytest.mark.parametrize("engine_id", _SCRIPTED_ENGINE_PARAMS)
async def test_real_binary_scripted_conformance(
    engine_id: EngineId,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    descriptor = BY_ENGINE_ID[engine_id]
    if shutil.which(descriptor.binary) is None:
        pytest.skip(f"{descriptor.binary} not installed")
    script = _done_script_for(engine_id)
    if not script.is_file():
        pytest.skip(f"no scripted-agent fixture at {script} (sibling repo not checked out?)")

    allow_env, script_env = _SCRIPTED_ENGINES[engine_id]
    monkeypatch.setenv(allow_env, "1")
    monkeypatch.setenv(script_env, str(script))

    adapter = LoopProcessAdapter(descriptor=descriptor)
    fixtures = [("credits", CREDITS_FIXTURES[engine_id], CreditsExhausted)]
    report = await run_conformance(
        adapter,
        capacity_fixtures=fixtures,
        trivial_worktree=str(tmp_path / "conformance-wt"),
    )

    assert report.ok, [c for c in report.checks if not c.ok]
