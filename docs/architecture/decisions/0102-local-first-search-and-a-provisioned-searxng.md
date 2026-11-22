# 0102 — Local-first search, and the SearXNG vibey installs and runs itself

**Status:** proposed · **Date:** 2026-11-22 · **Cites:** SD-01 v1.0; sub-doctrine 8.b; proposed sub-doctrine 12.q (ADR-0101); sub-doctrines 10.h, 12.c, 12.d, 12.e · **Related:** ADR-0016, ADR-0017, ADR-0018, ADR-0042, ADR-0057, ADR-0100, ADR-0101

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.

## Context

The operator ruled on 2026-11-21 that all search vibey controls asks a **local** SearXNG first,
and the Brave Search API only as a backup when that SearXNG fails and a key is set. Task 9c of
SP-ACP built the policy: `VIBEY_SEARXNG_URL` (default `http://127.0.0.1:28180`, a port chosen to
be uncommon and below every ephemeral range), an identity check before a SearXNG is believed (a
`GET /config` that must answer SearXNG's own JSON shape, and, with `VIBEY_SEARXNG_INSTANCE` set,
that `instance_name`), and Brave reached only after a failure, said once.

A policy that asks a local SearXNG is only as good as the SearXNG being there. On a fresh
computer nothing listens on 28180, so every search either fails with the fix or goes to Brave.
The person sees "install SearXNG" in a doctor line and has to find out how. Sub-doctrine 8.b
makes the sovereign, self-hosted option the default on every surface; a default that the person
must assemble by hand is not one.

## Decision

### 1. The policy (Task 9c, restated)

Search asks the local SearXNG first, always; Brave answers a query only when SearXNG failed and a
key is configured, and the person is told once per process. `VIBEY_SEARCH_PROVIDER=brave` is
refused: Brave is declared-only (8.b), never the primary. An engine session never receives the
Brave key.

### 2. vibey provisions the SearXNG itself, through the bootstrap that installs PostgreSQL

