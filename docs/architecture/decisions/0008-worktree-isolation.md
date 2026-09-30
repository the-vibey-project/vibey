# 0008 — Git worktree per work item; containers for real isolation

**Status:** accepted · **Date:** 2026-08-14

**Owes:** nothing — mechanism (ADR-0020)

## Context

Phase 2 builds several work items in parallel, each driven by a different engine.
Two agents editing the same checkout corrupt each other: one rewrites a file
mid-edit, tests fail for unrelated reasons, and the failure is attributed to the
wrong item.

## Decision

**Every `build.implement` job gets its own git worktree and branch.** Integration
happens on a dedicated integration worktree.

```
.vibey/worktrees/893c4fc1/1/
├── item-001/      branch vibey/893c4fc1/1/item-001
├── item-004/      branch vibey/893c4fc1/1/item-004
└── integration/   branch vibey/893c4fc1/1/integration
```

Naming lives in `domain/worktree.py` (`WorktreeNaming`:
`.vibey/worktrees/<scope>/<cycle>/<item_id>`, branch `vibey/<scope>/<cycle>/<item_id>`,
where `<scope>` is the first eight hex digits of the project id); the integration
worktree is the reserved item id `integration`
(`infrastructure/git/integration_branch.py`). Item branches are cut from the project's
integration branch once it exists, so later items stack on already-integrated code;
before the first integrate they are cut from the project checkout's `HEAD`.
`build.integrate` merges into it one job at a time under a Postgres advisory lock
([ADR-0029](0029-integrate-serialized-by-advisory-lock.md)).

**Amended 2026-09-30 — names carry the project, and a branch must prove whose it is.**
The scheme was `.vibey/worktrees/<cycle>/<item_id>` on `vibey/<cycle>/<item_id>`: keyed
by cycle alone. Every project in one repository shares that repository's refs — and the
triaged-delivery bridge runs each delivery in a linked worktree of the main checkout, so
all of them share one set of refs. A live delivery (project `893c4fc1`, issue #963) in
cycle 1 found an unrelated August project's `vibey/1/ws` and `vibey/1/integration`,
checked out `vibey/1/ws`, edited that project's codebase, and would have published its
history as #963's pull request. Three changes close it:

1. **Project-scoped names.** Paths and branches carry the project's scope, so no two
   projects' names meet. A project's worktrees live under their own root, so one
   project's self-healing wipe or orphan reclaim never reaches another's.
2. **An ownership record, proved before use.** Every branch BUILD creates records, in
   the repository's config under the branch's own section, the full project id
   (`branch.<name>.vibey-project`) and the commit it was cut from
   (`branch.<name>.vibey-base`) — written *before* the branch exists, so a create killed
   half-way still proves whose it is. Before a branch is reused, used as a base, or
   merged, the record must name this project and its base must still be in the branch's
   history. Eight hex digits make a collision unlikely, not impossible; the record is what
   makes one harmless. A branch that fails is refused (`ForeignBranchRefused`) before
   anything is wiped, and the job parks on a `foreign_branch` gate at once — no retry
   changes whose a branch is. The delivery bridge applies the same check before it
   pushes, and reads the branch name from `vibey status --json`
   (`integration_branch`) rather than rebuilding it.
3. **Projects created before the change** resolve through the new scheme. Nothing
   recorded which cycle-keyed branch was whose, so none is adopted: an in-flight job
   whose payload names the old `vibey/<cycle>/integration` as its base reads it as the
   project's own scoped integration branch, and any other existing branch in the
   `vibey/` namespace without this project's record is refused. The old branches are
   left exactly as they were. A project that had integrated items on cycle-keyed
   branches rebuilds them on its own; a person who knows an old branch is the project's
   can move it to the new name and record it, but vibey never does so on its own.

**Additionally**, three isolation levels are designed, selectable per project as
`[isolation] level` in `vibey.toml`:

| Level | Mechanism | Protects against | Status |
|---|---|---|---|
| `worktree` (default) | git worktree + engine destructive-command denies | concurrent-edit corruption | implemented |
| `container` | Docker/Podman, worktree mounted, hardened defaults (`infrastructure/container/`: no network, read-only root, all capabilities dropped, `no-new-privileges`) | filesystem escape, exfiltration | executor implemented, **not wired into dispatch** |
| `vm` | Firecracker / Lima microVM | kernel-level escape | **designed, not implemented** |

The config parser accepts all three levels and an `egress` list, but every dispatch
path today builds its `RunSpec` with `IsolationLevel.WORKTREE`. A level only selects
per-descriptor argv flags, and those are empty for every engine except agyloop's
`--safe`; the conformance suite found the other engines' isolation flags had been
invented and removed them. `OciContainerExecutor` is not referenced by the
composition root or any handler.

## Rationale

Worktrees remove the shared mutable resource rather than trying to lock it, which
is the standard answer to a standard concurrency problem. This became the
convergent industry pattern during 2026 — multiple agent CLIs shipped
one-worktree-per-write-capable-agent within the same period.

**A worktree is not a sandbox**, and this is worth stating loudly because the
convenience of worktrees invites the confusion. A worktree stops agent A from
overwriting agent B's file. It does nothing to stop either from running `rm -rf ~`,
reading `~/.ssh`, or POSTing the repository somewhere. For unattended overnight
runs — which is vibey's whole premise — that gap matters.

Hence `container` as the recommended level for autonomous operation, with egress
restricted to the provider API hosts the engines need. That is the target, not the
present: the container executor's default is no network at all, an allow-list is
not implemented, and a `vibey doctor` warning for `level = "worktree"` on an
unattended Phase 2 is planned but does not exist. Until container dispatch lands,
unattended runs have worktree isolation plus whatever the runners themselves deny.

## Consequences

**Good.** Parallel builds are conflict-free by construction. Conflicts surface at
integration, where they can be reasoned about, rather than as mysterious mid-build
corruption. Each worktree is independently savepoint-able and unwind-able.

**Bad.** Disk cost — N checkouts of the repo. Some toolchains (node_modules,
virtualenvs, build caches) are expensive to rebuild per worktree.

**Mitigation (partial).** The worktree manager is crash-safe: `SIGKILL` mid-create
leaves no orphan, and `create()` heals a half-registered path.
`WorktreeManager.reclaim_orphans()` removes directories git no longer recognizes,
but nothing calls it yet and there is no `vibey gc` command. Reclaiming worktrees on
item completion and a per-project cache-sharing `bootstrap` hook in `vibey.toml`
are planned; today worktrees stay on disk until removed by hand.

**Bad.** `container` mode adds a Docker dependency and slows iteration.
Accepted: it is opt-in, and the default stays `worktree` for supervised work.

## Alternatives rejected

- **A shared checkout with file locks.** Locks the symptom; agents still race on
  tests, caches, and generated files.
- **A full clone per item.** The same isolation as a worktree at N times the disk,
  without the shared object store, and integration becomes a fetch between
  repositories.
- **Containers instead of worktrees.** A container over one shared checkout still
  shares the checkout. The two compose; neither substitutes for the other.
