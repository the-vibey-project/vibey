import dataclasses

import pytest
from todo.cli import COMMANDS, main
from todo.stats import Stats, compute_stats, format_stats
from todo.store import Todo, TodoStore


def make(*specs: tuple[int, bool]) -> list[Todo]:
    return [Todo(i + 1, f"t{i + 1}", p, d) for i, (p, d) in enumerate(specs)]


def test_compute_basic() -> None:
    stats = compute_stats(make((1, False), (2, True), (1, False), (3, True), (3, False)))
    assert (stats.total, stats.done, stats.open) == (5, 2, 3)
    assert stats.percent_done == 40
    assert stats.by_priority == {1: 2, 3: 1}


def test_percent_is_floored() -> None:
    assert compute_stats(make((1, True), (1, False), (1, False))).percent_done == 33
    assert compute_stats(make((1, True), (1, True), (1, False))).percent_done == 66


def test_empty_list() -> None:
    stats = compute_stats([])
    assert (stats.total, stats.done, stats.open, stats.percent_done) == (0, 0, 0, 0)
    assert stats.by_priority == {}


def test_all_done() -> None:
    stats = compute_stats(make((1, True), (2, True)))
    assert stats.percent_done == 100
    assert stats.open == 0
    assert stats.by_priority == {}


def test_stats_is_frozen_dataclass() -> None:
    stats = compute_stats([])
    assert isinstance(stats, Stats)
    with pytest.raises(dataclasses.FrozenInstanceError):
        stats.total = 1  # type: ignore[misc]


def test_format_with_open_todos_sorted_numerically() -> None:
    stats = compute_stats(make((10, False), (2, False), (2, False), (1, True)))
    assert format_stats(stats) == (
        "total: 4\ndone: 1\nopen: 3\npercent: 25%\nopen by priority:\n  2: 2\n  10: 1\n"
    )


def test_format_with_nothing_open() -> None:
    assert format_stats(compute_stats([])) == (
        "total: 0\ndone: 0\nopen: 0\npercent: 0%\nopen by priority: none\n"
    )


def test_stats_command_is_registered() -> None:
    assert "stats" in COMMANDS
    assert {"add", "done", "list"} <= set(COMMANDS)


def test_stats_command_output() -> None:
    store = TodoStore()
    main(["add", "write", "docs", "--priority", "1"], store)
    main(["add", "ship"], store)
    main(["add", "relax", "--priority", "1"], store)
    main(["done", "2"], store)
    code, out = main(["stats"], store)
    assert code == 0
    assert out == ("total: 3\ndone: 1\nopen: 2\npercent: 33%\nopen by priority:\n  1: 2\n")


def test_stats_on_empty_store() -> None:
    code, out = main(["stats"], TodoStore())
    assert code == 0
    assert out.endswith("open by priority: none\n")


def test_stats_rejects_arguments() -> None:
    assert main(["stats", "now"], TodoStore()) == (2, "usage: stats\n")


def test_existing_commands_unchanged() -> None:
    store = TodoStore()
    assert main(["add", "a", "b"], store) == (0, "added 1\n")
    assert main(["add", "c", "--priority", "5"], store) == (0, "added 2\n")
    assert main(["done", "1"], store) == (0, "done 1\n")
    assert main(["done", "9"], store) == (1, "no such todo: 9\n")
    assert main(["list"], store) == (0, "1 [x] a b (p3)\n2 [ ] c (p5)\n")
    assert main([], store) == (2, "usage: todo <command>\n")
    assert main(["nope"], store) == (2, "unknown command: nope\n")
