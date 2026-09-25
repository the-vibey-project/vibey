# AGENTS.md

`vibey`: a queue-based, six-phase conductor for autonomous software delivery.
Built on PostgreSQL and five `*loop` autonomous session runners (claudeloop,
codexloop, cursorloop, agyloop, and the local runner that ships as two engines:
`gptossloop`, the sovereign default on GPT-OSS 20B, and the opt-in `qwenloop` on
Qwen), which live in this
repository under `src/vibey_runners/`. It orchestrates design → build → review with
an optional visual-design interstitial, plus an opt-in Azure deployment stage
set. One distribution — `pip install vibey` delivers the whole family,
engines and tools included (ADR-0037). Python 3.12+.

**This file is deliberately short — it holds facts, not procedures.** Every
"how do I..." lives in a skill below; every "why was it built this way"
lives in `docs/architecture/decisions/`.

## Non-negotiables

- **Never block a worker on a human.** Human input is a *parked job* plus a
  `human_gate` row, never a thread waiting on stdin.
- **Credits ≠ rate limit.** `CreditsExhausted` has no `resets_at` field and
  must never acquire one. This is enforced at three independent layers: the
  type definition, a property test, and a database CHECK constraint.
- **A capacity rejection always outranks a completion claim.**
- **`domain/` stays pure.** No I/O, no async, no clock, no network — enforced by
  `tests/domain/test_domain_purity.py`, which walks the AST. On imports: stdlib,
  itself, and **any family package that is itself dependency-free** (`vibey-gh`,
  `vibey-skills`, `vibey-runners-common` all declare `dependencies = []`, so they
  add nothing stdlib-only did not already allow). `vibey_bootstrap` is forbidden
  here by name, not by category — it carries the Azure SDK and OpenTelemetry, so
  it would pull a third-party graph in transitively. Use it from
  `infrastructure/`. Enforced by `import-linter` in CI, not convention. ADR-0017.
- **Dogfood the family, always.** If a capability exists inside this family, use
  it — do not reimplement it and do not reach for a third-party equivalent. The
  bar is not "is ours better", it is "does ours do this at all". Between using
  `vibey_bootstrap`'s retry or dead-letter routing and hand-rolling one, use
  ours. A new implementation of something the family already ships needs a
  written reason at the call site, and the reason must be a capability gap — in
  which case the fix is to add it to ours. ADR-0017; sub-doctrine 10.e.
- **Everything-as-code, and never less of it.** If a thing can be declared in the
  repository and reconciled from it, that is how it is done — branch protection,
  repository profile, pipelines, policy, infrastructure. No settings page, no
  one-off `gh api`, no runbook step that says "then set X". And **everything that
  can be generic and configurable must be**: a hard-coded value that could have
  been a key is a decision taken away from the next adopter, silently. Never
  change anything to a state that is less generic or less configurable. ADR-0018;
  sub-doctrine 12.c.
- **A governing rule is a ratified sub-doctrine, or it is not a rule.** Anything
  that can be spelled out explicitly as a sub-doctrine in the governance corpus
  must be — filed under one of the sealed Twelve in
  `src/vibey_tools/gh/docs/doctrines.md`, and ratified by the operator's merge per
  Article IV.4, under the authority Article I.1 places above every other. No
  exceptions. The test: it binds future decisions, it survives a rewrite, and it
  is about conduct rather than mechanism. An ADR records the decision; the canon
  records the law. Both get written. ADR-0020.
- **Convergence-Driven Development (CDD) is the enclosing development loop.**
  Every change uses Specification-Driven Development (SDD) for intent and
  acceptance criteria, Test-Driven Development (TDD) for executable checks, and
  CDD to repeatedly ground, implement, test, review and repair against the
  actual tracked repository until delivery evidence converges. Every iteration
  classifies its trajectory as converging, neutral or diverging; any divergence
  needs a bounded path to reconvergence, and unbounded divergence is abandoned.
  A verdict, marker, generated file or activity is never completion evidence by
  itself. The confirmed high-quality core is the nucleus; project, phase, epic
  and item are living orbitals, and nucleus-only is terminal: complete with no
  further change or dead and no longer maintained. Multiple project atoms may
  form chemical structures, and a suite of suites may be alive in the digital
  realm as a software organism when its identity, feedback, adaptation, repair
  and exchange are evidenced. ADR-0039; sub-doctrines 9.c–9.d.
- **Status is evidence-bounded.** Claims name their object, source and cutoff;
  active, blocked, failed, verified and published are not interchangeable, and
  missing or contradictory evidence stays unknown. ADR-0040; sub-doctrine 10.f.
