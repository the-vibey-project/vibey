# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import pytest

from opencodeloop.domain.model import DONE_MARKER, RunId, RunResult, RunStatus


def test_run_result_succeeds_only_for_clean_finished_process() -> None:
    assert RunResult(RunStatus.FINISHED, 0).succeeded
    assert not RunResult(RunStatus.FINISHED, 1).succeeded
    assert not RunResult(RunStatus.FAILED, 0).succeeded
    assert DONE_MARKER == "OPENCODELOOP_TASK_FULLY_COMPLETE"


def test_run_id_accepts_safe_segments_and_trims_surrounding_space() -> None:
    assert RunId.parse("  run-1.a_b  ").value == "run-1.a_b"
    assert RunId.parse("0").value == "0"


@pytest.mark.parametrize(
    "raw",
    ["", " ", ".", "..", "../escape", "a/b", "a\\b", ".hidden", "-leading", "a b", "a" * 129],
)
def test_run_id_refuses_anything_that_is_not_one_safe_path_segment(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid run id"):
        RunId.parse(raw)
