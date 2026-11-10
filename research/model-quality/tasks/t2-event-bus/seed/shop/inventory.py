class InsufficientStock(Exception):
    """Raised when more units are removed than are in stock."""


class Inventory:
    """Stock counts per SKU."""

    def __init__(self) -> None:
        self._stock: dict[str, int] = {}

    def stock(self, sku: str) -> int:
        return self._stock.get(sku, 0)

    def add_stock(self, sku: str, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        self._stock[sku] = self.stock(sku) + quantity
        return self._stock[sku]

    def remove_stock(self, sku: str, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        if quantity > self.stock(sku):
            raise InsufficientStock(sku)
        self._stock[sku] = self.stock(sku) - quantity
        return self._stock[sku]