- **Unattended authority is bounded by a gate, never by judgement.** A standing
  grant to act while the operator is away is read narrowly: it covers the work
  named and the judgement that work actually requires — never an act that cannot
  be undone, a protected branch written directly, or a gate routed around (no
  `--no-verify`, no `--admin`, no means whose purpose is to make a check stop
  applying). Work done overnight lands as a pull request through the merge train
  or it does not land, so it arrives where a human would have looked for it
  anyway. Repair is not authorship: adding the import the file next door already
  uses is bookkeeping, supplying the definition it was meant to find is the work,
  and where a lane's output is net-negative the answer is revert and re-queue.
  Silence is not consent, and declining is a reportable outcome — the refusals
  are the most useful part of the report. ADR-0046; sub-doctrine 12.d.
- **Toil that can be fully automated is.** Anything a human would otherwise do
  *again* — the remembering, the ordering, the repetition, the transcription,
  the checking of a thing that could check itself — is automated, no exceptions.
  Fully: a half-automation that still needs someone to remember the uncovered
  step is worse than none, because it looks finished; where it cannot be made
  whole, automate the check that says out loud when the step was missed. The
  judgement is never automated away — if a careful person doing it twice would
  do it identically it is toil, and if the right answer could reasonably differ
  it stays with the human and the automation surrounds it. Automation that
  reports success it did not observe is a liability wearing its clothes.
  ADR-0047; sub-doctrine 12.e.
- **Consume the whole gap, and prove the span.** A job that reads an
  accumulating record reads everything written since its own last run. A
  timestamp is not a watermark — records sharing the cutoff instant, or
  arriving late or out of order, fall through a time comparison silently. The
  watermark is a position in the data: a byte offset, an identity set, a
  sequence. It advances only after the data is durably recorded, so a crash
  re-reads rather than skips (at-least-once, de-duplicated by identity). An
  unreadable source is reported and the watermark left unmoved, never stepped
  over. A figure computed over an unknown subset is not evidence.
  ADR-0048; sub-doctrine 10.g.
- **Work outlives the machine.** Work in progress lives on durable storage
  and is committed and pushed often; volatile storage holds only what can be
  regenerated. Worktrees and storm roots live in the storm home
  (`VIBEY_STORM_HOME`, else `~/git/vibey-storm` on macOS or
  `~/.local/share/vibey/storm` on Linux), never under `/tmp` or `$TMPDIR`, and
  the storm tools refuse volatile paths with exit 78. Push work in progress
  to a draft PR at least every 30–45 minutes. ADR-0057; sub-doctrine 10.h.
- **Code lives in classes, and every class has an interface beside it.** A
  module-level function is the method of last resort, and its reason is written
  at the definition. `src/<pkg>/services/github_service.py` implies
  `src/<pkg>/services/interfaces/github_service_interface.py`. Interfaces
  declare; they never consume. New and changed code from 2026-09-15; the
  existing tree converges module by module. ADR-0016; sub-doctrine 9.b.
- **The handoff no-loss gate is not negotiable.** A handoff that fails the
  gate is a retry, an escalation to full-transcript mode, or a human gate —
  never a silent partial.
- **Every job is idempotent under replay.** Workers die; the lease expires
  and another worker picks it up.
- **The ledger is append-only.** No updates, no deletes. Corrections are new
  events that supersede prior ones.
- **Every commit follows Conventional Commits.** Enforced by a pre-commit hook.
- **Run `git commit` and `git push` in the foreground and wait for them.** Never edit
  a file in a worktree while a git hook is running there. The pre-push hooks test the
  *working tree*, not the refs being pushed, so a file written mid-run fails the push
  with `files were modified by this hook` — while the suite itself passed. It reads as
  a test failure and is not one. Knowing the hazard does not prevent it; this rule is
  here because it happened again to someone who had already written the warning down.
- **Never implement on `main`.** Feature PRs squash into `develop` through the
  merge train (`vibey-gh merge-train`); `develop` is promoted to `main` by
  `vibey-gh promote` as a **rebase** merge, keeping history linear
  (`.vibey-gh.toml [branches]`). A push to `develop` publishes `vibey-dev` to
  TestPyPI; a push to `main` publishes `vibey` to PyPI. ADR-0028.
- **Sovereign self-hosted free is the only default on every surface; paid is
  declared-only.** Each operational surface has one vibey-owned protocol and a
  sovereign default adapter that is always on: engine `gptossloop`,
  cloud self-hosted OpenStack, forge self-hosted Forgejo, ticketing self-hosted
  free Plane, documentation self-hosted free BookStack, secrets self-hosted
  free Bitwarden, files self-hosted free Nextcloud, email self-hosted free
  Forward Email, SMS self-hosted free Fossify Messages, and messaging
  self-hosted Matrix with the Element client. Paid platforms (engines
  claudeloop/codexloop/cursorloop/agyloop; cloud azure/aws/gcp; forge
  github/gitlab/bitbucket; tickets jira/linear/asana (+ sibling sovereign
  openproject); docs confluence/notion/gitbook; secrets lastpass/1password/
  proton; files gdrive/icloud; email proton/gmail/apple; sms google-messages/
  imessage; messaging signal/discord/slack/zoom/whatsapp/telegram/messenger/
  facebook/instagram/tiktok) are declared-only relays through the sovereign
  host and are never a default — sub-doctrine 8.b, ADR-0042.

