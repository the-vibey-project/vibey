# Changelog

All notable changes are recorded in immutable [GitHub Releases](https://github.com/the-vibey-project/vibey-gh/releases).
This file follows Keep a Changelog and semantic versioning conventions.

## Unreleased

- Fix `vibey-gh install` crashing with `FileNotFoundError`, after it had written every file, when `gh` is not on PATH; `installation_notices()` now reports `gh not found; skipping secret/permission checks` (#264).
- Add `vibey_gh/__main__.py`, so `python -m vibey_gh` runs the same CLI as the `vibey-gh` script instead of failing with `No module named vibey_gh.__main__` (#264).
- Correct `[issue_automation] fallback_enabled` in `docs/configuration.md` and its `config.py` comment: the default has been `true` since #277 (sub-doctrine 8.a), not `false`; the README, security and threat-model pages also stop calling the heartbeat-gated fallback "opt-in", and a test pins the documented defaults to the code (#264).
- Fix `release-surfaces.yml`, which GitHub had been rejecting outright as an invalid
  workflow file — `(Line: 670, Col: 14): Exceeded max expression length 21000`. The
  "Restore the other release channel" step had grown to a single 509-line script, and
  because it carried inline `${{ }}` expressions GitHub compiled the WHOLE script as one
  expression and capped it at 21,000 characters. Nothing ran: an unparseable workflow
  produces a run named by file path, with no jobs and no retrievable logs, so the docs
  site, the book, the paper and the OCI release bundle silently stopped publishing while
  the only visible symptom was a red mark on a workflow that was never the patient. The
  step is now four, split at its own seams — restore the other channel, write the chooser
  page, substitute its values, write robots/sitemap/llms — and every inline expression has
  moved into the `env:` block each step already used, which removes the file's last
  expression-bearing script and takes it out of the cap's reach entirely. **Shell state was
  the real hazard in that split**, not the YAML: `GA_ID` was assigned in the first segment
  and read 370 lines later by the chooser's Python pass, so a naive split would have
  published a blank analytics snippet with nothing red anywhere. It is now carried in the
  owning step's `env:` behind a `: "${GA_ID?}"` tripwire, which fails on an unset variable
  while still allowing the empty value that means analytics are switched off.
- Guard it: a new template test measures every interpolated workflow scalar — `run`, `with.*`
  and `env.*`, at step and job level, across the templates, the tenant's deployed copies and
  the workspace root's — against GitHub's limit. It measures the COMPILED length, the scalar
  escaped into `format('<literal>', ...)`, because that is what GitHub caps and it is
  materially larger than the parsed string: the commit that first broke this file carries a
  scalar of 20,786 parsed characters, comfortably under the cap, and 21,064 compiled, over
  it. A guard measuring the parsed string would have passed the exact commit that caused
  this outage. Scalars with no expression are exempt and are recorded as such, which the
  same file proves: a 21,958-character expression-free script sits 463 lines ABOVE the one
  GitHub named, and GitHub parsed straight past it.

- Fix the Claude tool lists in the managed workflow templates, which were being torn apart
  by argument tokenization. `claude_args` is split shell-style, so a permission spec
  containing a SPACE — `Bash(gh pr diff:*)` — arrived as three separate arguments:
  `Bash(gh`, `pr`, `diff:*)`. `Bash(gh` is an unbalanced rule, so the runtime failed while
  parsing its permissions before reaching the model at all — 490ms, one turn, no model
  usage, no cost — and the action then reported the only symptom it could see,
  `--json-schema was provided but Claude did not return structured_output`, naming the
  flag on the NEXT line, which was already quoted correctly. Every exact-head review in
  `pr-automation.yml` had been failing this way, and because the gate posts its check-run
  against the head SHA rather than against a workflow, the failure surfaced on unrelated
  runs that merely shared that commit — `release-surfaces.yml` appeared to be failing on
  every push to `develop` while being entirely innocent. Both affected values are now
  quoted, matching the `--json-schema` line directly beneath them, which had carried
  quotes all along. A new template test tokenizes every `--allowedTools` and
  `--disallowedTools` in every shipped template with `shlex`, asserts each resolves to
  exactly one argument, and asserts every comma-separated rule has balanced parentheses —
  the sibling of the `--json-schema` tokenization test that already existed, and which
  proves this repository had identified the hazard and simply never applied it here.

- Add `vibey-gh flatten`: rewrite the current branch as one commit on its base, with the
  subject normalised and the trailers re-derived. Two gates send a branch here and neither
  has another remedy. A commit authored through the GitHub web UI or API never meets
  `.githooks/commit-msg`, so it carries no `Made-With:` trailer and the provenance gate
  refuses it — `check --apply` cannot repair that, because it writes file headers, not commit
  trailers. And the Conventional Commits normaliser refuses outright any range containing a
  merge commit, which is every range that took the integration branch into a topic branch.
  Both answers were the same hand procedure, and that procedure has a live failure mode: a
  `reset --mixed` followed by an `add -A`, in a worktree created before a merge that deleted
  files, stages those files back and silently reverts a merged pull request inside an
  unrelated commit. It happened on 2026-09-17 — 12,115 lines of five deleted lockfiles — and
  was caught by reading a `--stat` and noticing the line count was too large, which is not a
  control. So the new commit is built with `git commit-tree` from the branch's EXISTING tree
  object: nothing is staged, nothing is reset, the working tree is never read, and there is no
  step at which content can enter or leave. The invariant is asserted as well as constructed —
  the built tree must equal the old HEAD's or the ref does not move — because an invariant
  nobody checks is a comment. Tree equality is necessary and NOT sufficient: against a base
  carrying commits the branch never merged, HEAD's tree is correctly HEAD's and is exactly what
  is wrong, because it never had those changes to lose, and the one commit would delete them.
  So the base must be an ancestor of HEAD, and a base that is not one is refused naming the
  remedy that keeps both sides: merge it in first, then flatten. Also refused: a detached HEAD,
  a permanent branch, an uncommitted tracked change, an empty range, and a range of only merge
  commits with no `--message` to reuse. Every author of the range becomes a `Co-Authored-By`,
  so absorbing one contributor's commit into another's cannot erase that it contributed at
  all — and so does every `Co-Authored-By` the range already declares, collected from EVERY
  commit of it the way the breaking footers are. Authorship is only half of how credit is
  written, and in this repository it is the quieter half: the convention here names the
  collaborator in a trailer while the git author stays the operator, so credit re-derived
  from authorship alone would drop every collaborator the range names. Those trailers are
  read from the trailing RUN of trailer paragraphs, not from git's final paragraph alone,
  because `.githooks/commit-msg` appends the provenance trailer as a paragraph of its OWN —
  so an ordinary commit here ends in two, and a reader that stops at the last one sees the
  provenance trailer and misses every `Co-Authored-By:` above it. That is not hypothetical:
  the first real flatten of this branch dropped its own co-author, with the full suite and
  100% branch coverage green, because a dropped co-author looks exactly like a commit that
  never named one. A paragraph that is not entirely trailer lines still ends the run, so a
  body sentence opening `Made-With:` remains prose. Breaking changes are
  collected from EVERY commit of the range, not from the first one: each `BREAKING-CHANGE:`
  footer is carried, deduplicated across both spellings the spec allows, and a `!` declared
  by a commit whose subject is not the one reused re-marks the composed subject rather than
  being invented into a footer nobody wrote — because nothing re-derives breaking-ness, and
  losing it silently demotes a major release to a minor one, in the direction nobody notices
  until it is published. Issue-closing keywords get the same treatment for the same reason.
  `Closes #12` is re-derivable from nothing — not authorship, not the tree, not the branch
  name — and the flatten had two ways to drop it: `Closes: #12` is trailer-shaped, so the
  trailer stripper removed it, and either spelling written in the range's third commit was
  never in the first commit's message to survive at all. So every closing keyword in the
  range is collected and put back, deduplicated by issue and keeping the verb its author
  used, in a paragraph of its own above the trailer block — placement that is load-bearing
  rather than decorative, since `Closes #12` is not `token: value` and a trailer block
  containing one stops being a trailer block, which the next flatten would read as a missing
  provenance trailer and add a second. Nothing is invented: a range that never promised to
  close an issue does not start promising it here. Both refs are pinned: `update-ref` takes
  the old LOCAL value and `--push` takes a lease on the value this clone last saw the REMOTE
  holding — its remote-tracking ref, which is what somebody else's push makes stale — so
  anything that landed in between refuses rather than being clobbered. Pinning the
  pre-rewrite local SHA instead reads like the same protection and is not: a branch about to
  be flattened usually carries a commit that was never pushed, the remote has therefore
  never held that value, and the lease refuses the ORDINARY case every time. A branch the
  remote does not have yet is created without a lease, decided by asking the remote and not
  by reading a failed push: there is no remote value to pin, and a lease naming one cannot
  be satisfied, so the first push of a branch would fail as a refused lease — the one thing
  it is not. If the remote cannot be asked at all the lease stays, because an unnecessary
  lease costs a retry and a dropped one costs somebody else's commits. A refused lease names
  the retry — a `git fetch` and a push leasing on what the fetch brought back — so pasting
  it is a decision taken after looking rather than instead of looking. A push that fails for
  any other reason is reported as itself with the local rewrite left standing. WHICH remote
  is asked of the branch and not of the base: the base's remote is the one `--onto` fetches
  from, and answering both questions with it would send a topic branch to somebody else's
  fork on `--onto upstream/main`. A branch is pushed to the remote it tracks, or to `origin`
  when it tracks none — the common case, since a branch is flattened before its first push
  at least as often as after it — and the success note names that remote, because a
  destination nobody prints is a destination nobody checks. That `--onto` fetch is REQUIRED
  rather than attempted: a transient network or auth failure used to leave a stale
  `origin/<base>` on disk, the ancestry guard agreed happily about a base the remote had
  moved past, and the flatten built one commit whose parent omitted every integration change
  since — then force-pushed it successfully, because the lease protects the topic branch and
  has nothing to say about the base. Same work-loss class as the ancestry guard, through a
  door the guard cannot watch. `--dry-run` does not fetch at all, so a rehearsal changes
  nothing rather than moving `FETCH_HEAD` and the remote-tracking refs on the way past; it
  reads the base as this clone already has it and says so among the notes.

- Refuse to flatten a branch whose open pull request has unresolved review threads, unless
  `--orphan-comments` says to. Inline review comments are anchored to commit SHAs. Replace
  those commits and GitHub marks every thread outdated: it collapses, it stops appearing
  against the code it was about, and nobody is prompted to answer it again. That is not
  hypothetical — 31 review comments were posted inline across five pull requests and 26 of
  them merged unaddressed, partly because nobody, human or tool, was looking. The refusal
  LISTS the threads it is refusing over — author, file, line, and the first line of the body
  — because a refusal nobody can act on is a refusal everybody routes around; and
  `--orphan-comments` then says yes on purpose, with the notes still naming what it cost.
  When `gh` is missing, unauthenticated or failing, the answer is that the check **could not
  be made** and the flatten proceeds: a check that did not happen must never read as one
  that passed, so "not checked" and "none unresolved" are different sentences rather than
  one comfortable one. The same rewrite also stales the "referenced this in commit" entries
  on every issue and discussion the range's commits mention. Nothing can save those — there
  is no trailer to carry and no keyword to preserve — so they are reported, in the notes and
  in `--dry-run`, and the operator decides.

- Look for the provenance and co-author trailers where git keeps trailers, which is the
  final paragraph and nowhere else. Searching the whole message meant a body sentence
  opening `Made-With:` — exactly how one writes ABOUT this tool — suppressed the provenance
  trailer the commit needs to pass its own gate, and a body line quoting `Co-Authored-By:`
  suppressed the real attribution for whoever it displaced. One helper now answers every
  question about the trailer block, because three copies of "is this a trailer block" drift,
  and the drift shows up as a trailer written twice or not at all.

- Refuse to replace a live documentation channel with an empty directory. A Pages deploy
  replaces the whole site, so the run publishing one channel restores the other from its last
  artifact — and when that restore failed the job emitted a **warning** and deployed anyway,
  republishing the other channel as an empty directory the chooser still links to. A warning
  does not prevent a deploy: every documented `main/` URL served Pages' 404 page — the book,
  the EPUB, the print HTML, the paper, the governance corpus, every runbook — while the job
  stayed green, which is why it went unnoticed. The two cases are now distinguished instead of
  warned through. If the other channel is **live**, this deploy would destroy it: the job fails
  and names the URL, the branch to republish, and the re-run. Liveness is decided on an
  explicit **404** and nothing else: `curl -f` exits non-zero for a timeout, a DNS or TLS
  failure, a 403 and a 500 alike, so keying it on the exit status would read a transient
  blip as "never published" and delete a live channel — failing open in the one guard
  whose job is to fail closed. Six cases are covered by a focused test that drives the
  rendered step with a stubbed `curl`. If it was never published there is
  nothing to lose, so the empty directory is dropped and the publish proceeds with one channel —
  the ordinary first publish of a new adopter, which failing outright would have broken.

- Stop `doctor` calling valid configuration an error, and make the drift that caused it a test
  failure. `_SECTION_KEYS` is hand-written for the sections whose keys load onto `GhConfig`
  itself, so it drifts from the loader silently — and the drift is not a missing hint, it is an
  **error** that exits nonzero and tells an adopter their working table "does nothing". Four
  things had fallen out: `install.self_source`, plus the whole of `[social_signals]`, `[tidy]`
  and `[workflow_names]` — `[tidy]` while carrying a documented section of its own and being
  named in this repository's own configuration comments. A new test asserts every section the
  loader reads is a section `doctor` knows, derived from the loader rather than from a second
  hand-written list, because a hand-written list is the thing that broke.
- Stop `doctor` calling `[install] self_source` an error. The loader reads it, this repository
  declares it, and the hand-written known-keys map in `doctor` did not list it — so the
  adoption preflight reported *"not a key vibey-gh reads; it is silently ignored"* at **error**
  severity, which exits nonzero and tells an adopter to delete a setting that works. That key
  is specifically the one that stops a workflow searching a pull request's own files for a
  `pyproject.toml` to install, so the advice was actively harmful. The regression test asserts
  the loader and the map agree about it.

- Find the other documentation channel by ARTIFACT NAME, not by searching runs. Each publish
  deploys the whole site, so the run for one channel restores the other from that channel's
  last artifact — and both previous lookups searched runs, both failing. `gh run list --limit
  20` with no branch filter walked the twenty most recent runs on any branch, and every
  integration publish took one of those slots, so after twenty merges in an afternoon the last
  release run fell out of the window. Adding `--branch` looked like the fix and was strictly
  worse: it never matches. A `workflow_run` run is attributed to the DEFAULT branch and a
  `workflow_dispatch` run to the ref it was dispatched on — neither is ever the release branch
  — so the filter found nothing on every publish and shipped the other channel as an empty
  directory the chooser still linked to. Observed as a 404 on every documented `main/` URL: the
  book, the EPUB, the print HTML, the paper, the governance corpus, every runbook page. Five
  unexpired `docs-main` artifacts existed the whole time. The artifacts endpoint takes the name
  directly, returns newest first and reports expiry, so branch attribution stops mattering.

- Separate checking a commit subject from rewriting it, and make the rewrite a key.
  `conventional-commits.yml` normalised every nonconforming subject automatically, which
  is a convenience and not the point of the job — and the automatic form is
  `chore: <the original subject>`, conforming without choosing a type, so a bug fix
  normalised that way is filed as a chore. In a repository whose changelog sections are
  derived from the type, that is a wrong label rather than a missing one. New
  `[pr_automation] normalise_commit_subjects` (default **true**, so no adopter loses the
  behaviour they have) splits the job into a check that always runs, a rewrite behind the
  key, and a refusal that names the offending subjects when the key is off.
- Refuse a workspace member whose marketplace name is the root's. Claude Code registers
  one marketplace per NAME per user, so `/plugin marketplace add` on a member answering to
  the root's name is not a second entry — it is the same registration twice, and whichever
  is added second silently replaces the first. The root manifest is rendered FROM the
  members, so the collision is between a thing and its own source. The existing
  duplicate-plugin check could not see it: those names collide one level down, among a
  manifest's plugins, not between manifests. `MarketplaceRenderer.build` now names the
  offending member and stops.
- Let the merge train clear the conflicts it creates itself. Every merge into the
  integration branch leaves the NEXT pull request behind the branch that just moved, and
  the train reported that as `conflicts with develop` and stopped — so it landed one
  change per run and a person merged the base forward by hand for every one behind it.
  Measured on nine open pull requests: each became unmergeable the moment its predecessor
  landed, and every one of them merged cleanly on a local `git merge`. GitHub calls them
  conflicting because its server-side merge runs without this repository's
  `.gitattributes`, so a path declared `merge=union` — the changelog every branch appends
  to — conflicts there and resolves here. `reconcile.merge_forward` already did exactly
  this for `reconcile-branches`; the train now uses it rather than carrying a second copy,
  and reports `restacked` instead of skipping. The restacked pull request is deliberately
  NOT merged on the same pass: its tree has changed, so its green checks describe a tree
  that no longer exists, and the next train takes it once they have re-run. Turn it off
  with `[merge_train] restack_conflicts = false`, for a repository that will not have
  automation push to branches it does not own; forks are excluded either way.
- Do the merge-forward in a throwaway worktree instead of detaching HEAD in the
  operator's own checkout. `merge_forward` ran `git checkout --detach` in the working tree
  somebody was using, which moved them off their branch without asking — and when a
  checkout failed partway, left files from another commit in the tree with no merge in
  progress to abort and no way to tell that wreckage from their own edits. Observed with a
  single unwritable path under `.claude/skills/`. A worktree cannot do either, and it
  means the merge no longer needs a clean tree: running the train by hand had been a
  choice between finishing the merge and keeping your work in progress. The worktree is
  removed in a `finally`, because a leftover registration makes the next `worktree add`
  refuse at the same path.
- Stop the documentation site deleting its own other channel. Each publish deploys the
  WHOLE site, so the run for one channel restores the other from that channel's last
  artifact — except it searched `gh run list --limit 20` with no `--branch` filter, while
  the branch it needed was the only one that ever produces the artifact. Every integration
  publish takes one of those twenty slots, so after twenty merges the last release run
  falls out of the window, the restore silently fails, and the deploy publishes the other
  channel as an EMPTY directory that the channel chooser still links to. Observed as a 404
  on every documented `main/` URL — the book, the paper, the governance corpus — after one
  day of merges, with nothing red anywhere to say so. `other_branch` was already computed
  and already passed into the step's environment; it was simply never used. The listing is
  now filtered to it, so twenty runs spans months, and a restore that still finds nothing
  raises a `::warning::` naming the branch it searched instead of a notice nobody reads.

- Stop the clean-repo survey reading a JSON object as an empty listing, and record why it
  must stay uncredentialed in CI. `_gh_json` answered `(value, "")` for a JSON *object* as
  readily as for a list, and both of its call sites are listing endpoints; iterating a dict
  yields its keys, so an error envelope such as `{"message": "Bad credentials"}` would
  enumerate field names, match no branch and no release, and report a clean survey with no
  problem recorded — "could not look" wearing the face of "nothing there", which is the one
  collapse that seam exists to prevent. Listings now go through `_gh_list`, which names a
  non-list answer as the non-answer it is; `_gh_json` keeps its general contract for any
  future endpoint that does return an object.

  The survey still reports `not surveyed` inside `Provenance`, and that is now a decision
  rather than an oversight. Supplying `GH_TOKEN` there was tried and reverted: the job
  installs the tooling from the *checked-out tree* where a repository self-hosts, so on a
  pull request the credentialed step would be running the contributor's own code, and a
  token in that environment is a token handed to whatever the pull request contains. The
  template now says so where the mistake would be made, and a new template contract test
  asserts structurally that no step of that job declares `GH_TOKEN` or any `secrets.`
  value — structurally, because the warning comment names `GH_TOKEN` and a text search
  would read the warning as the fault. A credentialed survey belongs in a job whose
  checkout is trusted, which is its own change.
- Make the package's own 100% branch floor reachable without a network, and gate it in CI.
  The branch that records a re-locked `uv.lock` after a version bump had exactly one
  reader: a test that resolves against a real package index. Offline the suite landed at
  99.97%, so the floor only held where PyPI did. It is now driven by a fake `uv` on PATH —
  a real subprocess, asserting argv and cwd, not a mocked one — and a plain `pytest` with
  no network reaches 100.00% with no flag to remember. Tests that leave the machine are
  marked `network` and skipped unless `VIBEY_GH_NETWORK_TESTS=1`; that replaces the
  second, incompatible convention this package had grown for the same job, so there is one
  marker, one environment variable and one skip rule. CI gates on the offline suite; the
  `network` tests run as a separate, non-blocking report on one matrix row, because a
  failure there is news about somebody else's service and not something a pull request
  author can fix.
- Make the exported book a valid EPUB. Chapters were taken from the built site's HTML
  verbatim, so every mkdocs permalink anchor carried `&para;` into the package -- and
  `&para;` is not one of the five entities XML defines, so an EPUB reader failed to parse
  the first heading of every chapter and refused the whole book. The same permalink
  pilcrows were also printed as visible furniture in a paper interior where nothing is
  clickable. A new `ChapterSanitizer` (with its interface beside it, per ADR-0016) now
  owns both halves of that judgement: it drops site chrome -- including any element
  carrying a permalink class -- and rewrites what survives as XHTML, resolving named
  entities to the characters they name, escaping bare ampersands, and rebuilding start
  tags so boolean attributes and attribute values are legal. Which tags and classes count
  as chrome are constructor arguments, so a theme that marks its permalinks differently
  configures the sanitizer instead of forking it.

  Three further ways a chapter could reach the package unparseable, all of which fail the
  whole book rather than the page they came from. The walk tracked NESTING DEPTH as a
  count, but HTML lets an end tag be omitted -- `<ul><li>one<li>two</ul>` is valid -- and
  `HTMLParser` synthesizes nothing, so a counter closed the wrong number of elements; it
  now holds the open elements by name, closes whatever an end tag actually closes, and
  closes what the document leaves open at end of input (`close()`, declared on the
  interface, because `out` is only well-formed once the caller says no more markup is
  coming). Elements HTML implicitly closes -- a second `<li>`, `<dd>`, `<td>`, `<tr>`,
  `<option>`, `<p>` -- are closed as siblings rather than stacked, because a list nested
  inside its own first item is well-formed XML and still the wrong book. And `text()`
  escaped the three markup characters while letting XML's FORBIDDEN code points through:
  `character_reference` already refused `&#0;`, but a literal NUL or form feed from the
  built HTML reached the output and made the chapter unparseable, so the same predicate
  now applies to character data.
- Read the machine's memory on Linux, and fail loudly on a machine that cannot be read.
  `vibey-gh fit` sampled memory only through macOS's `sysctl` and `vm_stat`, so on Linux
  every field came back zero and a machine with 32 GB free was reported as having none —
  a silent wrong answer where doctrine 10 requires a loud one. A `LinuxMemorySampler` now
  reads `/proc/meminfo`, and prefers the cgroup limit when one exists
  (`/sys/fs/cgroup/memory.max`, then `memory/memory.limit_in_bytes`) because inside a
  container `/proc/meminfo` describes the host rather than the machine the work will run
  on. When neither can be read, `Machine.readable` is false, `decide()` returns `floor`
  with the reason, and the CLI says the reading is unknown rather than empty. The samplers
  sit behind `vibey_gh/interfaces/` (ADR-0016) and read through an injected file-reader
  seam, so the Linux paths are covered by fixtures on any platform.

  The cgroup files are read where this process's limit actually lives, not only at the
  hierarchy root. A container on a host-mounted hierarchy -- Docker, Kubernetes -- is not
  at the root: `/sys/fs/cgroup/memory.max` reads `max` there while the real ceiling sits
  under the path `/proc/self/cgroup` reports, so reading only the root fell through to
  `/proc/meminfo` and projected on the HOST's memory, which is the one mistake preferring
  the cgroup exists to avoid. Each configured path now gains its nested equivalent AHEAD
  of the root: ahead, not instead, so a derived path that does not exist simply falls
  through and a host at the root behaves exactly as before. The memory controller's own
  line is preferred over the unified v2 line, because under v1 a sibling controller can
  sit at a different path entirely. `proc_self_cgroup_path` is a constructor argument
  like every other path here (ADR-0018).
- State in one place which review judgments a diff can carry. The pull-request review asks
  for nineteen answers, but two reviewers answer it from different evidence: the paid
  exact-head reviewer reads the whole proposed repository, while the local fallback sees
  one diff. Which half is which lived implicitly in three places, and one of them was
  already misread -- `audience_order` is reported unevaluated and yet emitted as `true`.
  The new `vibey_gh.review_contract.ReviewContract` (declared by
  `vibey_gh.interfaces.ReviewContractPort`) names the diff-groundable fields, names the
  documentation-contract fields that need wider context, and says plainly that the `true`
  is a shape-compatibility placeholder rather than an answer. `local_review` now reads its
  schema's `required` list and its `UNEVALUATED_FIELDS` from the contract instead of
  restating them, and a test holds the contract against the review schema shipped in
  `templates/workflows/pr-automation.yml`.
- Declare a branch's merge queue in `.vibey-gh.toml` and reconcile it like every other
  rule. `rulesets.py` already owned `deletion`, `non_fast_forward`,
  `required_linear_history`, `pull_request` and `required_status_checks`; a merge queue
  was not modelled at all, so the one part of branch protection that decides *when* a
  merge happens was settings-page state with no history, no review and no way to restore
  it — the condition ADR-0018 exists to end. New `[rulesets.<branch>.merge_queue]` carries
  all seven parameters GitHub requires (`merge_method`, `grouping_strategy`,
  `check_response_timeout_minutes`, `max_entries_to_build`, `max_entries_to_merge`,
  `min_entries_to_merge`, `min_entries_to_merge_wait_minutes`), because a value fixed in
  the tool is a decision taken away from the adopter. `enabled` defaults to **false**: a
  queue changes when every merge happens for everyone, and upgrading a tool must not do
  that. The integration branch defaults to `SQUASH` and the release branch to `REBASE`,
  matching the branch flow each already declares, and a queue that would create merge
  commits under `require_linear_history` is refused at load rather than once per queued
  pull request. The `provenance.yml` template now also answers `merge_group` events: a
  queue only ever sees checks that a merge-group run started, so a required check that
  does not trigger there ejects every queued pull request on timeout.

- Make the clean-repo survey inside `check --ci` safe where the forge cannot be reached.
  `_gh_json` now distinguishes "the forge answered" from "the forge could not be asked":
  a missing `gh` binary no longer raises an uncaught `FileNotFoundError`, and a non-zero
  `gh` exit (an unauthenticated or rate-limited runner) is reported as a named problem
  instead of being swallowed into an empty listing. Classes that could not be looked at
  drop out of the verdict entirely, so an absent forge can never be read as a clean one
  and can never name a live open-pull-request head as merged clutter. `check` also no
  longer runs `git fetch --prune`: a read-only verification command does not mutate the
  clone it verifies, and it acquires no network dependency. Under `--quiet` the survey is
  skipped unless `[tidy] fail_check` is on, where alone it could still move the exit code.

- Run the clean-repo survey inside `vibey-gh check --ci`. Sub-doctrine 9.a promised the
  cloud clutter classes were surveyed there, and they were not: `tidy.py` exposed the
  survey and `check` never called it, so clutter was only ever found by someone who
  remembered to run `vibey-gh tidy`. `check --ci` now reports merged-and-undeleted remote
  branches, draft releases, and orphan tags as named problems. It only reports — `check`
  runs on every commit and in every pull request, so it deletes nothing, ever, and
  `vibey-gh tidy --apply` remains the only thing that removes anything. The verdict is a
  key rather than a hard-coded judgment: new `[tidy] fail_check`, default `false`, prints
  the clutter as an advisory line, because the survey judges a repository's accumulated
  past and an adopter upgrading into this release must not find its CI red over branches
  that were already there. Set it true once the repository is clean, and clutter can never
  come back. `[tidy] enabled = false` turns the survey off entirely, and no survey runs
  under a local hook, which must not pay for a fetch and two `gh` calls.
- Add `vibey-gh marketplace` and the `[marketplace]` section: one Claude Code marketplace at
  the repository root, rendered from the workspace members' own manifests. `/plugin
  marketplace add owner/repo` reads exactly `<repo>/.claude-plugin/marketplace.json`, and a
  monorepo that absorbed its marketplaces as members (vibey ADR-0021) had nothing there —
  `the-vibey-project/vibey: no readable .claude-plugin/marketplace.json`. The root manifest
  now carries every member's plugins with their sources re-rooted, under a name of its own
  (Claude Code registers one marketplace per name per user, and each member's package still
  ships its manifest under its own name). `--check` and `check` report drift; a member
  defect is a named error. `MarketplaceRenderer` arrives with its seam declared in
  `vibey_gh/interfaces/` (vibey ADR-0016), the package's first.

- Add `vibey-gh book --site-dir site --title T --author A`, which exports the already-built
  documentation site as a book: a valid EPUB 3.0 package with Dublin Core metadata, and a
  print-ready HTML sized to the standard 6in x 9in KDP paperback trim. Chapters come from
  the site's own nav, in nav order, so the copy doctrine's tier ordering carries into the
  book unchanged. Stdlib-only, like the rest of the package.

- Let the local review fallback reach a pull request the diff API refuses. GitHub's diff
  API refuses a pull request beyond roughly 300 changed files, which is exactly the shape
  of a migration or adoption sweep — observed on a 347-file provenance sweep that could
  therefore never be reviewed at all, paid or local. The fallback job now reconstructs the
  same merge-base diff itself when `gh pr diff` fails: it fetches the base and head refs,
  deepens a shallow trusted checkout until their histories connect, and diffs one against
  the other. That reconstruction is read-only and executes no repository code, so the
  no-execution guarantee is untouched, and `max_diff_chars` still caps what reaches the
  model either way.

- Add an optional `[documentation] google_site_verification` setting: the bare Search
  Console "HTML tag" verification token, rendered as a `<meta
  name="google-site-verification">` tag on every published documentation page and the
  channel-picker landing page so verification survives Pages redeploys. Restricted to
  `^[A-Za-z0-9_-]{1,128}$`, which also rejects a pasted whole `<meta>` tag.
- Stop the required automation document from hijacking an adopter's front page. GitHub
  resolves a repository's landing README as `.github/README.md` first and the root
  `README.md` only if that is absent — so requiring `.github/README.md` replaced every
  adopting repository's *product* README with maintainer-facing automation notes, on the
  page a user lands on. Both this project and its first adopter were serving the wrong
  document, and nothing written inside the file could change it: the name is what GitHub
  reads. The required file is now `.github/AUTOMATION.md`, configurable as
  `[documentation].automation_doc`, and `github_readme_sections` /
  `github_readme_min_words` are renamed to `automation_doc_sections` /
  `automation_doc_min_words` — the former names are still read, so existing configuration
  keeps working. An adopting repository should rename its own `.github/README.md` to
  match, which is what makes its product README the one GitHub shows again.

- Stop the gate deadlocking on a pull request with nothing wrong with it. Two faults met.
  The rollup counted `Evaluate current head` — the job computing the rollup, still running
  while it counts — so the state reads "pending" from inside its own run; that survived
  only because a later run saw the earlier evaluate completed. And `Conventional Commits`
  gated through its `enforce` check while being absent from `scan_workflows`, which is
  also what `pr-automation.yml` renders into its `workflow_run` trigger, so finishing
  announced nothing. Put together: the last scan fires the final evaluation, `enforce`
  completes after it, and no run ever looks again. The pull request sits blocked with
  every check green, nothing failing and nothing to rerun, until the scheduled backstop
  notices hours later. Every job this workflow publishes is now excluded from its own
  rollup, pinned against the template so a job added later cannot start gating itself, and
  `Conventional Commits` is a scan workflow so its completion re-triggers evaluation.

- Let a repository that *is* vibey-gh run its own working tree. The hooks resolved
  `command -v vibey-gh` first, so a globally installed copy won — and since `develop` is
  ahead of the last release nearly always, that copy compared the repository's managed
  assets against the older ones it bundles, called them out of date, and refused the push
  with a provenance error that had nothing wrong behind it. Installing the CLI the obvious
  way, to satisfy an adopting repository's hook, was enough to lock this one. The hooks now
  detect self-hosting the same way the workflow templates already do — `name = "vibey-gh"`
  in `pyproject.toml`, plus the package directory — and run `python3 -m vibey_gh.cli`
  against the checkout, which needs no install and no virtualenv because the package is
  dependency-free stdlib. An adopting repository matches neither condition and falls
  straight through to its installed CLI, exactly as before.
- Finish the code-block colours: give every token a legible default rather than naming
  them one at a time. The previous pass covered strings and keywords and missed
  `.hljs-subst`, so `$(git rev-parse HEAD)` inside a shell string stayed at 1.33:1 — in
  the very example that tells a reader how to list their check names. `.hljs-code` and
  `.hljs-formula` were under the line too, at 4.06:1. A catch-all now sets a readable
  colour for any token, including ones this stylesheet has never heard of, and the palette
  overrides the ones worth distinguishing; it precedes the palette because an attribute
  selector and a class have equal specificity and source order decides. The contrast test
  could not have caught this on its own — it measured the colours that were declared, and
  the broken token had none — so a second test asserts the catch-all exists and comes
  first.

- Make code blocks readable on the published documentation site. The theme ships two
  highlight.js palettes and enables the *light* one by default (`#hljs-dark` carries
  `disabled`), so its token colours are chosen for a white page — while this stylesheet
  paints every code block `#080c17`. A string literal rendered `#032f62` on near-black,
  a contrast ratio of 1.48:1 against a 4.5:1 standard: not merely low-contrast but
  genuinely unreadable, and a configuration sample is mostly string literals. The
  stylesheet now supplies its own token palette, every colour of it measured at AA or
  better, covering both `.hljs-*` and the Pygments classes a `pymdownx.highlight` site
  emits instead. A test computes the contrast of every token colour against the forced
  background and fails below AA, since "looks fine to me" is what shipped this.
- Say why a model call failed, at every AI step. The action reports only
  `--json-schema was provided but Claude did not return structured_output` — the symptom —
  and the gate then tells an operator to check a log that does not contain the cause. It
  is in the execution record the run already writes: an immediate `is_error` at zero cost
  with an empty `modelUsage` is the API refusing the call outright, which is a different
  thing from a model that answered badly, and the two want different responses. Each step
  now reports `is_error`, `subtype`, turns, cost and model-call count into the job summary,
  quotes what the run said, and adds an explicit note when there were no model calls at
  all. A failure that genuinely burned tokens does not get that note, so exhausted credit
  and an exhausted turn budget stop looking identical. The step runs only on failure and
  never masks it, and the quoted text is fenced rather than interpolated, since model
  output may echo the pull request.

- Stop shipping this project's own self-test to the repositories that install it.
  `api-drift.yml` calls `vibey_gh.surfaces.parity()` — a statement about vibey-gh, not
  about an adopter's product — yet it was a managed template installed everywhere *and*
  named in the default `scan_workflows`. An adopting repository therefore received a
  required-looking gate that tested this library, and had to work out on its own that it
  should be excluded again; at least one did exactly that, permanently, with a comment
  explaining why. It is now hand-authored in this repository alongside `ci.yml` and
  `release.yml`, which already establish that repository-specific workflows are that
  repository's to author. Adopters get neither the workflow nor the scan entry. A
  repository that had excluded it can drop that exclusion.
- Add `[ai]`, so the AI steps can be pointed at an endpoint other than Anthropic's. Every
  one of them runs Claude Code, which honours `ANTHROPIC_BASE_URL`, so a gateway serving
  the Anthropic Messages API — LiteLLM and similar translate it to Gemini, Qwen, GitHub
  Models, or a model on your own hardware — is the whole of what it takes. Teaching five
  workflows a second vendor's request shape would buy nothing the gateway does not.
  `base_url` empty keeps the current endpoint, so nothing changes until asked, and
  `auth_secret` names a repository secret rather than carrying a token, because this file
  is committed. All seven call sites carry the hook, asserted by a test: a missed one
  would keep billing the original endpoint silently. The whole `env:` block is emitted or
  omitted rather than set empty, since an empty `ANTHROPIC_BASE_URL` points at nothing
  rather than at the default, and the secret fills both header conventions because Claude
  Code sends `x-api-key` while some gateways read `Authorization`.

- Install the packages a documentation site actually declares. The published-site build
  named exactly `properdocs` and its theme, with no way to extend the list, and ProperDocs
  depends on none of the plugins a real site configures — so a repository whose
  `properdocs.yml` used `mkdocs-gen-files`, `mkdocs-literate-nav`, a Material theme, or any
  `pymdownx.*` extension failed the `--strict` build on the first one it reached. Adding
  them was impossible without forking the workflow. `[documentation].site_requirements`
  now extends the install, a `site_requirements_file` (`docs/requirements.txt` by
  convention) is installed when present, and `properdocs_version` is no longer hardcoded.
  Each requirement is shell-quoted, so a specifier carrying spaces or extras stays one
  argument; a newline in one is refused at load time rather than quoted away, since it
  would otherwise end the install line and begin an arbitrary command. Both hooks are
  no-ops by default.
- Remove `README_SECTIONS`, `GITHUB_README_SECTIONS`, and `MERMAID_REQUIRED_TERMS` from
  `vibey_gh.documentation`, along with their unreferenced twins in `vibey_gh.config`. The
  documentation contract became configuration, and these were the literal copies left
  behind — importable, but describing *this* project's docs, which is exactly what an
  adopter is not held to. A repository wanting these headings declares them under
  `[documentation]`. `README_PROVENANCE` is unaffected and still enforced.
- Require checks that can actually report, and keep a way out when they cannot. The
  default `required_checks` were built from `scan_workflows`, which names *workflows*; a
  required status check names a *check run*, which for Actions is the job's name. So a
  fresh install demanded "CI", "Docs", and "API drift (Cloud Agents OpenAPI)" — three
  contexts nothing produces. That does not fail, it waits: the branch reports "N of M
  required status checks are expected" forever. And because a ruleset has no "include
  administrators" toggle the way the branch protection it replaced did, an empty
  `bypass_actors` meant nobody could merge past it, owner included. The defaults now name
  jobs the bundled templates actually render, `bypass_actors` defaults to the repository
  admin role, and a test asserts every default check is a job some template renders.
- Actually send the ruleset request body. `gh api` ignores stdin unless told to read it, so
  every reconciliation failed with HTTP 422 "data cannot be null" while the payload it had
  built was perfectly good — it simply never left the process.
- Merge the integration branch forward locally when GitHub refuses to. Its update-branch
  endpoint declines a branch it considers conflicting, which is exactly when a branch needs
  moving forward, and it computes that without this repository's merge drivers — so a
  changelog every branch appends to conflicts there while merging cleanly here. The
  fallback is an ordinary merge commit pushed without force: the branch moves forward and
  is never rewritten, and forks stay untouched.
- Report why an update was refused instead of "no detail reported".

- Identify a comment the same way whichever GitHub API produced it. A webhook numbers a
  comment; `gh issue view` returns a GraphQL node instead. They name the same comment and
  never match each other, and `int("IC_kwDO...")` raises — so the first real mention ever
  sent to the conversation feature crashed before it could answer. The numeric form,
  recovered from the comment's own URL when only the node is given, is now the single
  identity stored and compared.
- Rename the mention trigger to `@vibey-gh`, matching the tool's own name.
- Stop imposing this project's documentation contract on the repositories that install it.
  A project using vibey-gh as a dependency was required to carry a `## Why vibey-gh`
  heading in its own product README, this tool's branded provenance sentence verbatim, an
  and an architecture diagram naming this tool's modules — none of which describe the
  adopter's product. Those narrative requirements are now configuration with no default, so
  an adopter declares what *their* documentation must contain. The agent-docs layout still
  applies to every managed repository, because those files describe the adopter's own
  project and make it navigable to an agent; only their vibey-gh-specific contents are no
  longer demanded. This repository's own contract is unchanged: it declares the narrative
  requirements explicitly in its `.vibey-gh.toml`, so its internals stay fully documented
  and enforced.
- Make the generated release commit a Conventional Commit. `Release 1.23.0` does not stay
  on the release branch: any topic branch that later merges the integration branch in pulls
  it into its own commit range, where the provenance gate reads it like any other commit
  and rejects the subject. That blocked a pull request outright, and bounded repair could
  not fix it because the problem was history rather than file content. Now
  `chore(release): 1.23.0`.
- Add `[install].pin_version` to pin every managed workflow's `pip install vibey-gh` to the
  exact version that rendered it (`vibey-gh==X.Y.Z`) instead of floating on the latest
  release. An adopter could not previously pin this by hand: `vibey-gh install` regenerates
  every managed file from its template, so an edited install line was reported as out of
  date and silently reverted on the next install. `vibey-gh install` now owns bumping the
  pin, so upgrading is an explicit, reviewable diff. Unset, behavior is unchanged. The
  self-hosting `pip install -e .` branch is never pinned.
- Fail `vibey-gh check` when a `[pr_automation].scan_workflows` entry names a workflow
  that exists but has no `pull_request` or `pull_request_target` trigger. Such a workflow
  can never complete for a pull request, so `state` never leaves `pending`, `gate` never
  runs, and — made a required check — no pull request could ever merge, silently and
  permanently. A name absent from `.github/workflows/` is left alone, since it may live
  elsewhere or under another name.

- Declare `CHANGELOG.md merge=union` in `.gitattributes` so branches appending to the same
  section merge instead of conflicting. Every open branch adds an Unreleased entry, so each
  merge stranded every other one on a conflict carrying no information — four manual
  resolutions in a single afternoon, and the reason automated branch reconciliation kept
  deciding to rebase and then failing to. Configurable through `[install].union_merge_paths`,
  and appended to an adopter's existing `.gitattributes` rather than rewriting it.

- Say so on the issue when a solution attempt produces nothing. An attempt that exhausted
  its turn budget left no branch, no label, and no comment, so twenty minutes and real
  tokens looked from the issue exactly like nothing having happened. The issue now receives
  one comment naming the agent's outcome and the usual cause, and is labelled so it is
  visible in a listing.
- Make the attempt's turn budget configurable through `[issue_automation].max_turns`.

- Report whether a branch reconciliation actually took effect, not merely what it decided.
  A rebase that conflicted and aborted printed exactly like one that succeeded and left the
  job green, so two stranded pull requests looked reconciled across four runs while neither
  branch had moved. The decision and its outcome are now printed separately, and a run that
  could not apply an action says how many.
- Stop `github-release.yml` from failing on a release-branch push that carries no version
  bump. A docs-only or tooling-only promotion is expected, by an adopting repository's own
  `version.content_paths`/`code_paths` configuration, to publish nothing new — `publish()`
  now treats a version already tagged at a different commit as that intentional no-op
  rather than an error, unless the new `[github_release] require_new_version` opts a
  repository into the stricter behavior.
- Answer a configured mention in a comment. Everything else here reacts to scans, issues,
  and branches; none of it could hear "also handle the empty case" written under a pull
  request. Mentioning `@vibey-gh` now has the automation read the thread and answer, and — on
  a pull request, from a trusted commenter — make the change and push one guarded commit.
  Outside commenters get no response unless a repository opts in, comment text reaches the
  model only as a bounded untrusted briefing, interactions per thread are budgeted, and the
  automation refuses to answer its own comments so a reply cannot recurse indefinitely.

- Keep a successful realign successful when its branch reconciliation cannot reach GitHub.
  Reconciliation is a follow-up that needs credentials some contexts do not have, and a
  branch left unreconciled is a nuisance rather than a reason to report the realign as
  failed and leave the caller believing the branches never converged.

- Normalize formatting deterministically in the repair job. The repair agent holds no
  shell, so it cannot run a formatter: it hand-formats, guesses the line length, fails the
  lint gate, and the next attempt reformats the other way — a loop that spends the whole
  repair budget without converging. The trusted step now runs the repository's own declared
  formatters, which read their settings from its configuration rather than from a guess.
- Reconcile the `ruff` and `isort` import rules, which were mutually unsatisfiable: each
  rejected the other's output for a module imported both plainly and under an alias, so no
  number of attempts could make such a file green. A test now proves the two agree and do
  not oscillate.

- Bring open branches forward automatically whenever the integration branch moves, so a
  conflict never accumulates. Automation-owned branches are rebased; every other branch,
  fork included, is merged forward through GitHub's own update-branch endpoint, which
  never rewrites a contributor's history and succeeds only where they enabled maintainer
  edits.
- Refill a spent repair budget on a daily schedule, itself bounded by
  `branch_sync.max_self_heals`, so a transient outage stops being a permanent halt that
  only a human notices — while a genuinely stuck pull request still stops for good.
- Terminally block any outside author's pull request whose head is a permanent branch or
  whose base is the release branch, so no untrusted work can steer automation at `develop`
  or `main` from either end.

- Reconcile open topic branches after realign rewrites the integration branch. A branch
  cut from a replaced commit previously reported a conflict covering work that had already
  landed, through nobody's fault. Realign now closes and deletes a branch whose commits are
  all upstream by patch identity, rebases an automation-owned branch that carries real
  work, and leaves a contributor's branch untouched with an explanatory comment. Every
  action is individually configurable through `[realign]`, and no permanent, fork, or
  unsafe ref can reach a mutating path.

- Resolve conflicts on draft pull requests instead of stranding them. Conflict is now
  classified before draft status: a conflicted draft could never be promoted, because
  promotion requires a clean merge, and conflict resolution never ran because it was a
  draft — so every conflicted branch-intake and issue-solution pull request deadlocked.
  Fork drafts still wait, because their conflict path closes the contributor's pull
  request.

- Bound the review-to-repair cycle for every author. The budget check sat behind an
  outside-author condition, so a trusted author's exact-head review could request repair
  after repair without limit; it is now applied wherever another review would be
  dispatched, which is the only point that is reachable while each repair publishes a new
  head.
- Persist the per-lineage attempt reset that was previously computed and discarded. A new
  human commit started a fresh lineage in the evaluation but never in the stored record, so
  the documented per-lineage budget silently behaved as a cumulative per-pull-request one.
  Both paths now share `lineage_for()` and cannot disagree.
- Add an optional, generic `[documentation] google_analytics_id` setting: configure any
  repository's own GA4 measurement ID to inject Google Analytics into every page of both
  generated documentation channels and the channel-picker page. Empty (the default)
  disables it entirely, emitting no script tag and making no request to Google.

- Fix `conventional-commits.yml` installing the adopting repository's own default-branch
  checkout and assuming that yields the `vibey-gh` CLI: it now detects genuine self-hosting
  the same way `provenance.yml` does and otherwise installs the published package, and the
  commit-conformance check fails loudly instead of treating "command not found" as a false
  `if` condition that then barrels ahead into a doomed history rewrite. Fix the same
  adopting-repo-assumption bug in four `pr-automation.yml` installation steps.
- Report the exact-head gate's outcome truthfully when the review, not the scans, decides
  it: a review that returned actionable findings and a review that returned no verdict at
  all are now distinct, named states instead of a failing check whose summary claims every
  scan and review passed.

- Add autonomous issue automation: an eligible published issue is evaluated by trusted
  policy code, implemented by a constrained agent that reads the issue only as bounded
  untrusted data, and published as one guarded solution branch and linked pull request
  that closes the issue on merge.
- Treat issue text as an adversary-controlled input to a privileged job: outside authors
  are opt-in behind a configurable maintainer label, the agent holds no shell, `gh`,
  subagent, or Git tool, and nothing derived from an issue reaches a shell command, a
  workflow expression, or a branch name.
- Budget autonomous solution attempts against a fingerprint of the issue's title and body,
  so a redispatch of unchanged text cannot spend the budget twice and editing an issue
  starts a new lineage with a new branch.
- Render `branch-intake.yml` to yield the configured issue-solution branch namespace, so
  branch intake and issue automation never race to open the same pull request.
- Extract durable marker-comment automation state into `vibey_gh.github_state`, shared by
  pull-request and issue automation instead of duplicated across them.

- Require advanced debug instrumentation for every Python control-flow branch and add
  opt-in, correlated, metadata-only JSONL tracing with tamper-evident SHA-256 chaining.
- Enforce genuine 100% line and branch coverage with pytest-cov and align all contributor
  and testing documentation with the executable gate.
- Fix a duplicated provenance header in the packaged source modules and make the
  fingerprint check detect and repair a header repeated within a file, not just a header
  that is missing.
- Treat concurrent PR-head advances during repair or conflict publication as stale no-ops
  while preserving ordinary non-fast-forward protection and never force-pushing.
- Check operator-block and budget-exhausted labels before conflict-resolution eligibility,
  so a blocked or exhausted PR no longer triggers automated conflict resolution.
- Stop flagging a marketplace plugin whose source is the repository root (`.`) as an unsafe
  external source.
- Rewrite the release-channel navigation "Home" link to the correct Pages root instead of
  leaving its `href` unset.
- Replace the placeholder GitHub automation README with a comprehensive operator guide
  and enforce its required sections, minimum depth, and exact provenance deterministically.
- Fix GraphQL-only PR-state comment updates, synchronize package version metadata,
  correct constrained Claude command patterns, and ship real managed CodeQL and
  five-surface API-drift gates.
- Validate the capability-keyed parity matrix in its documented orientation.
- Add a configurable comprehensive FOSS and multi-agent documentation contract.
- Add guarded AI documentation authoring and repair automation.
- Add configurable crawler, sitemap, SEO, structured-data, and LLM discovery surfaces.
- Enforce and safely self-heal Conventional Commit subjects on guarded topic branches.
- Require a comprehensive, current Mermaid architecture map at `docs/project.mmd`.
- Use the native GitHub workflow credential when persisting AI review and repair state.
- Run Claude Code Action from a disposable, credential-free Git context while keeping
  untrusted pull-request checkouts isolated from repository credentials.
- Add configurable sanitized Claude progress, restricted execution artifacts, and a
  fail-closed manual raw-output diagnostic restricted to private repositories.
- Keep promotion PR checks non-destructive: skip topic-history normalization for
  permanent branches and verify repository provenance without re-auditing admitted history.
- Give repair agents a bounded trusted diagnostic bundle containing exact-head failed
  check metadata and available failed-job logs before they classify or edit anything.
- Satisfy Claude Code Action's required `origin` through its token-free credential-helper
  path without authorizing non-write actors or persisting a token in Git configuration.
- Gate Claude progress comments to the direct PR and issue event types supported by the
  action, preserving phase-level visibility for automated workflow events.

## Historical releases

See GitHub Releases for versioned notes, tags, artifacts, and provenance attestations.
