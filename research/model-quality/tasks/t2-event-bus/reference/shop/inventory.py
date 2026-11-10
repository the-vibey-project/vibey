from shop.events import EventBus


class InsufficientStock(Exception):
    """Raised when more units are removed than are in stock."""


class Inventory:
    """Stock counts per SKU."""

    def __init__(self, bus: EventBus | None = None, low_threshold: int = 2) -> None:
        self._stock: dict[str, int] = {}
        self._bus = bus
        self._low_threshold = low_threshold

    def stock(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def add_stock(self, sku: str, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        old = self.stock(sku)
        self._stock[sku] = old + quantity
        self._announce(sku, old, self._stock[sku])
        return self._stock[sku]

    def remove_stock(self, sku: str, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        old = self.stock(sku)
        if quantity > old:
            raise InsufficientStock(sku)
        self._stock[sku] = old - quantity
        new = self._stock[sku]
        self._announce(sku, old, new)
        if self._bus is not None and old > self._low_threshold >= new:
            self._bus.publish("stock.low", {"sku": sku, "quantity": new})
        return new

    def _announce(self, sku: str, old: int, new: int) -> None:
        if self._bus is not None:
            self._bus.publish("stock.changed", {"sku": sku, "old": old, "new": new})
