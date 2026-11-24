---
description: How `vibey-gh forecast` estimates the remaining delivery time and cost from real repository history, how to run it, and why the published estimate is currently stale and billing-free.
---

# Estimate how long the remaining work will take

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `vibey-gh forecast` reads open issues, pull requests and the
> integration branch's commits, and prints how much work remains and a range of active days to
> finish it. Unknowns stay unknown, never zero. Run it yourself in about a minute. The published
> [current estimate](../estimate.md) is a snapshot from 2026-10-30: its hourly refresh workflow
> has been switched off on GitHub since 2026-11-05, it has never carried billing, and its history
> read now truncates at 1,000 pull requests.

## The lesson

Daniel had the estimate page open and was frowning at a date.

**Daniel:** Professor, this says 41 to 53 active days left. Is that a promise?

**Professor Feynman:** It is a weather forecast, and a weather forecast is only worth something if
it tells you what it measured and how often it has been right. This one is built from the shop's
own books: how much work is still open, how much was finished, and how fast it has been finished
on the days anyone worked.

**Daniel:** So remaining work divided by speed.

**Professor Feynman:** Nearly. Each open issue or pull request counts by its size label: an extra
small is half a unit, an extra large is twelve. Then the speed is a band, the mean and the median
of units finished per active day, so you get a range, not a single number. And the forecast
stretches the range when the conditions are bad: a slow network, a weak machine, a missing
permission.

**Daniel:** It says `materials measured: 0/18`.

**Professor Feynman:** Then it measured none of those conditions, and it says so instead of
pretending they were perfect. An unknown stays unknown. The same goes for money: with no billing
export, every dollar figure says `unknown`, not zero.

**Daniel:** And `0 graded`?

**Professor Feynman:** That is the honest part. A forecast is graded once the work it predicted
is done. None has been graded yet, so nobody knows how good this forecaster is. Here my weather
picture fails in a second way, too: a weather service updates itself. This page is updated only
when a workflow runs and its pull request merges, and neither has happened since early November.
Look at the date before you look at the number.

## Do it

Run on 2026-11-24 in a clone of this repository with vibey-engine 0.4.0 and a logged-in `gh`.

1. Calculate a forecast without writing anything.

   ```bash
   vibey-gh forecast --no-record --no-report
   ```

   You should see lines like these (the billing lines are long and are cut here):

   ```text
   vibey-gh forecast: 672 work unit(s) remain; 871 completed
   vibey-gh forecast: time: 50.15–74.67 active day(s) after φ=1
   vibey-gh forecast: billing actual: elapsed_seconds=unknown, dollars=unknown, ...
   vibey-gh forecast: materials measured: 0/18
   vibey-gh forecast: first repair: unknown — no measured material shortfall
   vibey-gh forecast: source problem: billing ledger unavailable at .vibey/billing-ledger.jsonl: [Errno 2] No such file or directory: '.vibey/billing-ledger.jsonl'
   ```

2. Optional: add real billing. Export the operator-only billing projection from a project's ledger
   first, then forecast again.

   ```bash
   vibey ledger export PROJECT_ID --billing --out .vibey/billing-ledger.jsonl
   vibey-gh forecast --no-record --no-report
   ```

   With a readable billing export, the `dollars`, `turn_completed_events` and event-count
   dimensions are calculated from it instead of reported `unknown`. This step was not run for
   this page.

3. Record it. Without `--no-record` and `--no-report`, the forecast is appended to
   `.vibey/delivery-estimates.jsonl` and `docs/estimate.md` is rewritten.

   ```bash
   vibey-gh forecast
   ```

## Daniel's teach-back

**Daniel:** The forecast counts open work by size label, measures how fast work has been finished
per active day, and gives a range of days. It records every assumption with the number, leaves
unmeasured conditions and missing billing as unknown, and keeps an append-only history so each
forecast can be graded later. Today none has been graded, the published page is weeks old, and
dollars are unknown because nothing exports billing in CI.

**Professor Feynman:** All correct. Add one warning: it reads at most 1,000 issues and 1,000 pull
requests, and the repository now has more pull requests than that, so the history it reads is
cut short without a word.

## What is estimated

The calculus uses the paper's six materials (network, hardware, software, agent, information,
agency) and their eighteen coordinates (availability, stability and reliability of each). A
supplied `--materials` JSON file can replace unknown coordinates with measured readings. Unknown
coordinates remain unknown; they do not silently become healthy or zero. The `phi` constants are
recorded with every forecast, because the paper defines the shape of the dilation but leaves its
empirical parameters to measurement.

- **Remaining work** is open non-pull-request issues plus open pull requests.
- **Completed work** is merged pull requests.
- **Size labels** `size/XS`, `size/S`, `size/M`, `size/L` and `size/XL` map to work-unit weights
  (0.5, 1, 3, 6 and 12 by default); an unlabelled item uses the small weight.
- **The report** includes mean and median work-unit throughput per active merge day, commit counts,
  active days, and the estimator's time and dollar track records.

A refresh is a new record in the append-only `.vibey/delivery-estimates.jsonl` ledger. The same
complete forecast input is never appended twice, while a billing-only change still creates a new
record. Each record is also shaped as the core ledger's `DeliveryEstimateRecorded` event, so an
archive or the conductor can replay it without a second vocabulary; that kind is on the
[publication allowlist](ledger-publication.md).

## Billing

