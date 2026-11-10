from typing import Any

import pytest
from shop.audit import AuditLog
from shop.events import EventBus, EventHandlerError
from shop.inventory import InsufficientStock, Inventory


def test_publish_calls_subscribers_in_order() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("a", lambda t, p: seen.append(f"1:{t}:{p}"))
    bus.subscribe("a", lambda t, p: seen.append(f"2:{t}:{p}"))
    bus.subscribe("b", lambda t, p: seen.append("b"))
    assert bus.publish("a", 7) == 2
    assert seen == ["1:a:7", "2:a:7"]


def test_publish_without_subscribers() -> None:
    assert EventBus().publish("nothing", None) == 0


def test_wildcard_runs_after_direct_handlers() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("*", lambda t, p: seen.append("wild"))
    bus.subscribe("a", lambda t, p: seen.append("direct"))
    assert bus.publish("a", None) == 2
    assert seen == ["direct", "wild"]
    assert bus.publish("zzz", None) == 1


def test_unsubscribe_removes_only_that_subscription() -> None:
    bus = EventBus()
    seen: list[str] = []

    def handler(topic: str, payload: Any) -> None:
        seen.append("x")

    first = bus.subscribe("a", handler)
    bus.subscribe("a", handler)
    first()
    first()
    assert bus.publish("a", None) == 1
    assert seen == ["x"]


def test_failing_handler_does_not_stop_the_others() -> None:
    bus = EventBus()
    seen: list[str] = []

    def boom(topic: str, payload: Any) -> None:
        raise RuntimeError("boom")

    def bang(topic: str, payload: Any) -> None:
        raise KeyError("bang")

    bus.subscribe("a", boom)
    bus.subscribe("a", lambda t, p: seen.append("ok"))
    bus.subscribe("*", bang)
    with pytest.raises(EventHandlerError) as info:
        bus.publish("a", None)
    assert seen == ["ok"]
    assert [type(e) for e in info.value.errors] == [RuntimeError, KeyError]


def test_inventory_without_bus_is_unchanged() -> None:
    inv = Inventory()
    assert inv.add_stock("a", 3) == 3
    assert inv.remove_stock("a", 1) == 2
    with pytest.raises(InsufficientStock):
        inv.remove_stock("a", 5)
    with pytest.raises(ValueError):
        inv.add_stock("a", 0)


def _recorder(bus: EventBus) -> list[tuple[str, Any]]:
    events: list[tuple[str, Any]] = []
    bus.subscribe("*", lambda t, p: events.append((t, p)))
    return events


def test_add_stock_publishes_changed() -> None:
    bus = EventBus()
    events = _recorder(bus)
    Inventory(bus).add_stock("apple", 5)
    assert events == [("stock.changed", {"sku": "apple", "old": 0, "new": 5})]


def test_remove_stock_publishes_changed() -> None:
    bus = EventBus()
    inv = Inventory(bus, low_threshold=1)
    inv.add_stock("apple", 10)
    events = _recorder(bus)
    inv.remove_stock("apple", 2)
    assert events == [("stock.changed", {"sku": "apple", "old": 10, "new": 8})]


def test_low_stock_published_after_changed_on_crossing() -> None:
    bus = EventBus()
    inv = Inventory(bus)
    inv.add_stock("pear", 5)
    events = _recorder(bus)
    inv.remove_stock("pear", 3)
    assert [t for t, _ in events] == ["stock.changed", "stock.low"]
    assert events[1][1] == {"sku": "pear", "quantity": 2}


def test_low_stock_not_repeated_when_already_low() -> None:
    bus = EventBus()
    inv = Inventory(bus, low_threshold=3)
    inv.add_stock("pear", 3)
    events = _recorder(bus)
    inv.remove_stock("pear", 1)
    assert [t for t, _ in events] == ["stock.changed"]


def test_low_stock_when_dropping_to_zero_from_above() -> None:
    bus = EventBus()
    inv = Inventory(bus, low_threshold=0)
    inv.add_stock("fig", 2)
    events = _recorder(bus)
    inv.remove_stock("fig", 2)
    assert [t for t, _ in events] == ["stock.changed", "stock.low"]
    assert events[1][1]["quantity"] == 0


def test_failed_calls_publish_nothing() -> None:
    bus = EventBus()
    inv = Inventory(bus)
    events = _recorder(bus)
    with pytest.raises(InsufficientStock):
        inv.remove_stock("x", 1)
    with pytest.raises(ValueError):
        inv.add_stock("x", -1)
    assert events == []


def test_audit_log_records_changes_only() -> None:
    bus = EventBus()
    inv = Inventory(bus)
    log = AuditLog(bus)
    inv.add_stock("apple", 3)
    inv.add_stock("apple", 2)
    inv.remove_stock("apple", 4)
    assert log.entries == ["apple: 0 -> 3", "apple: 3 -> 5", "apple: 5 -> 1"]


def test_audit_log_ignores_other_topics() -> None:
    bus = EventBus()
    log = AuditLog(bus)
    bus.publish("stock.low", {"sku": "a", "quantity": 1})
    assert log.entries == []
