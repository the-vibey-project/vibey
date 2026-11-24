# vibey — open-source orchestration for AI coding agents

AI coding agents can write the code. Getting it delivered still takes a person:
re-prompting an agent that lost the thread, re-explaining everything after a crash,
restarting the run when one vendor's credits give out at 2 a.m.

**vibey is a free, open-source orchestrator for AI coding agents**: a program that runs a team
of them for you, the way a project manager runs a team. It interviews you until the
specification is precise, builds unattended on agents that run on your own machine first and on
paid ones only if you allow them, stops only for the decisions that are yours, and writes every
step to a ledger in PostgreSQL that can only be added to, so a crashed or out-of-credit agent's
work is picked up again rather than lost.

**Who it is for**, in this order ([ADR-0087](docs/architecture/decisions/0087-the-six-audiences-in-order.md)): FOSS developers who already use
Claude Code, Codex or a local model, want finished, reviewed work rather than one session at a
time, and may build vibey with us; freelancers and freelance clients, who need fixed-scope delivery
with hard budget caps; universities and
academia, who can study and cite a working design for durable, auditable agent orchestration
([the paper](https://the-vibey-project.github.io/vibey/main/paper/)); governments and their militaries, who can
[keep a record that cannot be quietly rewritten](docs/guides/outcomes/keep-a-tamper-evident-record.md); non-profit
orgs and other small mission-driven teams, who can
[cap what agents spend](docs/guides/outcomes/cap-agent-spending.md) and
[run them on their own hardware](docs/guides/outcomes/run-agents-on-your-own-hardware.md)
([the non-profit demo](docs/guides/demos/non-profit.md)); and industry teams. Each audience is meant to have its own demo; the non-profit one is written, and the other five are not yet.

**The mission:** a free, open, censorship-free replacement for Claude Code and Codex that writes
code the way a principal software engineer does, and in time an autonomous general intelligence.
That is where the project is going, not what it does today: today vibey drives Claude Code,
Codex and a local model rather than replacing them
([why](#does-vibey-replace-claude-code-or-codex)), and its own scorecard measures how far it
still is from running without a person ([Status](#status)).

**Never written code?** You can still read this. *Code* is text files of
instructions computers run; an *AI coding agent* is a program that writes and
edits that code from plain-English requests; *deploying* means putting the
finished software somewhere people can use it. vibey's job is to manage a
team of those agents from your first description to deployed software, the
way a project manager runs a team — asking you questions up front, checking
the work, and only interrupting you when a decision is truly yours.

<!-- standard-block:install:start -->
> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** One command installs vibey and gets a new macOS or Linux
> machine ready to run a first project on your own hardware. About 15 minutes, plus the model
> download of roughly 12 GB.
>
> ```bash
> curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --full
> ```
>
> It installs `uv` and Python if you lack them, then vibey with its hub, PostgreSQL, a local
> database, Ollama, the default model, and the connection to your editors, and ends by running
> `vibey doctor`. Each step is announced first and can be skipped (`VIBEY_FULL_POSTGRES=0`,
> `VIBEY_FULL_DATABASE=0`, `VIBEY_FULL_OLLAMA=0`, `VIBEY_FULL_MODEL=0`, `VIBEY_FULL_CONNECT=0`).
> On Linux it asks for your sudo password, and on macOS it needs Homebrew. Run it again to repair
> an install.
>
> **Afterwards, two things are yours:** add the `export VIBEY_PG_URL=...` line it prints to your
> shell profile, and require `scram-sha-256` in `pg_hba.conf` (`vibey doctor` says so until you do).
> Without `--full`, the same command installs only vibey, and `vibey doctor` lists what is missing.
<!-- standard-block:install:end -->

<!-- remove-after-release:start -->
**Until the next release:** `--full` calls commands added in pull request #1978, so it works from the release after that one. Until then the plain `install.sh | sh` form installs only vibey, without the hub; follow [Set it up by hand](#set-it-up-by-hand) for the rest.
<!-- remove-after-release:end -->

<!-- standard-block:llm-driver:start -->
> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Four steps let Claude Code run your vibey projects: start the
> hub, say where projects live, connect Claude Code, and ask it. About 5 minutes after the install.
>
> 1. **Start the hub** in a terminal where `VIBEY_PG_URL` is exported (the installer printed the
>    line): `vibey hub start`
> 2. **Say where projects live.** Add this to your own `vibey.toml` (macOS:
>    `~/Library/Application Support/vibey/vibey.toml`, Linux: `~/.config/vibey/vibey.toml`):
>    `[hub]` then `projects_root = "~/vibey-projects"`. Without it, starting a project from the
>    LLM is refused.
> 3. **Connect Claude Code** from the folder you will work in:
>    `vibey connect --client claude_code --yes`. It writes `./.mcp.json` there and saves the old
>    file as `.vibey.bak`. Leave out `--client` and it writes the config for every client it knows.
> 4. **Ask.** Run `claude` in that folder, approve the `vibey` server, and type: *Use the vibey
>    tools: list my vibey projects and any open gates, then tell me what each one is waiting on.*
>
> Claude Code gets 16 tools: start a project, start work, pause work, abandon a project, list
> projects, status, gates, answer a gate, queue, ledger, budget, lanes, loops, doctor, and search
> and fetch the web through the hub. The hub refuses it the gates that spend
> money, and its instructions say to abandon a project only after you confirm. One known gap: over
> MCP it can answer the deployment opt-in gate, which asks "deploy or stay local"; only ACP refuses
> that ([`SECURITY.md`](https://github.com/the-vibey-project/vibey/blob/develop/SECURITY.md)). Codex, Cursor, VS Code,
> Claude Desktop, Gemini CLI and any ACP client such as Zed work the same way through
> `vibey connect --client <name>` or `vibey acp`.
<!-- standard-block:llm-driver:end -->

Each of those, step by step and with what to do when a step fails:
[the install guide](docs/guides/install.md), and
[drive vibey from another LLM](docs/guides/drive-from-an-llm.md).

> It was raining, and Daniel came in shaking his umbrella and holding a question.
>
> **Daniel:** Professor, the coding agents already write code. What is vibey for?
>
> **Professor Feynman:** Picture a building site. You have good bricklayers. Who decides what
> gets built, in what order, and who checks that the wall is straight?
>
> **Daniel:** The project manager.
>
> **Professor Feynman:** That is vibey. It questions you until the plan is clear, hands each
> piece to a coding agent, one on your own machine first, checks the work, and comes back to
> you only for what is yours: the design, the review, deploying, and money.
>
> **Daniel:** And if a worker walks off halfway, or runs out of credit?
>
> **Professor Feynman:** Then the site diary saves you. Every question, answer, decision and
> handoff is written in it first, and you may only add lines, never change one. The next
> worker reads the diary and starts where the last one stopped.
>
> **Daniel:** So the work lives in the diary, not in any one agent's head.
>
> **Professor Feynman:** Yes. The picture stops in one place: a paper diary is only as honest as
> whoever holds the pen. This one is a ledger in PostgreSQL that refuses every change and
> deletion, with a chain of fingerprints that shows if anyone tried.
>
> **Daniel's teach-back:** vibey is a project manager for coding agents. It questions me until
> the specification is exact, gives the work to agents, local ones first, and checks it. It
> stops only for my decisions. Every step goes into a ledger that can only grow, so when an
> agent fails, the next one carries on from the ledger.
>
> **Professor Feynman:** Right, with one thing to add: checking is not approving. The review is
> yours, and nothing is deployed unless you say so.

*Professor Feynman and Daniel are written for this documentation; their words are not quotations
from the real Richard Feynman.*

**What makes it different** — each claim links to what proves it:

- **A crash loses no job.** Jobs are held under expiring leases and reclaimed when a worker dies. A [chaos test](tests/infrastructure/db/test_chaos.py) runs 8 workers through 500 jobs, abandoning each claim with probability 0.2, and passes only if no job is lost or committed twice — [the case study](docs/case-studies/how-vibey-survives-a-crashed-agent.md) tells how.
- **The record cannot be quietly rewritten.** The database refuses every update and delete to the ledger ([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)), and a SHA-256 hash chain over its events makes any edit visible ([`ledger_chain.py`](src/vibey/domain/ledger_chain.py)). **See one for yourself in the [ledger explorer](https://the-vibey-project.github.io/vibey/main/explorer/)**: a public, searchable view of a real project's ledger, where your browser checks each record's digest.
- **Local first, paid by choice.** The default engine runs the Heretic v2 build of GPT-OSS 20B on your own machine through Ollama ([ADR-0064](docs/architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md), [ADR-0099](docs/architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)); a paid engine runs only when no local one can ([ADR-0038](docs/architecture/decisions/0038-local-engines-are-preferred-first.md)).
- **You decide what matters.** Design, review and deployment wait for your recorded answer, and a waiting question parks its job instead of blocking a worker ([ADR-0009](docs/architecture/decisions/0009-human-gates-are-parked-jobs.md)).
- **Held to gates it cannot talk its way past.** vibey's four code layers each need 100% branch coverage to merge ([ADR-0023](docs/architecture/decisions/0023-four-layers-four-floors.md)), every hard call is argued in a [decision record](docs/architecture/decisions/) (105 ADRs), and releases publish through PyPI trusted publishing with no stored token ([`vibey-engine.yml`](.github/workflows/vibey-engine.yml)).

**See a real ledger** — no install, no account: [open the ledger explorer](https://the-vibey-project.github.io/vibey/main/explorer/), search every public decision, finding and phase change of a real project, and check each record yourself.

The full setup is under [Install](#install), then [Quickstart](#quickstart). Came with a
specific problem? [What do you want to do?](docs/guides/outcomes/index.md) answers six,
from running agents on your own hardware to capping what they spend.

**Contribute in your first hour.** Clone, `uv sync --extra dev`, run one test, make one
small change: [the first-hour guide](CONTRIBUTING.md#your-first-hour) walks it command
by command, from a [good first issue](https://github.com/the-vibey-project/vibey/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22)
to your pull request. The project governs itself by written law — start with
[the Constitution](src/vibey_tools/gh/docs/constitution.md).

---

[![PyPI](https://img.shields.io/pypi/v/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![PyPI downloads](https://img.shields.io/pypi/dm/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![Python versions](https://img.shields.io/pypi/pyversions/vibey-engine)](https://pypi.org/project/vibey-engine/)
[![CI](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/the-vibey-project/vibey/blob/develop/LICENSE)
[![Docs](https://img.shields.io/badge/docs-read-blue.svg)](https://the-vibey-project.github.io/vibey/main/)
[![Research paper](https://img.shields.io/badge/paper-PDF%20%7C%20HTML-6f42c1.svg)](https://the-vibey-project.github.io/vibey/main/paper.pdf)
[![Book](https://img.shields.io/badge/book-PDF%20%7C%20EPUB-0a7ea4.svg)](https://the-vibey-project.github.io/vibey/main/book.pdf)

**Prefer to read first?** The design is a research paper — [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) · [HTML](https://the-vibey-project.github.io/vibey/main/paper/) —
and the whole documentation is a book — [PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print](https://the-vibey-project.github.io/vibey/main/book-print.html).

The project and its engine are **vibey**; every app and interface a person uses is
**krypton** (sub-doctrine 9.e), whose emblem is the krypton atom: krypton-84, four shells.

For the precise version: a queue-based, six-phase conductor for autonomous
software delivery — with an optional visual-design interstitial and opt-in
Azure deployment — built on top of the [`*loop` autonomous session
runners](src/vibey_runners/), which live in this repository as uv
workspace members (ADR-0021).

## Contents

- [What problem this solves](#what-problem-this-solves)
- [Krypton client interfaces](#krypton-client-interfaces)
- [Install](#install)
- [Quickstart](#quickstart)
- [Drive vibey from another LLM](#drive-vibey-from-another-llm)
- [Command reference](#command-reference)
- [Configuration](#configuration)
- [Notifications](#notifications)
- [Telemetry](#telemetry)
- [The shape of it](#the-shape-of-it)
- [How it fits together](#how-it-fits-together)
- [Why it isn't just another agent framework](#why-it-isnt-just-another-agent-framework)
- [Questions people ask](#questions-people-ask)
- [Documentation](#documentation)
- [Status](#status)
- [Troubleshooting](#troubleshooting)
- [Upgrading](#upgrading)
- [Formal notes](#formal-notes)
- [Project links](#project-links)
- [Join the community](#join-the-community)
- [Related projects](#related-projects)
- [License](#license)
- [Say it in one line](#say-it-in-one-line)

## What problem this solves

An autonomous coding session is not autonomous software delivery. A single
`claudeloop` run can finish a task, but it cannot interview you until the spec
is sharp, split the work into parallel items, verify each one against gates it
cannot game, survive its own credit exhaustion by handing off to a different
vendor's engine *without losing a single open question*, or know that a review
finding should reopen design rather than vanish into a transcript.

vibey conducts all of that. You describe what you want; it interviews you until
the spec is sharp, builds unattended across a pool of engines with real budget
caps, reviews the result with you, and (only if you opt in) deploys. Every
choice, finding, and handoff lives in an append-only PostgreSQL ledger — never
in one vendor's chat session.

| | |
|---|---|
| Version | 0.4.0, held below 1.0 (`[version] max_major = 0` in `.vibey-gh.toml`) |
| Runs on | macOS / Linux, local. No cloud control plane required. Windows is not supported. |
| Language | Python 3.12+ |
| Queue | PostgreSQL 14 to 18 (`FOR UPDATE SKIP LOCKED`) |
| Engines | Paid: [`claudeloop`](src/vibey_runners/claude) and [`codexloop`](src/vibey_runners/codex). Local, from the runner in [`src/vibey_runners/qwen`](src/vibey_runners/qwen): `gptossloop`, the sovereign default on the Heretic v2 build of GPT-OSS 20B (on by default, and the sovereign DESIGN provider), and the opt-in `qwenloop` on Qwen (`qwen3:14b`); plus `claudeloop-local`, the claudeloop binary on a local backend profile (opt-in, no command of its own). Local engines are preferred first when switched on (ADR-0027, ADR-0038, ADR-0064, ADR-0099). `cursorloop` and `agyloop` are retired ([ADR-0078](docs/architecture/decisions/0078-retire-cursorloop-and-agyloop.md)). All three runners ship inside the `vibey-engine` package (ADR-0037). |
| State dir | `.vibey/` |
| Env prefix | `VIBEY_` |
| Done marker | Each loop's own marker: `CLAUDELOOP_TASK_FULLY_COMPLETE`, `CODEXLOOP_TASK_FULLY_COMPLETE`, and the local runner's `QWENLOOP_TASK_FULLY_COMPLETE` |

## Krypton client interfaces

Krypton is the client family for vibey: one interface across phones, the browser, desktop
workstations and code editors. The apps reach vibey through the hub (`vibey serve`, on
`http://127.0.0.1:8765/` by default); the VS Code extension can also drive vibey and a local
model on your own computer.

### Mobile & Web (`clients/app`)

Built with React Native and Expo for iOS, Android, and Web:

| Frontier Chat | Add to Session Modal | Usage & Limits | Settings & Themes |
| :---: | :---: | :---: | :---: |
| <img src="screenshots/01-mobile-chat.png" width="180" alt="Mobile Chat" /> | <img src="screenshots/02-mobile-add-session.png" width="180" alt="Add to session" /> | <img src="screenshots/03-mobile-usage.png" width="180" alt="Usage Telemetry" /> | <img src="screenshots/04-mobile-settings.png" width="180" alt="Settings Screen" /> |

### Desktop Native (`clients/desktop`)

Written in C on GTK 4 and libadwaita for macOS and Linux:

| Desktop Chat Workspace | Live Inspector Drawer |
| :---: | :---: |
| <img src="screenshots/08-desktop-chat.png" width="440" alt="Desktop Chat" /> | <img src="screenshots/09-desktop-inspector.png" width="440" alt="Live Inspector Drawer" /> |

### VS Code Extension (`clients/vscode`)

Right-hand docked chat participant for VS Code, VSCodium, and Cursor. In the chat, address it
as `@krypton`:

| VS Code Right-Hand Chat Participant |
| :---: |
| <img src="screenshots/11-vscode-panel.png" width="720" alt="VS Code Extension Panel" /> |

*Explore all screens and details in the [Visual Tour & Screenshots Guide](https://the-vibey-project.github.io/vibey/main/guides/gallery/).*

## Install

The one-command install is the first block at the top of this page. This section is the
whole picture: every interface, what each needs, and how to do it by hand.

*Never used a terminal?* On **macOS**, press **Cmd + Space**, type **Terminal**, and press
**Enter**. On **Linux**, press the **Super (Windows) key**, type **Terminal**, and press
**Enter**. Copy any command below, paste it into the window, and press **Enter**.

| What you want to install | Platform | Exact command or click-by-click steps |
|---|---|---|
| **1. vibey, set up for a first project, and the `krypton` browser launcher** | macOS & Linux | `curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh \| sh -s -- --full --with-krypton` (leave out `--with-krypton` for vibey alone) |
| **2. Your existing AI chat or IDE (`vibey connect`)** | Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI (over MCP) and Zed (over ACP) | In the folder you will work in, run `vibey connect --client claude_code --yes` (or another client id from `vibey connect --list`). Claude Code and VS Code are configured in the current folder; the others for your whole account. With no `--client`, it writes the configuration for all seven, installed or not. Then ask your chat: *"What vibey projects and gates are open?"* |
| **3. krypton browser launcher (`krypton-app`)** | macOS & Linux | `uv tool install krypton-app`, then type `krypton` and press Enter: it starts the local hub and opens it in your browser. Like vibey, it needs PostgreSQL and `VIBEY_PG_URL`. |
| **4. krypton desktop app (native chat-first app)** | **macOS 15+ (Apple silicon)** | 1. Download `krypton-desktop-<version>-macos-arm64.dmg` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (or [krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)).<br>2. Double-click the `.dmg` and drag **krypton** to **Applications**.<br>3. It is ad-hoc signed and not yet notarised, so run `xattr -dr com.apple.quarantine /Applications/krypton.app` in Terminal (or open it once and click **Open Anyway** in **System Settings → Privacy & Security**). |
| **4. krypton desktop app (native chat-first app)** | **Linux (any distro: Ubuntu, Fedora, Arch — Flatpak)** | Download `krypton-desktop-<version>-linux-x86_64.flatpak` (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run:<br>`flatpak install --user krypton-desktop-<version>-linux-x86_64.flatpak`<br>Launch with: `flatpak run io.github.the_vibey_project.krypton` |
| **4. krypton desktop app (native chat-first app)** | **Linux (Ubuntu 24.04+ native tarball)** | Download `krypton-desktop-<version>-linux-x86_64.tar.gz` (or `aarch64`) from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run:<br>`sudo apt update && sudo apt install -y libgtk-4-1 libadwaita-1-0 libsoup-3.0-0 libjson-glib-1.0-0 libavahi-client3 libavahi-glib1 glib-networking`<br>`sudo tar -xzf krypton-desktop-<version>-linux-x86_64.tar.gz -C /`<br>Launch with: `krypton-desktop` |
| **5. krypton for VS Code / VSCodium / Cursor** | macOS & Linux | **VSCodium / Open VSX editors:** `codium --install-extension the-vibey-project.krypton`<br>**VS Code / Cursor:** Download `krypton-vscode-<version>.vsix` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) and run `code --install-extension krypton-vscode-<version>.vsix` (or in VS Code click **Extensions → `…` → Install from VSIX…**). |
| **6. krypton web app (browser UI)** | Any current browser | Download `krypton-web-<version>.tar.gz` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases): static files any web server can serve, for example `mkdir krypton-web && tar -xzf krypton-web-<version>.tar.gz -C krypton-web && python3 -m http.server -d krypton-web`. The hub sends no cross-origin (CORS) headers by design, so a page served from another address may not be able to read it; the [downloads page](docs/guides/downloads.md) has the current advice. |
| **7. krypton mobile app (Android & iOS)** | **Android & iOS** | **Android:** download `krypton-android-<version>.apk` from [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) on your phone, allow installs from unknown sources and tap it (or from a computer: `adb install krypton-android-<version>.apk`). It is signed with the Android debug key, for sideloading and testing, not a Play Store build.<br>**iOS:** there is no App Store or TestFlight listing. The release builds a signed `krypton-ios-<version>.ipa` only when the project's Expo credential is set, and does not submit it anywhere; the file does not install by opening it. Developers can run the app in Expo Go (`cd clients/app && npm ci && npx expo start`).<br>**Then pair the phone** with the hub on your computer: `vibey hub pair` shows a QR code and a 6-digit code the phone claims within two minutes. |
| **Uninstall any krypton app cleanly** | macOS & Linux | `curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/uninstall-krypton.sh \| sh -s -- --yes` (removes krypton interfaces; never touches `vibey-engine`). |

For complete beginner-friendly walkthroughs of every platform, see
[Install, copy, reinstall, uninstall](docs/guides/install.md) and
[Downloads](docs/guides/downloads.md).

**What you need.** macOS or Linux; Windows is not a supported target. The install script
fetches `uv` and Python 3.12 itself, so you need Python 3.12+ only to install with `pip` or
`pipx` (which are not tested). vibey needs **PostgreSQL 14 or newer**: it supports every
currently supported major (14 to 18), and CI runs the database suite against each one. Every
database-backed command reads the connection string from `VIBEY_PG_URL`; vibey never guesses a
database and exits with `VIBEY_PG_URL is not set` when it is missing.

Memory, disk, GPU, network and each krypton client's needs are on the
[system requirements](docs/reference/system-requirements.md) page. Those figures are
re-measured every week, and any figure that could not be re-measured is marked stale.
For the sovereign default (a local model), memory is the binding constraint.

**Ready-built files.** Every release on GitHub (the newest is `vibey-v0.4.0`) also carries the
user interfaces built for each supported platform: krypton desktop for Linux (a Flatpak bundle
and an Ubuntu build, x86_64 and arm64) and for macOS on Apple silicon (a self-contained `.dmg`,
ad-hoc signed), the krypton app for Android and the web, the iOS build when its credential is
set, krypton for VS Code (also on Open VSX), and the Python wheels, with a `SHA256SUMS` file and
build provenance. The [downloads page](docs/guides/downloads.md) lists each file, what it runs on
and whether it is signed.

**One install is the whole family.** The `vibey-engine` package puts ten commands on your
`PATH` together ([ADR-0037](docs/architecture/decisions/0037-one-distribution-one-version.md)):
`vibey`; the four runner commands `claudeloop`, `codexloop`, `gptossloop` and `qwenloop`; and
the tools `vibey-gh`, `vibey-skills` (with its old name `vibe-skills`), `vibey-bootstrap` and
`azbootstrap`. `claudeloop-local` is an engine, not a command: it is the `claudeloop` command
on a local backend profile. The apps ship separately as `krypton-app`
([ADR-0069](docs/architecture/decisions/0069-two-packages-vibey-engine-and-krypton-app.md)).
What each paid engine still needs is its own vendor CLI and credentials, which `vibey doctor`
checks.

### Set it up by hand

Use this path if you did not run `--full`, or if one of its steps failed. Each command is safe
to run again.

```bash
uv tool install 'vibey-engine[hub]'   # vibey, with the hub that vibey serve, vibey hub and vibey mcp need
vibey install --postgres              # install and start PostgreSQL (Homebrew, apt or dnf)
vibey install --database              # the database, its two roles and the migrations
vibey install --model                 # pull the local model into Ollama (about 12 GB)
vibey connect --client claude_code --yes   # optional: connect your chat or editor
vibey doctor                          # what is still missing
```

- **`vibey install --postgres`** uses Homebrew, apt or dnf. Homebrew installs and starts
  PostgreSQL 18; apt and dnf install your distribution's default version through `sudo`, so it
  may ask for your password. `vibey doctor --install-postgres` does the same before checking.
- **`vibey install --database`** makes the database (`vibey`), an owner role (`vibey`) and an
  application role (`vibey_app`), keeps their passwords in `~/.pgpass` (never printed), applies
  the migrations as the owner, and prints the line to keep in your shell profile:
  `export VIBEY_PG_URL=postgresql://vibey_app@localhost:5432/vibey`. `--db-name`,
  `--owner-role`, `--app-role` and `--admin-user` change the names.
- **`vibey install --model`** pulls the model the local loop runs (the Heretic v2 build of
  GPT-OSS 20B, `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`) into the Ollama at
  `VIBEY_OLLAMA_URL`, unless it is already there. Install Ollama first: on macOS
  `brew install ollama` then `brew services start ollama`; on Linux, Ollama's own installer.
  The [local models guide](docs/guides/local-models-ollama.md) has the details.
- **Your own PostgreSQL.** Two DSNs, because the ledger is append-only by the database
  ([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md)):
  the application connects as a role that can read and append to the ledger and nothing more,
  and the owner's DSN is given to `vibey migrate` alone, never exported:

  ```bash
  export VIBEY_PG_URL=postgresql://vibey_app:change-me@localhost:5432/vibey
  VIBEY_PG_MIGRATE_URL=postgresql://vibey@localhost:5432/vibey vibey migrate
  ```

  `vibey migrate` creates the application role if it is missing and its DSN carries a password,
  grants it exactly what it needs, and exits 1 unless the ledger guard is in force. One DSN still
  works, but `vibey doctor` fails its `ledger-guard` check until the roles are split
  ([database roles](docs/reference/configuration.md#database-roles)).
- **Either way**, require `scram-sha-256` for every connection in `pg_hba.conf`
  ([`SECURITY.md`](SECURITY.md), section 7); `vibey doctor` says so until you do.

<!-- remove-after-release:start -->
**Until the next release**, `vibey install --database` and `vibey install --model` do not exist
yet (they come with pull request #1978). Make the database with `createdb vibey`, then use the
two-DSN `vibey migrate` above, and pull the model with
`ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`.
<!-- remove-after-release:end -->

### Local engines, skills and plugins

`gptossloop` and `qwenloop` install with everything else; what is opt-in is the
*feature*, not the install. Each local engine has a switch: `gptossloop` — the
sovereign default on the Heretic v2 build of GPT-OSS 20B — is on unless
`VIBEY_FEATURE_GPTOSSLOOP=0`; `qwenloop` — the same runner on `qwen3:14b` — needs
`VIBEY_FEATURE_QWENLOOP=1`; and `claudeloop-local` (claudeloop on a local backend profile)
needs `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` (ADR-0064). A switched-on local engine is
**preferred first** for BUILD — a paid engine runs only when no local one is
eligible — and `vibey doctor` lists it; `vibey doctor` also honours
`[features] gptossloop = false` / `qwenloop = true` / `claudeloop_local = true`
in a `./vibey.toml`. With no `--provider`, `vibey work` and `vibey worker` run
DESIGN and DECOMPOSE on the sovereign gptossloop providers too (ADR-0038).
`VIBEY_OLLAMA_URL` is the one endpoint setting; `VIBEY_SOVEREIGN_MODEL=stock` picks OpenAI's
unchanged `gpt-oss:20b` instead, and `VIBEY_OLLAMA_MODEL` names any other tag
([ADR-0099](docs/architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)).
The [local models guide](docs/guides/local-models-ollama.md) has the Ollama recipe.

To add deterministic, budgeted context packets from the `vibey-skills`
marketplace, enable it per project — `vibey-skills` ships in the same
distribution, so there is nothing extra to install:

```bash
vibey new my-app --repo ~/src/my-app \
  --skills-context-mode shadow --skills-context-budget 6000
```

`shadow` builds and records packet provenance without changing agent prompts.
After observing results, switch the project config to `inject` to append successful
packets to BUILD prompts. Missing tools, timeouts, low-confidence retrieval, and
insufficient budgets all fall back to the original prompt. The feature is off by
default, and wind-down prompts are never modified (ADR-0031).

The same tree is a Claude Code plugin marketplace — every plugin in the family, the 153
skills plugins and vibey-gh's four, from one address and nothing else:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install security-principles@vibey
/plugin                                    # browse all 157
```

The root manifest is rendered from the workspace members by `vibey-gh marketplace` and
held to them by `vibey-gh check` (ADR-0034); it is never edited by hand. Since the family
ships as one distribution (ADR-0037) this root manifest is the only marketplace there is.

## Quickstart

Your first project on the local engine, after the `--full` install (or after
[Set it up by hand](#set-it-up-by-hand)). Nothing here spends money.

1. Open a new terminal, so the `export VIBEY_PG_URL=...` line you saved is read, and check:

   ```bash
   vibey doctor
   ```

   You should see `gptossloop` installed, the model found, and PostgreSQL ready. Paid engines
   show `auth FAIL` until you log in to them; that does not stop a local run.

2. Make a folder for the project. BUILD takes a git worktree from it, so it must be a git
   repository with at least one commit (if git says it does not know who you are, set
   `git config --global user.name` and `user.email` first):

   ```bash
   mkdir -p ~/src/my-app && cd ~/src/my-app
   git init -b main && git commit --allow-empty -m "chore: start my-app"
   ```

3. Create the project and its first design interview:

   ```bash
   vibey new my-app --repo ~/src/my-app --intake "A command-line greeter that prints Hello, NAME"
   ```

4. Record the local engine's conformance, so BUILD may pick it:

   ```bash
   vibey doctor --conformance --record --engine gptossloop
   ```

5. Start a worker. It runs DESIGN and the work plan on the local model, then BUILD on
   `gptossloop`, and keeps going until something needs you:

   ```bash
   vibey worker
   ```

6. In a second terminal, answer what waits on you. `vibey gates` prints each open gate's id,
   its prompt, and the exact command that answers it:

   ```bash
   vibey gates
   vibey answer <gate-id> --defaults            # the design interview: accept every default
   vibey design accept <project-id>             # accept the spec; add --visual for a visual-design stage
   vibey answer <gate-id> --verdict accept      # the review
   vibey answer <gate-id> --choice local_only   # stay local: the project is DONE without deploying
   ```

   `<gate-id>` and `<project-id>` are the ids `vibey gates` and `vibey projects` print.

Some things to know on the way:

- **Research.** DESIGN research searches the web through a local SearXNG first
  (`vibey searxng install`, which needs a container runtime), and Brave only as a backup when a
  key is set ([ADR-0102](docs/architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)).
  With neither, research parks a `research_evidence` gate for you; `vibey worker
  --auto-record-research-gaps` records the topic as not researched and goes on instead.
- **Caps.** `vibey new --max-cycle-dollars 15` (and `--max-cycle-turns`) caps what a cycle may
  spend once paid engines join. A tripped cap parks a `budget_exhausted` gate;
  `vibey answer <gate-id> --raw '{"max_dollars": 25}'` grants more.
- **Paid engines.** `vibey worker --provider claudeloop --engines claudeloop,codexloop -j 2`
  runs DESIGN on claudeloop and BUILD across both paid engines, two jobs at a time. They need
  their own logins first, and `vibey doctor --conformance --record` for each. `--provider
  scripted` is the test double; `--provider qwenloop` is still accepted and read as gptossloop
  (ADR-0064).
- **Unattended.** `vibey worker --autonomous` answers what is safe to answer for one project
  (the interview defaults, more attempts, research gaps, design and review acceptance, and
  finishing locally); never a spending gate, never a deployment, and never publishing. Each
  answer is on the ledger.
- **Watching.** `vibey projects` lists your projects with their ids and open gates, `vibey
  status` shows one, `vibey watch` is a live dashboard, and `vibey llm tail` follows the
  conversation with the local model. `vibey gates`, `vibey projects` and `vibey status` take
  `--json`.

The [greeter live-demo runbook](docs/guides/greeter-live-demo.md) walks a full
paid run end to end, including the zero-touch contracts.

## Drive vibey from another LLM

The second block at the top of this page is the short form. The full guide is
[Drive vibey from another LLM](docs/guides/drive-from-an-llm.md); this is what to know first.

- **Two ways in.** Claude Code, Claude Desktop, Codex, Cursor, VS Code and Gemini CLI launch
  `vibey mcp`, a Model Context Protocol server over stdio. Zed and other Agent Client Protocol
  editors launch `vibey acp`, and vibey is itself the agent
  ([ADR-0100](docs/architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md),
  [ADR-0101](docs/architecture/decisions/0101-the-acp-agent-and-self-installing-services.md);
  [the Zed guide](docs/guides/acp.md)). `vibey connect --list` names every client it knows.
- **Everything goes through the hub.** Each tool call is one request to the hub on
  `127.0.0.1:8765`, as a scoped `agent` principal, never the owner. `vibey mcp` starts the hub
  itself on the first call when none runs, but only if the client's own environment carries
  `VIBEY_PG_URL`; starting it yourself with `vibey hub start` is the reliable route.
- **What the agent may do.** View, answer and run by default: list projects, gates, queue,
  ledger, budget, lanes and loops; answer a gate; start, pause or abandon a project (abandon is
  a dry run until you confirm); and search or fetch the web through the hub. It never holds the
  `spend` scope, so the hub refuses it the budget and deployment gates; answer those yourself
  with `vibey answer`. A repository may only narrow the agent's scopes, never widen them.
- **The plugin route.** In Claude Code, `/plugin marketplace add the-vibey-project/vibey` then
  `/plugin install vibey@vibey` adds the same server and the `vibey-chat-driver` skill. That
  server runs whichever `vibey` is first on your `PATH`, while `vibey connect` writes the
  absolute path of the install you ran it from. Use one route per project, not both.
- **What is refused, and why:** [`SECURITY.md`](SECURITY.md), sections 10 to 13.

## Command reference

Every command's flags and defaults are in the
[CLI reference](docs/reference/cli.md); `vibey explain <code>` explains any error code. The
most common ones:

| Command | What it does |
|---|---|
| `vibey -v` / `vibey --version` | Print the `vibey-engine` and `krypton-app` versions. Verbose output is `-d` (`-dd`, `-ddd`), not `-v`. |
| `vibey install` | Install what vibey can manage: `--postgres`; and, from the release after pull request #1978, `--database` and `--model`. |
| `vibey doctor` | Pre-flight: PostgreSQL, engine install state, versions, auth; `--conformance` runs the 9-check suite, `--record` persists health, `--install-postgres` installs PostgreSQL first, `--cluster` runs the in-cluster preflight. |
| `vibey migrate` | Apply migrations as the owner (`VIBEY_PG_MIGRATE_URL`) and reconcile the application role's grants. |
| `vibey connect` | Register vibey in Claude Code, Claude Desktop, Codex, Cursor, VS Code and Gemini CLI (over `vibey mcp`) and Zed (over `vibey acp`) (`--client`, `--yes`, `--dry-run`, `--list`; ADR-0100). |
| `vibey mcp` / `vibey acp` | Serve the hub's tools to a chat client over MCP, or be the agent for an editor over ACP (ADR-0100, ADR-0101). |
| `vibey serve` / `vibey hub start\|stop\|status` | Run the hub every krypton client and agent reaches, in the foreground or in the background (ADR-0068). |
| `vibey hub pair\|devices\|revoke` | Pair a phone or another computer by QR code and 6-digit code, list paired devices, revoke one (ADR-0071). |
| `vibey new` | Create a project and enqueue its first DESIGN interview (`--intake`, caps, `--accept-spec-json` to skip DESIGN). |
| `vibey projects` / `vibey gates` | Every project with its phase and open gates; every open gate with the command that answers it. |
| `vibey answer` | Answer a parked human gate (`--defaults`, `--verdict`, `--choice`, `--raw`). |
| `vibey design resume/accept` / `vibey visual accept/waive` | Resume or accept DESIGN; accept or waive VISUAL_DESIGN. |
| `vibey worker` | Long-running worker: dispatches jobs across every phase (`--provider scripted\|claudeloop\|gptossloop`, `--engines`, `-j`, `--all-projects`, `--autonomous`, `--azure memory\|az`). |
| `vibey work` | Process one ready DESIGN or VISUAL_DESIGN job for a project (foreground, capped). |
| `vibey watch` / `vibey status` | Live dashboard, or one-shot status (`--json` for scripting). |
| `vibey engines` / `vibey models` / `vibey loops` | Engine health and circuits; local model families and what Ollama can run; the two loops (sovereign and paid), their engines and the plugins, MCP servers and skills each run is given (ADR-0103). |
| `vibey cost` / `vibey budget` | This cycle's spend against its caps; see, set or clear a project's caps (`--json`). |
| `vibey ledger show\|search\|export\|site` | Read, search, publish a redacted shard of, or build a static site from the append-only ledger. |
| `vibey inputs add\|list` | Give every BUILD run of a project a pasted text or a file, stored by its hash (ADR-0104, ADR-0105). |
| `vibey searxng` / `vibey search` / `vibey fetch` | Install the local SearXNG; search the web through it (Brave only as a backup); read one public page as text (ADR-0102). |
| `vibey retry` / `vibey recover` / `vibey abandon` | Get a stalled project moving; return stuck leased jobs to the queue; stop a project for good, with a reason. |
| `vibey queue` | See the job queue in claim order, and move a job to the front. |
| `vibey ultra` | Run a project's BUILD passes at ULTRA effort, with no turn limit (ADR-0063). |
| `vibey supervisor` | Render the launchd or systemd units that keep `vibey worker --all-projects` running; it prints the command that loads them. |
| `vibey deploy status/inspect/plan/cancel/rollback` | Inspect and control Phases ④–⑥. |
| `vibey state` | Keep this database and its sealed copy on GitHub in step (ADR-0086). |
| `vibey operator` | Run the Kubernetes operator (`pip install 'vibey-engine[operator]'`; ADR-0025). |

## Configuration

`vibey.toml` is optional: with none, every default applies. vibey reads it from three places
and never merges them: **your own file** in your configuration folder
(`~/Library/Application Support/vibey/vibey.toml` on macOS, `~/.config/vibey/vibey.toml` on
Linux), which holds the powers (`[hub]`, `[web]`, `[loops]`, `[inputs]`, `[acp]`); **this
folder's** `./vibey.toml`; and **the project's** `vibey.toml` at the root of the checkout
`vibey new --repo` names. A file that is not your own may only narrow what yours grants.

Not every table does something yet. Some are live, some are copied into the project's stored
record once by `vibey new` (`[notifications]`, `[telemetry]`, `[gates]`,
`[engine_environment]`, `[design]`, `[build]`, `[human_gates]`, `[publish]` and the
`[engines]` dispatch keys), and some are parsed and then ignored. Before you set a key, find its
table in [Where each table is read](docs/reference/configuration.md#what-is-read-at-runtime-today):
it names the file, who may set it, and whether the key does anything today. The schema of the
core tables is `parse_config` in `domain/config.py`; the newer tables have loaders of their own.

The local-engine switches are the one place to be careful. `[features] gptossloop`,
`[features] qwenloop`, `[features] claudeloop_local` and `[engines.claudeloop_local]` are read
from `./vibey.toml` by `vibey doctor` and `vibey loops` only. Nothing writes them into a
project's record, so the switches that reach the worker are the environment variables
`VIBEY_FEATURE_GPTOSSLOOP`, `VIBEY_FEATURE_QWENLOOP`, `VIBEY_FEATURE_CLAUDELOOP_LOCAL` and
`VIBEY_CLAUDELOOP_LOCAL_PROFILE`.

What does configure a project at creation is a handful of `vibey new` flags (`--max-cycles`,
`--max-cycle-dollars`, `--max-cycle-turns`, `--skills-context-mode`, `--skills-context-budget`,
`--design-default-scope`), recorded into that project's stored config — see the
[CLI reference](docs/reference/cli.md). The two caps can be changed after that:
`vibey budget set` and `vibey budget clear` rewrite them in the stored config,
record each change on the ledger, and bind the next BUILD session of a worker
already running. The full schema, with defaults and an example file, is the
[configuration reference](docs/reference/configuration.md).

## Notifications

`infrastructure/notify/` implements a `NotificationService` that dispatches
desktop alerts and HMAC-SHA256-signed webhooks (`X-Vibey-Signature`, see
[SECURITY.md](SECURITY.md#6-webhook-payload-integrity--implemented-unit-tested-and-active-when-configured)), and it is covered
by tests. `build_app()` constructs it; workers notify on newly raised gates,
and project transitions notify on phase changes and completion. Enable it in
the repository TOML with `[notifications] enabled = true`; `vibey new` stores
that table with the project.

## Telemetry

`infrastructure/otel.py` implements `TelemetryTracer` (span tracing for
jobs, turns, and handoffs) and `TelemetryMetrics` (engine-selection,
queue-latency, phase-duration, handoff-failure, and cost-spend counters),
plus `calculate_rotation_fairness()` for measuring rotation fairness against
declared engine weights. It is covered by unit tests and constructed by
`build_app()`. The worker records queue latency, phase duration, and job spans;
BUILD records engine turns, selections, handoffs, and cost spend. Set
`[telemetry] enabled = false` to disable those runtime calls for a project.
Telemetry is an in-process recorder for now: it is available to the running app, but there is
no external exporter yet (`export_path` is parsed and not used).

## The shape of it

```
  DELIVERY STAGE SET
  INTAKE → ① DESIGN ──┬─ no ───────────────→ ② BUILD ⇄ ③ REVIEW
             ▲        │                       autonomous / interactive
             │        └─ yes → [VISUAL DESIGN]
             │                  interactive, media generation + confirmation
             │                            │ visual-ready
             │                            └──────────────→ ② BUILD
             │
             └─ loop-back from ② BUILD or ③ REVIEW: a finding needs clarification

  ③ REVIEW ── no deployment ─────────────────────────────→ DONE (local)
       │ opt in
       ▼
  DEPLOYMENT STAGE SET
  ④ DEPLOY DESIGN → ⑤ DEPLOY EXECUTE → ⑥ DEPLOY REVIEW → DONE (deployed)
       interactive       autonomous          interactive
             ▲                 ▲                    │
             └─────────────────┴────────────────────┘
                  ⑥ can also route a defect back to ①, ②, or ③
```

**The six phases** — ① Design · ② Build · ③ Review · ④ Deploy Design ·
⑤ Deploy Execute · ⑥ Deploy Review. The circled numbers above are these;
**bold** below means the phase talks to you.

**① Design** → ② Build → **③ Review** → **④ Deploy Design** → ⑤ Deploy Execute → **⑥ Deploy Review**

Phases 1, 3, 4, and 6 talk to you. The optional Visual Design stage also talks to
you and cannot hand work to BUILD until every planned visual is accepted or you
explicitly waive the stage. Phases 2 and 5 run unattended, survive rate-limit
windows and credit exhaustion, and rotate eligible engines/providers when one
runs dry. Phase 3 asks whether to deploy; "no" is a successful local completion.
Phase 6 accepts a successful deployment, requests changed deployment details in
Phase 4, retries an unambiguous deployment in Phase 5, or routes an application
defect back to the appropriate delivery phase.

## How it fits together

```
  you ──► vibey CLI · krypton apps and the VS Code extension (through the hub)
            │ answers to gates               ▲ questions, reviews, budget parks
            ▼                                │
  ┌─────────────────────── vibey conductor ───────────────────────┐
  │  six-phase machine  ·  human gates  ·  budget brake  ·  handoff │
  └──────────┬────────────────────────────────────┬────────────────┘
             │ claims jobs under leases            │ appends every event first
             ▼                                     ▼
   PostgreSQL job queue                 append-only ledger in PostgreSQL
   (FOR UPDATE SKIP LOCKED)             (no update, no delete; hash-chained)
             │
             ▼ one engine per job, local engines first
   gptossloop · qwenloop · claudeloop-local        on your machine
   claudeloop · codexloop                          paid, when you allow them
             │
             ▼
   one git worktree per work item ──► your repository
```

The same picture in words: you talk to vibey through its command line, the krypton
apps, or another LLM connected over MCP or ACP. The conductor runs the six phases, parks a job
whenever it needs your answer, and
enforces your budget. Workers claim jobs from a PostgreSQL queue under leases that expire
if a worker dies. Every decision, question, answer and handoff is appended to a ledger
in the same database before it takes effect, and the database refuses to change or
delete what is written there. Each job runs on one engine — a local model first, a paid
engine only when no local one can — inside its own git worktree, and finished work lands
in your repository. The [architecture map](docs/project.mmd) shows every layer.

## Why it isn't just another agent framework

The hard part is not calling an LLM in a loop — `claudeloop` and its siblings
already solve that, including the distinction between a waitable rate-limit
window and exhausted credits that no amount of waiting will fix. vibey adds the
things those runners deliberately do not do:

1. **A phase machine with loop-backs**, so a review finding becomes a new design
   conversation rather than a lost note.
2. **Round-robin engine rotation with lossless handoff** — the conversation is an
   append-only event ledger, not a chat transcript locked inside one vendor's
   session, so any engine can pick up where any other left off. A handoff that
   would lose an open question, decision, assumption, or finding is rejected by
   a pure, deterministic no-loss gate — never silently accepted.
3. **A durable queue**, so work survives a laptop lid closing, a crash, or a
   provider outage, and so multiple work items build in parallel in isolated
   git worktrees.
4. **Real money brakes** — per-cycle dollar and turn caps summed from the
   ledger's own cost events, with parks that tell you the exact command to
   grant more.

## Questions people ask

### What is vibey?

vibey is a free, open-source orchestrator for AI coding agents: it interviews you until
the specification is precise, builds unattended on local or paid agents, stops only for
the decisions that are yours, and records every step in an append-only PostgreSQL ledger.
It is written in Python, MIT-licensed, and runs on macOS and Linux.

### What happens if an AI agent crashes mid-task?

Its job is not lost. A worker holds each job under a lease it must keep renewing; when
the worker dies the lease runs out, a reaper returns the job to the queue, and another
worker picks it up. A late commit from the dead worker is refused, so the job is not
committed twice. Because every question and decision is in the ledger rather than in the
dead session, the next engine starts from the same place. The
[crash case study](docs/case-studies/how-vibey-survives-a-crashed-agent.md) walks
through the design, the chaos test behind it, and what it costs.

### Can vibey run without sending code to a cloud model?

Yes. The default engine, `gptossloop`, runs the Heretic v2 build of GPT-OSS 20B on your own
machine through [Ollama](docs/guides/local-models-ollama.md), and with no `--provider`, the
design interview and the work plan run on local models too. To keep every job on your machine,
allow only the local engine:

```bash
vibey worker --provider gptossloop --engines gptossloop
```

With that allow-list the only models vibey calls are the ones running on your machine
([ADR-0038](docs/architecture/decisions/0038-local-engines-are-preferred-first.md),
[ADR-0064](docs/architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)).
That is not the same as no network: DESIGN research searches the web, through a local SearXNG
first and Brave only as a backup when a key is set, and records each search on the ledger
([ADR-0102](docs/architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)).
`vibey doctor` with no `--engine` also checks the bundled Claude CLI, which may try to reach its
vendor; `vibey doctor --engine gptossloop` checks only the local engine.

### How does vibey keep an audit trail?

Every decision, question, answer, handoff, cost and phase change is appended to a ledger
in PostgreSQL before it takes effect. The database refuses to update or delete a ledger
row, and the application connects as a role that could not rewrite one anyway
([ADR-0055](docs/architecture/decisions/0055-the-ledger-is-append-only-by-the-database.md));
a SHA-256 hash chain over the events makes any edit detectable. `vibey ledger show`
reads it, and `vibey ledger export` publishes a redacted projection
([what gets published](docs/guides/ledger-publication.md)).

### What happens when an engine runs out of credits?

The work moves to another engine; it does not wait. vibey writes a handoff brief and
checks it with a deterministic no-loss gate — no model involved — that rejects any brief
missing an open question, decision, assumption or finding. A failing brief is retried,
then replaced by the full transcript, then brought to you; it is never passed on with
gaps ([ADR-0004](docs/architecture/decisions/0004-no-loss-gate-on-handoff.md)).

### Does vibey replace Claude Code or Codex?

No — it drives them. Each engine is a `*loop` runner around a vendor's own tool or a
local model ([ADR-0001](docs/architecture/decisions/0001-orchestrate-do-not-reimplement.md)).
vibey adds what a single session cannot do: a durable queue, a shared ledger, human
gates, budget caps, and rotation between engines. Replacing them is the project's stated
mission, not something vibey does today. The reverse also works: Claude Code, Codex and other
clients can drive vibey ([Drive vibey from another LLM](#drive-vibey-from-another-llm)).

### Where does a person stay in control?

At four gates: the design interview, the review, and the design and review of a
deployment. Each one waits for your recorded answer, and `vibey gates` lists every gate
that is open. Budgets cap the dollars and turns each cycle may spend, and a tripped cap
parks with the exact command that grants more. Nothing is deployed unless you opt in. An LLM
connected to vibey is refused the gates that spend money: those stay yours.

### How do I start contributing?

Follow [your first hour](CONTRIBUTING.md#your-first-hour): clone, install with uv, run a
first test, make one small change, and open a pull request into `develop`. Questions are
welcome on [Discord](https://discord.gg/Qvu8aYnVS) and in
[Discussions](https://github.com/the-vibey-project/vibey/discussions).

## Documentation

| Document | What's in it |
|---|---|
| [Install guide](docs/guides/install.md) | Install, reinstall, copy the codebase and remove the krypton interfaces, platform by platform |
| [Drive vibey from another LLM](docs/guides/drive-from-an-llm.md) | Claude Code and the other MCP and ACP clients as vibey's driver: setup, the tools, and what they are refused |
| [Architecture map](docs/project.mmd) | Comprehensive Mermaid diagram: every layer, the six phases, the ledger/handoff data flow, the security boundary, and the release channels |
| [Research paper](https://the-vibey-project.github.io/vibey/main/paper/) · [PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf) | *Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents* — the ledger invariant and what the database enforces, the no-loss handoff gate, the capacity taxonomy, the exact-head release calculus with its production counterexample, and a single-slot saturation curve measured on one machine, with what the records do not show: the family's one paper |
| [The book](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html) | Every page of the documentation site, in reading order, as one downloadable book |
| [What do you want to do?](docs/guides/outcomes/index.md) | Six outcome guides — local-only agents, spending caps, a tamper-evident record, review before merge, deployment without stored cloud secrets, regulated environments — each with commands, evidence and limits |
| [Local models on Ollama](docs/guides/local-models-ollama.md) | The local engines, the two sovereign model builds, research, and running unattended |
| [CLI reference](docs/reference/cli.md) | Every command, subcommand, flag, and default |
| [Configuration reference](docs/reference/configuration.md) | The full `vibey.toml` schema, with defaults and an example file |
| [Hub API](docs/reference/hub-api.md) | The HTTP API every krypton client and agent reaches |
| [Error codes](docs/reference/errors.md) | Every error code, its cause and what to do; `vibey explain <code>` prints the same |
| [System requirements](docs/reference/system-requirements.md) | Hardware, software, network and per-client requirements, re-measured weekly, with what is measured, derived or stale |
| [How far vibey is from full autonomy](docs/reference/autonomy.md) | The delivery loop's stages, each measured weekly from the forge, the review canary, the code and the local queue, with what would close each gap |
| [Host health](docs/reference/host-health.md) | The machine vibey runs on, measured weekly on the host itself (SSD, battery, memory and swap, thermals, generation rate), with a forecast of when it needs replacing |
| [Host optimization](docs/runbooks/host-optimization.md) | The host's measured memory and SSD-write budget, and its declared, gated and reversible tuning plan in three classes |
| [How vibey survives a crashed agent](docs/case-studies/how-vibey-survives-a-crashed-agent.md) | A case study: the problem, the fixes that fail, the lease-and-ledger design, the chaos test that checks it, and what it costs |
| [Convergence-Driven Development](docs/guides/convergence-driven-development.md) | The CDD loop above SDD and TDD, convergence/divergence checks at four scopes, the atom model, and delivery evidence |
| [The biological philosophy](docs/guides/biological-philosophy.md) | The atom, molecule, organism and ecology lens behind CDD, its evidence table, and Biodigitology, which the research paper does not rely on |
| [Kubernetes guide](docs/guides/kubernetes.md) | Container, Helm chart, KEDA autoscaling, and its own troubleshooting section |
| [Greeter live-demo runbook](docs/guides/greeter-live-demo.md) | A full paid run, end to end, with the zero-touch contracts |
| [What gets published](docs/guides/ledger-publication.md) | What `vibey ledger export` publishes of a ledger, what it withholds, and how it counts both |
| [Expansion runbooks](docs/runbooks/expansion/) | A master plan and 21 workstreams: JIRA, more clouds, Kubernetes server mode, clients, store submissions, … |
| [Architecture & roadmap](docs/plans/architecture-and-roadmap.md) | The master design: context, containers, layers, phases, risks, milestones. Planning notes, kept off the site because parts have drifted from the code |
| [Domain model](docs/plans/domain-model.md) | Every value object, ADT, and invariant in `domain/` (planning notes; check against the code) |
| [Data model](docs/plans/data-model.md) | Full PostgreSQL DDL, queue semantics, indices (planning notes; check against the code) |
| [Handoff protocol](docs/plans/handoff-protocol.md) | The event ledger, the envelope, and the no-loss gate |
| [Rotation & engines](docs/plans/rotation-and-engines.md) | Capability matrix, effort normalization, smooth weighted round robin |
| [Phase protocols](docs/plans/phase-protocols.md) | What all six phases do, turn by turn |
| [Implementation plan](docs/plans/implementation-plan.md) | Milestone-by-milestone, test-first task breakdown |
| [CLAUDE.md](CLAUDE.md) | The short facts file every coding agent working on vibey loads first: non-negotiables, layer map, gate commands |
| [Decision records](docs/architecture/decisions/) | Why each hard call was made (105 ADRs) |

## Status

**Work in progress.** vibey is in active development at version 0.4.0, held below 1.0:
features, interfaces and APIs still change. The finished product will be announced on the
[Discord server](https://discord.gg/Qvu8aYnVS).

<!-- BEGIN GENERATED autonomy:summary — regenerated by scripts/autonomy_scorecard.py -->
**Distance from full autonomy: 0 of 11 stages autonomous (2 partial, 5 manual, 4 unknown)**, measured at 2026-10-22 12:56Z from the forge, the review canary, the code and the local queue. Not yet autonomous: DESIGN resolves without a person (unknown), BUILD runs unattended (unknown), Paid engines stay available (unknown), REVIEW resolves without a person (partial), The pull-request review reaches a verdict (manual), The review's verdict is trustworthy (manual), Approval comes from the delegated approver (manual), Merges land without the operator (manual), Promotion and release run without hand steps (manual), CI stays green without human re-runs (partial), The queue delivers projects to DONE (unknown). Each stage's metric, threshold, evidence and what would close it are on [How far vibey is from full autonomy](docs/reference/autonomy.md); the record is [`docs/architecture/evidence/autonomy-scorecard.jsonl`](https://github.com/the-vibey-project/vibey/blob/develop/docs/architecture/evidence/autonomy-scorecard.jsonl). *Regenerated by `scripts/autonomy_scorecard.py`; do not edit inside these markers.*
<!-- END GENERATED autonomy:summary -->

The scorecard is scheduled weekly, but its record holds five measurements and the newest is
from 2026-10-22, so read the figures above as of that date.

**Live-validated, on an earlier engine pool.** The full pipeline has conducted real paid
deliveries end to end ([the greeter runbook](docs/guides/greeter-live-demo.md)): multi-worker
builds (`-j 2`) with cross-engine rotation (claudeloop implemented and agyloop verified;
agyloop has since been retired by ADR-0078), the bounded verify-repair ladder, budget caps
tripping and being granted live, and fully zero-touch DESIGN phases answered with nothing but
`--defaults`. The validation campaign's findings — a blind budget brake, a repair-loop livelock,
terminal gate-command failures — were each fixed and re-validated live. The same validation has
not been recorded on today's engine pool.

Every architectural layer (`domain`, `application`, `infrastructure`, `cli`)
holds a **100% branch-coverage floor**, enforced as four separate CI gates
(ADR-0023); the absorbed runner and tool packages keep their own gates (ADR-0022).
`domain/` is pure stdlib, enforced by import-linter and an AST-walking purity
test — the no-loss handoff gate is deterministic code, not a model's opinion.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `vibey: command not found` right after installing | uv's tool folder is not on your `PATH` yet; uv warns about this during the install. | Open a new terminal; if that does not help, run `uv tool update-shell` and open one again. |
| `vibey doctor` reports an engine `NOT INSTALLED` | The `*loop` commands ship in the `vibey-engine` package, so this is a `PATH` problem, not a missing package: `vibey` is being run from one environment while `PATH` points at another (a venv whose `bin/` is not exported, a shadowing `uv tool` shim, a system `python` install). | `python -c 'import shutil; print(shutil.which("claudeloop"))'` in the same environment that runs `vibey`; if it prints nothing, put that environment's `bin/` on `PATH` (or reinstall with `uv tool install --reinstall 'vibey-engine[hub]'`), then re-run `vibey doctor`. |
| `gptossloop` shows `auth FAIL` and says the model is not served | Ollama is not running, or the model has not been pulled. | Start Ollama, then `vibey install --model` (before the release after #1978: `ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`). |
| `VIBEY_PG_URL is not set` | No database connection string in this terminal. | Add the `export VIBEY_PG_URL=...` line that `vibey install --database` printed to your shell profile and open a new terminal, or export it by hand, pointing at a database you own. |
| `vibey doctor` fails `ledger-guard` | One DSN for everything: the application role could rewrite the ledger. | Split the roles: [Set it up by hand](#set-it-up-by-hand) ("Your own PostgreSQL"). |
| `vibey hub start`, `vibey serve` or `vibey mcp` fails with a missing-module error for `fastapi` | vibey was installed without its hub extra. | `uv tool install --reinstall 'vibey-engine[hub]'`. |
| Starting a project from Claude Code or a phone is refused | The hub has no `[hub] projects_root`. | Add `[hub]` and `projects_root = "~/vibey-projects"` to your own `vibey.toml`, then `vibey hub stop` and `vibey hub start`. Or create the project with `vibey new` in a terminal. |
| `vibey doctor` reports `auth FAIL` for a paid engine | The engine's own vendor credentials aren't configured. | Run that engine's own login, then re-run `vibey doctor --conformance`. A local-only run does not need it. |
| `vibey worker` logs `no recorded conformance for ...` | `vibey doctor --conformance --record` has never passed for that engine on this project. | Run it before starting the worker; engine-driven jobs won't select an unrecorded engine. |
| A project is parked and nothing progresses | A human gate (interview, research evidence, review verdict, budget cap) is waiting. | `vibey gates` (or `vibey gates <project-id>`) prints each open gate's id, its prompt, and the exact `vibey answer` command that answers it. Run that command, putting your value where it shows `N` or `<json>`. |
| A `research_evidence` gate opens during DESIGN | Research found no search backend and no reading folder. | `vibey searxng install`, or start the worker with `--auto-record-research-gaps`, or answer the gate as its prompt says. |
| Jobs sit `leased` after a worker crash | The lease hasn't expired yet, or nothing has reclaimed it. | `vibey recover --project <id>` (or `--all`) sets them back to `ready`; `vibey retry <id>` also stops old workers and starts a new one. |
| Budget cap trips mid-cycle | The project's `max_cycle_dollars` / `max_cycle_turns` cap (set by `vibey new --max-cycle-dollars` / `--max-cycle-turns`) was exceeded — by design. | `vibey answer <gate-id> --raw '{"max_dollars": 25}'` (or `{"max_turns": N}`) to grant more, or accept the park. |
| An error with a code such as `E0040` | A domain rule blocked the command. | `vibey explain E0040` prints the cause and what to do ([error codes](docs/reference/errors.md)). |
| Kubernetes-specific issues | — | See the [Kubernetes guide's Troubleshooting section](docs/guides/kubernetes.md#troubleshooting). |

## Upgrading

vibey is at **0.4.0** and stays below 1.0 for now (`[version] max_major = 0` in
`.vibey-gh.toml`). Below 1.0 a breaking change takes a minor version, not a major one, so read
the changelog before every upgrade.

1. **The numbers restarted.** On 2026-11-13 the version was reset from the old 4.x line (4.6.0
   was the last) to 0.3.0, and 0.4.0 followed. 0.3.0 and 0.4.0 are newer than 4.6.0, so a tool
   that compares version numbers may not offer them as an upgrade. Run the install command again
   instead: it reinstalls from the newest release.
2. **`vibey -v` changed meaning.** It now prints the versions (`vibey-engine <version>`, then
   `krypton-app <version>` or `krypton-app not installed`). Verbose output moved to `-d`
   (`-dd`, `-ddd`) or `--verbose`. Anything that ran `vibey -v`, `-vv` or `-vvv` for logging must
   change.
3. **Migrate the database.** A two-role install does not migrate itself: run
   `VIBEY_PG_MIGRATE_URL=<owner DSN> vibey migrate` after upgrading (`vibey install --database`
   does the same on a local PostgreSQL). Only a single-DSN install migrates when it starts, and
   that install fails `vibey doctor`'s `ledger-guard` check.
4. **Re-run `vibey doctor --conformance --record`** afterward — engine
   contracts and conformance checks can gain new checks between releases.
5. Read [CHANGELOG.md](CHANGELOG.md) and the `changelog.d/` notes not yet folded into it for
   the versions between yours and the target.

Every push to `develop` publishes a uniquely versioned dev build (`X.Y.Z.devN`)
to TestPyPI; every push to `main` publishes to PyPI. Two packages publish, each by its own
workflow (ADR-0069): `vibey-engine`, the engine family (`vibey-engine.yml`), and
`krypton-app`, the apps and the `krypton` command (`krypton-app.yml`).
After a successful `main` release, `github-release.yml` tags that exact commit
(`vibey-v<version>`) and creates the matching GitHub Release. Versioning and release are owned
by the in-tree `vibey-gh`; release-please is retired (ADR-0028). `uv tool install
'vibey-engine[hub]'` tracks stable releases of the engine family (ADR-0037, ADR-0069);
`uv tool install krypton-app` adds the apps.

## Formal notes

For the reader who wants the theory under the phases. Work items form a queue
$Q$ in PostgreSQL; workers claim with `SELECT ... FOR UPDATE SKIP LOCKED`, so
claims serialize per item without global locks: for any item $w$, at most one
worker holds $w$ at any instant, while throughput scales with
$\min(|Q|, \text{workers})$. The conductor is a six-phase state machine
$\Sigma = \langle D, B, R, D_d, D_e, D_r \rangle$ (design, build, review,
deploy-design, deploy-execute, deploy-review) with human gates exactly at
$\{D, R, D_d, D_r\}$ — interactive phases are the fixed points where the
ledger's open questions must drain to zero before the transition fires.
Crash recovery follows from two invariants: every decision, finding, and
handoff is a row in an append-only ledger *before* it takes effect
(write-ahead intent), and engine handoff re-derives session context from the
ledger alone — so vendor credit exhaustion is a scheduling event, not a loss
of state: $\text{state}(t) = f(\text{ledger}_{\leq t})$, independent of any
vendor session. The full treatment — with the queue-fairness argument and the gate-soundness
proof sketch — is the research paper, *Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents*:
[read it online](https://the-vibey-project.github.io/vibey/main/paper/) or [download the PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)
(source: [`docs/paper.md`](docs/paper.md)). The complete documentation is also a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf) · [EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) · [print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html).

## Project links

| | |
|---|---|
| Contributing | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Security policy | [SECURITY.md](SECURITY.md) |
| Getting help | [SUPPORT.md](SUPPORT.md) |
| Code of Conduct | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Community | [Discord](https://discord.gg/Qvu8aYnVS) · [Join me](https://vibewithadam.matthewsteinberger.com/join-me) |

## Join the community

vibey is free and open-source software, and it is built in the open. If you write
software and want to build the autonomous-delivery stack with us, come and say hello
on [Discord](https://discord.gg/Qvu8aYnVS), and read
[how to join me](https://vibewithadam.matthewsteinberger.com/join-me). Questions,
critiques, pull requests and wild ideas are all welcome.

## Related projects

These packages live in this repository as uv workspace members
(`src/vibey_runners/*`, `src/vibey_tools/*`; ADR-0021). Each keeps its own
`pyproject.toml`, version, Python floor, tests and gates — but none is
published separately any more: all seven ship inside the one `vibey-engine`
distribution (ADR-0037), and their former standalone GitHub repositories and
PyPI projects no longer exist.

| Project | Source | What it is |
|---|---|---|
| claudeloop | [`src/vibey_runners/claude`](src/vibey_runners/claude) | Autonomous Claude Code session runner — the design the family transplants |
| codexloop | [`src/vibey_runners/codex`](src/vibey_runners/codex) | The same design retargeted onto OpenAI Codex |
| qwenloop (the `gptossloop` and `qwenloop` commands) | [`src/vibey_runners/qwen`](src/vibey_runners/qwen) | The same design on a local model, as two engines over Ollama, llama.cpp or vLLM: `gptossloop` on the Heretic v2 build of GPT-OSS 20B — the sovereign default, on by default, and the sovereign DESIGN provider — and the opt-in `qwenloop` on Qwen (`qwen3:14b`); both preferred first when switched on (ADR-0064, ADR-0099) |
| vibey-runners-common | [`src/vibey_runners/common`](src/vibey_runners/common) | The code the runners share |
| vibey-skills | [`src/vibey_tools/skills`](src/vibey_tools/skills) | The Agent Skills marketplace (a Claude Code plugin marketplace) and its context packets |
| vibey-gh | [`src/vibey_tools/gh`](src/vibey_tools/gh) | Provenance fingerprints, derived version bumps, a merge train, and branch realignment; it owns vibey's own release (ADR-0028) |
| vibey-bootstrap | [`src/vibey_tools/bootstrap`](src/vibey_tools/bootstrap) | Azure bootstrap library for App Configuration, Key Vault, and App Insights integration |

## License

[MIT](LICENSE) © [Adam Matthew Steinberger](https://github.com/adammatthewsteinberger)

## Say it in one line

vibey is a free project manager for AI coding agents: it plans with you, builds on your own
machine first, stops for your decisions, and writes every step to a ledger that can only grow.

**Your next step**: install it and let it interview you, with the first command on this page.

**Prefer to read first?** The design is a [research paper](https://the-vibey-project.github.io/vibey/main/paper/)
([PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf)), and the whole documentation is a [book](https://the-vibey-project.github.io/vibey/main/book.pdf)
([EPUB](https://the-vibey-project.github.io/vibey/main/book.epub)).

**Want to build it with us?** [Your first hour](CONTRIBUTING.md#your-first-hour) takes you
from a clone to a pull request.
