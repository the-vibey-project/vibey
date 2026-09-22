# NNNN — `vibey install` installs everything a developer needs on the two default OSes, from one declared catalogue

**Status:** proposed · **Date:** 2026-09-22 · **Cites:** sub-doctrines 8.a, 8.b, 8.d, 9.b, 10.e, 10.f, 12.c · **Related:** ADR-0016, ADR-0018, ADR-0023, ADR-0037, ADR-0038, ADR-0042, ADR-0043, ADR-0044 · **Evidence:** `storm/integration` at `c91561f4`, read 2026-09-22. Every `file:line` below is at that commit. Package names and versions were read the same day from archlinux.org, aur.archlinux.org, formulae.brew.sh and ollama.com.

**Owes:** nothing new as conduct. This record is mechanism (ADR-0020). The standard it
implements is the operator's, set on 2026-09-22: "the installer must at all times always
automatically install everything needed to run this on the default OSes by a human
developer". It is met in code, not by changing law. The conduct it leans on is already
ratified: 8.a (freer and more sovereign wins), 8.b (sovereign defaults, paid declared-only),
8.d (`gpt-oss:20b` is this era's default model), 9.b (declared seams), 10.e (the family
first) and 12.c (the declared state).

It owes the docs wave:
- `docs/reference/cli.md` (`install`, `doctor`);
- the README Quickstart and `docs/guides/`;
- the four agent-surface trees;
- the advertised ADR count.

## Context

### What `vibey install` does today
- **One target.** `vibey install` handles `--postgres` only. With no flag, it exits 2
  (`src/vibey/cli/main.py:1155-1182`).
- **PostgreSQL's installer.** `PostgresLocalService` (`src/vibey/infrastructure/postgres.py:134-397`)
  knows Homebrew, apt-get and dnf, but not pacman (`:304-308`). It installs `postgresql@18`
  on Homebrew (`:33`), while the chart and the CI gate run 17
  (`deploy/helm/vibey/values.yaml:53`).
- **What doctor checks.** `vibey doctor` checks the engines and PostgreSQL
  (`main.py:1185-1391`).
- **Nothing else is installed.** Nothing installs:
  - Ollama or its model;
  - a container runtime, although vibey's gates run in OCI containers
    (`src/vibey/infrastructure/container/runtime.py:11-30`);
  - the broker that ADR-0044 makes the default dispatcher, or the cache;
  - llama.cpp's `llama-server`, which qwenloop starts
    (`src/vibey_runners/qwen/src/qwenloop/infrastructure/inference.py:249`);
  - uv, which runs the repository.
