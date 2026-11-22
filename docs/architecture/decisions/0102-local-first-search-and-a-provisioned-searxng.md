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
SearXNG (`VIBEY_SEARXNG_URL`), when a SearXNG already passes the identity check, or when vibey
installed one before. `[acp] searxng = "ask" | "never"` governs it (default `ask`); it needs
`auto_services` too, since it loads a unit. Like `install_postgres`, a project's `vibey.toml` may
only say `never`.

`vibey searxng install` does the same from a terminal, without an editor: it prints the question
and asks (`--yes` is the person's answer in advance). `vibey searxng status`, `uninstall
[--purge]` and the hidden `serve` complete the group.

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
runtime -- `podman` preferred, else `docker` -- found once on their PATH and kept as an absolute
path. vibey never installs a runtime: with none, it says how to get one, once, and does nothing
else.

### 4. The image is pinned by digest, and refreshed by a reviewed change

The image is the constant `SEARXNG_IMAGE` in `src/vibey/domain/searxng.py`:

    docker.io/searxng/searxng@sha256:fc1d81d7e9d04d3c8b3e23c7162feddf5c3d6aecd32e67a56eaabcb8d8747f79

It was read on 2026-11-22 from `registry-1.docker.io`, as the digest of `searxng/searxng:latest`'s
multi-platform index, with an anonymous pull token and a `HEAD` of the manifest -- the registry's
read-only API, no credentials. `scripts/searxng_image_digest.py` (standard library only) is how it
is read again; a new digest is a reviewed change, never an automatic one, and no test touches the
network (a test pins the constant's format). Every image reference that reaches a runtime must
match `docker.io/searxng/searxng@sha256:<64 hex>`; a tag, another repository or another registry
is refused before any command runs. `vibey searxng serve` never pulls (`--pull=never`, and it
checks the image is present first), so nothing downloads when the person logs in.

### 5. One command line, decided in the domain

`SearxngPlan.run_argv` is the whole container command:

    <runtime> run --rm --name vibey-searxng --pull=never --read-only
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
--env-file`: that file holds the database URL. `serve` checks the record and the image, removes a
container a killed run left behind, and `execve`s the runtime with an environment of the
variables a runtime finds its daemon by and a fixed PATH.

### 6. The settings, the record, and where search finds them

Both live in the person's own configuration folder, `<config>/searxng/` (0700), written
atomically (staged `O_EXCL|O_NOFOLLOW`, 0600, synced, renamed), never through a link, and refused
in a folder that is a link or someone else's:

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
`vibey.toml`, the folder is their configuration folder, the launcher is the running install's. A
project's `vibey.toml` can only say `[acp] searxng = "never"`. No sudo, no root (the loader
refuses as root, and the container never runs as uid 0), user-level units only.

### 8. The identity check is not authentication

The marker tells vibey's SearXNG from another program on the port -- a dev server, a second
SearXNG, a container someone else started. It does not stop code running as the same person:
such code can bind 127.0.0.1:28180 while SearXNG is down, or read the marker from the record or a
session's environment. The real answer is that engine sessions should not talk to SearXNG
directly at all. Task 9b serves search and fetch to sessions from the hub, as MCP tools, so
sessions are given no SearXNG address and no Brave key; until then this is a known limit, not a
guarantee.

## What is verified, and what is not

Verified here, by tests that fake every runtime and network call: the argv (a golden test), the
digest format, the writers' modes, atomicity and link refusal, the search precedence against a
hostile project folder, the bootstrap step's table (ask, never, observe, cancel, timeout, reject,
unknown option, already answering, the person's own URL, no runtime, a second window), the unit
planning, the keep-alive, `acp unload` removing the container, and the doctor line; each security
rule has a test that fails against a naive implementation.

**Not verified: nothing was pulled or run against a real container.** The flag set is chosen for
the image as it is documented, and these need a real run before release: that the image's
entrypoint starts with `--read-only` and the three tmpfs mounts (it may want to write elsewhere);
that it runs as the person's uid with `--user` (and podman's `--userns=keep-id`) and still reads
its own files; that `--cap-drop ALL` leaves it nothing it needs (an image that starts as root and
drops to its own user would need `SETUID`/`SETGID`); that a 0600 settings file is readable through
the mount under rootful docker, rootless podman, podman machine and Docker Desktop; that SELinux
hosts (Fedora) need `:Z` on the volume; and that SIGTERM to the runtime client stops and removes
the container on both runtimes. An opt-in test (`VIBEY_TEST_SEARXNG_CONTAINER=1`) documents what
such a run should assert.

## Consequences

- A person who allows it gets local search that works on a fresh computer, kept running and
  undone by `vibey acp unload` (the container) or `vibey searxng uninstall --purge` (everything).
- The bootstrap can download a container image on the person's word; it says so, once, and never
  at login. The question names the image and the port but not its size, which was not measured
  here (the digest was read with a `HEAD`, which carries none).
- A new pinned digest is a change someone reviews; an installed SearXNG is updated by running
  `vibey searxng install` again (doctor says when vibey pins a newer image).
- The Brave backup is still reachable only in vibey's own processes, never in a session.
