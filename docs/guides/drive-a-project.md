---
description: Start a vibey project, answer its questions, give it files, pause, resume and unwind it, from a terminal, a chat LLM, VS Code, the desktop app or Zed.
---

# Drive a project from anywhere

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** Every vibey surface does the same four things to a project:
> **start** it, **answer** its questions, **pause and resume** it, and **unwind** it. They all
> run the same audited `vibey` commands, so a project started in chat looks exactly like one
> started in a terminal. Pick the surface you already use; the terminal path below takes about
> five minutes once vibey is [installed](install.md). A device or an LLM can start a project only
> after you set `[hub] projects_root`.

This page is for anyone with vibey installed who wants to run a project, from whichever window
they happen to be in. To let Claude Code or another chat assistant do the driving, see
[Let another LLM drive vibey](drive-from-an-llm.md).

**Checked** against the vibey-engine 0.4.0 source on `develop` (2026-11-24): the command help of
`vibey new`, `answer`, `gates`, `recover`, `retry`, `abandon`, `inputs`, `projects` and
`hub pair`, the hub's lifecycle code, and the desktop, VS Code and phone app sources. The steps
were not run end to end on a fresh machine here.

## The lesson

Daniel had started a project from his laptop's terminal before lunch, and now he was looking at
it in VS Code and frowning.

**Daniel:** Professor, I started this in the terminal. If I pause it from VS Code, do the two of
them fight?

**Professor Feynman:** Think of a busy restaurant. You can order at the counter, by phone, or on
an app. Three ways in, one kitchen. Every order ends up as the same ticket on the same rail, and
the cook does not care how it arrived.

**Daniel:** So the terminal, VS Code and the desktop app are just different counters.

**Professor Feynman:** Yes. Each one turns your click or your sentence into the same few `vibey`
commands: `vibey new` to start, `vibey answer` to reply, `vibey recover` to pause,
`vibey retry` to resume, `vibey abandon` to unwind. And each is written down in the project's
ledger, with who asked.

**Daniel:** Then why can my phone not start a project, when the terminal can?

**Professor Feynman:** Because a new order needs a table, and a project needs a folder on your
computer. A device never names a folder; you say once, in `vibey.toml`, which folder projects may
be made in. Until you do, the hub turns away a "start" from anyone but the terminal. Answering,
pausing and unwinding a project that already exists need no folder, so they work at once.

**Daniel:** And unwinding is throwing the order away.

**Professor Feynman:** It cancels the order, yes. Here my picture stops working: a cancelled
meal goes in the bin, but an unwound project's files stay exactly where they are on your disk.
vibey stops working on them; it never deletes what was written.

## Do it

The terminal path, from nothing to a project you have paused and resumed. Each command needs
`VIBEY_PG_URL` exported.

1. **Make a folder that is a git repository** for the project.

   ```bash
   mkdir -p ~/src/greeter && cd ~/src/greeter
   git init -b main && git commit --allow-empty -m "chore: start greeter"
   ```

2. **Start the project.**

   ```bash
   vibey new greeter --intake "A command-line program that prints hello and the user's name."
   ```

   You should see `project` followed by the project's id, then a line saying what was queued.
   `vibey projects` lists it, newest first, with its phase and open questions.

3. **Start its worker.**

   ```bash
   vibey retry PROJECT_ID --keep-workers --start-worker
   ```

   Replace `PROJECT_ID` with the id from step 2. This is exactly what the hub runs when an app or
   an LLM presses **Start**: it starts `vibey worker --project PROJECT_ID` in the background.
   (To watch the worker in this terminal instead, run `vibey worker --project PROJECT_ID`.)

4. **Answer its questions.** vibey interviews you before it designs anything.

   ```bash
   vibey gates
   ```

   You should see each open gate, oldest first, with the `vibey answer` command that answers it.
   To accept every suggested answer of the interview:

   ```bash
   vibey answer GATE_ID --defaults
   ```

5. **Pause it.** This stops that project's worker and nothing else; its jobs wait in the queue.

   ```bash
   vibey recover --project PROJECT_ID --stop-workers
   ```

6. **Resume it.**

   ```bash
   vibey retry PROJECT_ID --keep-workers --start-worker
   ```

7. **Watch it** (optional): `vibey status PROJECT_ID` once, or `vibey watch PROJECT_ID` live.

## Daniel's teach-back

