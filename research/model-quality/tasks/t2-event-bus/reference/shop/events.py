from collections.abc import Callable
from typing import Any

Handler = Callable[[str, Any], None]


class EventHandlerError(Exception):
    def __init__(self, errors: list[Exception]) -> None:
        super().__init__(f"{len(errors)} handler(s) failed")
        self.errors = errors


class EventBus:
    def __init__(self) -> None:
        self._subs: list[tuple[int, str, Handler]] = []
        self._counter = 0

    def subscribe(self, topic: str, handler: Handler) -> Callable[[], None]:
        self._counter += 1
        token = self._counter
        self._subs.append((token, topic, handler))

        def unsubscribe() -> None:
            self._subs = [sub for sub in self._subs if sub[0] != token]

        return unsubscribe

    def publish(self, topic: str, payload: Any) -> int:
        direct = [h for _, t, h in self._subs if t == topic and t != "*"]
        wild = [h for _, t, h in self._subs if t == "*"]
        errors: list[Exception] = []
        handlers = direct + wild
        for handler in handlers:
            try:
                handler(topic, payload)
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
        if errors:
            raise EventHandlerError(errors)
        return len(handlers)
