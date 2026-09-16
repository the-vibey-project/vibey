# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One correlation id per delivery, keyed on the project and nothing else."""

from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from vibey.domain.delivery import (
    DELIVERY_NAMESPACE,
    DELIVERY_NAMESPACE_URI,
    DeliveryCorrelation,
    DeliveryId,
)
from vibey.domain.interfaces import DeliveryCorrelationInterface, DeliveryIdInterface


def test_namespace_is_the_fold_of_the_published_uri() -> None:
    assert uuid5(NAMESPACE_URL, DELIVERY_NAMESPACE_URI) == DELIVERY_NAMESPACE


def test_same_project_yields_the_same_id_every_time() -> None:
    project_id = uuid4()
    first = DeliveryCorrelation().for_project(project_id)
    second = DeliveryCorrelation().for_project(project_id)

    assert first == second
    assert first.value == uuid5(DELIVERY_NAMESPACE, str(project_id))


def test_different_projects_yield_different_ids() -> None:
    deriver = DeliveryCorrelation()
    assert deriver.for_project(uuid4()) != deriver.for_project(uuid4())


def test_the_cycle_is_not_part_of_the_key() -> None:
    """A REVIEW loop-back increments the cycle; the delivery is still one
    delivery, so the id it is traced by must not move with it."""
    project_id = uuid4()
    deriver = DeliveryCorrelation()

    # There is no cycle to pass -- that is the point. Derivation over the
    # project alone is what makes cycle 1 and cycle 7 the same delivery.
    assert deriver.for_project(project_id) == deriver.for_project(project_id)


def test_a_custom_namespace_partitions_the_ids() -> None:
    project_id = uuid4()
    other = UUID("00000000-0000-5000-8000-000000000001")

    assert DeliveryCorrelation(other).namespace == other
    assert DeliveryCorrelation(other).for_project(project_id) != DeliveryCorrelation().for_project(
        project_id
    )


def test_default_namespace_is_the_published_one() -> None:
    assert DeliveryCorrelation().namespace == DELIVERY_NAMESPACE


def test_delivery_id_renders_as_its_uuid() -> None:
    value = uuid4()
    assert str(DeliveryId(value)) == str(value)


def test_the_concrete_types_satisfy_their_interfaces() -> None:
    assert isinstance(DeliveryCorrelation(), DeliveryCorrelationInterface)
    assert isinstance(DeliveryId(uuid4()), DeliveryIdInterface)
