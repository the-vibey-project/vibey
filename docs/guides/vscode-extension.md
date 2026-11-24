---
description: Install the krypton extension in VS Code, VSCodium or Cursor, give a model on your own computer a task, review its change, and drive vibey projects from the editor's chat.
---

# Run vibey from VS Code, VSCodium or Cursor (krypton)

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** The krypton extension (`the-vibey-project.krypton`, 0.4.0)
> lets you give a model on your own computer a task, watch it work on a copy of your project,
> and **Review**, **Apply** or **Discard** the result. Install vibey, Ollama and the extension,
> then run **krypton: Ask the model to do a task**. The longest step is a 12-14 GB model
> download. Note: the extension runs stock `gpt-oss:20b` unless you set `vibey.model`.

## The lesson

Daniel had the extension open in one window and his project in the other, and he did not trust
either of them yet.

**Daniel:** If I tell a model to change my code, what stops it making a mess of my branch?

**Professor Feynman:** An architect never draws on the only copy of the plan. He lays tracing
paper over it and draws on that. If the client likes it, he copies the lines down; if not, he
throws the paper away.

**Daniel:** And the tracing paper is...?

**Professor Feynman:** A git worktree: a second checkout of your repository, on a branch of its
own, kept in a folder called the storm home. The model works only there. **Review** shows you
the lines it drew. **Apply** merges them into your branch, with your own git hooks. **Discard**
throws the paper away.

**Daniel:** So my files do not change until I press Apply.

**Professor Feynman:** Unless you switch on `vibey.runInPlace`. Then there is no tracing paper,
and you undo with git.

The narrator notes that Daniel then opened the Model view, and frowned.

**Daniel:** It says `gpt-oss:20b`. The rest of vibey runs a model called Heretic v2.

**Professor Feynman:** Good eyes. That is a real disagreement in the code today, not in your
head. vibey's engine defaults to the Heretic v2 build (ADR-0099). The extension still defaults
to stock `gpt-oss:20b`. Set `vibey.model` to the Heretic tag and the two agree, and you download
one model instead of two.

## Do it

The steps were checked against the extension's source and `package.json` at version 0.4.0. They
were not run end to end in an editor for this page, so the "You should see" lines describe what
the code shows.

1. Install vibey. The installer fetches uv and Python 3.12 if they are missing.

   ```bash
   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh
   ```

   You should see `vibey doctor`'s report, then `vibey is installed.` Its lines about
   PostgreSQL and engine logins do not block editor tasks: a task needs `gptossloop`, Ollama
   and git. Projects, gates and the hub need PostgreSQL ([install guide](install.md)).

