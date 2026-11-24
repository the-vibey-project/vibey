---
description: vibey stops at a REVIEW gate that waits for your verdict, and vibey-gh binds every check and review on a GitHub pull request to its exact head commit, so the merge train merges only what passed on that commit.
---

# How do I review an AI-built change before it can merge?

**Short answer:** vibey stops at a REVIEW gate that waits for your verdict, and vibey-gh
binds every check and review on a GitHub pull request to its exact head commit, so the
merge train merges only what passed on that commit.

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** For anyone merging code an agent wrote. Inside a run, answer
> the REVIEW gate with `vibey answer GATE_ID --verdict accept`; on your repository, adopt
> vibey-gh and let its merge train merge. Afterwards no change moves past review without a
> person, and no green tick from an older commit can carry a newer one in.

## The lesson: the stamp on one page

Daniel had a pull request open on his laptop, approved, with one more commit pushed since.

**Daniel:** It was reviewed and it is green. Why can't I merge it?

**Professor Feynman:** Picture a notary who stamps a contract page by page. After the stamp,
someone slips in a new page. Is the new page approved?

**Daniel:** No. The stamp was for the old one.

**Professor Feynman:** That is the whole idea. vibey-gh treats every check and every review as a
stamp on one exact commit, the pull request's head. Push again, and the stamps start over.

**Daniel:** And inside vibey itself?

**Professor Feynman:** There the notary is you. When a run finishes building, it stops and waits
for your verdict, with no timeout, and nothing goes further until you give it. The picture stops
working at the notary's honesty: a machine stamp proves the checks ran on that commit, not that
the checks were the right ones. Choosing them is still your job.

## Steps: inside a vibey run

