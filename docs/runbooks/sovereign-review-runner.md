# Sovereign review runner

How to stand up, verify and remove the self-hosted runner that runs `pr-review.yml`'s
`review-sovereign` job on `[self-hosted, vibey-local-vibey]` (sub-doctrine 8.a). Everything
on the host is rendered from the `[runners]` table in `.vibey-gh.toml` by `vibey-gh runner`
(sub-doctrine 12.c). Nothing here is hand-written, so this page is the whole procedure.

The runner is macOS-only: a launchd user agent keeps a bash supervisor alive, and the
supervisor starts one ephemeral runner container per job.

## What it needs

| Thing | Where it comes from |
|---|---|
| Docker Desktop, running | the host |
| `ollama serve` on `[pr_automation.fallback] base_url`, with its `model` pulled | the host |
| A fine-grained token for **this repository only**, **Administration: Read and write** | the operator, step 1 |
| That token in a **file-based** gh login in `~/.config/gh-runner` | the operator, step 2 |
| The LaunchAgent, supervisor, Dockerfile and entrypoint | `vibey-gh runner install`, step 4 |

### Why a dedicated credential

The supervisor mints a registration token per job, which needs a durable GitHub credential.
The operator's own `gh` login keeps its token in the macOS keyring, and a LaunchAgent cannot
read the keyring: `gh auth status` passes in every shell and fails under launchd, so the
runner stayed down with nothing visibly wrong. That login can also administer every
repository the operator owns, which is far more than a runner needs.

So the runner has a login of its own. It is set as `GH_CONFIG_DIR` in the LaunchAgent and
stored in a file by `gh auth login --insecure-storage`, and it holds a token that can do
nothing but manage this repository's runners. The supervisor refuses to start, and logs the
command that fixes it, if that directory is unset or missing, if it holds no login, if its
token went to the keyring, if its `hosts.yml` is readable by other users, or if GitHub
rejects the token. It also refuses a `GH_CONFIG_DIR` that resolves (through symlinks and
`..`) to gh's own default directory, `$XDG_CONFIG_HOME/gh` or `~/.config/gh`; so does
`vibey-gh` when it loads the configuration. It clears `GH_TOKEN` and `GITHUB_TOKEN`, names
the configured host on every `gh` call, and never falls back to any other credential. It
never prints the token.

### The token's permission

Exactly one repository permission: **Administration: Read and write**. GitHub's
[permissions for fine-grained personal access tokens](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens)
list, under "Repository permissions for Administration":

| Endpoint | What the supervisor uses it for | Access |
|---|---|---|
| `POST /repos/{owner}/{repo}/actions/runners/registration-token` | mint a registration token per job | write |
| `GET /repos/{owner}/{repo}/actions/runners` | find offline runners to reap | read |
| `DELETE /repos/{owner}/{repo}/actions/runners/{runner_id}` | reap them | write |

GitHub adds read-only Metadata to every fine-grained token. Add nothing else.

## Stand it up

Run these from a checkout of this repository on `develop`, so `vibey-gh` reads its
`.vibey-gh.toml`.

1. Create the token. On GitHub: **Settings → Developer settings → Personal access tokens →
   Fine-grained tokens → Generate new token**.
   - **Resource owner:** `the-vibey-project`. If the organization requires approval for
     fine-grained tokens, the token works only after an owner approves it.
   - **Expiration:** set one, and note the date. When it passes, the supervisor refuses
     with "not accepted by github.com" until step 2 is repeated with a new token.
   - **Repository access:** Only select repositories → `the-vibey-project/vibey`.
   - **Repository permissions:** Administration → **Read and write**.

2. Give the runner its own login. Paste the token when gh waits, press Enter, then Ctrl-D.

   ```bash
   mkdir -m 700 -p ~/.config/gh-runner
   env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=$HOME/.config/gh-runner \
     gh auth login --hostname github.com --with-token --insecure-storage
   chmod 600 ~/.config/gh-runner/hosts.yml
   ```

   `env -u` keeps an exported `GH_TOKEN` from standing in for the token you paste. Your own
   `gh` login in `~/.config/gh` is not touched.

3. Retire the agents of the absorbed repositories. They run the same `vibey-runner.sh` the
   install replaces, so retire them first. Read the dry run: it lists every
   agent under `[runners] unit_prefix` that the tree does not declare, with the repository
   each one serves.

   ```bash
   uv run vibey-gh runner cleanup
   uv run vibey-gh runner cleanup --apply
   ```

   `--apply` boots each one out of launchd and moves its plist to
   `~/.local/share/vibey-runner/retired-units/`. Nothing is deleted, and an earlier retired
   copy is never replaced: a second copy of the same agent is kept as `<name>.1.plist`, then
   `.2`, and so on. To put one back:
   `mv ~/.local/share/vibey-runner/retired-units/<name>.plist ~/Library/LaunchAgents/`, then
   `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/<name>.plist`.

