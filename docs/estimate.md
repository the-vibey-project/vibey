---
description: "The last published delivery forecast for this repository: a generated snapshot recorded 2026-10-30, with no billing and no graded track record."
---

<!-- Everything above "## Current estimate" except the two "Recorded at" and "Source
fingerprint" lines is written by hand. `vibey-gh forecast` rewrites this whole file
(`DeliveryEstimateLedger.write_report` in src/vibey_tools/gh/vibey_gh/estimate_ledger.py), so
this header is lost at the next refresh unless the generator learns to emit it. -->

# Read the current delivery estimate, and its date

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This is the last forecast `vibey-gh forecast` published for
> this repository. It was recorded on **2026-10-30** and has not been refreshed since: the hourly
> workflow has been switched off on GitHub since 2026-11-05. Its dollar figures are all `unknown`,
> it measured none of its 18 conditions, and none of its 54 earlier forecasts has been graded. For
> today's figures, run `vibey-gh forecast --no-record --no-report` yourself.

**How to read this page.**

**Daniel:** Professor, which line do I read first?

**Professor Feynman:** The date. Then "work units remain" and the range of active days. Then the
three lines that say how much to trust it: `materials measured`, the `track record`, and any
`source problem`. Here they say nothing was measured, nothing has been graded, and there was no
billing. The JSON below is the same record in full, for a program to read.

How the forecast is made, every flag, and why the published copy is stale are in
[the delivery estimate guide](guides/delivery-estimate.md).

- Recorded at: `2026-10-30T23:47:12.253134Z`
- Source fingerprint: `1669750d6f8119c6d8b1174779bc48590096ae37ee240ac5401eb4dd48835ab9`

## Current estimate

- 685 work unit(s) remain; 779 completed
- time: 41.33–52.69 active day(s) after φ=1
- billing actual: elapsed_seconds=unknown, dollars=unknown, turn_completed_events=unknown, budget_turns=unknown, ledger_events=unknown, phase_transition_events=unknown, capacity_rejections=unknown, handoffs=unknown, tool_invocations=unknown, file_edits=unknown, artifacts_produced=unknown
- billing planned: elapsed_seconds=3570793.3247753535–4552615.384615385, dollars=unknown, turn_completed_events=unknown, budget_turns=unknown, ledger_events=unknown, phase_transition_events=unknown, capacity_rejections=unknown, handoffs=unknown, tool_invocations=unknown, file_edits=unknown, artifacts_produced=unknown
- track record: time={'graded': 0, 'ungraded': 54, 'mean_error': None, 'mean_abs_error': None}; dollars={'graded': 0, 'ungraded': 54, 'mean_error': None, 'mean_abs_error': None}
- billing track records: elapsed_seconds=0 graded/54 ungraded, dollars=0 graded/54 ungraded, turn_completed_events=0 graded/54 ungraded, budget_turns=0 graded/54 ungraded, ledger_events=0 graded/54 ungraded, phase_transition_events=0 graded/54 ungraded, capacity_rejections=0 graded/54 ungraded, handoffs=0 graded/54 ungraded, tool_invocations=0 graded/54 ungraded, file_edits=0 graded/54 ungraded, artifacts_produced=0 graded/54 ungraded
- materials measured: 0/18
- first repair: unknown — no measured material shortfall
- billing unknowns: dollars, turn_completed_events, budget_turns, ledger_events, phase_transition_events, capacity_rejections, handoffs, tool_invocations, file_edits, artifacts_produced
- source problem: billing ledger unavailable at .vibey/billing-ledger.jsonl: [Errno 2] No such file or directory: '.vibey/billing-ledger.jsonl'

## Full machine-readable record

