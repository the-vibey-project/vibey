# Publishing a finished project

A run that ends at REVIEW leaves its work on a local branch. Publishing is the last step: it
pushes that branch and opens a pull request, or, for a project with no remote, creates a new
GitHub repository and pushes to it. Both send work off your machine and neither is easy to take
back, so nothing is published unless you turn it on, and the safe choices are the defaults.

## Turn it on

```toml
[publish]
mode = "interview"   # off (default) | interview | auto
```

| Mode | What happens after you decline deployment |
|---|---|
| `off` | The project finishes locally, as it always has. |
| `interview` | A `publish_interview` gate shows exactly what would be pushed and where, and waits. |
| `auto` | The proposal is published with no gate. |

Settings (all optional): `visibility` (`private` by default, or `public`), `draft` (`true` by
default), `base`, `remote`, `owner`. See [`[publish]`](../reference/configuration.md#publish).

## What it proposes

- **A project whose checkout has a remote** gets its integration branch pushed and a **draft**
  pull request opened into the remote's default branch.
- **A project with no remote** gets a new **private** GitHub repository, named from the project,
  and the branch pushed to it as `main`.
- If an earlier attempt created the repository but did not get to push, the retry pushes to it
  and does not create another.

The title and body come from the spec's objective and criteria. Nothing is forced, and the base
branch is never pushed to.

## The interview

`vibey gates` shows the gate and the exact command to answer it. The prompt reads like:

```text
The project is finished and reviewed. Publish it?

Push branch vibey/.../integration to origin and open a draft pull request into develop.
Title: feat: Fold Humbleberger Ministries into the site.
```

```sh
vibey answer GATE_ID --choice accept_defaults          # publish exactly that
vibey answer GATE_ID --choice skip                     # finish locally (the default)
vibey answer GATE_ID --raw '{"choice": "custom", "draft": false, "title": "..."}'
```

`custom` changes only the fields you name: `title`, `body`, `base`, `draft`, `visibility`,
`repo`, `owner`, `description`. A field that is not one, or a name that could be read as an
option, is refused and the gate asks again, saying what to fix. The gate has no timeout default:
silence publishes nothing.

## Unattended

`vibey worker --auto-publish` answers the interview `accept_defaults`, for one project. It is a
separate flag from `--auto-accept-all` on purpose: it is the one acceptance that sends work off
the machine. For an unattended run that publishes a draft pull request:

```sh
vibey worker --project ID --auto-accept-all --auto-publish
```

or set `mode = "auto"` and no gate is raised at all.

## What it needs, and what it refuses

- `git` and the GitHub CLI `gh`, **logged in** (`gh auth login`). If not, the job parks on an
  `engine_misconfigured` gate that says which: fix it and answer anything to retry. vibey does
  not pass `GH_TOKEN` or `GITHUB_TOKEN` to `gh`.
- A work item can write the repository's own git config, and a push runs whatever that config
  names. So publishing refuses a repository whose config sets `core.sshCommand`,
  `core.gitProxy`, `core.askPass`, a credential helper and similar, naming the key to remove;
  it runs git with hooks off; and it refuses a remote that is not an https or ssh address.
- It does not decide where the work goes: the plan names the remote. In `interview` mode, read
  the remote in the prompt; `auto` and `--auto-publish` trust the checkout's remote, so use
  them on repositories you control.

What it records: `PublishCompleted` (kind, URL, branch, draft, visibility) or `PublishSkipped`
on the ledger. The published form of the ledger leaves out the URL and branch.
