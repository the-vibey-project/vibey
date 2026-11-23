# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one run is given, resolved from the bundle and the lock (SP-LOOPS Task 6).

`plugin_dirs` are the run's own verified copies of the selected plugins, in bundle order, inside a
0700 folder under the person's snapshot folder; nothing in them is a link to a marketplace.
`skills` indexes those copies, with descriptions and skipped reasons made safe for a model context
and a terminal. `mcp_servers` are the bundle's servers, minus the disabled ones. `digest` is the
sha256 of the bundle's canonical JSON and the lock entries the snapshot used -- the value a run
records in the ledger; the same bundle and lock give the same digest on every run. A record with no
behaviour, so no seam of its own.
"""

from dataclasses import dataclass
from pathlib import Path

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.skill_catalog import SkillCatalog


@dataclass(frozen=True, slots=True)
class CapabilitySnapshot:
    plugin_dirs: tuple[Path, ...]
    skills: SkillCatalog
    mcp_servers: tuple[McpServerSpec, ...]
    digest: str
