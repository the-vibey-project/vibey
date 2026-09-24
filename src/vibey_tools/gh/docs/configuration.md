# Configuration reference

Configuration lives in `.vibey-gh.toml`. Every key is optional; omitted values use the
defaults below. Paths are repository-relative unless stated otherwise.

## `[fingerprint]`

| Field | Type / default | Meaning |
|---|---|---|
| `text` | string / built-in provenance sentence | Required source-header text. |
| `trailer` | string / `Made-With: ...` | Required commit trailer. |
| `sources` | string list / Python and workflow globs | Files checked for headers. |

## `[version]`

| Field | Type / default | Meaning |
|---|---|---|
| `files` | string list / empty | Version-bearing files updated by `version --apply`. |
| `content_paths` | string list / empty | Paths whose changes produce a minor bump. |
| `code_paths` | string list / `["src/"]` | Paths whose changes produce a patch bump. |

## `[branches]`, `[merge_train]`, and `[install]`

| Field | Type / default | Meaning |
|---|---|---|
| `branches.integration` | string / `develop` | Integration and preview branch. |
| `branches.release` | string / `main` | Production branch; managed automation never deletes it. |
| `merge_train.owner` | string / empty | Normalized repository-owner login. |
| `merge_train.trusted_authors` | string list / empty | Authors whose green pull requests the merge train may merge unattended (the owner is always included). Every other author's pull request is held "needs a human merge" whatever its gates and reviews say (ADR-0053); a bot matches either spelling (`app/x` or `x[bot]`). Distinct from `[unattended_approval] authors`, which says whom a delegated approver may act for. |
| `merge_train.restack_conflicts` | boolean / `true` | Let the train merge the integration branch into a conflicting or behind head itself, locally, before reporting it as stuck. GitHub computes mergeability without this repository's `.gitattributes`, so a path declared `merge=union` (see `install.union_merge_paths`) is called a conflict there and resolves here. The restacked pull request merges on the NEXT train run, once its checks have re-run against the tree that now exists. Forks are never written to, whatever this is set to. `false` reports the conflict and leaves it to a person. |
| `merge_train.protected_paths` | string list / empty | Paths the train never merges unattended. A pull request that touches one — or whose changed files it cannot list completely — is reported `needs a human merge` instead of merged, because the train's fallback to `gh pr merge --admin` would bypass the code-owner review a ruleset asks for (see `require_code_owner_review`). Shell-style globs matched case-sensitively against the whole repository-root path, where `*` also crosses `/`: `tests/live/*` protects that whole tree. A rename counts as a change to its old path too. The list comes from the paginated REST files endpoint and is checked against GitHub's own `changedFiles` count, so a truncated listing refuses rather than passes. A promotion from the integration branch is exempt: everything it carries already merged there under this check. Entries must be unique and non-empty, and a leading `/` (the CODEOWNERS habit) is refused at load because no listed path starts with one. Empty protects nothing — the behaviour before this key existed. |
| `install.workflows` | string list / all managed workflows | Exact managed subset; `[]` installs hooks and CLI assets only. |
| `install.union_merge_paths` | string list / `["CHANGELOG.md"]` | Files declared `merge=union` in `.gitattributes`, so two branches appending to the same section merge instead of conflicting. Appended to an existing `.gitattributes`, never rewriting it. `[]` declares none. |
| `install.self_source` | string / `"."` | Where a repository that **is** the tooling keeps its own copy, for the workflows that install it. Declared rather than discovered on purpose: a workflow that searched the tree for a `pyproject.toml` declaring `name = "vibey-gh"` would be reading a pull request's own files, and a branch that adds one anywhere would get it installed with that job's permissions. The rendered workflows verify the path before using it and fall back to the published release if it does not hold the tooling. It also anchors `automation-bootstrap.yml`'s change scope: `gh pr diff` reports repository-root paths, so a vendored copy's automation-core files are admitted under this prefix and nowhere else. |
| `install.fallback_package` | string / `"vibey"` | The distribution the managed workflows install when `self_source` does not hold the tooling — the branch every adopter takes, since their `self_source` default `"."` never matches. A key rather than a constant so a fork, or an internal index publishing under another name, can point it at their own distribution instead of one they cannot publish to. It is the package `pin_version` pins. |
| `install.pin_version` | boolean / `false` | Pin every managed workflow's `pip install vibey` — the distribution that carries `vibey-gh` — to the exact version that rendered it (`vibey==X.Y.Z`), instead of the latest release on every run. `false` keeps the historical floating install. That version is knowable in two places: in the repository that IS `fallback_package`, its own `[project] version`; everywhere else, the installed `fallback_package` release the running `vibey-gh` came from, so `uvx --from vibey==X.Y.Z vibey-gh install` renders `vibey==X.Y.Z`. An editable or other source-tree install names no release — its templates may be ahead of the number it carries — so there the fallback stays floating and `install` and `check` print a `notice:` saying why. The self-hosting path (this repository, and anything else installing from its own `pyproject.toml`) is never pinned — it installs from source regardless. Running `vibey-gh install` from a newer release moves the pin forward as one visible diff. |

## `[platform]`

