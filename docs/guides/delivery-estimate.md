# Continuous delivery estimate

`vibey-gh forecast` maintains the current delivery estimate from real repository
history. It reads open issues, open and merged pull requests, and the integration
branch's commit history. A refresh is a new record in the append-only
`.vibey/delivery-estimates.jsonl` ledger; the same complete forecast input digest is
not appended twice, while a billing-only change still creates a new record.

The generated [current estimate](../estimate.md) is the quickest human view. The GitHub
Actions job also writes the same lines to its job summary and refreshes the page after
integration changes, issue and pull-request changes, and on a schedule.

## What is estimated

The calculus uses the paper's six materials and eighteen coordinates. A supplied
`--materials` JSON file can replace unknown coordinates with measured readings. Unknown
coordinates remain unknown; they do not silently become healthy or zero. The configurable
`phi` constants are recorded with every forecast because the paper defines the shape of
the dilation but leaves its empirical parameters to measurement.

Remaining work is open non-pull-request issues plus open pull requests. Merged pull
requests are completed work. Size labels (`size/XS`, `size/S`, `size/M`, `size/L`, and
`size/XL`) map to configurable work-unit weights; an unlabelled item uses the configured
small weight. The report includes the mean and median work-unit throughput, commit
counts, active days, and the estimator's time and dollar track records.

## Billing materials

Pass a JSONL file exported by the operator-scoped billing projection with
`--billing-ledger`. Plain `vibey ledger export` is intentionally public and withholds raw
spend; the explicit `--billing` projection keeps only the numeric billing fields and
operational event kinds needed by this calculator. The forecast uses the same billing
vocabulary as the conductor's budget brake:

| Dimension | Meaning |
| --- | --- |
| `dollars` | `TurnCompleted.cost_usd` plus `BudgetSpent.dollars` |
| `turn_completed_events` | the ledger event count, never a guessed turn count |
| `budget_turns` | explicit `BudgetSpent.turns` |
| `elapsed_seconds` | wall-clock span of the supplied ledger events |
| event counts | phase transitions, capacity rejections, handoffs, tools, file edits, and artifacts |

The report shows actual cumulative usage, low/high planned usage, and low/high completion
totals for every dimension. If no billing export is supplied, those dimensions are
reported as unknown rather than zero. Planned usage is derived from observed cumulative
usage per completed work unit; elapsed time additionally uses the observed throughput
band and the material dilation.

```bash
vibey ledger export PROJECT_ID --billing --out .vibey/billing-ledger.jsonl
vibey-gh forecast
vibey-gh forecast --json --strict
```

The JSON record is also shaped as the core ledger's `DeliveryEstimateRecorded` event, so
an archival or conductor integration can replay it without inventing a second event
vocabulary. Raw engine chatter and credentials remain outside the public publication
allowlist.
