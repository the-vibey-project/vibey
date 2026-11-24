---
description: Turn on publishing so a finished vibey project pushes its branch and opens a draft pull request, or creates a private GitHub repository, only when you say so.
---

# Publish a finished project as a draft pull request

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** A run that ends at REVIEW leaves its work on a local branch.
> Set `[publish] mode = "interview"` in `vibey.toml` and vibey will offer to push that branch and
> open a **draft** pull request, or create a **private** GitHub repository when there is no
> remote, and wait for your answer. It is off by default, silence publishes nothing, and it needs
> `git` and a logged-in GitHub CLI (`gh`). Setting it up takes about five minutes.

## The lesson

Daniel had a finished project on his screen and a branch nobody but him could see.

**Daniel:** Professor, vibey built it and the review passed. Why is it still only on my laptop?

**Professor Feynman:** Think of a letter you have written and sealed. Posting it is a different
act from writing it. Once it is in the post box you cannot reach in and take it back. So vibey
writes the letter and then asks, "Shall I post this, to this address?"

**Daniel:** And if I never answer?

**Professor Feynman:** Then the letter stays on your desk. Silence posts nothing. That is the
whole design: the safe choice is the default, and every choice that sends work off your machine
is one you make on purpose.

**Daniel:** What exactly would it post?

**Professor Feynman:** If your checkout has a remote, it pushes the project's integration branch
and opens a pull request into the remote's default branch, as a draft. If there is no remote, it
creates a new private repository on GitHub and pushes the branch there as `main`. It never
forces a push, and it never pushes to the base branch.

**Daniel:** Could a work item trick it into posting somewhere else?

**Professor Feynman:** That is the right worry. A work item can edit the repository's own git
settings, and git runs whatever commands those settings name. So vibey refuses a repository whose
settings name a custom SSH command, a proxy, a password helper or a credential helper, runs git
with hooks switched off, and pushes only to an https or ssh address. Where the picture stops
working is the address itself: vibey uses the checkout's own remote. In `interview` mode you read
it in the prompt. In the unattended modes you are trusting it, so use those only on repositories
you control.

## Do it