**1. Let the build check itself.** Each work item runs its verification commands, then a
different engine reviews the diff when the pool has one
([ADR-0035](../../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).

**2. Answer the review gate.** REVIEW parks a gate and waits for a person
([ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md)).

```bash
vibey gates                                   # the review gate, and the command that answers it
vibey answer GATE_ID --verdict accept         # or: --verdict changes, --verdict cancel
vibey answer GATE_ID --raw '{"verdict": "changes", "feedback": ["The retry loop never backs off"]}'
```

Each piece of feedback becomes a finding, and the work goes back to design, or straight to
build when every finding is marked clear
([ADR-0010](../../architecture/decisions/0010-review-loopback-routing.md)).

**3. Let vibey open the pull request, if you want it to.** Put `[publish]` in the project
repository's `vibey.toml` before `vibey new`. After you accept and decline deployment, vibey
pushes the integration branch and opens a **draft** pull request, or creates a private GitHub
repository for a project with no remote ([publishing](../publishing.md)).

```toml
[publish]
mode = "interview"   # off (default), interview (a gate shows what will be pushed), or auto
```

`vibey worker --auto-publish` answers that gate for one unattended worker. Without
`[publish]`, the work stays on a local integration branch (`vibey status --json` names it),
and you, or the [triaged-delivery bridge](../../runbooks/triaged-delivery.md), push it.

## Steps: on your repository, with vibey-gh

vibey-gh ships inside `vibey-engine` and is how this repository merges its own changes.

**4. Install it on a topic branch and review what it generates.**

```bash
vibey-gh doctor       # an offline preflight of what adoption needs
vibey-gh install      # renders the hooks and the managed workflows
vibey-gh check --ci
```

The [adoption checklist](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#adoption-checklist)
lists what it needs. Your `CI` and `Release` workflows stay yours, under exactly those names, and
[the bootstrap merge](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/adoption.md#the-one-thing-no-code-can-remove-the-bootstrap-merge)
is the one step no code can do.

**5. Declare the rules.** Put required checks, approvals and code-owner review in
`.vibey-gh.toml` and apply them with `vibey-gh rulesets`. The managed workflows publish
`PR evaluate / gate` and `PR review / gate` for one commit; a new push restarts them. This
repository requires its own CI checks instead, one approval, code-owner review, and
GitHub's merge queue on `develop` with no bypass
([`.vibey-gh.toml`](https://github.com/the-vibey-project/vibey/blob/develop/.vibey-gh.toml)).

**6. Let the merge train merge.** `vibey-gh merge-train` merges only a pull request that is
current, free of conflicts and requested changes, and green on its exact head
([the merge train](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#the-merge-train)).
An author outside `[merge_train] trusted_authors`, Dependabot included, waits for a person
([ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md)).

## Daniel's teach-back

**Daniel:** Inside a run, REVIEW waits for my verdict, and vibey can open a draft pull request
only if `[publish]` says so. On the repository, every check and review is a stamp on one commit,
so a new push makes them start over, and the merge train merges only what is green on its head.

**Professor Feynman:** Yes. Just remember the stamps prove the checks ran, not that you chose
good ones.

## The evidence

| Claim | Where it is proved |
|---|---|
| A review waits for a recorded answer and never blocks a worker | [ADR-0009](../../architecture/decisions/0009-human-gates-are-parked-jobs.md) |
| Evidence for one commit never authorizes another | [Exact-head evaluation](../../paper.md#exact-head-evaluation-and-the-release-calculus); [vibey-gh's theory](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/docs/theory.md#the-exact-head-invariant) |
| vibey opens a draft pull request only when `[publish]` says so | [`[publish]`](../../reference/configuration.md#publish); [`publish.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/publish.py) |
| Strangers' pull requests are never merged unattended | [ADR-0053](../../architecture/decisions/0053-the-unattended-run-admits-no-stranger.md); [`merge_train.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/vibey_gh/merge_train.py) |
| Branch rules are declared in the repository | [ADR-0036](../../architecture/decisions/0036-the-merge-queue-is-declared-not-clicked.md) |
| vibey's own layers merge only at 100% branch coverage | [ADR-0023](../../architecture/decisions/0023-four-layers-four-floors.md) |

## Limits

- **Publishing is GitHub only**, through `gh`. vibey-gh's workflows are GitHub Actions; its
  Forgejo adapter maps branch rules where Forgejo can
  ([ADR-0096](../../architecture/decisions/0096-on-forgejo-branch-rules-are-mapped-where-they-can-be-and-waived-loudly-where-they-cannot.md)).
- **The model review is advice, not approval.** This repository declares Agent-Field pr-af, a
  paid reviewer, as its default exact-head reviewer
  ([ADR-0090](../../architecture/decisions/0090-pr-af-as-the-declared-default-reviewer.md)),
  with the sovereign lane as second opinion and fallback. That lane reviews only trusted
  authors, never repairs its own findings, and runs on macOS only ([sovereign review runner](../../runbooks/sovereign-review-runner.md)).
  With neither, a pull request is marked as needing a human review.
- **REVIEW runs no security scan by default**: a lint, and no security command
  ([automated review checks](../../reference/configuration.md#review)).
- **The coverage floors are vibey's own.** Your project gets the gates you declare.
- **A self-reviewed item is possible** on a one-engine pool; the ledger records it.

## When it goes wrong

| You see | It means | Do this |
|---|---|---|
| A pull request labelled "needs a human merge" | Its author is not trusted | Review it and merge it yourself |
| Required checks pending after a push | The new head restarted them | Wait for them on the new head |
| No pull request after REVIEW | `[publish] mode` is `off` | Set it before `vibey new`, or push yourself |

## Where next

- [Publishing a finished project](../publishing.md): what vibey pushes, and the interview.
- [vibey-gh's README](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_tools/gh/README.md#what-happens-after-a-push):
  what happens after every push.

## Say it in one line

vibey waits for your review verdict, and vibey-gh merges a pull request only on checks that passed on its exact head commit.

## Improve this guide

If adoption on your repository needed a step this page leaves out, that step is a good
first contribution. This page is
[`docs/guides/outcomes/review-ai-changes-before-merge.md`](https://github.com/the-vibey-project/vibey/blob/develop/docs/guides/outcomes/review-ai-changes-before-merge.md);
[your first hour](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md#your-first-hour)
takes you from a fork to a pull request. Not ready to edit? [Open an issue](https://github.com/the-vibey-project/vibey/issues/new/choose)
saying where adoption stopped.
