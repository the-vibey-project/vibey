# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""EngineEnvironmentPolicy: what each engine session may see, declared and exact.

An engine session runs model-chosen shell commands, unattended in BUILD and
DEPLOY_EXECUTE. It is given the system basics, its own declared variables and its own
API credential -- and nothing else unless the project's config record declares it.
vibey's queue and ledger DSN, database passwords, GitHub tokens and cloud credentials
are not on any default list, and the first two can never be put on one."""

from dataclasses import replace

import pytest

from vibey.domain.engine import EngineDescriptor, EngineId
from vibey.infrastructure.engines.descriptors import (
    AGYLOOP,
    ALL_DESCRIPTORS,
    CLAUDELOOP,
    CODEXLOOP,
    CURSORLOOP,
    OPENCODE,
    QWENLOOP,
)
from vibey.infrastructure.engines.engine_environment import EngineEnvironmentPolicy
from vibey.infrastructure.engines.interfaces import EngineEnvironmentPolicyInterface
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.process import SYSTEM_ENVIRONMENT
from vibey.infrastructure.process.interfaces import ChildEnvironmentInterface

# Everything credential-bearing a worker's environment can hold. None of it may reach
# an engine session unless the project declares it -- and the first group never can.
_NEVER = {
    "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
    "VIBEY_TEST_DATABASE_URL": "postgresql://vibey:secret@db/test",
    "VIBEY_SECRETS_TOKEN": "openbao-secret",
    "VIBEY_BLOB_SECRET_KEY": "garage-secret",
    "PGPASSWORD": "secret",
    "PGHOST": "db",
    "DATABASE_URL": "postgresql://app:secret@db/app",
}
_UNLESS_DECLARED = {
    "GH_TOKEN": "ghp_secret",
    "GITHUB_TOKEN": "ghs_secret",
    "AWS_ACCESS_KEY_ID": "AKIA",
    "AWS_SECRET_ACCESS_KEY": "aws-secret",
    "AWS_SESSION_TOKEN": "aws-session",
    "AZURE_CLIENT_SECRET": "azure-secret",
    "ARM_CLIENT_SECRET": "arm-secret",
    "GOOGLE_APPLICATION_CREDENTIALS": "/keys/sa.json",
    "GOOGLE_ACCESS_TOKEN": "ya29",
    "CLOUDSDK_AUTH_ACCESS_TOKEN": "ya29",
}
_WORKER = {"PATH": "/usr/bin:/bin", "HOME": "/home/worker", **_NEVER, **_UNLESS_DECLARED}

_EVERY_ENGINE = ALL_DESCRIPTORS


def _build(policy: EngineEnvironmentPolicy, descriptor: EngineDescriptor) -> dict[str, str]:
    return policy.environment(descriptor, source=_WORKER).build()


@pytest.mark.parametrize("descriptor", _EVERY_ENGINE, ids=lambda d: d.engine_id.value)
def test_no_engine_receives_a_dsn_or_credential_even_when_the_worker_holds_them(
    descriptor: EngineDescriptor,
) -> None:
    env = _build(EngineEnvironmentPolicy(), descriptor)

    assert env == {"PATH": "/usr/bin:/bin", "HOME": "/home/worker"}


def test_every_descriptor_is_covered_here() -> None:
    assert {d.engine_id for d in _EVERY_ENGINE} == set(EngineId)


# The engine's own declared variables (`env_passthrough`, a trailing `*` naming a
# prefix) and its own API credential (`auth_env`). Changing one of these is changing
# what a model-driven session can read; this table makes that a visible diff.
_DECLARED: dict[EngineId, tuple[str, ...]] = {
    EngineId.CLAUDELOOP: (
        "CLAUDE_CONFIG_DIR",
        "ANTHROPIC_API_KEY",
        "CLAUDELOOP_*",
        "CLAUDE_CODE_*",
        "ANTHROPIC_*",
    ),
    EngineId.CLAUDELOOP_LOCAL: (
        "CLAUDE_CONFIG_DIR",
        "CLAUDELOOP_*",
        "CLAUDE_CODE_*",
        "ANTHROPIC_*",
    ),
    EngineId.CODEXLOOP: (
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_ENDPOINT",
        "OPENAI_API_KEY",
        "CODEXLOOP_*",
        "CODEX_*",
        "OPENAI_*",
    ),
    EngineId.CURSORLOOP: ("CURSOR_API_KEY", "CURSORLOOP_*", "CURSOR_*"),
    EngineId.AGYLOOP: (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "AGYLOOP_*",
        "ANTIGRAVITY_*",
    ),
    EngineId.OPENCODE: ("OPENCODELOOP_*", "OPENCODE_*"),
    EngineId.GPTOSSLOOP: ("GPTOSSLOOP_*",),
    EngineId.QWENLOOP: ("QWENLOOP_*",),
}


@pytest.mark.parametrize("descriptor", _EVERY_ENGINE, ids=lambda d: d.engine_id.value)
def test_the_allow_list_is_exactly_the_system_list_plus_what_the_engine_declares(
    descriptor: EngineDescriptor,
) -> None:
    allow = EngineEnvironmentPolicy().allow_list(descriptor)

    assert set(allow.entries()) == set(SYSTEM_ENVIRONMENT.entries()) | set(
        _DECLARED[descriptor.engine_id]
    )


def test_each_engines_declared_variables_admit_what_the_engine_reads() -> None:
    policy = EngineEnvironmentPolicy()
    assert policy.allow_list(CLAUDELOOP).admits("ANTHROPIC_BASE_URL")
    assert policy.allow_list(CLAUDELOOP).admits("CLAUDELOOP_MAX_TURNS")
    assert policy.allow_list(CODEXLOOP).admits("CODEX_HOME")
    assert policy.allow_list(CURSORLOOP).admits("CURSOR_API_KEY")
    assert policy.allow_list(AGYLOOP).admits("GEMINI_API_KEY")
    assert policy.allow_list(OPENCODE).admits("OPENCODE_CONFIG")
    assert policy.allow_list(QWENLOOP).admits("QWENLOOP_BASE_URL")
    # ...and not what another engine reads.
    assert not policy.allow_list(QWENLOOP).admits("ANTHROPIC_API_KEY")


def test_the_project_config_adds_to_every_engine_and_to_one_engine() -> None:
    policy = EngineEnvironmentPolicy.from_config(
        {
            "engine_environment": {
                "allow": ["CORP_CA_BUNDLE", "CORP_*"],
                "engines": {"agyloop": ["GOOGLE_APPLICATION_CREDENTIALS"], "claudeloop": []},
            }
        }
    )

    agy = _build(policy, AGYLOOP)
    claude = _build(policy, CLAUDELOOP)

    assert agy["GOOGLE_APPLICATION_CREDENTIALS"] == "/keys/sa.json"
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in claude
    assert policy.allow_list(CLAUDELOOP).admits("CORP_CA_BUNDLE")
    assert policy.allow_list(QWENLOOP).admits("CORP_PROXY_PAC")
    for env in (agy, claude):
        for name in _NEVER:
            assert name not in env


def test_a_github_token_reaches_only_the_engine_it_is_declared_for() -> None:
    policy = EngineEnvironmentPolicy.from_config(
        {"engine_environment": {"engines": {"claudeloop": ["GH_TOKEN"]}}}
    )

    assert _build(policy, CLAUDELOOP)["GH_TOKEN"] == "ghp_secret"
    assert "GH_TOKEN" not in _build(policy, CODEXLOOP)
    assert "GITHUB_TOKEN" not in _build(policy, CLAUDELOOP)


@pytest.mark.parametrize("config", [{}, {"engine_environment": None}, {"engine_environment": {}}])
def test_without_an_engine_environment_object_the_defaults_apply(config: dict[str, object]) -> None:
    policy = EngineEnvironmentPolicy.from_config(config)

    assert policy.allow_list(CLAUDELOOP).entries() == (
        EngineEnvironmentPolicy().allow_list(CLAUDELOOP).entries()
    )


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("VIBEY_PG_URL", "engine_environment project config must be an object"),
        ({"allow": ["VIBEY_PG_URL"]}, "engine_environment.allow.*can never be passed"),
        ({"allow": ["VIBEY_*"]}, "can never be passed"),
        ({"allow": ["PGPASSWORD"]}, "can never be passed"),
        ({"allow": ["DATABASE_URL"]}, "can never be passed"),
        ({"allow": "GH_TOKEN"}, "engine_environment.allow must be a list of strings"),
        ({"engines": ["agyloop"]}, "engine_environment.engines must be an object"),
        ({"engines": {"nosuchloop": ["X"]}}, "unknown engine 'nosuchloop'"),
        ({"engines": {"agyloop": ["VIBEY_PG_URL"]}}, "engine_environment.engines.agyloop"),
        ({"engines": {"agyloop": "X"}}, "must be a list of strings"),
        ({"alow": ["X"]}, "unknown key 'alow'"),
    ],
)
def test_a_malformed_or_forbidden_declaration_is_refused_when_the_worker_is_built(
    raw: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        EngineEnvironmentPolicy.from_config({"engine_environment": raw})


def test_a_descriptor_that_declares_a_forbidden_credential_is_refused() -> None:
    """A descriptor is code, not config -- but the rule is the same, and a descriptor
    that names vibey's DSN as its credential fails loudly instead of receiving it."""
    bad = replace(CLAUDELOOP, auth_env=("VIBEY_PG_URL",))

    with pytest.raises(ValueError, match="can never be passed"):
        EngineEnvironmentPolicy().allow_list(bad)


