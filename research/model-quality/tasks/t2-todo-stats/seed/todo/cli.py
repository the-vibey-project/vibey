from collections.abc import Callable

from todo.store import TodoStore

Result = tuple[int, str]


def cmd_add(args: list[str], store: TodoStore) -> Result:
    priority = 3
    if len(args) >= 3 and args[-2] == "--priority":
        priority = int(args[-1])
        args = args[:-2]
    if not args:
        return 2, "usage: add TITLE [--priority N]\n"
    todo = store.add(" ".join(args), priority)
    return 0, f"added {todo.id}\n"


def cmd_done(args: list[str], store: TodoStore) -> Result:
    if len(args) != 1:
        return 2, "usage: done ID\n"
    try:
        store.complete(int(args[0]))
    except KeyError:
        return 1, f"no such todo: {args[0]}\n"
    return 0, f"done {args[0]}\n"


def cmd_list(args: list[str], store: TodoStore) -> Result:
    lines = []
    for todo in store.all():
        mark = "x" if todo.done else " "
        lines.append(f"{todo.id} [{mark}] {todo.title} (p{todo.priority})\n")
    return 0, "".join(lines)


COMMANDS: dict[str, Callable[[list[str], TodoStore], Result]] = {
    "add": cmd_add,
    "done": cmd_done,
    "list": cmd_list,
}


def main(argv: list[str], store: TodoStore) -> Result:
    if not argv:
        return 2, "usage: todo <command>\n"
    command = COMMANDS.get(argv[0])
    if command is None:
        return 2, f"unknown command: {argv[0]}\n"
    return command(argv[1:], store)
