# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""pr-af on a local model: the venue-to-provider declaration, the compose override, the command."""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from vibey_gh import pr_af, pr_af_local
from vibey_gh.config import (
    GhConfig,
    PrAfConfig,
    PrAutomationConfig,
    PrAutomationFallbackConfig,
)
from vibey_gh.install import WORKFLOWS, installation_notices, render_workflow

SHA = "421fbd23bf1c5a2c3916d7046c97b5273958e1f4"


def cfg(tmp_path: Path, *, fallback: dict[str, Any] | None = None, **pr_af_config: Any) -> GhConfig:
    return GhConfig(
        root=tmp_path,
        pr_automation=PrAutomationConfig(
            pr_af=PrAfConfig(**pr_af_config),
            fallback=PrAutomationFallbackConfig(**(fallback or {})),
        ),
    )


def local(tmp_path: Path, **overrides: Any) -> GhConfig:
    return cfg(
        tmp_path,
        enabled=True,
        ref=SHA,
        host_enabled=True,
        host_provider="local",
        **overrides,
    )


# --- the declaration --------------------------------------------------------------------


def test_the_default_declaration_still_means_openrouter_on_both_venues() -> None:
    value = PrAfConfig(enabled=True, ref=SHA)
    assert value.hosted_enabled is True
    assert value.host_provider == "openrouter"
    assert value.needs_openrouter is True


def test_a_local_host_with_a_hosted_venue_still_needs_the_router_secret() -> None:
    value = PrAfConfig(enabled=True, ref=SHA, host_enabled=True, host_provider="local")
    assert value.needs_openrouter is True


def test_a_local_only_declaration_needs_no_router_secret() -> None:
    value = PrAfConfig(
        enabled=True, ref=SHA, host_enabled=True, host_provider="local", hosted_enabled=False
    )
    assert value.needs_openrouter is False