- **Lanes already queued would each add their own copy.** #391 planned a bespoke
  `OllamaLocalService`, and R33 (#380) a bespoke `RabbitMqLocalService`. Each would carry its
  own copy of package-manager detection, sudo handling and step recording. Neither knows
  pacman.

### The default OSes
Arch Linux is the sovereign default and macOS the paid default. Both ship signed package
repositories that already carry almost the whole stack:
- **Arch Linux, official `extra` repository:**
  - `postgresql` 18.6
  - `rabbitmq` 4.3.1
  - `valkey` 9.1.2
  - `ollama` 0.34.2
  - `docker` 29.8.1
  - `docker-buildx`
  - `git`
  - `github-cli`
  - `uv`
  - `llama-cpp` (ships `/usr/bin/llama-server`)
  - `helm`
  - `kubectl`
  - `minikube`
  - `code` (Code - OSS)
- **macOS, Homebrew** (every formula bottle is sha256-verified by Homebrew):
  - formulas: `postgresql@17` 17.11, `rabbitmq`, `valkey`, `ollama`, `git`, `gh`, `uv`,
    `llama.cpp`, `helm`, `kubernetes-cli`, `minikube`;
  - casks: `docker-desktop`, `visual-studio-code`, `claude-code`, `codex`, `cursor-cli`,
    `antigravity-cli`.

Only the paid engines' vendor CLIs are missing from Arch's official repositories. They are in
the AUR:
- `claude-code`
- `openai-codex-bin`
- `cursor-cli`
- `antigravity-cli`

## Decision

### 1. One declared catalogue is the dependency list
`src/vibey/domain/local_stack.py` declares every dependency as pure, frozen data. Each entry
has:
- a key, a title and a group;
- whether it is in the default set;
- which installer serves it;
- per default OS, a recipe: the package source and names, the binaries that prove
  presence, an optional service, a readiness probe with a timeout, privileged post-install
  steps, and a hint line;
- the keys it `requires`;
- a `note` recording why each choice was made and when (10.f).

The declaration order is the install order. The catalogue also declares
`DEFAULT_LOCAL_MODEL = "gpt-oss:20b"`, the single source of the default model (8.d).
`ollama_chat.DEFAULT_OLLAMA_MODEL` aliases it, and a test pins qwenloop's literal to it.

Adding a tool is a data change reviewed in a pull request (12.c). No new class is needed.

### 2. What is installed

| key | group | default | Arch Linux | macOS |
|---|---|---|---|---|
| postgres | services | yes | pacman `postgresql` + initdb + role/db | `postgresql@17` |
| rabbitmq | services | yes | pacman `rabbitmq`, `rabbitmq.service` | formula, brew services |
| valkey | services | yes | pacman `valkey`, `valkey.service` | formula, brew services |
| ollama | services | yes | pacman `ollama`, `ollama.service` | formula, brew services |
| model | services | yes | `ollama pull gpt-oss:20b` (14 GB, asks first) | same |
| docker | services | yes | pacman `docker` `docker-buildx`, `docker.service`, docker group | cask `docker-desktop`, app |
| git, uv, llama-server | toolchain | yes | pacman | formulas |
| gh | toolchain | opt-in | pacman `github-cli` | formula |
| helm, kubectl, minikube | cluster | opt-in | pacman | formulas |
| vscode | editor | opt-in | pacman `code` (Code - OSS) | cask `visual-studio-code` |
| claude, codex, cursor, agy | paid-engine | opt-in | AUR | casks |

- **Python is not in the catalogue.** It is the interpreter already running `vibey install`
  (ADR-0037).
- **PostgreSQL's major differs by OS.** Homebrew is pinned to 17, the major the chart and CI
  run. Arch's repositories carry only the current major (18 today), which is inside vibey's
  supported range (14+).
- **The cache is Valkey.** 8.b names Redis as the cache surface. Valkey serves the same
  protocol, is BSD-3 (8.a prefers it over Redis 8's AGPL/RSAL/SSPL), and is the only
  Redis-protocol server in Arch's official repositories. If the operator reads 8.b as naming
  the Redis product rather than its protocol, it is one catalogue edit.
- **The GitHub CLI is opt-in.** 8.b makes GitHub declared-only, with Forgejo the forge
  default, so a GitHub client is not installed by default.

### 3. Per-OS mechanisms
- **Arch Linux.**
  - Official packages: `pacman -S --needed --noconfirm` through `sudo`.
  - AUR packages: `paru`, falling back to `yay`, run as the user, never as root. AUR packages
    are used only for opt-in entries.
  - Services: `systemctl enable --now`.
- **macOS.**
  - `brew install` or `brew install --cask`, run as the user; running as root is refused.
  - Formula daemons: `brew services start`.
  - Docker Desktop: `open -g -a Docker`.
- **Readiness.** It is a declared probe, polled with a bounded timeout. Two examples:
  `docker info` (180 s on macOS, where Docker Desktop's first start shows its agreement
  window) and `ollama list`.
- **Preconditions, stated rather than bootstrapped.** Homebrew on macOS, and sudo on Arch.
  - **Homebrew.** The installer names the signed Homebrew `.pkg` and stops. It never runs
    Homebrew's `curl | bash` installer.
  - **An AUR helper.** Needed only for the opt-in paid CLIs. The installer names the package
    page and `makepkg`.
- **Docker on Arch is the engine, not Docker Desktop.** The pacman `docker` engine is
  Apache-2.0 and in the official repositories. Docker Desktop for Linux is AUR-only,
  proprietary under a subscription agreement, and runs a VM (8.a).
- **Docker on macOS is Docker Desktop**, the operator's choice. The installer never accepts
  its agreement on the user's behalf.

### 4. No `curl | sh`, ever
- **Every artifact comes from a signed or digest-verified source.** That means:
  - Arch's signed repositories;
  - Homebrew's sha256-verified bottles and casks. Each of the six casks used here declares a
    sha256, checked 2026-09-22;
  - the AUR, for opt-in entries only, built locally by the user's helper;
  - Ollama's registry, which verifies each layer's digest.
- **A future artifact outside those sources** follows the image's pattern:
  - version and sha256 pinned in the catalogue;
  - the download checked with `sha256sum -c`, as in `deploy/docker/Dockerfile:58-85`;
  - never piped into a shell.
- **This is enforced by a test.** A guard iterates over every catalogue entry and fails if
  any probe or post-install argv starts with `curl`, `wget` or a shell.

### 5. One generic installer; bespoke classes only for behaviour data cannot express
- **The generic installer.** `CataloguePackageInstaller` serves every entry that is a
  package, an optional daemon and an optional probe. It builds on two host runners, the
  package runner and the service runner, behind `CommandExecutorInterface`, the only
  subprocess seam.
- **The bespoke exceptions.** Two dependencies keep their own classes because their steps
  are behaviour, not data:
  - PostgreSQL keeps `PostgresLocalService`, for initdb, the role and database, and version
    rules. It joins the stack through one structural adapter, `LocalServiceInstaller`.
  - The model pull is `OllamaModelInstaller`.
- **The orchestrator.** `LocalStackInstaller`, in the application layer, runs the selected
  entries in declared order.
  - A dependent whose requirement failed in the same run is SKIPPED, with the fix that names
    the requirement.
  - A failure never stops unrelated dependencies.
- **The composition root.** `bootstrap.py` composes it all as `LocalStackComposition`. The
  CLI sees only the `LocalStackFactory` port, and tests inject a fake through the typer
  context's `obj`, never by patching (9.b).

### 6. The command line
- **Bare `vibey install`** installs the default set for the detected default OS.
- **Narrowing:** `--only KEY|GROUP` (repeatable). `--postgres`, `--ollama` and `--rabbitmq`
  stay as aliases.
- **Extending:** `--with KEY|GROUP` adds opt-ins: `--with cluster`, `--with vscode`,
  `--with claude`, `--with paid-engine`.
- **The model:**
  - `--no-model` skips the pull;
  - `--model NAME` pulls another model;
  - `--yes` pulls without asking. Otherwise the model pull asks first and shows the download
    size.
- **`--check`** reports without installing.
- **A non-default host** is told so. `--postgres` keeps working there through
  `PostgresLocalService`'s apt and dnf paths.
- **Paid engines stay declared-only.** Installing a paid engine's CLI does not enable the
  engine. Enabling it stays a declaration in `vibey.toml` (8.b).

### 7. Idempotency
Every step checks before it acts:
- a binary on PATH or a package query (`pacman -Q`, `brew list`) comes before any install;
- `--needed` on pacman;
- a readiness probe comes before any start;
- `systemctl enable --now` and `usermod -aG` are idempotent;
- `createuser` and `createdb` treat "already exists" as success;
- `ollama show` comes before `ollama pull`.

A second run reports every dependency READY with `changed=False` and runs no install, start
or post-install command. Every installer's tests assert this replay.

### 8. How doctor reports
`vibey doctor` keeps its engine lines and its `postgresql` line. It then prints one line per
default dependency of the host (postgres excluded, since it already has a line):
- the line is `<key> <STATE> <detail>`;
- for anything not READY, it is followed by `fix: vibey install --only <key>`;
- the states are READY, MISSING, STOPPED, FAILED, SKIPPED and UNSUPPORTED.

The lines come from the same port and presenter as `vibey install --check`, so the two never
disagree (10.e).

The stack lines are informational: doctor's exit code is unchanged, while
`vibey install --check` exits non-zero. On a non-default host, doctor prints one line and runs
no command.

## Evidence flags (10.f)
- **Versions.** They were read on 2026-09-22 and will move. The catalogue pins package names,
  not versions, except PostgreSQL's Homebrew major.
- **The download size.** "14 GB" for `gpt-oss:20b` is ollama.com's figure, read 2026-09-22.
  It is only printed in the confirmation.
- **The cursor binary name.** cursorloop's CLI fallback runs `agent`
  (`src/vibey_runners/cursor/src/cursorloop/infrastructure/agent/cli_fallback.py:34`). The
  cask and the AUR package install only `cursor-agent`. The catalogue detects either name,
  and teaching cursorloop `cursor-agent` is a follow-up.
- **The Arch RabbitMQ probe.** It is privileged because Arch's RabbitMQ scripts refuse to run
  as an ordinary user. This is recalled from upstream packaging, and the lane's
  integration-free tests do not prove it. Verify on a live Arch host.
- **Not live-verified.** No step has been run end to end on a live Arch or macOS host by this
  record. Until it has, each dependency's install path is "specified, unit-tested with fakes,
  unverified live".

## Security impact
- **sudo.** Privileged commands run only through `sudo` on Arch: pacman, systemctl,
  post-install steps, the RabbitMQ and Docker probes, and PostgreSQL's postgres-user steps.
  The installer never elevates on macOS. Every command is a fixed argv, never a shell string,
  and every command run is recorded in the report.
- **The `docker` group is root-equivalent.** Adding the user to it on Arch is a declared step,
  shown in the report. Rootless Docker is a possible later alternative.
- **The AUR is user-submitted and unreviewed by Arch.** It is used only for opt-in paid CLIs,
  through the user's own helper, which shows the PKGBUILD.
- **The RabbitMQ `guest` account** works on loopback only, and the hint says so.

## Migration
- **Bare `vibey install` changes.** It installed nothing and exited 2; it now installs the
  default stack. This is a breaking CLI change, marked `feat(cli)!` with a `BREAKING CHANGE`
  footer.
- **Flags.** `--postgres` keeps its meaning, and `--rabbitmq` and `--ollama` keep the meaning
  #380 and #391 gave them.
- **#391** is re-scoped to the model-pull installer. Its other asks are delivered by the
  catalogue, the CLI and doctor lanes.
- **#380 should be amended:**
  - drop `RabbitMqLocalService` and its `install --rabbitmq` half, since the catalogue serves
    RabbitMQ on both default OSes;
  - keep its doctor checks, broker reachability and loop services.

  If #380 lands unchanged, a follow-up rebinds the `rabbitmq` key to its service through
  `LocalServiceInstaller`, so one code path remains.

## Consequences
- A new developer on Arch Linux or macOS runs one command and gets:
  - PostgreSQL, RabbitMQ, Valkey, Ollama with `gpt-oss:20b`;
  - Docker;
  - git, uv and llama.cpp.
- A second run is a no-op that proves the state.
- Adding a dependency, or following a package rename, is a catalogue edit with a test, not a
  new installer class.
- The catalogue is the natural home for #383's model tiers. #383's RAM-tiered default should
  replace `DEFAULT_LOCAL_MODEL` rather than add another constant.
- PostgreSQL and RabbitMQ keep apt and dnf paths for non-default hosts only through their
  bespoke services. Other dependencies are unsupported there, and say so.

## Alternatives rejected
- **One `*LocalService` class per dependency** (#391's first shape, and R33's). That is a copy
  of detection, sudo handling and step recording per tool, and a class where data suffices
  (12.c, 10.e).
- **The vendors' `curl … | sh` installers** (Homebrew, Ollama, Claude Code, Cursor). They
  execute unpinned remote code, and every tool has a signed repository or cask alternative.
- **Docker Desktop for Linux on Arch.** It is AUR-only, proprietary, subscription-bound and
  VM-based, and it loses to the official engine under 8.a.
- **Colima on macOS.** It is FOSS, and 8.a would favour it. The operator chose Docker Desktop
  on 2026-09-22, and this record keeps that choice explicit, so a later flip is one catalogue
  edit.
- **Redis from the AUR on Arch.** It is not in the official repositories, and it has a less
  free licence than Valkey for the same protocol.
- **Bootstrapping Homebrew or an AUR helper automatically.** Either would require running a
  downloaded installer or building from source with elevated trust. Both stay stated
  preconditions, with exact instructions.
