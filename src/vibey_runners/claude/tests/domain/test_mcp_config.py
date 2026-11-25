# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""domain/mcp_config.py — a snapshot MCP server as an SDK config with an explicit transport; a
local one starts through the scrubbed launcher (SP-LOOPS Phase 4, Task 5; R7)."""

from __future__ import annotations

import pytest
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec

from claudeloop.domain.interfaces import McpConfigTranslatorInterface
from claudeloop.domain.mcp_config import McpConfigTranslator

LAUNCHER = ("/usr/bin/python3", "-m", "vibey_runners.common.capabilities.scrubbed_exec")


def _local(*env_allow: str) -> McpServerSpec:
    return McpServerSpec(
        name="files",
        trust="local",
        command=("npx", "-y", "@scope/files-server", "--root", "."),
        url=None,
        env_allow=env_allow,
    )


def _remote() -> McpServerSpec:
    return McpServerSpec(
        name="docs",
        trust="remote",
        command=None,
        url="https://docs.example.invalid/mcp",
        env_allow=(),
    )


def test_the_translator_satisfies_its_interface() -> None:
    assert isinstance(McpConfigTranslator(LAUNCHER), McpConfigTranslatorInterface)


def test_a_local_server_is_stdio_through_the_launcher_with_no_env_key() -> None:
    config = McpConfigTranslator(LAUNCHER).translate(_local("FILES_ROOT", "FILES_TOKEN_NAME"))
    assert config == {
        "type": "stdio",
        "command": "/usr/bin/python3",
        "args": [
            "-m",
            "vibey_runners.common.capabilities.scrubbed_exec",
            "--allow",
            "FILES_ROOT",
            "--allow",
            "FILES_TOKEN_NAME",
            "--",
            "npx",
            "-y",
            "@scope/files-server",
            "--root",
            ".",
        ],
    }
    assert "env" not in config


def test_a_local_server_with_nothing_allowed_gets_no_allow_flag() -> None:
    config = McpConfigTranslator(LAUNCHER).translate(_local())
    assert config["args"] == [
        "-m",
        "vibey_runners.common.capabilities.scrubbed_exec",
        "--",
        "npx",
        "-y",
        "@scope/files-server",
        "--root",
        ".",
    ]
    assert "env" not in config


def test_a_one_word_launcher_puts_only_the_allow_flags_before_the_command() -> None:
    config = McpConfigTranslator(("/opt/vibey/scrubbed-exec",)).translate(_local("A"))
    assert config["command"] == "/opt/vibey/scrubbed-exec"
    assert config["args"] == [
        "--allow",
        "A",
        "--",
        "npx",
        "-y",
        "@scope/files-server",
        "--root",
        ".",
    ]


def test_a_remote_server_is_http_and_never_sse() -> None:
    config = McpConfigTranslator(LAUNCHER).translate(_remote())
    assert config == {"type": "http", "url": "https://docs.example.invalid/mcp"}
    assert config["type"] != "sse"


def test_every_server_has_an_explicit_type() -> None:
    translator = McpConfigTranslator(LAUNCHER)
    for server in (_local(), _local("A"), _remote()):
        config = translator.translate(server)
        assert config["type"] in {"stdio", "http"}


def test_each_translation_is_a_fresh_dict() -> None:
    translator = McpConfigTranslator(LAUNCHER)
    first = translator.translate(_local("A"))
    first["args"].append("--extra")  # type: ignore[attr-defined]
    assert "--extra" not in translator.translate(_local("A"))["args"]  # type: ignore[operator]


@pytest.mark.parametrize(
    "server",
    [
        McpServerSpec(name="x", trust="local", command=None, url=None, env_allow=()),
        McpServerSpec(name="x", trust="local", command=(), url=None, env_allow=()),
        McpServerSpec(name="x", trust="remote", command=None, url=None, env_allow=()),
        McpServerSpec(
            name="x",
            trust="other",  # type: ignore[arg-type]
            command=("a",),
            url="https://x.invalid",
            env_allow=(),
        ),
    ],
)
def test_a_spec_that_is_neither_local_nor_remote_is_refused(server: McpServerSpec) -> None:
    with pytest.raises(ValueError, match="'x'"):
        McpConfigTranslator(LAUNCHER).translate(server)


def test_an_empty_launcher_is_refused() -> None:
    with pytest.raises(ValueError, match="launcher"):
        McpConfigTranslator(())


def test_the_workers_vibey_web_connector_is_stdio_through_the_launcher_with_two_names() -> None:
    """SP-LOOPS Phase 6, Task 6 (R3): the connector the worker adds to a run that holds a web
    grant is a local server like any other, so it is typed `stdio` and started through the
    scrubbed launcher, which keeps exactly the grant's two names and nothing else."""
    connector = McpServerSpec(
        name="vibey-web",
        trust="local",
        command=("/opt/vibey/bin/vibey", "mcp", "--scope", "web", "--token-file", "/r/web-token"),
        url=None,
        env_allow=("VIBEY_HUB_URL", "VIBEY_WEB_TOKEN_FILE"),
    )
    config = McpConfigTranslator(LAUNCHER).translate(connector)
    assert config == {
        "type": "stdio",
        "command": "/usr/bin/python3",
        "args": [
            "-m",
            "vibey_runners.common.capabilities.scrubbed_exec",
            "--allow",
            "VIBEY_HUB_URL",
            "--allow",
            "VIBEY_WEB_TOKEN_FILE",
            "--",
            "/opt/vibey/bin/vibey",
            "mcp",
            "--scope",
            "web",
            "--token-file",
            "/r/web-token",
        ],
    }
    assert "env" not in config
