# Contributing to vibey

Thank you for considering a contribution. This document is meant to be
command-level and specific — if something here is unclear or you hit a
situation it doesn't cover, that's a bug in this document; please open an
issue or a PR fixing it.

## Table of contents

1. [Environment setup](#environment-setup)
2. [The branch model](#the-branch-model)
3. [Conventional Commits](#conventional-commits)
4. [Provenance](#provenance)
5. [Quality gates](#quality-gates)
6. [Pushing in this repository](#pushing-in-this-repository)
7. [The workspace tenants](#the-workspace-tenants)
8. [The onion architecture import rule](#the-onion-architecture-import-rule)
9. [Protected tests](#protected-tests)
10. [Agent surfaces](#agent-surfaces)
11. [Decisions and governing rules](#decisions-and-governing-rules)
12. [The paper and the book](#the-paper-and-the-book)
13. [PR checklist](#pr-checklist)
14. [Getting help](#getting-help)
15. [Code of Conduct](#code-of-conduct)
16. [License of contributions](#license-of-contributions)

## Environment setup

```bash
git clone https://github.com/the-vibey-project/vibey.git
cd vibey
uv sync --extra dev
# The framework hooks, all three stages. Without --hook-type the commit-msg
# and pre-push hooks are never installed and the suite never runs locally.
uv run pre-commit install --hook-type pre-commit --hook-type commit-msg --hook-type pre-push
# Then the provenance hooks. This points core.hooksPath at .githooks; the
# tracked .githooks/*.local shims chain back to the framework hooks above,
# resolving the common git directory to ensure they run in linked worktrees.
uv run vibey-gh install
```

The order matters: `pre-commit install` refuses to run while `core.hooksPath`
is set. The tracked shims (`.githooks/pre-commit`, `commit-msg.local` and
`pre-push.local`) all hand over to `.githooks/framework-hook.sh`. It finds the
framework's hooks through `git rev-parse --git-common-dir`, the same directory
`pre-commit install` writes to. That works from a plain clone and from a linked
worktree (`git worktree add`), where `.git` is a file rather than a directory,
and one install covers every worktree. It also drops the `GIT_DIR` that git
exports to a worktree's hooks, so the gate suite runs as it would from a plain
clone and a test's scratch `git init` cannot rewrite this repository's config.
If the framework's hook for a stage is
not installed, the shim prints
`warning: the pre-commit framework's <stage> hook is not installed` and lets
the commit or push go ahead. None of that stage's gates ran, so run them by
hand. CI runs them regardless.

Requires **Python 3.12+**, **PostgreSQL**, and **macOS or Linux**. Windows is
not a supported target. The suite reads `VIBEY_TEST_DATABASE_URL` (default
`postgresql://$USER@localhost:5432/vibey_test`); that role needs `CREATEDB`,
because the session builds a migrated `vibey_test_template` and clones one
`vibey_test_<worker>` per xdist worker. Parallel checkouts whose migrations
differ each set `VIBEY_TEST_TEMPLATE_DB` to a template name of their own. The server
authenticates every connection with scram-sha-256, the socket included (sub-doctrine
10.j, ADR-0061; the `pg_hba.conf` lines are in `SECURITY.md` §7). Give your role a
password and put it in `~/.pgpass` (mode `0600`, one line for `localhost`, which also
covers the local socket), and the DSN above works without the password written in it. The
default suite needs no engine binaries and no paid accounts: tests marked
`paid` are deselected unless you ask for them (ADR-0030).

A killed test run cannot drop its databases, so the harness reaps them. Each session holds a
lock on its database for as long as it lives, and marks the database with the process that
created it and that process's machine. At the start of every run, the harness drops, in the
background, the test databases no live session holds (`tests/db_reaper.py`). A database is kept
while its lock is held, or while the process its mark names is alive on this machine, so a
session that loses its lock mid-run still keeps its databases. `uv run python -m
tests.db_reaper --dry-run` shows what it would drop. `VIBEY_TEST_REAP=0` turns the automatic
reap off, and `VIBEY_TEST_REAP_LIMIT` (default 200) caps one run's drops.

### Where your work lives, and how often it is saved

Keep every clone and worktree on storage a reboot keeps. Never put one under `/tmp`,
`/private/tmp`, `/var/tmp`, `/var/folders`, `/dev/shm`, `/run/user` or `$TMPDIR`: the
operating system empties those at boot, by age or at logout. On 2026-09-24 a reboot emptied
`/private/tmp` in the middle of a storm and took every worktree there with it, along with
about 1.5 hours of measurements, a paper draft and three lanes of fixes. Only committed work
survived. Sub-doctrine 10.h is the rule and ADR-0057 is the record.

Parallel worktrees live in the storm home. It is `VIBEY_STORM_HOME` when set, else the
platform's default: `~/git/vibey-storm` on macOS, and `$XDG_DATA_HOME/vibey/storm` (falling
back to `~/.local/share/vibey/storm`) on Linux. The storm tools print and check it:

```bash
python3 docs/plans/qwenstorm-3.0.0/tools/storm_durability.py status   # durable or not
git worktree add "$(python3 docs/plans/qwenstorm-3.0.0/tools/storm_durability.py worktree fix-x)" \
  -b fix/x origin/develop
```

The storm tools refuse, with exit 78 and the key to change, to place work on volatile storage.

Durable storage alone is not enough. A disk fails and a laptop goes missing, so:

- Commit as soon as a change is coherent, not when it is finished.
- Push work in progress to a draft pull request (`gh pr create --draft`) at least every 30–45
  minutes. The merge train never merges a draft. Every push still runs the pre-push gates, so
  push when they pass. A commit on durable storage is the checkpoint in between.
- A long measurement writes each step as it finishes and resumes from the last one:
  `StepJournal` in `docs/plans/qwenstorm-3.0.0/tools/storm_checkpoint.py`.

## The branch model

```
main         ← always releasable; every push publishes to PyPI (release.yml)
  ▲ rebase merge — main's ruleset permits only rebase. The promotion PR is
  │ opened by `vibey-gh promote` (promote-to-main.yml); after a release,
  │ develop is realigned to main's tree.
develop      ← integration branch; every push publishes a vibey-dev build to TestPyPI
  ▲ squash merge — develop's ruleset permits only squash
feature/*    ← your work
```

1. `git checkout -b feature/short-description develop`
2. Commit using [Conventional Commits](#conventional-commits).
3. Open a PR **into `develop`**, never `main`.
4. You do not press Merge. Once the PR has one approval, a green `gates`
   check (ci.yml) and successful `PR evaluate / gate` and `PR review / gate`
   checks (pr-evaluate.yml + pr-review.yml), the merge train (`vibey-gh merge-train`,
   merge-train.yml) squash-merges it. A draft PR is never merged by the
   train. To see why a PR is not moving:
   `gh workflow run merge-train.yml -f pr=<N> -f dry_run=true`.
5. `vibey-gh promote` opens the promotion PR from `develop` into `main`; it is
   rebase-merged, `release.yml` publishes, and `develop` is realigned.

Never implement on `main`.

## Conventional Commits

Every commit message follows
[Conventional Commits](https://www.conventionalcommits.org/): `feat`, `fix`,
`docs`, `style`, `refactor`, `perf`, `test`, `build`, `chore`, `ci`,
`revert`. Two hooks act on the message: `conventional-pre-commit` rejects a
bad subject, and vibey-gh's `.githooks/commit-msg` appends the `Made-With:`
provenance trailer. The version of the next release is derived from what
changed (`vibey-gh version`, configured by `[version]` in `.vibey-gh.toml`),
not from the commit types (ADR-0028).

A commit made in the GitHub web UI — including an accepted Copilot autofix —
bypasses both hooks and fails the `Provenance` check. Reword it locally before
merge.

## Provenance

Every source file under `src/`, `tests/` and `scripts/`, and every workflow,
carries a fingerprint header, and every commit carries the `Made-With:`
trailer. The pre-push hook refuses a push whose fingerprints are not intact,
and the `Provenance` job (provenance.yml) audits the PR's commit range in CI.

```bash
uv run vibey-gh check            # what is missing
uv run vibey-gh check --apply    # add missing file headers
```

## Quality gates

On `git commit` the hooks run only ruff (`--fix`) and ruff-format. Everything
else runs on `git push`: first `vibey-gh check`, then the test suite, mypy
--strict, import-linter, the four 100% branch-coverage gates, bandit and
pip-audit. CI (ci.yml, job `gates`) enforces the same seven gates, of which
Gate 4 is the four per-layer floors (ADR-0023):

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/vibey

# One test run with coverage, then the per-layer 100% branch gates:
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100

uv run lint-imports
uv run bandit -q -r src/vibey
uv run pip-audit
```

There is no "coverage debt" mechanism: a PR that drops any layer below 100%
branch coverage does not merge. A `pragma: no cover`, `noqa`, `nosec` or
`type: ignore` needs its reason written beside it. Every `None`-default
keyword argument needs both-sides tests.

CI also runs a multi-arch container build, with one `Image contract - …` step
for each claim the Dockerfile makes, and a Helm install on minikube with four
cluster contracts
([Kubernetes guide](docs/guides/kubernetes.md), ADR-0025).

## Pushing in this repository

Every push goes through the push gate. Parallel lanes, agents and people share one
machine-wide push lock, so only one pre-push gate run (the whole suite, the coverage floors,
bandit, pip-audit) happens at a time, and a hung gate run is reaped by rule rather than
waited on. There is one recipe:

```bash
python3 <storm>/tools/push_gate.py run -- git push origin HEAD:<branch>
```

`<storm>` is the storm root, the directory that holds `storm.toml`: `<home>/qwenstorm-3.0.0`
under the storm home (see [Where your work lives](#where-your-work-lives-and-how-often-it-is-saved);
on the operator's Mac, `~/git/vibey-storm/qwenstorm-3.0.0`). It must be on a durable path, never
under a temporary directory such as `/tmp` or `/private/tmp`: a reboot wipes those, and on
2026-09-24 one took the storm's lock and state with it. From a checkout with no storm, use the
tracked copy and name the machine's shared lock, `<home>/.push-lock`:
`VIBEY_PUSH_LOCK=<home>/.push-lock python3 docs/plans/qwenstorm-3.0.0/tools/push_gate.py run -- git push …`.
Run from a checkout without a named lock, the tool refuses. A lock derived there would be
private to that checkout and would exclude nobody.

`run` waits for the lock and runs the push in a process group of its own. It keeps a log and
releases the lock however the push ends. Its exit code is the push's own, except for these:

| Exit code | Meaning |
|---|---|
| 124 | `reaped: hang`. The reaper judged the gate run hung and stopped it. This is not a test failure. |
| 125 | The push ran past `--push-timeout`. |
| 3 | The lock stayed busy past `--wait-timeout`. |

`push_gate.py status` says who holds the lock and what that push is doing.

The reaper also runs on a schedule of its own: a launchd agent on macOS, or a systemd user
timer on Linux, running `reap` every `[push_gate] schedule_seconds` (default 90). The
operator installs it once with `python3 <storm>/tools/push_gate.py install-schedule` and can
check it with `schedule-status`. Where neither launchd nor systemd exists,
`install-schedule --target cron` prints a cron line instead. There is no Kubernetes CronJob:
nothing pushes from inside the cluster, and a reaper can only see the processes on its own
machine. The rules the reaper acts on are in `docs/plans/qwenstorm-3.0.0/README.md`.

## The workspace tenants

This repository is a uv workspace (ADR-0021). `src/vibey` is the conductor;
`src/vibey_runners/{claude,codex,cursor,agy,qwen,common}` are the `*loop`
runners; `src/vibey_tools/{gh,skills,bootstrap}` are vibey-gh, vibey-skills
and vibey-bootstrap. Each was imported with its history, and each ships inside
the `vibey` distribution rather than under its own PyPI name (ADR-0037).

The root gates above cover `src/vibey` only. A tenant keeps every gate it was
already held to (ADR-0022), run from its own directory with its own command,
across the common supported Python range 3.12–3.14 — exactly as ci.yml's
`tools` and `tools-lint` jobs do. Nothing in that matrix may reach an index for a family
package: a tenant that needs a sibling installs it from the tree first.

| Tenant | Checks |
|---|---|
| `src/vibey_tools/gh` | `pip install -e ".[dev]"`, `python -m pytest -q` (100% branch floor), `black --check vibey_gh test`, `isort --check-only vibey_gh test`, `mypy vibey_gh`, and the managed-automation drift check; Python 3.12–3.14 |
| `src/vibey_tools/skills` | `python3 tools/validate_manifests.py`, `python3 tools/check_links.py`, `PYTHONPATH=src python3 -m unittest discover -s tests`; Python 3.12–3.14. On the 3.12 row, also its own strict docs build: `pip install -e ".[docs]"`, `mkdocs build --strict`, and a check that every plugin and skill produced a page |
| `src/vibey_tools/bootstrap` | `pip install -e ../gh` (it imports `vibey_gh`), `pip install -e ".[test,all]"`, `pytest test/ -m "not integration" --cov=vibey_bootstrap` (100% line floor); Python 3.12–3.14. On the 3.12 floor row, also `.[dev]` and its own pre-commit hook's `python -m mypy vibey_bootstrap/` and `python -m bandit -r vibey_bootstrap/ -ll -q` |
| `src/vibey_runners/common` | `pip install -e ".[dev]"`, `mypy --strict src/vibey_runners/common`, `lint-imports`; Python 3.12–3.14. It ships no suite |
| `src/vibey_runners/*` | the suite with the four per-layer 100% branch floors (qwenloop: one whole-package floor, in its addopts) on Python 3.12, 3.13, and 3.14. On the 3.12 row, also its own `mypy --strict src/<pkg>`, `lint-imports` and `bandit -q -r src/<pkg>`, plus agyloop's vendor-import grep and claudeloop's skill-frontmatter check. codexloop runs every gate on ubuntu and macOS, and agyloop and codexloop also run `properdocs build --strict` (properdocs 1.6.7) on ubuntu 3.12 |

A tenant carries no `.github/`, `.githooks/` or `.vibey-gh.toml` of its own.
GitHub reads only the root's workflows and templates, git runs only the root's
hooks (`core.hooksPath`), and vibey-gh stops at the nearest `.vibey-gh.toml`
walking upward — so a leftover tenant copy fires nothing and can only
misdirect a `vibey-gh` command run from inside that tenant. The copies the
absorbed repositories arrived with were removed under #189 and stay in git
history. `src/vibey_tools/gh` is the one exception: it is vibey-gh itself,
and ci.yml's `tools-lint` job verifies its rendered copy has no drift.

A change to a vibey-gh template (`src/vibey_tools/gh/vibey_gh/templates/`)
must be re-rendered at both roots, or the drift check fails:

```bash
uv run vibey-gh install
(cd src/vibey_tools/gh && uv run vibey-gh install)
```

## The onion architecture import rule

```
domain → application → infrastructure → cli, tui
                                  ▲
                          bootstrap.py (the sole composition root)
```

Dependencies point inward only, enforced by `import-linter` in CI — not by
convention. `domain/` has no I/O, no async, no clock and no network, verified
by an AST-walking purity test; on imports it allows the standard library and
the dependency-free family packages (`vibey-gh`, `vibey-skills`,
`vibey-runners-common`), never `vibey_bootstrap` (ADR-0017). New I/O goes in
`infrastructure/` behind a `Protocol` declared in `application/interfaces/`;
wiring happens only in `bootstrap.py`.

New and changed code lives in classes, and every class has an interface beside
it in a mirrored `interfaces/` package (`src/vibey/foo/bar.py` ↔
`src/vibey/foo/interfaces/bar_interface.py`). Interface modules import only the
standard library and other interfaces. A module-level function is the
exception, with its reason written at the definition (ADR-0016).

## Protected tests

A small set of test files encode contracts that must not drift
(`tests/system/test_delivery_stage_set.py`, `tests/domain/test_noloss*.py`,
`tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
and everything under `tests/live/`). Do not modify them without explicit
maintainer sign-off in the PR description; changes to them are reviewed as
contract changes, not test edits. The list is `[merge_train] protected_paths`
in `.vibey-gh.toml`, mirrored by `.github/CODEOWNERS`: the owner's review is
required, and the merge train refuses such a pull request as "needs a human
merge", so the maintainer merges it by hand.

## Agent surfaces

When a skill or procedure changes, update all four agent-surface trees in
the same PR: `.claude/skills/`, `.cursor/rules/`, `.agents/skills/`, and
`.agent/rules/`. CLAUDE.md, AGENTS.md and GEMINI.md hold facts, not
procedures, and change together.

## Decisions and governing rules

An architectural choice is an ADR in
`docs/architecture/decisions/NNNN-slug.md`: a status and date line, Context,
Decision, Consequences, and Alternatives rejected. Adding one means the next
contiguous number, an entry in the `properdocs.yml` nav (a title with no
colon, or the book exporter drops the chapter), and bumping the "(N ADRs)"
count in CLAUDE.md, AGENTS.md, GEMINI.md, README.md and docs/index.md;
`tests/meta/test_adr_counts.py` fails otherwise.

A **governing rule** — one that binds future decisions, survives a rewrite,
and is about conduct rather than mechanism — is not law until it is a
sub-doctrine in `src/vibey_tools/gh/docs/doctrines.md`, filed under one of the
sealed Twelve, and ratified by the operator's merge (ADR-0020; Constitution
Article II.3). Propose one per pull request, as a draft, regenerate the index
in the same change, and cite it from the ADR that argues it:

```bash
(cd src/vibey_tools/gh && uv run vibey-gh corpus-index && uv run vibey-gh corpus-index --check)
```

## The paper and the book

Two documents are built from this tree on every release and published on the
docs site beside the pages they mirror:

- **The research paper.** Source `docs/paper.md`, compiled by
  `vibey-gh paper` to [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf),
  and published as [HTML](https://the-vibey-project.github.io/vibey/main/paper/).
  Keep it to the constrained Markdown the renderer converts: a `# Title`, a
  `**Abstract.**` paragraph, `##` sections, lists, tables, ```` ```latex ````
  fences, and a `## References` list. Figures are TikZ inside those fences, drawn
  with the flat house styles `vibey_gh.paper.PREAMBLE` defines; a two-column
  figure fits 516pt, a one-column figure 252pt, measured in the paper's own fonts
  (TeX Gyre Termes, Heros and Cursor through `fontspec`, since IEEEtran's Times,
  Helvetica and Courier have no definitions under XeTeX). The fifteen empirical
  figures between `BEGIN GENERATED figure:` markers are written by
  `scripts/paper_figures.py` from tracked records and checked for drift with
  `--check`; every section closes with a `plainwords` box that restates it for a
  reader outside the field.
- **The book.** Every page in `properdocs.yml` nav order, exported by
  `vibey-gh book` as [PDF](https://the-vibey-project.github.io/vibey/main/book.pdf),
  [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) and
  [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html).
  A nav edit is a book edit.

Both are also attached to each GitHub Release as permanent assets. Preview
copies of everything are published under `/develop/`.

## PR checklist

- [ ] Branched from `develop`; targets `develop` (not `main`)
- [ ] Commits (or the squash-merge title) follow Conventional Commits
- [ ] `uv run vibey-gh check` passes (file headers and `Made-With:` trailers)
- [ ] `uv run pre-commit run --all-files --hook-stage pre-push` passes
- [ ] All four 100% branch-coverage gates pass
- [ ] If a tenant under `src/vibey_runners/` or `src/vibey_tools/` changed, its own checks pass
- [ ] New or changed classes have an interface beside them (ADR-0016)
- [ ] Protected tests untouched (or sign-off obtained and noted)
- [ ] Agent-surface trees updated if a procedure changed
- [ ] Docs updated if behavior changed; a new ADR bumps the count and the nav
- [ ] Any new governing rule is proposed as a sub-doctrine, with the corpus index regenerated
- [ ] I agree to the [Code of Conduct](CODE_OF_CONDUCT.md) and to license
      this contribution under the MIT License

## Getting help

See [SUPPORT.md](SUPPORT.md) for the right channel. Usage questions belong
in [Discussions](https://github.com/the-vibey-project/vibey/discussions), not
bug reports. Contributors talk on the [Discord server](https://discord.gg/Qvu8aYnVS);
if you want to build the autonomous-delivery stack with us, start at
[join me](https://vibewithadam.matthewsteinberger.com/join-me).

## Code of Conduct

This project follows the
[Contributor Covenant 2.1](CODE_OF_CONDUCT.md). By participating you agree
to uphold it.

## License of contributions

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENSE).
