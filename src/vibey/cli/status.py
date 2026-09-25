# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey status --json`'s document, in one place for both readers of it.

`vibey status --json` prints it and the hub's status route returns it (ADR-0067), so the
two can never disagree about what a project's status is: a client reads the same keys
whichever way it asks (doctrine 7).
"""

from typing import Final

from vibey.cli.interfaces.status_interface import StatusPresenterInterface
from vibey.tui.dashboard import DashboardState


class StatusPresenter:
    """Renders one project's dashboard state as the status document."""

    def document(self, state: DashboardState) -> dict[str, object]:
        return {
            "project_id": str(state.project_id),
            "name": state.project_name,
            "phase": state.phase.value,
            "cycle": state.cycle,
            "max_cycles": state.max_cycles,
            "repo_path": str(state.repo_path),
            "visual_decision": state.visual_decision,
            "deployment_decision": state.deployment_decision,
            "queue_depth": {k.value: v for k, v in state.queue_depth.items()},
            "circuits": [
                {
                    "engine_id": c.engine_id.value,
                    "installed": c.installed,
                    "version": c.version,
                    "conformance_ok": c.conformance_ok,
                    "circuit": (c.circuit.value if hasattr(c.circuit, "value") else str(c.circuit)),
                    "capacity_state": str(c.capacity_state) if c.capacity_state else None,
                    "consecutive_fail": c.consecutive_fail,
                    "cost_usd_cycle": c.cost_usd_cycle,
                    "selected_count": c.selected_count,
                }
                for c in state.circuits
            ],
            "active_worktrees": list(state.active_worktrees),
        }


STATUS_PRESENTER: Final[StatusPresenterInterface] = StatusPresenter()
"""The one status document. Annotated with the interface so `mypy --strict` checks the
class against its declared seam."""