The ACP bootstrap gains a fifth step, after PostgreSQL, run once per process inside a prompt turn
and never in observe mode. It is asked with `session/request_permission` ("Download and run
SearXNG (searxng/searxng@sha256:<first 12>) in a container on 127.0.0.1:<port>? ..."), and only
the "Install SearXNG" option installs; "Not now", a cancel, a timeout, any other option id, or a
switch to observe installs nothing. It is not asked when the person's environment names their own
SearXNG (`VIBEY_SEARXNG_URL`), when a SearXNG already passes the identity check, when vibey
installed one before, or when the person stopped it for good (below). Before asking, the port is
probed: anything listening on 127.0.0.1 there that is not SearXNG with vibey's marker -- a dev
server, someone else's SearXNG -- means nothing is asked and the reason is said, so no unit is
left failing at every login. `[acp] searxng = "ask" | "never"` governs it (default `ask`); it needs
`auto_services` too, since it loads a unit. Like `install_postgres`, a project's `vibey.toml` may
only say `never`.

`vibey searxng install` does the same from a terminal, without an editor: it prints the question
and asks; with `--yes` (the person's answer in advance) it still prints the question, then goes
on. It and `uninstall` take the same cross-process `acp-bootstrap.lock` the editor's step holds,
so the two never write the same files at once. `vibey searxng status`, `uninstall [--purge]` and
the hidden `serve` complete the group.

**Stopped for good.** `vibey acp unload` and `vibey searxng uninstall` leave a `disabled` mark in
the person's SearXNG folder: from then on step 3 never loads the unit, the keep-alive lets go of
it, step 5 never asks again and `serve` refuses to run -- until `vibey searxng install` removes the
mark. `[acp] searxng = "never"` stops step 3 from loading or restarting an installed unit and says
so; it does not unload one, and the service manager still starts it at login until `uninstall`.

On allow: the image is pulled through the ACP process-group runner (no shell, stdin closed, its
own process group stopped as a whole past `[acp] install_timeout_seconds`, a minimal
environment); the settings and the provision record are written; the unit is written and loaded
exactly as the hub's is (ADR-0101: the planner, `restart = [acp] restart` with the throttle, the
installer that never replaces an edited unit, the digest record, the loader, the keep-alive and
its notices, `vibey acp unload`); then the step waits, bounded, until the SearXNG answers the
identity check with vibey's marker. A failed part says one cleaned reason and leaves search on its
Brave-backup path. Two editor windows never install twice: the step runs inside the bootstrap's
in-process turn and the cross-process `acp-bootstrap.lock`, and a window that waited for the lock
looks again and finds it installed. Once installed, step 3 writes and loads the SearXNG unit beside
the hub's at every session start, and the keep-alive restarts it like the worker.

### 3. A container, with a runtime vibey finds and never installs

SearXNG is a Python web application with its own dependency tree; a container is the one form in
which it runs the same way on macOS and on Linux, and stops cleanly. vibey uses the person's own
runtime -- `podman` preferred, else `docker` -- found once, and **never on the PATH**: an editor
launched from a project may have that project's `bin/` (direnv, `node_modules/.bin`) first, and
the runtime is recorded and run again at every login. It is looked for only in fixed trusted
folders (`TRUSTED_RUNTIME_DIRS`: on macOS `/opt/homebrew/bin`, `/usr/local/bin`, `/usr/bin`,
`/Applications/Docker.app/Contents/Resources/bin`; on Linux `/usr/bin`, `/usr/local/bin`, `/bin`,
`/snap/bin`), and a candidate must be a regular executable file, not writable by anyone, owned by
root or the person, whose links lead only into `TRUSTED_RUNTIME_ROOTS` (Homebrew's Cellar, Docker
Desktop's bundle, `/usr`, `/snap`). Every use -- `serve`, doctor, status, uninstall, purge --
vets the recorded runtime again against those checks: a record naming any other binary is
refused with one cleaned notice and nothing is run. The recorded runtime need not be the one a
fresh look would choose now -- `find` only chooses at install -- so a second runtime installed
later (podman beside Docker Desktop, a Homebrew docker CLI ahead of it) never stops `serve`,
`uninstall` or `--purge`. vibey never installs a runtime: with none, it says how to get one, once, and
does nothing else.

The runtime sees the same small environment at install and in the unit (home, user, locale,
temporary folder, the rootless runtime's folder and bus) and never `DOCKER_HOST`,
`DOCKER_CONTEXT`, `DOCKER_CONFIG`, `CONTAINER_HOST` or `CONTAINER_CONNECTION`: a login unit has
none of them, so install and the unit always talk to the runtime's own default daemon. Install
refuses a `DOCKER_HOST`/`CONTAINER_HOST` that is not a local socket (it would publish the port
and mount the settings on another machine), and says when a local one is ignored.

### 4. The image is pinned by digest, and refreshed by a reviewed change

The image is the constant `SEARXNG_IMAGE` in `src/vibey/domain/searxng.py`:

    docker.io/searxng/searxng@sha256:fc1d81d7e9d04d3c8b3e23c7162feddf5c3d6aecd32e67a56eaabcb8d8747f79

It was read on 2026-11-22 from `registry-1.docker.io`, as the digest of `searxng/searxng:latest`'s
multi-platform index, with an anonymous pull token and a `HEAD` of the manifest -- the registry's
read-only API, no credentials. `scripts/searxng_image_digest.py` (standard library only) is how it
is read again; a new digest is a reviewed change, never an automatic one, and no test touches the
network (a test pins the constant's format). Every image reference that reaches a runtime must
**equal** `SEARXNG_IMAGE` -- not merely look like `docker.io/searxng/searxng@sha256:<64 hex>`: a
record naming any other digest is never run. **Updating** follows a new pin: the old record is
still read (every check but the pin) to recognise vibey's own instance by its marker -- so the
port probe never calls it "not vibey's" -- and to offer the update. Doctor and status say "a
newer pinned image is available (old -> new)"; the editor's step 5 asks once per process, in a
session that may run things, "Update vibey's SearXNG (old -> new)?" with **Update** and **Not
now**; and `vibey searxng install` updates it. On allow, the new image is pulled, the record
rewritten with the same marker and settings, and the running unit restarted. Nothing updates on
its own: until it is allowed, the old container keeps running, and `serve`, at its next start,
refuses the old record with exit 78 and says how to update rather than run another image. `vibey searxng serve` never pulls (`--pull=never`, and it
checks the image is present first), so nothing downloads when the person logs in.

### 5. One command line, decided in the domain

`SearxngPlan.run_argv` is the whole container command:

    <runtime> run --rm --name vibey-searxng-<uid>
      --label vibey.searxng.owner=<uid> --label vibey.searxng.image=<first 12>
      --pull=never --read-only
      --cap-drop ALL --security-opt no-new-privileges --pids-limit 256 --memory 512m
      [--userns=keep-id, podman only] --user <your uid>:<your gid>
      --publish 127.0.0.1:<port>:8080
      --volume <settings.yml>:/etc/searxng/settings.yml:ro
      --tmpfs /etc/searxng --tmpfs /var/cache/searxng --tmpfs /tmp
      docker.io/searxng/searxng@sha256:<digest>

Never `--privileged`, never the host network, never the runtime's socket, never a home folder, no
environment variable. The port is published on 127.0.0.1 only. The container gets one secret,
its own `secret_key`, inside the settings it mounts read-only. The unit runs `vibey searxng
serve` (the running install's own launcher, ADR-0101), never through `supervisor exec
--env-file`: that file holds the database URL. `serve` checks the record, the label, the settings
file, the runtime and the image, removes a container a killed run left behind, and `execve`s the
runtime with that small environment and a fixed PATH.

The container's name carries the person's uid, and its labels say whose it is: on a shared
rootful daemon names are daemon-wide, so vibey removes a container of its name (`serve` at every
start, `uninstall`, `acp unload`) only after `inspect` shows `vibey.searxng.owner=<this uid>`. A
container of that name without it is left alone and said.

A refusal `serve` cannot get past without the person (no record, a record vibey would not write,
stopped for good, a runtime it will not run, no image) exits 78, never with a traceback: the unit's
throttle (launchd's `ThrottleInterval`, systemd's start limit) spaces the restarts, and doctor and
`vibey searxng status` say why. A container that would not go exits 1, which may pass next time.

### 6. The settings, the record, and where search finds them

Both live in the person's own configuration folder, `<config>/searxng/` (0700), written
atomically (staged `O_EXCL|O_NOFOLLOW`, 0600, synced, renamed), never through a link, and refused
in a folder that is a link or someone else's. They are read the same careful way: opened without
following a link and non-blocking (a FIFO never hangs search, doctor or `serve`), and refused
unless each is a regular file the person owns, closed to everyone else (0600 or narrower), within
a size cap, in a folder that is the person's and closed too. The pair is staged and renamed
settings-then-record; a failed second rename removes the first; and a pair whose markers
disagree -- a crash between the renames, or two writers interleaved -- is made again, both files,
instead of being kept as a pair that could never pass the identity check:

- `settings.yml`, written once: `use_default_settings: true`, a random 32-byte hex
  `server.secret_key` from `secrets`, `server.limiter: false` and `public_instance: false`
  (loopback only), `bind_address: "0.0.0.0"` inside the container, `search.formats: [html,
  json]`, `general.instance_name: "vibey-<32 random hex>"` (the identity marker),
  `donation_url`/`contact_url: false`, metrics off.
- `provision.json`: `{image, port, marker, label, runtime}`, read back with every value checked,
  so a changed record cannot widen the command line.

When the person's environment sets neither `VIBEY_SEARXNG_URL` nor `VIBEY_SEARXNG_INSTANCE`,
search reads the URL (its loopback port) and the marker from this record -- the person's, never
a project's -- so `vibey search` in any terminal finds vibey's SearXNG and believes only it. Their
environment still wins.

### 7. Trust: the person's configuration only

Everything that reaches disk, a command line or a unit comes from the person's own configuration:
the image and argv are constants, the label is `[supervisor] label_prefix` from their own
`vibey.toml` -- never taken from the record (a record naming another label, the hub's say, is
not believed, so it can never make `uninstall` unload anything but the SearXNG unit) -- the
folder is their configuration folder, the launcher is the running install's, and the runtime
comes from the trusted folders. A
project's `vibey.toml` can only say `[acp] searxng = "never"`. No sudo, no root (the loader
refuses as root, and the container never runs as uid 0), user-level units only.

### 8. The identity check is not authentication

The marker tells vibey's SearXNG from another program on the port -- a dev server, a second
SearXNG, a container someone else started. It does not stop code running as the same person:
such code can bind 127.0.0.1:28180 while SearXNG is down, or read the marker from the record or a
session's environment. The real answer is that engine sessions should not talk to SearXNG
directly at all. Task 9b (§9) serves search and fetch from the hub, as MCP tools; it does not yet
reach engine sessions, for the reason §9 records, so for sessions this remains a known limit, not
a guarantee.

### 9. Search and fetch served from the hub (Task 9b, amendment of 2026-11-22)

The hub is the one vibey process that holds the Brave key, so it serves both tools itself, to any
principal holding the new `web` scope: `POST /api/v1/web/search` runs §1's policy in the hub's
own process (the key read from the hub's environment and never returned, logged or recorded; the
once-per-process notice handed back as `notice` on the answer that triggered it), and
`POST /api/v1/web/fetch` is a guarded fetch of one page. The MCP server offers them as
`vibey_search` and `vibey_fetch` (ADR-0100), listed only to an agent holding `web`. `web` is the
agent principal's by default and honours `[hub] agent_scopes`; a paired device gets it only when
the host offers it.

- **The fetch reaches only public pages.** Only `http` and `https`; no user name or password; no
  local, internal or metadata name; no address spelt other than canonically; every address a
  name resolves to must be public (loopback, private, link-local, carrier-grade NAT,
  unique-local, multicast, reserved, unspecified and documentation space refused, and an
  IPv4-mapped, NAT64 or 6to4 address judged by the IPv4 address inside it, Teredo refused), and
  the connection is pinned to the address checked. Every redirect is checked again, at most
  `[web] max_redirects`, never from https to http. Fixed headers only (`Accept-Encoding:
  identity`); any other content encoding is refused unread, so nothing is decompressed; only
  `[web] content_types` are read (PDF refused, not extracted); bounded in bytes, characters and
  one total deadline that fails closed -- every step, across every redirect, gets only the time
  left, and a cancelled fetch resolves, connects, sends and reads nothing more.
- **Budgeted and recorded.** Per principal and rolling hour (`[web] searches_per_hour`,
  `fetches_per_hour`; a 429 names the budget). Each use, refusals and failures included, is a
  `WebSearched` or `WebFetched` ledger event: the principal, the tool, the outcome, the backend,
  and for a fetch the hosts reached -- never the query and never the URL -- on the named project's
  ledger, else on every project's. With no ledger to write to, nothing is searched or fetched.
- **The person's `[web]`, narrowed by a project's.** Budgets, host lists and bounds are read from
  the person's own `vibey.toml`; the folder the hub started in may only tighten them.
- **ACP and chat.** Neither tool is a `/` command: the chat is typed by a person, who has a
  browser. The rule for when one is: a search is a read to a session's mode (observe may run it
  when the hub grants `web`); a fetch needs `web` in the mode itself, and no mode holds it.

**The residual risk, stated plainly.** A query and a URL leave the computer; a model steered by
what it read can put data into either. That is exfiltration, and these tools carry it by design.
The budgets, the ledger record, the host lists and the refusal of every non-public address bound
it and make an attempt visible after the fact. They do not prevent it.

**What 9b did not fix: engine sessions.** Sessions still run `vibey search` and `vibey fetch`
directly (§1, §8): they are still told the SearXNG address and the marker, still have no Brave
backup, and their fetch is still the older one. They have no channel to the hub: the worker
reaches PostgreSQL, not the hub, may run on a machine (a Kubernetes pod) where no hub runs, and a
session is given no hub address and no credential by design. The only hub credential there is
for a model is the agent token, which also answers gates and starts work; handing it to a session
would widen what a session can do, so 9b does not. The recommended next step is a session
principal of its own: a short-lived capability the worker mints per session (bound to the job,
holding `web` and nothing else, with its own budget), accepted by the hub, and given to the
session through the overlay that today carries the SearXNG settings -- after which the overlay
drops `WEBSEARCH_SEARXNG_URL` and the marker. Until then, code a session runs is as able to
reach SearXNG, and to read the person's files, as it was.

## What is verified, and what is not

Verified here, by tests that fake every runtime and network call: the argv (a golden test), the
digest format, the writers' modes, atomicity and link refusal, the search precedence against a
hostile project folder, the bootstrap step's table (ask, never, observe, cancel, timeout, reject,
unknown option, already answering, the person's own URL, no runtime, a second window), the unit
planning, the keep-alive, `acp unload` removing the container, and the doctor line; and, from the
first review: the trusted-folder runtime and its vetting by every consumer, the label never taken
from the record, the owner label before any removal, the FIFO and mode checks, the pair written
together or made again, the stop mark, the port probe and the refused remote daemon. Each
security rule has a test that fails against a naive implementation, and the suite itself fails any
test that would exec or spawn a real `docker` or `podman`.

**Not verified: nothing was pulled or run against a real container.** The flag set is chosen for
the image as it is documented, and these need a real run before release: that the image's
entrypoint starts with `--read-only` and the three tmpfs mounts (it may want to write elsewhere);
that it runs as the person's uid with `--user` (and podman's `--userns=keep-id`) and still reads
its own files; that `--cap-drop ALL` leaves it nothing it needs (an image that starts as root and
drops to its own user would need `SETUID`/`SETGID`); that a 0600 settings file is readable through
the mount under rootful docker, rootless podman, podman machine and Docker Desktop; that SELinux
hosts (Fedora) need `:Z` on the volume; and that SIGTERM to the runtime client stops and removes
the container on both runtimes. Three of these are probably failures, not just unknowns:

- **Rootless Docker** maps the host uid to root inside its user namespace, so `--user <uid>:<gid>`
  becomes a subordinate uid that probably **cannot read** a 0600 settings file the host user
  owns. Rootless podman has `--userns=keep-id`; rootless Docker has no equivalent flag.
- **SELinux (Fedora)**: a container under `container_t` is probably denied reading a file
  labelled `config_home_t` without relabelling, so the volume probably needs `:Z` (or `:z`) there.
  vibey does not add it yet.
- **Docker before 28 on Linux**: ports published on 127.0.0.1 could be reached by other machines
  on the same layer-2 segment (an upstream issue fixed in 28). "Published on 127.0.0.1 only" is
  only as good as the runtime's own forwarding rules.

Also unverified: that `rm -f` of a container that is already gone, and `inspect` of one that never
existed, say "no such container" in the words vibey matches. An opt-in test (`VIBEY_TEST_SEARXNG_CONTAINER=1`) documents what
such a run should assert.

## Consequences

- A person who allows it gets local search that works on a fresh computer, kept running, and
  stopped for good by `vibey acp unload` or `vibey searxng uninstall` (the unit, the container,
  and a mark so no session starts it again) until `vibey searxng install`; `--purge` also
  removes the image and the files.
- The bootstrap can download a container image on the person's word; it says so, once, and never
  at login. The question names the image and the port but not its size, which was not measured
  here (the digest was read with a `HEAD`, which carries none).
- A new pinned digest is a change someone reviews; an installed SearXNG is then offered the
  update (editor, doctor, status), never updated on its own. The old image is left in the runtime
  (disk only) until removed by hand.
- The Docker CLI's `currentContext` (in `~/.docker/config.json`, reached through `HOME`) can still
  name an ssh or tcp context: install and the unit read it alike, but "local" is only as good as
  that file.
- The Brave backup is reachable only in vibey's own processes -- the hub's web tools among them
  (§9) -- never in an engine session, which still searches SearXNG directly (§9, "What 9b did
  not fix").
- A driver model reached over MCP searches and fetches through the hub with no SearXNG address
  and no key of its own, budgeted, recorded on the ledger, and held to public pages; a query or
  a URL it is steered to write can still carry data out (§9).
