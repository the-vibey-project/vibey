# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The delivery id reaches every log line emitted inside its scope."""

from uuid import uuid4

import pytest
import structlog

from vibey.domain.delivery import DeliveryCorrelation
from vibey.infrastructure.interfaces import DeliveryLogContextInterface
from vibey.infrastructure.logging import DELIVERY_LOG_FIELD, DeliveryLogContext


@pytest.fixture(autouse=True)
def _clear_context() -> None:
    structlog.contextvars.clear_contextvars()


def test_binding_puts_the_id_in_the_merged_context() -> None:
    delivery_id = DeliveryCorrelation().for_project(uuid4())
    context = DeliveryLogContext()

    context.bind(delivery_id)

    assert structlog.contextvars.get_contextvars()[DELIVERY_LOG_FIELD] == str(delivery_id.value)


def test_clearing_removes_it() -> None:
    context = DeliveryLogContext()
    context.bind(DeliveryCorrelation().for_project(uuid4()))

    context.clear()

    assert DELIVERY_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_clearing_when_nothing_is_bound_is_not_an_error() -> None:
    DeliveryLogContext().clear()

    assert DELIVERY_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_the_field_is_configurable() -> None:
    delivery_id = DeliveryCorrelation().for_project(uuid4())
    context = DeliveryLogContext("run_correlation_id")

    assert context.field == "run_correlation_id"

    context.bind(delivery_id)

    bound = structlog.contextvars.get_contextvars()
    assert bound["run_correlation_id"] == str(delivery_id.value)
    assert DELIVERY_LOG_FIELD not in bound


def test_the_default_field_is_the_published_one() -> None:
    assert DeliveryLogContext().field == DELIVERY_LOG_FIELD


def test_the_scope_binds_and_unbinds() -> None:
    delivery_id = DeliveryCorrelation().for_project(uuid4())
    context = DeliveryLogContext()

    with context.bound(delivery_id) as value:
        assert value == str(delivery_id.value)
        assert structlog.contextvars.get_contextvars()[DELIVERY_LOG_FIELD] == value

    assert DELIVERY_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_the_scope_unbinds_when_the_block_raises() -> None:
    context = DeliveryLogContext()

    with pytest.raises(RuntimeError), context.bound(DeliveryCorrelation().for_project(uuid4())):
        raise RuntimeError("the delivery failed")

    assert DELIVERY_LOG_FIELD not in structlog.contextvars.get_contextvars()


def test_it_satisfies_its_interface() -> None:
    assert isinstance(DeliveryLogContext(), DeliveryLogContextInterface)
