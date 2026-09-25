# 0067 — The hub: `vibey serve`, one HTTP surface for every Krypton client

**Status:** proposed · **Date:** 2026-09-25 · **Cites:** SD-01 v1.0; sub-doctrines 10.c, 10.f, 10.g, 10.i, 10.j, 12.c, 12.d, 12.f, 12.j, 8.a, 10.a · **Related:** ADR-0009, ADR-0016, ADR-0017, ADR-0018, ADR-0023, ADR-0054, ADR-0055, ADR-0059, ADR-0065 · **Evidence:** `develop` at `30356862`, read 2026-09-25 · **Delivers:** runbook 12's work item 1; the server side runbook 08 depends on

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

## Context

The 3.0.0 client suite -- the desktop app, the mobile and web app, the VS Code extension,
all "Krypton" (ADR-0065) -- needs one thing vibey did not have: a network surface. Every
client until now shelled out to `vibey … --json` (ADR-0059: "never its database"), which
works on the host and nowhere else. A phone cannot run the CLI.

Two facts shaped the answer:

- **The building blocks existed, unused.** `vibey_bootstrap` already ships FastAPI
  request-timing middleware, a token-bucket rate limiter, a metrics snapshot, HMAC helpers,
  signed action tokens and a constant-time compare. The dogfood rule (ADR-0017, 10.e) says
  use them.
- **The contract existed too.** Every read a client needs already has a `--json` document
  with keys the extension reads (doctrine 7), printed by a presenter class in `vibey/cli/`.
  A second, hand-written JSON for HTTP would drift from it within a release.

And one fact shaped the risk: a surface a browser can reach is attacked by pages the user
merely visits (DNS rebinding, cross-origin reads), and a surface on the LAN is reachable by
every device on it. SD-01 §2 is explicit that being on the network proves nothing.

## Decision

**`vibey serve` is the hub.** One FastAPI app (`infrastructure/hub/app.py`) over one
application service (`application/hub/hub_service.py`), composed in `cli/serve.py`. It
ships behind a `hub` extra (`pip install 'vibey[hub]'`) for the reason `operator` is an
extra: a worker serves nothing, and a web stack in `dependencies` would put its CVE surface
on every install.