Which forge the repository lives on, and where. `kind` chooses the forge adapter: the only
code that knows which platform it is speaking to, so everything above it asks forge-neutral
questions ([ADR 0001](adr/0001-forge-neutral-nouns.md), #138).

| Field | Type / default | Meaning |
|---|---|---|
| `kind` | string / `"forgejo"` | The forge. The standard names `github`, `gitlab` and `forgejo`, and every named forge has an adapter today. The sovereign, self-hosted default is `forgejo` (ADR 0002); `github` and `gitlab` are declared-only — an adopter writes the kind explicitly to leave the default. Any unadapted value is refused as unknown. |
| `host` | string / `""` | The forge's host, as a bare host name with an optional port (`forgejo.local`, `ghe.example.com`, `git.internal:8443`); a scheme, path or whitespace is refused. Empty, the selected adapter's own default applies: `forgejo.local` for Forgejo, `github.com` for GitHub (which `gh` assumes on its own, so a `GH_HOST` already in the environment still applies), `gitlab.com` for GitLab. Any non-empty host is handed to the selected adapter's transport. |

Apart from that refusal, which every command makes, only the reads that have moved onto the
adapter use this table today: the open pull request heads and the releases that the
clean-repo survey (`vibey-gh tidy`, `check --ci`) reads.
With the defaults, those run exactly the `gh` command lines, in the same directory and
environment, that they ran before `[platform]` existed.

## `[ai]`

Where every AI step sends its requests. Unset, nothing changes: requests go to Anthropic
exactly as before this existed.

| Field | Type / default | Meaning |
|---|---|---|
| `base_url` | URL / empty | Endpoint override. Empty uses the Anthropic default. Must be `http(s)` and contain no whitespace. |
| `auth_secret` | secret name / `ANTHROPIC_API_KEY` | The repository secret authorising those requests. A name only — never a token; this file is committed. |

### Running the automation somewhere other than Anthropic

Every AI step runs Claude Code, which honours `ANTHROPIC_BASE_URL`. Any gateway serving
the Anthropic Messages API — LiteLLM and similar translate it to Gemini, Qwen, GitHub
Models, a model on your own machine — therefore works without this project learning a
second vendor's request shape:

```toml
[ai]
base_url = "https://your-gateway.example/v1"
auth_secret = "LITELLM_KEY"
```

That secret fills both `x-api-key` and `Authorization`, because Claude Code sends the
former while some gateways read the latter. A gateway must serve `/v1/messages` **and**
`/v1/messages/count_tokens`, and forward the `anthropic-beta` and `anthropic-version`
headers.

One caveat worth testing before you rely on it: the review and repair steps depend on
structured JSON output and tool calls, and translation layers vary in how faithfully they
carry `tool_use` arguments across providers. A provider that mangles them makes the gate
report `review incomplete` rather than approving anything — it fails closed — but the
review is then no longer running. Verify against a real pull request before turning off
the endpoint you trust.

`auth_secret` is validated as a bare secret identifier. It is rendered inside a
`${{ secrets.… }}` expression in a privileged workflow, so a name that could close that
expression is refused at load time.

## `[unattended_approval]`

The operator's grant to a delegated approver (sub-doctrine 12.f, ADR-0049). This is the
**declared** half of the grant, reviewed in a pull request like any other state (12.c). The
**live** half is the repository variable `switch_variable` names (`VIBEY_UNATTENDED_APPROVAL`
by default), which must read exactly `switch_value` (`on` by default); its value is
deliberately not a config key, because withdrawal must need no merge:

```bash
gh variable set VIBEY_UNATTENDED_APPROVAL --body off   # binds from that moment
```

Absence, `off`, empty, malformed or **unreadable** are all refusal. An approver that cannot
read its own authorization has already lost it.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `false` | Whether any delegated approval may be given. Off by default: upgrading vibey-gh is not an act of granting. |
| `branches` | string list / `[]` | Branch globs an approver may act on. Empty is refused when `enabled` — a grant naming no branch says nothing, and silence is not consent (12.d). |
| `authors` | string list / `[]` | Forge logins whose pull requests an approver may act on. Empty is refused when `enabled` — a grant that names nobody authorises nobody, and the absence of a grant is refusal rather than permission (12.f). The entry `@codeowners` expands to every login `.github/CODEOWNERS` names, `@` stripped, in order and without duplicates, so the allowlist and the owners of the protected paths cannot drift apart by one of them being edited alone. |
| `forbidden_paths` | string list / the corpus, this file, `.claude/settings.json`, `.github/**`, `CODEOWNERS` | Paths no delegated approval may ever touch. A change touching one is refused **whole** — an approver does not approve the safe subset of a pull request. Must contain `.vibey-gh.toml`, enforced: an approver may never approve a change to its own grant. |
| `require_all_gates` | boolean / `true` | Every deterministic gate must already be green. A delegated approval is added to the gates and never substituted for one. |
| `switch_variable` | string / `"VIBEY_UNATTENDED_APPROVAL"` | The repository variable holding the live switch. Declared rather than compiled in (12.h); it must be a valid variable name — a switch nobody can set is a grant nobody can withdraw. |
| `switch_value` | string / `"on"` | The exact value the switch must read. Compared byte for byte, so `On`, `on ` and an empty variable all refuse; surrounding whitespace is rejected when the configuration loads. |

`vibey-gh approve-check PR` is what reads both halves: it exits `0` only when every condition
above holds for that pull request, and prints each one that does not
([CLI reference](cli.md)). The delegated approver runs it first and refuses on a non-zero exit,
so none of these conditions rests on a model remembering to apply it.

`authors` is the bound `branches` cannot express: a branch glob says nothing about who pushed
to it. A repository with no `.github/CODEOWNERS` expands `@codeowners` to nothing rather than
failing to load — safe only because it fails closed. Both "no CODEOWNERS file" and "CODEOWNERS
names nobody" leave the allowlist empty, and an empty allowlist authorises nobody, never
everybody; an enabled grant left with no authors is refused outright.

Choosing `forbidden_paths` is the other half of the design when `branches` is wide. The test for an
entry is whether a change there could alter **what a gate measures**, **who may approve**, or
**what an agent may do**. Two that are easy to miss: `.github/workflows/**` is *generated*, so
forbidding only the rendered copy leaves every gate editable through its templates; and
`pyproject.toml` carries the coverage floors and pytest's `addopts`, so a one-line edit there is
a gate change wearing a dependency's clothes.

## `[pr_automation]`

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Enable event-driven evaluation, review, repair, and gating. |
| `scan_workflows` | string list / CI, Provenance, CodeQL, Docs, Conventional Commits | Workflow names that trigger evaluation. Every name must be a workflow with a `pull_request` or `pull_request_target` trigger — one that only runs on `push` can never complete for a pull request, so `state` never leaves `pending`, the gate never publishes, and — made a required check — no pull request can ever merge. `vibey-gh check` fails on any named workflow that exists but cannot fire for a pull request; a name absent from `.github/workflows/` is not an error. |
| `ignored_checks` | string list / orchestration checks | Checks excluded from the ordinary rollup. Own checks are always ignored. Also subtracted from `[rulesets.integration] required_checks` to give the gates `automation-bootstrap.yml` waits on. |
| `max_repair_attempts` | integer / `3` (1–10) | Repair budget per contributor lineage. |
| `model` | string / `claude-sonnet-5` | Review and repair model. |
| `review_untrusted_authors` | boolean / `true` | Require exact-head outside-author review. |
| `repair_untrusted_authors` | boolean / `true` | Permit constrained outside-author repairs. |
| `replace_fork_prs` | boolean / `true` | Repair forks through linked repository-owned PRs. |
| `retain_schedule_backstop` | boolean / `true` | Retain scheduled recovery beside event triggers. |
| `normalise_commit_subjects` | boolean / `true` | Whether `Conventional Commits` REWRITES a nonconforming subject or only reports it. The automatic form is `chore: <the original subject>`, which conforms without choosing a type — so a fix normalised this way is filed as a chore. Set it `false` where the author should pick the type; the check still runs and still fails the pull request. |
| `plugin_marketplaces` | string list / empty | Claude Code plugin marketplaces loaded by the review, repair, and conflict-resolution jobs. Each entry is an `https://` Git URL, or a repository-relative path resolved inside the trusted checkout of the default branch (never the pull request's own tree). Empty by default: a marketplace that cannot be cloned fails the review outright. |
| `plugins` | string list / empty | Plugins those jobs install, each `<plugin>@<marketplace>`. Requires at least one `plugin_marketplaces` entry. |
| `paid_review` | boolean / `false` | The declaration [sub-doctrine 8.b](doctrines.md) asks for before the exact-head review reaches a paid model: may the `review` job call `anthropics/claude-code-action` with `[ai] auth_secret` (by default `ANTHROPIC_API_KEY`)? **False by default**, because 8.b makes a paid counterparty declared-only — undeclared means sovereign only. See [the paid-review declaration](#the-paid-review-declaration-paid_review) below. Must be a TOML boolean; a string or a number is refused when the file is loaded. |
| `paid_repair` | boolean / `false` | The same declaration for the `repair` job, which hands failing scans (or a declared paid review's findings) to the paid model to edit the branch. Undeclared, the job — and `mirror-fork`'s repair case — is never scheduled, and the gate reports failing scans as `PR review: needs a human (failing scans)`, ending `needs a human: automated repair needs a paid model, and none is declared (8.b).` A declared paid review's findings are then reported with that sentence too, never with a promise that repair will address them. |
| `paid_conflict_resolution` | boolean / `false` | The same declaration for the `resolve-conflict` job, which hands a merge conflict to the paid model. Undeclared, the job — and `mirror-fork`'s conflict case — is never scheduled, and the evaluation's step summary says `needs a human: automated conflict resolution needs a paid model, and none is declared (8.b)` (the gate publishes nothing for a conflict). |

### The paid-review declaration (`paid_review`)

Every pull request needs one automated verdict on its exact head before the merge train
will take it: that is the `PR review / gate` check. Who gives that verdict is this key's
whole question.

**Undeclared (`false`, the default).** No paid model is asked anything. The
[sovereign lane](#pr_automationfallback) — a local model on a runner you own — answers the
**whole** review: the verdict on the diff (`pass`, `summary`, `findings`) *and* the sixteen
documentation-contract judgments. It is offered for exactly one kind of pull request: a
**trusted author** (the owner or `[merge_train] trusted_authors`) whose head is **in this
repository**, while the lane is switched on and its heartbeat is fresh. The local model is
handed the diff and the pages listed in `[pr_automation.fallback] context_paths`, fetched
read-only at the exact head, and its verdict says so: its summary begins
`[SOVEREIGN LANE — <model> — whole review]` and names the documents it judged against,
because this is a judgment of the change, not a repository-wide audit. The paid `review`
job is skipped before GitHub schedules it, so nothing on that path reads the API secret.

Every other pull request gets **no automated pass**. The gate fails and says why, in these
words:

| The pull request | What `PR review / gate` says |
|---|---|
| comes from a fork | `needs a human review: the head is in a fork (<owner/name>), which never reaches the self-hosted sovereign runner (no paid review is declared, 8.b).` |
| has an author who is not trusted | `needs a human review: the author is not a trusted author of this repository, and the sovereign lane reviews trusted authors only (no paid review is declared, 8.b).` |
| arrives while the lane is off | `needs a human review: the sovereign lane is switched off ([pr_automation.fallback] enabled = false) (no paid review is declared, 8.b).` |
| arrives while the runner is down | `needs a human review: the sovereign lane is not ready: <the heartbeat probe's own reason> (no paid review is declared, 8.b).` |
| was reviewed, but the model gave no verdict | `needs a human review: the sovereign lane produced no verdict: <its reason — an unreachable model, an unusable answer, a diff or page that could not be fetched> (no paid review is declared, 8.b).` |

The last two are titled `PR review: review incomplete (needs a human review)`, so the
scheduled recovery sweep re-probes them once the runner beats again; the others are titled
`PR review: needs a human review`. A whole review that fails reports its findings (or, with
none, that it returned `pass=false` without one) and is **never** handed to automated repair:
a local model's finding is a lead for a person to check, and repair is itself a paid agent.
The merge train already holds any pull request from an author outside `trusted_authors` for a
human merge (ADR-0053), so this is the same rule seen from the review side.

**Declared (`true`).** The two-lane review, exactly as before this key existed: the
sovereign lane carries the diff half for a trusted author and the paid reviewer answers the
documentation-contract half; for anyone else the paid reviewer answers the whole review and
the local verdict is held in reserve (see [`[pr_automation.fallback]`](#pr_automationfallback)).

**A refused paid call is named as one.** When the API refuses a paid call — an exhausted
credit balance, a revoked key — `claude-code-action` still ends with `Result subtype:
success`, which is false. The review, repair and conflict-resolution jobs read the
execution record instead: when it carries `is_error`, the step fails with `the paid
<review|repair|conflict resolution> was refused by the API: <the API's text, or "no reason
given">`, and the gate repeats that sentence rather than a bare job result.

**One key per paid use.** `paid_review`, `paid_repair` and `paid_conflict_resolution` each
declare one job, the way `review_untrusted_authors` and `repair_untrusted_authors` split the
same two jobs by author: whether a paid model may *judge* a change and whether it may *edit*
the branch are different questions, and a repository may answer them differently. With all
three false — the default — no job in `pr-review.yml` that references the paid model or its
secret can be scheduled, so the `[ai] auth_secret` repository secret can be deleted.

### `[pr_automation.observability]`

| Field | Type / default | Meaning |
|---|---|---|
| `sanitized_progress` | boolean / `true` | Request safe action progress only for Claude-supported direct PR/issue events; automated workflow events retain phase-level job visibility. |
| `archive_execution_file` | boolean / `true` | Retain each Claude execution record as a 90-day workflow artifact. |
| `allow_private_full_output` | boolean / `false` | Permit an explicit manual diagnostic run to emit raw Claude JSON, but only in a private repository. |

Raw output additionally requires a manual `workflow_dispatch` with
`full_claude_output = true`. Event-triggered runs can never enable it, and the workflow
fails closed when repository visibility is not private.

### `[pr_automation.fallback]`

The sovereign review lane: a local model on the operator's own runner. With no paid review
declared (`paid_review = false`, the default) it answers the **whole** review for a trusted
author, as [described above](#the-paid-review-declaration-paid_review). The rest of this
section describes the declared path (`paid_review = true`), where it reviews the
**diff-groundable half** of every pull request's exact-head review (`pass`, `summary`,
`findings`) FIRST, whenever its heartbeat is fresh (sub-doctrine 8.a, #133). The table keeps
its original name because it began as a fallback, and it still is one: the same verdict is
what the gate reads when the paid path returns **no verdict at all** — an exhausted API
key, expired credentials, an unavailable model. Because the gate is a required check, that
failure otherwise turns a billing problem into a hard stop on every pull request.

Whose review it carries is decided per pull request. For a **trusted** author (the owner or
`trusted_authors`) in this repository, the local verdict carries the diff half and the paid
reviewer answers only the sixteen documentation-contract judgments, reporting its own prose
and findings as `wider_summary` and `wider_findings`; the gate names the lane behind each
half. For **any other** same-repository author the local verdict is held in reserve: the
paid review still covers the whole change, including its correctness and security review,
and the local verdict is read only if that review returns no verdict. A fork never reaches
the lane while `trusted_only` is on.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Whether the sovereign fallback job (`review-sovereign`) can run at all. **On by default, per sub-doctrine 8.a:** the sovereign path is the preference, so it is not the one that has to be opted into. That costs an adopter nothing until they stand a runner up, because the **heartbeat** gates scheduling rather than this flag — a repository with no fresh `heartbeat_ref` never offers the lane. Once a runner does exist, keep `trusted_only` true: GitHub says self-hosted runners should "almost never be used for public repositories". |
| `runner_label` | string / `"vibey-local"` | Label the sovereign job targets, alongside `self-hosted`. |
| `model` | string / `"gpt-oss:20b"` | Model tag served by the Ollama-compatible endpoint. |
| `base_url` | string / `"http://127.0.0.1:11434"` | Where the local model listens. |
| `trusted_only` | boolean / `true` | Never run the sovereign lane for a fork pull request. |
| `heartbeat_ref` | string / `"refs/vibey-gh/sovereign-heartbeat"` | The git ref `vibey-gh sovereign --beat` publishes to and the workflow reads back, so "is the local lane alive?" is answered by something the lane itself had to write. |
| `heartbeat_max_age_minutes` | integer / `15` | How stale that heartbeat may be before the local lane is treated as down. A ref that stopped moving is indistinguishable from a runner that stopped, which is the point — both mean do not route work there. |
| `max_diff_chars` | integer / `60000` | For the diff half, a diff longer than this is **refused**, never cut: a verdict on part of a diff would pass the rest unread, so the gate asks a human. A **whole** review (no paid review declared) never cuts the diff either: it is shown the whole diff or refused. It never bounds the documents; `max_document_chars` does. |
| `max_document_chars` | integer / `120000` (at least 1000) | The most characters of `context_paths` documents a whole review is shown, whatever the window would allow. The documents' own limit, never the diff's: when they shared `max_diff_chars`, this repository's two pages already took 59,607 of its 60,000, and a few hundred more characters of README cut a page, so every pull request's review claimed the diff half alone and its gate asked a human. The default is about twice what those pages hold today; the window is what usually binds. |
| `context_window` | integer / `65536` (4096–1048576) | The model's context window in tokens, **as your host measured it**: every local request is sized from everything it sends (system prompt, user prompt, schema) and must fit inside it beside `reasoning_reserve_tokens`. A request that does not fit is **never sent**. Left to its defaults Ollama does not refuse an oversized prompt: it cuts it to about half the window and the model answers about the rest, with no error (measured on Ollama 0.34.2 with `gpt-oss:20b` at a 32,768 window: a 36,798-token request was read as 16,386 tokens). So every request is also sent with `truncate: false` and `shift: false`, which makes Ollama 0.34 refuse it with HTTP 400 — reported as `the model server refused the request (HTTP 400): …`, never as an unreachable model — and carries two random check codes, one at each end of the prompt, that the answer must echo; a reply that does not echo both is refused. A whole review first leaves out optional documents (the last in `context_paths` first, and the verdict names them); if the diff alone does not fit, the lane refuses with `the diff (~N tokens) exceeds the sovereign model's window (M tokens) once its ~S tokens of instructions and the R-token reasoning reserve are counted`, and the gate asks for a human. The default is what this repository's host tuning chose for `gpt-oss:20b`. |
| `reasoning_reserve_tokens` | integer / `8192` | Tokens kept free for the model's reasoning **and** its answer; at least 1024 and under half of `context_window`. A reasoning model thinks before it answers: on #1090's whole review `gpt-oss:20b` spent 3,676 tokens doing both at its default effort. After each call the lane also reads Ollama's own `prompt_eval_count`, and refuses the reply if the model read more than the request was sized for — an estimate that let too much through — and reads `done_reason`, so a model that ran out of room is reported as `the model ran out of room (done_reason=length, N reasoning chars, M answer chars)`, never as a JSON error. |
| `chars_per_token` | integer / `3` (1–8) | Characters per token when estimating a prompt. Pessimistic for prose and code (#1090 measured 3.95 for `gpt-oss:20b`), but optimistic for dense text — a lockfile tokenizes at about 2.1, hex 1.9, base64 1.5, CJK 1.4, emoji 0.7 — which is why the estimate only decides what to trim, and the request itself refuses truncation. |
| `think` | string / empty | The reasoning effort sent to the model as Ollama's `think`: `low`, `medium` or `high`, or empty to send nothing and keep the model's default. Empty by default. On #1090's whole review `low` returned the same verdict in 471 tokens (default: 3,676) and 103s (243s) — one sample, not a fidelity study. |
| `timeout_seconds` | integer / `600` | Bound on one review. |
| `context_paths` | string list / `["README.md", "docs/index.md"]` | With no paid review declared, the pages the whole review judges the documentation contract against — fetched read-only through the contents API at the exact head, never checked out, and handed to the model beside the diff. A page absent at that head is skipped and the verdict names the pages it did see; any other fetch failure stops the review. Each entry must be a plain repository-relative path: no leading `/` or `~`, no `..`, no whitespace, no glob or query characters. Their text is bounded by `max_document_chars` and by what the window leaves beside the diff, and the **last declared gives way first** (the workflow passes this order as `--context-paths`). The model is told, by name, which were cut short or left out — and because the documentation judgments were then made against less than you declared, the verdict claims the diff half alone and the gate asks a human. |

It never overrides a judgment the paid lane made: when the local verdict carries the diff
half, the paid reviewer is not asked that half at all, and when it is held in reserve it is
read only if the paid review produced no verdict — so findings are never discarded in
favour of a weaker opinion. A local finding is never handed to automated repair: the gate
points a human at it, and a later evaluation of the same head reviews it again. The diff is
passed to the model as text — repository code is never executed, and the model has no
shell, no tools, and no network beyond the local port.

The lanes run **serially**: the paid review waits for the local one, because which half it
answers depends on what the local lane returned. That costs the local review's latency
(bounded by `timeout_seconds`) on every pull request the lane is offered for. A heartbeat
that goes stale after the lane was offered leaves the job queued until GitHub times it out,
and the paid review waits with it; keep `heartbeat_max_age_minutes` short.

Fetching that diff prefers `gh pr diff`, but GitHub's diff API refuses pull requests beyond
roughly 300 changed files — exactly the shape of a large migration or adoption sweep, which
would otherwise never be reviewable at all. When the API refuses, the job reconstructs the
same merge-base diff locally instead: it fetches the base and head refs, deepening a shallow
trusted checkout until their histories connect, and diffs one against the other. That
reconstruction is read-only and executes no repository code, so the guarantee above holds
either way, and a diff past `max_diff_chars` is still refused rather than cut.

The verdict is deliberately narrower than the primary review's. Ollama constrains decoding
to the schema, so the output *shape* is guaranteed; the *judgments* are not, and a 14B model
will emit confident booleans it has no basis for. So it assesses only what it can ground in
a diff — `pass`, `summary`, `findings` — and reports the documentation-contract fields as
unevaluated. Its summary names the role it ran in (`[SOVEREIGN LANE — model]` or
`[LOCAL FALLBACK — model]`), and the gate titles a split verdict
`PR review: gate (diff: sovereign lane, documentation: paid lane)` and a fallback one
`PR review: gate (local fallback)`, so a narrower verdict is never mistaken for a full
one.

`trusted_only` carries the safety argument. GitHub says self-hosted runners should "almost
never be used for public repositories" because any user can open a pull request against
them; excluding forks is what removes that. Leave it on, register the runner as ephemeral
so it takes one job and exits, and run it in a container rather than on the host.

## `[runners]`

The machine that serves the sovereign lane, declared rather than hand-made (sub-doctrine
12.c). `vibey-gh runner install` renders the runner's LaunchAgent, supervisor, Dockerfile and
container entrypoint from this table and the templates in `vibey_gh/templates/runner/`;
`vibey-gh runner check` reconciles the host against them; `vibey-gh runner cleanup` finds
agents under `unit_prefix` that the tree no longer declares. The runner label is
`[pr_automation.fallback] runner_label` and the host-side model URL is its `base_url`; neither
is declared twice. The supervisor is macOS-only (launchd, `caffeinate`, `pmset`). The
operator's steps are in the vibey repository's `docs/runbooks/sovereign-review-runner.md`.

| Field | Type / default | Meaning |
|---|---|---|
| `repository` | string / `""` | `owner/name` the runner registers with. Empty derives it from `[platform] repository`. `[platform] kind` must be `github`: this is a GitHub Actions runner. |
| `unit_prefix` | string / `"org.vibey.runner"` | The LaunchAgent label is `<unit_prefix>-<repository name>`. Every agent under the prefix that is not that label is what `runner cleanup` lists. |
| `install_dir` | path / `"~/.local/share/vibey-runner"` | Where the supervisor, Dockerfile and entrypoint are installed. Retired agents are moved into its `retired-units/`. |
| `launch_agents_dir` | path / `"~/Library/LaunchAgents"` | Where the LaunchAgent plist is written. |
| `log_dir` | path / `"~/Library/Logs"` | The supervisor logs to `<log_dir>/<label>.log`. |
| `gh_config_dir` | path / `"~/.config/gh-runner"` | The runner's **own** gh login, set as `GH_CONFIG_DIR` in the LaunchAgent. It must be a file-based login (`gh auth login --with-token --insecure-storage`) holding a fine-grained token for `repository` only, with **Administration: Read and write**. gh's default directory (`$XDG_CONFIG_HOME/gh` or `~/.config/gh`) is refused however it is spelled, compared after resolving `~`, `..` and symlinks, both when the configuration loads and by the supervisor: its token is in the macOS keyring, which launchd cannot read. The supervisor refuses to start on a missing, keyring-held, unreadable-to-launchd or group/world-readable login, clears `GH_TOKEN` and `GITHUB_TOKEN`, and never falls back to another credential. |
| `image` | string / `"vibey-runner:latest"` | The runner image the supervisor starts one container of per job. |
| `runner_version` | `X.Y.Z` / `"2.337.0"` | The actions/runner release the image is built from (`--build-arg RUNNER_VERSION`); the Dockerfile carries no default. |
| `container_model_url` | URL / `"http://host.docker.internal:11434"` | The model endpoint as the container sees it. |
| `require_ac` | boolean / `true` | Stay down on battery rather than hold a laptop awake to idle-poll. |
| `throttle_seconds` | integer 10–3600 / `120` | launchd's `ThrottleInterval` between restarts. |
| `max_failures` | integer 1–100 / `5` | Consecutive runner failures before the supervisor stops rather than spins. |
| `path` | string / Homebrew then system paths | The `PATH` launchd gives the supervisor; `docker` and `gh` must be on it. |

## `[conversation]`

Answers a mention in a comment on an issue or pull request. Comments are the least guarded
input a repository has, so the defaults are closed.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Respond to mentions at all. |
| `trigger` | string / `@vibey-gh` | The mention that addresses the automation. Matched on a word boundary, so `@vibey-gh-bot` is not a mention. |
| `model` | string / `claude-sonnet-5` | Model that reads the thread and answers. |
| `max_interactions` | integer / `10` (1–100) | Responses per thread, so a conversation cannot become an unbounded work queue. |
| `respond_to_untrusted` | boolean / `false` | Answer commenters outside the owner/trusted set. A response costs tokens, so answering everyone is a deliberate spending decision. |
| `allow_changes` | boolean / `true` | Permit file changes. Only ever on a pull request, only from a trusted commenter, and never on a fork or permanent branch. |
| `ignore_actors` | string list / the automation's own bot identities | **The loop guard.** Its own reply mentions the trigger too; answering it would run and bill forever. Cannot be empty while enabled. |

An issue is answered in words only — there is nowhere to put a commit. A pull request from
a trusted commenter may also receive one guarded commit on its own branch.

## `[branch_sync]`

Keeps open branches current so conflicts never accumulate, and refills a spent repair
budget a bounded number of times so a transient outage does not become a permanent stop.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Run the sync and self-heal jobs at all. |
| `update_contributor_branches` | boolean / `true` | Merge the integration branch forward into branches this automation does not own, using GitHub's own update-branch endpoint. Never a rewrite. |
| `max_self_heals` | integer / `2` (0–10) | How many times one lineage's repair budget may be refilled before it stays exhausted for a human. `0` disables self-healing. |

A fork is only ever moved *forward*, never rewritten: `update-branch` succeeds only where
the contributor left "allow maintainer edits" enabled, so it carries their consent.
Rebasing, closing, and deleting are unreachable for a fork under every setting.

## `[realign]`

Realign converges the integration branch onto the release branch with a lease-protected
force update, which replaces commits with rewritten copies and strands any topic branch cut
from one of them. These keys decide how much the automation may do about that unaided.

| Field | Type / default | Meaning |
|---|---|---|
| `reconcile_branches` | boolean / `true` | Reconcile open pull-request branches after a realign rewrite. |
| `automation_prefixes` | string list / `["vibey-gh/"]` | Branch prefixes this automation may rebase on its own. Everything else is a human's to rebase. |
| `close_duplicates` | boolean / `true` | Close a pull request whose every commit is already upstream by patch identity. |
| `delete_duplicate_branches` | boolean / `true` | Delete that branch too. Permanent, fork, and unsafe refs are refused by name regardless. |
| `notify_contributor_branches` | boolean / `true` | Comment on a human's stranded branch with the rebase command instead of rewriting it. |

Decisions use `git cherry`, which compares by patch identity, so a commit re-created
upstream under a new SHA is correctly recognised as already present. A ref that cannot be
read reports unique work rather than none, so an unreadable branch is never closed.

## `[issue_automation]`

Turns a published issue into a reviewable pull request. Every field exists because an
adopting repository could reasonably disagree with the default; the defaults themselves are
closed, because anyone with a GitHub account can open an issue.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Enable evaluation and autonomous solution proposals. `false` keeps the workflow installed and inert. |
| `model` | string / `claude-sonnet-5` | Model used to design and implement the proposed solution. |
| `max_attempts` | integer / `2` (1–10) | Solution budget per issue content lineage. |
| `max_turns` | integer / `200` (1–1000) | Turn budget for one attempt. An attempt that exhausts it produces nothing, so raise it for a repository whose issues are routinely large — or split the issue, which is usually the better answer. |
| `branch_prefix` | string / `vibey-gh/issue` | Namespace every proposal branch lives under. Validated against the configured permanent branches and rendered into `branch-intake.yml`'s ignore list. |
| `base_branch` | string / empty | Branch a solution is built on. Blank uses `branches.integration`. |
| `solve_untrusted_authors` | boolean / `false` | Permit issues from outside the owner/trusted-author set without a maintainer label. |
| `required_label` | string / `vibey-gh:solve` | Label that opts an outside author's issue in. Empty disables that path entirely. |
| `trigger_labels` | string list / empty | When set, only issues carrying one of these labels are ever attempted. |
| `ignored_labels` | string list / question, discussion, duplicate, wontfix, `vibey-gh:solve-blocked` | Issues carrying one of these are never attempted, whoever wrote them. |
| `open_pull_request` | boolean / `true` | Open a linked pull request after publishing the branch. |
| `draft_pull_request` | boolean / `true` | Open that pull request as a draft, letting PR automation promote it when its exact head is green. |
| `retain_schedule_backstop` | boolean / `true` | Retain the scheduled recovery sweep beside the event triggers. |
| `fallback_enabled` | boolean / `true` | Post a bounded local-model triage comment when the paid solve produced nothing — the issue path's counterpart to `[pr_automation.fallback]`, sharing its runner, model, and limits. The triage writes no code, deduplicates itself to one comment per issue, and forces `needs_human` true whatever the model claims. **On by default, per sub-doctrine 8.a**, like `[pr_automation.fallback] enabled`, and for the same reason it costs a repository without a runner nothing: the sovereign heartbeat, not this flag, decides whether the job is scheduled, and a repository with no fresh `heartbeat_ref` never schedules it. Set `false` to never render the job at all. |

An issue's attempt budget is keyed to a SHA-256 fingerprint of its title and body, so
re-running automation on unchanged text cannot spend the budget twice and editing the issue
starts a fresh lineage. Managed labels are `vibey-gh:solve`, `vibey-gh:solving`,
`vibey-gh:solution-proposed`, `vibey-gh:solve-exhausted`, and `vibey-gh:solve-blocked`.

### Documenting your project, not this one

A repository that installs vibey-gh documents **its own product**. It is still held to the
agent-docs *layout* — those files describe the adopter's project and make it navigable to an
agent — but nothing about their contents describes vibey-gh: no `## Why vibey-gh` heading in
their product README, no branded provenance sentence, no architecture surfaces named after
this tool's modules.

Every entry in `required_files` is required: having one never excuses another.

| Field | Type / default | Meaning |
|---|---|---|
| `required_files` | string list / the agent-docs layout | Files that must exist and be non-empty, each one individually. |
| `require_roadmap` | boolean / `true` | The living-roadmap doctrine (#211): `docs/roadmap.md` or `ROADMAP.md` must exist and be non-empty until the project's goal is reached and its humans declare it done. Opting out silences only this deterministic presence check — the exact-head review still judges roadmap liveness against the release history. |
| `readme_sections` | string list / empty | Headings required in `README.md`, in your own words. |
| `automation_doc` | path / `.github/AUTOMATION.md` | Where this repository's automation documentation lives. **Not `.github/README.md`** — GitHub resolves that as the repository's landing README ahead of the root one, so naming it that replaces your product README on your repository's front page. |
| `automation_doc_sections` | string list / empty | Headings required in `automation_doc`. Also read from the former name `github_readme_sections`. |
| `automation_doc_min_words` | integer / `0` | Minimum length for `automation_doc`; `0` disables. Also read from the former name `github_readme_min_words`. |
| `mermaid_terms` | string list / empty | Surfaces that must appear in `docs/project.mmd`. |
| `mermaid_min_edges` | integer / `0` | Minimum `-->` edges in that diagram; `0` disables. |
| `require_provenance` | boolean / `false` | Require the Vibey provenance sentence. |
| `provenance_files` | string list / `README.md`, `docs/index.md` | Files checked for the sentence with a loose substring match (must merely contain "Made with" somewhere), skipped if the file does not exist. Independently of this list, `require_provenance` also forces an exact-suffix check — the file must end with the sentence verbatim — on `README.md` and on `automation_doc`, whether or not either appears here. |

This repository declares the full contract for itself in its own `.vibey-gh.toml`, which is
both the dogfooding rule the rest of the tool follows and the reason its own requirements
are visible rather than compiled in.

## The fit calculus — `vibey-gh fit`

Doctrine 10's hardware-decomposition clarification as a running control loop
(#263). `vibey-gh fit` reads **both sides of the fit** — the machine's memory,
free pages, and paging space; the model's actual size and context length, read
from the runner rather than assumed — then states whether a piece of work fits a
deadline, and what headroom the projection wants.

```bash
vibey-gh fit --model qwen2.5-coder:14b --queue 3 --payload-bytes 22000 --deadline 900
```

Three verdicts, each with its arithmetic in the reason:

| Verdict | Meaning |
|---|---|
| `admit` | projected wait + service fits the deadline at the current slots and queue |
| `defer` | it does not fit — decompose the work or wait for a slot |
| `floor` | the model cannot run on this machine at all, or its specs could not be read; **fails loudly**, never silently (doctrine 10) |

The constants come from measurement, never assumption: **s**, effective
parallelism (generation-seconds ÷ wall seconds), and **τ**, service time fitted as
`base + rate × KB` from operations that actually ran. With one payload size the
rate stays zero rather than being invented, and a physically meaningless fit (big
payloads finishing sooner) falls back to the flat mean.

**Nothing here resizes swap by itself.** The projection reports the headroom it
wants; growing paging space is an irreversible act on someone's machine, and
Article III's bounded delegation leaves that to a human.

**Both sides are read from the machine this actually runs on.** macOS is read from
`sysctl` and `vm_stat`; Linux from `/proc/meminfo` — except inside a container,
where `/proc/meminfo` reports the *host's* memory and the process is killed at the
cgroup limit long before it reaches that, so a cgroup limit wins when one exists
(`/sys/fs/cgroup/memory.max` for v2, then `memory/memory.limit_in_bytes` for v1).
A limit of `max`, or one at or above what the host itself has, is not a limit. Every
one of those paths is a default that can be overridden rather than a constant.

**A machine that will not state its own memory is the floor, not an empty machine.**
Zero is the absence of a measurement; reporting it as if it were one is the silent
failure doctrine 10 forbids. When nothing is readable, `vibey-gh fit` says so out
loud and the verdict is `floor`.

**The model is read from the runner the work would go to.** `--base-url`, else the
`VIBEY_OLLAMA_URL` environment variable (the one the fallback workflows already
export), else `[pr_automation.fallback] base_url` (default `http://127.0.0.1:11434`).
In code, `FitLoop(base_url=...)` and `sample_model(name, base_url)` resolve the same
way, with `http://127.0.0.1:11434` as the last step.

**A model that is not loaded is still a model.** Ollama's `/api/ps` lists only the
models currently in memory, so a model the runner holds on disk but has idled out
used to read exactly like one it does not have, and the verdict was `floor`. Now a
model missing from `/api/ps` is looked up in `/api/tags` (everything the runner
holds) and its context length is read from `/api/show`. The size it then reports is
the weights on disk. That is a lower bound, because loading adds the context's KV
cache, and the verdict says so in a note. `floor` means only that the runner does
not hold the model, or could not be read at all.

**The journal is on by default.** Each decision, and each `--observed-seconds`
measurement, is appended to `--journal PATH`, else to `VIBEY_GH_FIT_JOURNAL`, else to
`~/.local/state/vibey-gh/fit.jsonl`. That path sits next to the failover seat's state
because the journal describes this machine's runner, not any one repository. Every
invocation reads back the measurements already there, so separate runs form one
loop. `--no-journal` decides from the one call alone and writes nothing. In code,
`FitLoop(journal=None)` still keeps decisions only in memory. `FitLoop.default_journal()`
and `loop.replay()` are the opt-in.

**One context-sizing rule for every local call.** `local-review` and `local-triage`
both ask Ollama for a `num_ctx` sized to the prompt through `vibey_gh.fit.ContextSizer`:
`prompt_chars // 3 + 2048` tokens, never below 4096 (the server's small default,
into which a large diff context-shifts until it never finishes) and never above
32768 (an enormous request should fail visibly, not exhaust the host). Each of those
four numbers is a constructor keyword with that default, and both calls take a
`sizer=` argument.

Measured on a 24 GB machine running `qwen2.5-coder:14b`: peak throughput
**1.72 generations/min at 6 concurrent**, degrading to 1.27/min at 8 — the
saturation knee, past which added load buys queueing rather than work.

## `[estimate]` and `vibey-gh estimate`

The fit calculus answers one question for one machine: should it take this work now?
`vibey-gh estimate` (#134) asks the wider question from the paper's six-materials
calculus ([The mechanics of the governance dilemma](paper.md)). Before a run, it asks
whether the run can get through **every stage it must pass**, how long it will take,
what it will cost, and how far each of the eighteen coordinates sits from peak.

```bash
vibey-gh estimate --operation develop
vibey-gh estimate --operation main --from develop-validation --json
```

**Two coordinates are measured, and sixteen are `unknown`.** Hardware availability is
the machine's ceiling (memory plus paging, the same ceiling `fit` floors against)
divided by the size of the local model, capped at 1. It is 1 exactly when `fit` would
not declare the hardware floor. Software availability is 1 when the local runner holds
the model, whether loaded or on disk. Every other coordinate is `unknown`, and each one
names what would measure it. None is defaulted to healthy. The reported confidence
drops with each one. It is the fraction of the coordinates on the path that were
actually measured.

**Feasibility is three-valued.**

- `no`: a measured coordinate falls short of a stage's minimum, anywhere on the path.
- `yes`: every coordinate the path requires is measured and meets its minimum.
- `unknown`: anything in between. An unmeasured coordinate cannot produce a `yes`.

The exit status follows the verdict: `0` for yes, `1` for no, `3` for unknown, and `2`
for a stage that does not exist. Shortfalls are listed **agency first**, because a run
that cannot merge is infeasible however healthy the hardware.

**Duration and cost.** The local model's service time is projected from the fit
journal's own observations. The projection uses the same graded estimator that `fit`
uses (`vibey_gh.estimation`), and it states its basis and `n`. No stage timings are
recorded in vibey-gh, so the duration of the stages is `unknown`. Cost is `unknown`,
because no spend measurement reaches this command yet, and a made-up number is worse
than none. The repair ranking is not computed: the gradient `-∇T` needs φ, the dilation
each shortfall imposes, and φ is not measured yet.

**Offline by default.** The command reads this machine's memory. It reads the model
runner only when the runner is on this machine: `localhost`, a `.localhost` name, or a
loopback address. It decides this from the URL's text, because resolving the name would
itself leave the machine. A runner on another host is read only with `--online` or
`offline = false`. The fit journal is read, never written.

| Field | Type / default | Meaning |
|---|---|---|
| `offline` | boolean / `true` | Never leave this machine. A runner elsewhere is not read, and its coordinates stay `unknown` and say why. `--online` overrides it for one call. |
| `model` | string / empty | The local model the fit coordinates are measured against. Empty means `[pr_automation.fallback] model`. `--model` overrides it. |
| `stages` | string list / empty | The pipeline, in order. Empty means the nine default stages: `install`, `interview`, `feature-branch`, `develop`, `develop-deployment`, `develop-validation`, `main`, `main-deployment`, `main-validation`. A stage that is not one of these needs its own `[estimate.requirements.<stage>]` table. |
| `requirements` | table of stage tables / empty | `"material.property" = minimum` per stage, on the 0..1 scale where 1 is peak. A table **replaces** that stage's default vector outright. A table for a stage the pipeline never reaches is an error, and so is an unknown material or property. |
| `report_first` | string list / `["agency"]` | Materials whose shortfalls lead the report, in order. |

```toml
[estimate]
offline = true

# Promotion needs merge rights and a reachable forge, nothing more.
[estimate.requirements.main]
"agency.availability" = 1
"network.availability" = 1
```

By default, each stage gates only the **availability** of the materials it draws on. A
stability or reliability shortfall should dilate duration through φ rather than make
the work impossible, and φ is not measured yet. **Paid credit counts as agency**:
spending is a form of permission to act.

## `[local_models]` and `vibey-gh slots`

How many runs of one local model may run at once on a device is **measured on that
device, never assumed** (sub-doctrines 8.c and 8.j, ADR-0058). A second run of a model
already resident can double throughput, or it can overflow the machine's wired memory,
swap it into the ground, or refuse the deep prompts the first run served. Which of these
happens depends on the model, its context window, the runner and the hardware, so the
answer is a calibration recorded per device, and a declaration is checked against it.

```bash
# A pool of storm-shaped turns: from a storm's own lane records, or its committed specs ...
python docs/plans/qwenstorm-3.0.0/tools/storm_turn_pool.py specs --out pool.jsonl
vibey-gh slots corpus --pool pool.jsonl --out corpus.json --segments 20 --min-per-stratum 5
# ... swept at N = 1, 2, 3, ... beside an idle production runner.
vibey-gh slots calibrate --corpus corpus.json --lock /path/to/.ollama-lock --out evidence.json
# What a queue reads: the number on stdout, the reason on stderr.
vibey-gh slots allowed
```

**The declaration.** `concurrent_runs` is `1` by default: 8.c as written, one run at a
time, which needs no evidence and probes nothing. `"measured"` takes whatever this
device's evidence supports. A number above one runs only if this device's evidence
measured that number inside every bound and faster than one; otherwise **one runs**, and
the refusal names what is missing (`--strict` exits `2` on a refusal).

**The device.** Evidence is keyed to a fingerprint of the hardware model, processor,
memory, accelerator, operating system, runner version, model digest and context window.
Evidence for a device this no longer is (a runner upgrade, another model digest, more
memory) is **stale**, and so is evidence older than `max_evidence_age_days`. Missing or
stale evidence means one, said on stderr, and `slots allowed` writes a calibration
request beside the evidence. `slots calibrate --if-requested` acts on exactly those
requests, so an idle window closes the gap without anyone remembering it: the storm
runner does this itself when its queue empties (`storm-queue.sh`).

**The sweep.** `calibrate` starts its own `ollama serve` on `calibration_port`, with
`OLLAMA_NUM_PARALLEL=N` and `OLLAMA_NOPRUNE`, beside the production runner, which it
never restarts or reconfigures. It waits until the production runner has nothing
resident, and a step during which production loads a model is discarded and measured
again: two resident models bidding for one accelerator is the contention 8.c forbids, so
a reading taken beside one measures the wrong thing. It replays the corpus with N
closed-loop workers through `/api/chat` with `truncate: false` and `shift: false`, so a
prompt the slot cannot hold is a recorded refusal, never a silent loss of its front
half, and a `200` with no `done_reason` (what the runner answers when its decode fails
underneath it) is a failure, not an answer. It samples the host every second: wired
memory (on macOS, `vm_stat`'s wired pages; on Linux, `Unevictable` plus what an NVIDIA
accelerator holds), the free share, swap-ins and swap-outs, and what both runners hold
resident. It reads the runner's own log for slots, context per slot, KV cache sizes,
model loads, truncations, context shifts and device failures. One slot is measured
twice, so fidelity is judged against the model's agreement with itself. The sweep stops
when a bound breaks, or after two consecutive steps without a significant gain. The
**ideal N** is the smallest that reaches the best throughput inside every bound. At one
slot the memory bounds are reported as *floor warnings* and never refuse: one is 8.c's
floor.

**Resumable.** Each completed step is written under `<evidence_dir>/progress/<sweep>`
the moment it finishes, keyed by the device fingerprint, the corpus hash and the replay
method; `--out` gets the evidence so far after every step. An interrupted sweep, run
again with the same arguments, takes the steps it already has and measures the rest, and
`--max-runs` can walk it one step at a time.

**The runner must match.** The evidence records the runner version of every step. A
calibration that ran on a different binary from the production runner's (Homebrew's
`ollama` on `PATH` beside the macOS app's, say) is **not recorded** for this device. Pass
`--binary` or set `ollama_binary`. Running N lanes also needs the production runner
started with `OLLAMA_NUM_PARALLEL` of at least N **and** the calibrated context per slot:
a runner that sizes every slot to its own `OLLAMA_CONTEXT_LENGTH` is not the runner that
was measured.

| Field | Type / default | Meaning |
|---|---|---|
| `concurrent_runs` | integer ≥ 1 or `"measured"` / `1` | How many runs of the model run at once on this device, checked against this device's evidence as above. |
| `model` | string / empty | The model calibrated and gated. Empty means `[pr_automation.fallback] model`. |
| `context_window` | integer / `65536` | The context every slot is calibrated at: the window the loop declares, so every turn fits one slot. Part of the fingerprint. |
| `evidence_dir` | string / empty | Where evidence, requests and checkpoints live. Empty means `$VIBEY_GH_SLOTS_DIR`, else `~/.local/state/vibey-gh/slots`, on the device the evidence describes. |
| `max_runs` | integer / `8` | The sweep's upper limit. It normally stops earlier. |
| `calibration_port` | integer / `11435` | Where the calibration runner listens, beside production. |
| `ollama_binary` | string / empty | The runner binary. Empty means `ollama` on `PATH`, else the macOS app's bundled runner. |
| `lock` | string / empty | A `mkdir` lock held for the whole calibration, shared with anything else that must not use the model meanwhile. `--lock`, then `$VIBEY_OLLAMA_LOCK` (a machine's own convention), then this; empty takes none. |
| `wired_ceiling_fraction` | float / `0.80` | Peak wired memory, as a share of physical memory, that a step above one may reach. |
| `swap_growth_factor` | float / `2.0` | Swap-outs above one may reach this multiple of the one-slot rate ... |
| `swap_floor_mb_per_minute` | float / `64.0` | ... and are never judged below this rate. |
| `fidelity_tolerance` | float / `0.05` | How far structural agreement with the one-slot answers may fall below one slot's agreement with itself. |
| `min_throughput_gain` | float / `0.10` | What counts as a significant gain, for the plateau rule, the ideal N, and a declared number. |
| `max_evidence_age_days` | float / `30` | Evidence older than this is stale. |

The bounds are read when a decision is made, not frozen into the evidence, so tightening
one takes effect at once: the gate re-judges the stored measurements against what this
file says now.

```toml
[local_models]
concurrent_runs = 1        # 8.c as written; "measured" once the operator chooses it (ADR-0058)
model = "gpt-oss:20b"
context_window = 65536
```

**On a cluster.** Every node that serves a model is its own device. Run the calibration
as a Job pinned to the node (`nodeSelector`), inside the model runner's pod network, with
`VIBEY_GH_SLOTS_DIR` on a volume that outlives the Job, and give the workers the same
directory. A node without evidence, or with stale evidence, runs one. The chart does not
yet template this Job (ADR-0058 records it as owed).

## `[tidy]`

The clean repo (**sub-doctrine 9.a**): every repository is kept technically clean at
all times — no exceptions — locally and in the cloud, while **human messiness is
expressly welcome and never touched**: prose, discussions, stashes, work in
progress. The clutter this wars on is machine-state clutter only.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | The doctrine's bar; disabling records a deliberate exception in review. |
| `keep_branches` | string list / empty | Kept beyond the integration and release branches (an LTS line, say). |
| `trust_forge_deletions` | boolean / `true` | Squash and rebase merges rewrite SHAs, so ancestry cannot prove a merged branch landed — the forge deleting its remote at merge time is the proof instead. Set false where remote branches die for other reasons. |
| `fail_check` | boolean / `false` | Does the cloud clutter `vibey-gh check --ci` surveys — merged-and-undeleted remote branches, draft releases, orphan tags — fail the build, or print as an advisory line? Advisory by default: the survey judges a repository's accumulated past, so an adopter's CI must not go red for branches that were already there. Turn it on once the repository is clean. `check` only ever reports; `vibey-gh tidy --apply` is the only thing that removes anything. |

Losslessness governs every deletion: ancestry-contained refs and forge-deleted
upstreams only. Anything not provably redundant — draft releases, orphan tags,
stashes, untracked paths — is reported to the human and never machine-removed.

## `[social_signals]`

The social-signals surface (**sub-doctrine 4.a**, ratified by operator merge): the
published site presents real human social proof — testimonies, endorsements,
adoptions, case studies, reviews, community counts, citations, press, contributors,
backers, talks, certifications — as a self-contained, theme-aware section on the
landing page, injected after the site build.

The sub-doctrine's terms are permanent and configuration cannot soften them:

- **Opt-in, forever available.** Off by default in every repository; the capability
  itself exists at all times, in all places, with no exceptions — an adopter turns it
  on, never asks whether it exists.
- **100% comprehensive to the day.** The kind taxonomy covers the authentic
  social-signal classes of the current world and grows when the world grows a real
  new one — never a synthetic one.
- **Verification expires (the 4.a amendment).** A past-authentic signal is never
  assumed presently authentic — man-in-the-middle and forgery attacks target exactly
  that assumption. Every authenticity claim is only a claim, including the operator's
  own and especially the agent running the code; every entry carries the date a human
  last verified it, stale attestations block until re-verified, and a signal
  discovered inauthentic is removed immediately and permanently — revoked entries can
  never be re-attested.
- **100% authentic, from a real human agent, never a machine.** Every entry names its
  agent — a person, or an institution of persons such as a government — carries its
  source hyperlink at the point of reference, and carries `human_attested = true`:
  the operator's own attestation, made by the human who added the entry. Validation
  refuses anything less at config load, and the exact-head review blocks
  machine-authored, synthetic, unattributed, or unverifiable signals as **false
  witness**.

```toml
[social_signals]
enabled = true
heading = "Real people, real words"

[[social_signals.entries]]
kind = "testimony"                     # see the kind taxonomy above
agent = "Jane Doe"                     # the real human agent — always named
role = "CTO"
org = "Acme"
date = "2026-08-30"
quote = "It shipped my release while I slept."
source = "https://example.com/jane-said-it"   # provenance, at the point of reference
human_attested = true                  # the operator's own attestation — required

[[social_signals.entries]]
kind = "community"
agent = "GitHub stargazers"
value = "1,204"
source = "https://github.com/you/repo/stargazers"
human_attested = true
```

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `false` | Opt in per repository; the feature itself is always available. |
| `heading` | string / `"Real people, real words"` | The section heading on the landing page. |
| `max_attestation_age_days` | integer / `365` | The 4.a amendment's re-verification clock: an attestation older than this blocks the check until a human re-verifies the signal and re-dates it. Must be positive — attestations that never age are forbidden. |
| `entries` | array of tables / none | Each entry: `kind` (from the taxonomy), `agent`, `source` (https), `human_attested` (required `true`), `attested_on` (required ISO date — when the human last verified authenticity), and optionally `quote`, `role`, `org`, `date`, `value`, `revoked`. |
| `entries[].revoked` | boolean / `false` | The permanent tombstone: a signal discovered inauthentic renders nowhere, forever, and can never be re-attested — `revoked` with `human_attested` is refused at load, no exceptions ever. |

Voiced kinds (testimony, endorsement, review, press, case-study, talk) render as
quote cards; counted and named kinds render as compact linked chips. The section
closes by saying what it is: every entry is attested human speech — never a
machine's.

## `[yank]`

Report which releases on an index the just-published version supersedes.

**It reports. It cannot yank, and neither can anything else you write.** PyPI exposes no
API for yanking. The legacy upload endpoint answers `405 Method Not Allowed` for
`:action=yank` (a recognised action such as `:action=file_upload` answers `403` on bad
credentials, so authentication is never even reached), and the `/manage/...` route the web
UI uses is CSRF-protected against non-browser callers. Programmatic access is an open
upstream request, not a shipped capability:

- [pypa/packaging-problems#633](https://github.com/pypa/packaging-problems/issues/633)
- [pypi/warehouse#12708](https://github.com/pypi/warehouse/issues/12708)

[PyPI's own documentation](https://docs.pypi.org/project-management/yanking/) gives exactly
one method: the release management page, **Options → Yank**. No token changes this; do not
try to add one.

That is arguably the right design. [PEP 592](https://peps.python.org/pep-0592/) defines a
yanked release as one with *"a serious problem which should prevent it from being
installed"* — a distress signal, not a tidiness marker. Installers still resolve a yanked
version when a pin demands one, so nothing is reclaimed; what changes is that everyone
pinned to it starts seeing a warning about a release that may be perfectly good. The manual
click is the friction that keeps that deliberate.

So this automates the analysis and leaves the click: it works out exactly which releases
are superseded and prints them with a link to the page that can action them.

| Field | Type / default | Meaning |
|---|---|---|
| `pypi` | boolean / `false` | Report superseded PyPI releases after a publish. |
| `testpypi` | boolean / `false` | Report superseded TestPyPI releases. |
| `keep` | integer / `0` | How many releases below the newest to leave out of the report, so a rollback target is never suggested. |
| `governance_paths` | string list / the founding documents | fnmatch globs (default `docs/constitution.md`, `docs/commandments.md`, `docs/bill-of-rights.md`, `docs/sd-*.md`). Article V.4 of the Constitution: when a release's range touches any of them — a RATIFIED governance change — every previous release on both indexes is reported superseded, with `keep` and the two switches above overridden. Zero exceptions: the config is machinery and the rule is law. Pass the ratifying push's range as `--governance-since` (see below). |

Two invariants hold regardless of configuration:

- **the version just published is never listed**, excluded by identity rather than by
  version ordering;
- **a version this cannot parse is never listed.** Ordering covers `N.N.N` and
  `N.N.N.devN`, which is what this tooling publishes. Epochs, local segments, post- and
  pre-releases are left out, because half a PEP 440 parser mis-orders them silently and
  here that means naming a good release as a candidate for yanking.

Run it from a release workflow after the upload step. No credentials are involved — the
index JSON it reads is public:

```bash
vibey-gh report-superseded --index pypi --project my-package --version "$VERSION" \
  --governance-since "$GITHUB_EVENT_BEFORE"   # optional: evaluate Article V.4 on the push range
```

`--governance-since` takes the git ref that opened the release range (a push event's
`before` SHA). If the range touches a `governance_paths` file, the report is the
Article V.4 demand: every previous release named, retention window and switches
overridden. An unreadable ref is reported loudly — the rule is never silently waived —
but never fails the release.

It always exits 0: the package is already published by the time it runs, so a bookkeeping
failure is reported rather than turning a successful release red.

## Machine-level: `~/.config/vibey-gh/failover.toml`

The operator-seat failover engine (`vibey-gh failover`, #208) is configured per
**machine**, never per repository — seats describe the operator's laptop, so nothing
about them belongs in a repository's `.vibey-gh.toml`. A missing file is a disabled
engine; nothing here ever self-activates.

```toml
enabled = true
paid_probe = "claude -p ok --max-turns 1"   # exit 0 = the paid lane is alive
interval_seconds = 300

[[seats]]                                    # tried in order; first healthy one wins
name = "qwenloop"
launch = "qwenloop run"
health = "curl -sf http://127.0.0.1:11434/api/tags"

[[seats]]
name = "opencode"
launch = "opencode"                          # empty health = engage without preflight
```

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `false` | The operator writes `true` deliberately; the first live handoff should be supervised. |
| `paid_probe` | string / empty | A shell command whose exit status answers "is the paid lane alive?" — the 296 ms *Credit balance is too low* refusal is exactly what it distinguishes from health. A hang counts as down. |
| `interval_seconds` | integer / `300` | Loop cadence when run without `--once`. |
| `seats` | array of tables / qwenloop, then opencode | Each seat is a name, a `launch` command, and an optional `health` preflight, judged by exit status — any agent fits without a code change. |

Seat state (which agent holds the seat, and its pid) lives in
`~/.local/state/vibey-gh/failover.json`; `--config` and `--state` override both paths.
The handoff is lossless because the seats share one working tree and the
`local-authority` loop keeps local and remote synced throughout.

## `[github_release]`

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Enable immutable tags and GitHub Releases. |
| `tag_prefix` | string / `v` | Nonempty, whitespace-free tag prefix. |
| `generate_notes` | boolean / `true` | Ask GitHub to generate release notes. |
| `require_new_version` | boolean / `false` | Fail instead of silently doing nothing when a release-branch push does not carry a new version (the tag it would need already exists at a different commit). Leave off for a repository where a docs-only or tooling-only promotion is a normal, frequent, versionless push. |

## `[announce]`

The changelog `vibey-gh announce` posts to Discord after each documentation deploy (see
[operations](operations.md#discord_webhook_url-optional)). Every key is optional.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Post at all. Off, the step says so and passes. |
| `webhook_secret` | string / `DISCORD_WEBHOOK_URL` | The repository secret holding the webhook. A secret NAME, rendered into `${{ secrets.… }}`; never the URL. `GITHUB_*` is refused: GitHub reserves the prefix. |
| `username` | string / `vibey` | The name the message is posted under (1–80 characters). Refused where Discord would refuse it: containing `discord`, `clyde`, `@`, `#`, `:` or ` ``` `, or being `everyone` or `here`. |
| `max_changes` | integer / `8` | Lines listed before `…and N more` (1–50). Breaking changes are never counted against it. |
| `max_subject_chars` | integer / `100` | A longer description is cut with `…` (20–400). |
| `max_message_chars` | integer / `2000` | The message's ceiling in UTF-16 units (200–2000, Discord's limit). The message fits by construction: listed lines go first, then breaking lines shorten, then overflowing breaking changes are counted by name. |
| `include_other` | boolean / `true` | List types in no named group under `other_group`; off, they are only counted. |
| `breaking_group` | string / `Breaking` | The heading for any `!` or `BREAKING CHANGE` commit. It always leads. |
| `other_group` | string / `Other` | The heading for types no group names. |
| `groups` | table / `Added = ["feat"]`, `Fixed = ["fix"]` | `[announce.groups]`: label = commit types, in display order. A type may be in one group only. |
| `type_words` | table / `feat = "Feature"`, `fix = "Fix"`, `docs = "Docs"`, `perf = "Performance"`, … | `[announce.type_words]`: the word a type prefix becomes. Keys given here override; the rest keep their defaults. |
| `noise_patterns` | list of regex / merge commits, `chore(merge)`, `chore(release)`, `chore(heartbeat)`, merge-conflict chores | Subjects hidden from the list and counted as `+N maintenance commits`. A breaking change is never noise. |
| `link_pull_requests` | boolean / `true` | Link each line's `#N` (or short commit) to the forge. |
| `link_compare` | boolean / `true` | Link the compare view, or the changelog, after the list. |
| `link_surfaces` | boolean / `true` | End with the channel site and the surfaces this deploy produced. |
| `suppress_embeds` | boolean / `true` | Post with Discord's no-link-preview flag. |
| `changelog_path` | string / `CHANGELOG.md` | A release announces this file's section for its version. Repository-relative; letters, digits and `. _ / -` only, since it is also written into a link. |
| `max_history_pages` | integer / `10` | Pages of 100 runs, and of 100 compared commits, read for the previous position and the range (1–10: the Actions API serves a status-filtered run listing only to its 1000th result). Commits beyond are counted; no accepted announcement inside the window re-anchors, and says so. |
| `max_history_candidates` | integer / `20` | Runs for the branch whose announcement was not accepted that are read, one jobs call each, before the announcement re-anchors and says so (1–100). Staying unknown instead would never recover from a long outage. |

```toml
[announce]
max_changes = 6
include_other = false

[announce.groups]
Added = ["feat"]
Fixed = ["fix", "perf"]
```

## `[rulesets]`

Reconciles GitHub repository rulesets for the integration and release branches, so the
protection `repository-profile.yml` has always only *verified* is actually *set*. Branch
names are not configured here — `[rulesets.integration]` always targets
`branches.integration` and `[rulesets.release]` always targets `branches.release`.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Reconcile both rulesets at all. `false` leaves the repository untouched, exactly as before this feature existed. |

### `[rulesets.integration]` and `[rulesets.release]`

| Field | Type / default | Meaning |
|---|---|---|
| `required_checks` | string list / integration: `["Provenance", "Analyze Python", "Documentation contract", "PR evaluate / gate", "PR review / gate"]`; release: the same without the gates | Required status-check contexts — **check-run names, not workflow names** (see below). Empty omits the check requirement entirely. The integration list, less `[pr_automation] ignored_checks` and the gates it routes around, is also what `automation-bootstrap.yml` waits on (see below); empty there means the bootstrap refuses every merge. |
| `strict_required_checks` | boolean / `true` | Require the branch to be up to date with its base before merging. |
| `required_approvals` | integer / integration: `0`, release: `1` (0–6) | Required approving reviews. Integration defaults to `0` because PR automation gates it instead. |
| `dismiss_stale_reviews` | boolean / `true` | Dismiss stale reviews when new commits are pushed. |
| `require_code_owner_review` | boolean / `false` | Require an approving review from the owner `.github/CODEOWNERS` names on a pull request that touches an owned path. Inert without a CODEOWNERS file. Off by default because, with one, it blocks every such pull request until that owner approves. The merge train's `--admin` fallback bypasses this review, so pair it with `[merge_train] protected_paths` for any path that must never merge unattended. |
| `require_conversation_resolution` | boolean / `true` | Require every review thread to be resolved before merging. |
| `require_linear_history` | boolean / `true` | Forbid merge commits onto the branch. |
| `require_signed_commits` | boolean / `false` | Require every commit to be signed. |
| `allow_force_pushes` | boolean / `false` | **Rejected at load time if `true`.** A permanent branch can never be configured to allow force pushes. |
| `allow_deletions` | boolean / `false` | **Rejected at load time if `true`.** A permanent branch can never be configured to allow deletion. |
| `bypass_actors` | string list / `["RepositoryRole:5"]` | `"<ActorType>:<id>"` entries granted to bypass the ruleset. The default is the repository admin role. `[]` means nobody — including the owner. |

### `[rulesets.integration.merge_queue]` and `[rulesets.release.merge_queue]`

A green pull request is not a green merge: its checks ran against the base as it stood then,
and nothing between that base and the branch tip was ever built with it.
`strict_required_checks` already refuses to merge a stale branch, so without a queue that
proof is bought by hand, one rebase at a time, with the base moving underneath. The queue
builds each member against the real tip in sequence instead (ADR-0036).

All seven of GitHub's `merge_queue` parameters are keys rather than constants, because the
API requires all seven and a value hard-coded here would be a decision taken away from the
next adopter, silently (ADR-0018). The defaults are the shape this repository runs, not a
claim about anyone else's branch flow.

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `false` | Declare the queue at all. **Off by default on purpose:** a merge queue changes when and how every merge happens for everyone using the repository, and switching that on by upgrading a tool would be a behaviour change nobody asked for. |
| `merge_method` | `MERGE` \| `SQUASH` \| `REBASE` / `SQUASH` for integration, `REBASE` for release | How the queue lands a member. Match the branch's own flow — feature pull requests squash into the integration branch, and promotion rebases into the release branch (ADR-0028). |
| `grouping_strategy` | `ALLGREEN` \| `HEADGREEN` / `ALLGREEN` | `ALLGREEN` requires every member of a group to be green; `HEADGREEN` merges on the group head alone, which can land a member that was never green on its own. |
| `check_response_timeout_minutes` | integer 1–360 / `60` | How long the queue waits for a member's checks before treating it as failed. |
| `max_entries_to_build` | integer 1–100 / `5` | How many members are built speculatively at once. |
| `max_entries_to_merge` | integer 1–100 / `5` | How many members may land in one group. |
| `min_entries_to_merge` | integer 1–100 / `1` | How few members a group may contain before the wait below applies. |
| `min_entries_to_merge_wait_minutes` | integer 0–360 / `5` | How long the queue waits for a group to reach `min_entries_to_merge` before merging a smaller one. `0` never waits. |

Out-of-range values and unknown method or strategy names are rejected **at load time**, with
the field named — not at reconcile time, where a typo would surface as an API rejection
halfway through a run.

Declaring the table is not the same as applying it: `vibey-gh rulesets` (or the workflow that
calls it) is what reconciles the queue onto the branch. Declaring it **off** is worth doing
explicitly — a release branch that promotes with one controlled rebase gains nothing from a
queue and would add its wait to every release, and writing that down means the next reader
sees a decision rather than an oversight.

### `required_checks` names check runs, not workflows

This is the one field here that can lock a branch with no way out, so it is worth stating
plainly. A required status check matches a **check run**, and for GitHub Actions a check
run is named for its **job**, not its workflow. The `CI` workflow in this repository
reports as `Lint`, `Build`, and `Test (3.12)`; nothing ever reports as `CI`.

Requiring a name nothing produces does not fail — it *waits*. The branch reports
`N of M required status checks are expected` forever, and because a ruleset has no
"include administrators" toggle the way classic branch protection did, an empty
`bypass_actors` means no one can merge past it. The only exit is editing the ruleset.

Two habits avoid it: name the job, and keep a bypass actor. `[pr_automation].scan_workflows`
names *workflows* and looks like a tempting list to reuse here — it is not one. To find the
real names, open a recent pull request's checks tab, or:

```bash
gh api "repos/OWNER/REPO/commits/$(git rev-parse HEAD)/check-runs" \
  --jq '.check_runs[].name' | sort -u
```

### The integration list also gates the automation bootstrap

`automation-bootstrap.yml` — the admin-only path that merges a repair to privileged workflow
code past PR automation — waits on these names too, so it never names a check this
repository does not produce. `vibey-gh install` renders `[rulesets.integration]
required_checks` into the deployed workflow, less `[pr_automation] ignored_checks` and the
gates the bootstrap exists to route around (`gate`, `PR evaluate / gate`,
`PR review / gate`,
`Automation bootstrap / gate`). With the defaults that is `Provenance`, `Analyze Python`,
and `Documentation contract`; a repository whose CI reports one job named `gates` and
requires only that waits on `gates` alone. Change the list, then re-run `vibey-gh install`
and commit the re-rendered workflow — `vibey-gh check --ci` reports the drift until you do.

The step fails closed: an empty list, a head with no check runs, a named gate that is
absent, or any other check run that is not green each refuse the merge, and the error names
the absent gates. A name that opens a `${{ }}` expression is refused at render time,
because the list is rendered into the step's environment. See
[Workflows](workflows.md#automation-bootstrap) for the whole gate.

Reconciliation is idempotent read-compare-write, the same shape `repository-profile.yml`
already uses for settings and topics: an existing rule type the configuration does not
mention is never removed, only reported. A ruleset the API refuses fails the job with the
API's own reason rather than being silently skipped — a skipped reconciliation would look
identical to a satisfied one. Run `vibey-gh rulesets --dry-run` to inspect the diff before
a workflow run applies it.

## `[workflow_names]`

Every workflow name the rendered templates depend on. Templates chain by `workflow_run`, which
matches a workflow's display **name**, so these are keys rather than constants: a hardcoded name
silently assumes every adopter calls its pipeline `CI` and its publish step `Release`. When that
assumption is wrong the trigger simply never matches and nothing runs, with no error anywhere —
the silence is the whole danger.

**Two kinds live in this table.**

- `ci` and `release` name workflows the **adopter owns**. vibey-gh renders neither, and never
  installs or renames those files; it only needs to know what they are called in order to trigger
  off them. These genuinely differ per repository.
- The rest name **vibey-gh's own templates**. Renaming one is safe: each template renders its own
  `name:` from the same field the other templates trigger on, so both sides move together and the
  chain cannot drift.

| Field | Default |
|---|---|
| `ci` | `CI` |
| `release` | `Release` |
| `provenance` | `Provenance` |
| `pr_evaluate` | `PR evaluate` |
| `pr_review` | `PR review` |
| `merge_train` | `Merge train` |
| `promote` | `Promote` |
| `release_surfaces` | `Release surfaces` |
| `release_repair` | `Release repair` |
| `github_release` | `GitHub Release` |
| `repository_profile` | `Repository profile` |

Note the distinction from `required_checks` (see `[rulesets]`): these are **workflow**
names. A required status check matches a **check-run** name, which for GitHub Actions is the
job's name, not the workflow's.

## `[repository_profile]`

| Field | Type / default | Meaning |
|---|---|---|
| `enabled` | boolean / `true` | Reconcile repository settings. |
| `description` | string / derived | Description, at most 350 characters. |
| `topics` | string list / five automation topics | Lowercase topics, maximum 20. |
| `has_issues`, `has_projects`, `has_discussions` | boolean / `true` | Enable collaboration features. |
| `has_wiki` | boolean / `false` | Enable the wiki. |
| `allow_squash_merge`, `allow_rebase_merge`, `allow_auto_merge` | boolean / `true` | Allowed merge mechanisms. |
| `allow_merge_commit` | boolean / `false` | Permit merge commits. |
| `delete_branch_on_merge` | boolean / `false` | GitHub's own blanket auto-delete-on-merge. Keep false because `develop` heads promotion PRs and would itself be deleted. This is independent of branch cleanup: the merge train and Automation bootstrap already delete a merged PR's head branch themselves, through a guarded API call, whenever it is not a permanent, integration, or release branch and not a fork — regardless of this setting. |
| `web_commit_signoff_required` | boolean / `true` | Require web-editor signoff. |
| `vulnerability_alerts`, `automated_security_fixes` | boolean / `true` | Enable dependency security services. |

## `[documentation]`

| Field | Type / default | Meaning |
|---|---|---|
| `enabled`, `ai_maintenance` | boolean / `true` | Require and AI-maintain the documentation suite. |
| `model` | string / `claude-sonnet-5` | Documentation model. |
| `required_files` | string list / built-in FOSS and agent suite | Required documentation paths. |
| `production_label`, `preview_label` | strings / `Production`, `Preview` | Human-facing channel names. |
| `production_indexing` | boolean / `true` | Permit production indexing. |
| `preview_indexing` | boolean / `false` | Permit preview indexing. |
| `generate_robots`, `generate_sitemap_index`, `generate_llms_txt`, `generate_llms_full_txt`, `generate_json_ld` | boolean / `true` | Generate robot, search, LLM, and structured metadata. |
| `generate_book`, `generate_paper` | boolean / `false` | Export the built site as a book (`book.epub`, `book-print.html`, and `book.pdf` when the runner has a Chromium) and render `docs/paper.md` as a journal-class PDF (`paper.pdf`), published at the root of each channel site. Everything that was actually produced is then linked from every page's navigation and footer, from the channel chooser, and from `llms.txt`, and — on the release channel, when `[github_release]` is enabled — attached to the GitHub Release for that exact version as permanent assets. Links are rendered from what exists on the deploy, never from these flags, so a page never links a file that was not built. The book's print interior is the standard KDP 6x9in paperback (0.75in top and bottom, 0.5in outside, a 0.5in gutter, 11pt serif); its trim, margins, gutter and type are `vibey-gh book` flags (see the CLI reference), and the managed workflow does not pass them yet, so a published book uses those defaults — the 0.5in gutter meets KDP's minimum for 151–300 pages. |
| `math` | boolean / `false` | Render LaTeX on the published site: `$...$` and `$$...$$` math, kept intact through Markdown by `pymdownx.arithmatex` (installed at build time), and ```` ```latex ```` theorem-like environments (`invariant`, `theorem`, `lemma`, `definition`, `proposition`, `corollary`, `proof`, `verbatim`), converted to styled blocks. Typeset by MathJax 3.2.2, fetched from the npm registry at build time, verified against a pinned checksum and served from the site itself, so a reader's browser contacts no CDN. Off by default because every `$...$` pair in prose becomes math. |
| `governance_source` | string / empty | Repository-relative directory holding the governance corpus (`constitution.md`, `doctrines.md`, `commandments.md`, `bill-of-rights.md`, `sd-*.md`). When set, every channel site publishes those documents as a **Governance** section — so they are also chapters of the book — copied from this single source at build time, and every page's navigation and footer, the channel chooser and `llms.txt` link the pages that were published (sub-doctrine 7.b, governance in plain sight). Empty publishes nothing. |
| `corpus_index` | string / `corpus-index.json` | Repository-relative path of the index `vibey-gh corpus-index` writes; shipped beside each channel site after the build so the published law can be integrity-checked offline. |
| `funding_bitcoin`, `funding_monero`, `funding_ethereum` | string / empty | Opt-in funding signage (#198): when set, a small footer line beside the provenance signage offers the address as text with a copy button — never a payment-processor link. Each address is shape-validated at config load (bech32/Base58 for Bitcoin, 95/106-char Monero base58, `0x`+40-hex for Ethereum); a malformed value is a configuration error, and no default ever ships. The render is verbatim from this file, so any change to an address is a reviewed, fingerprinted commit. |
| `funding_label` | string / `Support this work` | The sentence introducing the funding line. |
| `bottom_nav` | boolean / `true` | Clone the theme's own `rel="prev"`/`rel="next"` header anchors into a previous/next bar at the bottom of every published page, so a reader who has just finished a page — especially on a phone — can move on from where they already are. Pages without those anchors (the channel picker, 404) get no bar. `false` disables the injection. |
| `author_name` | string / `Adam Matthew Steinberger` | Reserved documentation-provenance author label. Parsed and validated (non-empty), but not yet emitted into any generated asset. |
| `author_url` | URL / `https://vibewithadam.matthewsteinberger.com` | The author's own address. Stated in the rendered paper's first-page provenance note and provenance paragraph (`vibey-gh paper --author-url`), beside the revision the paper was rendered from and the time it was rendered. |
| `author_email` | email / empty | The paper's corresponding-author address. When set, it appears in the IEEEtran byline and the provenance paragraph; empty omits it. Must be a plain `mailbox@host` address. |
| `author_affiliation` | string / empty | The affiliation line under the author's name in the paper's byline. Empty omits it. |
| `google_analytics_id` | string / empty (disabled) | GA4 measurement ID (`G-<alphanumeric>`) injected into every page of both generated documentation channels and the channel-picker page. Empty disables Google Analytics entirely: no script tag is emitted and no request ever reaches Google. |
| `favicon` | string / `📘` | One or two emoji render as a zero-asset SVG favicon (plus a matching `apple-touch-icon`). A value that starts with `http://`, `https://`, or `/`, or whose last path segment contains a `.`, is instead used verbatim as a `<link rel="icon">` URL. Empty omits the favicon link. |
| `og_image` | URL / empty | Social preview image rendered into the Open Graph and Twitter Card meta tags on every generated page. Empty falls back to GitHub's own generated OpenGraph card for the release commit, which always exists and stays current. |
| `twitter_site` | string / empty | `@handle` rendered as the `twitter:site` meta tag. Empty omits the tag. |
| `twitter_creator` | string / empty | `@handle` rendered as the `twitter:creator` meta tag. Empty omits the tag. |
| `keywords` | string list / empty | Rendered as the page's `<meta name="keywords">` and, when `generate_json_ld` is enabled, the JSON-LD `keywords` property. Empty falls back to `[name, owner, "documentation", "release notes", "changelog"]`. Entries must not contain `<`, `>`, `"`, a comma, or a newline. |
| `author` | string / empty | Rendered as the page's `<meta name="author">` and, when `generate_json_ld` is enabled, the JSON-LD `author.name`. Empty falls back to the repository owner. Distinct from `author_name`/`author_url` below, which are not yet emitted anywhere. |
| `theme_color` | hex colour / `#080b14` | Rendered as `<meta name="theme-color">` when non-empty. Must match `^#[0-9a-fA-F]{3,8}$`. |
| `locale` | string / `en_US` | Rendered as `og:locale` and, when `generate_json_ld` is enabled, the JSON-LD `inLanguage` (with `_` replaced by `-`). |
| `google_site_verification` | string / empty | Google Search Console "HTML tag" verification token — the bare `content=` value, not the whole `<meta>` tag; must match `^[A-Za-z0-9_-]{1,128}$`. Rendered as a `<meta name="google-site-verification">` tag on every published page and the channel-picker index, so it survives Pages redeploys, unlike an uploaded verification file. |
| `site_requirements` | string list / empty | Extra packages installed before the published site is built, as PEP 508 requirement specifiers. Each is shell-quoted, so `"mkdocs-material[imaging] >= 9.5"` stays one argument. |
| `site_requirements_file` | path / `docs/requirements.txt` | Installed with `pip install -r` when the file exists. Absent, the step is skipped; empty disables the hook entirely. |
| `properdocs_version` | string / `1.6.7` | The `properdocs` and `properdocs-theme-mkdocs` version the site build pins. |

### Installing what your site actually needs

ProperDocs depends on `properdocs` and its theme, and on nothing your `properdocs.yml`
declares. A site configuring `mkdocs-gen-files`, `mkdocs-literate-nav`, a Material theme,
or any `pymdownx.*` markdown extension needs those packages present, or the `--strict`
build fails on the first one it reaches — the plugin is simply not installed.

Declare them once, either inline or in the conventional requirements file:

```toml
[documentation]
site_requirements = [
  "mkdocs-gen-files",
  "mkdocs-literate-nav",
  "pymdown-extensions>=10.7",
]
```

Both hooks are no-ops when unused, so a repository whose site needs nothing extra is
unaffected. This cannot have a useful default: which packages a site needs follows from
that site's own configuration.

`author_name` and `author_url` exist for a planned author credit in the generated
Pages sites and are exercised by config parsing, validation, and tests today, but
`release-surfaces.yml` never reads either one, so setting these two keys has no
visible effect on a generated site yet. This is unrelated to `author` above: that
field is already wired into the rendered `<meta name="author">` tag and the JSON-LD
`author.name` property.

`favicon`, `og_image`, `twitter_site`, `twitter_creator`, `keywords`, `author`,
`theme_color`, and `locale` land verbatim in rendered HTML and workflow YAML, so
each is validated at load time rather than discovered on a published page: none
of the string-valued fields may contain `<`, `>`, `"`, or a newline, `keywords`
entries additionally reject commas, and `theme_color` must match a hex colour
pattern.

Run `vibey-gh install`, review and commit generated assets, then run
`vibey-gh check --ci`. Identity and Pages URLs are derived at runtime.

## `[marketplace]`

The one Claude Code marketplace at the repository root, for a monorepo whose plugin
marketplaces are workspace members. `/plugin marketplace add owner/repo` reads exactly
`<repo>/.claude-plugin/marketplace.json` and nothing else; `vibey-gh marketplace` renders
that file from the members' own manifests — every plugin, its `./` source re-rooted from
the member to the repository, all other fields verbatim, the owner taken from the first
member — and `vibey-gh check` fails whenever the file on disk is not what the members render
to. The members' manifests are untouched, so a member's own package keeps shipping its
marketplace under its own name. Empty `members` renders nothing and checks nothing.

| Field | Type / default | Meaning |
|---|---|---|
| `name` | string / empty | The root marketplace's own name — what users type after `@` in `/plugin install <plugin>@<name>`. Kebab-case, required when `members` is set. Claude Code registers one marketplace per name per user, so this must differ from every member's own name (this repository's root is `vibey`; the packaged vibey-skills stays `vibey-skills`). |
| `members` | string list / empty | Repository-relative directories each holding a `.claude-plugin/marketplace.json`, in the order their plugins appear in the root. No absolute paths, no `..`, no whitespace or shell metacharacters. |
| `description` | string / empty | The root manifest's human description. Empty derives one from the plugin count and the members. |

Rendering is strict, and every failure names the member: a manifest that is missing,
unreadable, has no `name`, no `owner.name` or no `plugins`; a plugin entry with no `name` or
no `source`; a `./` source that leaves its member (`..`), carries a backslash or resolves to
a directory without `.claude-plugin/plugin.json`; or one plugin name declared by two members.
A source that is not a string (a `github`/`url` object) is remote, not member-relative, and
passes through untouched.

```toml
[marketplace]
name = "vibey"
members = ["src/vibey_tools/skills", "src/vibey_tools/gh"]
```

## Advanced debug environment

| Variable | Default | Meaning |
|---|---|---|
| `VIBEY_GH_DEBUG` | unset | Set to `1`, `true`, `yes`, or `on` to enable structured branch tracing. |
| `VIBEY_GH_DEBUG_LOG` | stderr | Append JSONL trace events to this operator-controlled path. |
| `VIBEY_GH_TRACE_ID` | generated UUID | Correlate the trace with a wider diagnostic session. |

GitHub correlation is read from `GITHUB_RUN_ID`, `GITHUB_RUN_ATTEMPT`, and `GITHUB_SHA`.
These controls affect diagnostics only; source validation always confirms that every
configured Python control-flow opcode can be represented by the tracer.

These environment variables only ever scope the tracer to `vibey_gh`'s own installed
package directory; there is no CLI flag or environment variable to point it at a
consuming project's source tree. A project embedding `vibey_gh.debugging` directly can
call `enable(roots=(...))` with its own package directories to trace its own code instead.