## Layer map

```
domain → application → infrastructure → cli, tui
                                  ▲
                          bootstrap.py
                   (the sole composition root)
```

Dependencies point inward only, enforced by `import-linter` in CI. Four of the
five layers carry a **100% branch coverage floor** enforced in CI as separate
gates: `domain/`, `application/`, `infrastructure/`, `cli/` each fail the build
under 100%. `tui/` is outside the floor, a recorded exemption. ADR-0023.

**Workspace tenants.** The map above covers `src/vibey` only. The repository is a
uv workspace (`[tool.uv.workspace] members = ["src/vibey_runners/*",
"src/vibey_tools/*"]`, ADR-0021) whose other members are absorbed with history:

- `src/vibey_runners/{claude,codex,cursor,agy,qwen}` — claudeloop,
  codexloop, cursorloop, agyloop, gptossloop and qwenloop (one package, two
  engines — ADR-0064); `src/vibey_runners/common` — vibey-runners-common.
- `src/vibey_tools/gh` — vibey-gh (provenance, merge train, promotion, release,
  and the governance canon under `docs/`); `src/vibey_tools/skills` —
  vibey-skills; `src/vibey_tools/bootstrap` — vibey-bootstrap.

Each tenant keeps its own `pyproject.toml`, version, Python floor (3.12+ for
every library), test suite and gates (ADR-0022). The old sibling GitHub
repositories are gone, and so are the old PyPI names: the whole tree ships as
the single `vibey` distribution (ADR-0037).

## The six-phase model

```
INTAKE → ① DESIGN → [optional VISUAL_DESIGN] → ② BUILD ⇄ ③ REVIEW

③ REVIEW ── user declines deployment ────────────────→ DONE (local)
       │ user opts into deployment
       ▼
④ DEPLOY_DESIGN → ⑤ DEPLOY_EXECUTE → ⑥ DEPLOY_REVIEW → DONE (deployed)
   interactive       autonomous          interactive
```

Phases ①, ③, ④, ⑥ and the optional VISUAL_DESIGN stage talk to you. Phases ②
and ⑤ run unattended. The deployment stage set (④–⑥) is entered only after
explicit opt-in; declining deployment records a successful local completion.

## The queue and engines

- **Queue backend:** PostgreSQL 14+, never SQLite. CI exercises every currently
  supported major (14–18), while the Helm chart defaults to PostgreSQL 17. `FOR UPDATE SKIP LOCKED` is
  the reason; see ADR-0002.
