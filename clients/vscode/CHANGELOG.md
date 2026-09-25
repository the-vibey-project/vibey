# Changelog

All notable changes to the Vibey extension for VS Code.

## 0.1.0

The first release: vibey and a model on your own computer, from the editor.

- **Ask the model.** Describe a task in the task panel, the Command Palette or `@vibey`. It runs
  on a copy of your folder (a git worktree on a branch of its own), so nothing in your checkout
  changes until you choose **Apply**. **Review** shows the diff; **Discard** deletes the copy.
- **The task panel.** Watch the model work as it happens: its words, each tool it runs, each
  turn and its tokens. Enter sends and Shift+Enter starts a new line (input methods are
  respected). Type while it runs to tell it something; it reads it at its next turn. **Stop**
  lets it finish its turn; **Force stop** opens only after a fair wait, and is recorded.
- **Loops, efforts and engines** come from `vibey loops --json`, never from the extension
  itself. sovereignloop (qwenloop on gpt-oss:20b through Ollama) is the default; paidloop runs
  only once you declare it with a spending cap.
- **Lanes.** Every loop running on this computer, whoever started it, with its turn, the tool
  it is running, its tokens and how long it has run.
- **vibey projects, gates and budgets**, through vibey's own commands: answer a parked gate, run
  a queued job next, and set a project's cycle caps. This computer's lanes have budgets of
  their own, per run, per day or per month.
- **A folder of task files** runs one after another, each on its own branch from one base, and
  resumes where it stopped: the same batch runs from a terminal with `vibey-vscode batch`.
- **Check my setup** names every program the extension uses, where it found it and its
  version, and says in plain words what to do about anything missing.
- Nothing that names a database, a password or vibey's own settings ever reaches the model.