2. Install Ollama: on a Mac, the app from [ollama.com/download](https://ollama.com/download),
   opened once; on Linux:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

3. Install the extension. In VSCodium, or any editor that reads Open VSX:

   ```bash
   codium --install-extension the-vibey-project.krypton
   ```

   In VS Code, download `krypton-vscode-<version>.vsix` from a
   [release](https://github.com/the-vibey-project/vibey/releases) and run (with the file's real
   name):

   ```bash
   code --install-extension ~/Downloads/krypton-vscode-0.4.0.vsix
   ```

   In Cursor, the same with `cursor --install-extension`. You should see the editor report the
   extension as installed, and the krypton atom appear in the activity bar.

4. Choose the model. To run the same model as the rest of vibey, open **Settings**, search for
   `vibey.model`, and set it to:

   ```text
   hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
   ```

   Leave it empty to run stock `gpt-oss:20b`, the extension's own default.

5. Open a folder that is a git repository with at least one commit, then run
   **krypton: Check my setup (doctor)** from the Command Palette. You should see one line per
   check, each `ok`, `warn` or `FAIL`, and every `FAIL` says what to do.

6. If the check says so, run **krypton: Start Ollama**, then **krypton: Download the model**.
   It asks before it downloads anything. You should see the download progress, then the Model
   view say the model is present.

7. Run **krypton: Ask the model to do a task** and describe it, for example
   `add a line to README.md that says how to run the tests`. You should see the task panel
   open beside your editor, with the model's words, each tool call and each turn as they
   happen. A turn can take a few minutes on a laptop.

8. When it finishes, press **Review** to see the diff, then **Apply** or **Discard**.

## Daniel's teach-back

**Daniel:** The extension gives a task to a model on my own computer, through vibey's
`gptossloop` and Ollama. The model works on a copy of my repository, a worktree in the storm
home, on its own branch. I look at the change with Review and keep it with Apply, which runs my
git hooks, or throw it away with Discard. The extension and vibey can run different models, so I
set `vibey.model` to the Heretic tag to keep them the same.

**Professor Feynman:** Exactly right. Add one thing: the same panel also drives whole vibey
projects through the hub, with `/new`, `/next` and `/reply`, and those run on vibey's worker,
not as editor tasks.

## The details

The design is [ADR-0059](../architecture/decisions/0059-the-editor-drives-the-familys-own-loops.md);
the engine is [ADR-0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)
and vibey's default model is
[ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md).
The extension's own
[README](https://github.com/the-vibey-project/vibey/blob/main/clients/vscode/README.md) lists
every command with a worked example and every setting with its default.

### What it is

| Fact | Value |
|---|---|
| Name and id | **krypton**, `the-vibey-project.krypton` (sub-doctrine 9.e); commands and settings keep `vibey.*` names |
| Version | 0.4.0 (`clients/vscode/package.json`) |
| Editors | VS Code 1.90 or newer, VSCodium, Cursor; Node 20 or newer to build it |
| Contributes | 54 commands, 36 settings, 7 views, the `@krypton` chat participant with 48 slash commands, a 6-step walkthrough |
| Platforms | macOS and Linux; Windows is not supported yet ([#1097](https://github.com/the-vibey-project/vibey/issues/1097)) |
| Account or cloud | None on the default loop, sovereignloop |

### What you need

- **VS Code 1.90 or newer** (or VSCodium or Cursor), and **git**.
- **Ollama**, from [ollama.com/download](https://ollama.com/download) on a Mac or
  `curl -fsSL https://ollama.com/install.sh | sh` on Linux.
- **vibey**, which brings `gptossloop`, `qwenloop` and `vibey-skills`. The one-line installer
  above is the tested path; `uv tool install vibey-engine` installs the same package. The loop,
  effort and engine pickers read `vibey loops --json`. When the extension cannot read it (no
  `vibey` found, or a build without `vibey loops`), **Check my setup** says
  `degraded: vibey loops is not available`, and tasks run on sovereignloop with gptossloop
  alone. Reinstalling with the one-line installer fixes both.
- **The model.** At least 24 GB of memory; 32 GB is recommended
  ([system requirements](../reference/system-requirements.md)).

### Which model the editor runs

Two parts of vibey choose a local model, and today they choose differently.

| Surface | Default model | How to change it |
|---|---|---|
| vibey's engine (`vibey worker`, DESIGN, DECOMPOSE, `gptossloop` run by vibey) | `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`, 12.1 GB (`src/vibey/domain/sovereign_model.py`) | `--ollama-model`, `VIBEY_OLLAMA_MODEL`, `VIBEY_SOVEREIGN_MODEL` |
| This extension's tasks | `gpt-oss:20b`, 14 GB (`packages/vibey-core/src/local-runner.ts`) | `vibey.model`, else `VIBEY_OLLAMA_MODEL` in the editor's environment |

The extension hands its model to gptossloop as `GPTOSSLOOP_MODEL`, which overrides the runner's
own Heretic default. It never reads `VIBEY_SOVEREIGN_MODEL`. **krypton: Download the model**
(`/pull`) downloads whatever `vibey.model` resolves to. Setting `vibey.model` to the Heretic tag
makes the editor and the engine agree; the Heretic tag's own verification status is in
[Local models on Ollama](local-models-ollama.md).

qwenloop is not handed `vibey.model`. It runs only once vibey switches it on
(`VIBEY_FEATURE_QWENLOOP=1`), and then its own config chooses its model (`qwen3:14b`) unless you
name one, as in `/model qwenloop/qwen3:14b`.

### Install it

| Editor | Command | Source |
|---|---|---|
| VSCodium, other Open VSX editors | `codium --install-extension the-vibey-project.krypton` | Open VSX |
| VS Code | `code --install-extension krypton-vscode-<version>.vsix` | the `.vsix` every [release](https://github.com/the-vibey-project/vibey/releases) attaches ([Downloads](downloads.md)) |
| VS Code, `code` not on PATH (macOS) | `"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --install-extension krypton-vscode-<version>.vsix` | same |
| Cursor | `cursor --install-extension krypton-vscode-<version>.vsix` | same |
| Any, without a terminal | Extensions view, the `…` menu, **Install from VSIX…** | same |

Visual Studio Code's own Marketplace does not carry it, so `code --install-extension` by id does
not work there. The nightly build is on the
[krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)
release. CI's `vscode-extension-ubuntu` and `vscode-extension-macos` jobs build the same file,
and `npx vsce package --no-dependencies` in `clients/vscode` builds it locally, named
`krypton-<version>.vsix`.

**Upgrading from a build before the rename.** It installed as `the-vibey-project.vibey`.
Uninstall it first (`code --uninstall-extension the-vibey-project.vibey`), since two extensions
offering the same `vibey.*` commands cannot both load. Settings and keybindings carry over; a
hub pairing does not (secrets are kept per extension id), so connect to the hub once more.

### The first run and the tour

On first install the editor opens **Get started with krypton**, six steps, each with its
button: **Check your setup**; **Light, Dark or System**; **Your first result**;
**Start a whole project**; **How hard it works**; **Connect to vibey on this network**. It is
also under **Help: Welcome** and in the Tasks view
([the Beauty Bar](../design/beauty-bar.md), item 4).

### How a task works

- **A copy of your folder.** Each task gets a git worktree in the storm home
  (`~/git/vibey-storm` on a Mac, `~/.local/share/vibey/storm` on Linux; `vibey.stormHome`
  changes it), on a branch `vibey/<words>-<id>`, starting from `HEAD` or `vibey.baseRef`. The
  storm home must be storage a restart keeps; the extension refuses anything else.
- **The task panel.** Enter sends; Shift+Enter starts a new line; `/` shows every command.
  While a task runs, what you type is a follow-up the model reads at its next turn. **Stop**
  lets the model finish its turn. **Force stop** appears only after
  `vibey.forceStopAfterSeconds` (120), asks first, and is journaled.
- **When it ends.** Finished work is committed on the task's branch with your repository's own
  hooks. The outcomes (`completed`, `completed-no-change`, `completed-commit-refused`,
  `completed-out-of-scope`, `failed`, `wound-down`, `budget-exhausted`, `error`) are in the
  extension's README.
- **One run at a time** uses the model (`vibey.maxConcurrentRuns`, default 1), the measured
  ideal for gpt-oss:20b on a 24 GB Mac
  ([ADR-0058](../architecture/decisions/0058-concurrent-local-runs-are-measured-per-device.md)).
  The lock is the family's own `mkdir` lock: set `VIBEY_OLLAMA_LOCK` to share one lock with
  storm tooling and vibey-gh.

### The chat: `@krypton` and the krypton panel

- **The krypton panel.** **krypton: Open krypton chat** (`/chat`) opens the chat-first panel,
  a view titled **krypton** in the secondary sidebar. `/chat <text>` opens it and starts a task
  with that text.
- **VS Code's own chat.** Type `@krypton` and a task to run one there, or `@krypton /<command>`.
  A bare number, such as `@krypton 1`, replies to the question a project is waiting on.
- **Projects through vibey.** `/new <name> [what to build]` starts a vibey project; `/follow`
  streams its progress; `/next` shows what is waiting for you; `/reply <number or answer>`
  answers it; `/pause`, `/resume` and `/unwind [why]` control it; `/projects`, `/status`,
  `/gates`, `/answer`, `/bump` and `/budget` read and change it. These run on vibey's worker,
  through the hub or the `vibey` command line, not as editor tasks.
- **Attachments.** `/attach <path>`, `/paste [text]`, `/image <path>` and `/paste-image` add to
  the next task. Images work only when the engine and model can see them; gpt-oss cannot, so
  for it the extension offers no image menu.
- **Context.** `/plugins [plugin ...]` adds ranked vibey-skills context to the next task
  (`vibey.skillsBudget`, 6,000 tokens by default).

### Loops, effort and budgets

- **sovereignloop** is the default, and **gptossloop** runs it, on the model above.
  gptossloop and qwenloop each read only their own settings (`GPTOSSLOOP_*` or `QWENLOOP_*`)
  and their own config file (`~/Library/Application Support/gptossloop/config.toml` on a Mac,
  `~/.config/gptossloop/config.toml` on Linux, and `qwenloop` in place of `gptossloop` for the
  other). The extension lays each run's context window over that file and hands the runner its
  Ollama address. `vibey.gptossloopPath` and `vibey.qwenloopPath` name the two programs when
  the first on your PATH is not the one you want.
- **paidloop** runs vendors' engines, Claude through claudeloop by default, only once you
  declare it, with a daily or monthly dollar cap or a no-cap declaration you confirm twice. An
  engine canon 8.b repeals while vibey still carries its code is shown and never runs.
- **Effort** `auto` climbs vibey's ladder, one rung per failed attempt, in the same copy.
  **ULTRA** ([ADR-0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md)) has
  no turn limit and stops only at **Stop** or a declared cap; it is shown with a flame in its
  own colour. A no-cap paidloop declaration takes the whole warned path, shows
  **UNLIMITED SPEND** everywhere while it stands, and **krypton: End unlimited spend** (`/cap`)
  ends it in one action.
- **Budgets.** A vibey project's cycle caps go through `vibey budget`. This computer's own lanes
  have per-run, daily or monthly caps in dollars, turns or minutes, kept in the storm home and
  journaled.

### A folder of task files

One task per `.md` file, run in name order, each on its own branch from one base commit. From a
terminal, at the top of your repository, after building the extension's command line once:

```bash
(cd clients/vscode && npm ci && npm run compile)
node clients/vscode/out/cli.js batch path/to/tasks --repo . --base origin/develop
```

`path/to/tasks` is your own folder of task files. A block at the top of a task file sets its
title, commit message, context window, turn limit, effort and scope:

```markdown
---
title: "docs(install): a step-by-step guide: for complete beginners"
max_turns: 60
paths: ["docs/guides/install.md"]
---
Rewrite docs/guides/install.md for someone who has never used a terminal.
```

With `paths:`, the task's commit holds only the changes its globs match. Anything else it
changed is left uncommitted and reported, the outcome is `completed-out-of-scope`, and the
command exits 4. The batch's journal records every step. One Ctrl-C winds the running task
down, and running the same command again resumes. Exit codes: `0` every task it ran completed;
`1` a task failed or something around the model broke; `4` a reviewer must look; `75` it was
stopped. In the editor, **krypton: Run a folder of tasks** (`/batch <folder>`) does the same.

### What reaches the model

A model-driven process gets a short, allow-listed environment: `PATH`, `HOME`, the locale, and
the names its runner declares. Some things never cross, whoever declares them: any name that
starts with `VIBEY_` or `PG`, any name containing `DSN`, `DATABASE_URL`, `PASSWORD` or
`PASSWD`, and any `postgres://` value. Everything the model writes is shown as text. The task
panel's page runs no script but its own.

### The hub on this computer

There is one vibey hub per user ([ADR-0068](../architecture/decisions/0068-the-hub.md)).
`vibey.hubAutostart` is **on by default**: when the editor opens and no hub runs, krypton starts
one (`vibey hub start`, in the background). Closing the editor never stops it.
**krypton: Start the vibey hub on this computer** (`/hub start`), **Stop** (`/hub stop`, a clean
shutdown) and **Show whether the vibey hub runs** (`/hub status`) control it. A device paired
with a hub elsewhere (`vibey.hubUrl`) does not start a local one. The hub needs `VIBEY_PG_URL`
in the environment it starts from.

### Connect to a hub on another computer

**krypton: Connect to vibey on this network** (`/connect studio.local`) looks for a hub on this
computer and then at the address you give, on port 8765 by default.

- On this computer it reads the hub's local token itself and connects.
- Elsewhere it asks for a key and checks it against the hub before keeping it in VS Code's
  secret storage: a **device key** the host issued, or the **host's token** from the hub's
  token file (which grants every scope, so prefer a device key).
- The extension does not claim the 6-digit code `vibey hub pair` shows; that is what the
  krypton apps' Pair screens do. The host must also set `[hub] lan = true` for the hub to
  listen on the network.

Projects, gates and budgets then come from the hub through `@vibey/core`'s `HubTransport`;
editor tasks still run on this computer. No key can change a cap from the network.
**krypton: Disconnect from the hub** (`/disconnect`) forgets the key.

### Other commands worth knowing

| Command | Slash | What it does |
|---|---|---|
| **Connect a chat app or editor (MCP)** | `/mcp [client]` | Runs `vibey connect` for one client, so Claude Code, Codex and the others can drive vibey |
| **Run a vibey command on GitHub** | `/workflows <vibey command line>` | Runs it on the repository's GitHub-hosted runners (`vibey -w`, [ADR-0085](../architecture/decisions/0085-vibey-on-the-workflows.md)); `vibey.workflows` sends every call there |
| **Start Ollama** | `/start-ollama` | Opens the Ollama app or runs `ollama serve`; never a second server |
| **Download the model** | `/pull [model]` | `ollama pull` of `vibey.model`'s model, after asking |
| **Show the loops and engines** | `/loops` | What `vibey loops` reports |
| **Show running lanes** | `/lanes` | Every loop running on this computer |
| **Choose the theme** | `/theme system\|light\|dark` | System follows the editor's colour theme live; Light and Dark keep krypton's palette from the design tokens ([ADR-0066](../architecture/decisions/0066-one-design-system-for-every-surface.md)) |

The extension's README has all 54 commands and 36 settings.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `vibey was not found`, or an older vibey is used | Another `vibey` comes first on PATH | Set `vibey.cliPath` and `vibey.gptossloopPath`; **Check my setup** prints every program's path and version |
| `degraded: vibey loops is not available` | The extension cannot read `vibey loops --json` | Reinstall vibey with the one-line installer |
| `<model> is not downloaded; run: ollama pull <model>` | The model in `vibey.model` (or `gpt-oss:20b`) is not in Ollama | **krypton: Download the model** |
| Ollama is not answering | No Ollama server runs | **krypton: Start Ollama** |
| `refused: this work would be kept on storage the operating system empties` | The storm home is on volatile storage | Choose a lasting folder with `vibey.stormHome` |
| `Quiet for N minutes. That can be normal ...` | A long turn | Wait; nothing is stopped for being slow. **Stop** is yours to press |
| Two ~13 GB models on disk | The editor runs stock, vibey runs Heretic | Set `vibey.model` to the Heretic tag, then `ollama rm gpt-oss:20b` if you no longer want it |
| `Not paired: ...` | The key was refused by the hub | Use a device key the host issued, or the host's token |

## Where next

- [Local models on Ollama](local-models-ollama.md): the server settings and the two model
  builds.
- [Drive vibey from Zed (ACP)](acp.md): the same hub from another editor.
- [Install every krypton app](install.md) and [Downloads](downloads.md): the desktop, web and
  mobile apps. Status updates are posted on the [Discord server](https://discord.gg/Qvu8aYnVS).

## Say it in one line

The krypton extension gives a local model a task on a copy of your repo and lets you Review, Apply or Discard it; set `vibey.model` so it runs the same model as vibey.
