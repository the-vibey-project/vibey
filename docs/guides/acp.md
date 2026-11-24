---
description: Connect the Zed editor to vibey over the Agent Client Protocol, see what the first session sets up on your computer, and fix it when it does not appear.
---

# Drive vibey from Zed (ACP)

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `vibey acp` makes vibey the coding agent in Zed's agent panel.
> Run `vibey connect --client zed --yes`, open the panel and pick **vibey**. The first session
> starts vibey's hub and worker as your own user services and offers to install PostgreSQL and a
> local search engine. The commands take seconds; optional installs take as long as their
> downloads. Then you type in Zed, vibey runs the work, and spending stays with you.

## The lesson

Zed's agent panel was open on the Professor's screen, empty, when Daniel came in with two coffees.

**Daniel:** Professor, Zed already has its own agents. Why would I put vibey in that panel?

**Professor Feynman:** Think of a wall socket. Zed has one socket, the Agent Client Protocol,
and any agent with the right plug can go in it. `vibey acp` is vibey's plug. Zed sends what you
type; vibey answers.

**Daniel:** So vibey becomes the agent. Who does the work?

**Professor Feynman:** The same machinery as always. Behind the plug is vibey's hub, which owns
the projects and the queue, and a worker that runs the engines. Zed only talks.

**Daniel:** And if the hub is not running?

**Professor Feynman:** That is where the picture stops working. A plug does not wire the house.
This one does, a little: the first time Zed opens a session, vibey checks the computer and
installs the hub and the worker as services that belong to you, never to the whole system. It
asks before installing PostgreSQL or a search engine.

Daniel set his cup down and asked the question every careful person asks.

**Daniel:** Can Zed approve spending money?

**Professor Feynman:** No. A shop assistant may take in a delivery but cannot sign the cheque.
The agent vibey runs as in Zed holds no `spend` permission, so a spending gate is never offered
in the editor at all. You answer those on the host, or in a krypton app.

## Do it