```json
{
  "assumptions": [
    "repository=the-vibey-project/vibey",
    "source_revision=f754757367720fe3a14b3be92025a63df6a88863",
    "billing_ledger=.vibey/billing-ledger.jsonl",
    "remaining work is open non-PR issues plus open PRs, weighted by size labels",
    "completed work is merged PRs, weighted by the same size labels",
    "throughput band is the observed mean/median merged work-unit rate per active merge day",
    "phi_i uses ((1-floor) / max(value-floor, epsilon))^exponent for measured coordinates; floor=0.1, epsilon=0.01, exponent=1",
    "unknown material coordinates use phi=1",
    "planned billing dimensions scale observed cumulative usage by remaining/completed work"
  ],
  "billing": {
    "actual": {
      "artifacts_produced": null,
      "budget_turns": null,
      "capacity_rejections": null,
      "dollars": null,
      "elapsed_seconds": null,
      "file_edits": null,
      "handoffs": null,
      "ledger_events": null,
      "phase_transition_events": null,
      "tool_invocations": null,
      "turn_completed_events": null
    },
    "completion_high": {
      "artifacts_produced": null,
      "budget_turns": null,
      "capacity_rejections": null,
      "dollars": null,
      "elapsed_seconds": null,
      "file_edits": null,
      "handoffs": null,
      "ledger_events": null,
      "phase_transition_events": null,
      "tool_invocations": null,
      "turn_completed_events": null
    },
    "completion_low": {
      "artifacts_produced": null,
      "budget_turns": null,
      "capacity_rejections": null,
      "dollars": null,
      "elapsed_seconds": null,
      "file_edits": null,
      "handoffs": null,
      "ledger_events": null,
      "phase_transition_events": null,
      "tool_invocations": null,
      "turn_completed_events": null
    },
    "planned_high": {
      "artifacts_produced": null,
      "budget_turns": null,
      "capacity_rejections": null,
      "dollars": null,
      "elapsed_seconds": 4552615.384615385,
      "file_edits": null,
      "handoffs": null,
      "ledger_events": null,
      "phase_transition_events": null,
      "tool_invocations": null,
      "turn_completed_events": null
    },
    "planned_low": {
      "artifacts_produced": null,
      "budget_turns": null,
      "capacity_rejections": null,
      "dollars": null,
      "elapsed_seconds": 3570793.3247753535,
      "file_edits": null,
      "handoffs": null,
      "ledger_events": null,
      "phase_transition_events": null,
      "tool_invocations": null,
      "turn_completed_events": null
    },
    "unknowns": [
      "dollars",
      "turn_completed_events",
      "budget_turns",
      "ledger_events",
      "phase_transition_events",
      "capacity_rejections",
      "handoffs",
      "tool_invocations",
      "file_edits",
      "artifacts_produced"
    ]
  },
  "history": {
    "commits": {
      "active_days": 49,
      "mean_per_active_day": 33.673469387755105,
      "median_per_active_day": 24.0,
      "total": 1650
    },
    "issues": {
      "open": 664,
      "open_units": 664.0,
      "total": 926
    },
    "pull_requests": {
      "merged": 779,
      "open": 21,
      "open_units": 21.0
    },
    "throughput": {
      "active_merge_days": 47,
      "mean_units_per_merge_day": 16.574468085106382,
      "median_units_per_merge_day": 13.0
    },
    "work_units": {
      "completed": 779.0,
      "remaining": 685.0
    }
  },
  "materials": [
    {
      "coordinate": "network.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from reachability of every endpoint the stage needs",
      "value": null
    },
    {
      "coordinate": "network.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from variance of reachability and latency over time",
      "value": null
    },
    {
      "coordinate": "network.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from whether the network delivers what it claims (loss, corruption)",
      "value": null
    },
    {
      "coordinate": "hardware.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from the fit calculus: whether this machine's memory and paging can host the local model",
      "value": null
    },
    {
      "coordinate": "hardware.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from drift in free memory, paging pressure and thermals over time",
      "value": null
    },
    {
      "coordinate": "hardware.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from whether the machine computes correctly (faults, wear)",
      "value": null
    },
    {
      "coordinate": "software.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from the fit calculus: whether the local runner holds the model; tool versions against pins",
      "value": null
    },
    {
      "coordinate": "software.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from version and configuration drift",
      "value": null
    },
    {
      "coordinate": "software.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from whether the software behaves as specified",
      "value": null
    },
    {
      "coordinate": "agent.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from a model or a human present to act, and their load",
      "value": null
    },
    {
      "coordinate": "agent.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from turnover, fatigue and load over time",
      "value": null
    },
    {
      "coordinate": "agent.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from historical success rate when acting",
      "value": null
    },
    {
      "coordinate": "information.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from required inputs at hand: specification, docs, credentials",
      "value": null
    },
    {
      "coordinate": "information.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from staleness and drift of those inputs",
      "value": null
    },
    {
      "coordinate": "information.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from whether the inputs are true when consulted",
      "value": null
    },
    {
      "coordinate": "agency.availability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from permissions actually held: merge rights, token scopes, ruleset bypass, and paid credit \u2014 permission to act by spending is agency",
      "value": null
    },
    {
      "coordinate": "agency.stability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from revocation risk of those permissions",
      "value": null
    },
    {
      "coordinate": "agency.reliability",
      "distance": null,
      "phi": 1.0,
      "source": "unmeasured \u2014 would come from whether each permission honours its grant when exercised",
      "value": null
    }
  ],
  "problems": [
    "billing ledger unavailable at .vibey/billing-ledger.jsonl: [Errno 2] No such file or directory: '.vibey/billing-ledger.jsonl'"
  ],
  "recorded_at": "2026-10-30T23:47:12.253134Z",
  "schema": "vibey-delivery-forecast/v1",
  "source_fingerprint": "1669750d6f8119c6d8b1174779bc48590096ae37ee240ac5401eb4dd48835ab9",
  "time": {
    "days_high": 52.69230769,
    "days_low": 41.32862644,
    "first_repair": [],
    "phi_product": 1.0
  },
  "track_record": {
    "dimensions": {
      "artifacts_produced": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "budget_turns": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "capacity_rejections": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "dollars": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "elapsed_seconds": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "file_edits": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "handoffs": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "ledger_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "phase_transition_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "tool_invocations": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      },
      "turn_completed_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 54
      }
    },
    "dollars": {
      "graded": 0,
      "mean_abs_error": null,
      "mean_error": null,
      "ungraded": 54
    },
    "time": {
      "graded": 0,
      "mean_abs_error": null,
      "mean_error": null,
      "ungraded": 54
    }
  }
}
```
