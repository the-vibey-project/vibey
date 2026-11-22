# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The "LLM tooling" lines `vibey connect`, `vibey doctor` and `vibey acp` print (SP-ACP).

One line per client and surface (`acp-agent`, `mcp-server`, `skill`, `plugin`), in the
`MARK name detail` grammar every other doctor section uses, so `vibey doctor --json` reads them
as findings under the names they carry (no new key in its document) and `vibey acp`'s doctor
step shows them through its own cleaning:

    PASS zed:acp-agent             present: in ~/.config/zed/settings.json
    WARN claude_code:plugin        missing: in Claude Code run /plugin marketplace add ...
    UNKNOWN cursor:skill           not-applicable: vibey ships no vibey-chat-driver skill ...

A missing surface is a `WARN`, never a `FAIL`: the section never fails doctor, and it never
raises -- a probe that breaks on what it read is one `UNKNOWN llm-tooling` line saying so. Each detail is
machine text read from files, so it is cleaned as a raised check's message is
(`DoctorChecks.cleaned`): one line, no control, format or separator character, no URL
credentials, cut at `DETAIL_CHARS` -- long enough to keep a snippet to paste whole.

Declared by `interfaces/llm_tooling_interface.py`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from vibey.application.acp.doctor_checks import DoctorChecks
from vibey.bootstrap import running_vibey
from vibey.cli.interfaces.llm_tooling_interface import LlmToolingSectionInterface
from vibey.infrastructure.mcp.interfaces.llm_tooling_probe_interface import (
    LlmToolingProbeInterface,
)
from vibey.infrastructure.mcp.llm_tooling_probe import LlmToolingProbe

NAME: Final = "llm-tooling"
DETAIL_CHARS: Final = 600


class LlmToolingSection:
    """Declared by `interfaces/llm_tooling_interface.py::LlmToolingSectionInterface`."""

    def __init__(self, probe: LlmToolingProbeInterface) -> None:
        self._probe = probe

    def lines(self, client_ids: Sequence[str] | None = None) -> list[str]:
        try:
            found = self._probe.findings(client_ids)
        except Exception as exc:  # noqa: BLE001 - the section never fails doctor, whatever it read
            reason = DoctorChecks.cleaned(f"{type(exc).__name__}: {exc}", limit=DETAIL_CHARS)
            return [f"UNKNOWN {NAME:<26} could not read the clients' configurations ({reason})"]
        if not found:
            return [f"UNKNOWN {NAME:<26} no supported LLM client is installed here"]
        return [
            f"{finding.mark} {finding.name:<26} {finding.state}: "
            f"{DoctorChecks.cleaned(finding.detail, limit=DETAIL_CHARS)}"
            for finding in found
        ]

    def doctor_lines(self) -> tuple[list[str], bool]:
        return self.lines(), True


LLM_TOOLING_SECTION: Final[LlmToolingSectionInterface] = LlmToolingSection(
    LlmToolingProbe(launcher=lambda: running_vibey())
)
"""Every detected client's surfaces, judged against the entry `vibey connect` writes with the
running install's own launcher (`bootstrap.running_vibey`)."""