**Daniel:** Every surface is a different counter onto the same kitchen. Starting is
`vibey new` and a worker, answering is `vibey answer`, pausing is `vibey recover --stop-workers`
for that one project, resuming is `vibey retry --start-worker`, and unwinding is
`vibey abandon`, which shows what it would cancel first and never deletes my files. A device or
an LLM can do all of that except start a project, until I set `[hub] projects_root`.

**Professor Feynman:** Right. And remember a device also needs the `run` scope to start or pause:
a pairing grants nothing unless you name it.

## The details

### The same four actions on every surface

| | Terminal | Chat LLM over MCP | VS Code (`@krypton`) | krypton desktop | Zed (ACP) |
|---|---|---|---|---|---|
| **Start** | `vibey new NAME`, then `vibey retry ID --keep-workers --start-worker` | Ask; it calls `vibey_start_project` | `@krypton /new NAME [what to build]` | **Chat** `/new`, or **Start a project** (`Ctrl+N`) | `/new NAME WHAT TO BUILD` in the agent panel |
| **Answer a question** | `vibey gates`, then `vibey answer GATE_ID ...` | Ask; `vibey_gates`, then `vibey_answer_gate` | `@krypton /next`, then `/reply 1`, or the inline card | **Chat** inline gate card, or **Gates** | A permission request: pick an option |
| **Pause / resume** | `vibey recover --project ID --stop-workers` / `vibey retry ID --keep-workers --start-worker` | Ask; `vibey_pause_work` / `vibey_start_work` | `/pause`, `/resume` | **Chat** `/pause`, `/start`, or the row's menu | `/pause`, `/start` |
| **Unwind** | `vibey abandon ID --reason "..." --dry-run`, then without `--dry-run` | Ask; `vibey_abandon_project`, dry run first | `/unwind [why]` | **Chat** `/abandon`, or the row's menu | `/abandon [ID] REASON`, then again with `--confirm` |

