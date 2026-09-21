# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application orchestration for a contract-preserving OpenCode run."""

from pathlib import Path

from opencodeloop.application.interfaces import ProcessInterface, RunStoreInterface
from opencodeloop.domain.model import RunId, RunResult, RunStatus


class OpencodeRunner:
    """Coordinate the process and append-only run store ports."""

    def __init__(self, process: ProcessInterface, store: RunStoreInterface) -> None:
        self._process = process
        self._store = store

    def doctor(self) -> tuple[bool, str]:
        """Expose the external CLI preflight without adding provider assumptions."""
        return self._process.doctor()

    def run(
        self,
        *,
        prompt: str,
        run_id: str,
        cwd: Path,
        session_id: str | None = None,
    ) -> RunResult:
        """Run OpenCode and persist every normalized event in its worktree.

        `run_id` is caller-supplied and becomes a path segment, so it is
        validated as a single safe component before any path is constructed;
        `RunId.parse` refuses `../..`, absolute paths and hidden names.
        """
        safe_id = RunId.parse(run_id).value
        run_dir = cwd / ".opencodeloop" / "runs" / safe_id
        self._store.begin(run_dir, safe_id, cwd, session_id)
        # The run boundary is owned here, exactly once per run. The process
        # adapter no longer re-emits `run.started` for a provider session
        # event, so a single run seeds the ledger exactly once.
        self._store.append_event(run_dir, {"event_type": "run.started", "run_id": safe_id})
        try:
            result = self._process.execute(
                prompt=prompt,
                cwd=cwd,
                session_id=session_id,
                emit=lambda event: self._store.append_event(run_dir, event),
            )
        except OSError as exc:
            result = RunResult(RunStatus.FAILED, 1, session_id=session_id, detail=str(exc))
            self._store.append_event(
                run_dir, {"event_type": "failed", "detail": str(exc), "run_id": safe_id}
            )
        self._store.finish(run_dir, result)
        return result
