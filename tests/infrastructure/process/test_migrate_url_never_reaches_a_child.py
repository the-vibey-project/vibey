# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`VIBEY_PG_MIGRATE_URL` -- the ledger OWNER's DSN (ADR-0055) -- never reaches a child.

It is the one credential that can rewrite the ledger once the roles are split, and it
sits in the worker's environment next to `VIBEY_PG_URL`. Every child vibey starts
builds its environment from an allow-list under a rule that forbids `VIBEY_*`; this
pins that for the migration DSN by name, for each kind of child, and pins that no
declaration can put it back.
"""

from pathlib import Path

import pytest

from vibey.infrastructure.azure.az_cli import AzCliSubprocessExecutor
from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.git.clean_env import CleanGitEnvSubprocessExecutor
from vibey.infrastructure.notify.desktop import DesktopNotifier
from vibey.infrastructure.skills_context import VibeySkillsContextCompiler

_NAME = "VIBEY_PG_MIGRATE_URL"


@pytest.fixture(autouse=True)
def _worker_holds_the_owner_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_NAME, "postgresql://vibey_owner:secret@db/vibey")


@pytest.mark.parametrize("engine", sorted(BY_ENGINE_ID, key=lambda e: e.value))
def test_no_engine_session_receives_it(engine: object) -> None:
    descriptor = BY_ENGINE_ID[engine]  # type: ignore[index]
    env = EngineEnvironmentPolicy().environment(descriptor).build()
    assert _NAME not in env


def test_no_gate_command_git_call_az_call_notifier_or_skills_cli_receives_it(
    tmp_path: Path,
) -> None:
    builders = {
        "gate": SubprocessGateRunner()._environment,
        "git": CleanGitEnvSubprocessExecutor()._environment,
        "az": AzCliSubprocessExecutor().environment,
        "notifier": DesktopNotifier()._environment,
        "skills": VibeySkillsContextCompiler(
            mode="shadow", index_path=tmp_path / "index"
        )._environment,
    }
    leaked = {kind for kind, builder in builders.items() if _NAME in builder.build()}
    assert leaked == set()


@pytest.mark.parametrize(
    "declare",
    [
        lambda: EngineEnvironmentPolicy(allow=(_NAME,)),
        lambda: EngineEnvironmentPolicy.from_config(
            {"engine_environment": {"engines": {"claudeloop": [_NAME]}}}
        ),
        lambda: SubprocessGateRunner.from_config({"gates": {"env_allow": [_NAME]}}),
        lambda: AzCliSubprocessExecutor(env_allow=(_NAME,)),
    ],
)
def test_no_declaration_can_put_it_back(declare: object) -> None:
    with pytest.raises(ValueError, match=_NAME):
        declare()  # type: ignore[operator]
