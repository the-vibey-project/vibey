# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/).
from vibey.domain.ultra import ULTRA_POLICY, UltraState
from vibey.domain.budget import BudgetLedger


def test_ultra_continues_indefinitely_when_no_cap_and_active():
    """Verify that ULTRA does not stop prematurely when no budget cap is set.
    The policy should return CONTINUE for many successive calls until the
    operator explicitly stops the run.  The loop is bounded only by Python's
    runtime, not by a budget."""
    # Create a budget with no cap
    budget = BudgetLedger(turns_spent=0, dollars_spent=0.0, max_turns=None, max_dollars=None)
    state = UltraState(active=True, no_cap_declared=True)
    # Run through a large number of passes and verify CONTINUE each time
    for _ in range(1000):
        verdict = ULTRA_POLICY.decide(state, budget)
        assert verdict == ULTRA_POLICY.decide(state, budget)  # simple self-consistency check
        assert verdict is not type(None)
        assert verdict.name == "CONTINUE"
    # After the loop, ensure that if we toggle active to False, the verdict changes
    inactive_state = UltraState(active=False, no_cap_declared=True)
    assert ULTRA_POLICY.decide(inactive_state, budget).name == "OPERATOR_STOP"
