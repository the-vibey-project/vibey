# 0106 — Engine sessions search through the hub, each as a principal that holds only `web`

**Status:** proposed · **Date:** 2026-11-24 · **Cites:** SD-01 v1.0 §4; sub-doctrines 10.e, 10.f, 12.c, 12.e · **Related:** ADR-0016, ADR-0017, ADR-0100, ADR-0101, ADR-0102, ADR-0103 · **Amends:** ADR-0102 (§9, "What 9b did not fix"; see its amendment of 2026-11-24)

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

ADR-0102 §9 served `vibey_search` and `vibey_fetch` from the hub, to any principal holding the
`web` scope, budgeted per principal and recorded on the ledger. It did not reach engine sessions:
a session still ran `vibey search` in its own process, was told the SearXNG address and identity
marker through `WEBSEARCH_*` names, had no Brave backup, and spent no hub budget. The only hub
credential a session could have been given was the agent token, which also answers gates and
starts work. ADR-0102 recorded the next step: a short-lived principal the worker mints per
session, holding `web` and nothing else.

SP-LOOPS Phase 6 (`docs/superpowers/plans/2026-11-24-sp-loops-phase6-web-principal.md`; the
spec's Goal 5 and Decision 5, approved by the operator 2026-11-22) builds it. The worker and the
hub are separate processes, and the worker may run where no hub runs, so the questions this
record answers are: what a session's principal may do, who makes it and when it ends, where the
hub finds it, how the session holds its token, what it may spend, how each loop reaches it, and
what a session with no hub is told.

## Rulings (made for this phase, each with its cost if wrong)

- **R1, delivery by file, not environment.** The token is written to `<run folder>/web-token`
  (0600, inside the run's 0700 folder). The session's environment carries only `VIBEY_HUB_URL`
  and `VIBEY_WEB_TOKEN_FILE`. Cost if wrong: the model can read its own token, which is still
  scoped to `web`, capped, and expires with the run.
- **R2, budgets: two checks, one spend.** A session's search or fetch is charged against the
  session's own cap (`[web] session_searches`, `[web] session_fetches`) and against the agent
  principal's existing rolling-hour bucket (`searches_per_hour`, `fetches_per_hour`). Sessions
  cannot raise total web spend. Cost if wrong: sessions can use the agent's whole hourly budget.
- **R3, claudeloop reaches the hub through an MCP connector in its snapshot, not through Bash.**
  Claude Code's own `WebSearch` and `WebFetch` stay disallowed. Cost if wrong: a Bash-based
  search would need a second path to test.
- **R4, lifetime.** A session principal expires at the engine run deadline plus the one-hour
  margin the snapshot sweep uses (`DEADLINE_MARGIN`), counted from the wall-clock time it is
  minted, and is revoked when its session ends, whichever is first.

## Decision

### 1. A session's principal holds only `web`

`SessionPrincipal` (`domain/session_principal.py`) is named `session:<run id>`, carries the run id
and an expiry, and its `scopes` is always `{web}`: a property, not a field, so neither its
constructor nor `dataclasses.replace` can widen it. The name rule has one owner
(`SessionPrincipalPolicy.names_session`), so a session can never share a name with a device
(`device:…`), the agent (`agent`) or the host (`host`).

The hub accepts a session token only on `POST /api/v1/web/search` and `POST /api/v1/web/fetch`
(`SESSION_ROUTES`). Every other route answers 403 before the route runs, view-only reads included,
and both live feeds close with a policy violation. The gate sits in the hub's one principal
dependency rather than in each route's own scope check: measured without it, several routes
answered 422 or 503 to a session before their scope check ran. An unknown, revoked or expired
token is a 401, and a refused call spends nothing and records nothing. The session authenticator
is last in the hub's order (local, device, agent, session), and a session token is never read as
the agent's, because its digest is only in the session registry.

### 2. The worker mints the grant per BUILD run, and revokes it before the snapshot is released

The grant is minted in `BuildImplementHandler`, right after `LoopCapabilitiesService.prepare`
makes the run's own 0700 folder, and revoked in the same `finally` that releases that folder,
before the release: `prepare, open, grant_web, record, start, …, close, release`. Both calls are
synchronous, so a cancellation cannot strand a minted grant or let the release overtake the
revocation. Only engines that take a capability snapshot have a run folder (claudeloop,
claudeloop-local, gptossloop, qwenloop); a run with none gets no grant.

The worker finds the hub the way every other client does: `<[hub] state_dir>/serving.json`,
believed only while the process it names holds the hub's lock, mapped to a loopback literal
(`RunningHub`). It mints with `time.time()`, the clock the hub reads expiry by. No hub, no run
folder, or a mint that fails is never a reason to stop a run: the session is told it has no web,
and why (§8). A replayed job is a new run with a new folder and a fresh grant; a dead run's grant
is never reused.

### 3. The registry: one 0600 file per session, named by the token's digest, in the hub's state folder

`<[hub] state_dir>/sessions/<sha256 hex of the token>.json`, in a 0700 folder, each file 0600,
holding the principal's name, run id and expiry, never the token. One file per session, so
workers minting at once need no lock; each is staged under a unique name and renamed into
place, so the hub never reads half an entry. The hub reads the entry afresh on every lookup, so
`revoke` refuses the token's very next request, as `devices.json` already does for a device.

An in-memory map could not cross the worker/hub process boundary. PostgreSQL would add a table
for state that is never history (and the ledger must never hold a token). A hub route the worker
calls to mint would fail whenever the hub restarts and would need the host token in the worker.
A registry entry that is not owner-only, or is malformed, is logged by its path (which contains
the digest, never the token) and treated as unknown: a planted file can only deny, never grant.

### 4. The token lives only in the run's 0600 file

`SessionTokenStore` creates `<run folder>/web-token` with `O_CREAT|O_EXCL` and mode 0600, and
refuses a folder that is missing, a symbolic link, not owner-only, or already holds a token.
Tokens come from `secrets.token_urlsafe` (32 bytes). The session's client reads the token from the
file on every call and never keeps it. A token never enters the ledger, a log line, a prompt, a
plan, an error, a `repr` or `vibey loops` output; the hub's ledger record names the principal
(`session:<run id>`) and the outcome only.

### 5. Budgets: two checks, one spend (R2)

`WebToolsService` checks the session's own cap first (`[web] session_searches`, default 30;
`[web] session_fetches`, default 15; each 0 to 100000, per session for as long as it runs, never
reset by time), then the agent's rolling-hour bucket. Only when both pass is the session's
counter increased by one and one entry added to the agent's bucket. A 429 names the budget that
was spent: the session's own (`session:<run> has used [web] session_searches = <n> for this
session`) or the agent's (`agent has used [web] searches_per_hour = <n> for this hour, which
session:<run> draws on`). Both keys are read from the person's own `vibey.toml`; the folder the
hub starts in may only lower them (ADR-0101's trust model). The session counters live in the hub's
memory, as the hourly buckets already did.

### 6. claudeloop reaches the hub through the `vibey-web` connector in its snapshot (R3)

When a claudeloop or claudeloop-local run holds a grant, `LoopCapabilitiesService.grant_web`
rewrites the run's capability document once, whole, with one more local MCP server after the
person's own: `vibey-web`, `trust = "local"`, `command = [<vibey>, "mcp", "--scope", "web",
"--token-file", "<run folder>/web-token"]`, `env_allow = ["VIBEY_HUB_URL",
"VIBEY_WEB_TOKEN_FILE"]`. claudeloop starts it as `"type": "stdio"` through the scrubbed launcher,
which passes it exactly those two names; the runner itself changed nothing and still imports
nothing from vibey. A person's own server already named `vibey-web` is never replaced (the
connector is not added, and a warning says so); a document that cannot be rewritten is logged and
the run goes on. Which engines get the connector is data (`EngineDescriptor.web_connector`): true
for claudeloop and claudeloop-local, false for gptossloop and qwenloop, whose own `web_search` and
`web_fetch` tools already run `vibey search` and `vibey fetch` with the grant.

`vibey mcp --scope web [--token-file PATH]` serves exactly `vibey_search` and `vibey_fetch`, as
the session's own principal: it never reads the agent token and never starts a hub. It reads the
hub's address from `VIBEY_HUB_URL` and the token file from `--token-file` (which stands for
`VIBEY_WEB_TOKEN_FILE`). Any other tool name is unknown and nothing is sent; a process with no
grant is served the two tools and told why on each call. `--token-file` without `--scope web`,
or any other scope, is a usage error (exit 2).

### 7. A session's own client, and how it exits

`vibey search` and `vibey fetch` decide first whether they run for a person or a session
(`SessionWebAccess.from_environment`). With both `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` they
ask the hub and nothing else: the address must be `http(s)`, loopback, with a port and no user,
path, query or fragment; an `https` hub is verified with the person's own hub certificate; one
request, never retried. With `VIBEY_WEB_STATE` set, half of the two names, or a name a worker gave
sessions before this phase (`WEBSEARCH_PROVIDER`, `WEBSEARCH_COMMAND`), they refuse. Only with
none of these is the caller a person, who searches the local SearXNG in-process as before.

| Exit | Meaning in a session |
|---|---|
| 0 | Done. |
| 1 | The search or page failed, or the hub said so (422, 502, 503, an unreadable answer). |
| 2 | Usage: a query or URL the hub would refuse, built and refused locally. |
| 67 | The hub refused the token (401): the session's web access has ended (finished, revoked or expired). |
| 69 | No hub answered at the session's address (one line; a read timeout is not sent again). |
| 75 | A `[web]` budget is spent (429), in the hub's own words naming it. |
| 77 | The hub knows the session but does not permit this (403). |
| 78 | This session has no web: `VIBEY_WEB_STATE` says why, or half the hub's names, an old session mark, a hub address off loopback, an unreadable hub certificate, or a token file that is missing, empty, unreadable or not owner-only (named by path). |

### 8. A session with no web is told so, and why, in one name

A session without a grant is given exactly `VIBEY_WEB_STATE=none:<reason name>` and no other web
name. Only a fixed name is ever written (`domain/no_web_reasons.py`), so free text never reaches
an environment; `vibey search` and `vibey fetch` say the same words the session's plan does.

| `VIBEY_WEB_STATE` | When | What the session is told |
|---|---|---|
| `none:no-hub` | No hub was running when the run started | "no hub is running; start one with `vibey serve`" |
| `none:no-run-folder` | The engine takes no capability snapshot (codexloop) | "this engine's session has no run folder of its own to hold a web token, so it was given none" |
| `none:no-token` | A hub was running and minting failed | "a hub is running, but this session's web token could not be made; the worker's log says why" |
| `none:not-given` | A session that is not a BUILD run: the reviewer, conformance, the worker's claudeloop DESIGN and DECOMPOSE provider, the DESIGN session of `vibey work --provider claudeloop` | "the worker that started this session gave it no web access" |
| `none`, or a name this vibey does not know | Read, never written by this vibey | "the worker that started this session did not say why" |

### 9. The one exception to the forbidden rule: three names, overlay only

`MODEL_SESSION_FORBIDDEN` forbids every `VIBEY_*` name in a session. It gains
`overlay_grants`, exactly `VIBEY_HUB_URL`, `VIBEY_WEB_TOKEN_FILE` and `VIBEY_WEB_STATE`: the
worker's own overlay may set them, and nothing else may. `forbids()` is unchanged, so no
allow-list, project or descriptor can admit them, a worker's own copy is never inherited, and
gates (`GATE_FORBIDDEN`) are granted nothing. Both rules also forbid every `WEBSEARCH_*` name,
the form vibey reads each of its own web search settings under (the SearXNG address's
`WEBSEARCH_SEARXNG_URL` among them), beside the Brave key's two aliases: a project's
`[engine_environment]` or `[gates] env_allow` that declares one, or a prefix covering one, is
refused when the worker is built, and the error says to give the project's own key or address
another name in its own environment. The person's own `vibey.toml` keeps its rules, and the
person's own environment is still read under those names. Two scrubs beneath a session keep exactly the two
grant names (`vibey_runners.common.capabilities.web_grant_names.WEB_GRANT_NAMES`), and no third:
the local runner's shell (`ShellEnvironment`), and a local MCP server's `env_allow`
(`BundleSpec`), which is how `vibey-web` receives them.

### 10. The acceptance test is the environment walk

`tests/meta/test_session_environment.py` builds each engine's session environment the way the
worker composes it, for every descriptor in `ALL_DESCRIPTORS` (a new engine is walked
automatically), with a hub running and without one, from a worker environment that holds a fake
SearXNG address, fake Brave keys under all three names, the host and agent tokens and the
pre-Phase-6 `WEBSEARCH_*` marks. It asserts that none of those names or values, no `WEBSEARCH_*`
name and no name containing `SEARXNG` or `BRAVE` reaches any session; that the session's own
token is in no value; and that the session's `VIBEY_*` names are exactly the grant's two or
exactly `VIBEY_WEB_STATE`. It fails, naming the name, when any one forbidden name is let through.
It also builds the worker from a project record whose `[engine_environment]` declares
`WEBSEARCH_SEARXNG_URL` or `VIBEY_SEARXNG_URL`, and asserts the worker refuses to build.

### 11. Stale grants are swept

At start-up the worker removes the registry entries that have expired (`SessionRegistrySweep`,
exclusive expiry, the hub's own rule; idempotent; an unreadable entry is named and left). A
crashed run's token file goes with its run folder, which the existing snapshot sweep removes once
it is older than the run deadline plus `DEADLINE_MARGIN`. On every session spend the hub lists
the registry and drops the counters of each session no longer listed unexpired; it keeps them
all when the listing fails or any entry is unreadable, since that entry may be a live session's.

## Consequences

- Every BUILD session on claudeloop, claudeloop-local, gptossloop and qwenloop searches and
  fetches through the hub, with the hub's Brave backup, the hub's guarded fetch, the person's
  `[web]` budgets and a ledger record, and no session environment holds a SearXNG address, a
  Brave key or a `WEBSEARCH_*` name from the worker's defaults.
- The agent's hourly web budget is now shared with every engine session: a driver model's `429`
  can come from BUILD runs' use in the same hour.
- Sessions outside BUILD have no web: the reviewer, conformance, the claudeloop DESIGN and
  DECOMPOSE provider and the one-shot `vibey work --provider claudeloop` DESIGN session
  (`none:not-given`), and codexloop BUILD runs (`none:no-run-folder`). Each
  would need a run folder of its own to hold a token.

### Known limits, stated plainly

- **A person's own MCP servers may keep the two names.** `[[loops.mcp_servers]]` `env_allow` may
  name `VIBEY_HUB_URL` and `VIBEY_WEB_TOKEN_FILE` too. Accepted: a loopback URL and a path are not
  secrets, and any local server running as the same person can already read the run folder.
- **The model can read its token's path, and so its token** (R1), through the local runner's
  shell or claudeloop's Bash. The token is scoped to `web`, capped, and ends with the run.
- **The hub reads the registry on each session web call:** one lookup per bearer token that is
  not the host's or the agent's (failed authentications are rate-limited per address), and one
  listing of the registry per session spend, to drop ended sessions' counters.
- **Expired registry entries are swept only at worker start.** A worker that runs for weeks keeps
  expired entries until it restarts (the hub refuses them regardless). A staged entry left by a
  kill between write and rename is ignored, never swept; it holds no token.
- **Session counters live in the hub's memory.** A hub restart gives every live session its
  whole cap again; the agent's hourly bucket still bounds total spend.
- **The worker and the hub must agree on `[hub] state_dir`.** Both read the person's own
  `vibey.toml`, as `serving.json` discovery already assumes.
- **The walk covers what `LoopProcessAdapter` spawns, with no project `engine_environment`.**
  It does not walk the one-shot `vibey work --provider claudeloop` DESIGN process, the preflight
  probes, gate commands, or the local runner's own `ShellEnvironment` beneath the session. The
  one-shot DESIGN process is given `VIBEY_WEB_STATE=none:not-given`, as the worker's own DESIGN
  session is, and a test asserts it (its `vibey search` and `vibey fetch` exit 78); a project
  allow-list that names a `WEBSEARCH_*` setting is refused by the rule itself (§9), and the walk
  asserts the worker refuses to build. Both were found by the review of this record and closed
  before it was accepted.
- **Breaking for a project that declared a `WEBSEARCH_*` name.** Its worker no longer starts; the
  error names the entry and says to rename the project's own key or address. Accepted: a project
  relying on those names fails at start with a clear message, rather than handing every session
  the person's SearXNG address.
- **A fetched page's title is empty through the hub** (`"title": ""`): the hub frames the title
  inside its nonce-marked block.
- **Not verified:** a real hub with a real `qwenloop` and a real `claudeloop` session calling
  `vibey-web`. The plan's operator-run probe is pending, and the descriptors' evidence says so.
