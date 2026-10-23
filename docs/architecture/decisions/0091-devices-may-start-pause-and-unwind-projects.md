# 0091 — A paired device may start, pause, resume and unwind a project

**Status:** proposed · **Date:** 2026-10-23 · **Cites:** ADR-0067, ADR-0068; sub-doctrines 10.c, 12.c, 12.j · **Related:** ADR-0054, ADR-0085

## Context

ADR-0068 gave a paired device the scopes `view`, `answer`, `spend`, `run`, `bump` and `workflows`,
and the device policy of the mobile and desktop clients refused four things outright: starting a
project, starting its worker, pausing work, and unwinding a project. The result was a first run
that dead-ended: a person with only the phone or the desktop app saw "No projects yet" and could
do nothing about it, because the only way to start one was a terminal or the editor on the host.

The `run` scope already existed ("start, stop or wind down work") and `abandon` and `worker` were
already `run`-scoped for a command sent to the workflows (ADR-0085). What was missing was a route,
and the decision that a device may use it. The operator has decided that it may.

## Decision

Four routes, each needing `run`, and no new scope:

| Route | Does |
|---|---|
| `POST /api/v1/projects` | starts a project from `{name, intake}` and gives it a worker |
| `POST /api/v1/projects/{id}/work/start` | starts, or starts again, that project's worker |
| `POST /api/v1/projects/{id}/work/pause` | stops that project's own workers and no one else's |
| `POST /api/v1/projects/{id}/abandon` | unwinds it, or with `dry_run` says what it would cancel |

**Delegation.** The hub owns no write of its own (ADR-0067). Each route runs the command the CLI
already offers (`vibey new --json`, `retry --keep-workers --start-worker`,
`recover --project --stop-workers`, `abandon --json`) on the host, so it cannot drift from them and
cannot route around a check they make: the one-live-project-per-checkout hold, the Sabbath window,
the runtime config's own refusals.

**A device never names a path.** The request carries a name and a sentence of intake; both are
validated by the service (a name is at most 64 characters of letters, digits, dot, dash and
underscore, starting with a letter or digit, so it can be neither a path nor a flag), an unknown key
is a 422, and the folder is `<projects_root>/<name>`, made by the host. `[hub] projects_root` is
**unset by default**: with none declared, a device can pause, resume and unwind but cannot start
anything, and is told why. A name whose folder exists is refused, never adopted.

**Reversibility is kept visible.** Pause stops only that project's workers; a worker that serves
every project is left running and named, and the leases are not reset while it lives (a job would
run twice). Unwind is the one irreversible act: the clients show a dry run, ask for on-device
confirmation (the biometric prompt spending already uses), and require a reason that is recorded
on the ledger under the device's name.

**What does not change.** `NEVER_FROM_THE_HUB` is untouched: paid use, caps, the DSN, migrations,
the canon and state sync stay on the host. A device that was not paired with `run` still cannot do
any of this; the operator grants the scope when pairing and may withdraw it.

## Consequences

A phone or the desktop app is now enough to start, steer and end a project, which is the first-run
the audience needs. The blast radius of a stolen device with `run` grows from "can wind down work
that exists" to "can also create folders under `projects_root` and start workers there", bounded by
the folder, the name rules, the caps the host declared, and the revocability of the device (ADR-0068).
An operator who does not want this simply never pairs a device with `run`, or leaves
`projects_root` unset.
