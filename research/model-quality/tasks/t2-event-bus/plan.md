`shop/inventory.py` holds an `Inventory` class. Make it announce changes through a small event
bus, and add an audit log that listens.

1. Create `shop/events.py` with class `EventBus` and exception `EventHandlerError(Exception)`.
   - `subscribe(topic, handler) -> Callable[[], None]`. A handler is called as
     `handler(topic, payload)`. The returned function unsubscribes that one subscription
     (calling it twice is harmless). Subscribing the same function twice gives two subscriptions.
   - The topic `"*"` receives every published event.
   - `publish(topic, payload) -> int` calls the handlers of that topic first, in subscription
     order, then the `"*"` handlers in subscription order, and returns how many handlers ran.
   - If a handler raises, the remaining handlers still run. After all have run, `publish` raises
     `EventHandlerError` whose `.errors` attribute is the list of the exceptions raised, in order.
2. In `shop/inventory.py` change the constructor to `Inventory(bus=None, low_threshold=2)`.
   When `bus` is given, a successful `add_stock` or `remove_stock` publishes topic
   `"stock.changed"` with payload `{"sku": sku, "old": old_quantity, "new": new_quantity}`. A
   `remove_stock` that makes the quantity cross the threshold (the old quantity was above
   `low_threshold` and the new one is at or below it) also publishes `"stock.low"` with payload
   `{"sku": sku, "quantity": new_quantity}` after `"stock.changed"`. A call that raises publishes
   nothing. Without a bus everything behaves exactly as before.
3. Create `shop/audit.py` with class `AuditLog(bus)`. It subscribes to `"stock.changed"` and
   keeps `entries: list[str]`, adding one string per event in the form `"SKU: OLD -> NEW"`, for
   example `"apple: 3 -> 5"`.
