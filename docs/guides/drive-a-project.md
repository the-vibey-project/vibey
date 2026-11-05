---
description: Start a vibey project, talk to it while it designs and builds, pause it, and unwind it, from a terminal, VS Code, the desktop app or your phone.
---

# Drive a project from anywhere

> **Bottom Line Up Front (BLUF) — Install any krypton interface first, then drive your project from chat:**
>
> Krypton and vibey are the free, censorship-free Claude Code and Codex killer — replacing both by writing code the way a principal software engineer does so you get quality code rather than slop, completely free of charge, with AGI superintelligence coming soon.
>
> | Surface | How to install it (one step) | How to start & drive a project |
> |---|---|---|
> | **1. Your existing AI chat / IDE (`vibey connect` MCP)** | Run `curl -fsSL https://raw.githubusercontent.com/the-vibey-project/vibey/main/scripts/install.sh \| sh -s -- --with-krypton && vibey connect --yes` in Terminal. | Open Claude Code, Claude Desktop, Codex, Cursor, VS Code, or Gemini CLI and say: *"Start a vibey project called my-app"* or *"Show open vibey gates."* |
> | **2. Browser launcher (`krypton`)** | Included with `--with-krypton` above (or `uv tool install krypton-app`). | Run `krypton` in Terminal — it starts the local hub (`127.0.0.1:8765`) and opens it in your browser. |
> | **3. krypton Desktop App (macOS & Linux)** | **macOS (Apple silicon):** Download `krypton-desktop-<version>-macos-arm64.dmg` from [Releases](https://github.com/the-vibey-project/vibey/releases), drag **krypton** to **Applications**, and run `xattr -dr com.apple.quarantine /Applications/krypton.app`.<br>**Linux (Flatpak):** `flatpak install --user krypton-desktop-<version>-linux-x86_64.flatpak` (or Ubuntu `.tar.gz`: `sudo tar -xzf krypton-desktop-<version>-linux-x86_64.tar.gz -C /`). | Open **krypton**. It lands directly on **Chat** (`Ctrl+L` / `Cmd+L`), starts your local hub automatically, and lets you type `/new`, `/status`, `/gates`, `/answer`, `/start`, `/pause`, or `/abandon` or click inline gate cards. |
> | **4. krypton for VS Code / VSCodium / Cursor** | **Open VSX:** `codium --install-extension the-vibey-project.krypton`<br>**VS Code / Cursor:** Download `krypton-vscode-<version>.vsix` from [Releases](https://github.com/the-vibey-project/vibey/releases) and run `code --install-extension krypton-vscode-<version>.vsix` (or **Extensions → `…` → Install from VSIX…**). | Click the **krypton atom** in the activity bar, or in VS Code Chat type `@krypton /chat`, `@krypton /mcp`, `@krypton /new`, `@krypton /next`, or `@krypton /reply`. |
> | **5. krypton Mobile & Web App (Android, iOS, Browser)** | **Web:** `mkdir krypton-web && tar -xzf krypton-web-<version>.tar.gz -C krypton-web && python3 -m http.server 8000 -d krypton-web` → open `http://localhost:8000`.<br>**Android:** Tap `krypton-android-<version>.apk` from [Releases](https://github.com/the-vibey-project/vibey/releases) on your phone (or `adb install`).<br>**iOS:** Signed `.ipa` for TestFlight / App Store, or run `npx expo start` in `clients/app` with **Expo Go**. | Open the app — it lands on the **Chat** tab, where you can switch projects, run `/` slash commands, and approve gates inline. |
>
> Full step-by-step installation instructions for every skill level are in [Install, copy, reinstall, uninstall](install.md) and [Downloads](downloads.md).

You can start a project, answer the questions it asks, pause it and end it from any of vibey's
surfaces. They all do the same four things, through the same audited commands, so a project
you start on your phone looks exactly like one you started in a terminal.

| | Frontier LLM Chat (MCP) | Terminal | VS Code chat | Desktop app | Phone and web app |
|---|---|---|---|---|---|
| **Start** | Ask (`vibey_start_project`) | `vibey new NAME` | `@krypton /new` | **Chat** (`/new`) or **Start a project** (`Ctrl+N`) | **Chat** (`/new`) or **Start a project** |
| **Answer a question** | Ask (`vibey_gates` → `vibey_answer_gate`) | `vibey answer` | `@krypton /next`, then `/reply 1` (or inline card) | **Chat** inline gate card (or **Gates**) | **Chat** inline gate card (or **Gates**) |
| **Pause and resume** | Ask (`vibey_pause_work` / `vibey_start_work`) | `vibey retry`, `vibey recover` | `/pause`, `/resume` | **Chat** (`/pause`, `/start`) or the row's menu | **Chat** (`/pause`, `/start`) or the project's card |
| **Unwind** | Ask (`vibey_abandon_project`, dry-run first) | `vibey abandon` | `/unwind` | **Chat** (`/abandon`) or the row's menu | **Chat** (`/abandon`) or the project's card |

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