def test_the_policy_is_applied_to_a_loop_adapter_and_leaves_anything_else_alone() -> None:
    policy = EngineEnvironmentPolicy.from_config(
        {"engine_environment": {"engines": {"claudeloop": ["GH_TOKEN"]}}}
    )
    adapter = LoopProcessAdapter(descriptor=CLAUDELOOP, env_overlay={"X_OVERLAY": "1"})
    other = object()

    applied = policy.applied_to(adapter)

    assert isinstance(applied, LoopProcessAdapter)
    assert applied.environment is policy
    assert applied.env_overlay == {"X_OVERLAY": "1"}
    assert applied.descriptor is CLAUDELOOP
    assert policy.applied_to(other) is other  # type: ignore[arg-type]


def test_the_environment_carries_the_overlay_and_the_python_guard() -> None:
    class _NoVenv:
        def interpreter_venv(self) -> str | None:
            return None

        def venv_prefixes(self) -> tuple[str | None, ...]:
            return (None, None)

    child = EngineEnvironmentPolicy().environment(
        QWENLOOP,
        overlay={"QWENLOOP_BASE_URL": "http://h/v1"},
        python_env=_NoVenv(),
        source={"PATH": "/usr/bin", "VIRTUAL_ENV": "/v", "VIBEY_OLLAMA_URL": "http://h"},
    )

    assert isinstance(child, ChildEnvironmentInterface)
    assert child.build() == {"PATH": "/usr/bin", "QWENLOOP_BASE_URL": "http://h/v1"}


def test_the_policy_satisfies_its_declared_interface() -> None:
    assert isinstance(EngineEnvironmentPolicy(), EngineEnvironmentPolicyInterface)
