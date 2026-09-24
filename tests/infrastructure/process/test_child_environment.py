# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ChildEnvironment: a model-driven child sees what it was allowed, never the rest.

Engine sessions and gate commands used to receive a copy of the worker's whole
environment with a few Python variables removed. `VIBEY_PG_URL` -- the queue and
ledger DSN -- went with it, into processes that run model-chosen shell commands
during unattended phases. The environment is now built up from an allow-list, and
vibey's own variables can never be put on one."""

import pytest

from vibey.infrastructure.process import (
    GATE_FORBIDDEN,
    MODEL_SESSION_FORBIDDEN,
    SYSTEM_ENVIRONMENT,
    ChildEnvironment,
    EnvironmentAllowList,
    ForbiddenEnvironment,
)
from vibey.infrastructure.process.interfaces import (
    ChildEnvironmentInterface,
    EnvironmentAllowListInterface,
    ForbiddenEnvironmentInterface,
)

# What a worker's environment really carries: its own DSN and credentials beside the
# things a child legitimately needs.
_WORKER = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/worker",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
    "VIBEY_TRACKER_TOKEN": "tracker-secret",
    "PGPASSWORD": "secret",
    "DATABASE_URL": "postgresql://app:secret@db/app",
    "GH_TOKEN": "ghp_secret",
    "GITHUB_TOKEN": "ghs_secret",
    "AWS_SECRET_ACCESS_KEY": "aws-secret",
    "AZURE_CLIENT_SECRET": "azure-secret",
    "GOOGLE_APPLICATION_CREDENTIALS": "/keys/sa.json",
    "ENGINE_API_KEY": "engine-key",
}


class _NoVenv:
    def interpreter_venv(self) -> str | None:
        return None

    def venv_prefixes(self) -> tuple[str | None, ...]:
        return (None, None)


def _model_session(*entries: str) -> EnvironmentAllowList:
    return SYSTEM_ENVIRONMENT.extended(entries, forbidden=MODEL_SESSION_FORBIDDEN)


def test_only_allowed_names_reach_the_child_and_never_a_credential() -> None:
    allow = _model_session("ENGINE_API_KEY")

    env = ChildEnvironment(allow, python_env=_NoVenv(), source=_WORKER).build()

    assert env == {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/worker",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "ENGINE_API_KEY": "engine-key",
    }


def test_a_declared_prefix_admits_every_name_under_it_but_no_forbidden_one() -> None:
    allow = _model_session("ENGINE_*", "DATA*")
    source = {"ENGINE_MODEL": "m", "ENGINE_DSN": "x", "DATABASE_URL": "y", "DATASET": "z"}

    env = ChildEnvironment(allow, python_env=_NoVenv(), source=source).build()

    assert env == {"ENGINE_MODEL": "m", "DATASET": "z"}


@pytest.mark.parametrize(
    "entry",
    [
        "VIBEY_PG_URL",
        "VIBEY_*",
        "VIB*",
        "V*",
        "*",
        "PGPASSWORD",
        "P*",
        "DATABASE_URL",
        "APP_DATABASE_URL",
        "SENTRY_DSN",
        "SMTP_PASSWORD",
    ],
)
def test_a_model_session_can_never_be_given_vibeys_own_variables_or_a_dsn(entry: str) -> None:
    with pytest.raises(ValueError, match="can never be passed"):
        _model_session(entry)


@pytest.mark.parametrize("entry", ["VIBEY_PG_URL", "VIBEY_*", "PGPASSWORD", "GIT_DIR", "GIT_*"])
def test_a_gate_can_never_be_given_vibeys_own_variables_or_git_plumbing(entry: str) -> None:
    with pytest.raises(ValueError, match="can never be passed"):
        SYSTEM_ENVIRONMENT.extended((entry,), forbidden=GATE_FORBIDDEN)


