# 0097 — This project runs its own sovereign Forgejo host, on the operator's home server

**Status:** proposed · **Date:** 2026-10-24 · **Cites:** sub-doctrines 8.b, 12.c; Constitution Article III.3 · **Related:** ADR-0042, ADR-0043, vibey-gh ADR-0002 · **Ruling:** #668, item 8

## Context

Sub-doctrine 8.b says a declared paid platform relays through the sovereign host and does not replace
it: the sovereign host stays the source of truth, and the paid platform feeds it. For the forge, the
sovereign host is Forgejo (vibey-gh ADR-0002). This repository, though, declares
`[platform] kind = "github"` and has no sovereign forge behind it, so the relay rule has nothing to
relay from, and GitHub is both the only forge and the source of truth. The storm's relay spike
(`docs/plans/qwenstorm-3.0.0/specs/gap-spike-relay.md`) names this as the open question: either run a
sovereign Forgejo host, or leave GitHub as the only forge with the relay deferred and the reason recorded.

## Decision

**The project runs its own sovereign Forgejo host, on the operator's own machine, a home server, operated
by the operator.** Running one was chosen over deferring the relay.

## Consequences

- **Nothing changes today.** `[platform] kind = "github"` stands, and GitHub stays the forge of record,
  until the host exists and a relay from it is built.
- **The operator takes on operating a service**: its updates, its backups and its security.
- **Much is still undecided**, and this record does not decide it: the host's address and hardware; its
  backups and what happens while it is down (Article III.3 expects a dead local machine to be carried by
  the cloud lanes); the relay's direction and vocabulary, which the spike notes are not yet written; when
  `.vibey-gh.toml` moves from `github` to `forgejo`; and what GitHub becomes afterwards, a relay of the
  Forgejo host.
- **Under 12.c the host is to be declared and reconciled from the repository**, not set up by hand. How
  is open; the installer wave's local stack is the likely home.
- **Rule status.** A decision under 8.b: it owes no sub-doctrine (ADR-0020).
