# 0042 — Sovereign self-hosted defaults, paid declared-only relays

**Status:** proposed · **Date:** 2026-09-21 · **Cites:** sub-doctrine 8.b ·
**Related:** ADR-0015, ADR-0016, ADR-0027, ADR-0038, ADR-0037 ·
**Evidence:** the engine-pool, deploy, forge and tracker surfaces; sub-doctrine
8.b; the corpus index

**Owes:** the conduct rule is sub-doctrine 8.b. This record decides the
mechanism that enforces it — one vibey-owned protocol per surface, sovereign
self-hosted defaults, paid platforms declared and relayed. The rule is
ratified only by the human merge that carries it.

## Context

Doctrine 8.a makes the purely sovereign path the preference, not the fallback.
But a preference without a concrete default is a platitude: the codebase still
defaulted spreadsheets of surfaces to paid or hosted platforms — the deploy
default was `azure`, the forge default was `github`, the ticketing surface had
no implementation at all, and the engine pool defaulted to the four paid loop
engines with the sovereign pair behind opt-in switches.

Sub-doctrine 8.b (ratified by this PR's merge) names what sovereign means,
surface by surface: the self-hosted, free implementation is the only default,
everywhere; every paid counterparty is declared by a human and relays through
the sovereign host on a vibey-owned protocol.

## Decision

Every operational surface speaks one vibey-owned protocol, realized by
per-platform adapters (ADR-0016). The sovereign, self-hosted, free adapter is
the default of every surface — always on, never needing declaration, never
demoted. Every paid platform adapter is declared-only and relays through the
sovereign host rather than replacing it.

| Surface | Protocol | Sovereign default | Declared-only |
|---|---|---|---|
| Engines | `EngineDescriptor`/`EngineProvider` (ADR-0005) | `qwenloop`, `opencode` | `claudeloop`, `codexloop`, `cursorloop`, `agyloop` |
| Cloud | `CloudClientPort` | self-hosted `openstack` | `azure`, `aws`, `gcp` |
| Forge | `ForgeAdapterInterface` (vibey-gh #138) | self-hosted `forgejo` | `github`, `gitlab` |
| Ticketing | `IssueTrackerPort` | self-hosted free `plane` | `jira`, `linear`, `asana` (+ sibling sovereign `openproject`) |
| Documentation | `DocsPort` | self-hosted free `bookstack` | `confluence`, `notion`, `gitbook` |
| Secrets | `SecretsPort` | self-hosted free `bitwarden` | `lastpass`, `1password`, `proton` |
| Files | `FilesPort` | self-hosted free `nextcloud` | `gdrive`, `icloud` |
| Email | `EmailPort` | self-hosted free `forward-email` | `proton`, `gmail`, `apple` |
| SMS | `SmsPort` | self-hosted free `fossify` | `google-messages`, `imessage` |
| Messaging | `MessagingPort` | self-hosted free Matrix (`matrix`/`element`) | `signal`, `discord`, `slack`, `zoom`, `whatsapp`, `telegram`, `messenger`, `facebook`, `instagram`, `tiktok` |

Mechanically:

- **Engines.** `qwenloop` and `opencode` are resident in the engine pool by
  default, in every phase, no option or switch. The paid loop engines join
  only when declared in `[engines] enabled` or `--engines` (config + CLI, the
  declaration mechanism of ADR-0037's single distribution). The `opencode`
  descriptor is targeted `LOCAL` (it is the local opencode binary, running on
  the operator's machine — a sovereign engine, not a paid one). `qwenloop`
  switches on by default. `_resolve_provider` prefers `opencode` first, then
  `qwenloop`.
- **Cloud.** `ApplicationAzureClientPort` is generalized to
  `CloudClientPort` by rename-with-alias; `AzureTargetScope` becomes a
  provider-discriminated `TargetScope` carrying the provider name, so the
  digest differs per provider. `deploy.target` defaults to `openstack`.
  The sovereign default loads the self-hosted OpenStack adapter (a real
  `openstack` CLI adapter plus the existing in-memory default), and `azure`,
  `aws`, `gcp` adapters are declared-only.
- **Forge.** In vibey-gh, `[platform] kind` defaults to `forgejo` (the
  self-hosted, free sovereign forge) with GitHub and GitLab declared-only.
  The selector and adapters already exist (#138); only the default and the
  declaration posture change, plus the stale "GitHub is the only adapter"
  claims in the architecture doc and ADR-0001.
- **Ticketing.** A vendor-neutral `IssueTrackerPort` protocol is added under
  `application/interfaces/`; its default implementation is self-hosted free
  Plane; Jira is declared-only (the inverse of runbook 01's original plan,
  which made Jira primary).
- **Documentation.** A vendor-neutral `DocsPort` protocol joins the same
  family; its default implementation is self-hosted free BookStack, whose own
  living docs (`properdocs.yml`) are already the first documentation surface;
  Confluence, Notion and GitBook are declared-only relays. Every surface keeps
  a common protocol — engines, cloud, forge, ticketing, documentation — each
  with a sovereign self-hosted default adapter and declared-only paid
  adapters that relay through the sovereign host rather than replacing it.

## Security impact

The trust boundary does not move. Declared adapters still run in the same
working directory and never reach a shell; `CloudClientPort` keeps the
in-memory default so a bare install exercises the deploy surface with no
credentials. The relay posture means the sovereign host stays the source of
truth, so a declared counterparty holds no authority it is not transitively
granted by a protocol call the sovereign host can inspect.

## Migration

- `deploy.target` no longer defaults to `azure`; an existing adopter that
  wants Azure must write `target = "azure"` (the declaration).
- `[platform] kind` no longer defaults to `github`; an existing adopter that
  wants GitHub must write `kind = "github"`.
- `[engines] enabled` / `--engines` now means "add the paid engines listed,
  atop the sovereign pair" — the sovereign pair is always present.
- The engine `opencode` descriptor's tier changes to `LOCAL`; no invocation
  changes, only tier classification.

## Consequences

- Every surface is empty-by-default and sovereign-by-default: a bare install
  runs on qwenloop + opencode, deploys to self-hosted OpenStack, lands in
  self-hosted Forgejo, tracks work in self-hosted Plane, and documents in
  self-hosted BookStack.
- A paid platform can never arrive silently; its declaration is a repository
  change, reviewed and merged by a human.
- Relay-through-sovereign keeps the sovereign host authoritative, which is
  the whole point: the paid platform is a reachable counterparty on a
  vibey-owned protocol, never a second source of truth.
- The interplay with the forge/ticketing surfaces is governance, filed under
  8.b; this record is the mechanism half.