1. **Use cases over the existing services only.** `HubService` owns no query and no write.
   It authorises, then delegates: gates answer through `GateAnswerService` (the
   compare-and-set of #1147, idempotent per request id), bumps go through
   `QueuePriorityService` and its grant (ADR-0054), budgets are read through
   `ProjectBudgetService` and never changed, the ledger is searched through `LedgerSearch`.
   It cannot drift from the CLI and cannot route around a check the CLI makes.

2. **One contract, two readers.** Every document is rendered by the CLI's own presenters
   (`CliHubDocuments`); `vibey status --json`'s dict moved into `cli/status.py` so the hub
   shares it. A test holds each hub document equal to the matching `--json` output against
   the same database.

3. **Loopback by default; the LAN only when declared (12.c).** `vibey serve` binds
   127.0.0.1 unless `--host` names another address, and refuses (exit 2) any non-loopback
   address unless `vibey.toml` declares `[hub] lan = true`. Both are needed: a cloned
   repository's `vibey.toml` alone never opens the LAN. `vibey doctor` gains a `hub-exposure` line:
   FAIL when a running hub listens where nothing declares it may (10.f, 10.j), UNKNOWN when
   no hub runs or its runtime record is stale -- never a PASS it did not observe.

4. **Scopes, deny by default (10.c, 12.j).** A caller holds a set of `view`, `answer`,
   `spend`, `run`, `bump`; each action needs exactly one, and the empty set permits
   nothing. Answering a spending gate (`budget_exhausted`, the `deploy_*` gates) needs
   `spend` as well as `answer`. A bump is always requested as the declared queue source
   `vibey-hub`, so the host's `[queue.priority] sources` decides whether the hub may reorder
   at all: a device's `bump` scope is necessary and never sufficient.

5. **Never from the hub.** Declaring paid use, lifting or changing a cap, the DSN,
   migrations and the canon are not hub actions under any scope (`NEVER_FROM_THE_HUB`), and
   no route offers them. They stay on the host's configuration and the operator's merge.

6. **The host's own key.** A process on the host presents `Authorization: Bearer <token>`,
   where the token is 32 random bytes in `<state_dir>/token`, mode 0600 in a 0700
   directory; a token file others can read is refused. It names the host principal, which
   holds every scope. There is no unauthenticated "dev mode" (runbook 12 had proposed one):
   loopback is not an identity, since every local process and every rebinding page shares
   it.

7. **Web hardening before any route.** A `Host` allowlist (the loopback names and port,
   plus, with the LAN declared, this computer's names and the declared `[hub] names`)
   refuses anything else with 421 -- the DNS-rebinding defence. No CORS header is ever sent.
   Every response carries `default-src 'none'` CSP, `frame-ancestors 'none'`, `nosniff`,
   `no-referrer` and `no-store`. Requests are rate-limited by vibey_bootstrap's token bucket,
   after authentication, one bucket per principal, so one caller's flood never starves
   another; requests that prove nothing draw from a small bucket per client address. A
   body over 64 KiB, or one without a length, is refused before it is read. No proxy is
   trusted for client addresses.

8. **Versioned, and the document committed.** Every route is under `/api/v1`; the OpenAPI
   3.1 document is served at `/api/v1/openapi.json`, printed by `vibey serve --openapi` (no
   database), and committed at `docs/reference/hub-api.json`. A test fails when they differ.

### What this change does not do, and where it goes

The hub arrives in three changes, each reviewable alone:

- **Core (this ADR's first change):** everything above.
- **Live:** an additive migration adding `NOTIFY vibey_ledger_appended` on ledger append,
  and a WebSocket per project that resumes "after seq N" -- a position, never a timestamp
  (10.g). Lane events tailed by byte offset.
- **Pairing and trust:** mDNS/DNS-SD advertisement of `_vibey._tcp` (the `zeroconf`
  package), a self-signed certificate made on first run and stored through `SecretsPort`,
  pairing by QR and 6-digit code (2 minutes), per-device keys, signed requests with nonce
  and timestamp, pairing/grant/revocation as ledger events, revocation immediate, CSRF for
  the served web app, and `spend` re-verified per action.

Not in any of the three: starting, stopping or winding down lanes, ULTRA controls, and the
push relay (8.a/10.a). The `run` scope exists so a grant can name it; no route needs it yet.

## Consequences

- **The independent reviews of the first change** found one blocking defect: an answer
  sent with a request id to a gate that was no longer open skipped the spend check. The
  service now reads the gate by id whatever its state and authorises on its kind. They also
  hardened the token store (no symlinks; owner and mode checked on the open file), bounded
  request bodies, moved the rate limit after authentication, and made the reserved list a
  test over the routes that exist. Deferred to pairing: lane paths are absolute, which a
  `view`-only device should not learn (relative paths for devices), and TLS before any
  credential crosses the LAN.

- A client on the host can use the hub today with the token file; a device on the LAN
  cannot until pairing lands, because there is no way to give it a principal.
- The REVIEW phase's opt-in to deployment is a generic `choice` gate, indistinguishable by
  kind from a harmless choice, so `answer` alone can answer it. Closing that needs the gate
  to say it spends (a gate attribute, not a kind list); recorded here rather than guessed.
- Answering a gate reads the open gates to learn its kind before the answer; the kind of a
  gate never changes, so the check cannot race the answer.
- The hub's doctor route runs only the checks it can run cheaply (the database, the
  exposure) and says so in its document; `vibey doctor` on the host remains the full check.
- `LoopsCommand` gains `report()`, and `vibey status --json` renders through
  `cli/status.py`: no output changes.

## Alternatives considered

- **A hand-written JSON layer in `infrastructure/`.** Rejected: two contracts for one set of
  facts, and the extension's goldens would test only one of them.
- **Serving the whole CLI over HTTP (run `vibey … --json` per request).** Rejected: a
  process per request, and the CLI's exit codes are a poor error channel.
- **Binding the LAN by a flag.** Rejected (12.c): a flag typed once is not a declaration
  anyone can review; the `vibey.toml` key is.
- **`vibey_bootstrap`'s `verify_api_key_header`.** Not used: it reads its key from the
  environment and fails open when unset. Its `compare_secrets` is used instead, and a
  fail-closed file token covers the gap; the reason is written at the call site.
