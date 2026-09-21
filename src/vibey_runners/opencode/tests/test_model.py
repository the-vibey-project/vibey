# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from opencodeloop.domain.model import DONE_MARKER, RunResult, RunStatus


def test_run_result_succeeds_only_for_clean_finished_process() -> None:
    assert RunResult(RunStatus.FINISHED, 0).succeeded
    assert not RunResult(RunStatus.FINISHED, 1).succeeded
    assert not RunResult(RunStatus.FAILED, 0).succeeded
    assert DONE_MARKER == "OPENCODELOOP_TASK_FULLY_COMPLETE"