def test_a_gate_may_be_given_a_test_database_of_its_own() -> None:
    """A project's own test DSN is the operator's explicit choice for gates; only
    vibey's own variables, libpq's and git's are refused outright there."""
    allow = SYSTEM_ENVIRONMENT.extended(("TEST_DATABASE_URL",), forbidden=GATE_FORBIDDEN)

    assert allow.admits("TEST_DATABASE_URL")
    assert not allow.admits("VIBEY_PG_URL")


@pytest.mark.parametrize("entry", ["", " ", "HAS SPACE", "A=B", "*X", "X**"])
def test_a_malformed_entry_is_refused(entry: str) -> None:
    with pytest.raises(ValueError, match="not an environment variable name"):
        _model_session(entry)


def test_an_entry_list_must_be_a_list_of_strings() -> None:
    with pytest.raises(ValueError, match="must be a list of strings"):
        EnvironmentAllowList.parse("PATH", where="gates.env_allow")
    with pytest.raises(ValueError, match="must be a list of strings"):
        EnvironmentAllowList.parse(["PATH", 3], where="gates.env_allow")


def test_parse_names_where_the_bad_entry_came_from() -> None:
    with pytest.raises(ValueError, match="engine_environment.allow"):
        EnvironmentAllowList.parse(
            ["VIBEY_PG_URL"], where="engine_environment.allow", forbidden=MODEL_SESSION_FORBIDDEN
        )


def test_parse_splits_names_from_prefixes() -> None:
    allow = EnvironmentAllowList.parse(["A_NAME", "A_PREFIX_*"], where="x")

    assert allow.names == frozenset({"A_NAME"})
    assert allow.prefixes == ("A_PREFIX_",)
    assert allow.entries() == ("A_NAME", "A_PREFIX_*")


def test_extending_keeps_what_was_there_and_rechecks_it_under_the_given_rule() -> None:
    base = EnvironmentAllowList.parse(["ONE", "PRE_*"], where="x")

    extended = base.extended(["TWO", "PRE_*"], forbidden=MODEL_SESSION_FORBIDDEN)

    assert extended.entries() == ("ONE", "TWO", "PRE_*")
    assert extended.forbidden is MODEL_SESSION_FORBIDDEN


def test_an_allow_list_that_already_holds_a_forbidden_name_cannot_be_narrowed_onto_it() -> None:
    lax = EnvironmentAllowList.parse(["DATABASE_URL"], where="x", forbidden=GATE_FORBIDDEN)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        lax.extended((), forbidden=MODEL_SESSION_FORBIDDEN)


def test_the_forbidden_rules_are_exactly_these() -> None:
    assert ForbiddenEnvironment(prefixes=("VIBEY_", "PG", "GIT_")) == GATE_FORBIDDEN
    assert (
        ForbiddenEnvironment(
            prefixes=("VIBEY_", "PG"), markers=("DSN", "DATABASE_URL", "PASSWORD", "PASSWD")
        )
        == MODEL_SESSION_FORBIDDEN
    )


def test_the_system_allow_list_is_exactly_what_is_declared() -> None:
    assert set(SYSTEM_ENVIRONMENT.names) == {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "SHELL",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LANGUAGE",
        "TZ",
        "TERM",
        "COLORTERM",
        "NO_COLOR",
        "COLUMNS",
        "LINES",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
        "REQUESTS_CA_BUNDLE",
        "CURL_CA_BUNDLE",
        "NODE_EXTRA_CA_CERTS",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "NO_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "no_proxy",
        "all_proxy",
        "XDG_CONFIG_HOME",
        "XDG_CACHE_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
        "XDG_RUNTIME_DIR",
        "__CF_USER_TEXT_ENCODING",
    }
    assert SYSTEM_ENVIRONMENT.prefixes == ("LC_",)
    # Nothing in the system list is a credential or a DSN under either rule.
    for name in SYSTEM_ENVIRONMENT.names:
        assert not MODEL_SESSION_FORBIDDEN.forbids(name)
        assert not GATE_FORBIDDEN.forbids(name)


