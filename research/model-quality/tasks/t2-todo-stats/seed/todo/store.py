from dataclasses import dataclass


@dataclass
class Todo:
    id: int
    title: str
    priority: int = 3
    done: bool = False


class TodoStore:
    def __init__(self) -> None:
        self._todos: list[Todo] = []

    def add(self, title: str, priority: int = 3) -> Todo:
        todo = Todo(len(self._todos) + 1, title, priority)
        self._todos.append(todo)
        return todo

    def complete(self, todo_id: int) -> None:
        for todo in self._todos:
            if todo.id == todo_id:
                todo.done = True
                return
        raise KeyError(todo_id)

    def all(self) -> list[Todo]:
        return list(self._todos)
