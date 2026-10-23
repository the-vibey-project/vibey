import pytest

from vibey.domain.budget import BudgetLedger
from vibey.domain.ultra import UltraPolicy, UltraState, UltraVerdict


class DummyBudget:
    def __init__(self, max_dollars=None, any_exhausted=False):
        self._max_dollars = max_dollars
        self._any_exhausted = any_exhausted

    @property
    def max_dollars(self):
        return self._max_dollars

    @property
    def any_exhausted(self):
        return self._any_exhausted

    # Required by UltraPolicy interface but unused in tests
    @property
    def turns_spent(self):
        return 0

    @property
    def dollars_spent(self):
        return 0.0

    @property
    def max_turns(self):
        return None

    @property
    def turns_exhausted(self):
        return False

    @property
    def dollars_exhausted(self):
        return False

    def would_exceed(self, projected: float) -> bool:
        return self.max_dollars is not None and (self.dollars_spent + projected > self.max_dollars)

    def spend(self, *, turns: int = 0, dollars: float = 0.0):
        return DummyBudget(max_dollars=self.max_dollars)
# Only one parametrize decorator
@pytest.mark.parametrize(
    "max_dollars,no_cap,expected",
    [
        (None, False, UltraVerdict.NEEDS_CAP),
        (None, True, UltraVerdict.CONTINUE),
        (1000, False, UltraVerdict.CONTINUE),
    ],
)

def test_ultra_policy_decide(max_dollars, no_cap, expected):
    policy = UltraPolicy()
    state = UltraState(active=True, no_cap_declared=no_cap)
    budget = DummyBudget(max_dollars=max_dollars)
    assert policy.decide(state, budget) == expected

# test that operator stop overrides everything
@pytest.fixture
def budget_any_exhausted():
    return DummyBudget(any_exhausted=True)


def test_operator_stop_overrides(budget_any_exhausted):
    policy = UltraPolicy()
    state = UltraState(active=False, no_cap_declared=True)
    # operator stop should take precedence
    assert policy.decide(state, budget_any_exhausted) == UltraVerdict.OPERATOR_STOP

