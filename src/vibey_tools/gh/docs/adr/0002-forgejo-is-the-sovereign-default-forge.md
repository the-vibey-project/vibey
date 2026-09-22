# 0002 — Forgejo is the sovereign default forge

**Status:** proposed — needs operator ratification · **Date:** 2026-09-21 ·
**Cites:** sub-doctrine 8.b · **Related:** ADR 0001, ADR-0042 · **Issue:**
[#138](https://github.com/the-vibey-project/vibey/issues/138)

## Context

ADR 0001 built the forge-neutral nouns and an adapter per forge. It chose
`github` as the default `[platform] kind`, which ADR 0001 itself recorded as a
default "that changes neither the argv nor the environment of any `gh` call" —
a conservative choice for a tool that then had exactly one adapter.

Since then sub-doctrine 8.b made the sovereign, self-hosted, free option the
only default for every operational surface, forever: the far reaches of the
repo are the sovereign forges, and GitHub is a paid platform that must be
declared, not assumed. A default of `github` now violates the doctrine twice:
it defaults to a hosted platform, and that hosted platform is a paid
counterparty.

The adapters already exist (ADR 0001's `ForgejoForge`, `GitLabForge`,
`GitHubForge` behind `ForgeSelector`, plus transports). This record flips the
default and the declaration posture; it does not add an adapter.

## Decision

`[platform] kind` defaults to `forgejo`: the self-hosted, free, sovereign
forge, always on, never needing declaration. GitHub and GitLab remain fully
implemented adapters, but they are declared-only: an adopter must write
`kind = "github"` or `kind = "gitlab"` in `.vibey-gh.toml` to use them. They
relay through the sovereign host rather than replacing it: the sovereign
Forgejo instance stays the source of truth for the repository, and the declared
platform is reached through the same `ForgeAdapterInterface` protocol, never by
a module that knows a platform's native dialect (ADR 0001's fourth rule).

The stale "GitHub is the only adapter" claims in the package's architecture
doc and ADR 0001 are corrected in the same change, with the nouns left that
general.

## Options

1. **Keep `github` as default, allow declaration.** Leaves the doctrine
   violated on every install that does not opt in; the default *is* the
   declaration taken away from the adopters.
2. **No default at all; force a declaration.** Sovereign says self-hosted
   free is *the default*, not *a required declaration*: the sovereign path
   must run with no file at all.
3. **Default `forgejo`; GitHub/GitLab declared-only.** The sovereign path
   runs from an empty config; a paid platform needs an explicit human merge.

## Decision

Option 3.

## Security impact

The forgejo transport is plain HTTP with a token (Forgejo's own API); no shell
is reached and no secret is logged. The default host for a declared-less
install is the operator's own (self-hosted) instance; `host` remains validated
as a bare host name.

## Migration

- An adopter with no `[platform]` table gets `forgejo` instead of `github` —
  the sovereign default — and must declare `kind = "github"` explicitly to
  keep GitHub (the declaration).
- A repository that already writes `kind = "github"` is unaffected.

## Consequences

- The tool is sovereign-first not only in doctrine but in its default file: a
  bare install speaks to the operator's self-hosted Forgejo.
- `ForgeSelector.kinds` continues to equal `ADAPTED_PLATFORM_KINDS`; the
  adapters and their test coverage are unchanged.
- The genericization ADR 0001 promised ("a verb arrives with its first
  caller") becomes the norm everywhere the package grows a surface: one
  vibey-owned protocol, one adapter per platform, sovereign default.