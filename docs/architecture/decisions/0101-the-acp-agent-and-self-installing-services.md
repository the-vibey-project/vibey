# 0101 — The ACP agent, and the user-level services it installs and keeps running

**Status:** proposed · **Date:** 2026-11-21 · **Cites:** SD-01 v1.0; proposed sub-doctrine 12.q; sub-doctrines 10.g, 10.h, 12.c, 12.d, 12.e · **Related:** ADR-0016, ADR-0017, ADR-0018, ADR-0023, ADR-0046, ADR-0055, ADR-0068, ADR-0070, ADR-0071, ADR-0091, ADR-0100

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md` (`tests/meta/test_adr_counts.py`), a nav entry in `properdocs.yml`,
and a fragment in `changelog.d/`. All are included in the change that carries this record.
The proposed sub-doctrine 12.q travels in a separate change that only the operator's merge
ratifies.

## Context

An editor that speaks the Agent Client Protocol (ACP) -- Zed is the first -- does not run a
server the operator started. It launches its agent itself, as a child process, whenever a
window opens a thread, and talks to it over the child's standard input and output. `vibey acp`
is that agent. ADR-0100 made the hub the one contract every conversational surface speaks, and
gave AI hosts a scoped `agent` principal that can never spend.

Two facts make first contact the hard case. The editor is often the first vibey surface a new
adopter opens, on a computer where nothing of vibey runs yet: no hub, no worker, perhaps no
PostgreSQL. And the operator is looking at the editor, not a terminal: a step that says "now
run this command" is a step a newcomer does not take.

Until now vibey never loaded anything into a service manager. ADR-0070 (the probe's timer) and
#1189 (`vibey supervisor install`) rendered units and printed the operator's own `launchctl` /
`systemctl --user` command: vibey never loaded an agent into the operator's session behind their
back. That stance was right for a terminal command the operator runs once. It leaves an editor
user with a hub that is "away" on every prompt until they find the right page of documentation.

## Decision

### 1. vibey is an ACP v1 agent over stdio

`vibey acp` speaks ACP protocol version 1: newline-delimited JSON-RPC 2.0 over standard input and
output, through one stdlib peer shared by both directions (the client's requests and vibey's own
`session/request_permission`). Standard output is the protocol stream alone: a guard redirects
every other write, and every child vibey starts gets standard input closed.

### 2. Every action goes through the hub, as the agent principal

The agent holds no database connection and no authority of its own. Each prompt, tool call,
ledger read and session write is a hub request made with `<state_dir>/agent.token`, so the hub
enforces `[hub] agent_scopes` (ADR-0100): the spend gates and the deployment opt-in are never
offered over ACP, and a session's mode (`observe`, `drive`) can only narrow the hub's grant. A
permission request that is not answered -- a timeout, a cancel, a dropped connection -- is never
an answer (12.d): the gate stays open.

### 3. Sessions persist through the hub, append-only

A session's log is kept by the hub, one append-only event at a time, keyed by the session and a
sequence number, so `session/load` and `session/resume` work across editor restarts and across
the two-window case. Corrections are new events; nothing is rewritten (the ledger's rule,
ADR-0055, applied to sessions).

### 4. vibey loads its own user-level units: the amendment to ADR-0070's stance

ADR-0070's "the operator loads the unit" is amended for two units and one surface only.

> vibey loads user-level units only (launchd `gui/<uid>`, `systemctl --user`), never system
> ones, never with sudo, only while `[acp] auto_bootstrap` and `[acp] auto_services` are true,
> and it says what it loaded and how to unload it.

The two units are the hub (`<[supervisor] label_prefix>.hub`, running `vibey serve`) and the
worker (`<label_prefix>.worker`, running `vibey worker --all-projects`), each through
`vibey supervisor exec --env-file <[supervisor] env_file>` so a secret lives in the environment
file (mode 0600) and never in a unit. They are rendered by the same renderer and paths as
`vibey supervisor install` (`SupervisorInstaller`, so both refuse the same volatile and
linked-worktree paths, 10.h), with `[acp] restart` (default `always`), throttled by
`[supervisor] restart_seconds` and, on systemd, a start limit, so a crash loop is slowed and then
stopped, never spun. In detail:

- **Only what vibey renders.** A unit is written atomically (mode 0644), never through a
  symbolic link, and with `overwrite=False`: a unit that differs from what vibey renders is the
  operator's edit, kept exactly as it is, and neither loaded nor restarted.
- **Never over a hub someone started.** A hub already running and answering outside the service
  manager is left alone. Its unit is not loaded now, and the keep-alive loads it only once that
  process has gone. vibey never stops a process it did not start.
- **Said and reversible.** The first load names each label and the exact commands that unload
  them (`launchctl bootout gui/<uid>/<label>`, `systemctl --user disable --now
  <label>.service`), and `auto_services = false` stops vibey loading them again.
- **Fixed argv, user scope.** Every command is a fixed argv built from a label held to a closed
  alphabet and the unit path the service manager reads for it. The binary comes from the
  system's own folders, stdin is closed, the environment is minimal, and the time is bounded.
  The runner refuses `sudo`, a shell, a `systemctl` without `--user` and the `system` launchd
  domain before anything runs.
- **Keep-alive.** While a session is open, `AcpKeepAlive` probes at the start of every prompt
  and every `[acp] probe_seconds`. It restarts only the labels vibey loaded, takes the bootstrap
  lock and probes again before it does, restarts a label at most once per period, and says one
  notice per change of state, never one per probe. While the hub is a unit, a read that finds
  no hub restarts the unit instead of spawning a second hub that would race it.
- **No service manager.** With none to load into (no login session's `gui/<uid>`, as over SSH,
  or no `systemctl --user` manager), vibey runs `vibey hub start` once per process and says that
  nothing keeps it running.

### 5. A privileged step is asked through the client, run non-interactively, or not run

The only step that needs more than the user's own authority is installing PostgreSQL. It is
asked through the client's own permission prompt, inside a prompt turn of a session that may
run, at most once per process. Only the explicit "Install PostgreSQL" option installs, and the
install runs `sudo -n`: vibey never asks for a password and never types one. A sudo that wants
one is told to the operator, with the command to run in their own terminal.

### 6. One bootstrap lock per user

Everything that changes the computer -- connecting clients, loading or restarting units,
installing PostgreSQL -- holds `<[hub] state_dir>/acp-bootstrap.lock`, the hub's own `ServeLock`
under another name (ADR-0017). Two editor windows therefore never change the computer at once:
connecting and installing are left to the window that holds it, and loading and restarting wait
for it within a bound and then find the other window's work already done.

## Consequences

- An editor user on a fresh computer gets a hub and a worker that stay up across crashes and
  logins without running a command, and is told what was loaded and how to undo it.
- The units are the operator's to change: editing one makes it theirs, and vibey stops touching
  it. Removing the grant is one key.
- **The default grant.** `[acp] auto_bootstrap` and `[acp] auto_services` default to `true`, as
  the operator ruled on 2026-11-20. That is a standing grant declared in configuration, which
  12.d reads narrowly: it covers what it names (two user-level units, loaded, kept running,
  unloadable) and nothing beyond it (no system unit, no sudo, no unit the operator edited). The
  tension between a default-true grant and "silence is not consent" is recorded here for the
  canon change carrying 12.q to settle: the mitigation in this record is that nothing is loaded
  without being said, everything loaded is named with its undo, and `false` runs nothing.
- `vibey supervisor install` is unchanged in what it renders and prints, and still loads
  nothing. It now writes atomically and refuses to write a unit through a symbolic link.
- The service manager is now something vibey drives. Its failures (a launchd domain missing over
  SSH, a systemd start limit reached) become notices in the editor rather than silent states.

## Proposed sub-doctrine

This decision binds how every surface a model drives may act on a person's computer, so
ADR-0020 requires a proposed sub-doctrine alongside it. It is proposed in its own change to
`src/vibey_tools/gh/docs/doctrines.md`; only the operator's merge ratifies it (Article II.3;
SD-01):

> **12.q — a driven surface acts within a declared grant** *(proposed; ratification requires
> the operator's merge)*: a surface a model drives (MCP, ACP, chat) holds a scoped principal
> that can never spend, and the hub, not the surface, enforces it. What such a surface keeps
> running on the person's machine runs as that person, at user level, never system-wide, and
> only while a grant declared in configuration says so; it says what it started and how to stop
> it. A step that needs more authority than the person's own is asked of the person through the
> surface's own prompt, runs without a password typed into the machine on their behalf, or does
> not run. Silence, a timeout or a dropped connection is never a yes (12.d).
