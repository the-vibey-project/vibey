---
description: Start a vibey project, talk to it while it designs and builds, pause it, and unwind it, from a terminal, VS Code, the desktop app or your phone.
---

# Drive a project from anywhere

You can start a project, answer the questions it asks, pause it and end it from any of vibey's
surfaces. They all do the same four things, through the same audited commands, so a project
you start on your phone looks exactly like one you started in a terminal.

| | Terminal | VS Code chat | Desktop app | Phone and web app |
|---|---|---|---|---|
| **Start** | `vibey new NAME` | `@krypton /new` | **Start a project** (`Ctrl+N`) | **Start a project** |
| **Answer a question** | `vibey answer` | `@krypton /next`, then `/reply 1` | **Gates** | **Gates** |
| **Pause and resume** | `vibey retry`, `vibey recover` | `/pause`, `/resume` | the row's menu | the project's card |
| **Unwind** | `vibey abandon` | `/unwind` | the row's menu | the project's card |

## Before a phone or desktop can start a project

A device never names a folder on your computer. You say, once, which folder projects may be
made in, and each project gets its own subfolder there. In `vibey.toml` on the computer that
runs the hub (`vibey serve`):

```toml
[hub]
projects_root = "~/vibey-projects"
```

With none set, a device can still answer, pause, resume and unwind projects, but **Start a
project** is refused with a message that names this setting. The device also needs the `run`
scope. A pairing grants nothing by default, so name the scopes when you pair it:
`vibey hub pair --scope view --scope answer --scope run` ([hub API](../reference/hub-api.md)).

## Starting, and talking to it

Give the project a name (letters, digits, dots, dashes and underscores, up to 64) and, if you
like, say what to build in a sentence or two. vibey then interviews you: it asks what it needs
to know before it designs anything. In VS Code the chat stays with the project and tells you,
in plain words, each phase it enters, each job that fails and the moment it needs you or is
done; `@krypton /follow` picks the thread up again after a break. In the apps, the question
appears under **Gates**, with a button to accept the suggested answers if you would rather not
think about it.

## Pausing, resuming and trying again

**Pause** stops *that project's* worker and nothing else: its jobs go back to the queue and
nothing is lost. **Resume** starts the worker again and grants another attempt to a job that
ran out. Other projects, and workers they share, are left running. If a project looks stuck,
`vibey recover --project PROJECT --stop-workers` is the same pause with a dry-run option
(`--dry-run`), and `vibey doctor` says what else is wrong.

## Unwinding

**Unwind** ends a project for good. Before it does anything, vibey shows what it would
cancel (how many jobs, how many waiting questions) and asks you to confirm. It then cancels
those jobs, withdraws those questions and records your reason on the project's ledger. **The
files already written stay where they are**; unwinding changes what vibey does, not what is
on your disk. On a phone it asks for your fingerprint or face first, as spending does.

## When it says no

- **A project already lives in that folder.** One folder holds one live project. Phones and
  desktops make a new folder for each project, so you meet this from a terminal: unwind the
  old project, or start in another folder.
- **"This host has not allowed projects to be started from a device."** Set
  `[hub] projects_root` as above, on the computer that runs the hub.
- **"No hub answers."** Start one with `vibey hub start` (it does nothing if one already
  runs; the desktop app and the VS Code extension run it for you when they open), or run
  `krypton`, which starts it and opens its front door in your browser. A phone cannot start
  the hub: it shows the command to run on the computer that hosts it, asks again by itself,
  and carries on when the hub answers.