- **Engines:** `claudeloop`, `codexloop`, `cursorloop`, and `agyloop` are the
  default paid-engine pool (tier PAID). Three local engines (tier LOCAL) join
  them, each behind its own switch: `gptossloop` — the sovereign default on
  GPT-OSS 20B, **on by default**, switched off only by `VIBEY_FEATURE_GPTOSSLOOP=0`
  or `[features] gptossloop = false`; `qwenloop` — the same runner on a Qwen model
  (`qwen3:14b`), off by default (`VIBEY_FEATURE_QWENLOOP=1` or `[features]
  qwenloop = true`); and `claudeloop-local` — the claudeloop binary on a local
  backend profile, off by default (`VIBEY_FEATURE_CLAUDELOOP_LOCAL` or `[features]
  claudeloop_local`). ADR-0064. Under sub-doctrine 8.a local engines are
  **preferred first**: BUILD selection runs SWRR within the LOCAL tier and falls
  back to PAID only when no local engine is eligible (ADR-0038, amending
  ADR-0015's standby). With no `--provider`, DESIGN and DECOMPOSE run on the
  sovereign providers (`GptossloopDesignProvider`, `GptossloopWorkPlanProducer`;
  ADR-0027, ADR-0038, ADR-0064). `VIBEY_OLLAMA_URL` is the one local endpoint
  setting.
- **Rotation:** `domain/rotation.py::select()` implements smooth-weighted
  round-robin selection (ADR-0005) and is wired in production: `bootstrap.py`
  builds `EngineSelector`, and BUILD jobs pick their engine per job through
  `SelectingEngineProvider` → `EngineSelector`.
- **Handoff:** when an engine hits `CreditsExhausted`, vibey produces a
  `HandoffBrief`, verifies it against the no-loss gate, and seeds the next
  engine. The full ledger is always written to disk inside the receiving
  worktree.

## Commands worth memorizing

```bash
# CI job `uv-lock` (runs first)
uv lock --check

# CI job `gates`: the 7-gate sweep over src/vibey (Postgres 17 service); the
# `postgres-compatibility` matrix runs the database suite on PostgreSQL 14–18
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/vibey

# Single test run with coverage, then per-layer 100% gates
uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
uv run coverage report --include='src/vibey/domain/*' --fail-under=100
uv run coverage report --include='src/vibey/application/*' --fail-under=100
uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
uv run coverage report --include='src/vibey/cli/*' --fail-under=100

uv run lint-imports
uv run bandit -q -r src/vibey
uv run pip-audit

# CI job `tools`: each tool's own suite, plain pip, on its Python floor and newer
(cd src/vibey_tools/gh && pip install -e ".[dev]" && python -m pytest -q)
(cd src/vibey_tools/skills && pip install -e . && python3 tools/validate_manifests.py && python3 tools/check_links.py && PYTHONPATH=src python3 -m unittest discover -s tests)
(cd src/vibey_tools/bootstrap && pip install -e ../gh && pip install -e ".[test,all]" && pytest test/ -m "not integration" --cov=vibey_bootstrap --cov-report=term)
# ...and on each tenant's floor row, its own static gates (the row's `static` key), e.g.
(cd src/vibey_runners/claude && pip install -e ../common && pip install -e ".[dev]" && mypy --strict src/claudeloop && lint-imports && bandit -q -r src/claudeloop)

# CI job `tools-lint`: vibey-gh's own linters
(cd src/vibey_tools/gh && python -m black --check vibey_gh test && isort --check-only vibey_gh test && python -m mypy vibey_gh)
```

CI (`.github/workflows/ci.yml`) also runs `image` (amd64 and arm64 builds; each
`Image contract - …` step asserts one claim the Dockerfile makes) and
`cluster-smoke` (Helm install on minikube; each `Contract - …` step asserts one
cluster behaviour). `tools-lint` additionally checks that vibey-gh's managed
automation has no drift.

## Where to go for everything else

| Need | Go to |
|---|---|
| How to work on any specific part of this codebase | `.claude/skills/`, `.cursor/rules/`, `.agents/skills/`, `.agent/rules/` |
| Comprehensive architecture diagram (layers, phases, data flow, security boundary, release channels) | `docs/project.mmd` |
| The formal model: ledger invariant, queue semantics, gate soundness | The research paper — source `docs/paper.md`; published at https://the-vibey-project.github.io/vibey/main/paper/ and https://the-vibey-project.github.io/vibey/main/paper.pdf |
| The whole documentation, offline, in reading order | The book — https://the-vibey-project.github.io/vibey/main/book.pdf · https://the-vibey-project.github.io/vibey/main/book.epub · https://the-vibey-project.github.io/vibey/main/book-print.html (built from `properdocs.yml` nav on every release) |
| The governing law: the Twelve Doctrines, sub-doctrines, the Constitution | `src/vibey_tools/gh/docs/doctrines.md`, `constitution.md` (index: `corpus-index.json`) |
| Every CLI command, subcommand, flag, default | `docs/reference/cli.md` |
| Full `vibey.toml` schema | `docs/reference/configuration.md` |
| Full architecture | `docs/plans/architecture-and-roadmap.md` |
| Domain model | `docs/plans/domain-model.md` |
| Data model | `docs/plans/data-model.md` |
| Handoff protocol | `docs/plans/handoff-protocol.md` |
| Rotation & engines | `docs/plans/rotation-and-engines.md` |
| Phase protocols | `docs/plans/phase-protocols.md` |
| Implementation plan | `docs/plans/implementation-plan.md` |
| System design and why each hard call was made | `docs/architecture/decisions/` (64 ADRs) |
| User-facing docs | `README.md` Quickstart, `docs/guides/` |
| Expansion workstreams (JIRA, clouds, k8s, clients, …) | `docs/runbooks/expansion/` (22 runbooks, `00-master-plan.md` first) |
| Contribution workflow, hooks, branch flow, PR expectations | `CONTRIBUTING.md` |
| Security policy and disclosure | `SECURITY.md` |

**Maintenance:** when procedural guidance changes, update Claude skills,
Cursor rules, Codex skills, and Antigravity rules in the **same PR**.

<!-- vibey:begin -->
This section is generated by vibey. Do not edit inside these markers --
changes here are overwritten on the next provisioning run.

## Non-negotiables

- None

## Skill plugins

none

## Full context

See .vibey/context/ for the accepted spec, acceptance criteria, NFRs, decisions, and open items.
<!-- vibey:end -->