Pass a JSON Lines file exported by the operator-scoped billing projection with
`--billing-ledger`, or put it at the configured default `.vibey/billing-ledger.jsonl`. Plain
`vibey ledger export` is public and withholds raw spend; the explicit `--billing` projection keeps
only the numeric billing fields and the operational event kinds this calculator needs. The forecast
uses the same billing vocabulary as the conductor's budget brake:

| Dimension | Meaning |
| --- | --- |
| `dollars` | `TurnCompleted.cost_usd` plus `BudgetSpent.dollars` |
| `turn_completed_events` | the ledger event count, never a guessed turn count |
| `budget_turns` | explicit `BudgetSpent.turns` |
| `elapsed_seconds` | wall-clock span of the supplied ledger events |
| event counts | phase transitions, capacity rejections, handoffs, tools, file edits, and artifacts |

The report shows actual cumulative usage, low and high planned usage, and low and high completion
totals for every dimension. With no billing export, those dimensions are reported as unknown
rather than zero. Planned usage is derived from observed usage per completed work unit; elapsed
time also uses the observed throughput band and the material dilation.

## Flags and settings

`vibey-gh forecast` flags:

| Flag | Default | What it does |
|---|---|---|
| `--repo OWNER/NAME` | the configured forge repository | The repository to read. |
| `--limit N` | `1000` | The most issues, and the most pull requests, read from GitHub. See the warning below. |
| `--billing-ledger PATH` | `[estimate.forecast] billing_ledger` | The billing projection to read. |
| `--materials PATH` | none | Measured material readings: a list of `{coordinate, value, source}`. |
| `--record PATH` / `--no-record` | `[estimate.forecast] ledger` | Append to this ledger, or read and append nothing. |
| `--report PATH` / `--no-report` | `[estimate.forecast] report` | Write the human page here, or write none. |
| `--summary PATH` | `$GITHUB_STEP_SUMMARY` | Also write the report lines here. |
| `--json` | off | Print the complete forecast as JSON. |
| `--strict` | off | Exit non-zero when a source could not be read. |

`[estimate.forecast]` in `.vibey-gh.toml`, as this repository sets it:

```toml
[estimate.forecast]
ledger = ".vibey/delivery-estimates.jsonl"
report = "docs/estimate.md"
billing_ledger = ".vibey/billing-ledger.jsonl"
phi_floor = 0.1
phi_epsilon = 0.01
phi_exponent = 1.0
unknown_factor = 1.0
size_weights = { xs = 0.5, s = 1.0, m = 3.0, l = 6.0, xl = 12.0 }
```

The code is [`vibey_gh/delivery_estimate.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/delivery_estimate.py),
[`delivery_sources.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/delivery_sources.py)
and [`estimate_ledger.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/estimate_ledger.py).

## The published estimate, and its state today

[`.github/workflows/delivery-estimate.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/delivery-estimate.yml)
is written to run at 17 minutes past every hour, and by hand, never on each push, pull request or
issue. It runs `vibey-gh forecast`, regenerates the paper's forecast figure, and pushes the ledger,
`docs/estimate.md` and `docs/paper.md` to the `automation/delivery-estimate` branch with a pull
request that runs every CI gate like any other change.

What was observed on 2026-11-24 (from the GitHub API and this repository at develop `d91a3791e`):

- **The workflow is switched off.** Its state on GitHub is `disabled_manually`, since 2026-11-05.
  Its last run was 2026-11-05 at 03:29 UTC. The file still says hourly; the switch lives in
  GitHub's settings, not in the repository.
- **The page is a snapshot.** [`docs/estimate.md`](../estimate.md) was recorded
  2026-10-30T23:47Z. The last refresh that merged is #1734; the later refresh pull requests
  #1819, #1833 and #1835 were closed without merging.
- **It has never carried billing.** The workflow runs bare `vibey-gh forecast`, and CI has no
  `.vibey/billing-ledger.jsonl`, so every published dollar figure is `unknown`.
- **Its track record is empty.** No forecast has been graded against an outcome.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `source problem: billing ledger unavailable at .vibey/billing-ledger.jsonl` | No billing export was found, so cost is unknown. | Export one with `vibey ledger export PROJECT_ID --billing`, or accept unknown cost. |
| `source problem: issues: ...` or `pull requests: ...` | `gh` could not read the tracker. | Run `gh auth status`; add `--strict` in automation so this fails the job. |
| `materials measured: 0/18` | No condition was measured, so no dilation is applied (φ=1). | Supply `--materials` readings if you have them. |
| The figures look too optimistic or too low on completed work | The history read may be truncated. `gh issue list` and `gh pr list` stop at `--limit` with no warning, and no problem is recorded. On 2026-11-24 the repository had 945 issues and 1,028 pull requests, past the default 1,000. | Pass `--limit` above the repository's totals, for example `--limit 5000`. |
| The published page's date is weeks old | The refresh workflow is disabled, or its pull requests are not merging. | Run `vibey-gh forecast` yourself, or re-enable the workflow and merge its pull request. |

The truncation is a defect against sub-doctrine 10.g ("consume the whole gap"): a figure computed
over an unknown subset is not evidence. It is reported, not fixed, by this page.

## Where next

- [The current estimate](../estimate.md), the generated page, read with its date in mind.
- [What gets published](ledger-publication.md), for what the billing projection keeps and why plain
  exports never carry spend.
- [Cap agent spending](outcomes/cap-agent-spending.md), for the budget brake that shares the billing
  vocabulary.

## Say it in one line

vibey-gh forecast turns open work and past throughput into a range of days and keeps unknowns
unknown; run it yourself, because the published copy is stale and billing-free.
