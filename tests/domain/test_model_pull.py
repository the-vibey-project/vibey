# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Ollama's pull stream, turned into lines a person can read in a terminal or a log.

A pull of the sovereign model streams thousands of progress events; a person needs each new
stage once and the download's progress in steps, not every event.
"""

from vibey.domain.interfaces.model_pull_interface import PullProgressInterface
from vibey.domain.model_pull import PullProgress


def test_the_reporter_satisfies_its_interface() -> None:
    assert isinstance(PullProgress(), PullProgressInterface)


def test_each_new_stage_is_said_once() -> None:
    progress = PullProgress()
    said = [
        progress.line(event)
        for event in (
            {"status": "pulling manifest"},
            {"status": "pulling manifest"},
            {"status": "verifying sha256 digest"},
            {"status": "success"},
            {},
        )
    ]
    assert said == ["pulling manifest", None, "verifying sha256 digest", "success", None]


def test_a_download_is_reported_in_steps_with_its_size() -> None:
    progress = PullProgress(step_percent=25)
    total = 12_100_000_000
    events = [
        {"status": "pulling abc", "digest": "sha256:abc", "total": total, "completed": done}
        for done in (0, 1, total // 5, total // 4, total // 2, total // 2 + 1, total)
    ]
    said = [progress.line(event) for event in events]
    assert said == [
        "pulling abc: 0% of 12.1 GB",
        None,
        None,
        "pulling abc: 25% of 12.1 GB",
        "pulling abc: 50% of 12.1 GB",
        None,
        "pulling abc: 100% of 12.1 GB",
    ]


def test_a_second_layer_starts_its_own_count() -> None:
    progress = PullProgress()
    assert progress.line({"status": "pulling a", "digest": "a", "total": 10, "completed": 10})
    assert progress.line({"status": "pulling b", "digest": "b", "total": 10, "completed": 0}) == (
        "pulling b: 0% of 0.0 GB"
    )


def test_an_event_without_usable_counts_is_a_stage() -> None:
    progress = PullProgress()
    assert progress.line({"status": "pulling a", "total": "x", "completed": 1}) == "pulling a"
    assert progress.line({"status": "pulling b", "total": 0, "completed": 0}) == "pulling b"
    assert progress.line({"status": "pulling c", "total": 5}) == "pulling c"
