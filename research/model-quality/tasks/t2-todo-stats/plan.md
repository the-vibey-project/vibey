The `todo/` package is a tiny to-do tracker: `todo/store.py` holds `Todo` and `TodoStore`,
and `todo/cli.py` dispatches `add`, `done` and `list` through the `COMMANDS` dict and
`main(argv, store) -> (exit_code, output)`. Add a `stats` command.

1. Create `todo/stats.py` with:
   - a frozen dataclass `Stats` with fields `total: int`, `done: int`, `open: int`,
     `percent_done: int`, `by_priority: dict[int, int]`;
   - `compute_stats(todos: list[Todo]) -> Stats`. `percent_done` is the integer floor of
     `100 * done / total`, and 0 when there are no todos. `by_priority` counts only the todos
     that are NOT done, keyed by priority;
   - `format_stats(stats: Stats) -> str`.
2. `format_stats` produces these lines, each ending in a newline:
   `total: T`, `done: D`, `open: O`, `percent: P%`. Then, if there are open todos, the line
   `open by priority:` followed by one line `  PRIORITY: COUNT` (two leading spaces) per
   priority in ascending numeric order. If there are no open todos the last line is
   `open by priority: none` instead.
3. In `todo/cli.py` register the command `stats` in `COMMANDS`, using a function
   `cmd_stats(args, store)` that returns `(0, format_stats(compute_stats(store.all())))`. If any
   argument is given it returns `(2, "usage: stats\n")` instead.
4. Existing commands and messages must not change.
