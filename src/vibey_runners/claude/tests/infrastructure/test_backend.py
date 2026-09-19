# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""infrastructure/backend.py — profile tables, environment resolution, and the
per-session backend history resume reads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claudeloop.domain.backend import BackendIdentity, BackendProfile
from claudeloop.domain.errors import BackendProfileError
from claudeloop.infrastructure.backend import (
    BackendEnvironmentResolver,
    BackendProfileLoader,
    RunBackendHistory,
)
from claudeloop.infrastructure.interfaces import (
    BackendEnvironmentResolverInterface,
    BackendProfileLoaderInterface,
    RunBackendHistoryInterface,
)
from claudeloop.infrastructure.rundir import RunDirectory, runs_root_for

OLLAMA = "http://127.0.0.1:11434"
_TIERS = {
    "base_url": OLLAMA,
    "model_low": "qwen2.5-coder:14b",
    "model_medium": "qwen2.5-coder:14b",
    "model_high": "qwen2.5-coder:32b",
}


# --- BackendProfileLoader ---


def test_parse_builds_every_key_with_its_type() -> None:
    table = {
        "local": {
            **_TIERS,
            "auth_token": "tok",
            "small_fast_model": "qwen2.5-coder:1.5b",
            "subagent_model": "qwen2.5-coder:7b",
            "context_window": 32768,
            "max_output_tokens": 8192,
            "cost_mode": "zero",
            "pass_effort": False,
            "disable_nonessential_traffic": True,
            "done_marker_fallback": True,
            "cli_path": "/opt/claude",
            "extra_env": {"CLAUDE_CODE_MAX_RETRIES": 2, "OLLAMA_KEEP_ALIVE": "30m"},
        }
    }
    profile = BackendProfileLoader().parse(table, source="claudeloop.toml")["local"]
    assert profile == BackendProfile(
        name="local",
        **_TIERS,
        auth_token="tok",
        small_fast_model="qwen2.5-coder:1.5b",
        subagent_model="qwen2.5-coder:7b",
        context_window=32768,
        max_output_tokens=8192,
        cost_mode="zero",
        pass_effort=False,
        disable_nonessential_traffic=True,
        done_marker_fallback=True,
        cli_path="/opt/claude",
        extra_env=(("CLAUDE_CODE_MAX_RETRIES", "2"), ("OLLAMA_KEEP_ALIVE", "30m")),
    )


@pytest.mark.parametrize(
    ("table", "message"),
    [
        ("not-a-table", r"\[profiles\] in f.toml must be a table of tables"),
        ({"local": "x"}, r"\[profiles.local\] in f.toml must be a table"),
        ({"local": {**_TIERS, "baseurl": "x"}}, "unknown key 'baseurl'"),
        ({"local": {**_TIERS, "model_low": 5}}, "model_low must be a string"),
        ({"local": {**_TIERS, "context_window": "big"}}, "context_window must be an integer"),
        ({"local": {**_TIERS, "context_window": True}}, "context_window must be an integer"),
        ({"local": {**_TIERS, "pass_effort": "no"}}, "pass_effort must be true or false"),
        ({"local": {**_TIERS, "extra_env": "A=1"}}, "extra_env must be a table"),
        ({"local": {**_TIERS, "extra_env": {"A": True}}}, "extra_env.A must be a string"),
        ({"local": {**_TIERS, "extra_env": {"A": {"x": 1}}}}, "extra_env.A must be a string"),
        ({"local": {"base_url": OLLAMA}}, "missing model_low, model_medium, model_high"),
    ],
)
def test_parse_refuses_what_it_cannot_trust(table: object, message: str) -> None:
    with pytest.raises(BackendProfileError, match=message):
        BackendProfileLoader().parse(table, source="f.toml")


def test_select_without_a_name_is_anthropic() -> None:
    loader = BackendProfileLoader()
    assert loader.select({}, None) == BackendProfile()
    assert loader.select({}, "  ") == BackendProfile()


def test_select_the_builtin_anthropic_name() -> None:
    assert BackendProfileLoader().select({}, "anthropic") == BackendProfile()


def test_select_a_defined_profile_by_name() -> None:
    local = BackendProfile(name="local", **_TIERS)
    assert BackendProfileLoader().select({"local": local}, " local ") is local


def test_select_an_undefined_profile_lists_the_defined_ones() -> None:
    local = BackendProfile(name="local", **_TIERS)
    with pytest.raises(BackendProfileError, match=r"unknown profile 'olama' \(defined: local\)"):
        BackendProfileLoader().select({"local": local}, "olama")


def test_select_an_undefined_profile_when_none_are_defined() -> None:
    with pytest.raises(BackendProfileError, match="none are defined"):
        BackendProfileLoader().select({}, "local")


# --- BackendEnvironmentResolver ---


def test_anthropic_profile_has_no_token_and_a_plain_identity() -> None:
    resolver = BackendEnvironmentResolver({})
    assert resolver.auth_token(BackendProfile()) == ""
    assert resolver.identity(BackendProfile()) == BackendIdentity()


