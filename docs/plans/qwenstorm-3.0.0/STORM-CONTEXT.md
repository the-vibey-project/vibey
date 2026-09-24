# QwenStorm 3.0.0: shared context for every spec writer (read first)

Updated 2026-09-22 11:45 EDT. Everything here is settled. Where a spec contradicts it, this file wins.

## Where things are
- Storm root: `$VIBEY_STORM_HOME/qwenstorm-3.0.0/` ("STORM"; the home defaults to `~/git/vibey-storm`, durable storage, sub-doctrine 10.h). It was under `/private/tmp` until a reboot emptied it on 2026-09-24; never put it there again.
- Code to read: the integration clone `STORM/integration`, branch `storm/integration`. That is
  `develop` plus the verified storm lanes. Never read `/Users/adam/git/vibey`, which is stale.
- Spec format: `STORM/SPEC-TEMPLATE.md`. End every spec with
  `## Hard repository rules (always)\nSee STORM/SPEC-TEMPLATE.md.`
- Queues: `STORM/queue.txt` (filed lanes, `slug issue deps`) and `STORM/specs/*-queue.txt`
  (unfiled lanes, `slug - deps`). A dependency may name any slug in either.
- Audit: `STORM/issue-audit/` holds `updates/<N>.md` (rewritten bodies), `gaps.md`,
  `storm-audit.md` and `roadmap-audit.md`.

## Who implements a spec
A local **gpt-oss:20b** served by Ollama, with a 131k context and about 40 turns. Its tools are
`read_file`, `write_file`, `edit_file`, `shell`, `search`, `find` and `open_file`. It succeeds on
narrow, exact lanes and fails on broad ones. So each lane is **one source file plus its
interface, and one test file**. Name exact files, classes, signatures, messages and file:line anchors, and write the whole check block out.
A reviewer verifies every result against the spec and the diff. A lane's claim that it is
complete is never evidence by itself (9.c).

## Ratified law to honour (src/vibey_tools/gh/docs/doctrines.md at integration HEAD)
- **8.a / 8.b:** sovereign first. `sovereignloop` drives this era's default model
  (**gpt-oss:20b on Ollama**, 8.d) and **VS Code** when its provider is local. `paidloop` is
  declared-only and holds `claudeloop` (the default), `codexloop`, `cursorloop`, `agyloop`, and
  VS Code on a paid provider. **OpenCode is repealed.** Paid defaults: Claude, VS Code (IDE),
  **AWS** (cloud), **GitHub** (forge). Sovereign defaults: OpenStack, Forgejo, Plane, BookStack,
  OpenBao, Nextcloud, SMTP, Kannel, Matrix, Infisical, the cache, RabbitMQ, Garage, Wazuh.
- **8.c:** exactly two loops, **a single instance per model**, fed by queues. Two rotation layers,
  both on RabbitMQ, each with a DLQ and idempotency.
- **8.e:** the test harness runs as one instance fed by a queue. **8.f:** every sovereign surface,
  the cache included, runs in one lane driven by the bus.
- **8.g:** always measured. Every loop, lane, queue, surface, test run and model records latency,
  throughput, depth and outcome, and optimizes from that evidence.
- **8.h:** **Arch Linux** is the default sovereign OS and **macOS** the default paid OS. Every change
  is proven on both.
- **7.c:** the thorough ledger. Record as much as possible, append-only, and record every
  redaction. 9.b: the declared seam (classes with interfaces; substitution never by patching an
  import). 9.c: CDD. 10.e: family first. 10.f: evidence-bounded status. 12.c: declared and
  configurable.

## Operator standards to meet in code (2026-09-22)
- **ORM always, behind interfaces.** Use SQLAlchemy 2 async on asyncpg, through the seams in the
  `orm-*` specs. Add no new raw SQL. There are two written exemptions: LISTEN, and the
  migrator's scripts.
- **Comprehensive in-memory fakes for every interface.** Tests need no outside service. Every new
  seam gets a registered in-memory fake (see the `fakes-*` specs and
  `specs/ADR-test-harness-fakes-amendment.md`). Tests substitute only at declared seams: no
  `monkeypatch.setattr` of an import, no `mock.patch`, no MagicMock as a stand-in for a port.
  Real-service tests are the opt-in `integration` tier.
- **The installer installs everything** a developer needs on Arch and macOS (see the `installer-*`
  specs).

## Operator rulings (2026-09-22)
- The cache is **Valkey** everywhere: installer and chart. 8.b's "Redis" names the protocol.
- Arch gets the **FOSS pacman docker engine** plus docker-buildx. macOS gets the Docker Desktop cask.
- Sovereignloop's VS Code is **Code - OSS / VSCodium** (Arch `code`, macOS `vscodium` cask, binary
  `codium`). Microsoft's VS Code is `vscode-paid`, for paidloop.
- **claudeloop-local is a paidloop adapter, declared-only**, because Claude Code is not FOSS.
- OpenCode is never always-on. It is declared-only and transitional until the VS Code adapter
  passes conformance, then it is retired (ADR-0046 §9).
- #383's RAM tiers: gpt-oss:20b is the default wherever it fits (8.d). Other models are opt-in
  alternatives, except in tiers where gpt-oss does not fit. Within a tier, an OSI licence wins a
  tie.
- The storm runs **unattended**, and nothing is integrated until a batch review.

## Settled facts
- The ADR drafts are `STORM/specs/ADR-test-harness-queue.md` (0045),
  `STORM/specs/ADR-two-loops.md` (0046, which supersedes R19 and R21–R28) and
  `STORM/specs/ADR-surface-lanes.md` (0047), plus `ADR-installer.md`, `ADR-orm.md` and
  `ADR-test-harness-fakes-amendment.md`.
- The repository declares `[platform] kind = "github"`. It is integrated, and its PR is to develop.
- #393's staged-bump fix is PR #394. The 3.0.0 release is PR #316, held as a draft.
- gpt-oss:20b is 13.8 GB on disk and 13.1 GB resident, with a 131k context. Ollama returns
  `message.thinking` separately; only `message.content` is read.
