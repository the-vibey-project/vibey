# krypton for VS Code

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** krypton 0.4.0 (`the-vibey-project.krypton`) lets you ask a
> model on your own computer to change your project, on a copy, then **Review**, **Apply** or
> **Discard** it; it also drives vibey projects through `@krypton` in the editor's chat. Install
> vibey and Ollama, install this extension, then run **krypton: Ask the model to do a task**.
> Tasks run stock `gpt-oss:20b` unless you set `vibey.model` (see [The model](#the-model)).

**How to read this page.**

**Daniel:** Where do I start?

**Professor Feynman:** With *What you need*, then *Your first task*. After that this page is a
lookup: find a command in *Every command* or a setting in *Every setting*, each with its
default and an example you can paste. The guide on the documentation site tells the story.

**Daniel:** Are `@krypton` and the panel's `/` different?

**Professor Feynman:** No. They are the same commands, typed in two places.

## Quick install

1. **Install vibey** (one line in a terminal; it fetches uv and Python 3.12 if they are
   missing). `--with-krypton` adds the `krypton` browser launcher; it is optional here.

   ```sh
   curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh | sh -s -- --with-krypton
   ```

   `vibey connect --yes` is a separate, optional step: it registers vibey's MCP server with
   Claude Code, Claude Desktop, Codex, Cursor, VS Code and Gemini CLI, and its ACP agent with
   Zed, so those chat apps can drive vibey. This extension does not need it.
2. **Install the extension**, either way:
   - **Without a terminal:** download `krypton-vscode-<version>.vsix` from
     [GitHub Releases](https://github.com/the-vibey-project/vibey/releases) (or
     [krypton-nightly](https://github.com/the-vibey-project/vibey/releases/tag/krypton-nightly)),
     open the **Extensions** view (**Cmd+Shift+X** on macOS, **Ctrl+Shift+X** on Linux), click
     the `…` menu at its top, choose **Install from VSIX…** and pick the file.
   - **With a terminal:**

     ```sh
     # VSCodium or any Open VSX editor:
     codium --install-extension the-vibey-project.krypton

     # VS Code, after downloading the .vsix:
     code --install-extension ~/Downloads/krypton-vscode-*.vsix

     # macOS, if 'code' is not on your PATH:
     "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --install-extension ~/Downloads/krypton-vscode-*.vsix

     # Cursor:
     cursor --install-extension ~/Downloads/krypton-vscode-*.vsix
     ```
3. **Open it:** click the **krypton atom** in the activity bar, or type `@krypton /chat` in the
   editor's chat.

The other krypton apps (desktop for macOS and Linux, web, Android, iOS) are in
[docs/guides/install.md](../../docs/guides/install.md) and
[docs/guides/downloads.md](../../docs/guides/downloads.md). vibey is pre-1.0; news is posted on
the [Discord server](https://discord.gg/Qvu8aYnVS).

## What it is

**krypton** is vibey's face in your editor: the display name of this extension, and of every
vibey app (sub-doctrine 9.e). Its extension id is `the-vibey-project.krypton`. The engine
underneath is still **vibey**, and the extension's settings (`vibey.*`) and commands
(`vibey.*`) keep their names.

Ask a model that runs **on your own computer** to make a change in your project, and watch
every step it takes. There is no account and no cloud on the default loop: the model runs in
[Ollama](https://ollama.com) on your machine, driven by **vibey**, the conductor this extension
belongs to.

## The model

The extension's tasks run **stock `gpt-oss:20b`** by default: `vibey.model`, else
`$VIBEY_OLLAMA_MODEL`, else `gpt-oss:20b` (`packages/vibey-core/src/local-runner.ts`). It hands
that model to gptossloop as `GPTOSSLOOP_MODEL`, and never reads `VIBEY_SOVEREIGN_MODEL`.

The rest of vibey (the worker, DESIGN, DECOMPOSE, and gptossloop when vibey starts it) defaults
to **Heretic v2 of GPT-OSS 20B**, `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`
([ADR-0099](https://the-vibey-project.github.io/vibey/main/architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model/)).
The two surfaces disagree today. To make editor tasks run the same model, and download one
model instead of two, set `vibey.model` to that tag. Both builds share one architecture; the
stock download is about 14 GB and the Heretic one about 12.1 GB.

Nothing the model does touches your files until you say so. Each task works on a **copy** of
your project, on a branch of its own. When it finishes, you **Review** the change, then
**Apply** it to your branch or **Discard** it.

## What you need

Tick these off once, in this order.

1. **VS Code 1.90 or newer.**
2. **git.** On a Mac, running `git --version` in a terminal offers to install it. On Linux, use
   your package manager, for example `sudo apt install git`.
3. **Ollama**, which runs the model.
   - On a Mac, download the app from [ollama.com/download](https://ollama.com/download) and open
     it once.
   - On Linux, run `curl -fsSL https://ollama.com/install.sh | sh`.
   - Windows is not supported yet ([#1097](https://github.com/the-vibey-project/vibey/issues/1097)).
4. **vibey**, which brings the two programs the extension drives, `gptossloop` (the local agent)
   and `vibey-skills` (context for plugins). The one-line installer above is the tested path;
   `uv tool install vibey-engine` installs the same package (Python 3.12 or newer).
   The same install brings `qwenloop`, the same agent on a Qwen model, which runs only once you
   switch it on in vibey
   ([ADR-0064](https://the-vibey-project.github.io/vibey/main/architecture/decisions/0064-gptossloop-is-the-sovereign-engine/)).
5. **The model.** Stock `gpt-oss:20b` (about 14 GB) unless you set `vibey.model`, for example to
   the Heretic v2 tag the rest of vibey uses (about 12.1 GB; see [The model](#the-model)). The
   extension can download it for you (step 4 below). It needs at least 24 GB of memory, and
   32 GB is recommended; a 16 GB Mac cannot run it
   ([system requirements](https://the-vibey-project.github.io/vibey/main/reference/system-requirements/)).

## Install the extension

From Open VSX, where it is listed as `the-vibey-project.krypton` (editors that read Open VSX,
such as VSCodium, find it in their Extensions view):

```sh
codium --install-extension the-vibey-project.krypton
```

That works in an editor whose extension gallery is Open VSX. Visual Studio Code's own
Marketplace does not carry it, so in VS Code install the `.vsix` that every
[release](https://github.com/the-vibey-project/vibey/releases) attaches,
`krypton-vscode-<version>.vsix` (`krypton-vscode-0.4.0.vsix` for this version):

```sh
code --install-extension krypton-vscode-0.4.0.vsix
```

If your Mac says `code: command not found`, use the full path instead:

```sh
"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --install-extension krypton-vscode-0.4.0.vsix
```

A `.vsix` you build yourself (`npx vsce package --no-dependencies` here) is named
`krypton-<version>.vsix` (`krypton-0.4.0.vsix` for this version); install it the same way.

You can also do it without a terminal: open the **Extensions** view, click the `…` menu at its
top, choose **Install from VSIX…**, and pick the file.

**Upgrading from an earlier build?** Builds before the rename installed as
`the-vibey-project.vibey`. Uninstall that one first
(`code --uninstall-extension the-vibey-project.vibey`): two extensions offering the same
`vibey.*` commands cannot both load. Your `vibey.*` settings and keybindings carry over; a hub
pairing does not, because the editor keeps secrets per extension id, so run **krypton: Connect
to vibey on this network** once more.

## Your first task, step by step

1. **Open your project.** Use **File → Open Folder…** and choose a folder that is a git
   repository with at least one commit. The task will work on a copy of it.
2. **Open krypton.** Click the krypton atom in the activity bar on the left.
3. **Check your setup.** Open the Command Palette (**Cmd+Shift+P** on a Mac, **Ctrl+Shift+P**
   elsewhere), type **krypton: Check my setup (doctor)**, and press Enter. Each line says `ok`, `warn` or
   `FAIL`. Every `FAIL` comes with a line that says what to do.
4. **Start Ollama and fetch the model**, if the check asked you to. Run **krypton: Start Ollama**,
   then **krypton: Download the model**. It asks before it downloads anything.
5. **Ask.** Run **krypton: Ask the model to do a task**, type what you want, for example
   `add a line to README.md that says how to run the tests`, and press Enter.
6. **Watch.** The task panel opens beside your editor and shows the model's words, each tool
   it runs, and each turn. A turn can take a minute or more on a laptop; a long quiet spell is
   normal, and nothing is ever stopped for being slow.
7. **Decide.** When it finishes, the panel shows **Review**, **Apply** and **Discard**.
   - **Review** opens the change as a diff.
   - **Apply** merges it into the branch you have checked out. Your repository's hooks run; if
     one refuses, nothing is forced.
   - **Discard** deletes the copy and its branch. The task's record stays.

## How a task works

- **A copy of your folder.** Each task gets a git worktree of its own in the *storm home*
  (`~/git/vibey-storm` on a Mac, `~/.local/share/vibey/storm` on Linux; the `vibey.stormHome`
  setting changes it), on a branch named `vibey/<words>-<id>`, starting from `HEAD` (or from
  `vibey.baseRef`). The extension refuses a storm home on storage your computer empties at
  restart, because the work would be lost.
- **The model.** On sovereignloop, the default, `gptossloop` runs the task through Ollama on
  the model in `vibey.model` (stock gpt-oss:20b when it is empty; see [The model](#the-model)). If you switch `qwenloop` on in vibey, it can run tasks too, on the Qwen model
  its own config names (`qwen3:14b`); each reads only its own settings (`GPTOSSLOOP_*`,
  `QWENLOOP_*`) and its own config file. One task uses the model at a time
  (`vibey.maxConcurrentRuns`, default 1); the rest wait their turn.
- **When it ends.** Finished work is committed on the task's branch with your repository's own
  hooks. The outcome is one of these:

| Outcome | What it means |
|---|---|
| `completed` | The model finished, and its work is committed on the task's branch. |
| `completed-no-change` | The model finished without changing anything. |
| `completed-commit-refused` | The model finished, but one of your hooks refused the commit. The work is in the copy, not committed, and the panel shows the hook's words. |
| `completed-out-of-scope` | The model finished and changed files outside the task's `paths`. Those are left uncommitted in the copy for you to look at. |
| `failed` | The model stopped without finishing, for example after using all its turns. |
| `wound-down` | You stopped it, or a budget did. |
| `budget-exhausted` | A budget would not allow it, or it used a budget up. |
| `error` | Something around the model failed: a program is missing, or Ollama is not answering. |

- **Running in place.** With `vibey.runInPlace` on, the task edits your open folder directly,
  on your current branch. There is then no Apply or Discard; review and undo with git.

## The first minute

On first install, VS Code opens **Get started with krypton**, a six-step tour (it is also
under **Help: Welcome** and in the Tasks view), with a button on every step:

1. **Check your setup**
2. **Light, Dark or System**
3. **Your first result**
4. **Start a whole project**
5. **How hard it works**
6. **Connect to vibey on this network**

How long the first result takes depends on your computer and the model; once the model is
downloaded and loaded, a short task is a few model turns.

## The task panel

- **Enter** sends; **Shift+Enter** starts a new line. Typing in Japanese, Chinese or Korean
  works: the key that confirms a character never sends.
- **While a task runs**, what you type is a follow-up: the model reads it at the start of its
  next turn. Engines that cannot take one say so, and the box stays closed while they run.
- **Type `/`** to see every command. The arrow keys choose one, and Tab fills it in.
- **Stop** asks the model to finish the turn it is on and end. The button shows **Stopping…**
  until it does. If it has not stopped after `vibey.forceStopAfterSeconds` (two minutes by
  default), a separate **Force stop** button appears. It asks you first, and the task's journal
  records it.
- **Its look** is krypton's design system: the colours, spacing, shapes and motion all come
  from vibey's design tokens (ADR-0066). The atom beside the title turns while work runs, the
  state is a coloured pill, and new lines ease in. With reduced motion on (your system's, or
  `workbench.reduceMotion` in VS Code), nothing moves.
- **Pasting an image** works only when the engine takes images and the model can see them.
  gpt-oss:20b cannot, so for it the extension offers no image menu at all.

## The views

| View | What it shows |
|---|---|
| **krypton** (`vibey.chatView`, in the secondary sidebar) | The chat-first panel ([ADR-0100](https://the-vibey-project.github.io/vibey/main/architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces/)): type a task or a `/` command, follow a project, answer what it waits on. **krypton: Open krypton chat** (`/chat`) opens it. |
| **Model** | Whether Ollama is answering, whether the model is downloaded, its context window, and the loop, effort and engine new tasks use. |
| **Tasks** | Tasks this window started, and the finished ones, with Review, Apply and Discard. |
| **Lanes** | Every loop running on this computer, whoever started it: a task, a batch, a terminal or a storm. It shows each one's turn, the tool it is running, its tokens, and how long it has run. |
| **Projects** | vibey projects, with their phase and cycle. |
| **Gates** | Questions vibey has parked for you. Click one to answer it. |
| **Budgets** | vibey projects' cycle caps, and this computer's own lane budgets, with what each has spent. |

## Light, Dark or System

**krypton: Choose the theme** (or `/theme`) sets `vibey.theme`:

- **System**, the default, follows VS Code's own colour theme, and switches live when it changes.
  The panel sits on the editor's own surfaces, so it looks native in any theme.
- **Light** and **Dark** keep krypton's own palette and surfaces, whatever the editor uses.

The Lanes and Tasks views colour each state from the same tokens: running, waiting, finished,
failed, and ULTRA in its own magenta. A running lane's icon spins; with reduced motion it holds
still.

## Connect to vibey on this network

By default krypton drives the `vibey` command line on this computer, exactly as before. If a
vibey hub runs on your network (`vibey serve` on another machine, ADR-0068), **krypton: Connect
to vibey on this network** (or `/connect studio.local`) uses it instead:

1. It looks for a hub on this computer, then at the address you give, on port 8765 unless you
   name another.
2. You pair once. A hub on this computer is connected with its local token, read for you.
   Elsewhere, being on the same network proves nothing, so krypton asks for a key and checks
   it against the hub before it keeps it: a device key the host issued, or the host's token
   (the content of the hub's token file, which grants every scope; prefer a device key).
   krypton for VS Code does not claim the 6-digit code `vibey hub pair` shows; the krypton
   apps' Pair screens do. For a hub to listen on the network, the host sets `[hub] lan = true`.
3. The key goes in VS Code's secret storage, never in settings; `vibey.hubUrl` holds only the
   address. Projects, gates and budgets then come from the hub, and the status bar says
   **hub**. Tasks you start still run on this computer's model.

What the hub never allows from the network, krypton never asks it for: no key can change a
budget cap or declare paid use. **krypton: Disconnect from the hub** (or `/disconnect`) forgets
the key and goes back to the local command line at once.

## The one hub on this computer

There is one vibey hub per user, and every krypton interface (this editor, the desktop app, a
terminal) starts and stops the same one. When the editor opens and no hub runs, krypton starts it
(`vibey hub start`, in the background; switch it off with `vibey.hubAutostart`). **Closing the
editor never stops it.** **krypton: Start the vibey hub on this computer** (`/hub start`),
**Stop the vibey hub on this computer** (`/hub stop`, a clean shutdown, never forced) and
**Show whether the vibey hub runs** (`/hub status`) are the buttons for it. The status bar's
tooltip says what the start said, or why it could not. A device paired with a hub elsewhere
(`vibey.hubUrl`) does not start a local one on open.

## Run vibey on GitHub's runners

vibey can run any of its commands on the repository's GitHub-hosted runners instead of on this
computer: `vibey -w <command>` (ADR-0085), through `.github/workflows/vibey-remote.yml`.
**krypton: Run a vibey command on GitHub** (or `/workflows status --json`, in the panel or after
@krypton) asks for a command line, without `vibey`, and runs it there:

- With a hub paired, the hub sends it (`POST /api/v1/workflows/runs`) and krypton looks again
  every 10 seconds, for up to an hour. The device's key needs the hub's `workflows` scope and
  the scope of what the command does.
- Otherwise the `vibey` command line here sends it as `vibey --workflows …`, from the open
  folder, whose GitHub repository it runs in. It needs the GitHub CLI (`gh`) installed and
  logged in.

What it printed, its exit code and the link to its run go to the **krypton: GitHub workflows**
output. A progress notification shows where the run is while you wait.

To send every call there, not just one command, switch on `vibey.workflows`: the views then
read projects, gates and budgets through `vibey --workflows`, so each refresh waits for a run.
A paired hub takes precedence over it.

## One menu for everything

Click **✨ krypton** in the status bar for every command, in groups. The same commands are in the
Command Palette under **krypton:**, and in the task panel after a `/`.

In VS Code's chat, type `@krypton` and your task to run one there, or a command, for example
`@krypton /lanes` or `@krypton /budget add scope=day loop=paidloop dollars=5`. A bare number,
such as `@krypton 1`, replies to the question a project is waiting on.

## Loops, efforts and engines

- **sovereignloop** (the default) runs everything on your computer.
- **paidloop** runs vendors' engines (Claude, through claudeloop, by default), which bill your
  own accounts with them. It runs only after you *declare* it: **krypton: Choose the loop**,
  then **paidloop**. You declare it with a daily or monthly dollar cap, or with no cap, which
  asks you twice.
- **Effort** `auto` starts low and, when an attempt fails, tries again one rung higher on
  vibey's ladder, in the same copy. You can also fix one level, from TRIVIAL to MAX.
- **ULTRA** is effort without a ceiling (ADR-0063): no turn limit, and a finished pass is a
  checkpoint before the next improvement pass. It stops only when you press **Stop** or a
  budget you declared is reached. It is shown with a flame, in its own colour, in the picker,
  the status bar, the panel and the views.
- **No cap** on paidloop is possible only the long way: a warning with the engine's measured
  cost per hour, the typed phrase `I accept unlimited spending`, and a second warning whose
  default keeps a cap. While it stands, the status bar and every panel say **UNLIMITED
  SPEND**. **krypton: End unlimited spend** (or `/cap`) ends it in one action, at once.
- **Engines and models** are listed by `vibey loops --json`. The extension knows none of them
  by itself. An engine the canon has repealed (by 8.b) while vibey still carries its code is
  shown, greyed out, and never runs. When `vibey loops --json` cannot be read (no `vibey`
  found, or a build without `vibey loops`), **Check my setup** says
  `degraded: vibey loops is not available`, and the extension runs sovereignloop with
  gptossloop on the model in `vibey.model`. Reinstalling vibey with the one-line installer
  fixes it.

## Budgets

- **A vibey project's budget** is its cycle caps, in dollars and turns. The extension changes
  them with vibey's own `vibey budget`, which records each change as `vibey-vscode`.
- **This computer's lanes** have budgets of their own: dollars, turns or minutes, per run, per
  day or per month, for sovereignloop, paidloop or both. They follow vibey's rule. A budget is
  used up once what was spent reaches its cap; a lane that uses one up finishes the turn it is
  on, then stops. A new task that would pass a cap does not start.
- These budgets live in `<storm home>/.vibey-vscode/`. `budgets.json` holds the budgets.
  `budget-journal.jsonl` records every change, and `spend.jsonl` records what each run spent.
  The journals are never rewritten.

## Many tasks: a folder of task files

Put one task per `.md` file in a folder. They run one after another, in name order, each on its
own branch from the same base commit. A block at the top of a file can set these:

```markdown
---
title: "docs(install): a step-by-step guide: for complete beginners"
commit_message: "docs(install): rewrite the install guide"
context_window: 65536
max_turns: 60
effort: high
paths: ["docs/guides/install.md"]
---
Rewrite docs/guides/install.md for someone who has never used a terminal.
```

- `title` names the task. Without `commit_message`, it is also the commit message; without
  either, the message is `<type>: <file name>`.
- `context_window` and `max_turns` set that task's model window and turn limit.
- `effort` is `auto` or a level.
- `paths` limits what the task may change, as globs (`*`, `?` and `**`). Its commit holds only
  the matching changes. Anything else it changed is left uncommitted and named.

Run the folder with **krypton: Run a folder of tasks**. To resume a batch that stopped, run it
again. Tasks that ended `completed`, `completed-no-change`, `completed-commit-refused`,
`completed-out-of-scope` or `failed` are skipped. A stopped or interrupted task runs again on a
new branch. Every step is written to the batch's journal as it happens.

## From a terminal: vibey-vscode

The extension's core runs without the editor too, with the same behaviour and the same
journals:

```sh
node out/cli.js ask "add a line to README.md that says how to run the tests" --repo ~/code/my-project
node out/cli.js batch docs/tasks --repo ~/code/my-project --base origin/main
node out/cli.js status --journal <journal>
node out/cli.js lanes
node out/cli.js doctor
node out/cli.js budget list
node out/cli.js declare-paid --daily-dollars 5
```

The exit codes: `0` completed; `1` failed, or an error; `4` completed, but one of your hooks
refused the commit or changes were left out of scope; `75` stopped (run it again to resume);
`3` a budget; `78` the storm home is on storage that is emptied at restart; `2` a mistake in
the command. One Ctrl-C stops gracefully. A second one, after the fair wait, ends the tasks by
force.

## What reaches the model

- On sovereignloop, everything stays on your computer.
- A task gets a short list of environment variables, and nothing else: `PATH`, `HOME`, `USER`,
  `LOGNAME`, `SHELL`, `TMPDIR`, `TERM`, `LANG`, `LANGUAGE`, `TZ`, the `LC_*` family, and the few
  names its engine declares. Some things never cross, whoever asks: any name that starts with
  `VIBEY_` or `PG`, any name containing `DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`, and any
  value that is a `postgres://` address. The `vibey.environment.allow` setting adds names, but
  never one of those.
- Everything the model writes is shown as text, never as a web page. The task panel runs no
  script but its own.

## Every command

### Run

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.openChat` | Open krypton chat | `/chat` | `/chat` |
| `vibey.ask` | Ask the model to do a task | `/ask <task>` | `/ask add a line to README.md that says how to run the tests` |
| `vibey.followUp` | Tell the running task something | `/tell <message>` | `/tell keep the heading short` |
| `vibey.runBatch` | Run a folder of tasks | `/batch <folder>` | `/batch docs/tasks` |
| `vibey.stopRun` | Stop a running task | `/stop [task id]` | `/stop` |
| `vibey.forceStopRun` | Force-stop a task that did not stop | `/force-stop [task id]` | `/force-stop` |
| `vibey.openRunLog` | Open a task's log | `/log [task id]` | `/log` |
| `vibey.reviewRun` | Review a finished task's changes | `/review [task id]` | `/review` |
| `vibey.applyRun` | Apply a finished task to my branch | `/apply [task id]` | `/apply` |
| `vibey.discardRun` | Discard a finished task | `/discard [task id]` | `/discard` |
| `vibey.attachFile` | Attach a file to the next task | `/attach <path>` | `/attach ~/Desktop/notes.md` |
| `vibey.attachImage` | Attach an image to the next task | `/image <path>` | `/image ~/Desktop/screenshot.png` |
| `vibey.pasteText` | Paste text into the next task | `/paste [text]` | `/paste Error: cannot find module "x"` |
| `vibey.pasteImage` | Paste an image into the next task | `/paste-image` | `/paste-image` |
| `vibey.plugins` | Add vibey-skills context to the next task | `/plugins [plugin ...]` | `/plugins frontend-design security-principles` |

### Loop & model

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.chooseLoop` | Choose the loop (sovereign or paid) | `/loop sovereign|paid` | `/loop sovereign` |
| `vibey.chooseEffort` | Choose the effort | `/effort auto|TRIVIAL|LOW|STANDARD|HIGH|MAX` | `/effort auto` |
| `vibey.chooseModel` | Choose the engine and model | `/model auto|<engine>|<engine>/<model>` | `/model gptossloop/gpt-oss:20b` |
| `vibey.showLoops` | Show the loops and engines | `/loops` | `/loops` |

### Lanes

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.showLanes` | Show running lanes | `/lanes` | `/lanes` |
| `vibey.openLane` | Watch a lane | `/watch <lane id>` | `/watch 1a2b3c4d` |
| `vibey.startQueue` | Start the queue | `/start [task id]` | `/start` |
| `vibey.stopAll` | Stop all lanes | `/stop-all` | `/stop-all` |

### Projects & gates

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.refresh` | Refresh | `/refresh` | `/refresh` |
| `vibey.newProject` | Start a new project | `/new <name> [what to build]` | `/new greeter a web page that greets the visitor by name` |
| `vibey.followProject` | Follow a project | `/follow [project id]` | `/follow` |
| `vibey.nextGate` | What is waiting for me? | `/next` | `/next` |
| `vibey.replyGate` | Reply to the waiting question | `/reply <number or answer>` | `/reply 1` |
| `vibey.pauseProject` | Pause a project | `/pause [project id]` | `/pause` |
| `vibey.resumeProject` | Resume a project | `/resume [project id]` | `/resume` |
| `vibey.abandonProject` | Unwind (abandon) a project | `/unwind [why]` | `/unwind the requirements changed` |
| `vibey.showProjects` | Show vibey projects | `/projects` | `/projects` |
| `vibey.showStatus` | Show a project's status | `/status [project id]` | `/status` |
| `vibey.showGates` | Show parked gates | `/gates` | `/gates` |
| `vibey.answerGate` | Answer a parked gate | `/answer <gate id> [--verdict V | --choice C | --defaults | --raw JSON | Q=A ...]` | `/answer 3f2a9c1e-0b7d-4c55-9a51-2b1f0e8d7c6a --verdict accept` |
| `vibey.bumpJob` | Run a queued job next | `/bump <job id>` | `/bump 5c1d2e3f-4a5b-6c7d-8e9f-0a1b2c3d4e5f` |

### Budgets

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.showBudgets` | Show budgets | `/budget [list]` | `/budget list` |
| `vibey.addBudget` | Add a budget | `/budget add scope=run|day|month loop=any|sovereignloop|paidloop [engine=ID] dollars=N turns=N minutes=N` | `/budget add scope=day loop=paidloop dollars=5` |
| `vibey.editBudget` | Edit a budget | `/budget edit <budget id> dollars=N turns=N minutes=N` | `/budget edit 1a2b3c4d dollars=10` |
| `vibey.removeBudget` | Remove a budget | `/budget remove <budget id>` | `/budget remove 1a2b3c4d` |
| `vibey.grantBudget` | Grant more budget | `/budget grant <gate or budget id> $N | N turns` | `/budget grant 3f2a9c1e-0b7d-4c55-9a51-2b1f0e8d7c6a $10` |
| `vibey.endNoCap` | End unlimited spend (put a cap back) | `/cap` | `/cap` |

### Connect & look

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.connectHub` | Connect to vibey on this network | `/connect [address]` | `/connect studio.local` |
| `vibey.connectMcp` | Connect a chat app or editor (MCP) | `/mcp [client]` | `/mcp vscode` |

`/mcp` runs `vibey connect` for the client you pick. `vibey connect --yes` in a terminal does
every client at once: Claude Code, Claude Desktop, Codex, Cursor, VS Code and Gemini CLI over
MCP (`vibey mcp`), and Zed over ACP (`vibey acp`,
[ADR-0101](https://the-vibey-project.github.io/vibey/main/architecture/decisions/0101-the-acp-agent-and-self-installing-services/)).
Claude Code and VS Code entries are written in the current folder.

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.disconnectHub` | Disconnect from the hub | `/disconnect` | `/disconnect` |
| `vibey.startHub` | Start the vibey hub on this computer | `/hub start` | `/hub start` |
| `vibey.stopHub` | Stop the vibey hub on this computer | `/hub stop` | `/hub stop` |
| `vibey.hubStatus` | Show whether the vibey hub runs | `/hub status` | `/hub status` |
| `vibey.runOnWorkflows` | Run a vibey command on GitHub | `/workflows <vibey command line>` | `/workflows status --json` |
| `vibey.chooseTheme` | Choose the theme (Light, Dark or System) | `/theme system|light|dark` | `/theme system` |

### Ollama

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.startOllama` | Start Ollama | `/start-ollama` | `/start-ollama` |
| `vibey.pullModel` | Download the model | `/pull [model]` | `/pull gpt-oss:20b` |

### Doctor

| Command | Palette title | In the panel or after @krypton | Example |
|---|---|---|---|
| `vibey.doctor` | Check my setup (doctor) | `/doctor` | `/doctor` |
| `vibey.showMenu` | Show every command | `/help` | `/help` |

## Every setting

Change them in **Settings** (search for `vibey`), or in `settings.json`.

| Setting | Default | What it does |
|---|---|---|
| `vibey.cliPath` | `""` | The `vibey` program to run. Empty: the first `vibey` on your PATH. **krypton: Check my setup** prints the one it found and its version. |
| `vibey.gptossloopPath` | `""` | The `gptossloop` program, the local engine that runs a task on the model in `vibey.model`. Empty: the first `gptossloop` on your PATH. It ships with vibey (the `vibey-engine` package). |
| `vibey.qwenloopPath` | `""` | The `qwenloop` program: the same local runner on a Qwen model, which runs only once vibey switches it on (`VIBEY_FEATURE_QWENLOOP=1`, ADR-0064). Empty: the first `qwenloop` on your PATH. |
| `vibey.ollamaPath` | `""` | The `ollama` program, used only to start a server with `ollama serve` and to show a download command. Empty: the first `ollama` on your PATH. |
| `vibey.gitPath` | `""` | The `git` program. Empty: the first `git` on your PATH. |
| `vibey.vibeySkillsPath` | `""` | The `vibey-skills` program that builds context packets for the **Plugins** menu. Empty: the first `vibey-skills` on your PATH. |
| `vibey.ollamaUrl` | `""` | Where Ollama listens, in root form without `/v1`. Empty: `$VIBEY_OLLAMA_URL`, else `http://127.0.0.1:11434`. |
| `vibey.ollamaAppPath` | `"/Applications/Ollama.app"` | macOS only: the Ollama app **Start Ollama** opens when it exists. Otherwise `ollama serve` is started. |
| `vibey.model` | `""` | The model gptossloop tasks run on. Empty: `$VIBEY_OLLAMA_MODEL`, else `gpt-oss:20b`. The rest of vibey defaults to `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`; set that here to match it ([The model](#the-model)). qwenloop is not handed this: its own config chooses (`qwen3:14b`), unless you name a model with the engine, `qwenloop/qwen3:14b`. |
| `vibey.loop` | `"sovereignloop"` | Which loop runs tasks. `paidloop` works only after you declare it once (**Choose the loop**), with a daily or monthly dollar budget. |
| `vibey.effort` | `"auto"` | How hard the engine works (vibey's own effort levels). `auto` starts at **Base effort** and climbs one step each time a task fails, as vibey's escalation ladder does, never past a budget. `ULTRA` has no turn limit and is shown in its own colour with a flame. |
| `vibey.baseEffort` | `"LOW"` | Where `auto` effort starts: vibey's BUILD phase starts at `LOW`. |
| `vibey.engine` | `"auto"` | `auto` picks within the loop by effort (preferring a model already loaded). Or name an engine, `gptossloop`, or an engine and model, `gptossloop/gpt-oss:20b`. The engines come from `vibey loops`. |
| `vibey.maxTurns` | `0` | The most model turns one task may take, used only when neither the task file (`max_turns`) nor the effort sets one. `0`: none from here. |
| `vibey.contextWindow` | `32768` | The context window, in tokens, the local runner (gptossloop or qwenloop) assumes (its own `context_window`, default 32768). **Check my setup** warns when Ollama loaded the model with a smaller one, because Ollama then drops the start of long tasks without saying so. |
| `vibey.runInPlace` | `false` | Run tasks directly in the open folder instead of in a separate copy (a git worktree on its own branch). **Off is safer**: with it on, the model edits your files as it goes and there is no Apply or Discard. |
| `vibey.baseRef` | `""` | The git branch or commit a task's copy starts from. Empty: whatever you have checked out (`HEAD`). |
| `vibey.stormHome` | `""` | Where task copies, plans and records are kept. Empty: `$VIBEY_STORM_HOME`, else `~/git/vibey-storm` on macOS and `$XDG_DATA_HOME/vibey/storm` (or `~/.local/share/vibey/storm`) on Linux. A folder your computer empties at restart is refused (sub-doctrine 10.h). |
| `vibey.modelLockPath` | `""` | A lock directory that keeps runs on the same computer from sharing the model at once, including runs started from a terminal with `vibey-vscode`. Empty: the lock the computer declares with `VIBEY_OLLAMA_LOCK` (the one vibey-gh and storm tooling share), else `.ollama-lock` in the storm home. A lock held by something that does not say who is never broken. |
| `vibey.maxConcurrentRuns` | `1` | How many tasks may use one model at the same time. Further tasks wait in line. `1` is the measured best on a 24 GB Mac: at two, answers drifted from what one run gives (structural fidelity 0.82, under the 0.95 floor; #1114, sub-doctrine 8.c, ADR-0058). Measured on stock gpt-oss:20b; the figures are recorded in the issue, not in this repository. |
| `vibey.refreshSeconds` | `30` | How often the Model, Projects and Gates views refresh themselves. |
| `vibey.pollMilliseconds` | `500` | How often a running task's event log is read for new lines. |
| `vibey.stuckHintMinutes` | `5` | After this many minutes without a new event, a running task shows a hint. Nothing is ever stopped for being slow: on a 24 GB Mac one turn of stock gpt-oss:20b took 16.5 s typically and 112.6 s at the 95th percentile (a measurement cited from the project's issues, not stored in this repository). |
| `vibey.forceStopAfterSeconds` | `120` | How long a graceful **Stop** is given before **Force stop** is offered. A force stop is only ever a person's choice, and it is written in the journal. |
| `vibey.lanesRecentMinutes` | `60` | The Lanes view lists lanes with an event in this many minutes. |
| `vibey.followPollSeconds` | `5` | How often krypton looks at a project it is following, to tell you what changed (`/new`, `/reply`, `/resume` and `/follow`). |
| `vibey.followMinutes` | `30` | How long one follow keeps watching before it hands back. The project keeps running; `/follow` picks it up again. |
| `vibey.skillsBudget` | `6000` | The token budget of a vibey-skills context packet (vibey's own bounds: 1,000 to 32,000). |
| `vibey.budgetInputTokensPerTurn` | `20000` | Input tokens per turn assumed when projecting a paid run's cost, until this machine has measured the engine's own. |
| `vibey.budgetOutputTokensPerTurn` | `2000` | Output tokens per turn assumed when projecting a paid run's cost, until this machine has measured the engine's own. |
| `vibey.desktopNotifications` | `false` | Let the local runner (gptossloop or qwenloop) send its own desktop notification at every turn. Off: the editor shows progress instead. |
| `vibey.environment.allow` | `[]` | Extra environment variables (a name, or a prefix ending in `*`) passed to the engine and the commands the model runs. vibey's own variables (`VIBEY_*`), PostgreSQL's (`PG*`) and anything named like a database credential are never passed, whatever this says. |
| `vibey.theme` | `"system"` | How krypton's panels are coloured. **System** follows the editor's colour theme, live; **Light** and **Dark** keep krypton's own palette from the design tokens (ADR-0066). Remembered on this device. |
| `vibey.hubUrl` | `""` | The vibey hub (`vibey serve`, ADR-0068) this device is paired with, like `http://studio.local:8765`. Empty: the local `vibey` command line, the default. Set it with **krypton: Connect to vibey on this network**, which also keeps the hub's key in the editor's secret storage, never in settings. |
| `vibey.hubAutostart` | `true` | Start the one vibey hub on this computer (`vibey hub start`) when the editor opens and none runs. Closing the editor never stops it: **krypton: Stop the vibey hub on this computer** does. Skipped when this device is paired with a hub (`vibey.hubUrl`). |
| `vibey.workflows` | `false` | Run every vibey call on the repository's GitHub workflows, as `vibey --workflows …` (ADR-0085), instead of on this computer. It needs the GitHub CLI (`gh`) installed and logged in, and the open folder's repository to carry `.github/workflows/vibey-remote.yml`. Each call waits for its run, so views are slow to fill. A paired hub (`vibey.hubUrl`) takes precedence. **krypton: Run a vibey command on GitHub** sends a single command either way. |

## When something is wrong

- **"vibey was not found", or an older vibey is used.** Another vibey on your PATH may come
  first. Point `vibey.cliPath` and `vibey.gptossloopPath` (or `vibey.qwenloopPath`) at the
  ones you want. **krypton: Check my setup** prints the path and version of every program it uses.
- **"Ollama is not answering".** Run **krypton: Start Ollama**. It never starts a second server.
- **"`<model>` is not downloaded; run: ollama pull `<model>`".** The model `vibey.model` names
  (stock gpt-oss:20b when empty) is not in Ollama. Run **krypton: Download the model**.
- **Two ~13 GB models on disk.** The editor runs stock gpt-oss:20b and the rest of vibey runs
  Heretic v2. Set `vibey.model` to the Heretic tag ([The model](#the-model)).
- **"degraded: vibey loops is not available".** The extension cannot read `vibey loops --json`.
  Reinstall vibey with the one-line installer.
- **The context window is "unknown".** It is known only once the model is loaded, at the first
  task. If the check later says it is too small, it names the setting to raise.
- **"refused: this work would be kept on storage the operating system empties".** Choose a
  folder that survives a restart with `vibey.stormHome`.
- **A task seems stuck.** A turn can take minutes. After `vibey.stuckHintMinutes` of quiet, the
  panel says so. Nothing is ever stopped for being slow; Stop is always yours to press.

## Uninstall

In the **Extensions** view, find **krypton** and choose **Uninstall**. Your tasks' branches and
copies stay in your repository and storm home: remove them with Discard, or with git.

## License

MIT. See [LICENSE](LICENSE).