You need vibey installed ([install guide](install.md)), a project that reaches REVIEW, `git`, and
the [GitHub CLI](https://cli.github.com).

1. Log the GitHub CLI in. vibey never passes `GH_TOKEN` or `GITHUB_TOKEN` to it, so it uses
   your own login.

   ```bash
   gh auth login
   gh auth status
   ```

   You should see `gh auth status` report that you are logged in to github.com.

2. Turn publishing on in `vibey.toml`. The table is read from the configuration stored with the
   project, the same way `[verify]` is, so set it before you create the project with
   `vibey new`.

   ```toml
   [publish]
   mode = "interview"   # off (default) | interview | auto
   ```

   A misspelt key, or a `base`, `remote` or `owner` that could be read as an option, is refused
   and the project fails to start rather than publish with a setting nobody meant.

3. Let the run reach the end of REVIEW and decline deployment. A `publish_interview` gate opens.
   List it.

   ```bash
   vibey gates
   ```

   You should see the gate with its id and the exact command to answer it. The prompt reads like
   this:

   ```text
   The project is finished and reviewed. Publish it?

   Push branch vibey/.../integration to origin and open a draft pull request into develop.
   Title: feat: Fold Humbleberger Ministries into the site.
   ```

4. Answer it. Replace `GATE_ID` with the id `vibey gates` printed.

   ```bash
   vibey answer GATE_ID --choice accept_defaults
   ```

   vibey pushes the branch and opens the draft pull request, and records `PublishCompleted` on
   the ledger. To finish locally instead, answer `--choice skip`.

## Daniel's teach-back

**Daniel:** Publishing is the step that posts the finished work: push the branch and open a draft
pull request, or make a private repository when there is no remote. It is off until I set
`[publish] mode`. In `interview` mode a gate shows me exactly what will be pushed and where, and
if I never answer nothing is sent. vibey refuses repositories whose git settings could run
someone else's command, and it uses my own `gh` login.

**Professor Feynman:** Right. One correction to keep: "never answer" is safe, but an answer with
no choice in it, `--raw '{}'`, counts as `accept_defaults` and publishes. Say `skip` when you mean
skip.

## The modes

| Mode | What happens after you decline deployment |
|---|---|
| `off` | The project finishes locally, as it always has. The default. |
| `interview` | A `publish_interview` gate shows exactly what would be pushed and where, and waits. |
| `auto` | The proposal is published with no gate. |

Every `[publish]` key ([reference](../reference/configuration.md#publish)); an unknown key is
refused:

| Key | Default | What it does |
|---|---|---|
| `mode` | `"off"` | `off`, `interview` or `auto`. |
| `visibility` | `"private"` | For a new repository: `private` or `public`. |
| `draft` | `true` | Open the pull request as a draft. |
| `base` | the remote's default branch, else `main` | The branch the pull request targets. |
| `remote` | `"origin"` | The remote to push to. |
| `owner` | your `gh` account | The account or organisation a new repository is created under. |

The code is [`domain/publish.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/domain/publish.py)
(the proposal and the answers) and
[`infrastructure/publish/github.py`](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey/infrastructure/publish/github.py)
(the git and `gh` calls).

## What it proposes

- **A project whose checkout has a remote** gets its integration branch pushed and a **draft**
  pull request opened into the remote's default branch (or `base`).
- **A project with no remote** gets a new **private** GitHub repository, named from the project,
  and the branch pushed to it as `main` (or as `base`, when you set one).
- If an earlier attempt created the repository but did not get to push, the retry pushes to it
  and does not create another. If an open pull request for the branch already exists, it is
  reported and no second one is opened.

The title is `feat:` plus the spec's objective, cut to 72 characters. The body lists the
objective and acceptance criteria and says the work was built by vibey and passed review.
Nothing is forced, and the base branch is never pushed to.

## The answers

```sh
vibey answer GATE_ID --choice accept_defaults          # publish exactly that
vibey answer GATE_ID --choice skip                     # finish locally
vibey answer GATE_ID --raw '{"choice": "custom", "draft": false, "title": "..."}'
```

`custom` changes only the fields you name: `title`, `body`, `base`, `draft`, `visibility`,
`repo`, `owner`, `description`. A field that is not one, or a name that could be read as an
option, is refused and the gate asks again, saying what to fix.

The gate's declared default is `skip`, and silence publishes nothing. An answer that names no
`choice` at all is read as `accept_defaults`, so `--raw '{}'` publishes.

## Unattended

`vibey worker --auto-publish` answers the interview `accept_defaults` for one project: a draft
pull request, or a new private repository, never `custom`. It works only for a project whose
`mode` is `interview`. It is a separate flag on purpose, because it is the one acceptance that
sends work off the machine:

- `--auto-accept-all` (design, review and finishing locally) does not include it.
- `--autonomous` (every switch that is safe to leave on unattended) does not include it either.

For an unattended run that publishes a draft pull request:

```sh
vibey worker --project ID --auto-accept-all --auto-publish
```

Or set `mode = "auto"` and no gate is raised at all.

## What it needs, and what it refuses

- `git` and the GitHub CLI `gh`, **logged in**. If one is missing, the job parks on an
  `engine_misconfigured` gate that says which: fix it and answer anything to retry. vibey does
  not pass `GH_TOKEN` or `GITHUB_TOKEN` to `gh`.
- A work item can write the repository's own git config, and a push runs whatever that config
  names. So publishing refuses a repository whose config sets any of `core.sshCommand`,
  `core.gitProxy`, `core.askPass`, `core.pager`, `core.editor`, `core.hooksPath`,
  `core.fsmonitor`, a `credential...helper`, or a remote's `receivepack`, `uploadpack` or `vcs`,
  naming the key to remove. It runs git with hooks off (`core.hooksPath` set to the null device)
  and `core.fsmonitor=false`, and it refuses a remote that is not an https or ssh address.
- It does not decide where the work goes: the checkout's remote does. In `interview` mode, read
  the remote in the prompt. `auto` and `--auto-publish` trust the checkout's remote, so use them
  on repositories you control.
- It publishes to GitHub only. The project's sovereign default forge is self-hosted Forgejo
  (sub-doctrine 8.b), and `vibey-gh` has a Forgejo adapter for its own work, but vibey's
  publisher speaks only to GitHub through `gh` today.

## What it records

`PublishCompleted` (kind, URL, branch, draft, visibility) or `PublishSkipped` (the reason) goes
on the ledger. The [published form of the ledger](ledger-publication.md) keeps `kind`, `draft`
and `visibility`, and `reason` for a skip. It leaves out the URL and the branch, because a private
repository's address is yours to share.

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| An `engine_misconfigured` gate saying `gh is not logged in: run gh auth login` | `gh auth status` failed. | Run `gh auth login`, then answer the gate with anything to retry. |
| An `engine_misconfigured` gate saying `the GitHub CLI (gh) is not installed` | `gh` is not on the path. | Install it from cli.github.com, then answer the gate. |
| `the origin remote (...) is not an https or ssh address, so nothing is pushed to it` | The remote is a local path or another scheme. | Point the remote at an https or ssh address, or answer `skip`. |
| Publishing refuses and names a key such as `core.sshCommand` | The repository's git config names a command git would run. | Remove that key from the repository's config, then retry. |
| Your `custom` answer is refused and the gate asks again | A field is not one of the eight, or a value is invalid. | Read the message, fix the field, answer again. |
| `branch ... does not exist ...: nothing was integrated to publish` | The run produced no integration branch. | Check the run with `vibey status`; there is nothing to publish yet. |

## Where next

- [What gets published](ledger-publication.md), to see what of the ledger can leave your machine
  and what never does.
- [Review AI changes before they merge](outcomes/review-ai-changes-before-merge.md), for how the
  pull request is then reviewed and merged.
- [`[publish]` in the configuration reference](../reference/configuration.md#publish), for the
  exact keys.

## Say it in one line

vibey posts finished work only when you say so: a draft pull request or a private repository,
off by default, and silence publishes nothing.