def test_ambient_base_url_is_recorded_as_a_gateway_not_ignored() -> None:
    resolver = BackendEnvironmentResolver({"ANTHROPIC_BASE_URL": "https://proxy.corp/"})
    assert str(resolver.identity(BackendProfile())) == "gateway:https://proxy.corp"


def test_local_profile_uses_its_static_token() -> None:
    profile = BackendProfile(name="local", **_TIERS)
    resolver = BackendEnvironmentResolver({})
    assert resolver.auth_token(profile) == "ollama"
    runtime = resolver.runtime(profile)
    assert runtime.environment()["ANTHROPIC_AUTH_TOKEN"] == "ollama"
    assert runtime.environment()["ANTHROPIC_API_KEY"] == ""
    assert str(resolver.identity(profile)) == f"local:{OLLAMA}"


def test_local_profile_reads_its_token_from_the_named_variable() -> None:
    profile = BackendProfile(name="gpu", auth_token_env="GPU_TOKEN", **_TIERS)
    resolver = BackendEnvironmentResolver({"GPU_TOKEN": "s3cret"})
    assert resolver.auth_token(profile) == "s3cret"
    assert resolver.try_auth_token(profile) == "s3cret"


@pytest.mark.parametrize("environ", [{}, {"GPU_TOKEN": "  "}])
def test_unset_token_variable_is_refused(environ: dict[str, str]) -> None:
    profile = BackendProfile(name="gpu", auth_token_env="GPU_TOKEN", **_TIERS)
    resolver = BackendEnvironmentResolver(environ)
    with pytest.raises(BackendProfileError, match=r"\$GPU_TOKEN, which is unset or empty"):
        resolver.auth_token(profile)
    assert resolver.try_auth_token(profile) is None


def test_resolver_defaults_to_the_process_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://from-env.example")
    assert str(BackendEnvironmentResolver().identity(BackendProfile())) == (
        "gateway:https://from-env.example"
    )


# --- RunBackendHistory ---


def _run(cwd: Path, run_id: str, **meta: object) -> RunDirectory:
    directory = RunDirectory.create(runs_root_for(cwd), cwd=cwd, run_id=run_id)
    directory.update_meta(**meta)
    return directory


def test_history_is_empty_without_any_runs(tmp_path: Path) -> None:
    assert RunBackendHistory(tmp_path).last_backend("sess") is None


def test_history_returns_the_most_recent_recorded_backend_for_the_session(
    tmp_path: Path,
) -> None:
    _run(
        tmp_path,
        "a-old",
        session_id="sess",
        backend="anthropic",
        started_at="2026-09-01T00:00:00+00:00",
    )
    _run(
        tmp_path,
        "b-new",
        session_id="sess",
        backend=f"local:{OLLAMA}",
        started_at="2026-09-02T00:00:00+00:00",
    )
    _run(
        tmp_path,
        "c-other",
        session_id="other",
        backend="anthropic",
        started_at="2026-09-03T00:00:00+00:00",
    )
    _run(tmp_path, "d-legacy", session_id="sess", started_at="2026-09-04T00:00:00+00:00")
    last = RunBackendHistory(tmp_path).last_backend("sess")
    assert last is not None
    assert str(last) == f"local:{OLLAMA}"


def test_history_without_a_recorded_run_for_this_session(tmp_path: Path) -> None:
    _run(tmp_path, "other", session_id="other", backend="anthropic")
    _run(tmp_path, "legacy", session_id="sess")
    assert RunBackendHistory(tmp_path).last_backend("sess") is None


def test_history_ignores_run_dirs_it_cannot_read(tmp_path: Path) -> None:
    root = runs_root_for(tmp_path)
    root.mkdir(parents=True)
    (root / "no-meta").mkdir()
    (root / "stray-file").write_text("x")
    broken = root / "broken"
    broken.mkdir()
    (broken / "meta.json").write_text("{not json")
    partial = root / "partial"
    partial.mkdir()
    (partial / "meta.json").write_text(json.dumps({"run_id": "partial"}))
    _run(tmp_path, "good", session_id="sess", backend="anthropic")
    assert RunBackendHistory(tmp_path).last_backend("sess") == BackendIdentity()


def test_history_refuses_a_corrupt_identity_rather_than_guessing(tmp_path: Path) -> None:
    _run(tmp_path, "weird", session_id="sess", backend="mystery")
    with pytest.raises(BackendProfileError, match="unrecognised backend identity"):
        RunBackendHistory(tmp_path).last_backend("sess")


def test_every_infrastructure_backend_class_satisfies_its_interface(tmp_path: Path) -> None:
    assert isinstance(BackendProfileLoader(), BackendProfileLoaderInterface)
    assert isinstance(BackendEnvironmentResolver({}), BackendEnvironmentResolverInterface)
    assert isinstance(RunBackendHistory(tmp_path), RunBackendHistoryInterface)