The surface-specific guides: [Let another LLM drive vibey](drive-from-an-llm.md) for Claude Code,
Codex, Cursor, VS Code's own chat, Claude Desktop and Gemini CLI;
[VS Code extension](vscode-extension.md) for `@krypton`; [Drive vibey from Zed (ACP)](acp.md);
and the desktop app's
[README](https://github.com/the-vibey-project/vibey/blob/develop/clients/desktop/README.md).
In VS Code the chat stays with the project and tells you, in plain words, each phase it enters,
each job that fails, and the moment it needs you or is done; `@krypton /follow` picks the thread
up again after a break. The desktop app and the VS Code extension start the hub for you when they
open.

### Phone and web

The krypton phone app and web bundle carry the same screens (Chat, Gates, the project card with
resume, pause and unwind), but neither can reach a hub today. The phone app's pairing by QR code
or 6-digit code is refused by the app itself ("This hub cannot pair devices yet"), and the web
bundle, served from its own address, cannot read a hub that sends no cross-origin headers. Both
are explained on [Install](install.md#phone-and-tablet). When it does connect, unwinding on a
phone asks for Face ID, Touch ID or your passcode first, as spending does
(`clients/app/src/core/device-policy.ts`).

### Before a device or an LLM can start a project

A device never names a folder on your computer. You say, once, which folder projects may be made
in, and each project gets its own subfolder there, made a git repository with one empty commit.
In your own `vibey.toml` (macOS `~/Library/Application Support/vibey/vibey.toml`, Linux
`~/.config/vibey/vibey.toml`), which `vibey hub start` reads:

```toml
[hub]
projects_root = "~/vibey-projects"
```

Restart the hub afterwards (`vibey hub stop && vibey hub start`): it reads the file when it
starts. A `vibey serve` you run by hand reads the `vibey.toml` of the folder you run it in
instead.

With none set, a device can still answer, pause, resume and unwind projects, but **Start a
project** is refused with a message that names this setting. A device also needs the `run`
scope. A pairing grants nothing by default, so name the scopes when you pair it:
`vibey hub pair --scope view --scope answer --scope run` ([hub API](../reference/hub-api.md),
[ADR-0091](../architecture/decisions/0091-devices-may-start-pause-and-unwind-projects.md)).
A device on another computer also needs `[hub] lan = true` and a hub started with
`vibey serve --host <your address>`; see [Install](install.md#phone-and-tablet). An LLM over MCP
or ACP holds `run` by default.

### Starting, and talking to it

Give the project a name and, if you like, say what to build in a sentence or two
(`--intake`). The name is a label: vibey does not require it to be unique, and the project is
known by its id and its folder. From a device or an LLM the name becomes the folder's name, so it
must be up to 64 letters, digits, dots, dashes and underscores, starting with a letter or a
digit, and a folder with that name must not already exist.

vibey then interviews you: it asks what it needs to know before it designs anything. In the apps
the question appears under **Gates**, with a button to accept the suggested answers if you would
rather not think about it. In a terminal, `vibey answer GATE_ID --defaults` does the same, and
`vibey answer --help` lists the other shapes: `QUESTION_ID=ANSWER` pairs, `--choice`,
`--verdict` and `--raw`.

**Give it material to work from.** `vibey inputs add` gives every BUILD run of a project one
pasted text or one file, and `vibey inputs list` shows them by digest, kind, size and name,
never content ([ADR-0104](../architecture/decisions/0104-run-inputs-hash-addressed.md)):

```bash
vibey inputs add PROJECT_ID --file ~/notes/requirements.md
vibey inputs add PROJECT_ID --paste "Use British spelling in every message."
vibey inputs list PROJECT_ID
```

`--paste-stdin` reads the text from standard input instead.

**See what it is doing.** `vibey projects` lists every project with its id, phase, cycle and open
gates. `vibey status PROJECT_ID` shows its phase, queue and engine health; `vibey watch` follows
it live. `vibey loops` shows which loop and which engines a project can run on, at each effort.

### Pausing, resuming and trying again

**Pause** stops *that project's* worker and nothing else: its jobs go back to the queue and
nothing is lost. A worker started with `--all-projects`, which serves every project, is left
running and named; add `--include-shared` to stop it too. `--dry-run` lists what would be
stopped and changes nothing.

**Resume** is `vibey retry PROJECT_ID --keep-workers --start-worker`: it starts the project's
worker again. `vibey retry` also grants more attempts (default 10) to any job that ran out
(an `attempts_exhausted` gate); any other open gate is a decision, so it is only named. Without
`--keep-workers` it first stops the project's old workers, which is the way to unstick a project
that looks frozen. `vibey doctor` says what else is wrong.

### Unwinding

**Unwind** ends a project for good. Before it does anything, vibey shows what it would cancel
(how many jobs, how many waiting questions), and every surface asks you to confirm. It then
cancels those jobs, withdraws those questions and records your reason on the project's ledger.
**The files already written stay where they are**; unwinding changes what vibey does, not what
is on your disk. A project already abandoned is left as it is; a finished project is refused.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `checkout PATH is held by live project ID (phase ...); two live projects never share a checkout` | One folder holds one live project, and a finished (`done`) project still holds its folder. Devices make a new folder each time, so you meet this from a terminal. | Unwind the old project with `vibey abandon` if it is not finished, or start in another folder. |
| "this host has not allowed projects to be started from a device: set [hub] projects_root ..." | No `projects_root` in your own `vibey.toml`, or the hub started before you added it. | Set it as above and restart the hub. |
| "a folder named NAME already exists on the host; choose another name" | `projects_root` already has that folder. | Pick another name. |
| "No hub answers." | No hub is running on the computer that hosts vibey. | `vibey hub start` (it does nothing if one already runs), or `krypton`, which starts one in the foreground and opens its front door in your browser. |
| `vibey new` exits 75 | The Sabbath: from sundown Friday to sundown Saturday, vibey starts no new work by default. | Wait, or add `--ignore-sabbath` to that one command ([The Sabbath](sabbath.md)). |
| The project sits in one phase | No worker is running, the model is not pulled, or a gate is waiting. | `vibey gates`; `vibey retry PROJECT_ID --keep-workers --start-worker`; `vibey doctor`. |
| `vibey answer` exits 3 | The gate was already answered; the first answer stands. | `vibey gates` shows what is still open. |

## Where next

- [Let another LLM drive vibey](drive-from-an-llm.md): hand the driving to Claude Code, Codex or
  another chat assistant.
- [VS Code extension](vscode-extension.md): everything `@krypton` can do inside the editor.
- [CLI reference](../reference/cli.md): every flag of `vibey new`, `answer`, `retry`, `recover`
  and `abandon`.

## Say it in one line

Start, answer, pause and unwind a vibey project from any window: every surface runs the same
audited commands, and only starting from a device needs `[hub] projects_root`.
