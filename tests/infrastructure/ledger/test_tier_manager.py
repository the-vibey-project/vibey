# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

from uuid import uuid4

from vibey.domain.interfaces.ledger_tier_interface import LedgerTierManagerInterface
from vibey.domain.ledger_tier import TierConfig
from vibey.infrastructure.ledger.tier_manager import TierManager


def test_tier_manager_satisfies_its_interface() -> None:
    manager = TierManager()
    project_id = uuid4()

    assert isinstance(manager, LedgerTierManagerInterface)
    assert manager.reconcile_tiers(project_id, TierConfig(10, 100)) == (0, 0)
    assert manager.get_event(project_id, 1) is None
    assert manager.get_range(project_id, 1, 10) == ()
