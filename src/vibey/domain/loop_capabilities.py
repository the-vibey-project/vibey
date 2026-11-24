# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the ledger records of the snapshot a run was given (SP-LOOPS Phase 4, ruling R3).

Before a BUILD engine that takes a capability snapshot starts, vibey appends one
`LoopCapabilitiesSnapshotted` event. Its payload is built here and holds only the run's id, the
snapshot's digest and counts: how many plugins and skills it enabled, how many skills the index
skipped, how many local and remote MCP servers it held, and how many notices the project's
narrowing raised. A server's command, URL and environment are never passed in, so no payload can
carry them. The digest names the bundle and lock the run was given; the same pair gives the same
digest, so two runs can be told apart without the ledger holding the operator's configuration.

The kind is withheld from publication (`publication_policy.WITHHELD_KINDS`): even as counts it
describes the operator's own plugins and servers.
"""

from typing import Final
from uuid import UUID

from vibey_runners.common.capabilities.lock import DIGEST_PATTERN

from vibey.domain.interfaces.loop_capabilities_interface import LoopCapabilitiesRecordInterface


class LoopCapabilitiesRecord:
    """Builds the `LoopCapabilitiesSnapshotted` payload, refusing what is not a digest or a
    count. Stateless."""

    def payload(
        self,
        *,
        run_id: UUID,
        digest: str,
        plugins: int,
        skills: int,
        skills_skipped: int,
        mcp_local: int,
        mcp_remote: int,
        notices: int,
    ) -> dict[str, object]:
        if not DIGEST_PATTERN.fullmatch(digest):
            raise ValueError(f"a snapshot digest is sha256: and 64 hex digits, not {digest!r}")
        counts = {
            "plugins": plugins,
            "skills": skills,
            "skills_skipped": skills_skipped,
            "mcp_local": mcp_local,
            "mcp_remote": mcp_remote,
            "notices": notices,
        }
        for name, value in counts.items():
            # A bool is an int to Python, never a count to a reader of the ledger.
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} is a count of zero or more, not {value!r}")
        return {
            "run_id": str(run_id),
            "digest": digest,
            "plugins": plugins,
            "skills": skills,
            "skills_skipped": skills_skipped,
            "mcp_local": mcp_local,
            "mcp_remote": mcp_remote,
            "project_notices": notices,
        }


LOOP_CAPABILITIES_RECORD: Final[LoopCapabilitiesRecordInterface] = LoopCapabilitiesRecord()
"""The one builder. Annotated with the interface so `mypy --strict` checks the class against it."""
