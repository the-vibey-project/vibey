## Title
docs: surfaces default to their lanes — the configuration reference, the Kubernetes guide, the governance facts and the CHANGELOG follow the flip

## Why
`surfaces-default-flip` made `queue` the default surface transport (sub-doctrine 8.f; draft
ADR-0047 §15). `surfaces-docs-wave` documented `direct` as the default because it had to land
first, to carry the measurement and the operator's decision the flip is gated on. Doctrine 7.b:
"When the law moves or grows, every surface follows in the same change"; CLAUDE.md: the four
agent-surface trees change together. This lane makes every page that names the default say
`queue`, and records the breaking change. Part of ADR-0047 lane S34, owned by the docs wave.

## Required behaviour
1. `docs/reference/configuration.md`: `[surfaces] transport` defaults to `queue`; the entry says
   `direct` is kept for unit tests and deployments without a bus, logs that 8.f is not held, and
   is set with `VIBEY_SURFACES_TRANSPORT=direct`.
2. `docs/guides/kubernetes.md`: `surfaceLanes.transport` defaults to `queue`; a laptop runs
   `vibey surface serve --all` (with `vibey install --rabbitmq` for the broker, R33).
3. The ADR (`docs/architecture/decisions/0047-*.md`): its "Migration" section records the flip's
   commit; its status stays whatever the operator's merge made it.
4. CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees: every sentence that says
   surfaces are reached in-process by default now says they are reached through their lanes.
5. `CHANGELOG.md`, through the release tooling's usual path: the breaking change, in the words
   of `surfaces-default-flip`'s `BREAKING CHANGE:` footer.

## Where to change
- The files above only.

## Acceptance criteria
- [ ] `grep -rn 'transport.*direct' docs/reference/configuration.md` shows `direct` only as the opt-out, never as the default.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes; the book builds.

## Tests to write first (TDD)
- None: the doc meta-tests are the tests.

## Checks the lane must run (all must pass)
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- Code. Canon text (the operator's).

## Lane card
- **Depends on:** `surfaces-default-flip`.
- **Must keep passing unchanged:** the doc meta-tests.
- **Standing constraints:** the four agent trees change together; evidence stays bounded (10.f).

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