def test_an_openrouter_host_without_a_hosted_venue_needs_the_secret() -> None:
    value = PrAfConfig(enabled=True, ref=SHA, host_enabled=True, hosted_enabled=False)
    assert value.needs_openrouter is True


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"hosted_enabled": False}, "at least one venue"),
        ({"host_provider": "gemini"}, "host_provider must be one of"),
        ({"host_provider": "local"}, 'host_provider = "local" needs host_enabled'),
        ({"local_model": "bad model!"}, "local_model is not a model id"),
        ({"local_base_url": "ftp://x"}, "local_base_url must be an http"),
        ({"local_base_url": "http://"}, "local_base_url must be an http"),
        ({"hosted_enabled": "yes"}, "hosted_enabled must be true or false"),
    ],
)
def test_the_declaration_refuses_what_it_cannot_honour(
    changes: dict[str, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        PrAfConfig(enabled=True, ref=SHA, **changes)


def test_a_local_verdict_does_not_pass_the_gate_alone_by_default() -> None:
    assert PrAfConfig(enabled=True, ref=SHA).local_verdict_passes is False


def test_the_local_verdict_switch_must_be_a_boolean() -> None:
    with pytest.raises(ValueError, match="local_verdict_passes must be true or false"):
        PrAfConfig(enabled=True, ref=SHA, local_verdict_passes="yes")


def test_an_undeclared_table_validates_nothing_else() -> None:
    PrAfConfig(host_provider="gemini", hosted_enabled=False)


def test_the_table_reads_the_new_keys() -> None:
    value = PrAfConfig.from_table(
        {
            "enabled": True,
            "ref": SHA,
            "host_enabled": True,
            "host_provider": "local",
            "local_model": "qwen3:14b",
            "local_base_url": "http://10.0.0.5:11434",
            "hosted_enabled": False,
        }
    )
    assert value.local_model == "qwen3:14b"
    assert value.hosted_enabled is False


# --- the model and the address the container uses ---------------------------------------


def test_the_local_model_defaults_to_the_fallback_lanes_model(tmp_path: Path) -> None:
    renderer = pr_af_local.PrAfLocalModel(local(tmp_path, fallback={"model": "gpt-oss:20b"}))
    assert renderer.model == "gpt-oss:20b"


def test_a_declared_local_model_wins_over_the_fallback_lane(tmp_path: Path) -> None:
    renderer = pr_af_local.PrAfLocalModel(local(tmp_path, local_model="qwen3:14b"))
    assert renderer.model == "qwen3:14b"


@pytest.mark.parametrize(
    ("declared", "seen_from_the_container"),
    [
        ("http://127.0.0.1:11434", "http://host.docker.internal:11434"),
        ("http://localhost:11434/", "http://host.docker.internal:11434"),
        ("http://0.0.0.0:11434", "http://host.docker.internal:11434"),
        ("http://[::1]:11434", "http://host.docker.internal:11434"),
        ("http://127.0.0.1", "http://host.docker.internal"),
        ("https://ollama.lan:8443/", "https://ollama.lan:8443"),
    ],
)
def test_a_loopback_address_is_rewritten_for_the_container(
    tmp_path: Path, declared: str, seen_from_the_container: str
) -> None:
    renderer = pr_af_local.PrAfLocalModel(local(tmp_path, local_base_url=declared))
    assert renderer.container_base_url == seen_from_the_container


def test_the_address_defaults_to_the_fallback_lanes(tmp_path: Path) -> None:
    renderer = pr_af_local.PrAfLocalModel(
        local(tmp_path, fallback={"base_url": "http://localhost:9999"})
    )
    assert renderer.container_base_url == "http://host.docker.internal:9999"


# --- the compose override ---------------------------------------------------------------


def unescaped(value: Any) -> Any:
    """What compose hands the container: it turns every `$$` back into a literal `$`."""
    if isinstance(value, str):
        return value.replace("$$", "$")
    if isinstance(value, list):
        return [unescaped(item) for item in value]
    if isinstance(value, dict):
        return {key: unescaped(item) for key, item in value.items()}
    return value


def override(tmp_path: Path, **overrides: Any) -> dict[str, Any]:
    text = pr_af_local.PrAfLocalModel(local(tmp_path, **overrides)).compose_override()
    return unescaped(yaml.safe_load(text)["services"]["pr-af"])


def test_the_override_selects_the_opencode_harness_and_the_local_model(tmp_path: Path) -> None:
    service = override(tmp_path)
    env = service["environment"]
    assert env["PR_AF_PROVIDER"] == "opencode"
    assert env["PR_AF_MODEL"] == "ollama/gpt-oss:20b"
    assert env["PR_AF_AI_MODEL"] == "ollama_chat/gpt-oss:20b"
    assert env["OLLAMA_API_BASE"] == "http://host.docker.internal:11434"


def test_the_override_never_lets_the_router_key_reach_a_local_review(tmp_path: Path) -> None:
    assert override(tmp_path)["environment"]["OPENROUTER_API_KEY"] == ""


def test_the_override_lets_a_linux_host_resolve_the_docker_gateway(tmp_path: Path) -> None:
    assert "host.docker.internal:host-gateway" in override(tmp_path)["extra_hosts"]


def test_the_override_replaces_the_entrypoint_that_only_knows_openrouter(tmp_path: Path) -> None:
    service = override(tmp_path)
    assert service["entrypoint"][:2] == ["/bin/sh", "-c"]
    assert "opencode.json" in service["entrypoint"][2]
    assert 'exec "$@"' in service["entrypoint"][2]
    # The image's CMD is dropped when the entrypoint is overridden, so it is restated.
    assert service["command"] == ["python", "-m", "pr_af.app"]


def test_the_override_writes_an_opencode_config_for_an_openai_compatible_endpoint(
    tmp_path: Path,
) -> None:
    service = override(tmp_path, fallback={"context_window": 49152})
    config = json.loads(service["environment"]["OPENCODE_CONFIG_JSON"])
    assert config["model"] == "ollama/gpt-oss:20b"
    assert config["small_model"] == "ollama/gpt-oss:20b"
    provider = config["provider"]["ollama"]
    assert provider["npm"] == "@ai-sdk/openai-compatible"
    assert provider["options"]["baseURL"] == "http://host.docker.internal:11434/v1"
    assert provider["models"]["gpt-oss:20b"]["limit"]["context"] == 49152
    assert "openrouter" not in config["provider"]


def test_every_dollar_is_escaped_so_compose_interpolates_nothing(tmp_path: Path) -> None:
    text = pr_af_local.PrAfLocalModel(local(tmp_path)).compose_override()
    # `$schema` in the opencode config and `$HOME`/`$@` in the entrypoint are literal.
    stripped = text.replace("$$", "")
    assert "$" not in stripped


def test_the_override_is_written_where_compose_loads_it_automatically(tmp_path: Path) -> None:
    target = tmp_path / "pr-af"
    target.mkdir()
    path = pr_af_local.PrAfLocalModel(local(tmp_path)).write_override(target)
    assert path == target / "docker-compose.override.yml"
    assert yaml.safe_load(path.read_text())["services"]["pr-af"]["environment"]


# --- the command ------------------------------------------------------------------------


def test_the_command_writes_the_override_and_names_it(tmp_path: Path) -> None:
    target = tmp_path / "pr-af"
    target.mkdir()
    out = io.StringIO()
    code = pr_af_local.PrAfLocalCommand(local(tmp_path), directory=target, env={}, out=out).run()
    assert code == 0
    assert (target / "docker-compose.override.yml").is_file()
    assert "gpt-oss:20b" in out.getvalue()


def test_the_command_writes_the_step_summary_when_asked(tmp_path: Path) -> None:
    target = tmp_path / "pr-af"
    target.mkdir()
    summary = tmp_path / "summary"
    pr_af_local.PrAfLocalCommand(
        local(tmp_path),
        directory=target,
        env={"GITHUB_STEP_SUMMARY": str(summary)},
        out=io.StringIO(),
    ).run()
    assert "local model" in summary.read_text()


def test_the_command_refuses_when_the_host_is_not_declared_local(tmp_path: Path) -> None:
    target = tmp_path / "pr-af"
    target.mkdir()
    out = io.StringIO()
    code = pr_af_local.PrAfLocalCommand(
        cfg(tmp_path, enabled=True, ref=SHA, host_enabled=True),
        directory=target,
        env={},
        out=out,
    ).run()
    assert code == 2
    assert not (target / "docker-compose.override.yml").exists()


def test_the_command_refuses_a_directory_that_is_not_there(tmp_path: Path) -> None:
    code = pr_af_local.PrAfLocalCommand(
        local(tmp_path), directory=tmp_path / "missing", env={}, out=io.StringIO()
    ).run()
    assert code == 2


def test_the_module_entry_point_reads_the_directory_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "pr-af"
    target.mkdir()
    monkeypatch.setattr(pr_af_local, "load_config", lambda: local(tmp_path))
    assert pr_af_local.main(["--directory", str(target)]) == 0
    assert (target / "docker-compose.override.yml").is_file()


# --- the verdict names the model that actually reviewed ---------------------------------


class FakeClient:
    def review(self, pr_url: str, **kwargs: Any) -> pr_af.PrAfVerdict:
        return pr_af.PrAfVerdict(True, reason="clean")


def outputs(tmp_path: Path, venue: str, config: GhConfig) -> dict[str, str]:
    target = tmp_path / "output"
    target.write_text("")
    pr_af.PrAfCommand(
        config,
        client=FakeClient(),
        env={
            "PR_URL": "https://github.com/o/r/pull/1",
            "PR_AF_VENUE": venue,
            "GITHUB_OUTPUT": str(target),
        },
        out=io.StringIO(),
    ).run()
    return dict(line.split("=", 1) for line in target.read_text().splitlines())


def test_the_host_venue_reports_the_local_model(tmp_path: Path) -> None:
    assert outputs(tmp_path, "host", local(tmp_path))["model"] == "gpt-oss:20b"


def test_the_hosted_venue_reports_the_router_model(tmp_path: Path) -> None:
    assert (
        outputs(tmp_path, "hosted", local(tmp_path))["model"] == "deepseek/deepseek-v4-flash-0731"
    )


def test_an_openrouter_host_reports_the_router_model(tmp_path: Path) -> None:
    config = cfg(tmp_path, enabled=True, ref=SHA, host_enabled=True)
    assert outputs(tmp_path, "host", config)["model"] == "deepseek/deepseek-v4-flash-0731"


def test_the_step_summary_names_the_local_model(tmp_path: Path) -> None:
    summary = tmp_path / "summary"
    command = pr_af.PrAfCommand(
        local(tmp_path), env={"GITHUB_STEP_SUMMARY": str(summary)}, out=io.StringIO()
    )
    command._write_summary(pr_af.PrAfVerdict(True, reason="clean"), "host")
    assert "`gpt-oss:20b`" in summary.read_text()


# --- the rendered workflow --------------------------------------------------------------


def render(tmp_path: Path, **overrides: Any) -> str:
    return render_workflow(WORKFLOWS / "pr-review.yml", local(tmp_path, **overrides))


def job(text: str, name: str) -> str:
    start = text.index(f"\n  {name}:\n")
    end = text.index("\n  review:\n", start)
    return text[start:end]


def test_a_local_host_probes_the_model_server_instead_of_reading_the_secret(
    tmp_path: Path,
) -> None:
    host = job(render(tmp_path), "review-pr-af-host")
    assert "PR_AF_HOST_PROVIDER: local" in host
    assert "/api/tags" in host
    assert "secrets.OPENROUTER_API_KEY" not in host
    assert "vibey_gh.pr_af_local" in host
    assert "__VIBEY_GH_" not in host


def test_an_openrouter_host_keeps_reading_the_secret(tmp_path: Path) -> None:
    text = render_workflow(
        WORKFLOWS / "pr-review.yml",
        cfg(tmp_path, enabled=True, ref=SHA, host_enabled=True),
    )
    host = job(text, "review-pr-af-host")
    assert "PR_AF_HOST_PROVIDER: openrouter" in host
    assert "secrets.OPENROUTER_API_KEY" in host


def test_the_hosted_venue_is_unscheduled_when_it_is_not_declared(tmp_path: Path) -> None:
    text = render(tmp_path, hosted_enabled=False)
    hosted = job(text, "review-pr-af")
    assert "false &&" in hosted.split("runs-on:")[0]
    assert "__VIBEY_GH_" not in text


def test_the_hosted_venue_stays_scheduled_by_default(tmp_path: Path) -> None:
    hosted = job(render(tmp_path), "review-pr-af")
    assert "true &&" in hosted.split("runs-on:")[0]


def test_the_gate_names_the_model_the_job_reported(tmp_path: Path) -> None:
    text = render(tmp_path)
    assert (
        "PR_AF_MODEL: ${{ needs.review-pr-af.outputs.model || "
        "needs.review-pr-af-host.outputs.model }}"
    ) in text


def test_the_gate_lets_a_local_model_block_but_not_pass_by_default(tmp_path: Path) -> None:
    text = render(tmp_path)
    assert "PR_AF_LOCAL_DEFERS: ${{ needs.review-pr-af-host.outputs.venue == 'host' }}" in text
    assert "a local model may block the gate but does not pass it alone" in text
    # The block branch is untouched: a local model's finding still fails the gate.
    assert "pr-af found blocking findings" in text


def test_the_gate_lets_a_local_pass_count_once_the_repository_opts_in(tmp_path: Path) -> None:
    assert "PR_AF_LOCAL_DEFERS: false" in render(tmp_path, local_verdict_passes=True)


def test_a_router_host_never_defers_its_pass(tmp_path: Path) -> None:
    text = render_workflow(
        WORKFLOWS / "pr-review.yml", cfg(tmp_path, enabled=True, ref=SHA, host_enabled=True)
    )
    assert "PR_AF_LOCAL_DEFERS: false" in text


def test_a_local_only_declaration_asks_for_no_router_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: subprocess.CompletedProcess([], 0, "[]", "")
    )
    notices = installation_notices(local(tmp_path, hosted_enabled=False))
    assert not any("OPENROUTER_API_KEY" in item for item in notices)
    both = installation_notices(local(tmp_path))
    assert any("OPENROUTER_API_KEY" in item for item in both)