def test_the_orchestrators_venv_is_stripped_from_path_by_default() -> None:
    class _Venv:
        def interpreter_venv(self) -> str | None:
            return "/repo/.venv"

        def venv_prefixes(self) -> tuple[str | None, ...]:
            return ("/active/.venv", "/repo/.venv")

    source = {
        "PATH": "/active/.venv/bin:/repo/.venv/bin:/usr/bin",
        "VIRTUAL_ENV": "/active/.venv",
        "PYTHONPATH": "/somewhere",
    }
    allow = _model_session("VIRTUAL_ENV", "PYTHONPATH")

    env = ChildEnvironment(allow, python_env=_Venv(), source=source).build()

    assert env == {"PATH": "/usr/bin"}


def test_turning_python_isolation_off_passes_the_orchestrators_python_environment() -> None:
    source = {
        "PATH": "/repo/.venv/bin:/usr/bin",
        "VIRTUAL_ENV": "/repo/.venv",
        "VIRTUAL_ENV_PROMPT": "(vibey)",
        "PYTHONHOME": "/py",
        "PYTHONPATH": "/pp",
        "VIBEY_PG_URL": "postgresql://secret",
    }

    env = ChildEnvironment(
        SYSTEM_ENVIRONMENT, python_env=_NoVenv(), isolate_python_env=False, source=source
    ).build()

    assert env == {
        "PATH": "/repo/.venv/bin:/usr/bin",
        "VIRTUAL_ENV": "/repo/.venv",
        "VIRTUAL_ENV_PROMPT": "(vibey)",
        "PYTHONHOME": "/py",
        "PYTHONPATH": "/pp",
    }


def test_the_overlay_lands_last_and_wins() -> None:
    allow = _model_session("QWENLOOP_*")
    source = {"PATH": "/usr/bin", "QWENLOOP_MODEL": "inherited"}

    env = ChildEnvironment(
        allow,
        python_env=_NoVenv(),
        overlay={"QWENLOOP_MODEL": "q", "QWENLOOP_BASE_URL": "http://h/v1"},
        source=source,
    ).build()

    assert env == {"PATH": "/usr/bin", "QWENLOOP_MODEL": "q", "QWENLOOP_BASE_URL": "http://h/v1"}


def test_an_overlay_can_never_carry_a_forbidden_variable() -> None:
    with pytest.raises(ValueError, match="VIBEY_PG_URL"):
        ChildEnvironment(
            _model_session(), python_env=_NoVenv(), overlay={"VIBEY_PG_URL": "postgresql://x"}
        )


def test_without_a_source_the_live_environment_is_read_at_build_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    child = ChildEnvironment(_model_session("LATE_*"), python_env=_NoVenv())
    monkeypatch.setenv("LATE_VALUE", "set after construction")
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://secret")

    env = child.build()

    assert env["LATE_VALUE"] == "set after construction"
    assert "VIBEY_PG_URL" not in env


def test_the_child_exposes_the_allow_list_it_was_built_from() -> None:
    allow = _model_session("X_*")

    assert ChildEnvironment(allow, python_env=_NoVenv()).allow_list is allow


def test_without_python_env_handles_missing_path_and_no_prefixes() -> None:
    assert ChildEnvironment.without_python_env({"VIRTUAL_ENV": "/v"}, venv_prefixes=("/v",)) == {}
    assert ChildEnvironment.without_python_env(
        {"PATH": "/v/bin:/usr/bin"}, venv_prefixes=(None,)
    ) == {"PATH": "/v/bin:/usr/bin"}


def test_the_classes_satisfy_their_declared_interfaces() -> None:
    assert isinstance(SYSTEM_ENVIRONMENT, EnvironmentAllowListInterface)
    assert isinstance(ChildEnvironment(SYSTEM_ENVIRONMENT), ChildEnvironmentInterface)
    assert isinstance(GATE_FORBIDDEN, ForbiddenEnvironmentInterface)