Checked on macOS with vibey-engine 0.4.0. You need vibey installed
([install guide](install.md)) and [Zed](https://zed.dev).

1. Preview what will be written. This writes nothing.

   ```bash
   vibey connect --client zed --dry-run
   ```

   You should see one line for Zed. On a fresh `settings.json` it is a plan to create or update
   the file. If your Zed settings file has `//` comments (Zed's own default file does), you see
   this instead, which is what it printed on the computer this page was checked on (the path is
   shortened here):

   ```text
     [refused  ] zed             (acp)
   Error: zed was not connected: ~/.config/zed/settings.json: invalid JSON (Expecting value): not strict JSON (comments or trailing commas), so vibey does not rewrite it. Add this to its top-level object by hand: "agent_servers": {"vibey": {"type": "custom", "command": "/path/to/vibey", "args": ["acp"], "env": {}}}
   ```

2. Register vibey with Zed.

   ```bash
   vibey connect --client zed --yes
   ```

   You should see a `create:` or `update:` line naming `settings.json`. If you saw the refusal in
   step 1, paste the printed snippet into the top-level object of Zed's settings
   (`zed: open settings`) exactly as printed instead.

3. Open the agent panel in Zed and pick **vibey** as the agent.

4. Type a first prompt, for example `/status`. You should see the first-contact steps appear as
   tool calls: doctor, connect, services, then the PostgreSQL and SearXNG offers if either is
   missing.

5. Confirm from a terminal.

   ```bash
   vibey doctor
   ```

   You should see `zed:acp-agent` reported as present in the `llm-tooling` section.

## Daniel's teach-back

**Daniel:** Zed has a socket for agents, and `vibey acp` is vibey's plug for it.
`vibey connect --client zed` writes the plug into Zed's settings, by the absolute path of my own
`vibey`. The first session sets up my computer: it runs doctor, installs the hub and worker as
my own services, and asks before it installs PostgreSQL or SearXNG. Zed can read, answer and
start work, but it can never approve spending.

**Professor Feynman:** All true. One correction: the worker service waits until your
environment file names `VIBEY_PG_URL`. Until then only the hub runs.

## The details

Every flag and key is in the reference: [`vibey acp`](../reference/cli.md#vibey-acp),
[`[acp]`](../reference/configuration.md#acp) and
[ADR-0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md).

### What `vibey connect` writes for Zed

`vibey connect --yes` registers vibey with every client it supports, Zed included; add
`--client zed` to touch only Zed. It writes a custom agent server into
`~/.config/zed/settings.json` (on Linux, `$XDG_CONFIG_HOME/zed/settings.json` when
`XDG_CONFIG_HOME` is set to an absolute path), keeping every other setting and agent server,
and copies the file it changed to `settings.json.vibey.bak` first:

```json
"agent_servers": {
  "vibey": {"type": "custom", "command": "/path/to/vibey", "args": ["acp"], "env": {}}
}
```

- `command` is the running install's own `vibey`, by absolute path, never whatever `vibey` is
  first on `PATH` (Zed starts agents with a minimal `PATH`).
- The entry is yours to extend: an `env`, other keys, or flags after `acp` (such as
  `--no-bootstrap`) are kept by every later `vibey connect`. It changes only `type`, `command`
  and the leading `acp` when it has to, and leaves a file that already runs this `vibey`
  exactly as it is.
- **A settings file with comments.** Zed's own `settings.json` usually starts with `//`
  comments, and Zed accepts trailing commas. vibey never rewrites a file it cannot read as
  strict JSON, so `vibey connect` leaves it as it is, prints the snippet to paste into its
  top-level object, still connects the other clients, and exits 1. Once the snippet is in,
  `vibey connect` and `vibey doctor` see the entry and leave the file alone. Paste it as
  printed: the `command` is the path vibey checks for.
- **By hand.** Open Zed's settings (`zed: open settings`) and add the snippet above with the
  path `vibey connect --dry-run` prints.

### What else your clients can have

`vibey connect` (and `vibey doctor`, in its `llm-tooling` section) lists, for each client
installed here, each surface vibey offers it:

| Surface | Which clients | Who installs it |
|---|---|---|
| ACP agent entry | Zed | `vibey connect` |
| MCP server entry (`vibey mcp`) | Claude Code, Claude Desktop, Codex, Cursor, VS Code, Gemini CLI | `vibey connect` |
| `vibey-chat-driver` skill | Claude Code and Codex | the client's own command |
| `vibey` plugin | Claude Code | the client's own command |

The Codex skill folder, `~/.codex/skills`, is where Codex reads user skills, but it has not been
verified against a real Codex install. A missing surface is named with the command that fixes
it; see [LLM tooling](../reference/cli.md#vibey-connect-llm-tooling). In Claude Code the plugin
and skill come from:

```text
/plugin marketplace add the-vibey-project/vibey
/plugin install vibey@vibey
```

### First contact on a fresh computer

The first session Zed opens sets the computer up, after `session/new` has answered and as tool
calls in that session, so you can watch each step (the
[Bootstrap](../reference/cli.md#bootstrap-doctor-connect-services-and-postgresql) reference
has every detail):

1. **`vibey doctor`** runs its local sections, the LLM tooling report included, and shows what
   it found.
2. **`vibey connect`** registers vibey with each client whose config folder already exists
   under your home folder. It never writes a project file, never creates a client's folder, and
   never writes through a symbolic link.
3. **Services.** vibey writes and loads two user-level units: `dev.vibey.hub` (`vibey serve`)
   and `dev.vibey.worker` (`vibey worker --all-projects`, only once your environment file sets
   `VIBEY_PG_URL`). It uses launchd (`~/Library/LaunchAgents`, `gui/<uid>`) or
   `systemd --user` (`$XDG_CONFIG_HOME/systemd/user`). Never a system unit, never `sudo`, never
   as root. While a session is open a keep-alive restarts them if they go down.
4. **PostgreSQL**, at your first prompt in `drive` mode, if it is missing. Zed asks
   "Install PostgreSQL with brew / apt-get / dnf?" and only **Install PostgreSQL** installs.
   vibey never types a password; if `sudo` wants one, run `vibey doctor --install-postgres` in
   your own terminal.
5. **SearXNG**, right after, at the same prompt. vibey's web search asks a local SearXNG first
   and Brave only as a backup. When none is there, Zed asks "Download and run SearXNG
   (searxng/searxng@sha256:...) in a container on 127.0.0.1:28180?" and only
   **Install SearXNG** installs.
   - vibey uses your own `podman` (or `docker`), found only in the usual install folders (never
     your PATH), and never installs one.
   - It pulls one image pinned by its digest, writes its settings in your configuration folder,
     and loads a third user-level unit, `dev.vibey.searxng`, kept running like the others.
   - Nothing is asked when you run your own (`VIBEY_SEARXNG_URL`) or one already answers.
   - `[acp] searxng = "never"` in your own `vibey.toml` stops the offer; `vibey searxng install`
     does the same job from a terminal ([`vibey searxng`](../reference/cli.md#vibey-searxng)).

### Who may switch these steps on

What may happen here is granted by your own `vibey.toml`, in your configuration folder
(`~/Library/Application Support/vibey/vibey.toml` on macOS, `~/.config/vibey/vibey.toml` on
Linux). The `vibey.toml` of the folder Zed opened can only turn steps off or narrow them
([who may set what](../reference/configuration.md#acp)).

| `[acp]` key | Default | What it does |
|---|---|---|
| `auto_bootstrap` | `true` | Run first contact at all. `false` turns the whole bootstrap off. |
| `auto_services` | `true` | Load the hub and worker units. |
| `searxng` | `"ask"` | `"ask"` offers SearXNG once; `"never"` stops the offer. |
| `default_mode` | `"drive"` | The mode a new session starts in. |
| `permission_timeout_seconds` | `600` | How long a gate question waits for your pick. |
| `cancel_grace_seconds` | `2.0` | How long a cancel waits for a hub call already sent. |

To skip the bootstrap for this editor only, use `"args": ["acp", "--no-bootstrap"]` in the
agent's entry: `vibey connect` and `vibey doctor` count that entry as connected and keep the
flag.

### Undo it

`vibey acp unload` stops and removes the units vibey loaded (a unit you edited is unloaded and
left in place). Then set `auto_services = false` in your own `vibey.toml`, or the next session
loads them again. By hand:

```bash
# macOS
launchctl bootout gui/$UID/dev.vibey.hub; rm ~/Library/LaunchAgents/dev.vibey.hub.plist
# Linux
systemctl --user disable --now dev.vibey.hub.service
```

Do the same for `dev.vibey.worker`. `vibey acp unload` also removes the SearXNG container and
marks SearXNG stopped for good, so no session starts it again until `vibey searxng install`;
`vibey searxng uninstall --purge` removes its image and settings too.

### Modes

A session is in one of two modes, which the editor switches (`session/set_mode`):

| Mode | May use | What it means |
|---|---|---|
| `observe` | `view` | `/status`, `/gates`, `/ledger`, `/queue` and the rest show you what is happening, and nothing changes. |
| `drive` | `view`, `answer`, `run` | May also answer gates that do not spend, and start, pause or unwind work. |

The default is `[acp] default_mode` (`drive`). A prompt the mode does not allow is answered
with a message and never reaches the hub. Every `/` command the hub's chat knows is offered in
Zed's command menu. Web search and page fetch are not ACP commands.

### What the agent may do at most

The mode is one limit; the hub's own grant is the other. `vibey acp` runs as the hub's `agent`
principal, whose scopes are `[hub] agent_scopes` in your own `vibey.toml`. Unset, they are
`view`, `answer`, `run`, `acp_sessions` and `web` (`AGENT_DEFAULT_SCOPES`,
`src/vibey/domain/hub_scope.py`). Never `spend`, `bump` or `workflows`. A repository's
`vibey.toml` may only narrow the list, and `agent_scopes = []` in your own file turns agent
access off. See [`[hub]`](../reference/configuration.md#hub).

### Gates

When a project waits on you, the gate is put to you after the hub's reply, as a permission
request with one option per answer plus vibey's own **Leave it open**. Only an option you pick
answers it. No answer within `[acp] permission_timeout_seconds`, a cancel, or
**Leave it open** answers nothing.

A gate that spends money (`budget_exhausted`, the `deploy_*` gates) and the deployment opt-in
after REVIEW are never offered in the editor. The agent principal holds no `spend` scope, so a
model in the loop cannot approve spending, and one click in a panel must not provision real
infrastructure. Answer those on the host (`vibey answer <gate id> ...`, with the id from
`vibey gates`) or in the krypton desktop or mobile app. Do not let Zed auto-approve vibey's
permission requests: a permission is your answer only if a person picks it.

### Cancel

Zed's stop button sends `session/cancel`: the turn ends at once and a permission request still
out answers nothing. A hub call already sent cannot be recalled; vibey waits
`[acp] cancel_grace_seconds` for its outcome and otherwise tells you it may still apply,
naming the request id to look for in the ledger.

### Sessions

Each session's history is kept by the hub. A client that offers it can reopen a session:
`session/load` shows its history again, `session/resume` restores its mode and project without
it. A session follows the project whose repository holds the folder Zed opened, and switches to
the project a reply names. Live ledger events stream into the session between turns. See
[Sessions are kept](../reference/cli.md#sessions-are-kept-load-resume-list-and-close).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| vibey is not in Zed's agent list | The entry was never written, often because the settings file has comments | `vibey connect --client zed --dry-run` prints the snippet to paste. `vibey doctor` shows `zed:acp-agent` as present or missing. |
| `zed was not connected: ... not strict JSON` | Zed's file has `//` comments or trailing commas | Paste the printed snippet by hand, exactly as printed. |
| The hub is away | The `dev.vibey.hub` unit is stopped | `launchctl print gui/$UID/dev.vibey.hub` (macOS) or `systemctl --user status dev.vibey.hub` (Linux). |
| The worker never starts | It waits for `VIBEY_PG_URL` in the environment file (`[supervisor] env_file`); the services step says so | Set it, then open a new session. |
| Search goes to Brave, or fails | No local SearXNG answers | `vibey searxng status` says what is here: the runtime, the image, the unit and whether the SearXNG answers as vibey's own. The `searxng` line of `vibey doctor` says the same in one line. |
| A spending gate never appears in Zed | By design: the agent holds no `spend` scope | Answer it on the host with `vibey answer`, or in a krypton app. |
| Something else looks wrong | | Run `vibey doctor` in a terminal: the same checks, printed. |

**Where the logs are.** The units log to `[supervisor] log_dir`: `~/Library/Logs/vibey/hub.log`,
`worker.log` and `searxng.log` on macOS, `$XDG_STATE_HOME/vibey/logs/` (else
`~/.local/state/vibey/logs/`) on Linux. `vibey acp`'s standard output is the protocol;
everything else goes to standard error, which Zed shows in its ACP logs (`dev: open acp logs`).

## Where next

- [VS Code extension](vscode-extension.md): the same hub from VS Code, with tasks that run on a
  local model.
- [Drive a project](drive-a-project.md): every surface that can talk to a vibey project, side
  by side.
- [Local models on Ollama](local-models-ollama.md): set up the model the worker this page
  installs will run.

## Say it in one line

`vibey connect --client zed --yes` makes vibey Zed's coding agent; the first session sets up the hub and worker as your own services, and Zed can never approve spending.
