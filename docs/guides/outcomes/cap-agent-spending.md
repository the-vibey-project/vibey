---
description: Set a per-cycle dollar or turn cap with vibey budget set; the brake reads it before every BUILD session and parks a gate when it trips, and vibey cost shows each engine's spend from the ledger.
---

# How do I cap what AI coding agents spend, and see where the money went?

**Short answer:** set a per-cycle dollar or turn cap with `vibey budget set`; the brake
reads it before every BUILD session and parks a gate when it trips, and `vibey cost` shows
each engine's spend from the ledger.

An agent left running overnight can spend real money, and a vendor's invoice tells you the
total a month later without saying which task spent it. vibey keeps the spend in its own
ledger, stops the next session when a cap is reached, and waits for you to decide whether
to spend more. The cheapest option comes first: the default engine runs on your own machine
and costs nothing per token.

## Steps

**1. Cap a project when you create it.** Caps are per delivery cycle, and `vibey budget`
shows which cycle a project is in.

```bash
vibey new my-app --repo ~/src/my-app --max-cycle-dollars 15 --max-cycle-turns 200
```

**2. Change the cap whenever you like.** No restart is needed: the brake reads the caps at
every BUILD session, so a running worker applies a change to its next session.

```bash
vibey budget set --max-cycle-dollars 25     # raise it
vibey budget clear --turns                  # remove the turn cap
vibey budget                                # caps, this cycle's spend, the last change
```

Every change is appended to the ledger as a `BudgetCapChanged` event, with who made it
([`vibey budget`](../../reference/cli.md#vibey-budget-project_id)).

**3. Answer the gate when a cap trips.** The next BUILD session parks a `budget_exhausted`
gate instead of starting. `vibey gates` lists it with the command that answers it:

```bash
vibey gates
vibey answer GATE_ID --raw '{}'                   # resume under the caps as they now stand
vibey answer GATE_ID --raw '{"max_dollars": 25}'  # or raise the cap for this one job only
```

**4. Keep paid engines out unless you mean them.** Local engines are chosen first and are
priced at zero; a paid engine is chosen only when no local engine is eligible
([ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md)). A paid
engine is also never selected until you have installed it, signed it in, and recorded a
passing `vibey doctor --conformance --record` run for it
([`vibey doctor`](../../reference/cli.md#vibey-doctor)). To rule paid engines out
altogether, give the worker an allow-list:

```bash
vibey worker --engines gptossloop
```

**5. See where the money went.**

```bash
vibey cost                                    # this cycle against the caps, then each engine
vibey ledger search --kind TurnCompleted --kind BudgetSpent --limit 1000 --json
vibey ledger export PROJECT_ID --billing -o billing.json
```

`vibey cost` shows the cycle's spend and each engine's metered BUILD spend
([`vibey cost`](../../reference/cli.md#vibey-cost-project_id)). The ledger search returns
the latest costed events, every field of each, up to `--limit` ([`vibey ledger`](../../reference/cli.md#vibey-ledger)).
The billing export keeps the metered spend fields for your own reporting.

## Credits are not rate limits

When a vendor refuses a request, vibey asks which kind of refusal it was, because the
right response differs.

- **A rate limit** is a window. It may say when it resets, and waiting is a real option.
- **Exhausted credits** have no clock. Only a person topping up the account changes them,
  so vibey never schedules a wait for them.

The rule is held three times: the `CreditsExhausted` type has no reset time
([`capacity.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/capacity.py)),
a test fails if it ever gains one ([`test_capacity.py`](https://github.com/the-vibey-project/vibey/blob/develop/tests/domain/test_capacity.py)),
and a database `CHECK` constraint refuses a stored credits state with one
([migration 0007](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/db/migrations/0007_engine_health_rotation.sql)).
Either refusal moves the work to the local engine by default, and hands it back only after
a recorded probe shows the paid engine answering again
([ADR-0070](../../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md)).
The move carries a handoff brief that must pass a no-loss check first
([ADR-0004](../../architecture/decisions/0004-no-loss-gate-on-handoff.md)).

## The evidence

| Claim | Where it is proved |
|---|---|
| Caps are read at every BUILD session, from the project's stored config | [Per-cycle caps](../../reference/configuration.md#per-cycle-caps-max_cycle_dollars-max_cycle_turns); [`budget_caps.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/budget_caps.py) |
| Spend is summed from the ledger, not estimated | [`[budget]`](../../reference/configuration.md#budget) |
| A tripped cap parks a gate that can grant more | [ADR-0024](../../architecture/decisions/0024-every-bounded-ladder-parks-with-a-grant.md) |
| Local engines first, paid only when none is eligible | [ADR-0038](../../architecture/decisions/0038-local-engines-are-preferred-first.md) |
| Credits and rate limits are different types | [`capacity.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/capacity.py); [Capacity verdicts](../../paper.md#capacity-verdicts) in the paper |

## Limits

- **`[budget]` in `vibey.toml` is not the brake.** Those keys are not read at runtime; the
  live caps are the ones `vibey new` and `vibey budget` store
  ([`[budget]`](../../reference/configuration.md#budget)). There is no lifetime cap across
  cycles today.
- **The brake stops the next session, not the current one.** It is checked before each
  BUILD session starts, against spend already recorded. Leave headroom for the sessions a
  worker may have running.
- **The figures are what the engines report.** `vibey cost` sums metered spend recorded in
  the ledger. Reconcile it with your vendor's invoice; vibey does not read the invoice.
- **Per-engine totals cross cycles.** The per-engine table accumulates across cycles, and
  its selection count is not a turn count.
- **ULTRA runs need an explicit decision.** A run with no dollar cap parks unless the
  operator declares no cap in a terminal, with a typed phrase
  ([`vibey budget no-cap`](../../reference/cli.md#vibey-budget-no-cap-and-vibey-budget-cap)).

## Go deeper

- [Budgets and selection](../../paper.md#budgets-and-selection), in the
  research paper.
- [Run AI coding agents entirely on your own hardware](run-agents-on-your-own-hardware.md),
  for the zero-cost path.

## Improve this guide

If a command here printed something different, or a link does not prove its sentence, that
is a good first contribution. This page is
[`docs/guides/outcomes/cap-agent-spending.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/cap-agent-spending.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying which command and what you saw.
