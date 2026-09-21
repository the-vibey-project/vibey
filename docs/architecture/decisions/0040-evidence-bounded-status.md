# 0040 — Evidence-bounded status for runs, features and research claims

**Status:** proposed · **Date:** 2026-09-21 · **Cites:** sub-doctrine 10.f · **Related:** ADR-0039, ADR-0020 · **Evidence:** the cutoff-bounded Qwen storm extraction and its event logs

**Owes:** the conduct rule is sub-doctrine 10.f. This ADR records why status
claims must be bounded by evidence; it does not replace the canon's rule.

## Context

Autonomous software systems emit several signals that look like completion but
are not equivalent: a model verdict, a runner marker, a terminal event, a clean
test, a local commit, a pushed branch and an accepted pull request. They can
arrive in different orders, disagree, or be absent because the process is still
alive. A generated file can also look like an implementation while not being
tracked by the repository or connected to its tests.

The Qwen storm record demonstrated each distinction. Some runs emitted a
provisional verdict without the completion marker. One exhausted its turn limit
and failed without a verdict. A fresh run directory existed at the cutoff with
no events, while a storm process was still alive. The extraction therefore kept
those states separate instead of converting partial activity into success.

## Decision

All operational and research status is evidence-bounded. A status claim names:

1. the object being claimed (item, run, repository, branch or pull request);
2. the evidence source (tracked code, test result, remote response or event
   stream); and
3. the scope and observation cutoff.

The status vocabulary keeps at least these distinctions:

```text
unknown       evidence is absent, stale or contradictory
active        work has not reached a terminal event
blocked       a concrete condition prevents the next safe step
failed        a terminal event records unsuccessful work
verified      the stated checks passed for the stated revision
published     the stated remote head and pull request are evidenced
```

No weaker signal promotes a stronger one: a verdict does not promote a run to
completed, a marker does not promote a feature to delivered, a local commit does
not promote a branch to published, and a generated artifact does not promote a
feature to implemented. Missing evidence is reported as missing, never inferred
from silence or activity. When sources disagree, the narrowest supported status
wins until a fresh check resolves the disagreement.

## Consequences

Evidence extraction must be cutoff-bounded and reproducible. Live monitors must
not call a still-running process terminal, and papers must distinguish tracked
compact evidence from ignored raw logs. Completion gates become stricter, but
the resulting failure is actionable: the next CDD iteration knows whether it
needs a test, a source change, a clean-up, a fresh remote query or human input.
