# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The delivery's correlation id reaches every log line inside its scope."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
import structlog

from vibey.domain.correlation import DeliveryCorrelation
from vibey.infrastructure.logging import CORRELATION_LOG_FIELD, CorrelationLogContext


@pytest.fixture(autouse=True)
def _clear_context() -> Iterator[None]:
    """Clear on both sides. Clearing only on entry leaves whatever the last
    test in this module bound alive in the worker's context vars, where the
    next module's rendered log payloads would pick it up."""
    structlog.contextvars.clear_contextvars()
    yield
    structlog.contextvars.clear_contextvars()


def test_binding_puts_the_id_in_the_merged_context() -> None:
    correlation_id = DeliveryCorrelation().for_project(uuid4())
    context = CorrelationLogContext()

    context.bind(correlation_id)

    assert structlog.contextvars.get_contextvars()[CORRELATION_LOG_FIELD] == str(
        correlation_id.value
    )


def test_clearing_removes_it() -> None:
    context = CorrelationLogContext()
    context.bind(DeliveryCorrelation().for_project(uuid4()))

    context.clear()

    assert CORRELATION_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_clearing_when_nothing_is_bound_is_not_an_error() -> None:
    CorrelationLogContext().clear()

    assert CORRELATION_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_the_field_is_configurable() -> None:
    correlation_id = DeliveryCorrelation().for_project(uuid4())
    context = CorrelationLogContext("delivery_correlation_id")

    assert context.field == "delivery_correlation_id"

    context.bind(correlation_id)

    bound = structlog.contextvars.get_contextvars()
    assert bound["delivery_correlation_id"] == str(correlation_id.value)
    assert CORRELATION_LOG_FIELD not in bound


def test_the_default_field_is_the_ledger_column_name() -> None:
    assert CorrelationLogContext().field == CORRELATION_LOG_FIELD == "correlation_id"


def test_the_scope_binds_and_unbinds() -> None:
    correlation_id = DeliveryCorrelation().for_project(uuid4())
    context = CorrelationLogContext()

    with context.bound(correlation_id) as value:
        assert value == str(correlation_id.value)
        assert structlog.contextvars.get_contextvars()[CORRELATION_LOG_FIELD] == value

    assert CORRELATION_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_the_scope_unbinds_when_the_block_raises() -> None:
    context = CorrelationLogContext()

    with pytest.raises(RuntimeError), context.bound(DeliveryCorrelation().for_project(uuid4())):
        raise RuntimeError("the delivery failed")

    assert CORRELATION_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_leaving_an_inner_scope_restores_the_outer_binding() -> None:
    """The bug this pins: a `finally: clear()` unbinds instead of restoring,
    so every line logged in the outer delivery's scope after the inner one
    returned would carry no correlation id at all."""
    outer = DeliveryCorrelation().for_project(uuid4())
    inner = DeliveryCorrelation().for_project(uuid4())
    context = CorrelationLogContext()

    with context.bound(outer):
        with context.bound(inner):
            assert structlog.contextvars.get_contextvars()[CORRELATION_LOG_FIELD] == str(
                inner.value
            )
        assert structlog.contextvars.get_contextvars()[CORRELATION_LOG_FIELD] == str(outer.value)

    assert CORRELATION_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_a_scope_inside_a_plain_bind_restores_it_too() -> None:
    """The same loss by the other route: `bind` then a `bound(...)` block."""
    outer = DeliveryCorrelation().for_project(uuid4())
    inner = DeliveryCorrelation().for_project(uuid4())
    context = CorrelationLogContext()

    context.bind(outer)
    with context.bound(inner):
        pass

    assert structlog.contextvars.get_contextvars()[CORRELATION_LOG_FIELD] == str(outer.value)
