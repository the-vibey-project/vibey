# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a run's locked capability snapshot gives one claudeloop session (SP-LOOPS Phase 4,
Task 4; R4, R5, R6, R11).

The conductor writes the snapshot as a document in the run's own folder and names it with
`--capabilities PATH`; `infrastructure/capabilities/snapshot_applier.py` reads it strictly and
turns it into this record, which the session holds for its whole life and applies on every
connect (`infrastructure/agent/capability_overlay.py`). Pure: no I/O, no clock. Declared by
`interfaces/applied_capabilities_interface.py::AppliedCapabilitiesInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

CLAUDE_BUILTIN_WEB_TOOLS: Final = ("WebSearch", "WebFetch")
"""Claude Code's own names for its built-in web tools. This is a fact of Claude Code's tool
vocabulary, not a policy: whether they are switched off is `[loops] builtin_web` (R4), and on a
local backend they are always off, because a local backend cannot serve them (R11)."""

EXIT_CAPABILITIES_REFUSED: Final = 78
"""sysexits.h EX_CONFIG, as `backend.EXIT_BACKEND_MISCONFIGURED`: the run's capability document
was refused, so the run never started (R9). The conductor's `engine_misconfigured` gate parks
the job on it."""


@dataclass(frozen=True, slots=True)
class AppliedCapabilities:
    """Declared by `interfaces/applied_capabilities_interface.py::AppliedCapabilitiesInterface`.

    `plugin_dirs` are the run's plugin copies; `skills` the catalog's qualified names
    (`plugin:skill`); `mcp_servers` the snapshot's servers as SDK configs; `disallowed_tools` the
    tools the session may never use; `add_dirs` the run's input folders; `system_prompt_append`
    the repository's instruction text; `notices` what the person should be told about how the
    snapshot was applied; `instruction_files` the names whose text was inlined."""

    digest: str
    plugin_dirs: tuple[str, ...]
    skills: tuple[str, ...]
    mcp_servers: Mapping[str, Mapping[str, object]]
    disallowed_tools: tuple[str, ...]
    add_dirs: tuple[str, ...]
    system_prompt_append: str
    notices: tuple[str, ...]
    instruction_files: tuple[str, ...] = ()

    def event_payload(self) -> dict[str, object]:
        """The `capabilities.applied` event: the digest, counts and names only. Never a path,
        a server's configuration, an environment value or any file text."""
        return {
            "digest": self.digest,
            "plugins": len(self.plugin_dirs),
            "skills": len(self.skills),
            "mcp_servers": len(self.mcp_servers),
            "disallowed_tools": list(self.disallowed_tools),
            "instruction_files": list(self.instruction_files),
            "notices": list(self.notices),
        }
