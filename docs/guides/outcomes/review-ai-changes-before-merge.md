---
description: vibey stops at a REVIEW gate that waits for your verdict, and vibey-gh binds every check and review on a GitHub pull request to its exact head commit, so the merge train merges only what passed on that commit.
---

# How do I review an AI-built change before it can merge?

**Short answer:** vibey stops at a REVIEW gate that waits for your verdict, and vibey-gh
binds every check and review on a GitHub pull request to its exact head commit, so the
merge train merges only what passed on that commit.

The risk with an AI-built change is rarely that nobody looked. It is that someone looked at
an earlier version: a review passed, the agent pushed one more commit, and the old green
tick carried the new code into the main branch. vibey answers at two levels. Inside a run,
nothing moves past review until a person records a verdict. On your repository, vibey-gh
treats any evidence gathered for one commit as worthless for the next.

## Steps: inside a vibey run

**1. Let the build check itself.** Each work item runs its own verification commands, and
then a different engine from the one that wrote it reviews the diff, when the pool has one
([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
A failure goes back to the implementer, a bounded number of times, then parks for you.

**2. Answer the review gate.** When the build is done, REVIEW parks a gate and waits. It
has no timeout; the job waits for a person
([ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md)).

```bash
vibey gates                                   # the review gate, and the command that answers it
vibey answer GATE_ID --verdict accept         # or: --verdict changes, --verdict cancel
vibey answer GATE_ID --raw '{"verdict": "changes", "feedback": ["The retry loop never backs off"]}'
```

Each piece of feedback becomes a finding in the ledger, and the work goes back — to design
by default, or straight to build on a fast path when every finding is marked clear
([ADR-0010](../../architecture/decisions/0010-review-loopback-routing.md);
[how each gate is answered](../../reference/cli.md#how-each-kind-of-gate-is-answered)).
Deployment is offered only after you accept.

## Steps: on your repository, with vibey-gh

vibey-gh ships inside `vibey-engine` and runs on GitHub. It is how this repository merges
its own changes.

**3. Install it on a topic branch and review what it generates.**

```bash
vibey-gh doctor       # an offline preflight of what adoption needs
vibey-gh install      # renders the hooks and the managed workflows
vibey-gh check --ci
```

The [adoption checklist](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#adoption-checklist)
lists the branches, secrets and settings it needs. It does not write your `CI` and
`Release` workflows; those stay yours, under exactly those names. And
[the bootstrap merge](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/adoption.md#the-one-thing-no-code-can-remove-the-bootstrap-merge)
explains the one step no code can do for you.

**4. Require the two exact-head gates.** Declare the branch rules in `.vibey-gh.toml` and
apply them with `vibey-gh rulesets`; require `PR evaluate / gate` and `PR review / gate`
beside your own checks. Both are published for one commit. A new push starts them again.

**5. Let the merge train merge.** `vibey-gh merge-train` merges a pull request only when it
is current with its target, free of conflicts and requested changes, and green on its
exact head ([the merge train](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#the-merge-train)).
A pull request from an author outside `[merge_train] trusted_authors`, Dependabot
included, is labelled "needs a human merge" and waits for a person
([ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md)).

## The evidence

| Claim | Where it is proved |
|---|---|
| A review waits for a recorded answer and never blocks a worker | [ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md) |
| Evidence for one commit never authorizes another | [Exact-head evaluation](../../paper.md#exact-head-evaluation-and-the-release-calculus), in the paper; [vibey-gh's theory](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/theory.md#the-exact-head-invariant) |
| Strangers' pull requests are never merged unattended | [ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md); [`merge_train.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/merge_train.py) |
| Branch rules are declared in the repository | [ADR-0036](../../architecture/decisions/0036-the-merge-queue-is-declared-not-clicked.md); [`.vibey-gh.toml`](https://github.com/the-vibey-project/vibey/blob/develop/.vibey-gh.toml) |
| vibey's own layers merge only at 100% branch coverage | [ADR-0023](../../architecture/decisions/0023-four-layers-four-floors.md); [`ci.yml`](https://github.com/the-vibey-project/vibey/blob/develop/.github/workflows/ci.yml) |

## Limits

- **vibey itself does not open the pull request.** A run leaves its work on a local
  integration branch (`vibey status --json` names it). The
  [triaged-delivery bridge](../../runbooks/triaged-delivery.md) pushes and opens one, or you
  do.
- **GitHub only, in practice.** vibey-gh's workflows are GitHub Actions.
- **The model review is advice, not approval.** Without a declared paid review or a running
  sovereign review lane, every pull request is marked as needing a human review. The
  sovereign lane reviews only trusted authors' pull requests, never repairs its own
  findings, and its runner is macOS only today
  ([sovereign review runner](../../runbooks/sovereign-review-runner.md)).
- **REVIEW runs no security scan by default.** Its automated checks run a lint by default
  and no security command; both lists live in the stored project record, not in
  `vibey.toml` ([automated review checks](../../reference/configuration.md#review)).
- **The coverage floors are vibey's own.** Your project gets the gates you declare. A
  `minimum_coverage` rule in `.vibey-gh.toml` is GitHub's code-coverage rule over the data
  you upload, not ADR-0023's branch floor.
- **A self-reviewed item is possible.** On a one-engine pool the implementer reviews its own
  diff; the ledger records it, and your REVIEW verdict is the independent look.

## Go deeper

- [The six-phase machine](../../paper.md#the-six-phase-machine), in the research paper.
- [vibey-gh's README](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#what-happens-after-a-push),
  for what happens after every push.

## Improve this guide

If adoption on your repository needed a step this page leaves out, that step is a good
first contribution. This page is
[`docs/guides/outcomes/review-ai-changes-before-merge.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/review-ai-changes-before-merge.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying where adoption stopped.
