# Continuous delivery estimate

This page is a generated, append-only-ledger-backed forecast. Re-run `vibey-gh forecast` after changes to refresh it.

- Recorded at: `2026-10-01T05:53:46.397192Z`
- Source fingerprint: `4b41a9fe12688f2c26dc233206552b7119cacf36b1afeb877ea41a0307778aac`

## Current estimate

- 695 work unit(s) remain; 463 completed
- time: 46.53–57.92 active day(s) after φ=1
- billing actual: elapsed_seconds=unknown, dollars=unknown, turn_completed_events=unknown, budget_turns=unknown, ledger_events=unknown, phase_transition_events=unknown, capacity_rejections=unknown, handoffs=unknown, tool_invocations=unknown, file_edits=unknown, artifacts_produced=unknown
- billing planned: elapsed_seconds=4020492.4406047515–5004000.0, dollars=unknown, turn_completed_events=unknown, budget_turns=unknown, ledger_events=unknown, phase_transition_events=unknown, capacity_rejections=unknown, handoffs=unknown, tool_invocations=unknown, file_edits=unknown, artifacts_produced=unknown
- track record: time={'graded': 0, 'ungraded': 23, 'mean_error': None, 'mean_abs_error': None}; dollars={'graded': 0, 'ungraded': 23, 'mean_error': None, 'mean_abs_error': None}
- billing track records: elapsed_seconds=0 graded/23 ungraded, dollars=0 graded/23 ungraded, turn_completed_events=0 graded/23 ungraded, budget_turns=0 graded/23 ungraded, ledger_events=0 graded/23 ungraded, phase_transition_events=0 graded/23 ungraded, capacity_rejections=0 graded/23 ungraded, handoffs=0 graded/23 ungraded, tool_invocations=0 graded/23 ungraded, file_edits=0 graded/23 ungraded, artifacts_produced=0 graded/23 ungraded
- materials measured: 0/18
- first repair: unknown — no measured material shortfall
- billing unknowns: dollars, turn_completed_events, budget_turns, ledger_events, phase_transition_events, capacity_rejections, handoffs, tool_invocations, file_edits, artifacts_produced
- source problem: billing ledger unavailable at .vibey/billing-ledger.jsonl: [Errno 2] No such file or directory: '.vibey/billing-ledger.jsonl'

## Full machine-readable record

```json
{
  "assumptions": [
    "repository=the-vibey-project/vibey",
    "source_revision=fe52d37cb6b96525e6c28f6144688a2fae9c3882",
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
      "elapsed_seconds": 5004000.0,
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
      "elapsed_seconds": 4020492.4406047515,
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
      "active_days": 38,
      "mean_per_active_day": 35.1578947368421,
      "median_per_active_day": 23.0,
      "total": 1336
    },
    "issues": {
      "open": 690,
      "open_units": 690.0,
      "total": 788
    },
    "pull_requests": {
      "merged": 463,
      "open": 5,
      "open_units": 5.0
    },
    "throughput": {
      "active_merge_days": 31,
      "mean_units_per_merge_day": 14.935483870967742,
      "median_units_per_merge_day": 12.0
    },
    "work_units": {
      "completed": 463.0,
      "remaining": 695.0
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
  "recorded_at": "2026-10-01T05:53:46.397192Z",
  "schema": "vibey-delivery-forecast/v1",
  "source_fingerprint": "4b41a9fe12688f2c26dc233206552b7119cacf36b1afeb877ea41a0307778aac",
  "time": {
    "days_high": 57.91666667,
    "days_low": 46.53347732,
    "first_repair": [],
    "phi_product": 1.0
  },
  "track_record": {
    "dimensions": {
      "artifacts_produced": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "budget_turns": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "capacity_rejections": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "dollars": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "elapsed_seconds": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "file_edits": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "handoffs": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "ledger_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "phase_transition_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "tool_invocations": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      },
      "turn_completed_events": {
        "graded": 0,
        "mean_abs_error": null,
        "mean_error": null,
        "ungraded": 23
      }
    },
    "dollars": {
      "graded": 0,
      "mean_abs_error": null,
      "mean_error": null,
      "ungraded": 23
    },
    "time": {
      "graded": 0,
      "mean_abs_error": null,
      "mean_error": null,
      "ungraded": 23
    }
  }
}
```
