from dataclasses import dataclass

from todo.store import Todo


@dataclass(frozen=True)
class Stats:
    total: int
    done: int
    open: int
    percent_done: int
    by_priority: dict[int, int]


def compute_stats(todos: list[Todo]) -> Stats:
    total = len(todos)
    done = sum(1 for todo in todos if todo.done)
    by_priority: dict[int, int] = {}
    for todo in todos:
        if not todo.done:
            by_priority[todo.priority] = by_priority.get(todo.priority, 0) + 1
    percent = 100 * done // total if total else 0
    return Stats(total, done, total - done, percent, by_priority)


def format_stats(stats: Stats) -> str:
    lines = [
        f"total: {stats.total}",
        f"done: {stats.done}",
        f"open: {stats.open}",
        f"percent: {stats.percent_done}%",
    ]
    if stats.by_priority:
        lines.append("open by priority:")
        for priority in sorted(stats.by_priority):
            lines.append(f"  {priority}: {stats.by_priority[priority]}")
    else:
        lines.append("open by priority: none")
    return "".join(line + "\n" for line in lines)