4. Render and install the runner's files. This loads nothing. It prints the same commands
   as the steps below, with this machine's paths filled in.

   ```bash
   uv run vibey-gh runner install
   ```

5. Build the runner image. The version comes from `[runners] runner_version`.

   ```bash
   docker build --build-arg RUNNER_VERSION=2.337.0 -t vibey-runner:latest ~/.local/share/vibey-runner
   ```

6. Load the runner's agent. This replaces the running `-vibey` agent in place.

   ```bash
   launchctl bootout gui/$(id -u)/com.adammatthewsteinberger.vibey-runner-vibey 2>/dev/null
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.adammatthewsteinberger.vibey-runner-vibey.plist
   ```

   `uv run vibey-gh runner install --load` does steps 4 and 6 together, and exits non-zero
   if launchd refuses to load the agent.

## Verify

```bash
uv run vibey-gh runner check
tail -n 20 ~/Library/Logs/com.adammatthewsteinberger.vibey-runner-vibey.log
env -u GH_TOKEN -u GITHUB_TOKEN GH_CONFIG_DIR=$HOME/.config/gh-runner \
  gh api --hostname github.com repos/the-vibey-project/vibey/actions/runners \
  --jq '.runners[] | {name, status, busy, labels: [.labels[].name]}'
```

- `runner check` prints `... matches the tree and its credential is usable` and exits 0.
  "Usable" means GitHub accepted the token: it runs `gh auth status --hostname github.com`
  under the runner's `GH_CONFIG_DIR` with `GH_TOKEN` and `GITHUB_TOKEN` unset, and prints
  none of gh's output. Otherwise it names each `missing:`, `drift:`, `not executable:` or
  `credential:` problem.
- The log shows `supervisor starting` and then `registering an ephemeral runner`. A line
  starting `REFUSING TO START:` names what is missing and the command that fixes it. The log
  moved: it was `~/Library/Logs/vibey-runner-vibey.log`, and is now named after the agent.
- The API lists a runner labelled `vibey-local-vibey` with `"status": "online"`. The runner
  is ephemeral, so after each job it deregisters and the next one registers under a new name.

The workflow schedules the sovereign job only while the heartbeat is fresh. The heartbeat is
published by a timer that `runner install` installs beside the runner (`vibey-gh heartbeat`,
ADR-0060): `<unit_prefix>-heartbeat-vibey`, a LaunchAgent here. Each beat publishes only while
GitHub lists a runner labelled `vibey-local-vibey` as online and Ollama answers with the model,
and it goes through the pre-push gate, which lets an empty parentless commit on a non-branch
ref through by its own rule. The timer must run a `vibey-gh` installed outside any checkout, so
install it as a tool first and run the install with it:

```bash
uv tool install --force --from . vibey
~/.local/bin/vibey-gh heartbeat install --load
~/.local/bin/vibey-gh heartbeat status
uv run vibey-gh sovereign            # the heartbeat's age, as the workflow reads it
```

`heartbeat status` prints the last beat's age and whether it was published or withheld, and
why. The hand-written `com.adammatthewsteinberger.vibey-local-authority` agent that used to
publish the heartbeat is retired: it pushed with `--no-verify` and said "up" whenever its
supervisor had a live process. If it is still loaded, boot it out
(`launchctl bootout gui/$(id -u)/com.adammatthewsteinberger.vibey-local-authority`) before
loading the timer.

## Remove it

```bash
uv run vibey-gh runner uninstall
uv run vibey-gh runner uninstall --apply
rm -rf ~/.config/gh-runner
```

`uninstall` boots the agent out, moves its plist to `retired-units/`, and deletes only the
three files `install` wrote; it also unloads the heartbeat timer and moves its plist to
`retired-units/`. Logs and the last beat's record stay. Then revoke the token on GitHub:
**Settings → Developer settings → Personal access tokens → Fine-grained tokens**.

## Changing it

Edit `[runners]` (or `[pr_automation.fallback]`) in a pull request, then after it merges
repeat steps 4 and 6. `uv run vibey-gh runner check` reports a host that has not caught up
as `drift:`. The supervisor, Dockerfile and entrypoint templates live in
`src/vibey_tools/gh/vibey_gh/templates/runner/`. Do not edit the installed copies.
