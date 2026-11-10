from typing import Any

from shop.events import EventBus


class AuditLog:
    def __init__(self, bus: EventBus) -> None:
        self.entries: list[str] = []
        bus.subscribe("stock.changed", self._on_change)

    def _on_change(self, topic: str, payload: Any) -> None:
        self.entries.append(f"{payload['sku']}: {payload['old']} -> {payload['new']}")
