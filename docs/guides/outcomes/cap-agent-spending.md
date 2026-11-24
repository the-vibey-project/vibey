---
description: Set a per-cycle dollar or turn cap with vibey budget set; the brake reads it before every BUILD session and parks a gate when it trips, and vibey cost shows each engine's spend from the ledger.
---

# How do I cap what AI coding agents spend, and see where the money went?

**Short answer:** set a per-cycle dollar or turn cap with `vibey budget set`; the brake
reads it before every BUILD session and parks a gate when it trips, and `vibey cost` shows
each engine's spend from the ledger.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone who lets an agent run unattended. Put
> `--max-cycle-dollars` on `vibey new`, or run `vibey budget set` later; no restart is needed.
> It takes a minute. Afterwards no new BUILD session starts past the cap until a person says
> so, and every dollar spent is in your own ledger.

## The lesson: the petty-cash tin

Daniel had found last month's invoice in the printer tray, and it was not small.

**Daniel:** How do I stop an agent spending money while I sleep?

**Professor Feynman:** Think of a house-sitter with a petty-cash tin and a notebook. Before
each errand she adds up the notebook. If it has reached the limit you wrote on the lid, she
leaves you a note and waits.

**Daniel:** So she can never go over?

**Professor Feynman:** Ah, she can, a little. She checks before each errand, not during one,
and only against what is already written down. An errand under way finishes. That is vibey's
brake: it is read before every BUILD session, against spend the ledger has recorded.

**Daniel:** So I leave some headroom.

**Professor Feynman:** Yes. And the cheapest errand is the one that costs nothing: the default
engine runs on your own machine at zero per token. The picture stops working at the note: a
vibey gate also says how to raise the limit, and only some people may answer it.

## Steps

**1. Cap a project when you create it.** Caps are per delivery cycle.

```bash
vibey new my-app --repo ~/src/my-app --max-cycle-dollars 15 --max-cycle-turns 200
```

**2. Change the cap whenever you like.** A running worker applies it at its next session.

```bash
vibey budget set --max-cycle-dollars 25     # raise it
vibey budget clear --turns                  # remove the turn cap (--dollars, --all)
vibey budget                                # caps, this cycle's spend, every change
```

Each change is appended as a `BudgetCapChanged` event, with the account that ran it and any
`--by` label ([`vibey budget`](../../reference/cli.md#vibey-budget-project_id)).

**3. Answer the gate when a cap trips.** The next BUILD session parks a `budget_exhausted`
gate instead of starting, and `vibey gates` prints the command that answers it.

```bash
vibey gates
vibey answer GATE_ID --raw '{}'                   # resume under the caps as they now stand
vibey answer GATE_ID --raw '{"max_dollars": 25}'  # or raise it for this one job
vibey answer GATE_ID --raw '{"max_turns": 300}'   # the same, for turns
```

**4. Decide who may answer it.** On the host, anyone who can run vibey against the database can.
Through the hub, only a device paired with the `spend` scope can
(`vibey hub pair --scope view --scope spend`), checked again on every action. An LLM driving
vibey over MCP never holds `spend`, so the hub refuses it. Changing a cap is never offered
through the hub at all ([`hub_scope.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/hub_scope.py)).

**5. Keep paid engines out unless you mean them.** Local engines are chosen first and cost
nothing; a paid engine needs installing, signing in and a passing
`vibey doctor --conformance --record` before it is ever selected. To rule them out:

```bash
vibey worker --engines gptossloop
```

With `--provider claudeloop`, each design and planning call is also bounded by the worker's
`--max-dollars` (default 2.00) and `--max-turns` (default 25).

**6. See where the money went.**

```bash
vibey cost                                    # this cycle against the caps, then each engine
vibey ledger search --kind TurnCompleted --kind BudgetSpent --limit 1000 --json
vibey ledger export PROJECT_ID --billing -o billing.jsonl   # JSON Lines, for vibey-gh forecast
```

## Credits are not rate limits

A rate limit is a window that may say when it resets. Exhausted credits have no clock: only a
person topping up changes them, so vibey never schedules a wait for them. The rule is held three
times: the `CreditsExhausted` type has no reset time
([`capacity.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/capacity.py)),
a test fails if it gains one ([`test_capacity.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/domain/test_capacity.py)),
and a database `CHECK` refuses one ([migration 0007](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/db/migrations/0007_engine_health_rotation.sql)).
A credit-exhausted engine is probed again on a backoff. Work it winds down moves to another
engine with a handoff brief that must pass the no-loss check first
([ADR-0004](../../architecture/decisions/0004-no-loss-gate-on-handoff.md)).

## Daniel's teach-back

**Daniel:** I set a dollar or turn cap per cycle, and change it any time with `vibey budget`.
Before each BUILD session vibey adds up the recorded spend; past the cap it parks a gate, and I
resume or raise it. Only the host, or a device I paired with `spend`, can say yes.

**Professor Feynman:** Right. And remember the errand under way: the brake stops the next
session, not the current one.

## The evidence

| Claim | Where it is proved |
|---|---|
| Caps are read at every BUILD session, from the project's stored config | [Per-cycle caps](../../reference/configuration.md#per-cycle-caps-max_cycle_dollars-max_cycle_turns); [`budget_caps.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/budget_caps.py) |
| Spend is summed from the ledger | [`[budget]`](../../reference/configuration.md#budget) |
| A tripped cap parks a gate that can grant more | [ADR-0024](../../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md) |
| Spending answers need the `spend` scope | [`hub_scope.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/hub_scope.py); [ADR-0071](../../architecture/decisions/0071-hub-pairing-and-trust.md) |
| Local engines first | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md) |
| Credits and rate limits differ | [Capacity verdicts](../../paper.md#capacity-verdicts), in the paper |

## Limits

- **`[budget]` in `vibey.toml` is not the brake.** The live caps are the ones `vibey new` and
  `vibey budget` store. There is no lifetime cap across cycles.
- **The figures are what the engines report.** Reconcile them with your vendor's invoice.
- **Per-engine totals cross cycles**, and the selection count is not a turn count.
- **Hand-back is not wired yet.** [ADR-0070](../../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md)'s
  failover-and-hand-back service is written and tested, but the worker does not construct it.
- **ULTRA runs need an explicit decision.** With no dollar cap they park unless the operator
  declares no cap in a terminal with a typed phrase
  ([`vibey budget no-cap`](../../reference/cli.md#vibey-budget-no-cap-and-vibey-budget-cap)).

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| `cycle budget exhausted: $… spent of $… cap` | The brake tripped | Answer the gate, step 3 |
| `hub refused (403)` on a budget gate | The caller lacks `spend` | Answer on the host |
| The gate comes back after `--raw '{}'` | Spend is still over the cap | Raise the cap or grant more |

## Where next

- [Run agents on your own hardware](run-agents-on-your-own-hardware.md): the zero-cost path.
- [Budgets and selection](../../paper.md#budgets-and-selection), in the research paper.

## Say it in one line

vibey checks recorded spend against your per-cycle cap before every build session, parks a gate when it trips, and only you decide to spend more.

## Improve this guide

If a command here printed something different, or a link does not prove its sentence, that
is a good first contribution. This page is
[`docs/guides/outcomes/cap-agent-spending.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/cap-agent-spending.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which command and what you saw.
