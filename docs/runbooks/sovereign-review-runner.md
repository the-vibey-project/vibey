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

## The egress gate

The job container has no route out. `vibey-runner.sh` creates a Docker network with
`--internal` (`[runners] egress_network`) and starts one small container on it and on the
default network, `[runners] egress_name` (`vibey-egress`). The job joins only the internal
network, so the gate is the only thing it can reach:

- **HTTPS to `egress_allow` only**, on port 443, through a `CONNECT` proxy
  (`HTTPS_PROXY=http://vibey-egress:3128`). The gate resolves the name itself and refuses any
  address that is not globally routable, so a name that points at this machine or its LAN is
  refused whatever it is called. An address literal is never an allowed host.
- **The model server's four endpoints**, on `http://vibey-egress:11434`: `GET /api/version`,
  `GET /api/tags`, `GET /v1/models`, `POST /v1/chat/completions`. A job cannot pull, create or
  delete a model on this machine, and cannot reach any other service on it.

Why: `--add-host host.docker.internal:host-gateway` makes **every** port on this machine
reachable from the container, and a job's shell has full network egress (`allow_network=False`
in the agent runner sets an environment variable; it enforces nothing). On 2026-10-09 the
host's Postgres (5432) and RabbitMQ (5672, 15672) accepted connections from inside a runner
container. The gate is what makes "unreachable" true by construction.

To verify it on this machine (a throwaway network and gate, nothing of the runner's):

```bash
docker network create --internal egress-test
docker run -d --name egress-test --read-only --cap-drop ALL \
  --add-host host.docker.internal:host-gateway \
  -v ~/.local/share/vibey-runner/egress:/egress:ro \
  -e EGRESS_ALLOW=github.com -e EGRESS_MODEL_UPSTREAM=host.docker.internal:11434 \
  --entrypoint python3 vibey-runner:latest /egress/egress_gate.py
docker network connect egress-test egress-test
docker run --rm --network egress-test --entrypoint bash vibey-runner:latest -c '
  (</dev/tcp/host.docker.internal/5432) 2>&1 | tail -1       # must fail
  curl -s -m 5 --noproxy "*" https://1.1.1.1 || echo blocked  # must be blocked
  curl -s -m 5 -x http://egress-test:3128 https://github.com -o /dev/null -w "%{http_code}\n"
  curl -s -m 5 -X DELETE http://egress-test:11434/api/delete -w "%{http_code}\n"  # 403'
docker rm -f egress-test; docker network rm egress-test
```

**When a job step fails on a host nobody listed**, the gate says so. Every decision is one line
on its standard output:

```bash
docker logs --since 30m vibey-egress | grep DENY
# egress DENY  example.com:443 -- not on the allowlist (add the host to [runners] egress_allow)
```

A `DENY ... not on the allowlist` line names the host to add to `[runners] egress_allow` (an
exact name, or `*.` and a domain you trust; see `docs/configuration.md` for what is refused).
The other reasons are not allowlist problems: `resolves to an address that is not public`
means the name points at this machine or a private network, which is refused whatever the
list says; `the host's model server did not answer` means Ollama is down.

After changing `egress_gate`, `egress_allow` or the gate's template, re-run
`uv run vibey-gh runner install --load` (the supervisor, and with it the gate, is restarted).

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
uv tool install --force --from . vibey-engine
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

## Does it catch defects?

A verdict from this runner is only worth what its recall is. The review canary measures it:
41 diffs against this repository's own code — 27 with one planted defect each, in nine
classes, and 14 clean controls — reviewed through `vibey-gh local-review` with every
`[pr_automation.fallback]` setting the pull-request review uses
(`docs/architecture/evidence/review-canary/corpus.toml` says how each was built).
`review-canary.yml` runs it weekly on GitHub-hosted runners, not this one (operator,
2026-10-03: every CI workflow on hosted runners): it serves the same model with Ollama on
the runners' CPU, cut into `[pr_automation.review_canary] shards` jobs that
`vibey-gh review-canary merge` joins into one measurement, and lands it as a pull request.
Every setting that decides a verdict is the one this runner reviews with; the deadline
rates are the hosted runners' own, declared beside the shard count. The silicon differs, so
a weekly measurement is of this configuration on CPU, not of this machine. A defect counts as caught only when the verdict
blocks and a finding is on the planted lines and names the defect's class. A review that
gives no verdict is counted apart, never as caught or missed.

```bash
uv run vibey-gh review-canary check               # the corpus builds; offline
uv run vibey-gh review-canary show --case race-worker-build-lock
uv run vibey-gh review-canary run --work ~/git/vibey-storm/review-canary.work.jsonl
uv run vibey-gh review-canary status              # exit 0 meets the floor, 1 not, 3 none
```

The floor is `[pr_automation.review_canary]` in `.vibey-gh.toml`. `status` also refuses a
measurement that is older than `max_age_days`, ran a subset, or ran under other settings.

<!-- BEGIN GENERATED review-canary — regenerated by `vibey-gh review-canary render` -->

Latest measurement: finished 2026-10-02T13:36:53.627598+00:00 on `f163a8ebe8a3`, at commit `3bb577a4e74b`, over all 41 cases of corpus `0fde8a43d7a7` (27 defects in 9 classes, 14 controls). Model `gpt-oss:20b`, think `default`, window 65536, reserve 16384, scope `full`, source context on.

| Measure | Result | 95% Wilson interval |
|---|---|---|
| Recall: blocked, on the planted lines, naming the class | 23 of 27 (85.2%) | 67.5% – 94.1% |
| Recall: blocked, on the planted lines | 23 of 27 (85.2%) | 67.5% – 94.1% |
| False positives: controls blocked | 0 of 14 (0.0%) | 0.0% – 21.5% |
| No verdict | 0 of 41 | not counted either way |

| Class | Caught | No verdict |
|---|---|---|
| `inverted_condition` | 3 of 3 | 0 |
| `missing_await` | 3 of 3 | 0 |
| `off_by_one` | 3 of 3 | 0 |
| `removed_guard` | 3 of 3 | 0 |
| `resource_leak` | 3 of 3 | 0 |
| `shared_state_race` | 2 of 3 | 0 |
| `sql_injection` | 2 of 3 | 0 |
| `swallowed_exception` | 2 of 3 | 0 |
| `wrong_error_return` | 2 of 3 | 0 |

Small samples: each interval is what this many cases can say, and is wide on purpose. Against the floor declared when it ran -- recall's lower bound at least 0.5, the false-positive rate's upper bound at most 0.5 -- this measurement **meets** it. Whether it still stands (its age, and settings changed since) is `vibey-gh review-canary status`'s to say.

<!-- END GENERATED review-canary -->

What the block does not say on its own:

- **The corpus is small diffs.** Every case is one file changed in one request. The canary
  says nothing about large diffs, which the review splits into parts and on which, up to
  2026-10-02, it had reached no verdict under #1316's settings. Why, and what would, is a
  preregistered study in progress, mechanism and screening only
  ([`research/large-diff-review/experiments/`](https://github.com/the-vibey-project/vibey/tree/develop/research/large-diff-review/experiments)).
  Production settings are unchanged until that study confirms a method.
- **A pass can contradict its own summary.** In the first measurement, five planted defects
  passed with no findings, and in two of them the summary named the defect while `pass` was
  true. The gate reads `pass`.
- **The matching rule is strict.** By hand, two of the first measurement's misses were real
  catches the lexical rule did not credit, so recall by hand was 20 of 25. The floor reads
  the strict figure.
- **One run.** The first measurement ran once, on one host, and `review-canary.yml` had not
  yet run on its schedule on 2026-10-02.

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
