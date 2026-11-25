# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The environment walk: no engine session holds a SearXNG address, a Brave key, the host or agent
token or the database DSN (SP-LOOPS Phase 6, Task 7; the parent plan's acceptance test).

Every engine vibey knows (`ALL_DESCRIPTORS`, so an engine added later is walked without a line
here) has its BUILD session started the way the worker starts it -- the adapter the worker
composes (`LocalEndpointEnvironment` overlay, the project's `EngineEnvironmentPolicy` with the
running `vibey` named), the run's web access opened by the worker's own `run_web_grants` -- while
the worker's own environment holds every forbidden name. The environment handed to the spawn is
captured and walked, for a worker with a hub running and one without:

- none of the forbidden names, no `WEBSEARCH_*` name, and no name carrying `SEARXNG` or `BRAVE`;
- none of their values under any other name, and never the session's own token;
- of vibey's own names, exactly the session's web names: `VIBEY_HUB_URL` and
  `VIBEY_WEB_TOKEN_FILE` (a token file in the run's own folder) when the run holds a grant, else
  exactly `VIBEY_WEB_STATE=none:<reason>`;
- for an engine that reaches the hub through its snapshot's `vibey-web` connector (claudeloop),
  the connector keeps nothing beyond those two names.

Real overlay, policy and grant code; only the process environment (`monkeypatch.setenv`), the
spawn (`asyncio.create_subprocess_exec`, captured, never run) and where the hub runs are stand-ins.
No process is started. The negative cases prove the walk is not vacuous: each forbidden name laid
over the session -- even past the forbidden rule, as a widened grant would let it -- fails it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Final, cast
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import vibey.bootstrap as bootstrap
from vibey.application.dto import RunSpec, RunWebAccess
from vibey.application.web_connector import WebConnector
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineDescriptor, IsolationLevel
from vibey.domain.no_web_reasons import NO_WEB_REASONS
from vibey.domain.session_web_state import (
    HUB_URL_VARIABLE,
    NO_HUB,
    NO_RUN_FOLDER,
    STATE_VARIABLE,
    TOKEN_FILE_VARIABLE,
)
from vibey.infrastructure.engines import engine_environment as engine_environment_module
from vibey.infrastructure.engines import loop_process_adapter as adapter_module
from vibey.infrastructure.engines.descriptors import ALL_DESCRIPTORS
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.engines.local_engines import LocalEndpointEnvironment
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.engines.session_web_overlay import SESSION_WEB_OVERLAY
from vibey.infrastructure.web.search import BRAVE_KEY_NAMES, SEARXNG_URL_ENV

HUB: Final = "http://127.0.0.1:8765"
VIBEY: Final = "/opt/vibey/bin/vibey"

FORBIDDEN: Final[Mapping[str, str]] = {
    # The search backend's address, under vibey's name and the old session name.
    SEARXNG_URL_ENV: "http://127.0.0.1:18080/fake-searxng-vibey",
    "WEBSEARCH_SEARXNG_URL": "http://127.0.0.1:18081/fake-searxng-websearch",
    # The Brave key under every name vibey reads it by.
    **{name: f"fake-brave-key-{n}" for n, name in enumerate(BRAVE_KEY_NAMES)},
    # The hub's host token and the agent's token.
    "VIBEY_HUB_TOKEN": "fake-host-token-0001",
    "VIBEY_HOST_TOKEN": "fake-host-token-0002",
    "VIBEY_AGENT_TOKEN": "fake-agent-token-0003",
    # The queue and ledger.
    "VIBEY_PG_URL": "postgresql://vibey:fake-password@127.0.0.1:5432/vibey",
    # What a session was told before Phase 6, so the worker may still hold it.
    "WEBSEARCH_PROVIDER": "fake-searxng-provider",
    "WEBSEARCH_COMMAND": "/fake/websearch/vibey",
}
"""Each name the worker holds and no session may: the plan's global constraints, by name."""

WORKER: Final[Mapping[str, str]] = {
    # The one local endpoint, so the local engines' own overlays are walked too.
    "VIBEY_OLLAMA_URL": "http://127.0.0.1:11434",
    **FORBIDDEN,
}
WEB_NAMES: Final = frozenset({HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE, STATE_VARIABLE})


class _Hub:
    """Where the hub runs: at `HUB`, or nowhere."""

    url_given: str | None = None

    def __init__(self, state_dir: Path, **_: object) -> None:
        self.state_dir = state_dir

    def url(self) -> str | None:
        return self.url_given


def _engines() -> list[EngineDescriptor]:
    return list(ALL_DESCRIPTORS)


def _check(env: Mapping[str, str], access: RunWebAccess, engine: str) -> None:
    """Fails, naming the engine and the leak, unless `env` is a clean session environment for
    `access`."""
    for name in FORBIDDEN:
        assert name not in env, f"{engine}: {name} reached the session"
    smuggled = [n for n in env if n.startswith("WEBSEARCH_") or "SEARXNG" in n or "BRAVE" in n]
    assert not smuggled, f"{engine}: {smuggled} reached the session"
    for name, value in env.items():
        for secret in FORBIDDEN.values():
            assert secret not in value, f"{engine}: a forbidden value reached it as {name}"
    vibeys = {name for name in env if name.startswith("VIBEY_")}
    if access.token_file is not None:
        assert vibeys == {HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE}, f"{engine}: {sorted(vibeys)}"
        assert env[HUB_URL_VARIABLE] == HUB
        assert env[TOKEN_FILE_VARIABLE] == str(access.token_file)
        token = access.token_file.read_text(encoding="utf-8").strip()
        assert token and not any(token in value for value in env.values())
    else:
        assert vibeys == {STATE_VARIABLE}, f"{engine}: {sorted(vibeys)}"
        assert env[STATE_VARIABLE] == NO_WEB_REASONS.state(access.reason)
        assert env[STATE_VARIABLE].startswith("none:")


async def _session(
    descriptor: EngineDescriptor,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    policy: Callable[[EngineEnvironmentPolicy], EngineEnvironmentPolicy] = lambda p: p,
) -> tuple[dict[str, str], RunWebAccess]:
    """The environment `descriptor`'s BUILD session is spawned with, and the run's web access,
    composed as the worker composes them."""
    engine = descriptor.engine_id.value
    folder: Path | None = None
    if descriptor.capabilities_flag is not None:  # only these get a run folder (BUILD, Phase 4)
        folder = tmp_path / "snapshots" / f"run-{engine}"
        folder.mkdir(mode=0o700, parents=True)
        folder.chmod(0o700)
    access = bootstrap.run_web_grants(timedelta(hours=2), state_dir=tmp_path / "hub").open(
        uuid4(), folder
    )
    adapter = policy(EngineEnvironmentPolicy.from_config({}).with_vibey_command(VIBEY)).applied_to(
        LoopProcessAdapter(
            descriptor=descriptor,
            env_overlay=LocalEndpointEnvironment(WORKER).overlay_for(descriptor.engine_id),
        )
    )
    captured: dict[str, str] = {}

    async def spawn(*argv: str, **kwargs: object) -> AsyncMock:
        env = kwargs["env"]
        assert isinstance(env, dict)
        captured.update(env)
        process = AsyncMock()
        process.pid, process.returncode = 4242, None
        return process

    monkeypatch.setattr(adapter_module.asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(adapter_module.shutil, "which", lambda name: f"/fake/bin/{name}")
    worktree = tmp_path / "worktrees" / engine
    worktree.mkdir(parents=True)
    spec = RunSpec(
        run_id=uuid4(),
        worktree_path=worktree,
        prompt="Implement the task.",
        effort=Effort.LOW,
        isolation=IsolationLevel.WORKTREE,
        web=access,
    )
    assert isinstance(adapter, LoopProcessAdapter)
    handle = await adapter.start(spec)
    adapter_module._active_processes.pop(handle.run_id, None)  # noqa: SLF001
    for file in adapter_module._diagnostic_files.pop(handle.run_id, ()):  # noqa: SLF001
        file.close()
    assert captured, f"{engine}: nothing was spawned"
    return captured, access


async def _walk(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    hub: str | None,
    policy: Callable[[EngineEnvironmentPolicy], EngineEnvironmentPolicy] = lambda p: p,
) -> list[str]:
    """Walks every engine's session for a worker with the hub at `hub` (or none); returns the
    engines walked."""
    for name, value in WORKER.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(_Hub, "url_given", hub)
    monkeypatch.setattr(bootstrap, "RunningHub", _Hub)
    walked: list[str] = []
    for descriptor in _engines():
        engine = descriptor.engine_id.value
        env, access = await _session(descriptor, tmp_path / engine, monkeypatch, policy=policy)
        _check(env, access, engine)
        if descriptor.web_connector and access.token_file is not None:
            connector = WebConnector(VIBEY).spec(access.token_file)
            assert set(connector.env_allow) == {HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE}
            assert set(connector.env_allow) <= set(env)
        walked.append(engine)
    return walked


def test_the_walk_covers_every_engine_vibey_knows() -> None:
    engines = {descriptor.engine_id.value for descriptor in _engines()}
    assert {"claudeloop", "claudeloop-local", "codexloop", "gptossloop", "qwenloop"} <= engines


async def test_a_hub_running_worker_gives_each_session_its_grant_and_nothing_of_its_own(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    walked = await _walk(tmp_path, monkeypatch, hub=HUB)

    assert walked == [descriptor.engine_id.value for descriptor in _engines()]


async def test_a_hub_running_worker_grants_exactly_the_engines_with_a_run_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An engine without a run folder of its own (codexloop) cannot hold a token, so it is told
    why it has no web, in the same fixed names."""
    for name, value in WORKER.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(_Hub, "url_given", HUB)
    monkeypatch.setattr(bootstrap, "RunningHub", _Hub)
    for descriptor in _engines():
        engine = descriptor.engine_id.value
        env, access = await _session(descriptor, tmp_path / engine, monkeypatch)
        if descriptor.capabilities_flag is None:
            assert access.reason == NO_RUN_FOLDER
            assert env[STATE_VARIABLE] == NO_WEB_REASONS.state(NO_RUN_FOLDER)
        else:
            assert access.state == "hub" and access.token_file is not None
            assert access.token_file.parent == tmp_path / engine / "snapshots" / f"run-{engine}"


async def test_a_worker_without_a_hub_tells_each_session_so_and_gives_it_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    walked = await _walk(tmp_path, monkeypatch, hub=None)

    assert walked == [descriptor.engine_id.value for descriptor in _engines()]
    assert not list(tmp_path.rglob("web-token"))  # no token file anywhere


@pytest.mark.parametrize(
    ("engine_environment", "refused"),
    [
        ({"allow": ["WEBSEARCH_SEARXNG_URL", "VIBEY_SEARXNG_URL"]}, "WEBSEARCH_SEARXNG_URL"),
        ({"allow": ["VIBEY_SEARXNG_URL", "WEBSEARCH_SEARXNG_URL"]}, "VIBEY_SEARXNG_URL"),
        (
            {
                "engines": {
                    "qwenloop": ["WEBSEARCH_SEARXNG_URL"],
                    "claudeloop": ["VIBEY_SEARXNG_URL"],
                }
            },
            "WEBSEARCH_SEARXNG_URL",
        ),
        ({"engines": {"gptossloop": ["VIBEY_SEARXNG_URL"]}}, "VIBEY_SEARXNG_URL"),
        ({"allow": ["WEBSEARCH_*"]}, r"WEBSEARCH_\*"),
    ],
    ids=["allow", "allow-reversed", "per-engine", "per-engine-vibey", "prefix"],
)
def test_a_project_that_declares_the_searxng_address_for_its_sessions_gets_no_worker(
    monkeypatch: pytest.MonkeyPatch, engine_environment: Mapping[str, object], refused: str
) -> None:
    """The walk above uses no project `engine_environment`; a project's own may not reopen what
    the walk proves closed. The worker is built the way `vibey worker` builds it, from the
    project's record, while its own environment holds the SearXNG address under both names: it
    refuses to build, naming the first declared name, so no session ever starts to receive one."""
    for name, value in WORKER.items():
        monkeypatch.setenv(name, value)

    def no_spawn(*argv: str, **kwargs: object) -> None:
        raise AssertionError("a worker that refuses to build starts no session")

    monkeypatch.setattr(adapter_module.asyncio, "create_subprocess_exec", no_spawn)
    project = SimpleNamespace(config={"engine_environment": engine_environment})

    with pytest.raises(ValueError, match=f"{refused} can never be passed to a child process"):
        bootstrap.build_full_worker(
            resources=cast(Any, SimpleNamespace(engine_adapters={})),
            project=cast(Any, project),
            design_provider=cast(Any, None),
            visual_provider=cast(Any, None),
            decomposer=cast(Any, None),
            owner="walk-refused-worker",
            engine_adapters={},
        )


async def test_with_no_hub_the_reason_is_no_hub_for_a_run_that_has_a_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name, value in WORKER.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(_Hub, "url_given", None)
    monkeypatch.setattr(bootstrap, "RunningHub", _Hub)
    for descriptor in _engines():
        env, access = await _session(descriptor, tmp_path / descriptor.engine_id.value, monkeypatch)
        expected = NO_HUB if descriptor.capabilities_flag is not None else NO_RUN_FOLDER
        assert env[STATE_VARIABLE] == NO_WEB_REASONS.state(expected)


# -- The walk is not vacuous ----------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
@pytest.mark.parametrize("hub", [HUB, None], ids=["hub", "no-hub"])
async def test_the_walk_fails_when_any_forbidden_name_is_laid_over_the_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, hub: str | None
) -> None:
    """The session's own web overlay is given one forbidden name more, and the forbidden rule is
    widened to grant it, as a careless change to `overlay_grants` would: nothing refuses it on
    the way to the spawn, and the walk alone catches it."""
    widened = replace(
        engine_environment_module.MODEL_SESSION_FORBIDDEN,
        overlay_grants=(*engine_environment_module.MODEL_SESSION_FORBIDDEN.overlay_grants, name),
    )
    monkeypatch.setattr(engine_environment_module, "MODEL_SESSION_FORBIDDEN", widened)
    real = SESSION_WEB_OVERLAY.environment

    def leaking(web: RunWebAccess | None) -> dict[str, str]:
        return {**real(web), name: FORBIDDEN[name]}

    monkeypatch.setattr(SESSION_WEB_OVERLAY, "environment", leaking)

    with pytest.raises(AssertionError, match=name):
        await _walk(tmp_path, monkeypatch, hub=hub)


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
async def test_the_walk_fails_when_the_workers_overlay_carries_a_forbidden_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    """The worker's own overlay for every session (`with_overlay`) gains one forbidden name: the
    forbidden rule refuses vibey's own names and vibey's web search settings (`WEBSEARCH_*`, the
    Brave key's aliases) as the adapter is built, and the walk catches anything it misses."""

    def polluted(policy: EngineEnvironmentPolicy) -> EngineEnvironmentPolicy:
        return policy.with_overlay({name: FORBIDDEN[name]})

    with pytest.raises((AssertionError, ValueError), match=name):
        await _walk(tmp_path, monkeypatch, hub=HUB, policy=polluted)


@pytest.mark.parametrize("name", sorted(FORBIDDEN))
def test_the_check_itself_names_each_forbidden_name(name: str) -> None:
    """A clean environment passes the check; the same with one forbidden name fails it."""
    access = RunWebAccess("none", reason=NO_HUB)
    clean = {"PATH": "/usr/bin", STATE_VARIABLE: NO_WEB_REASONS.state(NO_HUB)}
    _check(clean, access, "any")

    with pytest.raises(AssertionError, match=name):
        _check({**clean, name: FORBIDDEN[name]}, access, "any")
