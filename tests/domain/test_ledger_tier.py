# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

import pytest

from vibey.domain.interfaces.ledger_tier_interface import TierConfigInterface
from vibey.domain.ledger_tier import TierConfig


def test_tier_config_satisfies_its_interface() -> None:
    assert isinstance(TierConfig(standard_n=100, mid_tier_n=1_000), TierConfigInterface)


@pytest.mark.parametrize(("standard_n", "mid_tier_n"), [(-1, 0), (0, -1)])
def test_tier_config_rejects_negative_retention(standard_n: int, mid_tier_n: int) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        TierConfig(standard_n=standard_n, mid_tier_n=mid_tier_n)
