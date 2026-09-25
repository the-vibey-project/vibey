# VS Code extension

The Vibey extension lets you drive vibey, and a model on your own computer, from VS Code:
describe a task, watch the model work on a copy of your project, and apply the result when
you are happy with it. It needs no account and no cloud. Everything on the default loop,
sovereignloop, runs on your machine: gptossloop, vibey's local agent, drives **gpt-oss:20b**
through [Ollama](https://ollama.com). The design behind it is
[ADR-0059](../architecture/decisions/0059-the-editor-drives-the-familys-own-loops.md); the
engine it runs is set out in
[ADR-0060](../architecture/decisions/0060-gptossloop-is-the-sovereign-engine.md).

The extension's own
[README](https://github.com/the-vibey-project/vibey/blob/main/clients/vscode/README.md) lists
every command with a worked example, and every setting with its default.

## 1. What you need

- **VS Code 1.90 or newer**, and **git**.
- **Ollama**: the app on a Mac, from [ollama.com/download](https://ollama.com/download); on
  Linux, `curl -fsSL https://ollama.com/install.sh | sh`. Windows is not supported yet
  ([#1097](https://github.com/the-vibey-project/vibey/issues/1097)).
- **vibey**, which brings `gptossloop`, `qwenloop` and `vibey-skills`: `pip install vibey`
  (Python 3.12+). The loop, effort and engine pickers read `vibey loops --json`, which ships in
  vibey 3.0.0. Without it the extension says so, and runs sovereignloop with gptossloop alone.
  gptossloop ships in the same release as `vibey loops`, so with an older vibey the fix for
  both is `pip install --upgrade vibey`.
- **The model**, gpt-oss:20b, about 14 GB. The extension can download it for you, and asks
  first. [Local models on Ollama](local-models-ollama.md) covers the server's settings.

## 2. Install it

```bash
code --install-extension vibey-0.1.0.vsix
```

On a Mac where `code` is not on your PATH:

```bash
"/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code" --install-extension vibey-0.1.0.vsix
```

Or use **Install from VSIX…** in the Extensions view's `…` menu. The `.vsix` is built by CI's
`vscode-extension` job and by `npx vsce package --no-dependencies` in `clients/vscode`.

## 3. Your first task

1. Open a folder that is a git repository with at least one commit.
2. Click the **V** in the activity bar, then run **Vibey: Check my setup** from the Command
   Palette. Every `FAIL` says what to do.
3. Run **Vibey: Ask the model to do a task** and describe it, for example
   `add a line to README.md that says how to run the tests`.
4. The task panel shows the model's words, each tool call and each turn as they happen. Enter
   sends; Shift+Enter starts a new line; `/` shows every command. **Stop** lets the model finish
   its turn. **Force stop** appears only after a fair wait, asks first, and is journaled.
5. When it finishes: **Review** shows the diff, **Apply** merges the task's branch into yours
   with your repository's hooks, and **Discard** deletes the copy and its branch.

A task works on a git worktree of its own under the storm home (`~/git/vibey-storm` on a Mac),
on a branch `vibey/<words>-<id>`. The storm home must be storage a restart keeps; the extension
refuses anything else.

## 4. A folder of task files

This is how the documentation rewrite runs: one task per `.md` file, in name order, each on its
own branch from one base commit, from a terminal.

```bash
cd clients/vscode && npm ci && npm run compile
node out/cli.js batch docs/tasks --repo . --base origin/develop
```

A block at the top of a task file sets its title, commit message, context window, turn limit,
effort and scope:

```markdown
---
title: "docs(install): a step-by-step guide: for complete beginners"
max_turns: 60
paths: ["docs/guides/install.md"]
---
Rewrite docs/guides/install.md for someone who has never used a terminal.
```

With `paths:`, the task's commit holds only the changes its globs match. Anything else it
changed, such as a `pyproject.toml` rewritten by a package manager, is left uncommitted and
reported. The task's outcome is then `completed-out-of-scope`, and the command exits 4.

The batch's journal records every step as it happens. One Ctrl-C winds the running task down,
and running the same command again resumes: finished tasks are skipped, and a stopped or
interrupted one runs again on a new branch. The exit code says how it ended: `0` every task it
ran completed; `1` a task failed or something around the model broke; `4` a reviewer must look;
`75` it was stopped.

## 5. What reaches the model

A model-driven process gets a short, allow-listed environment: `PATH`, `HOME`, the locale, and
the names its runner declares. Some things never cross, whoever declares them: any name that
starts with `VIBEY_` or `PG`, any name containing `DSN`, `DATABASE_URL`, `PASSWORD` or
`PASSWD`, and any `postgres://` value. Everything the model writes is shown as text. The task
panel's page runs no script but its own.

## 6. Models, loops and budgets

- **sovereignloop** is the default, and **gptossloop** runs it, on gpt-oss:20b (or the model
  in `vibey.model`). **qwenloop** is the same runner on a Qwen model: it runs only once vibey
  switches it on (`VIBEY_FEATURE_QWENLOOP=1`), and then its own config chooses its model
  (`qwen3:14b`) unless you name one, as in `/model qwenloop/qwen3:14b`. Each reads only its own
  settings, `GPTOSSLOOP_*` or `QWENLOOP_*`, and its own config file
  (`~/Library/Application Support/gptossloop/config.toml` on a Mac,
  `~/.config/gptossloop/config.toml` on Linux, and `qwenloop` in place of `gptossloop` for the
  other). The extension lays each run's context window over that file, and hands the runner
  its Ollama address. `vibey.gptossloopPath` and `vibey.qwenloopPath` name the two programs
  when the first on your PATH is not the one you want.
- **paidloop** runs vendors' engines, Claude through claudeloop by default, only once you
  declare it, with a daily or monthly dollar cap or a no-cap declaration you confirm twice. A
  repealed engine (OpenCode, by canon 8.b) is shown and never runs.
- **Effort** `auto` climbs vibey's ladder, one rung per failed attempt, in the same copy.
- **Budgets**: a vibey project's cycle caps go through `vibey budget`. This computer's own
  lanes have per-run, daily or monthly caps in dollars, turns or minutes, kept in the storm
  home and journaled.
- **One run at a time** uses the model (`vibey.maxConcurrentRuns`), the measured ideal for
  gpt-oss:20b on a 24 GB Mac ([ADR-0058](../architecture/decisions/0058-concurrent-local-runs-are-measured-per-device.md)).
  The lock is the family's own `mkdir` lock: set `VIBEY_OLLAMA_LOCK` to share one lock with
  storm tooling and vibey-gh.
