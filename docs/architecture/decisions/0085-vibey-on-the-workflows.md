# 0085 — `vibey -w`: any vibey command, run on the repository's GitHub-hosted runners

**Status:** accepted · **Date:** 2026-10-06 · **Cites:** sub-doctrines 10.f, 12.c, 12.d and 12.j · **Related:** ADR-0016, ADR-0055, ADR-0067, ADR-0068, ADR-0071, ADR-0081, ADR-0083 · **Evidence:** `vibey.cli.main.run`, `.github/workflows/vibey-remote.yml`, 7,152 tests passing with every layer at 100% branch coverage on this change

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; a `properdocs.yml` nav entry for this record; `docs/llms.txt`
regenerated from that nav; `docs/reference/hub-api.json` regenerated. All are in the change
that carries this record.

## Context

The operator asked that every krypton interface be able to reach vibey through the GitHub
workflows themselves, from the CLI core, with a new `-w` / `--workflows` flag. Asked how far
the flag should reach, the operator chose *any command, run on a runner*: `vibey -w <command>`
runs the same command line with vibey on a GitHub-hosted runner. The other two choices were
the GitHub-meaningful commands only, or one new command. Asked how interfaces that cannot
start a CLI should reach it, the operator chose *the CLI core plus the hub*.

The interfaces today reach vibey through one transport interface with two transports
(ADR-0067): a local `vibey` process, and the hub (`vibey serve`, ADR-0068). The chat lane
(ADR-0081) already runs a model on a GitHub runner from a `workflow_dispatch`, and reports
into a thread.

## Decision

1. **The flag belongs to the `vibey` command, not to a subcommand.** The console entry point
   (`vibey.cli.main:run`) reads `-w`/`--workflows` among the leading global options, including
   a short cluster such as `-vw`, before the command line is parsed. A `-w` after the command
   is the command's own. The flag is declared on the root callback for `--help`. Reaching the
   parser with it, which means the entry point was bypassed, exits 2 rather than run locally
   by mistake.
2. **One workflow runs the command**: `.github/workflows/vibey-remote.yml`, dispatched with
   the command line as a JSON array and a request id. The run is named after that id. The
   command line arrives through `env:` only. `scripts/vibey_remote.py` holds it to the
   domain's rules (`RemoteCommand`: no nested `-w`, no NUL, at most 4,000 characters, a
   well-formed id) and runs it as an argument vector, never through a shell. The report (exit
   code, stdout and stderr, each capped and cut out loud) comes back as the `vibey-result`
   artifact. The job can write nothing. The runner starts from an empty PostgreSQL migrated
   with an owner and an application role (ADR-0055). A **private** repository may declare
   `VIBEY_WORKFLOWS_PG_URL` instead. A public one never uses it, because anyone can read its
   runs' logs and reports, and the run says so. The command runs with the system basics vibey
   hands any child plus its application DSN, never the runner's whole environment. The owner's
   DSN reaches only a `vibey migrate`. No engine key and no model are present.
3. **The service is stateless.** `RemoteCommandService.start` dispatches; `poll` finds the run
   by the name the id gives it and reads the report. A caller that waits, a hub restarted
   half-way and a phone asking later all read the same run, and nothing is stored. A run the
   forge has not shown yet is `queued`. A run that ended without a report is `failed`, with
   the forge's conclusion, never read as the command having run (10.f).
4. **`gh` is the adapter.** `GhRemoteWorkflowForge` runs `gh workflow run`, `gh run list` and
   `gh run download` through an executor whose environment is declared, as `az`'s is. The
   database DSN and engine keys never reach it.
5. **The hub offers the same path** at `POST /api/v1/workflows/runs` (202, the request id) and
   `GET /api/v1/workflows/runs/{request_id}`. They are guarded by a new deny-by-default
   `workflows` scope, which only the host token holds until the host grants it to a device
   (12.j). The scope alone never lets a device do what its other scopes do not. A command
   needs the scope of each action it performs as well (`COMMAND_ACTIONS`): `status` needs
   `view`; `answer` needs `answer` and `spend`, since a command line cannot say whether the
   gate spends; `queue bump` needs `bump`; `work` needs `run`. A command the policy does not
   name needs every scope. A read command stays a read only with its declared safe options
   (`READ_COMMANDS`). `gates --remind` notifies, and `doctor --record` or `--install-postgres`
   writes or installs, so either needs every scope. A test against the CLI's own command tree
   keeps that list honest. A command that reaches a `NEVER_FROM_THE_HUB` capability is refused
   outright:
   `vibey migrate` and the `vibey budget` commands that change caps
   (`HubScopePolicy.reserved_command`). It would run where a repository may have declared its
   real database, so the hub refuses it there exactly as it never routes it itself.
   **A run is bound to its starter.** A request id is not a secret: the run carries it in
   its name, which anyone can read on a public repository. So the hub mints the ids it
   dispatches as `<nonce>-<tag>`: 24 hex characters of random nonce and the first 32 hex
   characters of HMAC-SHA256 over the starter's principal name and the nonce, under a
   32-byte key created once, owner-only, in the hub's state directory (`run.key`, made and
   checked as the host token is). `RunOwnership` mints and verifies; the poll compares the tag
   in constant time. The host may read any run, since the operator can read every run on
   GitHub anyway. A device reads only a run whose id verifies for its own name. Any other
   id, including one the host's own `vibey -w` made, gets the 404 an unknown run gets, and
   the forge is never asked. The id carries its owner and the key is on disk, so nothing is
   stored and a restarted hub still knows whose run each one is. Without the key, the
   routes answer 503.
6. **Configurable, not compiled in** (12.c): `VIBEY_WORKFLOWS_REPOSITORY`, `_WORKFLOW`, `_REF`,
   `_POLL_SECONDS` and `_TIMEOUT_SECONDS`, each with a declared default.

## Consequences

- From a terminal, the VS Code extension, the desktop app or a phone, anyone with write access
  to the repository can run vibey with nothing installed locally beyond `gh`, or with only the
  hub. The results are the same bytes the command printed.
- A command that needs state finds an empty queue unless a database is declared. A command
  that needs a model or an engine key fails there, as it would on a host without one. Both
  are said in its own output.
- A run costs GitHub-hosted runner time: free on a public repository, metered on a private
  one. The workflow is held to GitHub's CPU runners by `continuation_prompts.py check`.
