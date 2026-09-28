# ADR-0075 — Context-bearing surfaces are linked microslice graphs

## Status

Proposed; ratification requires the operator's merge.

## Decision

Adopt the context microslice contract described by proposed sub-doctrine 10.k.
Skills, agent guidance, ADRs, bot scripts, prompts, ledgers and specifications
must be decomposable into small, independently retrievable slices. A slice has a
stable identifier, one purpose, bounded size, provenance and explicit links to
the slices needed to use it safely. Retrieval is conservative: select the
smallest sufficient connected set for the task, measure the context budget, and
decompose or park when the set does not fit. No consumer silently truncates
acceptance criteria, safety constraints, evidence or uncertainty.

Migration is incremental and inventory-driven. Existing large files are legacy
surfaces until their slices are recorded; they are not mass-rewritten merely to
change formatting. New or materially changed content adopts the contract, and
validators report missing identities, broken links, unbounded slices and missing
provenance. The canonical contract and migration checklist live in
`docs/context-microslices.md`.

## Evidence and rationale

The sovereign GPT-OSS lane repeatedly stalled before REVIEW when a full nested
decomposition schema and accumulated project context were sent as one request.
Experiments showed that a smaller JSON-mode request completed while the larger
grammar-shaped request could return empty content. This is a capacity and
correctness boundary, not a reason to discard requirements. Stable links and
retrieval-time selection preserve the requirements while keeping the request
within the measured server budget.

## Consequences

- Context compilation must expose selected slice identities and measured size.
- Every migration can be reviewed and resumed; an incomplete corpus is reported,
  not represented as complete.
- Summaries are pointers, not replacements for source evidence.
- A future change may choose different slice sizes per host and model, but the
  budget and validation rules remain explicit and configurable.

## Related decisions

ADR-0018 (everything as code), ADR-0039 (CDD), ADR-0040 (evidence-bounded
status), ADR-0059 (context retrieval), ADR-0064 (sovereign engines), and
ADR-0069 (workspace packaging).
