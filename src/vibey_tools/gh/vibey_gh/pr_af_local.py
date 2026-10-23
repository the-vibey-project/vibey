# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Point Agent-Field `pr-af` at a model the operator serves, instead of OpenRouter.

pr-af has one model setting (`PR_AF_MODEL`) used by every one of its agents, and a container
entrypoint that writes an opencode configuration naming only OpenRouter. Reaching a local
server therefore takes three things, all of them configuration: the opencode harness in
place of the default one, an opencode provider for the server's OpenAI-compatible endpoint,
and an entrypoint that writes that provider instead of the OpenRouter one.

This module renders exactly that as a `docker-compose.override.yml`, which compose loads
beside the pinned checkout's own file. Third-party code is never patched -- it stays the
bytes at the pinned SHA -- and the override is a reviewed, tested artefact of this
repository. It also blanks `OPENROUTER_API_KEY` inside the container: a review declared
local must not be able to reach the paid router even by accident.

The server is the sovereign lane's by default (`[pr_automation.fallback]`), so one
declaration of "which local model, where" serves both lanes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TextIO
from urllib.parse import urlsplit, urlunsplit

from vibey_gh.config import GhConfig, load_config
from vibey_gh.interfaces.pr_af_local_interface import PrAfLocalModelInterface

__all__ = ["PrAfLocalCommand", "PrAfLocalModel", "main"]

OVERRIDE_NAME = "docker-compose.override.yml"
# What a container calls the machine it runs on. A loopback address inside a container is
# the container itself, so a server declared at 127.0.0.1 is rewritten to this.
_HOST_ALIAS = "host.docker.internal"
_LOOPBACK = frozenset({"127.0.0.1", "localhost", "0.0.0.0", "::1"})
# opencode reads this id for its provider, and litellm (pr-af's direct `ai` path) reads the
# `ollama_chat/` prefix. Same model, two clients, two spellings.
_PROVIDER_ID = "ollama"
_LITELLM_PREFIX = "ollama_chat"

# Written once, run by the container's shell. `$@` is the image's own command, restated in
# the override because compose drops an image's CMD when the entrypoint is replaced.
_ENTRYPOINT = (
    'dir="${XDG_CONFIG_HOME:-$HOME/.config}/opencode"; '
    'mkdir -p "$dir"; '
    'printf \'%s\' "$OPENCODE_CONFIG_JSON" > "$dir/opencode.json"; '
    'exec "$@"'
)


def _escape(text: str) -> str:
    """Compose reads `$name` as interpolation, so every literal dollar is doubled."""
    return text.replace("$", "$$")


def _scalar(text: str) -> str:
    """A YAML double-quoted scalar. JSON strings are valid YAML, and are escaped for compose."""
    return json.dumps(_escape(text))


class PrAfLocalModel(PrAfLocalModelInterface):
    """The local model a host-venue review uses, and the override that wires it in."""

    def __init__(self, cfg: GhConfig) -> None:
        self._cfg = cfg

    @property
    def model(self) -> str:
        return self._cfg.pr_automation.pr_af.local_model or self._cfg.pr_automation.fallback.model

    @property
    def base_url(self) -> str:
        pr_af = self._cfg.pr_automation.pr_af
        return pr_af.local_base_url or self._cfg.pr_automation.fallback.base_url

    @property
    def container_base_url(self) -> str:
        parts = urlsplit(self.base_url.rstrip("/"))
        if parts.hostname not in _LOOPBACK:
            return urlunsplit(parts)
        port = f":{parts.port}" if parts.port else ""
        return urlunsplit(parts._replace(netloc=f"{_HOST_ALIAS}{port}"))

    def opencode_config(self) -> dict[str, object]:
        """The opencode configuration naming only this server, never OpenRouter."""
        window = self._cfg.pr_automation.fallback.context_window
        qualified = f"{_PROVIDER_ID}/{self.model}"
        return {
            "$schema": "https://opencode.ai/config.json",
            "model": qualified,
            "small_model": qualified,
            "provider": {
                _PROVIDER_ID: {
                    "npm": "@ai-sdk/openai-compatible",
                    "name": "Local model server",
                    "options": {"baseURL": f"{self.container_base_url}/v1"},
                    "models": {
                        self.model: {
                            "name": self.model,
                            "limit": {"context": window, "output": max(1, window // 4)},
                        }
                    },
                }
            },
        }

    def compose_override(self) -> str:
        environment = {
            "PR_AF_PROVIDER": "opencode",
            "PR_AF_MODEL": f"{_PROVIDER_ID}/{self.model}",
            "PR_AF_AI_MODEL": f"{_LITELLM_PREFIX}/{self.model}",
            "OLLAMA_API_BASE": self.container_base_url,
            # Blanked, not omitted: the base file passes the host's value through, and a
            # review declared local must never be able to reach the paid router.
            "OPENROUTER_API_KEY": "",
            "OPENCODE_CONFIG_JSON": json.dumps(self.opencode_config(), separators=(",", ":")),
        }
        lines = [
            "# Generated by `python -m vibey_gh.pr_af_local` -- pr-af on a local model.",
            "services:",
            "  pr-af:",
            "    extra_hosts:",
            f"      - {_scalar(f'{_HOST_ALIAS}:host-gateway')}",
            "    entrypoint:",
            "      - /bin/sh",
            "      - -c",
            f"      - {_scalar(_ENTRYPOINT)}",
            "      - --",
            '    command: ["python", "-m", "pr_af.app"]',
            "    environment:",
            *(f"      {name}: {_scalar(value)}" for name, value in environment.items()),
        ]
        return "\n".join(lines) + "\n"

    def write_override(self, directory: Path) -> Path:
        path = directory / OVERRIDE_NAME
        path.write_text(self.compose_override(), encoding="utf-8")
        return path


class PrAfLocalCommand:
    """The workflow step: write the override beside the pinned checkout, say which model."""

    def __init__(
        self,
        cfg: GhConfig | None = None,
        *,
        directory: Path,
        env: Mapping[str, str] | None = None,
        out: TextIO = sys.stdout,
    ) -> None:
        self._cfg = cfg or load_config()
        self._directory = directory
        self._env = env if env is not None else os.environ
        self._out = out

    def run(self) -> int:
        pr_af = self._cfg.pr_automation.pr_af
        if not (pr_af.enabled and pr_af.host_provider == "local"):
            print(
                'pr-af: the host venue is not declared local (host_provider = "local")',
                file=sys.stderr,
            )
            return 2
        if not self._directory.is_dir():
            print(f"pr-af: no checkout at {self._directory}", file=sys.stderr)
            return 2
        local = PrAfLocalModel(self._cfg)
        path = local.write_override(self._directory)
        print(
            json.dumps(
                {"model": local.model, "server": local.container_base_url, "path": str(path)}
            ),
            file=self._out,
        )
        self._summarise(local)
        return 0

    def _summarise(self, local: PrAfLocalModelInterface) -> None:
        target = self._env.get("GITHUB_STEP_SUMMARY")
        if not target:
            return
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(
                "### pr-af local model\n\n"
                f"- Model: `{local.model}` (no OpenRouter key is passed to the container)\n"
                f"- Server, from the container: `{local.container_base_url}`\n"
            )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m vibey_gh.pr_af_local")
    parser.add_argument("--directory", required=True, type=Path, help="the pr-af checkout")
    args = parser.parse_args(argv)
    return PrAfLocalCommand(load_config(), directory=args.directory).run()


if __name__ == "__main__":
    raise SystemExit(main())
