# Drive vibey from Zed (ACP)

`vibey acp` is an [Agent Client Protocol](https://agentclientprotocol.com) agent: an editor
such as Zed launches it over standard input and output and talks to vibey as it would to any
other coding agent. You type in the editor's agent panel; vibey's hub runs the projects, keeps
the ledger and asks you the gates. This guide covers connecting Zed, what happens the first time
on a fresh computer, and what to look at when something is wrong. Every flag and key is in the
reference: [`vibey acp`](../reference/cli.md#vibey-acp), [`[acp]`](../reference/configuration.md#acp)
and [ADR-0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md).

## Connect Zed

The one command, which registers vibey with every client it supports (Zed included):

```bash
vibey connect --yes
# or only Zed:
vibey connect --client zed --yes
```

It writes a custom agent server into `~/.config/zed/settings.json` (on Linux,
`$XDG_CONFIG_HOME/zed/settings.json` when `XDG_CONFIG_HOME` is set to an absolute path),
keeping every other setting and agent server, and copies the file it changed to
`settings.json.vibey.bak` first:

```json
"agent_servers": {
  "vibey": {"type": "custom", "command": "/path/to/vibey", "args": ["acp"], "env": {}}
}
```

`command` is the running install's own `vibey`, by absolute path, never whatever `vibey` is
first on `PATH` (Zed starts agents with a minimal `PATH`). `vibey connect --dry-run` shows
the plan without writing anything. The entry is yours to extend: an `env`, other keys, or
flags after `acp` (such as `--no-bootstrap`) are kept by every later `vibey connect`, which
changes only `type`, `command` and the leading `acp` when it has to, and leaves a file that
already runs this `vibey` exactly as it is.

**A settings file with comments.** Zed's own `settings.json` usually starts with `//`
comments, and Zed accepts trailing commas. vibey never rewrites a file it cannot read as strict
JSON, so `vibey connect` leaves it exactly as it is and prints the snippet to paste into its
top-level object, by hand (the other clients are still connected, and the command exits 1).
Once the snippet is in, `vibey connect` and `vibey doctor` see the entry and leave the file
alone. Paste it as printed: the `command` is the path vibey checks for.

**By hand.** Open Zed's settings (`zed: open settings`) and add the snippet above with the path
`vibey connect --dry-run` prints after `ACP agent command:`.

Then open the agent panel in Zed and pick **vibey** as the agent.

## What else your clients can have

`vibey connect` (and `vibey doctor`, in its `llm-tooling` section) lists, for each client
installed here, each surface vibey offers it: the ACP agent entry (Zed), the MCP server entry
(every other client), the `vibey-chat-driver` skill (Claude Code and Codex; the Codex folder,
`~/.codex/skills`, is where Codex reads user skills but has not been verified against a real
Codex install) and the `vibey` plugin (Claude Code). A missing one is named with the command that fixes it; see
[LLM tooling](../reference/cli.md#vibey-connect-llm-tooling). vibey writes the two entries
itself. The skill and the plugin are installed by the client's own command, for example in
Claude Code:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install vibey@vibey
```

## First contact on a fresh computer

The first session Zed opens sets the computer up, after `session/new` has answered and as tool
calls in that session, so you can watch each step (the
[Bootstrap](../reference/cli.md#bootstrap-doctor-connect-services-and-postgresql) reference
has every detail):

1. **`vibey doctor`** runs its local sections, the LLM tooling report included, and shows what
   it found.
2. **`vibey connect`** registers vibey with each client whose config folder already exists under
   your home folder. It never writes a project file, never creates a client's folder, and never
   writes through a symbolic link.
3. **Services.** vibey writes and loads two user-level units -- `dev.vibey.hub` (`vibey serve`)
   and `dev.vibey.worker` (`vibey worker --all-projects`, only once your environment file sets
   `VIBEY_PG_URL`) -- with launchd (`~/Library/LaunchAgents`, `gui/<uid>`) or `systemd --user`
   (`$XDG_CONFIG_HOME/systemd/user`). Never a system unit, never `sudo`, never as root. While a
   session is open a keep-alive restarts them if they go down.
4. **PostgreSQL**, at your first prompt in `drive` mode, if it is missing: Zed asks
   "Install PostgreSQL with brew / apt-get / dnf?" and only **Install PostgreSQL** installs. vibey
   never types a password; if `sudo` wants one, run `vibey doctor --install-postgres` in your own
   terminal.

What may happen here is granted by your own `vibey.toml`, in your configuration folder
(`~/Library/Application Support/vibey/vibey.toml` on macOS, `~/.config/vibey/vibey.toml` on
Linux). The `vibey.toml` of the folder Zed opened can only turn steps off or narrow them
([who may set what](../reference/configuration.md#acp)). Turn the whole bootstrap off with
`auto_bootstrap = false` there, or for this editor with `"args": ["acp", "--no-bootstrap"]` in
the agent's entry: `vibey connect` and `vibey doctor` count that entry as connected and keep the
flag.

**Undo it.** `vibey acp unload` stops and removes the units vibey loaded (a unit you edited is
unloaded and left in place). Then set `auto_services = false` in your own `vibey.toml`, or the
next session loads them again. By hand:

```bash
# macOS
launchctl bootout gui/$UID/dev.vibey.hub; rm ~/Library/LaunchAgents/dev.vibey.hub.plist
# Linux
systemctl --user disable --now dev.vibey.hub.service
```

(and the same for `dev.vibey.worker`).

## Modes

A session is in one of two modes, which the editor switches (`session/set_mode`):

- **`observe`** reads: `/status`, `/gates`, `/ledger`, `/queue` and the rest show you what is
  happening, and nothing changes.
- **`drive`** may also answer gates and start, pause or unwind work.

The default is `[acp] default_mode` (`drive`). A prompt the mode does not allow is answered with
a message and never reaches the hub. Every `/` command the hub's chat knows is offered in Zed's
command menu.

## Gates

When a project waits on you, the gate is put to you after the hub's reply, as a permission
request with one option per answer plus vibey's own **Leave it open**. Only an option you pick
answers it; no answer within `[acp] permission_timeout_seconds`, a cancel or **Leave it open**
answers nothing.

A gate that spends money -- `budget_exhausted`, the `deploy_*` gates -- and the deployment
opt-in after REVIEW are never offered in the editor. The agent principal `vibey acp` runs as
never holds the `spend` scope, so a model in the loop cannot approve spending, and one click in a
panel must not provision real infrastructure. Answer those on the host (`vibey answer <gate
id> ...`) or in the krypton desktop or mobile app. Do not let Zed auto-approve vibey's
permission requests: a permission is your answer only if a person picks it.

## Cancel

Zed's stop button sends `session/cancel`: the turn ends at once and a permission request still
out answers nothing. A hub call already sent cannot be recalled; vibey waits
`[acp] cancel_grace_seconds` for its outcome and otherwise tells you it may still apply,
naming the request id to look for in the ledger.

## Sessions

Each session's history is kept by the hub. A client that offers it can reopen a session:
`session/load` shows its history again, `session/resume` restores its mode and project without
it. A session
follows the project whose repository holds the folder Zed opened, and switches to the project a
reply names. Live ledger events stream into the session between turns. See
[Sessions are kept](../reference/cli.md#sessions-are-kept-load-resume-list-and-close).

## Troubleshooting

- **vibey is not in Zed's agent list.** Run `vibey connect --client zed --dry-run`: a refused
  file prints the snippet to paste. `vibey doctor` shows `zed:acp-agent` as present or missing.
- **The hub is away.** Ask the service manager:

  ```bash
  launchctl print gui/$UID/dev.vibey.hub        # macOS
  systemctl --user status dev.vibey.hub          # Linux
  ```

  The units log to `[supervisor] log_dir`: `~/Library/Logs/vibey/hub.log` and `worker.log` on
  macOS, `$XDG_STATE_HOME/vibey/logs/` (else `~/.local/state/vibey/logs/`) on Linux.
- **What `vibey acp` itself said.** Its standard output is the protocol; everything else goes
  to standard error, which Zed shows in its ACP logs (`dev: open acp logs`).
- **The worker never starts.** It waits for `VIBEY_PG_URL` in the environment file
  (`[supervisor] env_file`); the services step says so. Set it, then open a new session.
- **Something looks wrong.** Run `vibey doctor` in a terminal: the same checks, printed.
