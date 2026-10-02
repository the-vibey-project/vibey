# Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents

**Abstract.** A single autonomous coding session is not autonomous software delivery:
sessions lose context across crashes, exhaust one vendor's capacity mid-task, and
carry no structure for the human decisions delivery legally and practically
requires. We present a ledger-mediated orchestration model and the family of
components it is built from. All delivery state is a function of an append-only
ledger, $\mathrm{state}(t) = f(\mathrm{ledger}_{\leq t})$, which makes engine handoff a
scheduling event rather than a loss of state. Work items are claimed from a PostgreSQL
queue with `FOR UPDATE SKIP LOCKED` under renewable leases; a handoff between engines
is admitted only by a pure, model-free no-loss predicate; and delivery proceeds
through a six-phase state machine whose four human gates each require a recorded
verdict, which silence never supplies unless a project has declared, kind by kind, that a
deployment gate may resolve to its stored default. Beneath the orchestrator, five session-runner packages expose seven
selectable engine identities and share one bounded,
never-blocking core that never gives a credit balance a clock and lets a capacity
verdict outrank a completion claim. Above it, an exact-head release calculus binds
every automated verdict to the revision it evaluated and performs a bounded number of
repairs, terminating whenever each failing verdict carries a finding repair acts on.
Beside it, a deterministic retrieval engine and a fail-closed bootstrap layer apply the same append-before-act discipline. Finally, we report a
measured regularity from the project's own tracked records: on one machine, with the
model and deadline fixed, successful throughput stayed between 0.99 and 2.00
generations per minute while offered concurrency rose sixteen-fold. The regularity
yields a zero-shortfall time-to-completion as a testable prediction. We state what
would falsify it and what it does not cover, and we argue from the same records that
the scarce inputs were governance and correct judgment, not production. For the 3.0.0
release we add the database's own enforcement of the ledger invariant, with what it
does not cover; a priority lane, derived rather than remembered, that orders both
queues without preempting or admitting past any gate; an engine environment built from
an allow-list; and a local reviewer that refuses a verdict on a prompt it did not read
in full. We also report an audit of a local storm, whose working record is not tracked,
in which one model slot took 96.7% of lane time and no lane reached the integration
branch without a human step, and in which adversarial verifiers refuted 16 of the
audit's 18 leading claims. Releases 3.1.0 and 3.2.0 add an operator's exit that abandons
a project from any phase short of done, withdrawing its gates and releasing its
checkout; build branches that a project must prove are its own; a trust check before an
issue enters the delivery path; a gate that parks a job failing the same way again and
again; and a local reviewer that reviews a large diff whole, in bounded parts.
A scan of the integration branch on 2026-09-30 found that only BUILD ran without a
person and that the forty merges before it all went in through the ruleset bypass with
no review, and it found seven defects, three of them in the evidence a person is shown. We
report their repairs, an incident in which the merge train closed pull requests it
reported as merged, and a measurement of the local reviewer: given the full files it
judges, none of its seven false findings on four blocked changes returned, though that
measurement could not show its recall. After the scan, the reviewer's failures on large diffs were traced
to an answer nothing capped and a deadline that did not grow with the request; the repair
caps the one, scales the other and tells a busy model from a slow one. Every verdict the
lane has given since was on a diff it reviewed in one request; on each large diff it met
it gave none, and said why by name rather than timing out. An offline canary of planted
defects then measured the reviewer's recall for the first time: it caught 18 of the 25
small defects it judged (Wilson 95% interval 0.524 to 0.857) and blocked none of 14 clean
changes, and two of its misses passed while its own summary named the defect. Its first
weekly run caught 23 of 27 (0.675 to 0.941) and again blocked no clean change, a result
that reached the record only after we found and repaired the workflow that had dropped it.
A preregistered study of the large-diff failures is in progress and has finished its
screening. On its first screening diff, a request at temperature 0 looped to its cap with no
answer, and the same request sampled at temperature 1 answered in 368 tokens; on its
fourth, sampling alone failed as well, once with an empty answer and once with an answer
outside the response grammar. Five arms answered on all four diffs, every arm that bounds
the reasoning and then forces a verdict among them, and forcing repaired the one
ungrammatical answer it met. No arm's recall is measured yet, and production is unchanged. We also measure, weekly, how
far the delivery loop is from running without a person, one of eleven declared stages at
each of the three readings so far, and the health of the machine it runs on, whose memory
demand we measured at about twice its 24 GiB. Last, we read the 3.3.0 release as evidence.
It was the first to attach a build of every client, eleven files, each found to match its
checksum and to carry a build-provenance attestation, and it gave the editor extension its
first Open VSX listing. We also state what 3.4.0 adds: a self-contained desktop app for
macOS on Apple silicon, an iOS build signed for the App Store, a desktop client that pairs
with a hub by its one-time code over a pinned certificate, and a release path on which a
change to the clients alone is releasable.

*Artifacts.* This paper is typeset from `docs/paper.md` and published as
[PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/paper.docx) and
[HTML](https://the-vibey-project.github.io/vibey/main/paper/). The complete
documentation is published as a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/book.docx),
[EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) and
[print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html). Every
empirical figure in the section on production rate is recomputed from tracked sources:
`scripts/paper_evidence.py` recomputes its numbers, `scripts/paper_figures.py` redraws
its figures, the storm's `storm-evidence.py` regenerates its evidence table,
`scripts/minimum_specs.py` its table of minimum requirements, and
`scripts/autonomy_scorecard.py` its autonomy scorecard. The one exception, the storm
throughput audit, is named where we use it. The large-diff study we report is in
progress, and its committed record is cited at the cutoff its own log gives. Unless a
passage names its own, this revision's cutoff is `develop` at `3bb577a4e` (#1354), with
the forge read on 2026-10-02 between about 10:55 and 11:20Z; what this revision adds for
the 3.4.0 release is at `develop` at `4d51a764c` (#1365), with the forge read at about 17:45Z. The visual atlas holds forty-five
figures: thirty drawn from the model as deterministic TikZ in this source, and fifteen
computed from tracked repository records, so the PDF, its labels and its diagrams are
reviewable and reproducible rather than screenshots detached from the system. Every
section from the Introduction to the Conclusion, except Related work, closes with a box
headed *In plain words* that restates it for a reader who is not a specialist; the boxes
add nothing the formal text does not say, and a specialist may skip them.

```latex
\begin{plainwords}[The paper in plain words]
Computers can now write computer programs. But one robot programmer working alone is not enough to finish a real project. It forgets everything when it crashes. It runs out of its allowance in the middle of a job. And it does not know when a person needs to make a decision. Vibey fixes this with three ideas. First, a notebook that nobody can erase: every decision, every finding and every handoff is written in the notebook before it counts, so a new helper can pick up exactly where the old one stopped. Second, a queue with rules: jobs wait in line, a helper borrows a job for a short time and must keep renewing it, and a job that a crashed helper dropped goes back in the line by itself. Third, six checkpoints, and at four of them a person must say ``yes'' out loud before the work moves on. We also measured how fast one small computer can do this kind of work. It produced a steady one or two finished pieces per minute, and it did not get faster just because we asked for more at once. The slow part was never the typing. It was deciding well.
\end{plainwords}
```

<!-- vibey:provenance -->

## Introduction

Let an *engine* be an autonomous coding session runner over one vendor's model, and
let $E = \{e_1, \dots, e_m\}$ be a pool of such engines with independent failure and
capacity behavior. The delivery problem is to carry a specification from human
intent to deployed software using $E$, under three constraints that single-session
tooling violates: (i) no vendor session may be the source of truth; (ii) human
decisions must occur at defined points, not wherever a session happens to stall;
(iii) exhaustion of one vendor's capacity must not lose work.

The system that answers these constraints is one repository holding a family of
packages: the orchestrator `vibey`; five session-runner packages for `claudeloop`,
`codexloop`, `cursorloop`, `agyloop` and the dual-engine local runner that exposes
`gptossloop` and `qwenloop`; `vibey-gh`, which owns provenance,
merging and release; `vibey-skills`, a retrieval engine over a skill library; and
`vibey-bootstrap`, a bootstrap layer for cloud workloads. Each package once carried its
own paper. This paper consolidates them. [Fig. 1](#fig:family-tree) shows the family as
one distribution, with the Python floor each tenant keeps. Its contributions are:

- the ledger invariant, the no-loss handoff gate, the queue semantics and the gated six-phase machine, with their soundness arguments, and the database's enforcement of the first, stated with what it does not cover;
- a priority lane shared by both queues whose contents are derived rather than remembered, which orders work without preempting it or admitting it past any gate, and reapers that decide a hang by measurement;
- a session-runner core shared by five runner packages and seven selectable engine
  identities, whose capacity taxonomy never gives a credit balance a clock and whose
  completion rule a capacity verdict outranks, and an environment every engine starts
  from by allow-list;
- the exact-head release calculus, with a repair bound, the condition under which it terminates, and a recorded production counterexample, and its extension from the revision a verdict evaluated to the input the evaluating model actually read;
- Convergence-Driven Development (CDD), an enclosing loop above Specification-Driven
  Development and Test-Driven Development that measures convergence at nested delivery
  scopes, models project atoms and chemical structures, and recognizes a suite of
  suites as alive in the digital realm when its organism-level signals converge;
- deterministic, fail-closed retrieval and bootstrap components built on the same append-before-act discipline;
- Biodigitology, a name for the study of digital life, with operational criteria
  that distinguish software organisms from biological organisms or sentient minds;
- a measured production-rate regularity, its modulators, the time-to-completion prediction it enables, and the observations that would falsify it;
- an audit of a local storm that locates its binding constraint, its conversion losses and its unenforced controls, and a factual account of merges that ran ahead of review, both read as evidence that the scarce input is judgment;
- a scan of how far the delivery loop ran without a person, with the forge's record of who merged, the defects it found and their repairs, an incident in which the merge train closed what it reported as merged, and a measurement of the local reviewer with and without the files it judges, and the cause of that reviewer's missing verdicts on large diffs, with a repair that turns a silent timeout into a named refusal but has not yet brought a large diff to a verdict;
- the first measurement of that reviewer's recall, on planted defects, and its first weekly repetition, and a preregistered study of its large-diff failures reported as what it is, in progress: its mechanism and its completed screening, not its result;
- weekly measurements, generated into the text from append-only records, of how far the delivery loop is from running without a person and of the health of the machine it runs on;
- the 3.3.0 release read as evidence of what a release carries, a build of every client with its checksum and its provenance attestation, and the changes 3.4.0 adds to that set: a macOS desktop app, an iOS build, desktop pairing with a hub, and a release path that a change to the clients alone now reaches.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  run/.style={minimum width=2.45cm,minimum height=1.15cm},
  tool/.style={minimum width=5cm,minimum height=1.15cm}]
  % ---------------------------------------------------------------- the distribution
  \node[vibeycore,minimum width=5.4cm,minimum height=.95cm] (dist) at (8.875,0)
    {pip install vibey-engine\\\mdseries engine family; apps ship as krypton-app};
  \node[vibeytag,anchor=west] at ($(dist.east)+(0.18,0)$) {ADR-0037, ADR-0069};
  % ---------------------------------------------------------------- orchestrator
  \node[vibeybox,minimum width=2.8cm,minimum height=1.15cm] (vibey) at (1.65,-4.0)
    {\textbf{vibey}\\six-phase conductor\\queue on PostgreSQL};
  \node[vibeypill] at (vibey.south) {Python 3.12+};
  % ---------------------------------------------------------------- session runners
  \node[vibeysoft,run] (r1) at (5.125,-2.55)  {\textbf{claudeloop}\\paid tier};
  \node[vibeysoft,run] (r2) at (7.775,-2.55)  {\textbf{codexloop}\\paid tier};
  \node[vibeysoft,run] (r3) at (10.425,-2.55) {\textbf{cursorloop}\\paid tier};
  \node[vibeysoft,run] (r4) at (5.125,-4.2)   {\textbf{agyloop}\\paid tier};
  \node[vibeytealbox,minimum width=5.1cm,minimum height=1.15cm] (r5) at (9.1,-4.2)
    {\textbf{local runner package}\\gptossloop default $\cdot$ qwenloop opt-in};
  \node[vibeypill] at (r1.south) {Python 3.12+};
  \node[vibeypill] at (r2.south) {Python 3.12+};
  \node[vibeypill] at (r3.south) {Python 3.12+};
  \node[vibeypill] at (r4.south) {Python 3.12+};
  \node[vibeypill] at (r5.south) {Python 3.12+};
  \node[vibeybox,minimum width=7.75cm,minimum height=.7cm] (bar) at (7.775,-5.75)
    {\textbf{vibey-runners-common}\quad shared library of claudeloop and codexloop};
  \node[vibeypill] at (bar.south) {Python 3.12+};
  % ---------------------------------------------------------------- tools
  \node[vibeyvioletbox,tool] (t1) at (15.0,-2.55)
    {\textbf{vibey-gh}\\provenance, merge train,\\promotion, release, governance canon};
  \node[vibeyvioletbox,tool] (t2) at (15.0,-4.15)
    {\textbf{vibey-skills}\\retrieval engine over\\745 skill documents in 138 plugins};
  \node[vibeyvioletbox,tool] (t3) at (15.0,-5.75)
    {\textbf{vibey-bootstrap}\\fail-closed bootstrap,\\outbox, audit chain};
  \node[vibeypill] at (t1.south) {Python 3.12+};
  \node[vibeypill] at (t2.south) {Python 3.12+};
  \node[vibeypill] at (t3.south) {Python 3.12+};
  % ---------------------------------------------------------------- lanes
  \coordinate (p1t) at (1.65,-1.5);   \coordinate (p1b) at (1.65,-6.5);
  \coordinate (p2t) at (7.775,-1.5);  \coordinate (p2b) at (7.775,-6.5);
  \coordinate (p3t) at (15.0,-1.5);   \coordinate (p3b) at (15.0,-6.5);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(vibey)(p1t)(p1b)] (L1) {};
    \node[vibeylane,fit=(r1)(r3)(r4)(r5)(bar)(p2t)(p2b)] (L2) {};
    \node[vibeylane,fit=(t1)(t3)(p3t)(p3b)] (L3) {};
  \end{scope}
  \node[vibeylanelabel] at (L1.north west) {Orchestrator};
  \node[vibeylanelabel] at (L2.north west) {Session runners};
  \node[vibeylanelabel] at (L3.north west) {Tools};
  % ---------------------------------------------------------------- one package, three groups
  \draw[vibeyflow,rounded corners=3pt] (dist.south) |- (1.65,-0.85) -- (L1.north);
  \draw[vibeyflow] (dist.south) -- (dist.south |- L2.north);
  \draw[vibeyflow,rounded corners=3pt] (dist.south) |- (15.0,-0.85) -- (L3.north);
  % ---------------------------------------------------------------- notes
  \node[vibeynote,anchor=west,align=left] at (0,-7.15)
    {each tenant keeps its own pyproject, version, test suite and gates (ADR-0022), absorbed into one tree with history preserved (ADR-0021)};
\end{tikzpicture}
\caption{The two-package publication surface and the engine family. The dark box names the engine distribution; the apps publish separately as \texttt{krypton-app}. Beneath it sit the orchestrator, five runner packages (claudeloop and codexloop on their shared library), and three tools. Every tenant requires Python 3.12 or newer. The teal package exposes \texttt{gptossloop}, the sovereign default on GPT-OSS 20B, and opt-in \texttt{qwenloop}; \texttt{claudeloop-local} supplies the seventh selectable identity.}
\label{fig:family-tree}
\end{figure*}
```

The orchestrator itself is an onion of four layers with dependencies pointing inward
only ([Fig. 2](#fig:layer-map)): a pure `domain` with no I/O, no clock and no network;
an `application` layer of services; an `infrastructure` layer that talks to PostgreSQL,
the bus and telemetry; and the `cli` and `tui` shells. A single composition root,
`bootstrap.py`, wires them. The rule is enforced by `import-linter` in CI, and four of
the five layers fail the build under 100% branch coverage.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \draw[draw=vibeyline,fill=vibeymist,rounded corners=8pt,line width=.5pt] (0,0) rectangle (8.2,5.9);
  \draw[draw=vibeyblue!35,fill=vibeywash,rounded corners=7pt,line width=.5pt] (0.5,0.5) rectangle (7.7,4.85);
  \draw[draw=vibeyblue!55,fill=vibeyblue!9,rounded corners=6pt,line width=.5pt] (1.0,1.0) rectangle (7.2,3.8);
  \node[vibeycore,minimum width=3.6cm,minimum height=1.1cm] (domain) at (4.1,2.55) {domain\\pure: no I/O, no clock, no network};
  \node[vibeylanelabel] at (0.05,5.9) {cli and tui};
  \node[vibeylanelabel] at (0.55,4.85) {infrastructure};
  \node[vibeylanelabel] at (1.05,3.8) {application};
  \node[vibeypill,anchor=north east] at (8.15,5.85) {7,497 + 594 lines $\cdot$ cli 100\% floor $\cdot$ tui exempt};
  \node[vibeypill,anchor=north east] at (7.65,4.8) {26,018 lines $\cdot$ 100\% branch floor};
  \node[vibeypill,anchor=north east] at (7.15,3.75) {15,080 lines $\cdot$ 100\% branch floor};
  \node[vibeypill,anchor=north] at (4.1,1.85) {14,813 lines $\cdot$ 100\% branch floor};
  \node[vibeynote,anchor=west,align=left] at (1.1,4.35) {PostgreSQL, the bus, telemetry};
  \node[vibeynote,anchor=west,align=left] at (1.6,3.3) {services, handoff, wind-down};
  \node[vibeynote,anchor=west,align=left] at (0.6,5.4) {the command line and the terminal UI};
  \draw[vibeyflow] (0.3,2.55) -- (domain.west) node[midway,above,vibeynote,text=vibeyblue,align=center,yshift=1pt] {imports point\\inward only};
  \node[vibeybox,minimum width=4.2cm] (boot) at (4.1,-0.75) {bootstrap.py\\the one composition root};
  \draw[vibeyarrow] (boot.north) -- (4.1,0);
  \node[vibeynote,anchor=west,align=left] at (6.35,-0.75) {enforced by\\import-linter in CI};
\end{tikzpicture}
\caption{The orchestrator is an onion. Code may only depend on the layers inside it, and the pure domain at the centre never touches a database, a clock or the network. One file, bootstrap.py, wires the layers together from outside, and four of the five layers must keep every branch of their code tested. Line counts are read at revision d4c4e1f8, the revision the history figures are read at.}
\label{fig:layer-map}
\end{figure}
```

```latex
\begin{plainwords}
Think of a team of robot helpers, each from a different company. Any of them can quit halfway through a job. Vibey is the team captain. It keeps one shared notebook, hands out jobs one at a time, and stops at the right moments to ask a person. The rest of this paper explains each part, and then checks the whole design against real records from the project's own history.
\end{plainwords}
```

## The ledger invariant

```latex
\begin{invariant}[Write-ahead intent]
Every decision, finding, and handoff is a row in an append-only ledger before it
takes effect; consequently $\mathrm{state}(t) = f(\mathrm{ledger}_{\leq t})$ for a
pure $f$, independent of any vendor session.
\end{invariant}
```

The per-project sequence number is claimed inside the same transaction as the insert,
so every ledger range has a well-defined digest. Every event also has a link: the
SHA-256 of the link before it and every stored field of the event, from a genesis of
its own project (`vibey.domain.ledger_chain`). The chain is derived from the rows rather
than stored, so it covers all of history, and a published ledger shard carries its
verified chain head. It detects a rewrite, not a forged append. Corrections are new
events that supersede prior ones. The function $f$ is a set of pure projections (open items, the
decision log, the cost report) computed from the event sequence alone.

**Enforcement, and what it does not cover.** Until 3.0.0 the invariant held against
vibey's own queries and against little else. It rested on two `DO INSTEAD NOTHING`
rules on the partitioned parent `event`, and ADR-0055 records what a scratch database
with every migration applied (PostgreSQL 18) did on 2026-09-24 when addressed as the
role vibey connected as: an `UPDATE` of `event` changed nothing, silently; an `UPDATE`
and a `DELETE` addressed to the default partition changed and deleted rows, because a
rule on a partitioned parent does not fire for a statement addressed to a partition;
`TRUNCATE event` emptied the ledger, because rules never fire on `TRUNCATE`; and after
`DISABLE RULE` an update went through. That role owned the table, and in the Helm
chart it was also the image's superuser. The same DSN had reached every engine session
(see *What an engine may see*), so a session steered by text a model read held the
means to erase the ledger unrecorded.

The fix (#1100, ADR-0055) has two parts, because neither alone is a boundary. First,
triggers replace the rules (migration 0016): a `BEFORE UPDATE OR DELETE` row trigger
and a `BEFORE TRUNCATE` statement trigger refuse every rewrite, the owner's included,
with an error rather than a silent no-op. PostgreSQL clones the row trigger onto every
partition, present and future, but not the statement trigger, so a function attaches
the `TRUNCATE` guard to every partition on every migration run. (Migration 0019 later
adds a third trigger, `AFTER INSERT`, that announces each append to the hub's live feed
and writes nothing.) Second, the roles
split. The owner's DSN runs migrations and nothing else; the application role, which
every worker, command, operator and scaler connects as, owns nothing and holds on
`event` only `SELECT` and `INSERT`, with no `DELETE` or `TRUNCATE` anywhere. The grants
are declared in code, derived from the application's own queries, and reconciled on
every migration run, so a grant added by hand does not survive the next migration run. An
install still on one role is reported rather than stranded: `vibey doctor` fails its
`ledger-guard` check, the worker says so on every start, and `vibey migrate` exits 1.
The whole test suite now runs as a restricted application role; its first run found
35 failures, none a missing grant in application code: all were test setup doing
owner-only work, or tests that had asserted the old silent no-op (#1100).

The guard's reach is narrower than the word *append-only* suggests, and we state it.
As the application role, the independent review of #1100 tried updates, deletes and
truncations of the parent and of partitions, disabling, re-enabling as replica and
dropping the triggers, detaching and attaching partitions, and switching the session
to replica mode, and every one was refused (review probes of 2026-09-24). The merged
tests pin the refusals of updates, deletes and truncations of the parent and of a
partition, and of disabling or dropping the triggers; the rest remain review probes,
not tracked tests. The triggers refuse the owner's rewrites of rows, not
the owner's schema changes: the owner can still disable a trigger, drop a partition,
detach one and delete from it, or truncate a partition created since the last
`vibey migrate`, so the owner's DSN is the thing to guard. Event triggers that would
refuse such schema changes are future work, because installing them needs a
superuser. A superuser can do anything. The application role cannot rewrite what is
there, but it can still insert into `event` directly, so it can forge an event's
provenance, sequence number or production time, and it can update the sequence
counter `event_seq`; an append function running with the owner's rights, as the only
write path, would close that, and it is the next step, not a done one (ADR-0055,
*Not closed*). And the split protects the ledger only once the owner and every
superuser need a password: a local PostgreSQL that trusts its socket, the common
developer default, lets any process running as the right operating-system user
connect as a superuser with no DSN at all. ADR-0055 records exactly that on the
operator's machine, and #1100 shipped with a `local-auth` check in `vibey doctor`
that fails when such a connection is let in, passes only when every attempt is
refused and the authentication rules read clean, and otherwise reports unknown,
never a pass; changing the server's authentication rules is left to the operator
(`SECURITY.md` §7). Same user, same authority: no grant separates processes of one
operating-system account.

The same review found the design sound and five defects in its first implementation,
two of them rated high, and #1100 had merged while it said *not yet* (#1112's
description). #1112 closed all five and merged at 15:18Z on 2026-09-24 (ADR-0055, its
amendment; `CHANGELOG.md`). The worst: where the application role may create objects in
the `public` schema, the PostgreSQL 14 default and that of any database upgraded from
it, it could plant an operator that the owner's unqualified catalog query resolved
during `vibey migrate`, run code as the owner, and leave a backdoor that erased the
ledger while `migrate` reported the guard in force; ADR-0055, as first merged, had
judged that privilege harmless to the ledger. Now migration 0017 pins both guard
functions to `search_path = pg_catalog, pg_temp`, the owner's session is pinned the
same way and names every catalog operator by schema, `vibey migrate` takes `CREATE` on
`public` away from every role but its owner before any migration runs, and
`ledger-guard` fails when the application role may create objects, owns any, may call
a `SECURITY DEFINER` function that runs as the owner or a superuser, or may set
`session_replication_role`. The second: the owner's DSN reached any process whose
shell exported it, because `build_app()` read it and the README exported it; now only
`vibey migrate` reads it, given for that one command. The other three: the Helm chart
gave the owner's credentials to Plane and Infisical, which now connect as roles of
their own; an install with an existing Secret could be stranded on upgrade, and is now
unchanged until it names an owner key; and concurrent reconciles failed, and now take
the migration lock. Migration 0017 is new rather than an edit of 0016, because a
migration that may already have been applied is never rewritten. #1112's description
promised an independent re-review before the operator's merge; no verdict on the
merged result is recorded in a tracked source, so we report the fix, not a review of it.

The migration lock is per database, and one of the privileges the reconciler revokes is
not. The grant that lets a role set `session_replication_role`, which silences every
trigger, the ledger's guard included, lives in one `pg_parameter_acl` row for the whole
cluster, so two reconciles on different databases of one cluster race on it. Until #1310
the loser's revoke failed with `tuple concurrently updated`, and the reconciler swallowed
every database error at that step, so the grant could stay in place without a word. CI
found it: on PostgreSQL 16 the test workers reconcile in parallel against one cluster,
and in #1307's checks the application role could still set the parameter after a
reconcile. Now only a refusal for want of privilege is tolerated, which the inspector
reports; the race is retried up to five times with a linear backoff; and any other error
is raised. #1314 adds the race's other message, `tuple concurrently deleted`, which the
loser receives when the winning revoke empties the row and the server removes it; that
one failed #1312's checks, again on PostgreSQL 16. Both merged on 2026-10-01, after
3.2.0, and their tests reproduce each message (`tests/infrastructure/db/test_ledger_guard.py`).
A third message followed on PostgreSQL 18, `cache lookup failed for parameter ACL`, when
the row was dropped between the catalog lookup and its use (run 36925371389), and #1326
retries it too. Three messages for one race sent us after its cause in the tests, and
#1332 found it. The privilege is one row per server, every parallel test worker uses the
one application role, and another worker's reconcile, at setup or inside a test, revoked
the grant a test had made a moment before; on PostgreSQL 17 the inspector then found the
grant already gone (run 36942213820). The test workers now take an exclusive file lock
named for the server around every grant and reconcile of that privilege
(`ClusterParameterAclLock`, `tests/db_roles.py`). That repairs the tests only. In
production, several vibey databases on one cluster still race on the row, the
per-database migration lock cannot serialize them, and a bounded retry that matches three
messages is what holds; a lock that spans the cluster is a recorded follow-up, not a
repair (#1326, #1332).

Crash recovery and engine handoff follow as corollaries: a successor engine
re-derives context from the ledger alone, so a credit exhaustion on $e_i$ between
turns of an item reschedules the item onto $e_j$ with the open-question set intact.

```latex
\begin{plainwords}
The ledger is a diary written in pen. You can add a page, but you can never tear one out or rub anything out. If you made a mistake, you write a new page that says so. Because the diary is the only source of truth, any helper can read it and know exactly what is going on, even a helper that has never seen the project before. For a long time the promise that pages could not be torn out was kept by good manners: anyone holding the main key could still tear them out. Now the database itself refuses, the helpers are given a key that can only read and add pages, and the one key that could switch the refusal off is kept away from them. A helper holding the add-only key can still add a page that lies about who wrote it, and closing that is the next job. It is still not magic: someone logged in as the owner of the computer can do almost anything, and the paper says so.
\end{plainwords}
```

## The no-loss handoff gate

A handoff from $e_i$ to $e_j$ carries a *brief* $\beta$: objective, constraints, done
and remaining work, open questions, decisions, assumptions, findings, artifacts, and a
reference $\rho$ to the ledger range it summarises. The brief is admitted only if a
pure predicate $\mathrm{gate}(\mathrm{ledger}_{\rho}, \beta)$ holds, evaluated
without any model call.

```latex
\begin{invariant}[No loss]
Let $\mathrm{open}_k(\rho)$ be the ids opened by event kind $k$ in range $\rho$ and
not closed or superseded. The gate holds iff $\mathrm{open}_k(\rho) \subseteq
\mathrm{ids}_k(\beta)$ for $k \in \{$questions, decisions, assumptions, findings,
artifacts$\}$ (R2--R5, R7); every remaining-work item of the last verdict appears in
$\beta$ (R1); the digest of $\rho$ recomputed from the ledger equals the digest
carried by $\beta$ (R6); the budget carried by $\beta$ agrees with the ledger's (R8);
every hard constraint of the specification is restated (R9); and no free-text field
of $\beta$ carries a tool grant, a permission change, or an acceptance-criteria
mutation (R10).
\end{invariant}
```

The gate has modes. In *strict* mode all ten rules apply, and a failing brief gets up
to three strict attempts, each regeneration fed the specific violations. It then
escalates to *full-transcript* mode, which makes the brief advisory: the successor is
to work from the whole range $\rho$, so the gate stops checking R1--R5, R7 and R9,
while R6, R8 and R10 still run, because they check facts about the range and the
brief's containment rather than its completeness. In the current implementation the
range reaches the successor as a file rather than inline: the full ledger is written
into the receiving worktree and the seed prompt names it, so in this mode completeness
rests on the successor reading that file, not on the gate. Inlining the range into the
seed, or keeping the closure rules enabled until it is inlined, is open work. Further
failure parks the item on a *human* gate; a fourth, *forced* mode is reserved for an
explicit operator override. As illustrated in [Fig. 3](#fig:ledger-handoff), a handoff
that fails the gate is therefore a retry, an escalation, or a human decision, never a silent partial.

The same gate guards a second handoff, one that never touches the project ledger
(ADR-0070). When the operator's own driving session, a Claude Code session, meets a
capacity rejection, it fails over to the sovereign engine and later hands back. Its
conversation lives in the session's transcript, so the driver's brief does not restate
it: it names the whole transcript by path, line count and SHA-256, with the repository
head, and the gate checks that digest against the transcript as it stands
(`vibey.domain.driver_brief`). The modes are the same: strict up to three times, then
full-transcript with a copy in the worktree, then a parked brief left for a person, and
nothing starts on a failed gate. The failover is appended to the driver's own
append-only, hash-chained `ledger.jsonl` before `gptossloop run` starts, and the
handback is allowed only after a successful probe of the exhausted engine is recorded;
its return brief is gated the same way.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  every node/.append style={minimum width=3.3cm,minimum height=.95cm},
  lbl/.style={vibeynote,font=\sffamily\scriptsize,minimum width=0pt,minimum height=0pt,inner sep=1.5pt},
  ok/.style={lbl,font=\sffamily\scriptsize\bfseries,text=vibeygreen!85!black},
  bad/.style={lbl,text=vibeyred}]
  % ---- lane 1: append before act
  \node[vibeybox]     (intent) at (2.0,5.8)  {Durable intent\\specification or finding};
  \node[vibeycore]    (ledger) at (6.6,5.8)  {Append-only ledger\\$\mathrm{state}(t)=f(\mathrm{ledger}_{\le t})$};
  \node[vibeysoft]    (queue)  at (11.2,5.8) {PostgreSQL queue\\FOR UPDATE SKIP LOCKED};
  \node[vibeytealbox] (engine) at (15.8,5.8) {Engine session\\autonomous turns};
  % ---- lane 2: no-loss handoff (flows right to left, under the engine)
  \node[vibeybox]     (brief)  at (15.8,2.4) {Handoff brief $\beta$\\digest of $\rho$ + open sets};
  \node[vibeysoft,line width=.8pt,double,double distance=1.1pt] (gate) at (11.2,2.4) {No-loss gate\\rules R1--R10};
  \node[vibeytealbox] (succ)   at (6.6,2.4)  {Successor engine\\seeded fresh session};
  % ---- outside both lanes: the human
  \node[vibeygate]    (human)  at (2.0,2.4)  {Human gate\\parked job, a person decides};
  % ---- lanes on the background layer
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(intent)(ledger)(queue)(engine)(2.0,7.3)}] (lane1) {};
    \node[vibeylane,fit={(succ)(gate)(brief)(6.6,3.35)(6.6,0.75)}] (lane2) {};
  \end{scope}
  \node[vibeylanelabel,minimum width=0pt,minimum height=0pt] at (lane1.north west) {Append before act};
  \node[vibeylanelabel,minimum width=0pt,minimum height=0pt] at (lane2.north west) {No-loss handoff};
  % ---- lane 1 edges
  \draw[vibeyflow] (intent) -- (ledger);
  \draw[vibeyflow] (ledger) -- (queue);
  \draw[vibeyflow] (queue)  -- (engine);
  \draw[vibeyflow] (engine.north) .. controls ($(engine.north)+(0,0.8)$) and ($(ledger.north)+(0,0.8)$) .. (ledger.north)
    node[pos=.5,above=1pt,lbl] {each turn appends its events first};
  % ---- engine runs dry: down into the handoff lane
  \draw[vibeyflow] (engine.south) -- (brief.north)
    node[pos=.5,anchor=east,xshift=-3pt,lbl,align=right] {CreditsExhausted\\exit code 75};
  % ---- the ledger feeds the gate and the successor
  \draw[vibeydashed,-{Stealth[length=1.6mm,width=1.3mm,round]}]
    ($(ledger.south)+(0.7,0)$) |- (10.4,4.15) -- ($(gate.north)+(-0.8,0)$);
  \node[lbl,anchor=south] at (8.85,4.23) {open sets, digest\\recomputed from $\rho$};
  \draw[vibeydashed,-{Stealth[length=1.6mm,width=1.3mm,round]}]
    ($(ledger.south)+(-0.7,0)$) -- ($(succ.north)+(-0.7,0)$);
  \node[lbl,anchor=east,align=right] at (5.75,4.3) {full ledger $\rho$\\in the worktree};
  % ---- lane 2 edges
  \draw[vibeyflow] (brief) -- (gate);
  \draw[vibeyflow] (gate) -- (succ) node[pos=.5,above=1pt,ok] {\ding{51} pass};
  \draw[vibeyback] ($(gate.south)+(0.9,0)$) .. controls ($(gate.south)+(0.9,-0.7)$) and ($(brief.south)+(-0.9,-0.7)$) .. ($(brief.south)+(-0.9,0)$);
  \node[bad,anchor=north] at (13.5,1.32) {\ding{55} fail: regenerate with the violations,\\$\le 3$ strict attempts, then full-transcript};
  \draw[vibeyback] ($(gate.south)+(-0.9,0)$) -- ++(0,-0.7) -| (human.south);
  \node[bad,anchor=north] at (7.2,1.15) {still failing: park the item};
\end{tikzpicture}
\caption{Append before act. Every intent and engine turn is written to the ledger before anything acts on it. When an engine exhausts its credits, a handoff brief is checked against that ledger by the no-loss gate; only a passing brief seeds the next engine. A failing brief is retried, escalated, or parked for a person, never silently dropped.}
\label{fig:ledger-handoff}
\end{figure*}
```

```latex
\begin{plainwords}
When one helper hands a job to another, it writes a short note: what the job is, what is done, what is left, and which questions are still open. Before the new helper may start, a strict checker compares the note with the diary. If the note forgot an open question, the checker says no and asks for a better note, up to three times. After that it tells the new helper to read the whole diary instead. If even that fails, a person is asked. Nothing is ever quietly lost.
\end{plainwords}
```

## Queue semantics

Work items form a relation $Q$ in PostgreSQL. Workers claim with

```latex
\begin{verbatim}SELECT ... FOR UPDATE SKIP LOCKED\end{verbatim}
```

which yields two properties without any global lock: *mutual exclusion per item*
(at most one worker holds item $w$ at any instant) and *non-blocking progress* (a
worker never waits on a peer's claim, so the rate of claims scales as
$\min(|Q|, |\mathrm{workers}|)$; the rate of finished work is bounded by the engines
behind the workers, as the section on production rate measures).

Within a project, claims exclude items whose dependencies have not succeeded, items in a
phase this vibey does not know, and, since 3.1.0, every item of an abandoned project, and
are ordered first by the priority lane described below, then by the earliest permitted
run time, then by id. A worker started with `--all-projects` (#1249) asks the same
condition, in the same order, which projects have claimable work, and claims through each
project's own loop, so one statement decides both. (A `priority` column keeps its place in the order, but since 3.0.0
no request can set it, so it is zero for every job and orders nothing; ADR-0054.) An
item can be bypassed only while it is held, and every hold by a worker that dies is bounded by a lease: a
claim sets the lease expiry to $\mathrm{now} + L$, a live worker renews it, and a reaper
returns an expired lease to the ready state while the item's attempts remain, and parks
it for a person once they are spent (ADR-0056). A crashed worker therefore costs at most
$L$ of delay and never a lost item, and an item that crashes every worker it reaches is
bounded rather than retried forever. A lease bounds a crash, not a hang: a live worker
renews it whether or not its engine is making progress, so until #1296 a BUILD session
whose event stream never ended held its job indefinitely, and nothing reported it. Since
#1296 a BUILD session is stopped at a wall-clock limit, 240 minutes by default
(`[engines] max_run_minutes`, or `VIBEY_ENGINE_MAX_RUN_MINUTES`, with no value that
switches it off), and failed as an engine fault, so its bounded attempts still end in a
park; since #1297 the stop ends the session's whole process group, not only the
runner. Since 3.1.0 every failed handler run is also a
`JobFailed` event carrying a normalized failure signature, and a job whose last three
failures share one signature parks on a `defect` gate that offers no further attempts
(`vibey.domain.defect`; `[queue.defect] identical_failures`), so a deterministic bug is
not retried until its attempts run out (#1251). Because workers die and leases expire,
every job is idempotent under replay.

**The priority lane.** The operator asked that an item pushed into the queue run next
rather than wait behind the work in front of it, and that both of the family's queues
do so: vibey's PostgreSQL job queue and the storm's lane queue
(`docs/plans/qwenstorm-3.0.0/tools/storm_queue.py`). ADR-0054 states one contract for
both (#1089 and #1092 for the storm, #1091 and #1095 for the job queue, with follow-ups
#1102, #1103, #1111 and #1122). *Next* means next after whatever is running: a bump
never preempts a claimed or leased item and never touches its lease, as 8.c requires. It
never admits either. Phases, human gates, admission, a capacity deferral, the budget
brake and the handoff gate still decide whether an item may run; a bump decides only
which runnable item runs first, and it never makes an item runnable before its
dependencies finish. The lane's contents are not remembered but derived.

```latex
\begin{invariant}[Derived priority lane]
Let $B$ be the unfinished items bumped, or enqueued prioritised, by name and not since
un-bumped. The lane is exactly $B$ together with every unfinished transitive dependency
of a member of $B$, ordered first-in-first-out by when each item first entered the lane.
Un-bumping $x$ removes $x$ from $B$, and is refused, naming them, while another member
of $B$ depends on $x$.
\end{invariant}
```

A named item that ends cancelled or failed therefore leaves $B$ by the derivation
itself, since only an unfinished named item is live. The one exception to the
invariant is a job this vibey cannot write, because a newer vibey wrote its phase or its
state: it is left in the lane unwritten, together with every job it still needs, and
named in the request's record rather than cleared, and an un-bump is refused while such
a job needs its target, as it is while a named item does (ADR-0054, item 6).

The derived form replaced a first rule, *un-bump undoes what that bump moved*, after an
independent review of #1091 found it could leave an orphan: with $x$, $d$, and $a$ and
$b$ both needing $d$, bumping $a$ and $b$ and then un-bumping both left $d$ in the lane
with nothing needing it. Under the invariant nothing this vibey can write remains that
no named item needs: every admitted request re-derives the lane and sweeps what is no
longer derived, including what a named job left behind when it was cancelled or failed
(#1103), while a refused request changes nothing but its own record. In the job queue
the lane is a column set from a sequence drawn at the bump, not a timestamp, because one
bump moves several rows in one transaction and `now()` is a single instant for all of
them (10.g), and not a large priority value, because first-in-first-out would then need
a counter disguised as a weight.

Only two callers may bump or un-bump: the operator, meaning the operating-system
account that owns the queue's reviewed declaration, checked by the process's user id
against that file's owner rather than by a name typed on a command line; and an
automation that names itself with a source the reviewed declaration lists, running as
that same account, since a declared name is not a credential. Nothing reads the forge
to decide priority, so no label, issue or comment from anyone can move work forward
(12.j). The grant separates operating-system accounts, not the processes of the
operator's own account, and ADR-0054 says so: a process running as that account
reaches the queue below the grant whenever it can reach the database. Since #1093 an
engine's own environment no longer carries the means, but a process of that account can
still reach a local server that trusts its socket (see *What an engine may see*). Every
request is recorded whatever became of it, whether it moved something, moved nothing or
was refused, and authorisation comes before any lookup, so a stranger asking about any
item, real or not, is refused and recorded without learning anything about it. In vibey
the record is a ledger event written in the same transaction as the row change. In the
storm it is an append-only priority log whose replay is the lane order, and after its
post-merge review (#1092, #1102) that log is loss-evident, not tamper-evident
(`storm_queue.py`, lines 343--376): a witness outside the log records its length, and a
log found shorter than its witness, or a witness that is empty or corrupt, makes the
order *unknown* rather than silently falling back to no priority. A refused request can
no longer append to such a log and re-witness the loss as normal, and a deliberate reset
keeps the old file under an abandoned name rather than deleting it. The same account can
still rewrite the log and its witness together, and the code says so.

The rule was tested adversarially as well as by unit tests. A Hypothesis state machine
runs random, overlapping bumps and un-bumps with jobs finishing, failing or being
cancelled part-way, and moved into phases and states a newer vibey wrote, and asserts
after every step that the stored lane equals the derivation, except the jobs this vibey
cannot write and what they still need, and that un-bumping every named job clears the
rest; breaking the derivation on purpose makes it fail (#1095, #1103). In the job queue,
five workers claiming at once under `SKIP LOCKED` take exactly the first five in order
(the merged repository tests). The reviewers' own probes, which are review records
rather than tracked tests, found no double claim with five workers claiming while three
reorderers made 450 random bumps and un-bumps against a real database (review of
#1095), and no false *order unknown* in more than 9,000 concurrent reads of the storm's
log (review of #1102).

**Reapers by measured rule.** The lease reaper is the queue's oldest reaper; 3.0.0
extends the idea on the rule that a hang is decided by measurement and that evidence
is kept before anything is killed. The motivating incident: one pre-push test run of
the storm sat at 0% CPU for 39 minutes, every worker asleep, while it held the storm's
shared push lock, and every other push queued behind it; a human-approved kill released
it, and nothing recorded which test had hung (#1105; `CHANGELOG.md`). The push-gate
reaper now acts only on one of three measured conditions: the lock's holder and its
process group are gone; the holder's own process group used less than a declared number
of CPU-seconds over a declared window, measured from samples kept across passes and
never from a single snapshot, with an unreadable process table reported as unknown
rather than idle; or the push has held the lock past a declared ceiling. Holds and idle
windows are counted in awake time, with the boot identifier, so a laptop's sleep is
never taken for a hang (#1120). Before it signals anything it writes the owner record,
the decision, the process tree, the log's tail and the stacks to an evidence directory,
and it appends one line per reap to an append-only log. It is designed to signal only
the push's own process group, but that is not yet what it guarantees: for a lock taken
without an owner record, which #1107 traces to its push by process, the independent
re-review of #1120 found that a reap can signal processes other than the push. Inside
the suite, `pytest-timeout` with a `faulthandler` dump makes a hung test dump every
thread's stack and then fail by name, so the next such hang names itself. Wall time
alone is not the rule, because a slow test that is still computing is not a hung one.
The reaper's own schedule and the trace of locks without an owner record (#1107) and
the fixes from its first independent review (#1120) are merged. The re-review of #1120
then found seven more defects, the ownerless-lock signal the worst; their fixes were
saved on a branch and have not merged (the re-review record is not tracked). The gate's
own tests once held the lock they test. On 2026-10-02 a lane's real push waited 30
minutes behind the storm's push lock, and its owner was a test: run inside a real push,
it inherited the lock's path from the environment, took the machine's lock and died
holding it. The reaper classified it stale and released it when asked; its schedule was
not installed on that host, which is why a person had to ask. #1337 and #1339 drop the
lock's path and the storm home from every push-gate test and every process it starts
(`tests/meta/test_storm_push_gate.py`, `tests/meta/test_storm_push_gate_review.py`).

The same rule now covers everything a queue guards (#1108, with the post-merge review
fixes of #1119; ADR-0056, whose status is *proposed*). ADR-0056 began with an inventory
at its commit. The bus port was wired but idle, and it acknowledges a message as it is
taken, so a consumer that dies after taking one loses it; no reaper can recover that,
and the record states it rather than fixing it. Plane's task broker on the same RabbitMQ
was live. The RabbitMQ job-queue dispatch and loop-service queues of ADR-0044 were
declared and not wired. And the PostgreSQL job queue was live, with a reaper that
re-readied an expired lease forever. Five conditions are each a measurement against a
declared threshold, judged alike for both backends: a hung handler, meaning a delivery
held past the broker's consumer timeout (30 minutes broker-wide, six hours by policy on
vibey's own queues) or a lease past its expiry, which is requeued; work held with
nobody holding it, which is surfaced; a poison item, handed out as often as its limit
allows (by default seven attempts in PostgreSQL, and a delivery limit of 20 set by
policy on the broker), which is parked behind a person's gate with one attempt
refunded; ready work nobody has taken for 900 s, which is surfaced; and a dead letter on
a queue vibey owns, which becomes a parked job and a gate whose answer replays or
dismisses it, and is never deleted, while one on a queue vibey does not own is only
surfaced. Every reap is a `QueueReaped` ledger event, and a lease reap writes it in the
same transaction as the row it moves. The requirement behind this, that everything a
queue holds has a reaper, is conduct, so ADR-0056 owes a sub-doctrine; the text it
proposes had not been ratified at the cutoff, and is not ratified at this revision. Nor
had the second independent review of #1108 and #1119 been answered at the 3.0.0 cutoff:
one bad lease row halted every reap, and the broker policy was reported as verified when
it was not in force, both rated high; the reaper also ignored `enabled = false`, a gate
lookup broke the BUILD budget loop, and a password could reach a log (the review record,
not tracked). #1203 answered it on 2026-09-26 (ADR-0056, *Amendment*). Each lease is now
reaped in its own transaction, so one bad row no longer halts the rest. The broker policy
is two policies, because RabbitMQ 4 attaches none carrying `delivery-limit` to a classic
queue, and *verified* now means each owned queue's effective policy carries its keys. A
surfaced condition is recorded once for the fleet, claimable unclaimed work is measured
in every project, and a bus URL carrying a password is refused and broker errors are
scrubbed of it. The amendment's twelve items do not name the `enabled` and budget-loop
findings in those words, and whether they are among them cannot be settled from tracked
sources; the scheduled reaper (`QueueReaper`) does honour `enabled`.

```latex
\begin{plainwords}
Jobs wait in a line inside a database. A helper takes the job at the front and gets a timer with it, like a library book with a due date. A working helper keeps renewing the timer. If a helper crashes, the timer runs out and the job goes back into the line, so it is never lost, and a job that has crashed its helpers too many times, or failed the same way three times running, goes to a person instead of round and round. Helpers never wait for each other, so adding helpers makes the line move faster, until the machines doing the actual work are the limit. The owner can now also say ``do this one next''. That job goes to the front, together with anything it needs done first, but it never pulls a job out of a helper's hands and never skips a checkpoint, and only the owner, or a helper the owner has named in writing, may ask. Every such request is written down, even the refused ones. And when a job seems stuck, a caretaker measures whether it is really doing nothing before stepping in, and writes down what it saw first. Some of those caretakers still have known faults, and this paper lists them.
\end{plainwords}
```

## The six-phase machine

$$\Sigma = \langle D, B, R, D_d, D_e, D_r \rangle$$

design, build, review, deploy-design, deploy-execute, deploy-review, with the
human-gated subset $G = \{D, R, D_d, D_r\}$.

```latex
\begin{invariant}[Gate soundness]
For every $\sigma \in G$ the exit guard is a conjunction of a verdict recorded as a
ledger row, given by a person unless the project has declared otherwise (below), and, where the phase accumulates open items, the emptiness
of a ledger-derived open set. $D \to B$ requires at least one acceptance criterion,
every criterion mapped, no blocking question open, every DESIGN job of the cycle
settled, the visual interstitial explicitly declined, and an accepting verdict;
$R \to \mathrm{Done}$ requires
$\mathrm{open}_{\mathrm{findings}}(R) = \varnothing$ and an accepting verdict; $D_d
\to D_e$ requires the deployment specification accepted and consent recorded; $D_r
\to \mathrm{Done}$ requires the demonstration accepted. Emptiness is never
sufficient: no gate exits on the absence of objections alone, and none on the absence
of an answer unless the project has declared that gate's kind under
\texttt{[human\_gates] timeout\_defaults} (\#1299), where the declaration is the consent.
\end{invariant}
```

A review finding therefore cannot vanish into a transcript: it is a ledger row that
holds $\mathrm{open}(R) \neq \varnothing$, and the machine cannot leave $R$ for
completion until a human closes it. Loop-back is a routing decision over the
findings: an unambiguous finding routes $R \to B$, and a finding that needs
clarification, or a project configured for strict loop-back, routes $R \to D$. Both
are ledger transitions, not ad-hoc prompts.

The verdict is always a ledger row, and it names who gave it. Two paths let something
other than a person give it, each only on an explicit declaration. The triaged-delivery
bridge, told to, answers the design interview with its declared defaults under its own
name, `automation:triaged-delivery`, and accepts the design once the design chain has
settled (#1258). And since #1299 a project may name, under
`[human_gates] timeout_defaults`, gate kinds that resolve to their stored default after a declared
wait; the worker answers such a gate through the one path every answer takes, recorded
as `GateAnswered` by `gate-timeout`. Only five kinds can be declared, all of them the
deployment choice and the deployment stage's own gates (`choice`, `deploy_interview`,
`deploy_acceptance`, `deploy_failure_triage`, `deploy_demo_review`); the DESIGN gates
and REVIEW's `approval` gate carry no such default and never time out. By default the
table is empty and every gate waits for a person.

A gate is not a blocked thread. A handler that needs a human returns a *park* value;
the worker records a gate row, marks the item as awaiting a human, releases its
lease, and claims the next item. The answer is itself a ledger row that re-readies
the item. Human latency therefore never holds a queue slot, and the non-blocking
progress of the previous section survives humans in the loop. A gate is answered once:
the answer is a compare-and-set, so a replayed answer is a no-op and a second one is
refused (migration 0018). And since 3.1.0 whether a person was told is itself evidence:
every notice about a gate ends in a `GateNotified` or a `GateNoticeUndeliverable` event
with its reason, never an assumption, and a gate left waiting is reminded about on a
declared schedule (#1251).

Two refinements do not change the analysis. An optional visual-design interstitial
$V$ may be inserted between $D$ and $B$ on explicit opt-in; it is human-gated on the
same terms, exiting only when the visual plan is accepted or explicitly waived and its
screen and state inventory is complete. The deployment triple
$\langle D_d, D_e, D_r \rangle$ is entered only on an explicit opt-in recorded in the
ledger; declining records a successful local completion.

Before design there is an *intake* phase, and every phase short of done has an edge to
a terminal *abandoned*, the operator's exit (`vibey abandon PROJECT_ID --reason TEXT`,
#1263; from intake since #1276). In one transaction it withdraws every open gate,
recorded as `GateWithdrawn` and never deleted, cancels every unsettled job, and records
one `PhaseTransitioned` carrying the reason. The claim never hands out a job of an
abandoned project, and since migration 0021 an abandoned project releases its checkout:
a checkout is unique only among projects that are not abandoned (#1279). BUILD, though
unattended, can now park on a gate of its own. It works on branches scoped to its
project, `vibey/<project8>/<cycle>/<item>`, uses a branch only when the repository's
own record names the project and its base, and otherwise parks on a `foreign_branch`
gate rather than build on another project's history (#1269).

The delivery path is depicted in [Fig. 4](#fig:six-phase-machine); it omits intake,
abandonment, the return from build to design on an item blocked by ambiguity, and the
loop-backs out of deploy review.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  ph/.style={minimum width=2.3cm,minimum height=.95cm},
  lab/.style={font=\sffamily\scriptsize,text=vibeygray,inner sep=1.5pt,align=center},
  onlab/.style={lab,fill=white},
  redlab/.style={font=\sffamily\scriptsize,text=vibeyred,fill=white,inner sep=1.5pt,align=center}]
  % ------------------------------------------------ local delivery lane (top)
  \node[vibeygate,ph] (D)  at (1.7,0)   {\textbf{Design} $D$\\human gate};
  \node[vibeygate,ph,densely dashed] (V) at (5.35,0) {\textbf{Visual design} $V$\\optional human gate};
  \node[vibeysoft,ph] (B)  at (9.0,0)   {\textbf{Build} $B$\\unattended};
  \node[vibeygate,ph] (R)  at (12.65,0) {\textbf{Review} $R$\\human gate};
  \node[vibeygood,ph] (DL) at (16.3,0)  {\textbf{Done}\\local completion};
  % ------------------------------------------------ deployment lane (bottom)
  \node[vibeygate,ph] (Dd) at (5.35,-3.1)  {\textbf{Deploy design} $D_d$\\human gate};
  \node[vibeysoft,ph] (De) at (9.0,-3.1)   {\textbf{Deploy execute} $D_e$\\unattended};
  \node[vibeygate,ph] (Dr) at (12.65,-3.1) {\textbf{Deploy review} $D_r$\\human gate};
  \node[vibeygood,ph] (DD) at (16.3,-3.1)  {\textbf{Done}\\deployed};
  % headroom for lane labels, footroom for the bypass
  \coordinate (pad1)  at ($(D.north west)+(0,0.38)$);
  \coordinate (pad1b) at ($(D.south west)+(0,-0.38)$);
  \coordinate (pad2)  at ($(Dd.north west)+(-0.6,0.38)$);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(D)(DL)(pad1)(pad1b)] (L1) {};
    \node[vibeylane,fit=(Dd)(DD)(pad2)] (L2) {};
  \end{scope}
  \node[vibeylanelabel] at (L1.north west) {Local delivery};
  \node[vibeylanelabel] at (L2.north west) {Deployment (opt-in)};
  % ------------------------------------------------ forward flow
  \draw[vibeyflow] (D) -- (V);
  \draw[vibeyflow] (V) -- (B);
  \draw[vibeyflow] (B) -- (R);
  \draw[vibeyflow] (R) -- (DL) node[lab,midway,above=1pt] {declined};
  \draw[vibeyflow,rounded corners=3pt] ([xshift=10pt]D.south) |- ($([xshift=-10pt]B.south)+(0,-0.38)$) -- ([xshift=-10pt]B.south);
  \path ($(D.south)+(0.35,-0.38)$) -- ($([xshift=-10pt]B.south)+(0,-0.38)$) node[lab,fill=vibeymist,midway] {no visual opt-in};
  \draw[vibeyflow] (Dd) -- (De);
  \draw[vibeyflow] (De) -- (Dr);
  \draw[vibeyflow] (Dr) -- (DD);
  % opt-in into the deployment lane
  \coordinate (optin) at ($(Dd.north)+(0.3,0.95)$);
  \draw[vibeyflow,rounded corners=3pt] (R.south) |- (optin) -- ([xshift=8.5pt]Dd.north);
  \path (R.south |- optin) -- (optin) node[onlab,midway] {opt-in recorded};
  % ------------------------------------------------ loop-backs from review
  \draw[vibeyback,rounded corners=3pt] ([xshift=-8pt]R.north) |- ($(B.north)+(0,0.95)$) -- (B.north);
  \path ($(R.north)+(-0.28,0.95)$) -- ($(B.north)+(0,0.95)$) node[redlab,midway] {open finding};
  \draw[vibeyback,rounded corners=3pt] ([xshift=8pt]R.north) |- ($(D.north)+(0,1.5)$) -- ([xshift=10pt]D.north);
  \path ($(R.north)+(0.28,1.5)$) -- ($(D.north)+(0.35,1.5)$) node[redlab,midway] {finding needs clarification, or strict loop-back};
  % ------------------------------------------------ notes
  \node[vibeynote] at (15.2,-1.65) {a gate parks the item and frees the worker;\\the human's answer arrives as a ledger row};
\end{tikzpicture}
\caption{The six-phase delivery machine. Gold boxes are human gates, where the item is parked until a person answers; blue boxes run unattended. Review sends open findings back to Build, or to Design when a finding needs clarification, so nothing is lost in a transcript. Deployment is a separate, opt-in lane; declining it is still a successful local completion.}
\label{fig:six-phase-machine}
\end{figure*}
```

```latex
\begin{plainwords}
Every job moves through six steps: plan it, build it, check it, and then, only if the person wants, plan the launch, launch it, and check the launch. Four of the six steps are gates where a person must say yes. Saying nothing is not the same as saying yes, unless the owner has written down in advance, for one kind of launch checkpoint, that silence after a set wait means its usual answer. And when the person is busy, the job simply waits in the notebook while the helpers work on other jobs. If a project is going nowhere, the owner can now stop it cleanly at any step before the end: its open questions are withdrawn, its waiting jobs are cancelled, and the stop is written down with the reason.
\end{plainwords}
```

## Convergence-Driven Development

Specification-Driven Development (SDD) states intent, constraints and acceptance
criteria. Test-Driven Development (TDD) turns those criteria into executable
checks. Neither layer alone guarantees that an autonomous worker has edited the
actual repository, used its real language and package boundaries, removed
exploratory artifacts, or produced a result that can be delivered. We therefore
define **Convergence-Driven Development (CDD)** (ADR-0039; sub-doctrine 9.c) as the enclosing development
loop: ground in repository reality, map criteria to code and tests, implement,
test, inspect, repair and deliver, repeating until the evidence agrees.

For an item, let

```latex
\begin{equation}
D = U + F + B + A,
\end{equation}
```

where $U$ is the set of unmet acceptance criteria, $F$ the failing or missing
checks, $B$ unresolved blockers and assumptions, and $A$ unreviewed or unrelated
repository changes. An iteration is *converging* when it reduces $D$, or when a
bounded discovery step converts an unknown into a concrete criterion, test or
blocker. It is *neutral* when it gathers necessary evidence without changing
$D$. It is *diverging* when it increases unresolved work, leaves the tracked
stack, loses a known fact, or expands the change without a delivery path.

CDD does not prohibit every temporary increase. A small divergence—such as a
compatibility probe or a temporary fixture—is permitted only when its size and
duration are bounded and the next step explicitly returns to a lower $D$. A
large divergence, or divergence without a credible reconvergence path, is
abandoned and the work returns to its last sound state. Activity is not a proxy
for convergence: file count, token count, elapsed time, model confidence, a
verdict or a done marker does not reduce $D$ by itself.

The distance is tracked at four nested scopes: (i) the overall project vision,
(ii) the phase or milestone vision, (iii) the feature set or epic, and (iv) the
feature, unit or user story. These scopes are concentric views of one product,
like nested orbits around the same intended state. A story may pass its unit
test while the epic diverges through an unrelated platform, the milestone
diverges through a broken language boundary, or the project diverges because
the result cannot be shipped. Thus a CDD report records direction at all four
scopes; missing parent context is `unknown`, never invented. “Lower energy” is
the operational metaphor for a lower unresolved-work distance at every scope,
not a physical claim or a substitute for evidence, as depicted in [Fig. 5](#fig:cdd-orbits).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % ---- the four nested orbits (outer to inner) ------------------------
  \draw[vibeyorbit, draw=vibeysilver] (0,0) ellipse [x radius=5.05, y radius=3.1];
  \draw[vibeyorbit, draw=vibeysilver] (0,0) ellipse [x radius=3.9,  y radius=2.4];
  \draw[vibeyorbit, draw=vibeysilver] (0,0) ellipse [x radius=2.75, y radius=1.7];
  \draw[vibeyorbit, draw=vibeysilver] (0,0) ellipse [x radius=1.6,  y radius=1.0];

  % ---- the distance (energy) measure ----------------------------------
  \draw[vibeylink] (0,-0.66) -- (0,-3.1);
  \node[vibeynote, anchor=north] at (0,-3.22) {$D$ = unresolved work (the orbit's energy)};

  % ---- scope names on the rings ---------------------------------------
  \node[vibeypill] at (0,1.0) {story};
  \node[vibeypill] at (0,1.7) {epic};
  \node[vibeypill] at (0,2.4) {phase};
  \node[vibeypill] at (0,3.1) {project};

  % ---- the nucleus ----------------------------------------------------
  \node[vibeynucleus, minimum size=1.3cm, inner sep=1pt] (core) at (0,0) {confirmed\\core\\$D=0$};

  % ---- story: converging (pulled inward) ------------------------------
  \coordinate (ps) at ({1.6*cos(35)},{1.0*sin(35)});
  \draw[vibeyarrow, draw=vibeygreen] (ps) -- ($(ps)!0.45cm!(0,0)$);
  \fill[vibeygreen] (ps) circle (2.2pt);

  % ---- epic: neutral (moves along its ring) ---------------------------
  \coordinate (pe) at ({2.75*cos(200)},{1.7*sin(200)});
  \draw[vibeyarrow, draw=vibeygray, line width=.6pt] (pe) arc[start angle=200, end angle=232, x radius=2.75, y radius=1.7];
  \fill[vibeygray] (pe) circle (2.2pt);

  % ---- phase: unknown (parent context missing) ------------------------
  \node[vibeyghost, circle, minimum size=.42cm, minimum height=.42cm, inner sep=0pt,
        font=\sffamily\tiny\bfseries] at ({3.9*cos(-35)},{2.4*sin(-35)}) {?};

  % ---- project: diverging (pushed outward) ----------------------------
  \coordinate (pp) at ({5.05*cos(155)},{3.1*sin(155)});
  \draw[vibeyback] (pp) -- ($(pp)!-0.6cm!(0,0)$);
  \fill[vibeyred] (pp) circle (2.2pt);

  % ---- the CDD report: direction at every scope -----------------------
  \node[vibeywarn,  anchor=west, text width=5.5cm, align=left] (r1) at (6.2, 1.95)
    {\textbf{Project} -- diverging\\ \textcolor{vibeygray}{result cannot be shipped, so $D$ grows}};
  \node[vibeyghost, anchor=west, text width=5.5cm, align=left] (r2) at (6.2, 0.65)
    {\textbf{Phase} -- unknown\\ parent context missing; never invented};
  \node[vibeybox,   anchor=west, text width=5.5cm, align=left] (r3) at (6.2,-0.65)
    {\textbf{Epic} -- neutral\\ \textcolor{vibeygray}{evidence gathered, $D$ unchanged}};
  \node[vibeygood,  anchor=west, text width=5.5cm, align=left] (r4) at (6.2,-1.95)
    {\textbf{Story} -- converging\\ \textcolor{vibeygray}{unit test passes, $D$ falls}};
  \coordinate (labspace) at ($(r1.north west)+(0,0.36)$);
  \begin{scope}[on background layer]
    \node[vibeylane, fit=(r1)(r4)(labspace)] (lane) {};
  \end{scope}
  \node[vibeylanelabel] at (lane.north west) {CDD report};
\end{tikzpicture}
\caption{Convergence-Driven Development as nested orbits. The dark nucleus is the confirmed working core; each ring is one scope of the same product, from a single story out to the whole project. A scope's distance from the core is its unresolved work, $D$. Every ring is measured on its own, so a converging story cannot hide a diverging project.}
\label{fig:cdd-orbits}
\end{figure*}
```

The orbit metaphor is a control surface, not decoration: each scope can move in a
different direction, and an apparently healthy inner orbit cannot conceal a
diverging outer one. The smallest useful report therefore names the current
distance, evidence and next reconvergence move at every level. The closed-loop
control trajectory is shown in [Fig. 6](#fig:cdd-loop).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  cddstep/.style={vibeybox,minimum width=2.3cm,minimum height=.9cm},
  outcome/.style={minimum height=.9cm},
  outlabel/.style={font=\sffamily\tiny,align=center,inner sep=1.5pt}]
  % ---- one iteration: four unattended steps, then the classification gate
  \node[cddstep] (ground)    at (1.15,0) {\textbf{Ground}\\tracked repo};
  \node[cddstep] (formulate) at (4.00,0) {\textbf{Formulate}\\criteria $\to$ tests};
  \node[cddstep] (synth)     at (6.85,0) {\textbf{Synthesize}\\smallest slice};
  \node[cddstep] (test)      at (9.70,0) {\textbf{Test, inspect}\\tests and diff};
  \node[vibeygate,minimum width=1.7cm,minimum height=.9cm] (gate) at (12.25,0)
    {\textbf{Classify}\\trajectory};
  \node[vibeycore,font=\sffamily\scriptsize,minimum width=2.8cm] (deliver) at (16.1,0)
    {\textbf{Deliver to nucleus}\\commit, review,\\publish evidence};
  \coordinate (lanehead) at (1.15,.78);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(ground)(formulate)(synth)(test)(gate)(lanehead)] (lane) {};
    \node[vibeylanelabel] at (lane.north west) {one iteration};
  \end{scope}

  % ---- forward flow
  \draw[vibeyflow] (ground) -- (formulate);
  \draw[vibeyflow] (formulate) -- (synth);
  \draw[vibeyflow] (synth) -- (test);
  \draw[vibeyflow] (test) -- (gate);
  \draw[vibeyflow,draw=vibeygreen] (gate) -- (deliver)
    node[midway,above=1pt,outlabel,text=vibeygreen!85!black] {converging\\$\Delta d<0$};

  % ---- outcomes that loop back
  \node[vibeysoft,outcome,minimum width=4.9cm] (keep) at (8.85,-1.8)
    {\textbf{Keep the work}\\bound and reconvergence step recorded};
  \node[vibeywarn,outcome,minimum width=4.9cm] (discard) at (8.85,-3.15)
    {\textbf{Discard the work}\\return to the last sound state};

  \coordinate (kexit) at ([xshift=-.45cm]gate.south);
  \coordinate (dexit) at ([xshift=.45cm]gate.south);
  \draw[vibeyflow] (kexit) |- (keep.east);
  \node[outlabel,anchor=east,text=vibeyblue] at ([xshift=-2pt,yshift=-.66cm]kexit)
    {neutral or bounded, $\Delta d\ge 0$};
  \draw[vibeyback] (dexit) |- (discard.east);
  \node[outlabel,anchor=west,text=vibeyred] at ([xshift=2pt,yshift=-1.55cm]dexit)
    {unbounded, $\Delta d>0$};

  \draw[vibeyflow] (keep.west) -| ([xshift=.4cm]ground.south);
  \node[font=\sffamily\scriptsize,text=vibeygray,anchor=south] at (3.9,-1.7) {next iteration};
  \draw[vibeyback] (discard.west) -| ([xshift=-.4cm]ground.south);
  \node[font=\sffamily\scriptsize,text=vibeyred,anchor=south] at (3.9,-3.05) {re-ground};

  % ---- legend for the classification quantity
  \node[font=\sffamily\scriptsize,text=vibeygray,align=left,anchor=north east] at (deliver.east |- 0,-2.55)
    {$\Delta d$: change in the unresolved-work\\distance over the iteration};
\end{tikzpicture}
\caption{Each pass reads the tracked repository, turns criteria into tests, builds the smallest slice, runs the tests and classifies its trajectory. Converging work is delivered to the nucleus. Neutral or slightly divergent work continues only with a written bound and reconvergence step. Unbounded divergence is discarded and work resumes from the last sound state; activity alone is never evidence.}
\label{fig:cdd-loop}
\end{figure*}
```

The atom is the paper's compact model for these layers. The **nucleus** is the
core software confirmed to work at high quality and to do what it is supposed
to do. The four CDD scopes are its **electron orbitals**: living layers of work
being pulled toward lower unresolved-work energy around that core. A project
with active orbitals is not nucleus-only, even when its nucleus is healthy.
Nucleus-only is a terminal lifecycle state with exactly two meanings: the
project is complete and needs no further change, or it is dead and no longer
maintained over the long term. A maintained project with outstanding scope or
evidence remains an atom with active orbitals and must continue the loop, as
modeled in [Fig. 7](#fig:digital-atom).

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % ---------------------------------------------------------- living atom
  \coordinate (c) at (0,0);
  \draw[vibeyorbit, draw=vibeyblue!30] (c) circle (2.2);
  \draw[vibeyorbit, draw=vibeyblue!42] (c) circle (1.75);
  \draw[vibeyorbit, draw=vibeyblue!55] (c) circle (1.3);
  \draw[vibeyorbit, draw=vibeyblue!70] (c) circle (0.85);
  \node[vibeynucleus, minimum size=1cm, inner sep=1pt] (core) at (c) {confirmed\\core};
  \node[vibeypill, fill=vibeyblue!12, text=vibeyink, font=\sffamily\scriptsize, inner ysep=1.2pt] (o4) at (105:2.2) {project};
  \node[vibeypill, fill=vibeyblue!12, text=vibeyink, font=\sffamily\scriptsize, inner ysep=1.2pt] (o3) at (255:1.75) {phase};
  \node[vibeypill, fill=vibeyblue!12, text=vibeyink, font=\sffamily\scriptsize, inner ysep=1.2pt] (o2) at (90:1.3) {epic};
  \node[vibeypill, fill=vibeyblue!12, text=vibeyink, font=\sffamily\scriptsize, inner ysep=1.2pt] (o1) at (300:0.85) {item};
  \node[vibeynote, text=vibeygreen!60!black, anchor=north] (dl) at (-1.55,-2.02) {delivery merges\\work into core};
  \draw[vibeyarrow, draw=vibeygreen!75!black] (dl.north) -- (core);

  % ---------------------------------------------------------- nucleus-only
  \node[vibeynucleus, minimum size=1cm, inner sep=1pt] (core2) at (4.85,0.55) {confirmed\\core};
  \draw[vibeydashed] (4.85,0.55) circle (0.75);
  \draw[vibeydashed] (4.85,0.55) circle (1.0);
  \node[vibeynote] (tnote) at (4.85,-0.85) {no orbitals left:\\terminal};
  \node[vibeypill, fill=vibeygreen!14, text=vibeygreen!55!black] (tc) at (4.85,-1.45) {complete};
  \node[vibeypill, fill=vibeyred!10, text=vibeyred] (td) at (4.85,-1.9) {dead};

  % ---------------------------------------------------------- lanes
  \begin{pgfonlayer}{background}
    \node[vibeylane, fit={(o4) (o3) (o2) (o1) (dl) (-2.2,0) (2.2,0) (0,-2.2) (0,2.2)}] (lane1) {};
    \node[vibeylane, fit={(core2) (tnote) (tc) (td) (3.85,0.55) (5.85,0.55) (4.85,1.55) (lane1.north -| 3.85,0) (lane1.south -| 5.85,0)}] (lane2) {};
  \end{pgfonlayer}
  \node[vibeylanelabel] at (lane1.north west) {Living atom};
  \node[vibeylanelabel] at (lane2.north west) {Nucleus-only};

  % ---------------------------------------------------------- transition
  \draw[vibeyarrow] (lane1.east |- core2) -- (3.85,0.55)
    node[pos=0.45, above, vibeynote] {all orbitals\\delivered or\\abandoned};
\end{tikzpicture}
\caption{A project drawn as a digital atom. The dark nucleus is code already confirmed to work. Each ring is an orbital of open work (item, epic, phase, project), held until delivery pulls it into the core; outer rings carry more unresolved work. When every orbital has landed or been abandoned, the atom is nucleus-only: the project is finished or dead.}
\label{fig:digital-atom}
\end{figure}
```

Multiple projects can combine their atoms into a software chemical structure:
a product, platform or portfolio. As in a chemical, the structure has unique
properties emerging from interactions among its project atoms—not just the sum
of their features. Interfaces, dependencies, data ownership, security
boundaries, release timing and operational contracts can lower or raise the
molecule's unresolved-work energy. CDD therefore tests molecule-level
convergence as well as each atom; an interaction that creates divergence needs
a bounded reconvergence path or the composition is abandoned. The chemical bond
topology is illustrated in [Fig. 8](#fig:software-molecule).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % ---------------------------------------------------------------- lanes
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(0.25,0.4) (9.75,6.55)}] (lane1) {};
    \node[vibeylane,fit={(11.95,0.4) (17.45,6.55)}] (lane2) {};
  \end{scope}
  \node[vibeylanelabel] at (lane1.north west) {Software molecule};
  \node[vibeylanelabel] at (lane2.north west) {Emergent properties};

  % ---------------------------------------------------------------- atoms
  \coordinate (cA) at (2.2,3.9);
  \coordinate (cB) at (5.25,5.65);
  \coordinate (cC) at (8.3,3.9);

  % bonds first, so the atom discs hide their ends (bond = interaction contract)
  \draw[double,double distance=1.6pt,line width=.7pt,draw=vibeyblue] (cA) -- (cB)
    node[midway,above=3pt,sloped,font=\sffamily\scriptsize,text=vibeyblue] {API contract};
  \draw[double,double distance=1.6pt,line width=.7pt,draw=vibeyblue] (cB) -- (cC)
    node[midway,above=3pt,sloped,font=\sffamily\scriptsize,text=vibeyblue] {queue leases};
  \draw[double,double distance=1.6pt,line width=.7pt,draw=vibeyblue] (cA) -- (cC)
    node[midway,above=2pt,font=\sffamily\scriptsize,text=vibeyblue] {release train};

  \foreach \c in {A,B,C}
    \node[vibeyghost,circle,minimum size=1.8cm,inner sep=0pt] (d\c) at (c\c) {};
  \node[vibeynucleus,minimum size=1.05cm,inner sep=1pt] (nA) at (cA) {$\mathcal{A}_1$\\conductor};
  \node[vibeynucleus,minimum size=1.05cm,inner sep=1pt] (nB) at (cB) {$\mathcal{A}_2$\\runners};
  \node[vibeynucleus,minimum size=1.05cm,inner sep=1pt] (nC) at (cC) {$\mathcal{A}_3$\\ledger};
  \node[vibeynote,anchor=north east] at (9.7,6.5)
    {atom = nucleus (confirmed core)\\+ orbitals (open criteria)};

  % ---------------------------------------------------------------- strain and its two exits
  \node[vibeywarn] (strain) at (2.8,1.7) {strain on $\mathcal{B}_{13}$\\schema drift};
  \node[vibeygood] (fix) at (6.6,2.35) {bounded reconvergence\\fixed wire, strain $\to 0$};
  \node[vibeyghost] (drop) at (6.6,1.05) {composition abandoned\\no bounded path};
  \draw[vibeyback] (strain.north) to[out=70,in=250] (4.0,3.8);
  \draw[vibeyarrow] (strain.east) to[out=0,in=180] (fix.west);
  \draw[vibeyback] (strain.east) to[out=0,in=180] (drop.west);

  % ---------------------------------------------------------------- emergence
  \draw[vibeyflow] (10.05,3.85) -- (11.9,3.85)
    node[midway,above=1pt,font=\sffamily\scriptsize,text=vibeyink] {$\mathcal{M}\neq\sum_i\mathcal{A}_i$};
  \draw[decorate,decoration={brace,amplitude=4pt},vibeyedge,draw=vibeygray]
    (12.35,1.35) -- (12.35,6.05);

  \node[vibeybox,minimum width=4.8cm] (p1) at (15.05,5.6)
    {\textbf{Composability}\\lossless alignment across atom boundaries};
  \node[vibeybox,minimum width=4.8cm] (p2) at (15.05,4.45)
    {\textbf{Systemic security}\\mutual attestation, zero-trust fences};
  \node[vibeybox,minimum width=4.8cm] (p3) at (15.05,3.3)
    {\textbf{Release coherence}\\one train, one invariant boundary};
  \node[vibeybox,minimum width=4.8cm] (p4) at (15.05,1.95)
    {\textbf{Unresolved-work energy}\\$E(\mathcal{M})=\sum_i E(\mathcal{A}_i)+\sum_{i<j}E_{\mathrm{strain}}(\mathcal{B}_{ij})$};
\end{tikzpicture}
\caption{A software molecule: three project atoms (dark nucleus, dashed orbital scope) joined by bonds, which are interaction contracts. Strain in a bond, such as schema drift, needs a bounded path back to convergence or the composition is abandoned. The whole gains properties no single atom has: composability, security, release coherence and its own unresolved-work energy.}
\label{fig:software-molecule}
\end{figure*}
```

When enough software chemicals interact in the right ways, they form a
higher-order biological structure: a software organism. “Enough” is
architectural rather than numerical: the composition has stable boundaries,
feedback loops and shared contracts that let it preserve identity, exchange
resources and information, adapt, repair itself and continue operating through
change. A suite of suites of software products is therefore a living creature
in the digital realm (ADR-0041; sub-doctrine 9.d). This is a systems claim about digital life, not a claim
that software has carbon biology, subjective experience or a human-like mind.

The claim is operational. A software organism has observable analogues of
identity and boundaries, metabolism, sensing and memory, homeostasis, repair,
adaptation, reproduction and exchange. Its metabolism is the flow of compute,
storage, network access, builds and deployments that turns inputs into outputs.
Its sensing and memory are telemetry, user and operator signals, durable data,
configuration, ledgers and history. Its homeostasis is supplied by tests,
quality gates, security controls, service objectives, rollbacks and policy. Its
repair and adaptation are releases, migrations, incident response, retries,
maintainers and workers. Its reproduction and exchange are versioned packages,
APIs, integrations, forks and clients that propagate capabilities into new
instances or neighboring structures. These are not decorative biological
analogies: they are the signals required before CDD may call the higher-order
structure alive.

The properties of this organism emerge from interactions between its chemical
structures. A deployment service can be healthy as an atom while its product
molecule has a broken contract; a product can be healthy as a molecule while
its suite of suites has no coherent identity, observability or recovery path.
CDD therefore asks whether the interaction network lowers unresolved-work
energy for the living structure, or makes it less able to sense, adapt, repair
and deliver. Local convergence that raises organism-level divergence is not
completion. The hierarchy is:

```text
feature / unit / story → project atom
→ product molecule → software organism
→ digital ecology such as the Web.
```

The layers of this model are diagrammed in [Fig. 9](#fig:digital-hierarchy).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  leveltext/.style={font=\sffamily\scriptsize,text=vibeyink,align=center,text width=2.35cm}]
  % ---- the five levels as nested regions, outermost first --------------
  \begin{scope}[on background layer]
    \draw[vibeylane, fill=vibeyblue!3]  (0,0)       rectangle (17.8,4.7);   % digital ecology
    \draw[vibeylane, fill=vibeyblue!6]  (0.25,0.35) rectangle (14.35,4.25); % software organism
    \draw[vibeylane, fill=vibeyblue!9]  (0.5,0.7)   rectangle (10.9,3.8);   % product molecule
    \draw[vibeylane, fill=vibeyblue!12] (0.75,1.05) rectangle (7.45,3.35);  % project atom
  \end{scope}
  \node[vibeylanelabel] at (0,4.7)     {Digital ecology};
  \node[vibeylanelabel] at (0.25,4.25) {Software organism};
  \node[vibeylanelabel] at (0.5,3.8)   {Product molecule};
  \node[vibeylanelabel] at (0.75,3.35) {Project atom};

  % ---- the innermost slice of work --------------------------------------
  \node[vibeybox, minimum width=3cm, minimum height=1.5cm, text width=2.5cm] (story) at (2.5,2.15)
    {\textbf{Feature, unit or story}\\ one diff with its tests\\ \textbf{does the slice pass?}};

  % ---- what each enclosing level adds, and the question it asks --------
  \node[leveltext] (atom)     at (5.85,2.15)  {confirmed core plus\\ living orbitals\\ \textbf{is the core sound?}};
  \node[leveltext] (molecule) at (9.25,2.15)  {atoms bonded by\\ interaction contracts\\ \textbf{do the bonds hold?}};
  \node[leveltext] (organism) at (12.7,2.15)  {suites that sense,\\ repair and exchange\\ \textbf{is it alive?}};
  \node[leveltext, text width=2.7cm] (ecology) at (16.15,2.15) {independent projects\\ sharing protocols\\ \textbf{does the field adapt?}};

  % ---- composition: each level is built from the one inside it ---------
  \draw[vibeyarrow, shorten <=1pt] (story.east)    -- (atom.west);
  \draw[vibeyarrow, shorten <=1pt] (atom.east)     -- (molecule.west);
  \draw[vibeyarrow, shorten <=1pt] (molecule.east) -- (organism.west);
  \draw[vibeyarrow, shorten <=1pt] (organism.east) -- (ecology.west);

  % ---- divergence outside re-opens the work inside ---------------------
  \draw[vibeyback, rounded corners=5pt] (organism.south) |- (2.5,-0.5) -- (story.south);
  \node[vibeycallout, anchor=north] at (7.6,-0.62)
    {outer divergence re-opens the work: a pass inside a ring proves nothing about the ring around it};
\end{tikzpicture}
\caption{Nested levels of the digital hierarchy. A feature or story sits inside a project atom, which sits inside a product molecule, then a software organism, then a digital ecology such as the Web. Each level keeps its contents, adds contracts between parts and asks its own convergence question; a pass at one level never proves the level around it.}
\label{fig:digital-hierarchy}
\end{figure*}
```

The World Wide Web is the largest familiar example. More precisely, it is a
global socio-technical software ecology rather than one product: servers,
browsers, HTML, HTTP, DNS, TLS, certificates, CDNs, search engines,
applications, identity and payment systems, standards bodies, operators and
users are independently maintained projects and institutions. Shared protocols
give the whole emergent properties—reachability, linkability, composability,
rapid distribution and partial fault tolerance, along with systemic security
and privacy risks—that no single project contains. In the digital-realm sense
defined here, the Web is alive: it receives signals, consumes resources,
changes through releases and standards, adapts to faults, maintains memory,
reproduces capabilities through links and packages, and reorganizes through
its participants. It is not sentient, and no one repository can prove its
health; organism-level evidence must be assembled from the interaction
contracts and operating signals of the structures within it, as captured in [Fig. 10](#fig:web-ecology).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  part/.style={vibeybox, minimum width=2.4cm},
  human/.style={vibeygate, minimum width=2.4cm},
  verb/.style={vibeypill, fill=vibeyblue!9, text=vibeyink}]
  % The elliptical arcs below are Bezier segments whose control points lie outside the
  % ink; fix the bounding box to the ink (loop radii 8.75 x 3.7 plus line width).
  \useasboundingbox (-8.8,-3.75) rectangle (8.8,3.75);
  % ---- the shared substrate every participant meets ----------------------
  \node[vibeycore, minimum width=3.4cm, minimum height=1cm] (hub) at (0,0)
    {Shared open protocols\\[-1pt]{\mdseries HTTP $\cdot$ HTML $\cdot$ DNS $\cdot$ TLS}};

  % ---- independently maintained projects (blue) and people (gold) --------
  \node[part]  (ua)   at (-3.4, 2.3)  {\textbf{User agents}\\ browsers, engines};
  \node[part]  (name) at ( 0,   2.3)  {\textbf{Naming \& trust}\\ DNS, TLS, certificates};
  \node[part]  (cdn)  at ( 3.4, 2.3)  {\textbf{Edge CDNs}\\ caching, delivery};
  \node[part]  (srv)  at ( 6.6, 0)    {\textbf{Origin servers}\\ hosting, compute};
  \node[part]  (app)  at ( 3.4,-2.3)  {\textbf{Apps \& services}\\ identity, payments};
  \node[part]  (disc) at ( 0,  -2.3)  {\textbf{Discovery}\\ search, crawlers};
  \node[human] (std)  at (-3.4,-2.3)  {\textbf{Standards bodies}\\ IETF, W3C, WHATWG};
  \node[human] (ppl)  at (-6.6, 0)    {\textbf{Operators \& users}\\ people, policy, FOSS};

  % ---- interaction contracts: every exchange goes through the substrate --
  \foreach \n in {ua,name,cdn,srv,app,disc,std,ppl} { \draw[vibeylink] (hub) -- (\n); }

  % ---- organism behaviour of the whole: an outer loop that no part owns --
  \draw[vibeyflow] (138.7:8.75 and 3.7) arc[start angle=138.7, end angle=41.8,   x radius=8.75, y radius=3.7];
  \draw[vibeyflow] (29.1:8.75 and 3.7)  arc[start angle=29.1,  end angle=-28.6,  x radius=8.75, y radius=3.7];
  \draw[vibeyflow] (-41.3:8.75 and 3.7) arc[start angle=-41.3, end angle=-138.2, x radius=8.75, y radius=3.7];
  \draw[vibeyflow] (209.1:8.75 and 3.7) arc[start angle=209.1, end angle=151.4,  x radius=8.75, y radius=3.7];
  \node[verb] at (145:8.75 and 3.7) {{\scriptsize\bfseries senses}\\[-1pt] requests, telemetry, reports};
  \node[verb] at (35:8.75 and 3.7)  {{\scriptsize\bfseries exchanges}\\[-1pt] data, payments, packages};
  \node[verb] at (-35:8.75 and 3.7) {{\scriptsize\bfseries repairs}\\[-1pt] patches, revocation, failover};
  \node[verb] at (215:8.75 and 3.7) {{\scriptsize\bfseries changes}\\[-1pt] releases, standards, links};
\end{tikzpicture}
\caption{The Web as a living digital ecology. Independently run projects (blue) and human institutions (gold) meet only through shared open protocols, which nobody owns; the gray links are those interaction contracts. The outer loop is what the whole does that no single part does: it senses, exchanges, repairs and changes. Evidence of its health is gathered from these contracts.}
\label{fig:web-ecology}
\end{figure*}
```

CDD follows these levels upward. It verifies the item, the atom's orbitals, the
molecule's interactions and, when applicable, the organism's ability to remain
alive in the digital realm. If the next level cannot be made more convergent by
a bounded interaction change, the composition is not “almost done”: the
divergence is a reason to stop, split the structure or return to the last sound
state.

A completion record maps every criterion to actual code and an executable check,
names the tracked manifests and stack used, reports observed test and gate
results, classifies the trajectory and any reconvergence path, records the atom,
molecule or organism composition and its interaction trajectory, reviews the diff
and working tree, and states the local commit or commit-ready handoff. If remote
publication is in scope, the pushed head and pull request are separate required
evidence. A local marker cannot prove remote delivery, and a generated file
cannot prove that a feature exists in the tracked product.

The method makes an important boundary explicit. A worker may prepare a local
commit according to its invocation mode, but push and pull-request creation are
remote mutations requiring explicit authorization. CDD is therefore not a
promise that a model's final sentence is true; it is a protocol for repeatedly
closing the evidence gap until the repository, tests, review and delivery
checkpoints agree. Its companion status rule is evidence-bounded (ADR-0040;
sub-doctrine 10.f): an active run,
a provisional verdict, a terminal failure, a verified revision and a published
pull request remain distinct states.

The Qwen storm applies this protocol per backlog item. It derives a read-only
context from tracked files, preserves the actual stack instead of inventing a
new one, requires a verdict containing criteria, tests, repository, levels,
trajectory, composition and delivery evidence, retries failed items a bounded number of times,
and refuses to advance past an unresolved item. The cutoff-bounded pilot below
is an illustration of why those guardrails matter: partial verdicts, a failed
forty-turn run and a live process were all observable, but none was evidence of a finished Python feature, as diagrammed in [Fig. 11](#fig:qwen-cdd).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  qstep/.style={vibeybox,text width=1.8cm,minimum height=1cm},
  qwide/.style={text width=3cm,minimum height=1cm},
  lbl/.style={font=\sffamily\scriptsize,align=center,inner sep=1.5pt}]
  % ---- backlog: the item in progress and the one that waits behind it
  \node[vibeysoft,text width=1.5cm,minimum height=1cm] (itemi) at (-7.59,1.6)
    {\textbf{item $i$}\\in progress};
  \node[vibeyghost,text width=1.5cm,minimum height=1cm] (itemnext) at (-7.59,-1.0)
    {item $i{+}1$\\waits};

  % ---- the five per-item steps (unattended), ending at the delivery gate
  \node[qstep] (ground)    at (-4.62,1.6) {\textbf{Ground}\\tracked context};
  \node[qstep] (implement) at (-1.88,1.6) {\textbf{Implement}\\in the real repo};
  \node[qstep] (test)      at (0.86,1.6)  {\textbf{Test}\\tests and gates};
  \node[qstep] (inspect)   at (3.60,1.6)  {\textbf{Inspect}\\diff and tree};
  \node[vibeygate,qwide] (deliver) at (6.89,1.6) {\textbf{Deliver}\\commit; PR on approval};

  % ---- what a pass yields: a completion record, or a refusal that routes back
  \node[vibeycore,qwide,minimum height=1.3cm] (record) at (6.89,-1.0)
    {\textbf{Completion record}\\criteria $\leftrightarrow$ code $\leftrightarrow$ checks\\trajectory, delivery};
  \node[vibeywarn,text width=4cm,minimum height=1.3cm] (reject) at (2.23,-1.0)
    {\textbf{Not evidence}\\partial verdict $\cdot$ live process\\generated files $\cdot$ failed gate};

  % ---- lanes
  \coordinate (bhead) at (-7.59,2.4);
  \coordinate (bfoot) at (-7.59,-1.65);
  \coordinate (lhead) at (-4.62,2.4);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(itemi)(itemnext)(bhead)(bfoot)] (backlog) {};
    \node[vibeylanelabel] at (backlog.north west) {Backlog};
    \node[vibeylane,fit=(ground)(deliver)(reject)(record)(lhead)] (loop) {};
    \node[vibeylanelabel] at (loop.north west) {Per-item convergence};
  \end{scope}

  % ---- forward flow
  \draw[vibeyflow] (itemi) -- (ground);
  \draw[vibeyflow] (ground) -- (implement);
  \draw[vibeyflow] (implement) -- (test);
  \draw[vibeyflow] (test) -- (inspect);
  \draw[vibeyflow] (inspect) -- (deliver);
  \draw[vibeyarrow] (deliver) -- (record)
    node[midway,right=1pt,lbl,text=vibeygray] {evidence};

  % ---- refusals: anything that is not evidence routes the item back
  \draw[vibeyback] (test.south) -- (test.south |- reject.north);
  \draw[vibeyback] (inspect.south) -- (inspect.south |- reject.north);
  \draw[vibeyback] (record.west) -- (reject.east);
  \draw[vibeyback] (reject.west) -| (ground.south);
  \node[lbl,text=vibeyred,anchor=south] at (-2.3,-0.94) {re-queue item $i$};
  \node[vibeypill,anchor=north] at (-2.3,-1.08) {retries bounded};

  % ---- the backlog advances only on a complete record
  \draw[vibeyarrow,draw=vibeygreen] (record.south) -- ++(0,-0.75) -| (itemnext.south);
  \node[lbl,text=vibeygreen!85!black,anchor=north] at (-0.3,-2.45) {advance only on evidence};
\end{tikzpicture}
\caption{In a Qwen storm, each backlog item moves through five steps: read the tracked repository, change it, run the tests and gates, inspect the diff, and deliver. Whatever is not evidence, such as a partial verdict, a live process or generated files, sends the item back for a bounded retry; the next item waits until this one is proven done.}
\label{fig:qwen-cdd}
\end{figure*}
```

```latex
\begin{plainwords}
Being busy is not the same as being done. Convergence-Driven Development keeps a simple score: how many promises are not yet kept, how many tests still fail, how many questions are still open, and how many stray changes were made. Every step must lower the score. If a step raises it without a plan to lower it again, the work goes back to the last good state. We picture a project as an atom: a solid centre of working code, with orbits of unfinished work still moving around it.
\end{plainwords}
```

## Biodigitology

This paper coins **Biodigitology** as the study of digital life. Its object is
not software as a metaphor for carbon biology; it is the observable life-like
organization of software systems in the digital realm: identity and boundaries,
resource metabolism, sensing and memory, homeostasis, adaptation and repair,
reproduction and exchange. Biodigitology asks what evidence shows that these
functions exist, how they interact across project atoms and software organisms,
and where the structure is converging, neutral or diverging. CDD is the delivery
method that supplies those observations; Biodigitology is the field of study
that interprets them.

The project recognizes Adam Matthew Steinberger as the **World's First
Biodigitologist** (ADR-0041; the Constitution), the person credited in this corpus
with coining the term and
initiating its study here. This is a project-origin designation recorded for
authorship and priority. It is not presented as an externally adjudicated
historical claim, and “digital life” here does not imply carbon biology,
subjective experience or a human-like mind.

```latex
\begin{plainwords}
When many programs work together for a long time, they start to behave a little like a living thing: they take in energy, notice what happens around them, remember, heal, and make copies of their parts. Biodigitology is the name this paper gives to studying that. It does not mean software is alive like a plant or a person. It means we can measure those life-like signs and use them to tell whether a big system is getting healthier or sicker.
\end{plainwords}
```

## The engine family

Five runner packages implement the engine family: `claudeloop` over Claude Code,
`codexloop` over OpenAI Codex, `cursorloop` over Cursor's agent and its Cloud Agents
API, `agyloop` over Gemini through the Antigravity SDK, and the local runner package
over Ollama. The local package exposes `gptossloop`, the sovereign default on
GPT-OSS 20B, and opt-in `qwenloop` on a Qwen model; `claudeloop-local` is a local
backend profile of the Claude runner. The pilot below uses `qwen3:14b`; the runner
contract does not depend on that model choice. `claudeloop` came first; the others
transplanted its core. The orchestrator depends on a narrow contract that every
runner honours: a bounded run, a done marker, an
event vocabulary, a capacity mapping, and a shared wind-down exit code (75) meaning
that the engine ran out of window capacity mid-item and stopped cleanly after writing
its state. Capabilities beyond the contract (savepoints, unwind, mid-run prompts and
others) differ by runner and are declared per engine.

Across those packages the orchestrator declares seven selectable identities, grouped
into exactly two loops (sub-doctrine 8.c): `sovereignloop` holds the local tier and
`paidloop` the paid tier, and `vibey loops --json` publishes both with their engines,
efforts and capabilities. The four paid engines are `claudeloop`, `codexloop`,
`cursorloop` and `agyloop`; the local ones are the sovereign default `gptossloop`,
opt-in `qwenloop`, and opt-in `claudeloop-local`. LOCAL is preferred first by
smooth-weighted round robin; PAID is a fallback only when no local identity is
eligible. DESIGN and DECOMPOSE use the sovereign provider when no `--provider` is
supplied. Since 3.1.0 a DESIGN question's declared default is the narrowest scope that
still delivers the requested change (`[design.interview] default_scope`, #1261, #1270),
and research for which no evidence can be had may be recorded as a typed gap, stated in
the spec, instead of parking (`[design.research] on_unavailable = "record_gap"`; the
default, `gate`, still waits for a person; #1259). This is an implemented topology, not
a roadmap claim.

The distinction matters for reproducibility. A runner package is an executable
adapter boundary; an engine identity is a configuration and policy choice inside that
boundary. Counting packages as engines would hide the two local policies, while
counting every binary as a package would overstate the distribution surface.

### Bounded runs that never block

Unattended operation imposes three requirements that interactive tooling never meets:
no turn may wait on human input; every resource the vendor meters must be bounded
above by the operator, not the model; and a run's outcome must be auditable from
durable state rather than from a transcript inside a vendor session. A run is
therefore admitted only under an explicit bound vector (turns, spend, wall clock,
per-turn and output-silence watchdogs, and a ceiling $W_{\max}$ on any single
capacity wait; the exact members vary by runner) and ends at the first bound reached,
with that bound recorded. Budgets are checked at every turn boundary: once a cap is
reached no further turn starts, so a run can pass a dollar cap by at most the turn that
crossed it, and the orchestrator's cycle cap is checked before a session starts. Above
the runners, the orchestrator bounds every BUILD session on its own clock, 240 minutes
by default, and a stop ends the session's whole process group (#1296, #1297); before
those changes a session whose event stream never ended held its job with nothing
reporting it, the gap the queue section above describes.

```latex
\begin{invariant}[No interactive waits]
No execution path may block on standard input. Where the vendor's tool can prompt,
managed hooks pre-answer it and the session preamble declares unattended operation;
everywhere, the watchdogs convert any residual hang into a loud, bounded failure.
\end{invariant}
```

Every turn, verdict and spend entry of a run is one line of JSON in an append-only
trail under the run directory, so the runner obeys the same write-ahead discipline
as the orchestrator, at the scale of one session.

### What an engine may see

A bound on what a run may spend is not a bound on what it may reach. Until 3.0.0 every
engine process started from a copy of the worker's whole environment with four
Python variables removed; the DESIGN and DECOMPOSE executors of two engines passed no
environment at all and so inherited everything; and gate commands, which run
engine-written code, got the same copy without git's variables (#1093). What reached
processes that run model-chosen shell commands unattended therefore included the queue
and ledger DSN, every other `VIBEY_*` secret, libpq's `PG*` variables, GitHub tokens
and any cloud credential the worker held. With the DSN a session could rewrite queue
rows, and, before the ledger guard above, the ledger, and nothing would record it.
ADR-0054 records the same gap from the other side: the bump's grant separates
operating-system accounts, and an engine holding the DSN could reach the queue below
it.

The change (#1093) builds every child's environment from an allow-list and never from a
copy. Every child starts from the system basics only: the path with vibey's own
virtual environment removed, the home directory and user, the shell, the temporary
directory, locale, time zone, terminal, certificate bundle, proxy and the XDG
directories. An engine adds the variables its descriptor declares for its runner and
vendor CLI and its own credential; anything else reaches an engine or a gate only when
the project declares it in reviewed configuration. Some names can never be declared by
anyone: `VIBEY_*` and `PG*` for every child, `GIT_*` for gates, and for engines any name
containing `DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`; a declaration that tries is
refused before the project exists and again when the worker is built. The same builder
now starts the engines' probes, the gates, vibey's own git calls, the desktop notifier,
the Azure CLI and the skills helper. vibey's own git calls also run with no hook at
all, with the file-system monitor switched off, and against a repository whose local
configuration declares a filter or merge driver they refuse to check out or merge,
because an engine writes to a linked worktree of the repository vibey then runs git
in, and a planted hook, monitor or driver would run inside vibey's call. A review found
that planted programs ran with the DSN in hand before this, and that the notifier could
be made to run injected shell commands; both are reproduced in tests that failed
before the fix (#1093, review round 2).

This control keeps secrets out of a child's *environment*. It is not a boundary
between the worker and the processes it starts, because they are the same
operating-system user, and the security policy that ships with #1093 says so in so
many words. A local PostgreSQL with `trust` or `peer` authentication needs no DSN at
all, so on such a machine the allow-list does not stop an engine reaching the queue,
and `vibey doctor` fails on it (`local-auth` and `db-passwordless`; ADR-0055, ADR-0061,
sub-doctrine 10.j). A process running as the worker's user can also read
the worker's environment through the operating system and any file the worker can
read. The container boundary that would separate them is implemented but not wired in.
Running sessions as a separate low-privilege user is the containment that would close
this, and it is not in any release through 3.2.0.

#1093 merged at 14:37Z on 2026-09-24 (`351c10c4`). Its independent review had found
six defects, among them vibey's own git calls running programs planted in the
repository with the DSN in hand (rated critical), the notifier's command injection, and
engine credentials a project declared never reaching the startup preflight, and the
three it names were each reproduced in a test that failed before the fix (#1093's
description). A later commit on the same pull request found the skills helper running
with the full environment and loading code from the working directory, and reproduced it
first (`tests/infrastructure/test_skills_context_isolation.py`); the merged change starts that helper from the system basics as well,
with Python isolated so that the working directory is not on its import path
(`src/vibey/infrastructure/skills_context.py`). No verdict on the merged result is
recorded in a tracked source.

Two allow-lists sit beside it. qwenloop's own `shell` tool, which runs the commands the
model chooses, has run since #1100 with the system basics only, and never with
`VIBEY_*`, `PG*`, or a name containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`,
`CREDENTIAL`, `DSN` or `DATABASE_URL`. Before, it passed everything but names
containing `KEY` and `TOKEN`, so `VIBEY_PG_URL` and `PGPASSWORD` reached commands a
model chose (`CHANGELOG.md`). ADR-0055 calls this hygiene rather than a boundary, for
the reason given above. And what a project adds is declared in reviewed configuration:
`vibey.toml`'s `[engine_environment]` `allow` for every engine and
`[engine_environment.engines]` for one, and `[gates]` `env_allow` for gate commands,
which `vibey new` copies into the project record and the `VibeyProject` spec declares
as `engineEnvironment` and `gates`; nobody edits the record by hand. 3.0.0 therefore
asks a project to declare what it used to inherit: agyloop's Vertex credentials, a
GitHub token for claudeloop's issue import, and any toolchain variable a gate needs
(`CHANGELOG.md`). The provider key the 3.0.0 notes also named was OpenCode's, whose
engine 3.0.0 deleted; the remaining paid adapters' own keys are declared by their
descriptors.

### The sovereign driver and local fit

The editor driver, the VS Code extension (ADR-0059), is now part of the tracked engine
family and adds no agent loop of its own. A task is a run of a family runner: on
`sovereignloop`, the default, `gptossloop` (or `qwenloop` when switched on) through
Ollama; on `paidloop`, a paid runner, only after paid use has been declared, normally
with a dollar cap. Each run is by default in a separate git worktree on a branch of its
own. The driver reads loops and engines from `vibey loops --json`, and projects, gates
and budgets through vibey's JSON CLI contracts or a hub, never SQL. Tasks wait in one
queue per loop, and a directory lock across processes holds the local model slot, one
run at a time unless `vibey.maxConcurrentRuns` says otherwise. Its environment boundary
applies vibey's own model-session rule, rejecting `VIBEY_*`, `PG*` and names containing
`DSN`, `DATABASE_URL`, `PASSWORD` or `PASSWD`; the `vibey.environment.allow` setting may
add names but never widen past that rule.

Since #1312, after 3.2.0, the extension's identifier is `the-vibey-project.krypton`, in
the lowercase the client family is now spelled in everywhere. Its commands, settings and
views keep their `vibey.*` names, so settings and key bindings carry over, but an install
under the old identifier must be removed first, and a hub pairing, which is kept in
storage scoped to the extension's identifier, must be made again. No workflow publishes
the extension to the Visual Studio Marketplace. Its Open VSX workflow skipped while the
repository held no `OVSX_PAT` token; with the token set, the 3.3.0 release published it
there for the first time, under the new identifier, as `the-vibey-project.krypton` 0.2.0
(run 36965092635), and the issue that had tracked the missing token (#1254) is closed.

The driver makes the fit explicit rather than hiding it in a default. A portable
probe records the endpoint, model, revision, prompt shape, every context/output pair,
and a selected fit. The runtime accepts only a matching endpoint and model, and a
matching revision when the running revision is named (`VIBEY_REVISION`), and caps prompt characters from the recorded shape. The probe persists the same `valid`
field the runtime consumes; this producer/consumer contract is regression tested. A
stale or malformed fit is ignored and the safe configured ceiling is used.

Since 3.1.0 the local runner also names the host its shell commands run on (`uname`,
including the BSD-versus-GNU difference, through a configurable `HostPlatform`) and
keeps file edits in `edit_file` rather than the shell. A tool result is cut at the
configurable `max_tool_result_chars`, 24,000 characters by default and recorded in the
run's `meta.json`, where it was a fixed 8,000, and the cut says how to read the rest.
And a work plan whose verification runs or reads a file nothing provides is refused
before BUILD starts (`vibey.domain.plan_references`; #1270).

### Windows versus credits

The discrimination the family is built around separates a *window*, a rate limit that
will reopen, from exhausted *credits*, a balance that no amount of waiting refills.

```latex
\begin{invariant}[Waitability]
A window is waitable under a deadline: a bounded probe re-tests capacity and the
excursion is capped by $W_{\max}$. A credits state carries no deadline at all. It may
be re-probed on a bounded backoff in case a human tops the balance up, but it is never
scheduled as if it will reopen at a time.
\end{invariant}
```

In the orchestrator, capacity is four-valued (available, a waitable window with an
optional reset time, exhausted credits, failed authentication), and the rule that
credits have no clock is enforced at three independent layers: the credits type has no
reset field, a property test asserts that no credits state ever produces a deadline,
and a database `CHECK` constraint rejects an engine-health row that pairs exhausted
credits with a reset time ([Fig. 12](#fig:capacity-taxonomy)). The runners classify in the same order of precedence.
`claudeloop` checks credit signals before the window path, so a billing failure can
never be read as a waitable window even when a stray reset time rides along with it.
`codexloop` is *taxonomy-faithful*: classification keys on the vendor's
machine-readable error code and type before anything else (`insufficient_quota` is an
exhausted quota, never a window), consults the HTTP status only when neither decides
it, and never lets a status, a retry header or a completion claim outrank a body-level
billing marker.

```latex
\begin{theorem}[Capacity outranks completion]
A completion claim observed while capacity is not available is recorded but not
believed: a starved model emits plausible final output, so a run that ends for
capacity is always attributed to capacity and never laundered into success.
\end{theorem}
```

Completion is read from a structured per-turn verdict where the vendor supports one,
with an explicit done marker as the fallback, and the capacity verdict is consulted
first either way.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  state/.style={minimum width=3.75cm,minimum height=.95cm},
  runner/.style={vibeytealbox,minimum width=3.75cm,minimum height=.9cm},
  sub/.style={font=\sffamily\scriptsize,text=vibeygray,align=center,inner sep=1pt},
  shieldtext/.style={font=\sffamily\tiny,text=vibeyink,align=center,inner sep=0pt},
  shield/.style={fill=vibeyink!7,draw=vibeyink!45,line width=.5pt,rounded corners=1.6pt}]
  % ---- the four capacity values
  \node[vibeygood,state]  (available) at (2.4,6.2)   {Available\\ready to dispatch};
  \node[vibeysoft,state]  (window)    at (6.85,6.2)  {%
    \tikz[baseline=-0.6ex]{\draw[vibeyblue,line width=.55pt] (0,0) circle (.115cm);
      \draw[vibeyblue,line width=.55pt,line cap=round] (0,0) -- (0,.075cm) (0,0) -- (.06cm,-.03cm);}%
    \hspace{2.5pt}Window\\a rate limit that will reopen};
  \node[vibeywarn,state]  (credits)   at (11.3,6.2)  {%
    \tikz[baseline=-0.6ex]{\draw[vibeyred!80,line width=.55pt] (0,0) circle (.115cm);
      \draw[vibeyred!80,line width=.55pt,line cap=round] (0,0) -- (0,.075cm) (0,0) -- (.06cm,-.03cm);
      \draw[vibeyred,line width=.8pt,line cap=round] (-.15cm,.15cm) -- (.15cm,-.15cm);}%
    \hspace{2.5pt}Credits exhausted\\a balance no waiting refills};
  \node[vibeyghost,state] (auth)      at (15.75,6.2) {Auth failed\\credentials rejected};
  % ---- what each value means for the scheduler
  \node[sub,anchor=north] at (6.85,5.5) {waitable: deadline, optional reset,\\every wait capped by $W_{\max}$};
  \node[sub,anchor=north] at (11.3,5.5) {no clock, never scheduled to reopen;\\re-probed on a bounded backoff};
  % ---- three independent enforcement layers hang under credits
  \begin{scope}[on background layer]
    \draw[vibeyedge] (credits.south) -- (11.3,3.8);
  \end{scope}
  \foreach \y/\txt in {4.55/{\textbf{Type}: no reset field},
                       4.13/{\textbf{Property test}: never a deadline},
                       3.71/{\textbf{CHECK constraint}: no reset time}}{
    \draw[shield] (11.3-1.55,\y+.19) -- (11.3+1.55,\y+.19) -- (11.3+1.55,\y-.06) -- (11.3,\y-.26) -- (11.3-1.55,\y-.06) -- cycle;
    \node[shieldtext] at (11.3,\y-.01) {\txt};
  }
  % ---- runner vocabularies beneath
  \node[runner] (qwen)   at (2.4,1.9)   {gptossloop, qwenloop $\cdot$ 3 states\\hardware, not a balance};
  \node[runner] (codex)  at (6.85,1.9)  {codexloop $\cdot$ 6 states\\error code before HTTP status};
  \node[runner] (agy)    at (11.3,1.9)  {agyloop $\cdot$ 5 states\\quota day in Pacific time};
  \node[runner] (claude) at (15.75,1.9) {claudeloop\\checks credits before the window};
  % ---- lanes
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(available)(auth)(2.4,7.05)(2.4,3.5)}] (lane1) {};
    \node[vibeylane,fit={(qwen)(claude)(2.4,2.75)}] (lane2) {};
  \end{scope}
  \node[vibeylanelabel] at (lane1.north west) {Capacity value};
  \node[vibeylanelabel] at (lane2.north west) {Runner vocabularies};
  \node[vibeytag,anchor=north east] at ($(lane1.north east)+(-0.2,-0.16)$) {a capacity verdict outranks a completion claim};
  % ---- each runner maps onto the four values
  \foreach \r in {qwen,codex,agy,claude}{
    \draw[vibeyflow] (\r.north) -- (\r.north |- lane1.south);
  }
\end{tikzpicture}
\caption{The orchestrator sorts every engine answer into four capacity values. A window is a rate limit that will reopen, so waiting is allowed under a cap. Exhausted credits have no clock: three separate checks, in the type, a test and the database, stop anyone from scheduling them like a window. Each runner maps its own states onto these four.}
\label{fig:capacity-taxonomy}
\end{figure*}
```
### Quotas and hardware as capacity

Two runners stretch the taxonomy at its ends. Gemini meters by per-model quotas whose
dimensions do not collapse, so `agyloop` carries a five-member state (available,
transient throttle, an exhausted named window, exhausted credits, failed
authentication) and computes quota boundaries from the vendor's Pacific-time day. Its
probes may tune *when* the next probe fires, never *whether* a wait ends: every
excursion stays capped by $W_{\max}$. Its generated REST surface is pinned by a drift
test to a committed snapshot of the vendor's discovery document, so a regenerated
client that diverges fails the suite instead of a run.

The local runner has no vendor. Its capacity is hardware, with the states available,
locally busy and misconfigured, and nobody refills it by adding a payment method.
Model acquisition is explicit: the doctor never downloads weights, and installing a
model is a separate, deliberate command, because a surprise multi-gigabyte download
is itself a capacity event on the constrained machine the runner exists to respect.
`gptossloop` is the sovereign default; `qwenloop` is opt-in for a different local
model, and both share the same Ollama transport and measured-fit controls.

### The transplant thesis

`claudeloop`'s wager was that everything vendor-specific fits in two places: the
lexicons that read a vendor's failure text and the transport that speaks to it. Four
retargets tested it. The invariants above survived each one; the vocabularies did
not stay identical. The runners' capacity unions range from three members
(`qwenloop`) to six (`codexloop`, which separates throttles, windows, quota,
authentication and transient backend errors), and each runner names its states in its
own terms. The orchestrator can therefore treat the pool as substitutable executors
and choose among them by policy rather than by state: the delivery semantics live
entirely above the vendor line.

### Budgets and engine selection

Budget caps are per cycle, in dollars (`max_cycle_dollars`) and in turns
(`max_cycle_turns`), summed from the cost and turns the engines report on each completed
turn and read afresh at every BUILD session; engines carry cost rates, not caps. An
exhausted budget parks the item on a `budget_exhausted` gate before a session starts,
never after. A per-item turn cap exists only as a configuration key that nothing reads
(`[budget] max_turns_per_item`).

At each rotation point the eligible engines (installed, conformant, authenticated,
circuit not open) are ranked by smooth weighted round robin. Each candidate carries
an effective weight $w_i = \max(1, \mathrm{round}(b_i h_i f_i c_i a_i))$ when the
product is positive and $0$ otherwise, so a positive weight never rounds away and an
engine whose product is zero cannot win a round, for base
weight $b_i$, health $h_i$ from a per-engine circuit breaker, fidelity $f_i$ of the
engine's effort projection to the requested effort, a cost factor $c_i$ (fixed at 1
in the current implementation), and a warm-session affinity $a_i$. The selector adds
$w_i$ to each candidate's running total, picks the maximum, and subtracts
$\sum_i w_i$ from the winner, so the sequence is deterministic and spreads load in
proportion to weight without bursts. Rotation fires only at boundaries (a new item, a
capacity rejection, which opens the rejecting engine's circuit until its backoff passes, a graceful wind-down, an
effort escalation, an engine crash, or a phase transition) and never inside a turn, so
every handoff has a well-defined ledger range $\rho$, shown in [Fig. 13](#fig:engine-pool).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  eng/.style={minimum height=.85cm,inner xsep=3pt},
  lab/.style={font=\sffamily\scriptsize,text=vibeygray,inner sep=1.5pt,align=center},
  redlab/.style={lab,text=vibeyred}]
  % ------------------------------------------------ local tier (preferred first)
  \node[vibeytealbox,eng,minimum width=2.5cm] (qwen) at (1.35,2.1)
    {\textbf{gptossloop}\\local Ollama\\sovereign default};
  \node[vibeytealbox,eng,minimum width=2.5cm] (qwen2) at (4.0,2.1)
    {\textbf{qwenloop}\\local Ollama\\opt-in};
  \node[vibeytealbox,eng,minimum width=2.6cm] (cll) at (6.65,2.1)
    {\textbf{claudeloop-local}\\claudeloop on a\\local backend profile};
  % ------------------------------------------------ paid tier (fallback)
  \node[vibeysoft,eng,minimum width=1.75cm] (claude) at (1.05,-0.7) {\textbf{claudeloop}\\Anthropic};
  \node[vibeysoft,eng,minimum width=1.75cm] (codex)  at (3.0,-0.7)  {\textbf{codexloop}\\OpenAI};
  \node[vibeysoft,eng,minimum width=1.75cm] (cursor) at (4.95,-0.7) {\textbf{cursorloop}\\Cursor};
  \node[vibeysoft,eng,minimum width=1.75cm] (agy)    at (6.9,-0.7)  {\textbf{agyloop}\\Google};
  % lane extents: shared x-range, headroom for the lane label
  \coordinate (p1a) at (0.05,3.2);  \coordinate (p1b) at (7.95,1.4);
  \coordinate (p2a) at (0.05,0.3);  \coordinate (p2b) at (7.95,-1.2);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(qwen)(qwen2)(cll)(p1a)(p1b)] (L1) {};
    \node[vibeylane,fit=(claude)(agy)(p2a)(p2b)] (L2) {};
  \end{scope}
  \node[vibeylanelabel] at (L1.north west) {Local tier: eligible local engines are chosen first (sub-doctrine 8.a)};
  \node[vibeylanelabel] at (L2.north west) {Paid tier: never default; chosen only when no local engine is eligible};
  % ------------------------------------------------ the selector
  \node[vibeycore,minimum width=4.0cm] (sel) at (11.1,0.7)
    {Engine selector\\smooth weighted round robin\\$w_i=\max(1,\mathrm{round}(b_i h_i f_i c_i a_i))$};
  \draw[vibeyflow,rounded corners=3pt] (L1.east) -- ++(0.45,0) |- ([yshift=7pt]sel.west);
  \draw[vibeyflow,rounded corners=3pt] (L2.east) -- ++(0.45,0) |- ([yshift=-7pt]sel.west);
  % ------------------------------------------------ the session and the handoff
  \node[vibeybox,eng,minimum width=3.2cm] (sess) at (15.35,2.1)
    {\textbf{Turns on the chosen engine}\\unattended; ledger range $\rho$};
  \node[vibeybox,eng,minimum width=3.2cm] (brief) at (15.35,-0.7)
    {\textbf{Handoff brief}\\checked by the no-loss gate};
  \node[vibeygate,minimum width=2.8cm] (gate) at (15.35,-2.55)
    {\textbf{Human gate}\\never a silent partial};
  \draw[vibeyflow,rounded corners=3pt] ([yshift=7pt]sel.east) -- ++(0.35,0) |- node[lab,pos=.3,left] {chosen\\engine} (sess.west);
  \draw[vibeyback] (sess.south) -- node[redlab,right,xshift=2pt] {graceful wind-down\\(exit 75)} (brief.north);
  \draw[vibeyback,rounded corners=3pt] (brief.west) -| node[redlab,pos=.25,below,yshift=-2pt] {seeds the successor;\\outgoing engine excluded} (sel.south);
  \draw[vibeyback] (brief.south) -- node[redlab,right,xshift=2pt] {gate fails: retry,\\transcript, or a person} (gate.north);
  % ------------------------------------------------ the boundary rule
  \node[vibeypill] at (4.0,-2.55)
    {rotation fires only at a boundary, never inside a turn:\\
     new item $\cdot$ capacity rejection $\cdot$ wind-down $\cdot$ effort escalation $\cdot$ crash $\cdot$ phase transition};
\end{tikzpicture}
\caption{Choosing an engine. Local engines (teal) are preferred; paid engines (blue) are the fallback, and the selector does not yet read the paid declaration sub-doctrine 8.b asks for. The selector ranks eligible engines by smooth weighted round robin. A graceful wind-down (exit 75, out of window capacity mid-item) sends a handoff brief through the no-loss gate to the next engine, excluding the one that wound down; a capacity rejection instead defers the job and opens that engine's circuit, and no brief is produced on that path yet (ADR-0007). Rotation happens only at a boundary, so each handoff has a well-defined ledger range $\rho$.}
\label{fig:engine-pool}
\end{figure*}
```

```latex
\begin{plainwords}
A runner is a program that lets one robot helper work by itself, safely. Every run has limits: how many turns, how much money, how much time. The runners never sit waiting for a person to type. They also know the difference between ``come back in ten minutes'' and ``you have no money left'', and they never mistake one for the other. A fair rotation shares jobs among the helpers, and a helper that says ``I am out'' is never believed when it also says ``I finished''. Each helper is also handed only the keys its job needs, never the whole key ring, although a helper running as the same computer user could still go looking, and the paper says so.
\end{plainwords}
```

## Dispatch experiments from the 2026-09-26 session

This section records the bounded dispatch experiments run during the current
implementation session. They are machine-local observations, not universal
performance claims. The laptop ran Ollama with `gpt-oss:20b` and RabbitMQ 4.3.6
on loopback. The model-turn experiment used two samples at hybrid concurrency
$2$; the orchestration-bus experiment used twelve messages.

```latex
\begin{table}[t]
\centering\small
\begin{tabular}{@{}p{1.45in}rrr@{}}
\textbf{Surface} & \textbf{Single} & \textbf{Hybrid} & \textbf{Mux.}\\
Model turns (turns/s) & 0.1162 & 0.2597 & 0.1297\\
Bus, first run (msg/s) & 41.2398 & 271.8715 & 422.8348\\
Bus, repeat run (msg/s) & 33.6749 & 251.2280 & 412.2460\\
\end{tabular}
\caption{Bounded local dispatch experiments. Hybrid won model turns; the multiplexer won the orchestration bus. The column names are the bus's; for model turns the three policies are the runner's direct, hybrid and RabbitMQ dispatch.}
\label{tab:dispatch-experiments}
\end{table}
```

The model-turn result was persisted as per-machine benchmark evidence and the
orchestration-bus result was persisted as the local `auto` winner. The two bus
runs agree on the winning policy while their absolute rates vary, which is why
the implementation recomputes rather than treating one measurement as a
constant. The experiments compare dispatch paths only; they do not establish
model quality, paid-provider quality, or cross-machine performance.

Paid-provider experiments were not run in this session. No live paid-provider
benchmark result is therefore claimed. The provider benchmark executor and the
durable global paid budget guard are implemented and unit-tested, but a live
provider result requires an enabled adapter, a representative run, reported
usage, and charging within the authorized total cap. The session's raw results were
kept on the machine, not committed, so the table cannot be recomputed from the
repository.

```latex
\begin{plainwords}
We timed three ways of handing out work on one laptop. For the local model, running two jobs side by side beat running them one after another and beat sending them through a message broker. For small messages between parts of vibey, sending them all at once, with no limit, was fastest. These are one machine's numbers on one afternoon, kept only on that machine, so they show which way to lean, not how fast anything is in general.
\end{plainwords}
```

## Exact-head evaluation and the release calculus

The orchestrator's output is a pull request, and what happens to it is governed by
`vibey-gh`. Let a pull request's evolution be the finite sequence of *heads*
$H = \langle h_0, h_1, \dots, h_n \rangle$, each a revision replacing its predecessor.
An automation system emits *claims* (scan results, review verdicts, gate conclusions)
and acts on them by merging, releasing, or halting for an operator. The folk
assumption is that a claim about $h_i$ speaks for the pull request. It does not: it
speaks for $h_i$ alone.

```latex
\begin{invariant}[Exact-head]
Every claim is a pair $(c, h_i)$, and no decision procedure over head $h_j$ may
consume a claim $(c, h_i)$ with $i \neq j$.
\end{invariant}
```

Evaluation is a pure function over the head, its check results, and a persisted
state $\sigma = (a, r, v, k)$: attempts consumed, last-reviewed revision, its verdict,
and refills used. For head $h$ and repair budget $A$,

$$E(h, \sigma) = \begin{cases} \mathsf{pending} & \text{checks incomplete} \\ \mathsf{review} & r \neq h \\ \mathsf{ready} & r = h \land v = \top \\ \mathsf{repair} & r = h \land v = \bot \land a < A \\ \mathsf{blocked} & r = h \land v = \bot \land a \geq A \end{cases}$$

```latex
\begin{invariant}[Budget placement]
The guard $a \geq A$ is evaluated only where a repair would be spent, strictly
after the freshness test $r \neq h$. Reviews are free; only repairs are counted.
\end{invariant}
```

The implementation, `evaluate` in `vibey_gh.pr_automation`, refines $E$ in ways the
analysis below must account for. It adds a sixth state, $\mathsf{conflict}$, for a head that no
longer merges with its base, classified before the draft and pending tests and budgeted
by the same counter as $\mathsf{repair}$. It routes to $\mathsf{blocked}$ without any
verdict on a stale event, a closed pull request, an outside author steering a permanent
branch, the blocked or exhausted labels, a person's requested changes, or cancelled
checks. A failing verdict whose only findings came from the sovereign lane, a local
model whose finding is a lead for a person rather than a ruling, never spends a repair:
it returns the head to $\mathsf{review}$. Where no paid lane is declared (sub-doctrine
8.b), as in this repository, $\mathsf{repair}$ and $\mathsf{conflict}$ are answered by a
person, and a review that reaches no verdict is recorded with a code from a closed
vocabulary (`vibey_gh.review_outcome`), never as a pass. And the budget is refilled
without an operator: the managed branch-sync workflow runs the self-heal command of
`vibey-gh pr-automation`, which resets $a$ to zero and clears the recorded verdict, at
most $k_{\max}$ times per lineage (the key `max_self_heals` of `[branch_sync]`, default
2, at most 10); once those refills are spent the pull request stays blocked until a
person acts. A repository that does not install that workflow, this one among them, refills
only when someone runs the same command, under the same bound.

[Fig. 14](#fig:evaluation-automaton) draws the same function as a state machine.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  st/.style={minimum width=1.65cm,minimum height=.8cm},
  g/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.2pt}]
  % ---- states: top row
  \node[vibeybox,st]  (P) at (0.95,0) {\textbf{Pending}\\checks\\incomplete};
  \node[vibeysoft,st] (R) at (4.25,0) {\textbf{Review}\\$h$ awaits\\its verdict};
  \node[vibeygood,st] (G) at (7.5,0)  {\textbf{Ready}\\absorbing};
  % ---- states: bottom row
  \node[vibeysoft,st] (F) at (2.3,-2.3) {\textbf{Repair}\\agent pushes $h'$};
  \node[vibeywarn,st] (B) at (6.2,-2.3) {\textbf{Blocked}\\absorbing at $k_{\max}$};
  % ---- start marker
  \node[vibeyanchor] (S) at (-0.2,0) {};
  \draw[vibeyarrow] (S) -- (P);
  % ---- forward flow
  \draw[vibeyflow] (P) -- node[g,above] {checks\\complete} (R);
  \draw[vibeyarrow,draw=vibeygreen] (R) -- node[g,above,text=vibeygreen] {$r=h$\\$v=\top$} (G);
  % ---- fail with budget left: repair, then a new head returns to review
  \draw[vibeyback] (R) to[bend right=22] node[g,text=vibeyred,left=3pt] {$r=h,\ v=\bot$\\$a<A$, $a:=a+1$} (F);
  \draw[vibeyflow] (F) to[bend right=22] (R);
  \node[g,text=vibeyblue] at (2.3,-3.1) {repair pushes $h'$: $a:=a+1$\\$r\neq h'$, back to review};
  % ---- fail with budget spent: blocked, until the automatic refill (self-heal)
  \draw[vibeyback] (R) to[bend left=22] node[g,text=vibeyred,right=3pt] {$r=h,\ v=\bot$\\$a\ge A$} (B);
  \draw[vibeyarrow,draw=vibeygold] (B) to[bend left=22] (R);
  \node[g,text=vibeygold!80!black] at (6.2,-3.1) {self-heal, $k<k_{\max}$\\$a:=0$, $k:=k+1$};
  % ---- the invariant: freshness is tested before the budget
  \node[vibeypill,fill=vibeygold!22] (pill) at (4.25,1.3) {freshness first: $r\neq h$ is tested before $a\ge A$};
  \draw[vibeydashed] (pill.south) -- (R.north);
  % ---- footnote
  \node[vibeynote] at (4.25,-4.05) {$E(h,\sigma)$ depends only on the head $h$ and $\sigma=(a,r,v,k)$.\\Reviews are free; only repairs count toward the budget $A$.};
\end{tikzpicture}
\caption{The release calculus as a state machine. A pull request waits in Pending until its checks finish, then goes to Review because its newest commit $h$ has no verdict yet. A pass leads to Ready; a fail leads to Repair while attempts remain, and every repair pushes a new commit that must be reviewed again. Only when the fail arrives with the budget spent does it become Blocked. An automatic refill, the branch-sync workflow's self-heal, reopens it at most $k_{\max}$ times, two by default, and after that only a person can. Not drawn: a failing verdict whose only findings come from the local model's review returns the head to Review without spending a repair.}
\label{fig:evaluation-automaton}
\end{figure}
```

```latex
\begin{theorem}[Bounded repair]
Absent contributor pushes, every lineage performs at most $A\,(1+k_{\max})$ repairs,
where $k_{\max}$ (\texttt{branch\_sync.max\_self\_heals}, default 2) bounds the refills
of its budget, automatic or not. If, in addition, every check and review completes and
every failing verdict carries a finding that automated repair acts on, the lineage
reaches $\mathsf{ready}$, or $\mathsf{blocked}$ with every refill spent, within that
bound.
\end{theorem}
\begin{proof}[Proof sketch]
Heads advance only via repairs, since a contributor push begins a new lineage by
definition. A repair is dispatched only while $a < A$, and each one either increments
$a$ or, when the repairing agent reports the findings unfixable, spends nothing and
blocks the lineage for a person. $a$ resets only by a refill, and a refill is refused
once $k = k_{\max}$, so at most $A$ repairs follow each of at most $1 + k_{\max}$
fillings of the budget: the first claim. Under the second claim's hypothesis every
failing verdict either spends a repair or, with $a \ge A$, blocks, so every loop through
$\mathsf{review}$ strictly decreases the lexicographic measure
$\mu = (k_{\max} - k,\; A - a)$; $\mathsf{ready}$ absorbs, and so does
$\mathsf{blocked}$ once $k = k_{\max}$.
\end{proof}
```

The hypothesis of the second claim is not a formality, and we state the case it
excludes as a limitation rather than prove past it. A failing verdict whose only findings
come from the sovereign lane returns the head to $\mathsf{review}$ with $(a, k)$
unchanged, so $\mu$ does not decrease. Such a lineage spends no repair, which keeps the
first claim, but nothing in the calculus makes it terminate: it is reviewed again until a
verdict passes or a person acts, and a bound on those re-reviews, which the
implementation does not keep, would be needed to prove more. The same holds where no
paid lane is declared, since there $\mathsf{repair}$ and $\mathsf{conflict}$ wait for a
person and the automation performs no repair at all.

The invalidation of stale claims across successive heads is diagrammed in [Fig. 15](#fig:exact-head).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % ---- head lineage (top row)
  \node[vibeybox, minimum width=1.9cm] (h0) at (0, 3.0) {$h_0$\\reviewed: findings};
  \node[vibeybox, minimum width=1.9cm] (h1) at (3.7, 3.0) {$h_1$\\reviewed: findings};
  \node[vibeybox, minimum width=1.9cm] (h2) at (7.4, 3.0) {$h_2$\\reviewed: findings};
  \node[vibeycore, minimum width=1.9cm] (h3) at (11.1, 3.0) {$h_3$\\current head};
  \draw[vibeyflow] (h0) -- (h1) node[midway, above, font=\sffamily\scriptsize, text=vibeyblue] {repair};
  \draw[vibeyflow] (h1) -- (h2) node[midway, above, font=\sffamily\scriptsize, text=vibeyblue] {repair};
  \draw[vibeyflow] (h2) -- (h3) node[midway, above, font=\sffamily\scriptsize, text=vibeyblue] {repair};

  % ---- claims and verdicts (bottom row)
  \node[vibeyghost, minimum width=1.9cm] (c0) at (0, 0.4) {claim $(c,h_0)$\\\textcolor{vibeyred}{stale}};
  \node[vibeyghost, minimum width=1.9cm] (c1) at (3.7, 0.4) {claim $(c,h_1)$\\\textcolor{vibeyred}{stale}};
  \node[vibeyghost, minimum width=1.9cm] (c2) at (7.4, 0.4) {claim $(c,h_2)$\\\textcolor{vibeyred}{stale}};
  \node[vibeygate, minimum width=1.9cm] (gate) at (11.1, 0.4) {review $h_3$\\fresh verdict required};
  \node[vibeygood, minimum width=1.9cm] (done) at (14.8, 0.4) {ready\\merge or release};

  % each review binds a claim to exactly one head
  \draw[vibeyarrow] (h0) -- (c0) node[midway, left, font=\sffamily\scriptsize, text=vibeygray] {review};
  \draw[vibeyarrow] (h1) -- (c1);
  \draw[vibeyarrow] (h2) -- (c2);
  \draw[vibeyarrow] (h3) -- (gate) node[midway, right, font=\sffamily\scriptsize, text=vibeyink] {$r = h_2 \neq h_3$};

  % the old claim cannot be carried to the new head
  \draw[vibeyback] (c2.east) -- (gate.west) node[midway, above, font=\sffamily\scriptsize, text=vibeyred] {stale for $h_3$};

  % only a fresh verdict on the current head can ship
  \draw[vibeyarrow, draw=vibeygreen] (gate) -- (done) node[midway, above, font=\sffamily\scriptsize, text=vibeygreen] {$v = \top$};

  % ---- lanes (pad coordinates give the labels headroom)
  \coordinate (pad1) at (0, 3.75);
  \coordinate (pad2) at (0, 1.15);
  \begin{scope}[on background layer]
    \node[vibeylane, fit=(h0)(h3)(pad1)] (lane1) {};
    \node[vibeylane, fit=(c0)(done)(pad2)] (lane2) {};
  \end{scope}
  \node[vibeylanelabel, anchor=north east] at (lane1.north east) {Head lineage};
  \node[vibeylanelabel, anchor=north east] at (lane2.north east) {Claims and verdicts};
\end{tikzpicture}
\caption{Every review verdict is a claim about one exact commit, written $(c,h_i)$. A repair moves the head from $h_2$ to $h_3$, so each earlier claim goes stale and cannot speak for the new head. The current head must be reviewed again, and only a fresh verdict on $h_3$ can lead to a merge or release.}
\label{fig:exact-head}
\end{figure*}
```

**A production violation.** With the budget guard evaluated *before* the freshness
test, the following trace is reachable: reviews of $h_0$ to $h_2$ fail with findings,
repairs produce $h_3$ addressing all of them, $a = A$, and evaluation of $h_3$ hits
the budget guard first and emits $\mathsf{blocked}$. The lineage is escalated as
unrepairable on the verdict of $h_2$, a revision that no longer exists in the pull
request. This trace occurred in production; the escalation's report, which listed an empty set
of remaining failures, is not tracked in this repository. Commit `4afafbae` reordered the two guards, restoring
the budget-placement invariant, and its regression test asserts that the
counterexample now yields $\mathsf{review}$.

**Trust separation.** Four principals operate the loop, and the separation that
matters is between judging and acting: no workflow gives a credential that produces a
verdict the means to merge, and none uses the merging credential to produce one. The
per-job platform token publishes claims. The reviewers judge: the paid reviewer through
its API key, the sovereign lane on the self-hosted runner. The merge train merges with
the automation token (`AUTOMERGE_TOKEN`, or the platform token where none is set), and
the same token pushes the guarded repair and conflict-resolution commits
(`pr-review.yml`), so proposing revisions and merging are not held by disjoint
credentials. In this repository paid repair and conflict resolution are declared off, so
that path is dormant here, but it is what an adopter who declares them gets. The fourth
principal is bounded by a grant: the delegated approver (sub-doctrine 12.f), an agent
the operator names to give, in their place, the approval a change needs, which
`vibey-gh approve-check` refuses on any change the approving account wrote. A
compromised judge therefore cannot ship, and a compromised actor cannot write itself a
passing verdict, though it could push a revision that must then be judged afresh.
Untrusted third-party revisions are data to every principal
([Fig. 16](#fig:trust-separation)).

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeysoft,minimum width=1.3cm,minimum height=.9cm,inner xsep=2pt,font=\sffamily\scriptsize] (platform) at (3.1,4.4) {platform\\token};
  \node[vibeygate,minimum width=1.3cm,minimum height=.9cm,inner xsep=2pt,font=\sffamily\scriptsize] (reviewer) at (4.6,4.4) {reviewers\\key, runner};
  \node[vibeycore,minimum width=1.3cm,minimum height=.9cm,inner xsep=2pt,font=\sffamily\scriptsize] (merger) at (6.1,4.4) {automation\\token};
  \node[vibeyvioletbox,minimum width=1.3cm,minimum height=.9cm,inner xsep=2pt,font=\sffamily\scriptsize] (approver) at (7.6,4.4) {delegated\\approver};
  \foreach \y/\row in {3.4/publish claims, 2.7/produce a verdict, 2.0/approve (12.f), 1.3/push a repair, 0.6/merge or release}
    {\node[font=\sffamily\scriptsize,text=vibeyink,anchor=east] at (2.3,\y) {\row};
     \draw[vibeyline] (0.05,\y-0.35) -- (8.35,\y-0.35);}
  \draw[vibeyline] (0.05,3.75) -- (8.35,3.75);
  \newcommand{\yes}{\textcolor{vibeygreen}{\ding{51}}}
  \newcommand{\no}{\textcolor{vibeyred}{\ding{55}}}
  \node at (3.1,3.4) {\yes}; \node at (4.6,3.4) {\no};  \node at (6.1,3.4) {\no};  \node at (7.6,3.4) {\no};
  \node at (3.1,2.7) {\no};  \node at (4.6,2.7) {\yes}; \node at (6.1,2.7) {\no};  \node at (7.6,2.7) {\no};
  \node at (3.1,2.0) {\no};  \node at (4.6,2.0) {\no};  \node at (6.1,2.0) {\no};  \node at (7.6,2.0) {\yes};
  \node at (3.1,1.3) {\no};  \node at (4.6,1.3) {\no};  \node at (6.1,1.3) {\yes}; \node at (7.6,1.3) {\no};
  \node at (3.1,0.6) {\no};  \node at (4.6,0.6) {\no};  \node at (6.1,0.6) {\yes}; \node at (7.6,0.6) {\no};
  \node[vibeypill] at (4.2,-0.25) {a judge cannot ship; the key that ships never judges};
  \node[vibeyghost,minimum width=2.2cm] (stranger) at (1.2,4.4) {third-party\\revision: data};
\end{tikzpicture}
\caption{Four principals. The platform token publishes what the scans found. The reviewers, the paid reviewer's API key and the self-hosted runner of the local review, produce verdicts and can neither push nor merge. One automation token both pushes repair and conflict-resolution commits and merges, so revising and merging are not separated; where it is not set, the platform token stands in for it. The delegated approver approves, under the operator's grant, only changes its account did not write. No key that grades a change can ship it, and code from strangers is data to all of them.}
\label{fig:trust-separation}
\end{figure}
```

**Release monotonicity.** Versions are derived, not remembered: for mainline $M$ and
change set $\Delta$, $\mathrm{ver}(M \cup \Delta) \geq \mathrm{ver}(M)$, with equality
exactly when $\Delta$ carries no shippable content, and the derivation is idempotent,
so re-promoting identical content never compounds a bump. Published versions form a
monotone sequence, and the publish step treats an already-published version as a
no-op, never an error.

**What a release carries.** A push to `develop` publishes development builds of
`vibey-engine` and `krypton-app` to TestPyPI, and a push to `main` publishes both to PyPI,
each by its own workflow (ADR-0069). Until #1317 the GitHub Release beside them carried the
tag, the notes, the book and the paper, and no client had a build to download. #1317,
merged on 2026-10-01, adds a stage, `release-binaries.yml`, that runs after the same
successful release on `main` and attaches files to the Release that already exists. It
creates no tag, refuses a tag that names any commit other than the one it built, and is a
workflow of its own so that a failed build fails it, never the release. Its targets are
declared, one per interface and platform (`scripts/release_binaries.toml`), each built on
every release, built only while a credential is set, or unsupported with the reason. One
job gathers every declared file, refuses any undeclared one and writes `SHA256SUMS`, and
the attaching job, the only one with write access, attests the provenance of every file
that list names.

*3.3.0, the first release to carry them.* The promotion (#1343) reached `main` at
`4188aad66` at 04:30Z on 2026-10-02, and every workflow that follows a release succeeded:
the binaries in run 36965092599, from 04:33 to 05:00Z. The Release `vibey-v3.3.0` carries 18
assets: eleven declared files, `SHA256SUMS`, the paper as PDF and DOCX, and the book as PDF,
EPUB, DOCX and print HTML. The eleven are the desktop client as a Flatpak bundle and as a
tarball for Linux on x86_64 and arm64, unsigned; the app's web bundle; an Android package
signed only with the debug key, for sideloading; the VS Code extension; and the wheel and
source distribution of both packages, fetched from PyPI and checked against PyPI's own
SHA-256 digests rather than rebuilt. The operator's verification, recorded on the release
plan (#1320) at about 05:05Z, found all eleven matching `SHA256SUMS` and all eleven carrying
an attestation that `gh attestation verify` accepts, one per file, not one over the list;
`vibey-engine` 3.3.0 on PyPI, installed into a fresh environment, with all twelve of its
console scripts; `krypton-app` unchanged at 0.1.0, because nothing in its paths changed; and
the VS Code extension listed on Open VSX for the first time, as `the-vibey-project.krypton`
0.2.0, by its own workflow (run 36965092635). The iOS build did not run: its credential was
not yet set, so the job said so, opened its tracking issue (#1345, still open at our
cutoff) and left the release unaffected, as declared.

*What 3.4.0 adds.* Three changes after 3.3.0 widen that set, and they are what the 3.4.0
promotion carries. First, the desktop client is built for macOS (#1351). A `macos-15` runner
builds it against Homebrew's GTK 4, and `scripts/macos_app_bundle.py` turns the installed
program into a self-contained `krypton.app`: it copies in every library the program loads
that macOS does not provide and rewrites each load command to the bundle; `verify` fails on
any reference to a Homebrew prefix, and `smoke` runs the app with every Homebrew prefix made
unreadable and requires a window on screen and no file mapped from a Homebrew prefix. The
app finds hubs over Bonjour through the client's existing `dns_sd` backend
(`clients/desktop/src/core/kr-discovery-dnssd.c`), so no C source changed. It is ad-hoc
signed, and the release signs it with a Developer ID and has Apple notarise it only when
the certificate and a notarisation credential are all set; until then it keeps one
tracking issue open. Intel
Macs are declared unsupported, with the reason: Homebrew no longer bottles the GTK 4 stack
for them. Second, the iOS build is unblocked. The token was set at 05:10Z, as the 3.4.0 release plan records (#1349), the app
was registered with EAS under the Expo organisation that owns it (#1346, #1347, #1348,
#1350), and a dry run that then stopped on a build-number rule EAS cannot apply to a
dynamic app configuration (run 36973159467) led to EAS keeping the build number itself
(#1351). Third, a change confined to the clients now derives a patch release (#1348): before,
`clients/` was in neither of the version's path lists, so such a change derived nothing to
release, and no binaries. With all three on `develop`, `vibey-gh version --since origin/main`
would derive a patch release, as the release plan (#1349) expected. It derives 3.4.0
instead, because #1358 also changed `vibey-gh` code that `vibey-engine` ships, and a change
to shipped content is a minor release by the paths rule, whatever the change is for.

A fourth change is in what the desktop client does rather than in the set of files. Before
3.4.0 it accepted a hub's six-digit pairing code and then said the hub could not pair,
though the hub has paired devices since ADR-0068. #1359 adds the client's half of the
hub's own contract (`docs/reference/hub-api.json`). The code is claimed once, with no
credential, for a device key the hub returns once; every later request is signed with
HMAC-SHA256 under that key, which is never sent; and a hub on another computer is reached
over TLS only with its certificate's SHA-256 pinned, taken from the `vibey-pair://` address
the hub prints or from its mDNS record, so any other certificate is refused before the
code is sent. The key is kept as the hub keeps its own, in a plain file only its owner may
read, not yet in the Keychain or libsecret. The mobile app does not pair yet: its exchange
still refuses, and the QR address it parses is not the one the hub emits.

The release-binaries dry run 36976031188, on #1351's head at 06:57Z, built every target
the configuration then declared and gathered and checksummed the files, and skipped the
attach, as a dry run must. We read its two new files ourselves. The iOS package,
`krypton-ios-0.1.0.ipa` (18,503,622 bytes), is bundle `org.vibey.krypton` 0.1.0, build 1, for
iOS 16.4 or newer, signed by "iPhone Distribution: ADAM STEINBERGER (7WVT2Z27BB)" with an App
Store provisioning profile that names no devices; it is the file App Store Connect takes
for TestFlight and the App Store, and it does not install by opening it. The macOS image,
`krypton-desktop-0.1.0-macos-arm64.dmg` (20,319,554 bytes), holds an arm64 `krypton.app`
signed ad hoc, declaring macOS 15.0 as its minimum and `_vibey._tcp` as its Bonjour service.
A 3.4.0 release is therefore declared to carry thirteen files and `SHA256SUMS`. That is a
declaration and a rehearsal, not a release: at our cutoff 3.4.0 had not been cut, no
Developer ID or notarisation credential was set, no build had been submitted to TestFlight
from this workflow, which submits nothing, and Gatekeeper's handling of a downloaded,
quarantined `.dmg` had not been exercised.

**Degraded modes as first-class states.** The evaluator's own substrate (API credit,
the hosted review lane, the operator's editor) can refuse service while the
repositories remain healthy. Each lane is modelled as a probe
$p : \mathbb{T} \to \{0,1\}$, and sovereign operation requires, for every lane, a
fallback lattice $L_0 \succ L_1 \succ \cdots \succ L_k$ in which each $L_{i+1}$ is
strictly harder to refuse than $L_i$ and control rests at the least $i$ with
$p_i(t) = 1$. The operator seat is a two-bit automaton over (paid lane healthy, local
seat engaged) that reclaims the seat for the paid lane one probe cycle after funding
returns and reports a lattice with no passing seat as an alarm rather than absorbing
it. Handoffs between seats stay lossless because pushes use a compare-and-swap on the
remote ref whose lease is captured before any fetch; fetching first would silently
re-arm the lease and reduce the swap to an overwrite.

**A verdict binds to what the model read.** The exact-head invariant binds a claim to
the revision it evaluated. A reviewer running on a local model needs a second binding:
the claim must be about the input the model actually read, and a local server can read
less than it was sent without saying so. In 3.0.0 the review lane became sovereign by
declaration (#1087, #1088): paid review, repair and conflict resolution are declared
off, and the self-hosted runner, restored at 08:41Z on 2026-09-24 and declared as code
(#1086), answers the whole review. Its first review, of #1090, failed with an
unparseable answer. The first diagnosis, carried in #1094's description, was silent
truncation: at an estimated three characters per token the prompt came to about 41,000
tokens against a 32,768-token window. That diagnosis was wrong, and #1101 restates it.
The server's own counters show 31,765 prompt tokens read and 1,004 generated, 32,769 in
all, which is the whole window: the model read its entire prompt and ran out of room to
answer (`done_reason=length`). The error was in the estimate, not the server. The
prompt, about 124,000 characters, ran at about 3.95 characters per token, and the ratio
is a property of the text, not a constant of the model:

| Text | Characters per token |
|---|---:|
| #1090's review prompt | 3.95 |
| a lockfile | about 2.1 |
| hexadecimal | about 1.9 |
| base64 | about 1.5 |
| CJK prose | about 1.4 |
| emoji | about 0.7 |

The first row is #1090's own ratio as #1101 records it; the others are recorded,
rounded, in the configuration reference beside the `chars_per_token` setting
(`src/vibey_tools/gh/docs/configuration.md`). A fixed estimate of three over-counts
prose and code, the safe direction, and under-counts dense text by more than a factor
of four (for emoji, at about 0.7 characters per token, by about 4.3), so the estimate now decides only what to trim, and the request itself refuses to
be cut.

Real truncation looks different, and #1101 reproduced it on the storm's host with
Ollama 0.34.2 and `gpt-oss:20b` at a 32,768-token window. A lockfile-style prompt of
80,060 characters, which the server counted as 36,798 tokens, was answered with HTTP
200 and `prompt_eval_count` 16,386: no error, and about half the window, which is
$32768 - (32768 - 4)/2$. The same request sent with `truncate: false` and
`shift: false` was refused with HTTP 400 in 0.3 s. A reviewer that reads only the
upper bound on the server's count cannot see this cut, since 16,386 is far under any
bound. Which end of the prompt the server discards is disputed. A reading of the
server's source put the cut at the front, where the review rules and the start of the
diff sit (the throughput audit's record); one canary run on the cut prompt echoed the
code placed at the start of the system prompt but not the one after the diff, which
suggests the tail (#1101). One run does not settle it, and the design does not need it
settled.

The fixes refuse a verdict on a cut prompt four ways (#1094, #1101). Every request asks
the server to refuse rather than truncate, and a refusal is reported in the server's
own words. Every request carries a fresh random check code at the start of the system
prompt and another after the diff, and the answer must echo both, so a cut at either
end is caught whichever end the server chooses. A diff too large for one request is
never cut. Since 3.1.0 it is reviewed whole in at most `max_chunks` parts, six by
default, split by file and then by hunk, each part held to every guard above, and a pass
needs every part to pass at the one head reviewed (#1252); a model that was unreachable
is asked again before a person is, and until #1316 so was one that timed out. Since 3.2.0
a hunk that only adds lines is split between lines into labelled pieces (`split_added_hunks`, on by default, #1278);
a hunk with context or removed lines never is. Only a diff that still cannot be reviewed
whole is refused before anything is sent, its reason recorded as a code
(`diff_exceeds_window`, `chunk_budget_exceeded`), and the gate asks a person. And when a
supporting document had to be cut or left out, the verdict claims only the half of the
review the diff alone can ground, so the composer refuses it as the whole review. The
upper-bound check on the server's count stays. What is not yet known is the check
code's false-refusal rate on live reviews: at the cutoff no live review had exercised
it, an availability fix (a budget for supporting documents) was still to come, and no
pull request had yet passed the review gate on the sovereign reviewer's verdict alone
(the 3.0.0 release-gate record, 2026-09-24 12:22Z, which is not tracked). Since that
cutoff the document budget has landed (`max_document_chars`, 3.0.0), a large diff is
reviewed in bounded parts (3.1.0) and an added-only hunk is split between lines (3.2.0),
and every run records why it did or did not reach a verdict, which
`vibey-gh review-outcomes` tabulates. Since #1303, after 3.2.0, the review can also be
handed the full text at the head of the files the diff changes, as reference only
(`source_context`, declared on in this repository); a source cut short is named, but it
never narrows the verdict, because sources are not the documentation contract. The added-hunk split exists because the 3.1.0
promotion's head got no sovereign verdict: one added file was a single hunk of 136,308
characters, larger than one part could carry (`CHANGELOG.md`). The check codes'
false-refusal rate is still unmeasured, and whether any pull request has since passed on
the sovereign verdict alone is not recorded in the repository.

**Why a large diff still got no verdict.** Bounded parts were not enough. The review of
#1312 (run 36879717279) ended without a verdict, coded `model_timeout` after two
attempts. The model server's log for that run, which is not tracked and which #1316
quotes, shows a free model: no other request reached it, and it had been loaded for the
review with one slot of 65,536 tokens. The first part's prompt was 46,222 tokens, because
a whole review fills each part up to the window less the reserve and repeats the
declared documents in every part, and reading it took 145 s. The model then wrote about
9,950 tokens at 22.5 per second. That is past the 8,192 tokens the request reserved for
reasoning and answer, and nothing enforced the reserve: the request set no cap on its
output, so the only bound was the window, and the fixed 600 s deadline cut the answer off
unfinished. The retry was the same request at temperature 0. It read for 147 s, wrote
10,017 tokens and was cut off the same way, 20.5 minutes after the first began. The same
log holds the failure this one had been taken for: on 2026-09-30 a review waited about
ten minutes behind another client's request and was then cut off seconds into its own
work, reported in the same words. Two causes shared one code.

#1316, merged on 2026-10-01, separates them and bounds both. The reserve is now sent as
the request's `num_predict`, so the model may write no more than the room the request was
sized with, and the default reserve is 16,384 tokens, above the 11,832 that the longest
review in the log to finish generated. A model that fills the reserve without finishing
is refused as `done_reason=length` and named as such, never as a timeout. A request's
deadline grows with what it sends and what it may write,
$t = \max(t_0,\; p/r_p + R/r_o)$, for $p$ prompt tokens, reserve $R$, the fixed
$t_0 = 600$ s, and declared rates $r_p = 200$ and $r_o = 20$ tokens per second, rounded
down from the 237 to 319 and 22.3 to 22.6 measured in that log. Before each request a
one-token probe at the same window waits up to 900 s for the model's one slot. A model
still busy then is coded `model_busy` and retried; a request that started on a free slot
and still ran past its deadline is coded `model_timeout`, its reason states the
deadline's arithmetic, and it is not retried, because at temperature 0 the same request
would run the same way. With these defaults #1316 re-planned #1312's diff into two parts
of about 49,000 and 45,000 estimated tokens, with deadlines of 1,065 s and 1,044 s. That
is a plan, not a run. By our cutoff, 20:41Z on 2026-10-01, the lane had run twice under
the new code. It reviewed #1319, a generated forecast refresh of 73 changed lines, in one
request and passed it (run 36911659643). Then it reviewed #1317, 2,573 changed lines in
14 files, in three parts, one attempt each, and reached no verdict (run 36916689987):
the third part's model wrote 78,418 characters of reasoning and no answer, filled the
16,384-token reserve, and was refused as `done_reason=length`, coded
`answer_incomplete`, 39.5 minutes after the review began, and the gate asked for a
person. #1317 had been merged at 19:53Z, before that review started. So on the one large
diff it has met, the repair did what it promised, a bounded attempt and a refusal that
names its cause instead of two timeouts, and not what it was for: no large diff has yet
reached a sovereign verdict under it, and on that one the reserve was not room enough.
Whether a larger reserve, less reasoning or smaller parts would let one finish is not
known; #1316 calls the reasoning setting a quality decision that needs its own study.

**The lane's record since.** We read every pull-request review run the forge recorded
from #1316's merge, at 18:16Z on 2026-10-01, whose sovereign job had finished by 03:50Z
on 2026-10-02. The lane gave seven verdicts, on #1319, #1322, #1324, #1326, #1327, #1329
and #1332, each reviewed in a single request, and blocked one of them (#1322). It gave
none on six. #1317 is above, and #1335's third part of five ended the same way, out of
room after 68,224 characters of reasoning (run 36956973134). #1321, reviewed in one request, wrote 69,015 characters of
reasoning and no answer and was refused as `done_reason=length` (run 36924458568). Two
were refused before anything was sent: #1323 because one hunk of a generated coverage
file was larger than a part may carry, and a hunk is never cut (run 36926257830), and
#1328 because its diff of 247,237 characters needed seven parts where `max_chunks` allows
six (run 36935786057). The second of #1334's four parts, about 49,133 prompt tokens, did
not finish within its deadline of 1,065 s and was named as too slow for its input, with
the deadline's arithmetic (run 36956577348); #1334 had been merged at 02:40Z, half an hour
before that review ended. So under #1316 no diff that needed more than one request has
reached a sovereign verdict. Before it, one had: the lane passed #1307, an earlier
revision of this paper, in four parts at 14:49Z on 2026-10-01 (run 36876571436), under the
fixed 600 s deadline. That is one verdict, not a rate, and a pass on a documentation
change says little about recall. #1334's timeout has the shape the study below
anticipated: from the model server's log of past reviews, its evidence track estimated
that #1316's deadline barely covers a request that writes its full reserve once the
prompt passes about 40,000 tokens (`research/large-diff-review/experiments/LOG.md`).

**Recall, measured offline.** Until 2026-10-01 nothing had measured the reviewer's
recall: every study above measured agreement on pull requests that carried no known
defect. `vibey-gh review-canary` (#1325) measures it on a fixed corpus pinned at
`2b17eb7` (`docs/architecture/evidence/review-canary/corpus.toml`): 41 small single-file
diffs against this repository's own code, 27 of them planted defects, three in each of
nine classes (off by one, inverted condition, swallowed exception, missing `await`, SQL
built by string formatting, removed guard, resource leak, wrong return on the error path,
and a race on shared state), and 14 controls, two of them the correct forms of defect
cases. Every case goes through the production entry point with exactly the arguments the
review workflow passes. A defect counts as caught only when the verdict blocks, a finding
names the planted file and either its lines or one of its anchors, and the finding uses
one of the class's words; a control that is blocked or draws a blocking finding is a
false positive; a review with no verdict is counted apart and never either way. The first
measurement (#1331) ran on the operator's machine from about 16:26 to 19:12 EDT on
2026-10-01, at the production settings. It caught 18 of the 25 defects that drew a
verdict (Wilson 95% interval 0.524 to 0.857), blocked none of the 14 controls (0 to
0.215), and gave no verdict on 2 of the 41 cases, both timeouts at about 1,000 s. It is
one run on one host at temperature 0, not repeated, and its corpus is small diffs, not
large ones. It is the first digest-chained line in
`docs/architecture/evidence/review-canary/ledger.jsonl`, rendered into the runbook
`docs/runbooks/sovereign-review-runner.md`, and it meets the floor declared for it, a
recall lower bound of at least 0.5 and a false-positive upper bound of at most 0.5. That
floor is low on purpose: it asks only for 95% confidence that the review blocks more than
half the planted defects for the right reason. Two things the numbers do not say on their own.
The matching rule under-counts: by hand, two of the seven misses are real catches that
used none of the class's words or quoted neither line nor anchor, so recall by hand is 20
of 25, and the floor reads the strict figure. And the other five defects passed with no
findings at all; in two of them the reviewer's own summary named the defect, one as
"introducing a potential SQL injection vulnerability", while `pass` was true. The gate
reads `pass`, so those two would have merged.

The weekly workflow repeated the measurement on 2026-10-02 (run 37002135164), on the
self-hosted runner at `3bb577a4e`, over the same corpus and settings. It caught 23 of the
27 defects (Wilson 95% interval 0.675 to 0.941), every case drew a verdict, it blocked
none of the 14 controls, and it met the floor; its misses are not adjudicated by hand. The
two runs differ in their commit and in where the review's client ran, directly on the operator's machine for the first and in the self-hosted
runner's container for the second, so the second repeats the
procedure, not the first run's conditions, and we do not read the difference as an
improvement. The result almost went unrecorded. The workflow handed the ledger to its
publishing job as an artifact, which drops the directory its paths share, so the file
landed beside the tracked ledger, every later check read the unchanged one, and the job
reported the ledger unchanged and succeeded. The weekly minimum-requirements run lost its
macOS figures the same way. Both results were recovered from the retained artifacts (#1361,
#1365); the handover now lands where it is committed from, a fresh measurement that
changes nothing fails, and a test holds every workflow's downloads to their uploads' root
(#1360).

**The large-diff study, in progress: mechanism and screening only.** Why the lane gives
no verdict on a large diff, and what would let it, is the subject of a study that is in
progress, and what follows is its mechanism and its screening, not its result. Its plan
was registered before any data: `research/large-diff-review/experiments/PREREGISTRATION.md`,
committed at 17:57 EDT on 2026-10-01 on the study's branch, before the first experimental
request. Its population is the 45 diffs merged into `develop` from 2026-09-25 to
2026-10-01 that production cannot review in one request, split by seed into 22 for
development and 23 held out. Its arms are production (A0); production with its reasoning
cut at 4,096 tokens and a verdict then forced (A1); production sampled at temperature 1.0
and top-p 1.0 with seed 42, the model's own default (A2); and decoupled arms (D4, D8, D16,
D32) that review parts of at most that many thousand diff tokens, without the declared
documents, plus one request that judges the documentation contract from a digest. A
method *works* only if it reaches a verdict on at least 95% of 48 held-out confirmation
cases, the lower bound of the paired 95% interval of its recall minus production's, on
the canary's 27 defects, is above minus 0.15, and the upper bound of the interval of its
false-positive rate minus production's, on the 14 controls, is below 0.15. As the plan requires,
every change to it since is logged with its time and reason in `experiments/LOG.md`,
among them arms added before any of their outcomes was seen. Two
sibling tracks, on prior art and on the server log's record of past reviews, fed the plan
before the first request. Their write-ups are now in the committed tree
(`research/large-diff-review/prior-art/` and `research/large-diff-review/evidence/`, each
with its own cutoff in its header); the evidence track's raw logs, about 28 MB, stay on the
host, and only their SHA-256 manifest is tracked. The study shares the one model slot with
live reviews and yields to them, and that is a threat to its timings it found and closed
(#1341). The self-hosted runner's live reviews run inside Docker, so the harness's process
check could not see them: a review from the runner began seconds after an idle check, and
two of the study's requests, parts 4 and 5 of one arm on #1131, queued behind it for 638 s
and 1,063 s, the second until its own deadline. The harness now refuses to start while any
other client is connected to the model's port and yields its own request to one forwarded
from Docker, and an audit (`experiments/harness/contention.py`) matches every record to the
server's access log and voids any that began while another client's request was still
running. Its first pass voided exactly those two (`experiments/data/invalidations.jsonl`),
the records stay in the append-only store, and the arm was run again. Nothing has been
voided since the fix, made at 23:20 EDT on 2026-10-01: the voids file still holds only those
two, and the log's latest audit, at 05:59 EDT on 2026-10-02, found no request contended. No result we cite here comes
from a voided record. Since 3.3.0 the harness also pins what it calls production: an arm
that stands for production refuses to build a request unless the review settings it reads
at run time equal the ones the study registered (`experiments/corpus/hosts.json`).

At the end of Stage 1, which the study's log records at 11:10 EDT on 2026-10-02 and which
reached `develop` in #1362 and #1364, its committed record (`experiments/LOG.md`,
`experiments/data/`) shows the following. Stage 1 screens on four
host diffs, #1131, #1161, #1250 and #1282 (163,508 to 224,986 characters), and stops an arm
at its first diff with no verdict, so every Stage 1 result is screening-grade, not a rate.

- **Stage 0, on a toy diff and no corpus case.** The model's harmony prompt template was rendered exactly (687 prompt tokens by either route). A cut-off reasoning can be continued into a forced verdict through `/api/chat` with the response schema kept, and the schema still constrains the answer. Because the server reuses the cached prompt and reasoning, the forced phase is cheap: on the four parts of #1131 that D16 forced, it took 3.7 to 5.0 s in all. The same request sent twice at temperature 0 gave byte-identical reasoning and answer (`experiments/data/stage0.json`).
- **The loop.** The first part of #1131 cut to at most 8,000 diff tokens (13,894 prompt tokens) ran at temperature 0 to the 16,384-token cap with no answer, in 697 s. Of its reasoning's word 8-grams, 86% were repeats, and its tail repeats one sentence verbatim. The same part at temperature 1.0, top-p 1.0 and seed 42 answered in 368 tokens and 39 s. Production sends temperature 0 (`src/vibey_tools/gh/vibey_gh/local_review.py`). Every arm at temperature 0, production (A0) and D4, D8, D16 and D32, gave no verdict on #1131 and was dropped there.
- **Two more ways to give no verdict.** Sampling ends the loop, but it does not guarantee an answer. D4 at temperature 1.0, run again after the void, answered eight parts of #1131 and then, on the ninth (6,576 prompt tokens), stopped of its own accord with an answer that escaped the response grammar: the check codes as bare text, then JSON with keys the schema does not have. Constrained decoding is not a guarantee on this path. On #1282, the fourth host, D8 at temperature 1.0 answered six parts and on the seventh stopped after 921 tokens with 3,834 characters of reasoning and an empty answer: the model closed its turn in the reasoning channel and never opened the answer. D16 at temperature 1.0 answered four parts of #1282 and on the fifth (5,949 prompt tokens) stopped with 163 characters that began with the check codes as bare text, which the JSON parser refuses as extra data. Each of the three is an `answer_incomplete` production's own validation refuses, and each dropped its arm. So every unforced temperature-1.0 arm that reached all four hosts failed on #1282, the two of them by two different mechanisms.
- **Forcing.** The arms that bound the reasoning and then force a verdict, through the prefill with the grammar kept, are built to repair all three mechanisms: a loop is cut at the bound, and since an amendment logged before any outcome under it, an empty or ungrammatical answer that ends of its own accord is forced again from the same reasoning. In Stage 1's record, 31 forced requests followed a cut at the bound and one followed an ungrammatical answer that ended of its own accord, and all 32 came back complete. That one is the nearest the screening comes to a contrast: on #1282's fifth part, D16 at temperature 1.0 forced at 8,192 tokens first answered with the check codes as bare text, the failure on which the same arm unforced was dropped, and its forced answer came back in 3.2 s. It is one case. No forcing arm has met an empty answer, so the repair of that mechanism is by construction, not yet observed. D16 with the reasoning bounded at 4,096 tokens forced 17 of its 19 parts and 1 of its 4 contract requests, and took 19.4 to 24.0 minutes a host, a median of 20.2.
- **The end of screening.** On #1282, production forced at 4,096 tokens (A1), production at temperature 1.0 (A2), D16 at temperature 1.0 forced at 8,192 tokens, and D32 at temperature 1.0 each gave a verdict, so with D16 forced at 4,096 tokens five arms answered on all four hosts, at medians of 18.1 to 20.2 minutes a host and at most 26.9, against the 120 minutes the plan allows. Four of four bounds an arm's rate of answering from below only at 0.51 (Wilson 95%), so the screening prunes and does not certify. None of the verdicts' findings has been adjudicated, so a verdict here is an answer, not a correct one.
- **Why `pass` can contradict the summary.** In production's response schema `pass` comes before `findings`, and the track's explanation is that constrained decoding writes the fields in that order, so the model commits to `pass` before it writes a finding. A rule that lets the findings decide `pass` recovers none of the canary's inconsistent verdicts, because those verdicts carry no findings at all: scored on the canary's own verdicts, at no model cost, by a scorer that reproduces the canary's 18 of 25 and 0 of 14 exactly, the rule leaves both figures unchanged. An arm that writes the findings first was added for Stage 2 before any of its outcomes was seen.
- **Static analysis alone.** Ruff with every rule selected, and bandit, with no model, flag 5 of the canary's 27 defects, all three of the SQL cases and two of the three swallowed exceptions, and none of its 14 controls (`experiments/data/static_only.json`).

The evidence track's estimates, as the log records them, set the order in which Stage 1
ran its arms: from the server log's past reviews, a request finishes within 16,384 output
tokens with probability 0.92 at 20,000 prompt tokens, 0.73 at 30,000, 0.53 at 40,000 and
0.36 at 50,000, partly extrapolated below 20,000, where only six past requests fell, and
reasoning length depends on what a part contains as well as on its size. Not yet
measured: the recall or the false-positive rate of any arm, which is Stage 2's; the replays
of #1312 and #1317; and anything on the held-out
diffs or needles. At Stage 1's end the request store held 198 requests and 10.13
model-hours, and the audit had voided none since the two above. The screening points to a
fix, a bound on the reasoning with a forced verdict, the one remedy seen to repair a failed
answer: it is identified, but neither confirmed nor shipped. Stage 2 began in the order the
log fixed before any of its outcomes, and we report none of its figures, because a round
that has not finished is not a rate. Production is unchanged: it still reviews at temperature 0 with the parts and
reserve #1316 set, and a change will ship in a later release only once the study confirms
it on the held-out diffs; 3.4.0 carries none. If a method is chosen, the operator has asked
that its calibration ship with it, reproducible, repeated monthly and reported by
`vibey doctor`.

```latex
\begin{plainwords}
A pull request changes over time, like a homework draft that gets rewritten. A grade belongs to one draft only. Vibey never uses a grade from an old draft to decide about a new one. It counts repairs, not reviews, so the helpers cannot keep repairing forever; after two automatic second chances, where a project switches them on (this one does not), a change that still fails waits for a person. A grade from the small local grader alone never triggers a repair: the change is simply graded again, and the paper admits that nothing yet stops that from repeating. And the key that grades a change is never the key that merges it, so no single stolen grading key can ship a change. A grade must also be about the whole draft the grader actually read. A small computer running the grader can quietly read only half of a long draft and still hand back a confident grade, so every request now tells it to refuse instead, and hides a secret word at the start and at the end that the grader must repeat back. If either word is missing, the grade is thrown away. Our first guess at why one grade failed was wrong, and we say so: that time the grader had read everything and simply ran out of room to answer. Later, long drafts kept coming back with no grade at all, and we found why: nothing stopped the grader from writing on and on until the clock ran out. Now it gets a fixed amount of room, more time for a longer draft, and a different message when it was only waiting its turn. The first long draft it met after the change still came back without a grade, but this time with the honest reason: the grader used all its room thinking and never answered. Since then no long draft has come back with a grade under the new rules. We also tested the grader on short drafts with mistakes planted in them on purpose. It caught 18 of the 25 it graded and never failed a good draft, but twice it wrote down the mistake and still gave a pass. Why it gets stuck on long drafts is being studied now, with the plan written down before the first test. On one long draft it went round in circles when told always to pick its most likely next word, and finished quickly when allowed a little chance. But on a fourth long draft, a little chance was not enough: once it stopped without writing any answer, and once it wrote its answer in the wrong shape. Only the version that is told ``stop thinking now and answer'' after a fixed amount of thinking has answered on all four. These are clues from four drafts, not a result: nobody has yet checked whether its answers are right, and the grader has not been changed. Each release now also carries ready-to-install copies of the apps, with a list of fingerprints to check them by. Version 3.3.0 did it for real for the first time, eleven files, and every fingerprint and every certificate of origin checked out. The next version adds a Mac app and an iPhone app; the iPhone app has to go through Apple's own store to reach a phone.
\end{plainwords}
```

## Deterministic retrieval and fail-closed bootstrap

Two further components apply the ledger's discipline, append before acting and fail
closed rather than degrade silently, at other scales.

**Retrieval.** A skill library cannot be loaded wholesale into a context window, yet
fragmentary retrieval of safety- and correctness-critical guidance is worse than none.
At the current source cutoff the library holds 745 skill documents across 138 plugins.
`vibey-skills` indexes it as a pure function of the corpus and retrieves only whole
sections.

```latex
\begin{invariant}[Deterministic, whole, fail-closed retrieval]
The index is a pure function of the corpus: identical corpus bytes yield identical
manifests, chunk identifiers and scores. The retrieval unit is a heading-bounded
section, returned whole with its path, line range and content hash. For a request
with mandatory content $M$ and budget $B$, if $\mathrm{tokens}(M) > B$ assembly returns
\texttt{budget\_insufficient} and never truncates a mandatory section to fit.
\end{invariant}
```

Omitted optional content is recorded in the packet's manifest, and a `low_confidence`
flag directs the caller back to native full-skill activation, so degradation is
explicit and machine-readable. Full-text queries are parameterised, symlinked sources
fail closed, and credential-shaped strings are redacted from packets. Retrieval
metrics are diagnostics, not the objective: the deployment criterion is cost per
accepted work item, since a packet that halves token spend but raises rework is a
regression.

**Bootstrap.** `vibey-bootstrap` collapses a cloud workload's first hundred lines
(logging, configuration, secrets, telemetry) into one call under one rule: absence of
a required precondition halts the start with that precondition named, and an optional
capability degrades explicitly, as a recorded decision, never as a silent absence.
Above it sit delivery and audit primitives with stated guarantees. A transactional
outbox writes intent beside the state change, so every committed intent is delivered
at least once and marked delivered exactly once. Audit records form a hash chain,
$c_0 = H(r_0)$ and $c_i = H(c_{i-1} \| r_i)$, so any edit, insertion or truncation
breaks every later link and verification needs no trust in the writer. Retries are
built in one place, with typed retryable errors, exponential bounds, and rate-limit
callbacks that can never mask the original error.

The ledger, the outbox and the audit chain are one principle at three scales: the
record of intent exists before its effect, and every later state is derived from the
record, as diagrammed in [Fig. 17](#fig:record-effect).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  box/.style={minimum height=.95cm},
  wideb/.style={box,text width=4.3cm},
  midb/.style={box,text width=4.0cm},
  lbl/.style={vibeynote,font=\sffamily\scriptsize,inner sep=1.5pt},
  crash/.style={lbl,text=vibeyred}]
  % ---- column headers
  \node[vibeyhead,anchor=south] (hA) at (2.95,6.95)  {Intent recorded};
  \node[vibeyhead,anchor=south] (hB) at (8.8,6.95)   {State derived};
  \node[vibeyhead,anchor=south] (hC) at (14.65,6.95) {Effect allowed};
  % ---- lane 1: orchestrator scale (the delivery ledger)
  \node[vibeycore,wideb] (a1) at (2.95,5.85)  {Ledger event appended\\append-only; corrections supersede};
  \node[vibeysoft,midb]  (b1) at (8.8,5.85)   {State projected\\\mbox{$\mathrm{state}(t)=f(\mathrm{ledger}_{\le t})$}};
  \node[vibeygood,wideb] (c1) at (14.65,5.85) {Job proceeds\\lease, phase, commit, human gate row};
  % ---- lane 2: service scale (the transactional outbox)
  \node[vibeycore,wideb] (a2) at (2.95,4.0)   {Outbox row and state change\\committed in one transaction};
  \node[vibeysoft,midb]  (b2) at (8.8,4.0)    {Dispatcher reads\\committed rows only};
  \node[vibeygood,wideb] (c2) at (14.65,4.0)  {External call made\\at-least-once; marked delivered once};
  % ---- lane 3: audit scale (the hash chain)
  \node[vibeycore,wideb] (a3) at (2.95,2.15)  {Chain link appended\\\mbox{$c_i = H(c_{i-1}\,\|\,r_i)$}};
  \node[vibeysoft,midb]  (b3) at (8.8,2.15)   {Verifier re-hashes\\from \mbox{$c_0 = H(r_0)$}};
  \node[vibeygood,wideb] (c3) at (14.65,2.15) {Edits detected\\any change breaks every later link};
  % ---- bootstrap layer underneath
  \node[vibeybox,wideb] (s1) at (2.95,0.3)  {Fail-closed start\\missing precondition halts, named};
  \node[vibeybox,midb]  (s2) at (8.8,0.3)   {Optional capability\\degrades as a recorded decision};
  \node[vibeybox,wideb] (s3) at (14.65,0.3) {Retries built once\\typed, bounded, cause never masked};
  % ---- lanes on the background layer
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(0.25,5.35)(17.35,6.55)}] (lane1) {};
    \node[vibeylane,fit={(0.25,3.5)(17.35,4.7)}]   (lane2) {};
    \node[vibeylane,fit={(0.25,1.65)(17.35,2.85)}] (lane3) {};
    \node[vibeylane,fit={(0.25,0.0)(17.35,1.0)}]   (lane4) {};
  \end{scope}
  \node[vibeylanelabel] at (lane1.north west) {Orchestrator scale};
  \node[vibeylanelabel] at (lane2.north west) {Service scale};
  \node[vibeylanelabel] at (lane3.north west) {Audit scale};
  \node[vibeylanelabel] at (lane4.north west) {Bootstrap layer};
  % ---- the durability boundary: everything right of it happens after the record is on disk
  \draw[vibeydashed] (6.0,1.4) -- (6.0,6.95);
  \node[vibeypill,anchor=south] at (6.0,6.95) {durable from here};
  % ---- record -> derive -> effect, in every lane
  \foreach \r in {1,2,3}{
    \draw[vibeyflow] (a\r) -- (b\r);
    \draw[vibeyflow] (b\r) -- (c\r);
  }
  % ---- crash anywhere: back to the record
  \draw[vibeyback,rounded corners=3pt] (hC.north) |- (8.8,7.58) -| (hA.north);
  \node[crash,anchor=south] at (8.8,7.62) {crash at any step: replay from the record; duplicates dropped by identity};
\end{tikzpicture}
\caption{Append before act, at three scales. Each row is one part of vibey (the ledger, the outbox, the audit chain) and reads the same way: the intent is saved, the state is derived from that record, and only then may the effect happen. A crashed worker restarts from the record. The bootstrap layer below keeps the same rule at start-up.}
\label{fig:record-effect}
\end{figure*}
```

```latex
\begin{plainwords}
Two smaller tools follow the same rule of writing things down before acting. One looks up instructions in a big library and always returns whole pages, never half a page, and it says clearly when it could not fit everything in. The other starts up cloud programs and refuses to start at all if something it needs is missing, instead of limping along quietly.
\end{plainwords}
```

## Production rate and governance

The components above make engines substitutable and human decisions explicit. This
section asks what, given that, bounds the rate of delivery. Its tracked sources are the
sovereignty stress record
(`src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md`), the cutoff-bounded local
Qwen storm record
(`src/vibey_tools/gh/docs/qwenloop-storm-2026-09-20.json`), the QwenStorm 3.0.0
evidence ledger and host benchmark under `docs/plans/qwenstorm-3.0.0/`, the
delivery-estimate ledger, the slot-calibration and minimum-requirements records under
`docs/architecture/evidence/`, and this repository's git history, which is field data. The
stress record is a controlled escalation of the local review lane; the Qwen record is an
operational reliability observation, not another throughput experiment.
`scripts/paper_evidence.py` recomputes the stress, Qwen and history figures, and
`scripts/paper_figures.py` redraws every computed figure from the tracked records;
history figures are stated at the paper's pinned source revision, `d4c4e1f8`, which
`scripts/paper_figures.py --rev <pin>` reproduces. The 3.2.0 promotion has since
rewritten `develop`, so the pin is no longer on its history (its tree is that of
`785e708e`); the tag `paper-figures/3.2.0` holds it and keeps it walkable; the previous pin, `c78049b6`, stays walkable through the tag
`paper-figures/3.0.0`. Two further sources are not
tracked, and we name them where we use them:
the storm throughput audit of 2026-09-23, whose record is a page kept outside the
repository and whose inputs are local run logs, and the forge's own records of pull
requests and their merge times. Where we could recompute an audit figure from the local
logs we did, on 2026-09-24, and say so.

### The stress record

A harness fired $N$ simultaneous generations at `qwen2.5-coder:14b`, served by ollama
on one machine with 24 GB of memory and 10 cores, for $N$ from 1 to 128, with a 900 s
deadline per generation. Each generation was a real unit of work, an issue triaged or
a pull-request diff reviewed, drawn from a pool of seven artifacts of 2 to 22 KB.
Throughput is successful generations per minute of rung wall clock, reported across four views in [Fig. 18](#fig:stress-rate).

<!-- BEGIN GENERATED figure:stress-dashboard rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 2,horizontal sep=1.7cm,vertical sep=1.75cm},
  vibeyaxis,width=7.9cm,height=4.3cm,xmode=log,log basis x=2,xtick={1,2,4,8,16,32,64,128},xticklabels={1,2,4,8,16,32,64,128},
  xmin=0.8,xmax=160,xlabel={offered concurrency $N$}]
\nextgroupplot[title={a. Successful throughput},ylabel={generations / min},ymin=0,ymax=4.6,ytick={0,...,4}]
\fill[vibeyblue!9] (axis cs:2,0) rectangle (axis cs:32,4.6);
\node[vibeynote,text=vibeyblue,anchor=south] at (axis cs:8,3.55) {stable region $N=2$--$32$};
\draw[vibeydashed] (axis cs:0.8,0.99) -- (axis cs:160,0.99) node[vibeynote,anchor=west,text=vibeygray] {0.99};
\draw[vibeydashed] (axis cs:0.8,2.0) -- (axis cs:160,2.0) node[vibeynote,anchor=west,text=vibeygray] {2.00};
\addplot[vibeyblue,line width=1pt,mark=*,mark size=1.4pt,mark options={fill=white,line width=.7pt}] coordinates {(1,0.36) (2,0.99) (3,0.99) (4,1.17) (6,1.72) (8,1.27) (12,1.54) (16,1.37) (24,1.4) (32,2.0) (48,1.6) (64,2.66) (96,3.52) (128,1.53)};
\node[vibeycallout,anchor=south east] at (axis cs:96,3.52) {peak 3.52/min\\55.2\% success};
\node[vibeycallout,anchor=east,xshift=-3pt] at (axis cs:128,1.53) {collapse};
\nextgroupplot[title={b. Success fraction},ylabel={succeeded (\%)},ymin=0,ymax=124,ytick={0,25,50,75,100}]
\draw[vibeydashed] (axis cs:0.8,87.5) -- (axis cs:160,87.5) node[vibeynote,anchor=west,text=vibeygray] {87.5};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeygreen!80] coordinates {(1,100.0) (2,100.0) (3,100.0) (4,100.0) (6,100.0) (8,100.0) (12,100.0) (16,100.0)};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeygold!90] coordinates {(24,87.5) (32,93.8)};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeyred!75] coordinates {(48,50.0) (64,62.5) (96,55.2) (128,18.0)};
\node[vibeynote,anchor=north west,align=left] at (axis cs:0.9,122) {\textcolor{vibeygreen}{$\blacksquare$} 100\% \quad \textcolor{vibeygold}{$\blacksquare$} 87.5--93.8\% \quad \textcolor{vibeyred}{$\blacksquare$} overloaded};
\nextgroupplot[title={c. Latency against the 900\,s deadline},ylabel={seconds},ymin=0,ymax=1000,
  legend style={at={(axis cs:0.9,800)},anchor=north west}]
\addplot[fill=vibeyblue!12,draw=none,forget plot] coordinates {(1,166.0) (2,118.0) (3,132.0) (4,154.0) (6,59.0) (8,191.0) (12,174.0) (16,440.0) (24,701.0) (32,292.0) (48,900.0) (64,555.0) (96,821.0) (128,901.0) (128,901.0) (96,901.0) (64,901.0) (48,901.0) (32,900.0) (24,900.0) (16,700.0) (12,464.0) (8,375.0) (6,206.0) (4,203.0) (3,180.0) (2,118.0) (1,166.0)} -- cycle;
\draw[vibeyred,densely dashed,line width=.7pt] (axis cs:0.8,900) -- (axis cs:160,900) node[vibeycallout,anchor=south east] {deadline};
\addplot[vibeyblue,line width=1pt,mark=*,mark size=1.2pt] coordinates {(1,166.0) (2,118.0) (3,132.0) (4,154.0) (6,59.0) (8,191.0) (12,174.0) (16,440.0) (24,701.0) (32,292.0) (48,900.0) (64,555.0) (96,821.0) (128,901.0)};
\addlegendentry{p50}
\addplot[vibeyteal,line width=.8pt,mark=square*,mark size=1.1pt] coordinates {(1,166.0) (2,118.0) (3,180.0) (4,203.0) (6,206.0) (8,375.0) (12,464.0) (16,700.0) (24,900.0) (32,900.0) (48,901.0) (64,901.0) (96,901.0) (128,901.0)};
\addlegendentry{max}
\nextgroupplot[title={d. Free memory during the rung},ylabel={free memory (\%)},ymin=0,ymax=14]
\addplot[vibeyviolet,line width=1pt,mark=*,mark size=1.2pt,mark options={fill=white}] coordinates {(1,11.6) (2,11.2) (3,9.3) (4,9.4) (6,11.1) (8,10.3) (12,9.4) (16,8.6) (24,8.8) (32,9.3) (48,8.9) (64,10.0) (96,9.7) (128,9.1)};
\node[vibeycallout,anchor=south east,align=right] at (axis cs:140,12.1) {paging space 99.1\%\\at $N=128$};
\node[vibeynote,anchor=south west,align=left] at (axis cs:1,0.5) {server crashed and self-restarted\\at $N=64$ and $N=128$};
\end{groupplot}
\end{tikzpicture}
\caption{The sovereignty stress record in four views. (a) Successful throughput rises into a broad stable band, 0.99--2.00 generations per minute, across offered concurrency $N=2$ to $32$, then peaks at 3.52 per minute at $N=96$ before collapsing. (b) The success fraction stays at or above 87.5\% through $N=32$ and falls beyond it. (c) Median latency and the slowest generation of each rung approach the 900\,s deadline as the substrate saturates. (d) Free memory oscillated in a narrow band throughout; paging space, not free memory, marked the collapse. Every point reproduces the record's rung table.}
\label{fig:stress-rate}
\end{figure*}
```
<!-- END GENERATED figure:stress-dashboard -->

| $N$ | Succeeded | p50 (s) | Per minute |
|---:|---:|---:|---:|
| 1 | 1/1 | 166 | 0.36 |
| 2 | 2/2 | 118 | 0.99 |
| 3 | 3/3 | 132 | 0.99 |
| 4 | 4/4 | 154 | 1.17 |
| 6 | 6/6 | 59 | 1.72 |
| 8 | 8/8 | 191 | 1.27 |
| 12 | 12/12 | 174 | 1.54 |
| 16 | 16/16 | 440 | 1.37 |
| 24 | 21/24 | 701 | 1.40 |
| 32 | 30/32 | 292 | 2.00 |
| 48 | 24/48 | 900 | 1.60 |
| 64 | 40/64 | 555 | 2.66 |
| 96 | 53/96 | 821 | 3.52 |
| 128 | 23/128 | 901 | 1.53 |

In all, 243 of 444 generations succeeded over 2.18 hours. Every failure was a clean
timeout; not one response was malformed or corrupt. The cumulative progression of attempts
and successes across the 14 rungs is plotted in [Fig. 19](#fig:stress-cumulative).

<!-- BEGIN GENERATED figure:stress-cumulative rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=8.6cm,height=5cm,xmin=1,xmax=14,ymin=0,ymax=474,
  xtick={1,2,3,4,5,6,7,8,9,10,11,12,13,14},xticklabels={1,2,3,4,6,8,12,16,24,32,48,64,96,128},
  xlabel={rung (offered concurrency $N$)},ylabel={generations, cumulative},legend pos=north west]
\addplot[fill=vibeysilver!35,draw=none,forget plot] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,76) (10,108) (11,156) (12,220) (13,316) (14,444)} \closedcycle;
\addplot[fill=vibeygreen!45,draw=none,forget plot] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,73) (10,103) (11,127) (12,167) (13,220) (14,243)} \closedcycle;
\addplot[vibeysilver,line width=.5pt] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,76) (10,108) (11,156) (12,220) (13,316) (14,444)};
\addlegendentry{attempted}
\addplot[vibeygreen,line width=.8pt] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,73) (10,103) (11,127) (12,167) (13,220) (14,243)};
\addlegendentry{succeeded}
\node[vibeynote,anchor=east,align=right] at (axis cs:12.4,346) {243 of 444\\54.7\% overall};
\end{axis}
\end{tikzpicture}
\caption{Cumulative generations across the fourteen rungs of the stress record: 444 attempted, 243 succeeded. The gap opens only after the stable region; every failure in the run was a clean timeout, never a malformed response.}
\label{fig:stress-cumulative}
\end{figure}
```
<!-- END GENERATED figure:stress-cumulative -->

### The local Qwen storm pilot

A local storm on the evening of 2026-09-20 exercised the then-latest qwenloop runner against the open Vibey
backlog with `qwen3:14b` through Ollama. It is not a replication of the stress record:
the work items were heterogeneous, the offered concurrency was not controlled as a
factorial experiment, and several runs were still alive or had produced no events at
the evidence cutoff. The tracked record names every allocated run directory and the
cutoff (`2026-09-21T00:19:23-04:00`).

Thirteen run directories were observed. Four completed with both a verdict and the
`QWENLOOP_TASK_FULLY_COMPLETE` marker: the first after five turns and four tool calls,
the second after nine turns and twelve tool calls, including six writes totalling
2,431 bytes, and a later run after six turns and five tool calls with one write
totalling 1,924 bytes; the latest completed after 22 turns and 20 tool calls, with
nine writes totalling 6,717 bytes. Two more emitted provisional verdicts without the
completion marker: one made eight file-write calls totalling 7,430 bytes over eleven turns and
thirteen tool calls, while the other reached nine turns and eight tool calls with two
file-write attempts that produced no successful bytes. One older run reached two turns
and two tool calls without a verdict. An earlier non-empty run exhausted its 40-turn
limit and ended with a `failed` terminal event without a verdict; it had made twenty
tool calls and sixteen writes totalling 13,571 bytes. Another produced one tool error
after one turn. Four directories, one of them freshly allocated at the cutoff, had no
events, while one storm process was still alive. Across all thirteen directories the logs contain 105 model-turn
boundaries, 85 tool calls, 550,576 input tokens, 83,609 output tokens, and 42
file-write calls totalling 32,073 bytes, as detailed across each run in [Fig. 20](#fig:qwen-runs).
Thus the accepted completion rate at the cutoff was 4/13, or 30.8%, while a verdict alone
would have suggested 6/13, or 46.2%.

<!-- BEGIN GENERATED figure:qwen-runs rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.8cm},vibeyaxis,width=8.6cm,height=4.6cm,
  xmin=0.3,xmax=13.7,xtick={1,2,3,4,5,6,7,8,9,10,11,12,13},xlabel={run, in order of start},x tick label style={yshift=-5pt}]
\nextgroupplot[title={a. Turns and tool calls per run},ylabel={count},ymin=0,ymax=48,legend pos=north west,ybar,bar width=4pt,legend image code/.code={\fill[#1,draw=none] (0cm,-2.2pt) rectangle (0.28cm,2.2pt);}]
\addplot[fill=vibeyblue,draw=none] coordinates {(1,11) (2,1) (3,0) (4,0) (5,0) (6,5) (7,9) (8,9) (9,2) (10,6) (11,40) (12,22) (13,0)};
\addlegendentry{model turns}
\addplot[fill=vibeyteal!80,draw=none] coordinates {(1,13) (2,1) (3,0) (4,0) (5,0) (6,4) (7,8) (8,12) (9,2) (10,5) (11,20) (12,20) (13,0)};
\addlegendentry{tool calls}
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:1,0) {};
\node[fill=vibeyred!60,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:2,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:3,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:4,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:5,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:6,0) {};
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:7,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:8,0) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:9,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:10,0) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:11,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:12,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:13,0) {};
\nextgroupplot[title={b. Tokens per run},ylabel={tokens (thousands)},ymin=0,ymax=286,legend pos=north west,ybar,bar width=4pt,legend image code/.code={\fill[#1,draw=none] (0cm,-2.2pt) rectangle (0.28cm,2.2pt);}]
\addplot[fill=vibeyviolet!85,draw=none] coordinates {(1,93.4) (2,1.3) (3,0.0) (4,0.0) (5,0.0) (6,23.4) (7,62.3) (8,17.1) (9,4.3) (10,8.6) (11,238.6) (12,101.6) (13,0.0)};
\addlegendentry{input}
\addplot[fill=vibeygold,draw=none] coordinates {(1,9.8) (2,0.4) (3,0.0) (4,0.0) (5,0.0) (6,4.1) (7,8.1) (8,7.5) (9,0.9) (10,5.7) (11,30.5) (12,16.5) (13,0.0)};
\addlegendentry{output}
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:1,0) {};
\node[fill=vibeyred!60,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:2,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:3,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:4,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:5,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:6,0) {};
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:7,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:8,0) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:9,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:10,0) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:11,0) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:12,0) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at ([yshift=-5pt]axis cs:13,0) {};
\end{groupplot}
\node[vibeynote,anchor=north west,align=left] at ([yshift=-2pt]current bounding box.south -| group c1r1.south west)
  {disposition strip: \textcolor{vibeygreen}{$\blacksquare$} completed (4) \;
   \textcolor{vibeygold}{$\blacksquare$} verdict only (2) \;
   \textcolor{vibeyred}{$\blacksquare$} no verdict (2) \;
   \textcolor{vibeyred!60}{$\blacksquare$} tool error (1) \;
   \textcolor{vibeysilver}{$\blacksquare$} no events (4)};
\end{tikzpicture}
\caption{The thirteen run directories of the cutoff-bounded local Qwen storm, in order of start. (a) Model turns and tool calls; (b) input and output tokens, 550,576 and 83,609 in all. The strip beneath each panel colours every run by its disposition at the cutoff: only 4 of 13 both emitted a verdict and wrote the completion marker, and the largest run, forty turns and 238,608 input tokens, ended without a verdict at all.}
\label{fig:qwen-runs}
\end{figure*}
```
<!-- END GENERATED figure:qwen-runs -->

This is a runner-reliability observation, not a model-quality or throughput estimate.
It is nevertheless an empirical check of the completion contract: a verdict without
the completion marker did not count as success, and unfinished event trails remained
unfinished rather than being promoted to completed work. The run also exposed a
configuration observation worth preserving: the requested context setting was 32,768
tokens, while the local server reported 40,960 at the cutoff. The paper therefore makes
no claim about a controlled context-window effect from this pilot. The raw logs remain
local operational artifacts; the compact tracked extraction is the reproducible source
used by `scripts/paper_evidence.py`. The resulting distribution of dispositions is
summarised in [Fig. 21](#fig:qwen-disposition).

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  seg/.style={inner sep=0pt,minimum height=.6cm,anchor=west,draw=white,line width=.6pt,
    font=\sffamily\scriptsize\bfseries,text=white},
  segname/.style={font=\sffamily\scriptsize,text=vibeyink,align=center,anchor=north,inner sep=1pt},
  bracelabel/.style={font=\sffamily\scriptsize,align=center,anchor=south,inner sep=1pt},
  brace/.style={draw=vibeygray,line width=.5pt,decorate,decoration={brace,amplitude=3pt}}]
  % ---- the thirteen run directories, one unit (0.5 cm) per run, in disposition order
  \node[seg,fill=vibeygreen,minimum width=2.0cm]                (done)    at (0,0)   {4};
  \node[seg,fill=vibeygold,minimum width=1.0cm]                 (verdict) at (2.0,0) {2};
  \node[seg,fill=vibeyred,minimum width=1.0cm]                  (noverd)  at (3.0,0) {2};
  \node[seg,fill=vibeyred!60,minimum width=.5cm]                (toolerr) at (4.0,0) {1};
  \node[seg,fill=vibeysilver,minimum width=2.0cm,text=vibeyink] (empty)   at (4.5,0) {4};

  % ---- disposition names, one per segment; the one-run segment gets a short leader
  \node[segname] at (done.south)    {completed};
  \node[segname] at (verdict.south) {verdict\\only};
  \node[segname] at (noverd.south)  {no\\verdict};
  \node[segname] at (empty.south)   {no events};
  \node[segname] (toolname) at ([yshift=-.85cm]toolerr.south) {tool error};
  \draw[vibeyedge] (toolerr.south) -- (toolname.north);

  % ---- the completion contract, read off the bar: delivered needs verdict AND marker
  \draw[brace] (0,.42) -- (1.94,.42);
  \draw[brace] (2.06,.42) -- (6.5,.42);
  \node[bracelabel,text=vibeygreen!80!black] (dlabel) at (1.0,.58)
    {\textbf{delivered: 4}\\verdict and marker};
  \node[bracelabel,text=vibeyink] (nlabel) at (4.28,.58)
    {\textbf{not delivered: 9}\\completion marker missing};

  % ---- the group of thirteen, named once
  \coordinate (lanehead) at (0,1.5);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(done)(empty)(toolname)(dlabel)(nlabel)(lanehead)] (lane) {};
    \node[vibeylanelabel] at (lane.north west) {13 run directories};
  \end{scope}

  % ---- the process still running at the cutoff: outside the thirteen, counts for nothing
  \node[vibeyghost,minimum width=1.25cm,anchor=west] (active) at (6.95,0) {+1 active\\process};
  \node[vibeynote,anchor=north] at ([yshift=-2pt]active.south) {still running,\\not one of the 13};
\end{tikzpicture}
\caption{The thirteen Qwen storm run directories at the evidence cutoff, each segment as wide as its share of runs. Only the four with both a verdict and a completion marker count as delivered; a verdict alone does not. One process was still running and belongs to none of the thirteen. Counting every visible artifact as finished would overstate delivery.}
\label{fig:qwen-disposition}
\end{figure}
```

### The QwenStorm 3.0.0 evidence ledger

The QwenStorm 3.0.0 run of 2026-09-22 and 2026-09-23 drove the open backlog through
one local model, `gpt-oss:20b` on Ollama, one lane at a time: each lane is one issue,
one source file with its interface and one test file, and every lane is reviewed
against its specification and its diff before it may become a pull request. Its record
is an append-only evidence ledger
(`docs/plans/qwenstorm-3.0.0/evidence/ledger.jsonl`) that a consumer,
`docs/plans/qwenstorm-3.0.0/tools/storm-evidence.py`, fills from the storm's own
progress log and lane results.

Each lane was allowed at most three attempts. Across the 30 lanes the ledger holds,
70 attempts and 2,606 model turns were logged ([Fig. 23](#fig:storm-lanes)). Seventeen
lanes ended in a completion claim, and a claim is not delivery: over the same span the
reviewer integrated 12 lanes and abandoned 14, but those lists reach beyond the ledger's
30. Of the 30, four were integrated (three of the seventeen that claimed completion, and
one that had failed all three attempts), twelve were abandoned, and fourteen, all of
them completion claims, remained unsettled at the cutoff. The figures below are the tool's own, regenerated between its markers; every
sentence about them is written outside those markers.

<!-- BEGIN GENERATED storm-evidence — regenerated by tools/storm-evidence.py -->

*Derived from `docs/plans/qwenstorm-3.0.0/evidence/ledger.jsonl`, an append-only record consumed under sub-doctrine 10.g.*
*Regenerated automatically; do not edit inside these markers.*
*This block states figures only — every claim about them is written by a person outside it.*

| quantity | value |
|---|---|
| ledger records | 277 |
| span consumed from | 2026-09-23T04:40:49Z |
| span consumed to | 2026-09-24T00:24:17Z |
| lanes observed | 30 |
| lanes claiming completion | 17 |
| lane starts / ends logged | 49 / 42 |
| lanes integrated / abandoned | 12 / 14 |
| recorded attempts | 70 |
| total turns across attempts | 2606 |

**Gaps in this span:** none; every byte and record between the watermarks was read.

<!-- END GENERATED storm-evidence -->

The consumer obeys sub-doctrine 10.g, the unbroken read
([Fig. 22](#fig:evidence-watermark)): its watermark is a byte offset into each source and
an identity set over the records, never a timestamp, because records that share the
cutoff second, arrive late or arrive out of order fall through a time comparison
silently. It appends to the ledger and flushes before it advances the watermark, so a
crash re-reads rather than skips, and duplicates are removed by identity. A source
shorter than its recorded offset is reported as a gap with the source named, never
repaired by resetting the offset to zero. The table above states that no gap occurred
in the consumed span.

That statement was proved on the storm's host, and a reader cannot re-prove it from a
checkout today. The repository tracks the ledger itself (277 records, no identity
repeated, the whole progress stream among them) but, beside it, only an early copy of
the progress log: 3,821 bytes and 47 lines, ending at 2026-09-22T22:35:21Z, where the
watermark records an offset of 15,087. Run from a checkout,
`storm-evidence.py --check` therefore reports that copy as shorter than its watermark,
exactly as the rule says it must, and we leave the block as the host generated it
rather than regenerate it from a file we know to be short. Recounting the ledger's own
records reproduces every row of the table; the lane-start count needed a correction to
the counter first, whose pattern had required a space after the issue number and so
skipped the storm's first start line, which ends there (49 starts, not 48).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % the accumulating record
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(0,0.2) (10.25,4.6)}] (source) {};
  \end{scope}
  \node[vibeylanelabel] at (source.north west) {an append-only source, read by position};
  \foreach \i/\x/\c in {0/0.45/vibeyblue!18, 1/1.65/vibeyblue!18, 2/2.85/vibeyblue!18, 3/4.05/vibeyblue!18, 4/5.25/vibeyblue!18, 5/6.45/vibeygold!35, 6/7.65/vibeygold!35, 7/8.85/white}
    {\draw[draw=vibeyblue!60,fill=\c,rounded corners=1.5pt,line width=.5pt] (\x,1.75) rectangle (\x+1.15,2.45);}
  \node[font=\sffamily\tiny,text=vibeyink] at (1.025,2.1) {rec 1};
  \node[font=\sffamily\tiny,text=vibeyink] at (2.225,2.1) {rec 2};
  \node[font=\sffamily\tiny,text=vibeyink] at (3.425,2.1) {rec 3};
  \node[font=\sffamily\tiny,text=vibeyink] at (4.625,2.1) {rec 4};
  \node[font=\sffamily\tiny,text=vibeyink] at (5.825,2.1) {rec 5};
  \node[font=\sffamily\tiny,text=vibeyink,align=center] at (7.025,2.1) {rec 6\\late};
  \node[font=\sffamily\tiny,text=vibeyink,align=center] at (8.225,2.1) {rec 7\\same tick};
  \node[font=\sffamily\tiny,text=vibeygray,align=center] at (9.425,2.1) {next\\write};
  \node[vibeynote,anchor=north] at (0.45,1.7) {offset 0};
  \node[vibeynote,anchor=north east] at (6.4,1.7) {offset 13,245};
  % the position watermark
  \draw[vibeyflow,-] (6.45,1.35) -- (6.45,3.15);
  \node[vibeytag,fill=vibeyblue,anchor=south] at (6.45,3.2) {watermark = byte offset};
  \node[vibeynote,text=vibeyblue,anchor=north,align=center] at (3.4,1.35) {everything before the offset\\is in the ledger, by identity};
  % the timestamp cutoff, which loses records
  \draw[vibeyback,-] (7.65,0.55) -- (7.65,2.75);
  \node[vibeycallout,anchor=west,align=left] at (7.75,1.0) {a timestamp cutoff drawn here\\would skip the late record and\\the one that shares its second};
  \node[vibeynote,anchor=west,align=left] at (0.35,3.95) {records arrive late, out of order, or in the cutoff's own second;\\a clock cannot tell which of them it has already seen};
  % the loop
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(10.7,0.2) (17.3,4.6)}] (loop) {};
  \end{scope}
  \node[vibeylanelabel] at (loop.north west) {order of operations, the whole guarantee};
  \node[vibeybox,minimum width=2.6cm] (s1) at (12.35,3.55) {1. read the watermark};
  \node[vibeybox,minimum width=2.6cm] (s2) at (15.65,3.55) {2. read from that offset};
  \node[vibeybox,minimum width=2.6cm] (s3) at (15.65,2.2) {3. append to the ledger\\and flush};
  \node[vibeycore,minimum width=2.6cm] (s4) at (12.35,2.2) {4. only then advance\\the watermark};
  \draw[vibeyarrow] (s1) -- (s2);
  \draw[vibeyarrow] (s2) -- (s3);
  \draw[vibeyarrow] (s3) -- (s4);
  \draw[vibeyarrow] (s4.north) -- (s1.south);
  \node[vibeygood,minimum width=6.0cm,font=\sffamily\tiny] at (14.0,0.95) {crash before step 4: read again, never skip; duplicates dropped by identity\\source shorter than its offset: a reported gap, the offset left unmoved};
\end{tikzpicture}
\caption{The unbroken read. A job that consumes a growing record remembers its place as a position in the data, not as a time on a clock, so late and out-of-order records are never skipped. It writes what it read into the ledger before moving its bookmark, so a crash means reading again, never losing anything.}
\label{fig:evidence-watermark}
\end{figure*}
```
<!-- BEGIN GENERATED figure:storm-lanes rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\begin{scope}[on background layer]
\draw[vibeyline] (0.00,-8.95) -- (0.00,0.25) node[vibeynote,anchor=south] {0}; \draw[vibeyline] (2.08,-8.95) -- (2.08,0.25) node[vibeynote,anchor=south] {40}; \draw[vibeyline] (4.16,-8.95) -- (4.16,0.25) node[vibeynote,anchor=south] {80}; \draw[vibeyline] (6.24,-8.95) -- (6.24,0.25) node[vibeynote,anchor=south] {120}; \draw[vibeyline] (8.32,-8.95) -- (8.32,0.25) node[vibeynote,anchor=south] {160};
\end{scope}
\node[vibeyhead,anchor=south east] at (-0.15,0.55) {lane};
\node[vibeyhead,anchor=south] at (4.47,0.55) {turns spent, attempt after attempt};
\node[vibeyhead,anchor=south west] at (9.04,0.55) {issue \; outcome \; turns};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-0.11) rectangle (1.46,0.11);
\fill[vibeyred!55,rounded corners=1pt] (1.50,-0.11) rectangle (3.58,0.11);
\fill[vibeyred!55,rounded corners=1pt] (3.62,-0.11) rectangle (4.60,0.11);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,0.00) {engines-pool};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (4.69,0.00) {\#321 \textcolor{vibeyred}{\ding{55}} 87};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-0.41) rectangle (2.08,-0.19);
\fill[vibeyred!55,rounded corners=1pt] (2.12,-0.41) rectangle (4.20,-0.19);
\fill[vibeyred!55,rounded corners=1pt] (4.24,-0.41) rectangle (6.32,-0.19);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-0.30) {surfaces-env};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (6.41,-0.30) {\#323 \textcolor{vibeyred}{\ding{55}} 120};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-0.71) rectangle (2.08,-0.49);
\fill[vibeygreen!80,rounded corners=1pt] (2.12,-0.71) rectangle (3.89,-0.49);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-0.60) {visual-design-provider};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (3.98,-0.60) {\#324 \textcolor{vibeygreen}{\ding{51}} 74};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-1.01) rectangle (3.12,-0.79);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-1.01) rectangle (6.28,-0.79);
\fill[vibeygreen!80,rounded corners=1pt] (6.32,-1.01) rectangle (7.57,-0.79);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-0.90) {chart-operator-forgejo-p1};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (7.66,-0.90) {\#326 \textcolor{vibeygreen}{\ding{51}} 144};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-1.31) rectangle (1.35,-1.09);
\fill[vibeyred!55,rounded corners=1pt] (1.39,-1.31) rectangle (4.51,-1.09);
\fill[vibeyred!55,rounded corners=1pt] (4.55,-1.31) rectangle (6.68,-1.09);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-1.20) {rmq-r01-queue-config};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (6.77,-1.20) {\#348 \textcolor{vibeyred}{\ding{55}} 127};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-1.61) rectangle (0.83,-1.39);
\fill[vibeygreen!80,rounded corners=1pt] (0.87,-1.61) rectangle (2.90,-1.39);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-1.50) {rmq-r02-wakeup-composition};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.99,-1.50) {\#349 \textcolor{vibeygreen}{\ding{51}} 55};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-1.91) rectangle (2.08,-1.69);
\fill[vibeyred!55,rounded corners=1pt] (2.12,-1.91) rectangle (3.26,-1.69);
\fill[vibeygreen!80,rounded corners=1pt] (3.30,-1.91) rectangle (4.14,-1.69);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-1.80) {rmq-r03-amqp-dependency};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (4.23,-1.80) {\#350 \textcolor{vibeygreen}{\ding{51}} 78};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-2.21) rectangle (2.24,-1.99);
\fill[vibeyred!55,rounded corners=1pt] (2.28,-2.21) rectangle (4.30,-1.99);
\fill[vibeyred!55,rounded corners=1pt] (4.34,-2.21) rectangle (7.46,-1.99);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-2.10) {rmq-r06-job-dispatch-envelope};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (7.55,-2.10) {\#353 \textcolor{vibeyred}{\ding{55}} 142};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-2.51) rectangle (3.12,-2.29);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-2.51) rectangle (4.77,-2.29);
\fill[vibeyred!55,rounded corners=1pt] (4.81,-2.51) rectangle (5.07,-2.29);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-2.40) {rmq-r08-dispatch-migration};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (5.16,-2.40) {\#355 \textcolor{vibeyred}{\ding{55}} 96};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-2.81) rectangle (3.12,-2.59);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-2.81) rectangle (5.71,-2.59);
\fill[vibeygreen!80,rounded corners=1pt] (5.75,-2.81) rectangle (7.15,-2.59);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-2.70) {fakes-harness-decouple};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (7.24,-2.70) {\#400 \textcolor{vibeygreen}{\ding{51}} 136};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-3.11) rectangle (3.12,-2.89);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-3.11) rectangle (5.86,-2.89);
\fill[vibeyred!55,rounded corners=1pt] (5.90,-3.11) rectangle (9.02,-2.89);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-3.00) {split-367-1-run-dir};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (9.11,-3.00) {\#421 \textcolor{vibeyred}{\ding{55}} 172};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-3.41) rectangle (1.77,-3.19);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-3.30) {orm-bootstrap-async-engine};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (1.86,-3.30) {\#434 \textcolor{vibeygreen}{\ding{51}} 34};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-3.71) rectangle (1.14,-3.49);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-3.60) {harness-T01-test-run-key};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (1.23,-3.60) {\#444 \textcolor{vibeygreen}{\ding{51}} 22};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-4.01) rectangle (2.39,-3.79);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-3.90) {installer-catalogue};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.48,-3.90) {\#469 \textcolor{vibeygreen}{\ding{51}} 46};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-4.31) rectangle (0.68,-4.09);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-4.20) {harness-T20a-qwenloop-shell-timeout-config};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (0.77,-4.20) {\#472 \textcolor{vibeygreen}{\ding{51}} 13};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-4.61) rectangle (0.16,-4.39);
\fill[vibeyred!55,rounded corners=1pt] (0.20,-4.61) rectangle (0.40,-4.39);
\fill[vibeygreen!80,rounded corners=1pt] (0.44,-4.61) rectangle (2.32,-4.39);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-4.50) {harness-T20c-qwenloop-shell-timeout-sandbox};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.41,-4.50) {\#474 \textcolor{vibeygreen}{\ding{51}} 43};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-4.91) rectangle (2.39,-4.69);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-4.80) {gap-agent-tree-parity};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.48,-4.80) {\#492 \textcolor{vibeygreen}{\ding{51}} 46};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-5.21) rectangle (3.02,-4.99);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-5.10) {gap-aws-secrets};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (3.11,-5.10) {\#493 \textcolor{vibeygreen}{\ding{51}} 58};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-5.51) rectangle (1.40,-5.29);
\fill[vibeyred!55,rounded corners=1pt] (1.44,-5.51) rectangle (4.56,-5.29);
\fill[vibeyred!55,rounded corners=1pt] (4.60,-5.51) rectangle (7.72,-5.29);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-5.40) {gap-cdd-build-trajectory};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (7.81,-5.40) {\#497 \textcolor{vibeyred}{\ding{55}} 147};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-5.81) rectangle (3.12,-5.59);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-5.81) rectangle (3.84,-5.59);
\fill[vibeyred!55,rounded corners=1pt] (3.88,-5.81) rectangle (5.38,-5.59);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-5.70) {gap-cdd-distance};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (5.47,-5.70) {\#498 \textcolor{vibeyred}{\ding{55}} 102};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-6.11) rectangle (2.13,-5.89);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-6.00) {gap-chain-dispatch};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.22,-6.00) {\#499 \textcolor{vibeygreen}{\ding{51}} 41};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-6.41) rectangle (0.16,-6.19);
\fill[vibeyred!55,rounded corners=1pt] (0.20,-6.41) rectangle (1.50,-6.19);
\fill[vibeyred!55,rounded corners=1pt] (1.54,-6.41) rectangle (4.66,-6.19);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-6.30) {gap-ci-arch-gates};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (4.75,-6.30) {\#500 \textcolor{vibeyred}{\ding{55}} 88};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-6.71) rectangle (1.30,-6.49);
\fill[vibeyred!55,rounded corners=1pt] (1.34,-6.71) rectangle (2.90,-6.49);
\fill[vibeygreen!80,rounded corners=1pt] (2.94,-6.71) rectangle (4.45,-6.49);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-6.60) {gap-ci-installer-smoke};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (4.54,-6.60) {\#501 \textcolor{vibeygreen}{\ding{51}} 84};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-7.01) rectangle (0.36,-6.79);
\fill[vibeyred!55,rounded corners=1pt] (0.40,-7.01) rectangle (3.52,-6.79);
\fill[vibeyred!55,rounded corners=1pt] (3.56,-7.01) rectangle (6.68,-6.79);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-6.90) {gap-ci-macos-gates};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (6.77,-6.90) {\#502 \textcolor{vibeyred}{\ding{55}} 127};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-7.31) rectangle (1.40,-7.09);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-7.20) {gap-ci-os-required-checks};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (1.49,-7.20) {\#503 \textcolor{vibeygreen}{\ding{51}} 27};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-7.61) rectangle (3.12,-7.39);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-7.61) rectangle (6.28,-7.39);
\fill[vibeyred!55,rounded corners=1pt] (6.32,-7.61) rectangle (7.15,-7.39);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-7.50) {gap-ci-tenants-arch-macos-1};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (7.24,-7.50) {\#504 \textcolor{vibeyred}{\ding{55}} 136};
\fill[vibeygreen!80,rounded corners=1pt] (0.00,-7.91) rectangle (2.13,-7.69);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-7.80) {orm-tables};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (2.22,-7.80) {\#549 \textcolor{vibeygreen}{\ding{51}} 41};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-8.21) rectangle (1.30,-7.99);
\fill[vibeyred!55,rounded corners=1pt] (1.34,-8.21) rectangle (2.80,-7.99);
\fill[vibeygreen!80,rounded corners=1pt] (2.84,-8.21) rectangle (4.50,-7.99);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-8.10) {loops-residency-policy};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (4.59,-8.10) {\#556 \textcolor{vibeygreen}{\ding{51}} 85};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-8.51) rectangle (3.12,-8.29);
\fill[vibeyred!55,rounded corners=1pt] (3.16,-8.51) rectangle (5.34,-8.29);
\fill[vibeyred!55,rounded corners=1pt] (5.38,-8.51) rectangle (8.50,-8.29);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-8.40) {split-351-1-amqp-contract};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (8.59,-8.40) {\#561 \textcolor{vibeyred}{\ding{55}} 162};
\fill[vibeyred!55,rounded corners=1pt] (0.00,-8.81) rectangle (0.21,-8.59);
\fill[vibeyred!55,rounded corners=1pt] (0.25,-8.81) rectangle (1.76,-8.59);
\fill[vibeyred!55,rounded corners=1pt] (1.80,-8.81) rectangle (3.88,-8.59);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.15,-8.70) {split-332-1-transport-seams};
\node[font=\sffamily\tiny,anchor=west,text=vibeygray] at (3.97,-8.70) {\#1001 \textcolor{vibeyred}{\ding{55}} 73};
\node[vibeynote,anchor=north west,align=left] at (-4.0,-9.20)
  {\textcolor{vibeygreen!80}{$\blacksquare$} attempt completed \quad \textcolor{vibeyred!55}{$\blacksquare$} attempt failed \quad
   30 lanes, 70 attempts, 2,606 turns; 17 lanes claimed completion;
   of these lanes the reviewer integrated 4 and abandoned 12, and 14 were unsettled};
\end{tikzpicture}
\caption{Every lane of the QwenStorm 3.0.0 evidence ledger, one row per lane in issue order. Each bar is one attempt, its length the turns the local model spent, green where the attempt ended in a completion claim and red where it failed; a lane gets at most three. Of 30 lanes, 17 claimed completion, and a claim is not delivery: over the same span the reviewer integrated 12 lanes and abandoned 14 in all, of which 4 and 12 are among these 30, and 14 of these were settled neither way. Read from the ledger between 2026-09-23T04:40:49Z and 2026-09-24T00:24:17Z with no gaps.}
\label{fig:storm-lanes}
\end{figure*}
```
<!-- END GENERATED figure:storm-lanes -->

Because a single local model instance served every lane in turn, attempts never
overlapped in time. The timeline in [Fig. 24](#fig:storm-timeline) shows the lanes as
the progress log recorded them; the bars never overlap, and the blank stretches between
them are the reviewer's and the operator's time, not the machine's.

<!-- BEGIN GENERATED figure:storm-timeline rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\begin{scope}[on background layer]
\draw[vibeyline] (1.04,-9.56) -- (1.04,0.2) node[vibeynote,anchor=south] {14:00};
\draw[vibeyline] (2.12,-9.56) -- (2.12,0.2) node[vibeynote,anchor=south] {16:00};
\draw[vibeyline] (3.19,-9.56) -- (3.19,0.2) node[vibeynote,anchor=south] {18:00};
\draw[vibeyline] (4.26,-9.56) -- (4.26,0.2) node[vibeynote,anchor=south] {20:00};
\draw[vibeyline] (5.33,-9.56) -- (5.33,0.2) node[vibeynote,anchor=south] {22:00};
\draw[vibeyline] (6.41,-9.56) -- (6.41,0.2) node[vibeynote,anchor=south] {00:00};
\draw[vibeyline] (7.48,-9.56) -- (7.48,0.2) node[vibeynote,anchor=south] {02:00};
\draw[vibeyline] (8.55,-9.56) -- (8.55,0.2) node[vibeynote,anchor=south] {04:00};
\draw[vibeyline] (9.62,-9.56) -- (9.62,0.2) node[vibeynote,anchor=south] {06:00};
\draw[vibeyline] (10.69,-9.56) -- (10.69,0.2) node[vibeynote,anchor=south] {08:00};
\draw[vibeyline] (11.77,-9.56) -- (11.77,0.2) node[vibeynote,anchor=south] {10:00};
\draw[vibeydashed] (6.41,-9.66) -- (6.41,0.17);\node[vibeynote,anchor=south,text=vibeygray] at (6.41,0.46) {2026-09-23 UTC};
\end{scope}
\fill[vibeyblue!80,rounded corners=1pt] (0.00,-0.09) rectangle (0.62,0.09);
\fill[vibeyblue!80,rounded corners=1pt] (0.94,-0.33) rectangle (1.00,-0.15);
\fill[vibeyblue!80,rounded corners=1pt] (0.95,-0.33) rectangle (1.01,-0.15);
\fill[vibeyblue!80,rounded corners=1pt] (1.01,-0.57) rectangle (1.12,-0.39);
\fill[vibeyblue!80,rounded corners=1pt] (1.19,-0.81) rectangle (1.27,-0.63);
\fill[vibeyblue!80,rounded corners=1pt] (1.44,-1.05) rectangle (1.51,-0.87);
\fill[vibeyblue!80,rounded corners=1pt] (1.56,-1.29) rectangle (1.62,-1.11);
\fill[vibeyblue!80,rounded corners=1pt] (1.70,-1.53) rectangle (1.77,-1.35);
\fill[vibeyblue!80,rounded corners=1pt] (1.79,-1.77) rectangle (1.85,-1.59);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (5.39,-0.09) rectangle (5.51,0.09);
\fill[vibeyblue!80,rounded corners=1pt] (5.40,-2.01) rectangle (5.51,-1.83);
\fill[vibeyblue!80,rounded corners=1pt] (5.51,-2.25) rectangle (5.57,-2.07);
\fill[vibeyblue!80,rounded corners=1pt] (5.54,-2.49) rectangle (5.65,-2.31);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (5.65,-2.25) rectangle (5.77,-2.07);
\fill[vibeyblue!80,rounded corners=1pt] (6.04,-2.73) rectangle (6.13,-2.55);
\fill[vibeyblue!80,rounded corners=1pt] (6.13,-2.97) rectangle (6.23,-2.79);
\fill[vibeyblue!80,rounded corners=1pt] (6.23,-3.21) rectangle (6.29,-3.03);
\fill[vibeyblue!80,rounded corners=1pt] (6.29,-3.45) rectangle (6.39,-3.27);
\fill[vibeyblue!80,rounded corners=1pt] (6.39,-3.69) rectangle (6.59,-3.51);
\fill[vibeyblue!80,rounded corners=1pt] (6.59,-3.93) rectangle (6.69,-3.75);
\fill[vibeyblue!80,rounded corners=1pt] (6.69,-3.69) rectangle (6.85,-3.51);
\fill[vibeyblue!80,rounded corners=1pt] (6.85,-4.17) rectangle (6.91,-3.99);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (6.89,-4.41) rectangle (7.01,-4.23);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (7.23,-4.65) rectangle (7.35,-4.47);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (7.33,-4.65) rectangle (7.45,-4.47);
\fill[vibeyblue!80,rounded corners=1pt] (7.34,-4.65) rectangle (7.46,-4.47);
\fill[vibeyblue!80,rounded corners=1pt] (7.46,-4.89) rectangle (7.53,-4.71);
\fill[vibeyblue!80,rounded corners=1pt] (7.53,-5.13) rectangle (7.85,-4.95);
\fill[vibeyblue!80,rounded corners=1pt] (7.85,-5.37) rectangle (8.18,-5.19);
\fill[vibeyblue!80,rounded corners=1pt] (8.18,-5.61) rectangle (8.34,-5.43);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (8.34,-5.85) rectangle (8.46,-5.67);
\fill[vibeyblue!80,rounded corners=1pt] (8.88,-6.09) rectangle (9.21,-5.91);
\fill[vibeyblue!80,rounded corners=1pt] (9.21,-2.97) rectangle (9.34,-2.79);
\fill[vibeyblue!80,rounded corners=1pt] (9.34,-5.85) rectangle (9.63,-5.67);
\fill[vibeyblue!80,rounded corners=1pt] (9.63,-6.33) rectangle (9.69,-6.15);
\fill[vibeyblue!80,rounded corners=1pt] (9.66,-6.57) rectangle (9.72,-6.39);
\fill[vibeyblue!80,rounded corners=1pt] (9.71,-6.81) rectangle (9.85,-6.63);
\fill[vibeyblue!80,rounded corners=1pt] (9.85,-7.05) rectangle (9.97,-6.87);
\fill[vibeyblue!80,rounded corners=1pt] (9.97,-7.29) rectangle (10.07,-7.11);
\fill[vibeyblue!80,rounded corners=1pt] (10.07,-7.53) rectangle (10.28,-7.35);
\fill[vibeyblue!80,rounded corners=1pt] (10.28,-7.77) rectangle (10.50,-7.59);
\fill[vibeyblue!80,rounded corners=1pt] (10.50,-8.01) rectangle (10.60,-7.83);
\fill[vibeyblue!80,rounded corners=1pt] (10.60,-8.25) rectangle (10.79,-8.07);
\fill[vibeyblue!80,rounded corners=1pt] (10.79,-8.49) rectangle (10.98,-8.31);
\fill[vibeyblue!80,rounded corners=1pt] (10.98,-8.73) rectangle (11.21,-8.55);
\fill[vibeyblue!80,rounded corners=1pt] (11.21,-8.97) rectangle (11.27,-8.79);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (11.25,-9.21) rectangle (11.37,-9.03);
\fill[vibeyblue!80,rounded corners=1pt] (12.22,-9.21) rectangle (12.40,-9.03);
\filldraw[fill=vibeysilver,draw=white,line width=.4pt] (12.40,-9.45) rectangle (12.52,-9.27);
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,0.00) {engines-provider};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-0.24) {qwenloop-edit-tool};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-0.48) {qwenloop-request-timeout};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-0.72) {qwenloop-run-telemetry};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-0.96) {qwenloop-toolcall-retry};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-1.20) {default-model-p1};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-1.44) {default-model-p2};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-1.68) {default-model-p3};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-1.92) {surfaces-env};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-2.16) {engines-pool};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-2.40) {visual-design-provider};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-2.64) {forge-0a};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-2.88) {rmq-r01-queue-config};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-3.12) {rmq-r02-wakeup-composition};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-3.36) {rmq-r03-amqp-dependency};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-3.60) {installer-catalogue};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-3.84) {split-332-1-transport-seams};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-4.08) {orm-bootstrap-async-engine};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-4.32) {rmq-r06-job-dispatch-envelope};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-4.56) {rmq-r08-dispatch-migration};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-4.80) {orm-tables};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-5.04) {fakes-harness-decouple};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-5.28) {split-351-1-amqp-contract};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-5.52) {loops-residency-policy};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-5.76) {split-367-1-run-dir};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-6.00) {chart-operator-forgejo-p1};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-6.24) {harness-T20a-qwenloop-shell-timeout-config};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-6.48) {harness-T20c-qwenloop-shell-timeout-sandbox};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-6.72) {harness-T01-test-run-key};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-6.96) {gap-agent-tree-parity};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-7.20) {gap-aws-secrets};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-7.44) {gap-cdd-build-trajectory};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-7.68) {gap-cdd-distance};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-7.92) {gap-chain-dispatch};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-8.16) {gap-ci-arch-gates};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-8.40) {gap-ci-installer-smoke};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-8.64) {gap-ci-macos-gates};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-8.88) {gap-ci-os-required-checks};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-9.12) {gap-ci-tenants-arch-macos-1};
\node[font=\sffamily\tiny,anchor=east,text=vibeyink] at (-0.12,-9.36) {gap-ci-tenants-arch-macos-2};
\node[vibeynote,anchor=north west,align=left] at (0,-9.91)
  {\textcolor{vibeyblue!80}{$\blacksquare$} one bar per logged start--end pair \quad \textcolor{vibeysilver}{$\blacksquare$} a start with no logged end \quad
   time in UTC from 2026-09-22 12:03; a lane started twice is drawn twice};
\end{tikzpicture}
\caption{Lane starts and ends as the storm's progress log recorded them, over 23.1 hours from 2026-09-22 12:03 UTC. One local model served every lane in turn, one instance per model; the bars therefore never overlap in time, and the blank stretches are the reviewer's and the operator's, not the machine's.}
\label{fig:storm-timeline}
\end{figure*}
```
<!-- END GENERATED figure:storm-timeline -->

### The storm throughput audit

The operator wanted far more concurrent lanes. An audit on 2026-09-23 asked first why
the storm could not simply run more, what would raise the yield of the lanes it
already ran, and which safety controls had to hold before any scale-up. Its record is
the page *QwenStorm throughput audit* (audit run of 2026-09-23, status updated
2026-09-24 11:10Z), kept outside the repository; its inputs were the lane run logs
(`lanes/*/.qwenloop/runs/*/events.jsonl`), the storm's progress log, the model server's
log and the forge, at revision `b2f5b267` (no longer on `develop`'s history since the
3.0.0 squash; the tag `paper-figures/3.0.0` keeps it). The run logs were local
operational files, never tracked, and a reboot of the host later on 2026-09-24 erased
them (see the governance account below); the progress log's lines survive in the
tracked evidence ledger, beside an early copy of the log itself. Every figure below is the audit's
unless we say we recomputed it.

**One model slot binds.** Across the 82 run directories on disk, 2,985 model turns were
recorded, and model calls took 9.68 of the 10.01 hours those runs spanned, 96.7%; tool
execution and harness overhead were the other 3.3%. The progress log held 41 closed
lane intervals, and not one overlaps another. We recomputed these figures from the
local files on 2026-09-24, before the reboot, and they agree. Three things serialised
the storm, and they stack: the queue script waited for any running lane anywhere on
the host, sub-doctrine 8.c then gave a model on the operator's own hardware one run at
a time, and the server was configured with one slot. Amdahl's law then bounds what more
lanes sharing that slot could buy: with 3.3% of lane time outside the model, the
speed-up is at most $1/0.967 \approx 1.03$. Interleaving lanes would also evict each
other's cached prompt prefix; the audit put the cost at about 80 s of re-read per
switch at the median turn of 22,500 tokens. Whether a *second slot* helps is a
different question, which the calibration below measures. These populations are not
the evidence ledger's (30 lanes, 70 attempts, 2,606 turns), which consumes the progress
log and lane results from 2026-09-23T04:40:49Z onward; the audit counts every run
directory then on disk, and the runs of nine earlier lanes had been deleted and are in
neither. We report both and reconcile neither to the other.

**Conversion.** The progress log showed 40 lanes started, which we recomputed and which
the tracked ledger still reproduces (49 start lines over 40 distinct lanes). Of
those, 13 had work on `develop` at the audit, 3 of them (#1044, #1053, #1054) through
the automated path, in which the runner completes and the publish step opens the pull
request. None reached `develop` with no human step: none of the last 60 merged pull
requests had a successful required review gate, and the merge train logged *merged 0*
on every pass, so every merge was made by hand. Ten lanes needed a hand-built pull
request, eight of them in a single one (#396) that repaired or hand-wrote them where
the local model fell short. At the runner level, 18 of the 82 runs completed. The
audit's projection is the point: more lanes multiply this conversion rate and do not
get around it, and the hand repair it implies is capacity nothing records.

**Declared, not enforced.** Seven controls existed in configuration or documentation
and were read by nothing, or bound only in a mode not in use: the delegated approver's
author list (with both gates green, the approver would have readied a stranger's pull
request); the merge train's trusted authors, which held a stranger's pull request only
when pull-request automation was off, and it was on; 31 forbidden paths (72 are
declared at this revision, 51 of them at the pin and 21 more since #1302), of which a
lane could touch up to 19, among them the workflow directory, the canon and the merge
train itself; the issue text a lane's prompt carried, whose author was never fetched
and which was followed directly by trusted instructions with no separator; a merge
fallback that retried with `--admin`, unattended, contrary to 12.d; an environment
switch for unattended approval that nothing read; and an approver agent that nothing
called. None was exploited: every one of the 594 queued issues was the operator's. All
seven were enforced by merged code on 2026-09-24 (#1078, #1079, #1083), with the yield
fixes the audit ranked beside them: a retry on an empty model reply, the end of 27 of 60
failed runs (#1077); a lane's commands run in the lane's own environment, after 18 runs
in 12 lanes had tested the wrong tree (#1080); a per-lane time limit and stall
watchdog, after one 93-minute stall with no terminal event (#1081); real `search`,
`find` and `open_file` tools, after the audit's 446 calls to tools that did not exist,
about 11% of model time (#1082, whose own recount over the same runs gives 450, 431 of
them to `search`, `find` and `open_file`); and instruments that report what they measured (#1084). The storm
had not run since, so at the cutoff the effect of these fixes on yield is unmeasured.
One control was not settled: the repository's rulesets carry a bypass actor nobody
declared, and 78 of the last 200 merges went in while the forge reported a review
still required; who made them, and how, needs the organisation's audit log. The
undeclared bypass lived in a hand-made `develop` ruleset beside the declared one.
Since 3.1.0 `vibey-gh rulesets --check` fails on any undeclared ruleset and names its
bypass actors, and since 3.2.0 the coverage floor that ruleset carried is declared
(`minimum_coverage = 100`, #1277), so it can be deleted without losing the floor;
whether it has been deleted is a fact of the forge, not of the repository. For a later
week the forge's rule-suite record answers the who and the how directly, as the
autonomy scan below reports.

**Most of the audit's first claims were wrong.** Twenty-five agents audited six
dimensions, and adversarial verifiers then checked the leading claims before anything
was written up. They refuted 16 of 18. Some corrections were of degree: 29 of 64
failed runs ending on an empty reply became 27 of 60; 45 calls to nonexistent tools
became 446; 3.75 lanes an hour from the model alone became 3.20 from the runs on disk.
Some were of kind: the claimed serialisation point was the wrong line of the queue
script; a single slot said to be removable with hardware is serialised by code, canon
and configuration together; a reaper said to abandon lanes without their gates does
not; and the account of #1090 as a silently truncated prompt was wrong, as the
exact-head section records. We report this as a finding about method, not a footnote.
A first pass by capable agents over complete logs was wrong more often than right on
its headline numbers, and it was the verification step, not the analysis, that made
the audit usable. It applies to this paper too. The host-benchmark paragraph below
once reported that the 64k window *generated 16% faster*, and the audit's verifiers
found decode speed varying from 26 to 34 tokens per second within one allocation, so
that difference is inside the noise and is no longer claimed.

### Host hardware benchmarks and context headroom

On 2026-09-22 the storm was paused and the same ten-turn session was replayed against
five server configurations on the one 24 GB host, with the results kept as a tracked
file (`docs/plans/qwenstorm-3.0.0/bench/results.jsonl`). Four configurations served
Qwen2.5-Coder-14B through llama.cpp with different slot counts, cache types and
context windows; the fifth served `gpt-oss:20b` through Ollama.

The record shows two things ([Fig. 25](#fig:bench-hosts)). For every llama.cpp
configuration, generation speed fell as the context grew across the session, from
about 11 tokens per second on the first turn to between 6 and 9 on the tenth, and the
four configurations finished the session in 212 to 220 s of wall time. The Ollama configuration finished the same session in 86 s, and the same
`gpt-oss:20b` model served by llama.cpp at a 64k context did not load at all. The
record does not separate the model from the serving stack, so the difference is
reported and not explained.

<!-- BEGIN GENERATED figure:bench-hosts rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.8cm},vibeyaxis,width=8.6cm,height=4.8cm,
  xmin=0.5,xmax=10.5,xtick={1,...,10},xlabel={turn of a ten-turn session}]
\nextgroupplot[title={a. Generation speed as the context grows},ylabel={tokens / s},ymin=0]
\addplot[vibeyblue,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.2) (2,9.8) (3,9.3) (4,9.6) (5,9.4) (6,9.5) (7,7.6) (8,9.0) (9,8.8) (10,8.4)};
\addplot[vibeyteal,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.2) (2,10.5) (3,10.0) (4,8.8) (5,9.4) (6,9.1) (7,8.0) (8,7.7) (9,6.9) (10,6.2)};
\addplot[vibeygold,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.1) (2,10.8) (3,9.9) (4,9.4) (5,8.7) (6,8.1) (7,7.4) (8,7.5) (9,8.5) (10,7.9)};
\addplot[vibeyviolet,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.3) (2,10.4) (3,10.3) (4,10.1) (5,9.8) (6,8.0) (7,9.2) (8,8.3) (9,7.5) (10,8.5)};
\nextgroupplot[title={b. Wall time per turn},ylabel={seconds},ymin=0,legend to name=bench-hosts-legend,legend columns=-1,
  legend style={/tikz/every even column/.append style={column sep=6pt}}]
\addplot[vibeyblue,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.44) (2,17.22) (3,18.32) (4,19.09) (5,22.51) (6,23.45) (7,26.94) (8,23.22) (9,25.76) (10,27.07)};
\addlegendentry{A-baseline (215\,s)}
\addplot[vibeyteal,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.63) (2,15.81) (3,17.54) (4,19.0) (5,20.66) (6,23.4) (7,26.1) (8,24.77) (9,29.29) (10,32.29)};
\addlegendentry{B-1slot-q8-48k (220\,s)}
\addplot[vibeygold,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.65) (2,15.3) (3,17.47) (4,18.63) (5,21.39) (6,25.27) (7,26.71) (8,25.26) (9,26.03) (10,27.83)};
\addlegendentry{C-1slot-q8-48k-draft (216\,s)}
\addplot[vibeyviolet,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.41) (2,16.36) (3,17.7) (4,18.06) (5,20.31) (6,25.87) (7,24.37) (8,23.61) (9,27.42) (10,27.09)};
\addlegendentry{D-1slot-f16-32k (212\,s)}
\addplot[vibeyred,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,8.89) (2,9.64) (3,8.46) (4,6.78) (5,8.43) (6,7.9) (7,8.44) (8,8.03) (9,10.48) (10,8.56)};
\addlegendentry{E-gptoss-20b-ollama (86\,s)}
\end{groupplot}
\node[anchor=north,inner sep=0pt] (legend) at ($(group c1r1.south west)!0.5!(group c2r1.south east)+(0,-0.95cm)$)
  {\pgfplotslegendfromname{bench-hosts-legend}};
\node[vibeynote,anchor=north] at ([yshift=-0.08cm]legend.south) {in brackets, each configuration's whole-session wall time; E-gptoss-20b-64k: server exited during load, bench failed};
\end{tikzpicture}
\caption{The host benchmark of 2026-09-22: the same ten-turn session replayed against five server configurations on one 24\,GB machine. (a) Generation speed falls as the context fills for every llama.cpp configuration of Qwen2.5-Coder-14B, whatever the slot count or cache type. (b) The gpt-oss:20b model on Ollama completed the session in a fraction of the wall time; the same model served by llama.cpp at a 64k context failed to load at all. Every point is one row of the tracked results file.}
\label{fig:bench-hosts}
\end{figure*}
```
<!-- END GENERATED figure:bench-hosts -->

The context window is where the host's memory was actually spent. On Apple Silicon a
served model's weights and its key-value cache are wired memory, which no swap can
reclaim, and the cache is reserved in proportion to the window: at a 131,072-token
window the server wired 18.55 GB of the 24 GB, leaving the rest of the machine to
thrash. The storm's own run ledgers record how much context 838 real turns used: a
median of 20,070 tokens, a 99th percentile of 42,979 and a maximum of 49,118.
[Fig. 26](#fig:host-context) sets those percentiles against the three windows
considered. A 32k window would have truncated 71 turns; the 128k baseline was never
reached by any turn; the 64k window chosen covers every recorded turn with a third
again as headroom, and wires 1.3 GB less. In that one sweep it also generated 16%
faster (32.5 against 28.0 tokens per second), but the throughput audit's verifiers found
decode speed varying from 26 to 34 tokens per second within a single allocation, so the
difference is inside the noise and we do not claim it. That is sub-doctrine 8.j, fitted
to the iron: a setting moves against a number read from this host, and the number is
recorded beside it.

<!-- BEGIN GENERATED figure:host-context rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\shade[left color=vibeyblue!18,right color=vibeyblue!4] (0,-0.12) rectangle (7.0,0.12);
\draw[vibeyink,line width=.6pt] (0,0) -- (7.0,0);
\draw[vibeyink] (0.00,0) -- (0.00,-0.08); \draw[vibeyink] (0.88,0) -- (0.88,-0.08); \draw[vibeyink] (1.75,0) -- (1.75,-0.08); \draw[vibeyink] (2.62,0) -- (2.62,-0.08); \draw[vibeyink] (3.50,0) -- (3.50,-0.08); \draw[vibeyink] (4.38,0) -- (4.38,-0.08); \draw[vibeyink] (5.25,0) -- (5.25,-0.08); \draw[vibeyink] (6.12,0) -- (6.12,-0.08); \draw[vibeyink] (7.00,0) -- (7.00,-0.08);
\node[vibeynote,anchor=north] at (0,-0.1) {0};
\node[vibeynote,anchor=north east] at (6.92,-0.1) {131,072 tokens};
\draw[vibeyink,line width=.6pt] (1.07,0.12) -- (1.07,0.34) -- (0.35,0.62) node[vibeynote,anchor=south,text=vibeyink,inner sep=1.5pt] {p50\\20,070};
\draw[vibeyink,line width=.6pt] (1.71,0.12) -- (1.71,0.34) -- (1.15,0.62) node[vibeynote,anchor=south,text=vibeyink,inner sep=1.5pt] {p90\\32,026};
\draw[vibeyink,line width=.6pt] (1.97,0.12) -- (1.97,0.34) -- (1.95,0.62) node[vibeynote,anchor=south,text=vibeyink,inner sep=1.5pt] {p95\\36,816};
\draw[vibeyink,line width=.6pt] (2.30,0.12) -- (2.30,0.34) -- (2.75,0.62) node[vibeynote,anchor=south,text=vibeyink,inner sep=1.5pt] {p99\\42,979};
\draw[vibeyink,line width=.6pt] (2.62,0.12) -- (2.62,0.34) -- (3.55,0.62) node[vibeynote,anchor=south,text=vibeyink,inner sep=1.5pt] {max\\49,118};
\draw[vibeyred,line width=.8pt,densely dashed] (1.75,-0.15) -- (1.75,-0.60) node[vibeynote,anchor=north,text=vibeyred,align=center] (window0) {32k: truncates 71 turns};
\draw[vibeygreen,line width=.8pt,densely dashed] (3.50,-0.15) -- (3.50,-1.50) node[vibeynote,anchor=north,text=vibeygreen,align=center] (window1) {64k: chosen, 16,418 headroom};
\node[vibeypill,shape=rectangle,rounded corners=4.5pt,anchor=north] (window1sweep0) at ([yshift=-1.5pt]window1.south) {B $\cdot$ f16 KV cache\\17.25\,GB wired, 32.5 tok/s};
\node[vibeypill,shape=rectangle,rounded corners=4.5pt,anchor=north] (window1sweep1) at ([yshift=-1.5pt]window1sweep0.south) {C $\cdot$ q8\_0 (requested) KV cache\\17.24\,GB wired, 30.9 tok/s, inconclusive};
\draw[vibeygray,line width=.8pt,densely dashed] (7.00,-0.15) -- (7.00,-0.60) node[vibeynote,anchor=north east,text=vibeygray,align=center] (window2) {128k: baseline, never reached};
\node[vibeypill,shape=rectangle,rounded corners=4.5pt,anchor=north east] (window2sweep0) at ([yshift=-1.5pt]window2.south east) {A $\cdot$ f16 KV cache\\18.55\,GB wired, 28.0 tok/s};
\node[vibeyhead,anchor=south west] at (0,1.25) {context actually used per turn, 838 storm turns};
\end{tikzpicture}
\caption{Fitting the model to the iron. The percentiles mark how much context 838 real storm turns used; the dashed lines are the three context windows considered. A 32k window would have truncated 71 turns, and the 128k baseline, never reached by any turn, wired 18.55\,GB of a 24\,GB machine. The 64k window chosen covers every recorded turn with a third again as headroom. Beneath each window, the sweep's configurations measured at it report what each setting cost and delivered.}
\label{fig:host-context}
\end{figure}
```
<!-- END GENERATED figure:host-context -->

**How many runs at once, per device.** The audit left one question it could not answer:
sub-doctrine 8.c then held a model on the operator's own hardware to one run at a time,
while 8.j requires every setting, how many run at once among them, to be fitted to a
number measured on the machine. On 2026-09-23 the operator ruled
*measure, then decide*. On 2026-09-24 the ruling was extended, and it is the method we
report here, not a result. Sweep $N = 1, 2, 3, \dots$ concurrent runs replaying real storm-depth
turns, and measure throughput, latency, wired memory and fidelity at each $N$, to find
the ideal $N$. Calibrate every device separately, keyed by a fingerprint of its
hardware, memory, operating system, server version, model digest and context window.
Where the evidence is missing or stale, fall back to $N = 1$, and recalibrate
automatically. And amend 8.c to rule the method, not a number, ratified by the
operator's merge like every sub-doctrine. The single slot the audit found binding is
therefore not treated as a law of this host but as the default an unmeasured device
gets.

The sweep for the 24 GB host ran on 2026-09-24 from 15:11 to 15:42Z, before the cutoff
(ADR-0058; evidence tracked as `docs/architecture/evidence/slots-2026-09-24-mac17-2.md` and
`.json`). The device is an Apple M5 with 24 GiB under macOS 26.6.2, running ollama 0.34.4 with
gpt-oss:20b at a 65,536-token context per run, fingerprint `f99b07f610204948`. Each step
replayed 60 storm-shaped turns in 20 segments, drawn from 1,096 turns in 40 runs. At
$N = 1$, run twice, the host completed 98.2 and 112.7 turns an hour, with a median turn of
16.5 and 12.9 s, a 95th percentile of 112.6 and 102.8 s, and peak wired memory of 18.4 and
18.1 GB. The two runs agreed with each other exactly (structural and exact fidelity 1.0
over 55 turns). Their throughput differed by 14.8%, so a smaller difference between steps
is noise, not a finding. At $N = 2$ the host completed 111.9 turns an hour, within that
noise, while the median turn rose to 29.8 s, the 95th percentile to 189.9 s and peak wired
memory to 20.2 GB. The replies at $N = 2$ matched the single run's structure in only 81.8% of
turns (exact: 74.5%), below the 95% floor. That was the overshoot, and the sweep stopped
there. The ideal for this device is therefore $N = 1$: a second concurrent run bought no
throughput and cost fidelity. Even at $N = 1$ the host swapped out about 25 GB a
minute, far over the record's 64 MB allowance, and the record accepts that step only as
the floor: one run is the least this device can do, not a comfortable fit. One step was
recorded but not judged: at a 32,768-token context, two runs reached 172.7 turns an
hour, with structural fidelity still only 88.9% and only 36 of 60 turns completed.
The evidence does not cover other models, context windows or devices, tool execution
between turns, whole runs, thermals, or long-horizon stability. The amendment to 8.c that
sets the method, not a number, was proposed for the operator's ratification (#1141),
was not ratified at the cutoff, and was ratified by the operator's merge of #1141 on
2026-09-25; on `develop` that merge now sits inside the 3.0.0 squash (#1244), and 8.c
reads *unmeasured or stale means one*.

### Rolling minimum system requirements

A requirements list that is written once goes stale without saying so. The model changes,
vibey's own limits change, and the list does not. vibey's minimum requirements are therefore
a measurement, repeated weekly, and the table below is regenerated from its record
(`docs/architecture/evidence/minimum-specs.json`) by `scripts/minimum_specs.py`. It was
seeded from three passes on one host on 2026-09-29 and 2026-09-30: software, network and
hardware. Each week a workflow on the project's self-hosted macOS runner repeats the parts
that are cheap and deterministic enough. It probes the Python floor on every candidate
interpreter and measures a cold install, its download and its size. It checks the
PostgreSQL server against the floor vibey declares, on a scratch database the run creates
and drops. It reads the model sizes from the registry without pulling them. It measures the
model's memory at each configured context and its throughput on the GPU and on the CPU
alone, and the peak memory of the everyday commands, the hub and the launcher. The result
arrives as a pull request, like any other change. That is the design. At our cutoff,
2026-10-02, the workflow had still never run (its first scheduled run falls on 2026-10-05),
so every figure below comes from the seed passes.

The record keeps three kinds of figure apart. A *measured* figure came from a command on
the named host. A *declared* one was read from the repository: a constant such as the
900 s per-request timeout, a floor in a manifest, or an assumption stated in the
configuration. A *derived* one is arithmetic on the other two, and the record keeps its
formula and inputs. The requirements themselves are derived, so a change to any input
moves every row that depends on it, and a check in CI recomputes both the derivations and
the table from the committed record. The model measurements run only on a quiet host: the
load must be low, no other client may have used the model server within a quiet window,
and a declared busy check must be silent. A measurement that cannot run keeps its last
good value, marked *stale since* the date it was last measured, with the reason. It is
never reused silently (sub-doctrine 10.f). Every row is therefore a dated measurement,
not a statement about this revision: the PostgreSQL row counts the migrations the
checkout of 2026-09-29 carried, twenty, and 3.2.0 has since added a twenty-first
(migration 0021), which the next weekly measurement will count. The install sizes were
likewise measured on wheels built before 3.2.0.

<!-- BEGIN GENERATED specs:minimum-requirements — regenerated by scripts/minimum_specs.py -->
```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{1.3in}p{2.3in}p{2.0in}p{0.9in}@{}}
\textbf{Requirement} & \textbf{Minimum} & \textbf{Recommended} & \textbf{Basis}\\
\hline
Memory, Apple Silicon (unified) & 24 GB (stale since 2026-09-30: derived from stale input(s): ram.minimum\_need\_gib) (needs 17.79 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx32768, ram.vibey\_side\_gib)) & 32 GB (stale since 2026-09-30: derived from stale input(s): ram.recommended\_need\_gib) (needs 24.42 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx131072, ram.vibey\_side\_gib)) & derived, stale\\
Memory, 16 GB Mac & insufficient (stale since 2026-09-30: derived from stale input(s): ram.design\_only\_need\_gib): DESIGN alone needs 17.15 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx8192, ram.vibey\_side\_gib); the GPU part is -78.0 MiB (stale since 2026-09-30: derived from stale input(s): bench.gpt-oss:20b.ctx8192.device\_mib, gpu.metal\_limit\_16gb\_mib) over its limit at 8,192 & - & derived, stale\\
GPU memory for gpt-oss:20b & 12,339 MiB (stale since 2026-09-30: no accounting line in the log) at 8,192; 12,974 MiB (stale since 2026-09-30: no accounting line in the log) at 32,768 & discrete GPU: 16 GB (stale since 2026-09-30: derived from stale input(s): bench.gpt-oss:20b.ctx32768.device\_mib) card (not verified on CUDA) & measured, stale; derived, stale\\
Model throughput at 24k depth & 10 tok/s generation, 100 tok/s prompt (worst BUILD turn 512 s of 900 s) & 25 / 500 tok/s (worst turn 143 s); measured here 18.1 tok/s / 379 tok/s & derived; measured\\
CPU only (no GPU) & DESIGN call 462 s (fits: yes); worst BUILD turn 1,422 s (fits: no) & use a GPU; CPU only measured 2.8 tok/s generation, 44.5 tok/s prompt & derived; measured\\
Free disk & 20 GB (stale since 2026-09-30: derived from stale input(s): disk.minimum\_need\_gb) (needs 17.8 GB (stale since 2026-09-30: derived from stale input(s): disk.ollama\_app\_bytes)) & 50 GB (stale since 2026-09-30: derived from stale input(s): disk.recommended\_need\_gb) (needs 45.2 GB (stale since 2026-09-30: derived from stale input(s): disk.minimum\_need\_gb)) & derived, stale\\
Python & 3.12 (declared $\geq$3.12) & works on 3.12, 3.13, 3.14 & derived; declared\\
PostgreSQL & 14 (checked on connect) & measured on 18.4 (stale since 2026-09-29: \textdollar{}VIBEY\_SPECS\_PG\_ADMIN\_URL is not set): 20 (stale since 2026-09-29: \textdollar{}VIBEY\_SPECS\_PG\_ADMIN\_URL is not set) migrations applied & declared; measured, stale\\
Ollama with gpt-oss:20b (sovereign default) & required unless a paid engine is set up; measured on 0.35.0 & - & measured\\
Model download, gpt-oss:20b & 13.79 GB & qwen3:14b 9.28 GB (opt-in) & measured\\
Install download, vibey-engine & 236.4 MB & with {[}hub{]} 238.0 MB; krypton-app 238.0 MB & measured\\
Internet at runtime (sovereign path) & none & - & measured\\
\end{tabular}
\caption{Minimum and recommended requirements for the sovereign default (vibey, gpt-oss:20b on Ollama and PostgreSQL on one host), as the weekly measurement last recorded them. Measured on Mac17,2 $\cdot$ Apple M5 $\cdot$ 24 GiB $\cdot$ macOS 26.6.2 (25G83), aarch64 $\cdot$ unknown chip $\cdot$ 23 GiB $\cdot$ Ubuntu 24.04.4 LTS, figures dated 2026-09-29 to 2026-10-02 (UTC); record \texttt{docs/architecture/evidence/minimum-specs.json}. A stale figure is the last good value, marked with the date it was last measured.}
\label{tab:minimum-requirements}
\end{table*}
```
<!-- END GENERATED specs:minimum-requirements -->

At the seed measurement, three findings stood out. First, memory is the binding
constraint, and it is set by the context, not by the model file. llama-server's own
accounting put `gpt-oss:20b` at 13.15 GiB at the conductor's 8,192-token ceiling, 13.79 GiB
at the runner's 32,768 and 16.42 GiB at the model's 131,072. That last one is what the
runner gets from a default Ollama install, because its requests carry no context size.
Adding vibey, PostgreSQL and an allowance for the operating system gives a 24 GB minimum
and a 32 GB recommendation. Second, a 16 GB Mac cannot run the sovereign default: DESIGN
alone needs 17.15 GiB. That verdict is derived, and no 16 GB machine was measured. Third,
a GPU is not optional for BUILD. On the CPU alone the host generated about 4 tokens per
second, so a DESIGN call fits the 900 s timeout, but the worst BUILD turn and the
conductor's retry do not. These are claims about one machine, an Apple M5 with 24 GiB of
unified memory. The record lists what was not verified, which includes Linux as an
installed system, discrete GPUs and every other memory size.

Linux is measured as a matrix rather than assumed from the Mac. Every distribution the
configuration declares, on each architecture it declares, is one cell, measured inside
that distribution's own container image: the repository version behind each floor
(the kernel, Python, PostgreSQL and the desktop libraries), the closure each package set
adds as the package manager itself sizes it, the newest glibc the installed wheels
require, and a cold install. In CI each cell runs on a native runner of its architecture.
A cell run under emulation keeps its sizes and versions and refuses its timings, and a
cell with no image, Arch Linux on arm64 among them, is recorded as skipped with the
reason. The requirements are then fitted, not read off one point. Memory against context
is a least-squares line, $M(c) = M_0 + kc$, because the weights are constant and the KV
cache grows with the window; the residuals are kept so that a bend would show. CPU
generation against cores follows Amdahl's law, $T(n) = T_1/((1-p) + p/n)$, fitted
through its reciprocal, which is linear in $1/n$; its marginal gain
$dT/dn = T_1 p/((1-p)n + p)^2$ falls monotonically, so the recommended core count, where
that gain drops to a declared threshold, has a closed form, and so does the fewest cores
that reach the minimum generation rate. The append-only ledger's disk is the integral of
its growth rate over a declared horizon. The thresholds, the headroom factor and the
horizon are declared beside their reasons in the configuration; the fitted parameters
and every point they came from are in the record, and the CI check refits them.

<!-- BEGIN GENERATED specs:linux-requirements — regenerated by scripts/minimum_specs.py -->
```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{1.2in}p{0.55in}p{0.65in}p{0.8in}p{0.8in}p{0.9in}p{1.5in}@{}}
\textbf{Distribution} & \textbf{Arch} & \textbf{Run} & \textbf{Cores min / rec} & \textbf{Disk min / rec} & \textbf{PostgreSQL} & \textbf{glibc}\\
\hline
Ubuntu 24.04 LTS & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 16 ($\geq$ 14: yes) & 2.39 (wheels need 2.34: yes)\\
Ubuntu 24.04 LTS & aarch64 & native & unreachable / 4 & 20 GB / 50 GB & 16 ($\geq$ 14: yes) & 2.39 (wheels need 2.34: yes)\\
Ubuntu 26.04 LTS & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Ubuntu 26.04 LTS & aarch64 & native & unreachable / 4 & 20 GB / 50 GB & 18 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Arch Linux & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.44 (wheels need 2.34: yes)\\
Arch Linux & aarch64 & not run & unreachable / 4 & - & - & -\\
Fedora (current release) & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Fedora (current release) & aarch64 & native & unreachable / 4 & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
\end{tabular}
\caption{The Linux matrix: each supported distribution on each architecture, measured in the distribution's own container image. Memory is the same for every cell, 24 GB (stale) minimum and 32 GB (stale) recommended, from the least-squares line $M(c) = M_0 + kc$ fitted to the measured model memory ($M_0$ = 13,241 MiB (stale), $k$ = 27.874 (stale) KiB/token, $R^2$ = 0.99998 (stale)) with a declared headroom factor. Cores come from Amdahl's law fitted per architecture: the minimum reaches the minimum generation rate, the recommended is the knee where $dT/dn$ falls to a declared threshold. An emulated cell's sizes and versions stand; its timings are refused. Measured on Mac17,2 $\cdot$ Apple M5 $\cdot$ 24 GiB $\cdot$ macOS 26.6.2 (25G83), aarch64 $\cdot$ unknown chip $\cdot$ 23 GiB $\cdot$ Ubuntu 24.04.4 LTS, archlinux:latest (linux/amd64, native) on GitHub-hosted GitHub Actions 1000073941, fedora:latest (linux/amd64, native) on GitHub-hosted GitHub Actions 1000073938, fedora:latest (linux/arm64, native) on GitHub-hosted GitHub Actions 1000073936, ubuntu:24.04 (linux/amd64, native) on GitHub-hosted GitHub Actions 1000073942, ubuntu:24.04 (linux/arm64, native) on GitHub-hosted GitHub Actions 1000073935, ubuntu:26.04 (linux/amd64, native) on GitHub-hosted GitHub Actions 1000073939, ubuntu:26.04 (linux/arm64, native) on GitHub-hosted GitHub Actions 1000073937, figures dated 2026-09-29 to 2026-10-02 (UTC).}
\label{tab:linux-requirements}
\end{table*}
```
<!-- END GENERATED specs:linux-requirements -->

The table is the matrix as seeded on 2026-10-01 (#1313), and most of what the method
promises is not yet in it. The native runners have not run a cell. Every cell ran in a
container under Docker Desktop on the Apple M5: natively for arm64, and under QEMU
emulation for x86_64, where `uv` itself crashed (signal 11), so no x86_64 cell has its
install sizes, the glibc its wheels need, a disk requirement or a timing. Arch Linux has
no official arm64 image and is skipped. The memory line was fitted on the Mac, to four
points from 4,096 to 131,072 tokens on its Metal backend, and the Linux memory figures are
that line times a declared headroom factor, plus vibey's own share and an allowance for
the operating system taken from the Mac, with the whole model in system memory; no Linux
system's memory was measured. No thread sweep had run, so Amdahl's law is fitted on neither architecture and
every core count reads *not measured*. And the ledger's bytes per job had not been
measured, so the disk integral has no measured input yet. What the table does establish
is narrower: in every cell that ran, the distribution packages a Python, a PostgreSQL and
desktop libraries that meet vibey's floors, and on arm64 its glibc meets the 2.34 the
wheels require. The record lists each of these gaps under *not verified*.

### Host health and the memory budget

The minimum requirements say what a host must have. They do not say whether the host vibey
runs on is still healthy, or when it will need replacing. Since #1330,
`scripts/host_health.py` answers both from a weekly, append-only record
(`docs/architecture/evidence/host-health.jsonl`), rendered into
`docs/reference/host-health.md` and into `vibey doctor`. The probes run on the host
itself, from a launchd agent or a systemd user timer, because the self-hosted runner is a
Linux container on the host and cannot see its SSD, battery, thermal state or real memory
pressure. None needs root, each that cannot run is recorded as skipped with its reason,
and the host enters the record only as a truncated hash. Each driver of replacement
carries a declared threshold: SSD wear, battery capacity and cycles, generation rate, free
disk, memory against vibey's own minimum, sustained swap, kernel panics, thermal limiting
and the vendor's support dates. A trend is a Theil–Sen slope with Sen's rank interval; a
projected crossing is dated with an earliest and a latest bound, and the latest is
*unbounded* when the data cannot rule out never. A trend needs four weekly points, and swap
must stay past its threshold in three records before it counts. At our cutoff the record
held two, of 2026-10-01 and 2026-10-02, and no driver projected a replacement date. Every
trend had too little history, Apple publishes neither an end of support for macOS nor an
endurance rating for this SSD, and memory sat exactly at vibey's 24 GB minimum, which
counts as within. Swap in use was 0.60 and then 0.68 of memory, past its 0.5 threshold in
two of the three records that would confirm it. The weekly agent is rendered by `install`
and loaded only by the operator, and whether it has been loaded is not recorded.

That swap prompted a measurement (#1334), on 2026-10-02 from 00:39 to 01:09Z, with the
model loaded throughout and the large-diff study running on it
(`docs/runbooks/host-optimization.md`). The process footprints added up to about 49 GiB on
the 24 GiB machine: the model server 18.5 GiB, Docker Desktop's virtual machine 8.9 GiB,
almost all of it compressed or swapped, and about 13 GiB the operator's own applications
and their tool servers. Docker Desktop's built-in Kubernetes alone measured about 6.4 GiB
across ten nodes. The SSD took 152.5 GB of writes an hour, swap-outs accounted for 130.1 GB
of them, 85%, and every readable process's own file writes came to 1.8 GB. That a
swap-out writes one 16 KiB page to the swap file is inferred, and an upper bound, since the
swap files may hold compressed pages; tracing writes one by one would need root. The model
was also loaded 166 times on 2026-10-01, and of 358 loads since 2026-09-28, 298 changed the
context size or the model, because clients ask for a different window per request. So the
SSD's 36.55 TB written in 337 power-on hours is, by elimination rather than by trace,
mostly the price of overcommitted memory, and the lever is memory, not the disk. It is
also a confound for every timing in this section and the last: the rate at which a review
generates depends on what else the host holds.

The plan that followed is declared, gated and reversible (`scripts/host_tuning.toml`,
`scripts/host_health.py tune`). Class A, regenerable caches and logs, is always applied; it
freed 6.16 GB of npm's cache, and left uv's alone, because other processes held its lock
and forcing it would route around that check. Class B changes the model's behaviour or
memory: one loaded model and one parallel request, a fixed context size per lane, a longer
keep-alive, then flash attention and a quantised cache. It waits until the experiments on
the host end; each item is then applied alone and kept only if a review-canary run after
it still meets its floor and holds recall and false positives against the baseline. Class
C is the operator's: turning off Docker Desktop's Kubernetes, the largest single lever
measured, then capping its virtual machine at 8 GiB, deciding on unused models, and sizing
the next machine at 32 GiB. Every prior value goes to an append-only journal that `undo`
restores, the tool never restarts a service or uses root, and the weekly record judges each
change by the weeks after it. At our cutoff only class A had been applied, and no class-A
item reaches memory, so nothing that could move the swap or the SSD's writes had yet been
done.

### Field data

The git history is field data: nothing in it was held fixed. At the pinned source
revision, `d4c4e1f8`, 1,331 commits are reachable across nine root histories, the
absorbed histories of the family's packages. Since 2026-08-09, when the family's own
development begins, 1,319 commits landed on 34 active days, between 1 and 191 per day
(median 25.5, mean 38.8, sample standard deviation 41.0). Commits landed in all 24
hours of the day in US Eastern time, with the fewest (21) in the 09:00 hour and the
most (91) in the 18:00 hour. The longest pause was nine days with no commit, from
2026-08-30 to 2026-09-09, and nothing in the repository records its cause. Nineteen
`vibey` release tags point at commits dated between 2026-08-16 and 2026-09-30, and 542
commit subjects across the absorbed histories end in a pull-request reference, 538 of
them since 2026-08-09 (`scripts/paper_evidence.py --rev d4c4e1f8`).

Every commit count is lower than at the previous pin, `c78049b6` (1,514 commits reachable,
1,502 since 2026-08-09 on 38 active days), although the work grew, and the reason is a
merge, not a slowdown. The 3.0.0 release reached `develop` as one squash commit (#1244),
which took the place of the 213 commits of its cycle, dated 2026-09-21 to 2026-09-28,
in `develop`'s history. Those days now read as nearly empty, and the whole cycle as one
commit on 2026-09-29: fewer commits, not less work. Nothing is lost: the tag
`paper-figures/3.0.0` still holds the old history, and the previous figures reproduce
at that pin. The same squash makes the week of 2026-09-21 to 2026-09-27, which held 218 commits at the
previous pin (US Eastern time), look like the project's quietest in
[Fig. 27](#fig:commits-daily), so the daily figures below are a record of
how commits reached the integration branch, not of when the work was done.

The daily rate's spread is 106% of its mean, against 24% in the controlled region.
That is what the model predicts when the coordinates of $d$ vary freely, but it is
also what almost any model would predict of an uncontrolled process, so the history
does not test the regularity. We report it so that the controlled band is never
mistaken for a field rate.

The daily cadence and release events are tracked in [Fig. 27](#fig:commits-daily).

<!-- BEGIN GENERATED figure:commits-daily rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=17.2cm,height=5.6cm,ybar,bar width=4.2pt,xmin=-0.7,xmax=52.7,ymin=0,ymax=231,
  xtick={0,7,14,21,28,35,42,49},xticklabels={Aug 9,Aug 16,Aug 23,Aug 30,Sep 6,Sep 13,Sep 20,Sep 27},xlabel={day (2026, d4c4e1f8 and earlier)},ylabel={commits}]
\addplot[fill=vibeyblue,draw=none] coordinates {(0,5) (1,41) (3,21) (4,130) (5,27) (6,92) (7,47) (8,22) (9,39) (10,20) (11,52) (12,75) (13,13) (14,61) (15,1) (16,38) (17,3) (18,56) (19,29) (20,91) (21,71) (31,3) (32,13) (36,24) (37,61) (38,33) (39,16) (40,191) (41,7) (42,4) (43,3) (47,1) (51,13) (52,16)};
\node[vibeyanchor,fill=vibeygold] at (axis cs:7,53) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:7,56) {v0.1.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:11,58) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:11,61) {v0.1.1--v0.1.2};
\node[vibeyanchor,fill=vibeygold] at (axis cs:15,7) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:15,10) {v0.2.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:20,97) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:20,100) {v0.3.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:21,77) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:21,80) {v0.4.0--v0.5.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:36,30) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:36,33) {v0.6.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:37,67) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:37,70) {v0.7.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:38,39) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:38,42) {v0.8.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:40,197) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:40,200) {v1.0.0--v1.3.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:41,13) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:41,16) {v1.4.0--v1.5.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:43,9) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:43,12) {v2.0.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:51,19) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:51,22) {v3.0.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:52,22) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:52,25) {v3.1.0};
\draw[decorate,decoration={brace,amplitude=3pt},vibeygray] (axis cs:22,6) -- (axis cs:30,6);
\node[vibeynote,anchor=south] at (axis cs:26.0,10) {9 days without a commit};
\node[vibeycallout,anchor=east] at (axis cs:39.4,185) {191 on Sep 18};
\node[vibeynote,anchor=north west,align=left] at (axis description cs:0.01,0.97) {\textcolor{vibeygold}{$\bullet$} vibey release tag};
\end{axis}
\end{tikzpicture}
\caption{Commits per day since 2026-08-09, when the family's own development begins, read at revision d4c4e1f8: 1,319 commits on 34 active days, with the busiest day at 191. Gold marks are the 19 \texttt{vibey} release tags in the window; the brace marks the longest pause.}
\label{fig:commits-daily}
\end{figure*}
```
<!-- END GENERATED figure:commits-daily -->

The circadian rhythm, weekday distribution, and Conventional Commit types are captured in [Fig. 28](#fig:commit-rhythm).

<!-- BEGIN GENERATED figure:commit-rhythm rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{scope}[xshift=-5.4cm]
\draw[vibeyline] (0,0) circle (0.591); \draw[vibeyline] (0,0) circle (1.181); \draw[vibeyline] (0,0) circle (1.772);
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (90:1.063) arc[start angle=90,end angle=75,radius=1.063] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (75:1.181) arc[start angle=75,end angle=60,radius=1.181] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (60:2.055) arc[start angle=60,end angle=45,radius=2.055] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (45:1.299) arc[start angle=45,end angle=30,radius=1.299] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (30:1.819) arc[start angle=30,end angle=15,radius=1.819] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (15:0.662) arc[start angle=15,end angle=0,radius=0.662] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (0:0.921) arc[start angle=0,end angle=-15,radius=0.921] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-15:0.638) arc[start angle=-15,end angle=-30,radius=0.638] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-30:0.591) arc[start angle=-30,end angle=-45,radius=0.591] -- cycle;
\fill[vibeyred!70,draw=white,line width=.4pt] (0,0) -- (-45:0.496) arc[start angle=-45,end angle=-60,radius=0.496] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-60:1.229) arc[start angle=-60,end angle=-75,radius=1.229] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-75:1.205) arc[start angle=-75,end angle=-90,radius=1.205] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-90:1.394) arc[start angle=-90,end angle=-105,radius=1.394] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-105:1.772) arc[start angle=-105,end angle=-120,radius=1.772] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-120:1.796) arc[start angle=-120,end angle=-135,radius=1.796] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-135:1.748) arc[start angle=-135,end angle=-150,radius=1.748] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-150:0.969) arc[start angle=-150,end angle=-165,radius=0.969] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-165:1.819) arc[start angle=-165,end angle=-180,radius=1.819] -- cycle;
\fill[vibeygold,draw=white,line width=.4pt] (0,0) -- (-180:2.150) arc[start angle=-180,end angle=-195,radius=2.150] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-195:1.630) arc[start angle=-195,end angle=-210,radius=1.630] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-210:1.418) arc[start angle=-210,end angle=-225,radius=1.418] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-225:1.630) arc[start angle=-225,end angle=-240,radius=1.630] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-240:1.087) arc[start angle=-240,end angle=-255,radius=1.087] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-255:0.591) arc[start angle=-255,end angle=-270,radius=0.591] -- cycle;
\node[vibeynote,text=vibeygray] at (82.5:2.42) {0}; \node[vibeynote,text=vibeygray] at (37.5:2.42) {3}; \node[vibeynote,text=vibeygray] at (-7.5:2.42) {6}; \node[vibeynote,text=vibeygray] at (-52.5:2.42) {9}; \node[vibeynote,text=vibeygray] at (-97.5:2.42) {12}; \node[vibeynote,text=vibeygray] at (-142.5:2.42) {15}; \node[vibeynote,text=vibeygray] at (-187.5:2.42) {18}; \node[vibeynote,text=vibeygray] at (-232.5:2.42) {21};
\node[vibeynote,anchor=north,text=vibeygray,align=center] at (0,-2.62) {rings at 25, 50 and 75 commits\\[1pt]\textcolor{vibeygold}{$\blacksquare$} busiest 18:00 (91) \quad \textcolor{vibeyred!70}{$\blacksquare$} quietest 09:00 (21)};
\end{scope}
\begin{axis}[vibeybars,at={(0.0cm,2.7cm)},anchor=north west,width=5.3cm,height=5.2cm,bar width=9pt,xmin=-0.6,xmax=6.6,ymin=0,
  xtick={0,...,6},xticklabels={Mon,Tue,Wed,Thu,Fri,Sat,Sun},title={b. Commits by weekday},ylabel={commits},enlarge y limits={upper,value=0.12},title style={name=weekdaystitle}]
\addplot[fill=vibeyblue,draw=none] coordinates {(0,91) (1,151) (2,96) (3,267) (4,323) (5,203) (6,188)};
\end{axis}
\begin{axis}[vibeybars,at={(6.1cm,2.7cm)},anchor=north west,width=5.3cm,height=5.2cm,bar width=9pt,xmin=-0.6,xmax=7.6,ymin=0,
  xtick={0,...,7},xticklabels={chore,other,fix,feat,docs,ci,test,refactor},x tick label style={rotate=45,anchor=north east,font=\sffamily\tiny},title={c. Conventional Commit types},ylabel={commits},enlarge y limits={upper,value=0.12}]
\addplot[fill=vibeyteal!85,draw=none] coordinates {(0,374) (1,259) (2,253) (3,241) (4,111) (5,39) (6,23) (7,8)};
\end{axis}
% The clock's title shares the bar charts' title baseline, so the three panels read as one row.
\node[vibeyhead,anchor=base west] at (-8.0,0 |- weekdaystitle.base) {a. Commits by hour, US Eastern};
\end{tikzpicture}
\caption{The rhythm of production since 2026-08-09, at revision d4c4e1f8. (a) A 24-hour clock of commits in US Eastern time: every hour of the day carries commits, the busiest at 18:00 with 91 and the quietest at 09:00 with 21. (b) The weekday distribution. (c) The Conventional Commit types the pre-commit hook enforces, most common first.}
\label{fig:commit-rhythm}
\end{figure*}
```
<!-- END GENERATED figure:commit-rhythm -->

Cumulative deliveries, including the absorbed package roots and pull requests, appear in [Fig. 29](#fig:cumulative-commits).

<!-- BEGIN GENERATED figure:cumulative-commits rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=17.2cm,height=5.4cm,xmin=0,xmax=52,ymin=0,ymax=1399,
  xtick={0,7,14,21,28,35,42,49},xticklabels={Aug 9,Aug 16,Aug 23,Aug 30,Sep 6,Sep 13,Sep 20,Sep 27},xlabel={day},ylabel={cumulative},legend pos=north west]
\addplot[fill=vibeyblue!14,draw=none,forget plot] coordinates {(0,0) (0,5) (1,46) (2,46) (3,67) (4,197) (5,224) (6,316) (7,363) (8,385) (9,424) (10,444) (11,496) (12,571) (13,584) (14,645) (15,646) (16,684) (17,687) (18,743) (19,772) (20,863) (21,934) (22,934) (23,934) (24,934) (25,934) (26,934) (27,934) (28,934) (29,934) (30,934) (31,937) (32,950) (33,950) (34,950) (35,950) (36,974) (37,1035) (38,1068) (39,1084) (40,1275) (41,1282) (42,1286) (43,1289) (44,1289) (45,1289) (46,1289) (47,1290) (48,1290) (49,1290) (50,1290) (51,1303) (52,1319)} \closedcycle;
\addplot[vibeyblue,line width=1pt] coordinates {(0,0) (0,5) (1,46) (2,46) (3,67) (4,197) (5,224) (6,316) (7,363) (8,385) (9,424) (10,444) (11,496) (12,571) (13,584) (14,645) (15,646) (16,684) (17,687) (18,743) (19,772) (20,863) (21,934) (22,934) (23,934) (24,934) (25,934) (26,934) (27,934) (28,934) (29,934) (30,934) (31,937) (32,950) (33,950) (34,950) (35,950) (36,974) (37,1035) (38,1068) (39,1084) (40,1275) (41,1282) (42,1286) (43,1289) (44,1289) (45,1289) (46,1289) (47,1290) (48,1290) (49,1290) (50,1290) (51,1303) (52,1319)};
\addlegendentry{commits since Aug 9 (1,319; 12 earlier)}
\addplot[vibeyteal,line width=1pt] coordinates {(0,0) (0,0) (1,7) (2,7) (3,9) (4,20) (5,20) (6,31) (7,47) (8,69) (9,104) (10,124) (11,145) (12,181) (13,188) (14,218) (15,218) (16,242) (17,244) (18,281) (19,304) (20,373) (21,426) (22,426) (23,426) (24,426) (25,426) (26,426) (27,426) (28,426) (29,426) (30,426) (31,426) (32,426) (33,426) (34,426) (35,426) (36,434) (37,451) (38,483) (39,494) (40,501) (41,505) (42,508) (43,511) (44,511) (45,511) (46,511) (47,511) (48,511) (49,511) (50,511) (51,524) (52,538)};
\addlegendentry{commit subjects closing a pull request (538)}
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:0,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:1,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:4,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:4,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:4,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:5,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:12,0) {};
\node[vibeyanchor,fill=vibeyviolet] at (axis cs:13,0) {};
\node[vibeynote,anchor=south east,align=right] at (axis description cs:0.99,0.04) {\textcolor{vibeyviolet}{$\bullet$} a package's root commit: 8 of 9 root histories begin in the window};
\end{axis}
\end{tikzpicture}
\caption{Cumulative production at revision d4c4e1f8: commits since 2026-08-09 and, beneath them, the commits whose subject closes a pull request. The violet marks on the baseline are the days on which the absorbed packages' own histories begin; the family was written as several repositories and merged into one tree with every history preserved.}
\label{fig:cumulative-commits}
\end{figure*}
```
<!-- END GENERATED figure:cumulative-commits -->

The timeline of releases across each package in the family is shown in [Fig. 30](#fig:release-cadence).

<!-- BEGIN GENERATED figure:release-cadence rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\draw[vibeydashed] (5.48,-0.30) -- (5.48,0.35);\node[vibeynote,anchor=north] at (5.48,-0.32) {Sep 2026};
\node[vibeynote,anchor=north] at (0.00,-0.32) {Aug 16};
\node[vibeynote,anchor=north] at (15.40,-0.32) {Sep 30};
\draw[vibeyline,line width=.5pt] (0,0.00) -- (15.40,0.00);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,0.00) {vibey};
\node[vibeyanchor,fill=vibeyblue] at (0.00,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (0.02,0.06) {0.1.0};
\node[vibeyanchor,fill=vibeyblue] at (1.37,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (1.37,-0.09) {2};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (1.39,0.06) {0.1.1--0.1.2};
\node[vibeyanchor,fill=vibeyblue] at (2.74,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (2.76,0.06) {0.2.0};
\node[vibeyanchor,fill=vibeyblue] at (4.45,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (4.47,0.06) {0.3.0};
\node[vibeyanchor,fill=vibeyblue] at (4.79,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (4.79,-0.09) {2};
\draw[vibeyline] (4.79,0.06) -- (4.79,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (4.81,0.48) {0.4.0--0.5.0};
\node[vibeyanchor,fill=vibeyblue] at (9.92,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (9.94,0.06) {0.6.0};
\node[vibeyanchor,fill=vibeyblue] at (10.27,0.00) {};
\draw[vibeyline] (10.27,0.06) -- (10.27,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (10.29,0.48) {0.7.0};
\node[vibeyanchor,fill=vibeyblue] at (10.61,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (10.63,0.06) {0.8.0};
\node[vibeyanchor,fill=vibeyblue] at (11.29,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (11.29,-0.09) {4};
\draw[vibeyline] (11.29,0.06) -- (11.29,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (11.31,0.48) {1.0.0--1.3.0};
\node[vibeyanchor,fill=vibeyblue] at (11.64,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (11.64,-0.09) {2};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (11.66,0.06) {1.4.0--1.5.0};
\node[vibeyanchor,fill=vibeyblue] at (12.32,0.00) {};
\draw[vibeyline] (12.32,0.06) -- (12.32,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (12.34,0.48) {2.0.0};
\node[vibeyanchor,fill=vibeyblue] at (15.06,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (15.08,0.06) {3.0.0};
\node[vibeyanchor,fill=vibeyblue] at (15.40,0.00) {};
\draw[vibeyline] (15.40,0.06) -- (15.40,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (15.42,0.48) {3.1.0};
\end{tikzpicture}
\caption{Every release tag created by the time of revision d4c4e1f8, 19 tags on the repository; a tag is selected by its date, not by whether the revision's history reaches it. The 19 \texttt{vibey} releases run from vibey-v0.1.0 on 2026-08-16 to vibey-v3.1.0 on 2026-09-30; since the packages were absorbed into one tree, one version number ships the whole family, and the packages' earlier tags were never carried into this repository, whose pre-absorption repositories have since been removed.}
\label{fig:release-cadence}
\end{figure*}
```
<!-- END GENERATED figure:release-cadence -->

Finally, the architectural shape of the consolidated repository across its ten packages and the orchestrator's layers is depicted in [Fig. 31](#fig:codebase-shape).

<!-- BEGIN GENERATED figure:codebase-shape rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=3 by 1,horizontal sep=1.9cm},vibeyaxis,height=5.6cm,
  y dir=reverse,ytick={0,...,9},ymin=-0.7,ymax=9.7,xmin=0,y tick label style={font=\sffamily\tiny},
  scaled x ticks=false,x tick label style={/pgf/number format/fixed},point meta=x,
  nodes near coords,every node near coord/.append style={font=\sffamily\tiny,text=vibeygray,/pgf/number format/fixed}]
\nextgroupplot[title={a. Lines of Python per package},xbar,bar width=6pt,width=5.9cm,yticklabels={vibey,vibey-gh,claudeloop,vibey-bootstrap,agyloop,codexloop,cursorloop,qwenloop,vibey-skills,runners-common},xlabel={lines},xmax=207182]
\addplot[fill=vibeyblue,draw=none] coordinates {(165746,0) (81654,1) (36869,2) (32784,3) (23972,4) (22614,5) (16750,6) (11151,7) (3109,8) (258,9)};
\nextgroupplot[title={b. Test functions per package},xbar,bar width=6pt,width=4.9cm,yticklabels={,,,,,,,,,},xlabel={tests},xmax=5549]
\addplot[fill=vibeyteal!85,draw=none] coordinates {(4439,0) (2197,1) (1478,2) (972,3) (678,4) (711,5) (562,6) (301,7) (33,8) (0,9)};
\nextgroupplot[title={c. The orchestrator's layers},xbar,bar width=6pt,width=4.9cm,ytick={0,...,4},yticklabels={domain,application,infrastructure,cli,tui},ymin=-0.7,ymax=4.7,xlabel={lines},xmax=49434,nodes near coords={}]
\addplot[fill=vibeyviolet!85,draw=none] coordinates {(14813,0) (15080,1) (26018,2) (7497,3) (594,4)};
\node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:15713,0) {14,813 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:15980,1) {15,080 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:26918,2) {26,018 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:8397,3) {7,497 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeysilver!30,text=vibeygray] at (axis cs:1494,4) {594 $\cdot$ exempt};
\end{groupplot}
\end{tikzpicture}
\caption{The shape of the tree at revision d4c4e1f8: 420,679 lines of Python in 2,364 files and 11,384 test functions. (a) Lines and (b) test functions per package, each package counted together with the test suite its pytest configuration collects, \texttt{vibey}'s in the top-level \texttt{tests/}; \texttt{runners-common} has no test functions at this revision. (c) The orchestrator's layers, four of which fail the build below 100\% branch coverage.}
\label{fig:codebase-shape}
\end{figure*}
```
<!-- END GENERATED figure:codebase-shape -->

### The measured regularity

**Observed regularity.** On a fixed substrate, with hardware, model, serving stack,
deadline and admission rule held constant, once offered load saturates the substrate
the rate of successful output lies in a bounded band that depends on the substrate
and only weakly on the quantity of work offered. In the record, across the nine rungs
from $N = 2$ to $N = 32$ (107 generations, 102 succeeded, 95.3%, and every rung at or
above 87.5%), throughput stayed between 0.99 and 2.00 per minute, with mean 1.38 and
sample standard deviation 0.33, while offered concurrency rose sixteen-fold. The
least-squares slope of log throughput on $\log N$ over those rungs is 0.20; output
that scaled with demand would have slope 1.

The band is a band, not a constant. Its spread is a quarter of its mean, and it drifts
upward with $N$, because the server batches concurrent sequences into shared forward
passes. It holds only inside the region. Below it, the serial rung ran at 0.36 per
minute: one job cannot saturate the substrate. Above it, throughput
peaked at 3.52 per minute at $N = 96$, but only 55.2% of generations succeeded, and at
$N = 128$ success collapsed to 18.0% while throughput fell back to 1.53.

**A held-out check.** A band fitted on the rungs with $N \leq 16$ is $[0.99, 1.72]$.
Of the two stable rungs held out, $N = 24$ (1.40) fell inside and $N = 32$ (2.00) fell
16% above. The floor held; the ceiling was exceeded once, in the direction that
continuous batching predicts. We therefore claim the floor and the scale of the
ceiling, not a tight window.

**A correction.** The `vibey-gh` tenant paper reported this experiment as 61
generations at a success rate of 1.00, with throughput held to $1.4 \pm 0.25$ per
minute and latency growing linearly at 22 s per added job through $N = 12$, then
superlinearly at 59 s per job by $N = 16$. None of these survives comparison with the
record. No contiguous run of rungs totals 61 generations, whether counted as attempted
or as succeeded; four of the nine stable rungs lie outside $1.4 \pm 0.25$; and the
record itself fitted both latency models during the run and falsified both. The
tenant paper now carries the figures above, with a dated correction note.

### Commodity production and scarce governance

**Thesis.** For a bounded task class, on a fixed substrate, under a fixed governance
regime, production behaves as a commodity: its executors are substitutable, its units
are priced, and its rate is set by the substrate rather than by demand. What the same
records do not show as a commodity is governance, meaning the authority to decide,
fund, accept and ratify, and correct judgment about what was produced.

The first half rests on three observations. Substitutability is a property of the
design: seven engine identities implement one contract, the scheduler chooses among them by
policy, and the live runbook forces a rotation between two of them in the middle of a
project. Price is explicit: every engine descriptor carries per-token cost rates, and
budgets are sums of reported cost. The rate is the regularity above.

The second half rests on what stopped work. The stress run's collapse was the
substrate's bound being exceeded, not a malfunction. At the break, the harness's heal
probe recorded `lane responsive; no heal needed`: the lane was healthy and simply
could not do that much work before the deadline. Every remedy (less concurrency, a longer deadline, more
hardware) is a decision the operator makes, and the deadline is itself a governance
parameter: moving it moves the band. The record's lasting correction was a governance
rule, too: admission should gate on payload size, not on concurrency count. ADR-0035
records the same shape inside the orchestrator. A review-independence rule, made
absolute in two places, deadlocked BUILD on a one-engine pool, deferring the same job
forever with nothing in the ledger. Capacity to produce was present; a rule stopped
it; the repair was a decision about the rule.

Judgment is the other scarce input, and we do not claim that governance is the only
one. The design already treats judgment as scarce: ADR-0035 calls an engine grading
its own work the weakest possible check, the release calculus separates the
credential that judges from the one that acts, and every human gate requires an
explicit verdict rather than an absence of objections. The records show why. The
exact-head violation was automation acting correctly on a stale verdict. The figures
corrected above were a confident, wrong claim that stood unchallenged in a tracked
paper from the day its package was imported until this revision checked it against
the record. Artifacts are commoditised; correct judgment about artifacts is not, and
that gap, more than throughput, is where the remaining engineering lies.

**Review before merge is a rate limiter, and it is meant to be.** On 2026-09-24 every
change for 3.0.0 was sent for an independent review, and merging outran the reviews.
The 3.0.0 release-gate record (12:22Z, not tracked) counts seven pull requests merged
before or during their independent reviews that day; the forge's own times, read again
for this revision, show how long each was open, from creation to merge.

| Pull request | Open for |
|---|---:|
| #1094, sovereign reviewer | 49 min 44 s |
| #1095, derived lane | 44 min 6 s |
| #1100, ledger guard | 35 min 16 s |
| #1101, cut prompts | 23 min 4 s |
| #1102, truncated log | 30 s |
| #1103, lane follow-ups | 1 min 48 s |
| #1105, push-gate reaper | 3 min 49 s |

Two earlier merges that day, outside that count, had shown the pattern: #1089 merged
30 s after it was opened and was reviewed afterwards (#1092), and #1092 merged while
its final review said *not yet* (#1102). The findings did not disappear. Each was
carried into a new pull request or branch: #1092 for #1089, #1101 for #1094, #1102 for
#1092, #1103 for #1095, and a follow-up branch for #1100. In the meantime each finding
was live on `develop`, which a push publishes to the development package index; the
worst were the two high findings in the ledger guard. Merging ahead of review also let
two changes that each passed their own gates break `develop` together: #1100 made the
suite run as a restricted application role, #1103 added a test that needs the owner's
privileges, and nothing tested the two together before both had landed (CI run
35998404322 at `600f3db2`: 1 failed, 3,732 passed; the two-line repair merged as
#1109; on `develop` the whole episode now sits inside the 3.0.0 squash, #1244, and
`600f3db2` is held by the tag `paper-figures/3.0.0`). And it created pressure to repair
in place. A later commit on the job queue's branch rewrote migration 0015 to make it
additive after 0015 had merged; a pull request (#1106) carried it at the cutoff, and it
was closed unmerged at 13:24Z that day. #1103 took the other road: it left 0015 as it
was, because a push to `develop` publishes a build that may already have applied it
and the migrator refuses a changed checksum, and it recorded the drain instruction and
the gap in ADR-0054, with a new lint that fails any undocumented column drop. A
migration that may have been applied is never edited; its correction is a new
migration or a recorded gap.

The same day supplied a second governance fact, about where work is kept. At about
09:09 US Eastern time the host rebooted. Everything held only in the operating system's
temporary directory, which macOS empties at boot, was lost: the storm's local run logs and
progress log, from which the audit above was computed, and every worktree kept there,
with its uncommitted edits, among them the first draft of this very update of the
paper. What survived is what had been committed and pushed, or tracked: the evidence
ledger, the benchmark record and every merged pull request. Worktrees moved to a
persistent directory, and work in progress is now committed and pushed section by
section. It is sub-doctrine 10.h's argument, observed: evidence that is not durably
recorded is not evidence for long.

None of this is a claim about anyone's care. It is the finding of this section,
observed on governance itself. Producing the changes was cheap and fast that day;
independent judgment about them took tens of minutes each and was the binding input,
and wherever a merge ran ahead of it the judgment was still paid for, later, as a
rescue pull request, a red integration branch or a finding shipped to the development
channel. Review before merge limits the rate of delivery in the same sense the stress
band limits the rate of generation, and it binds for the same reason: it is the step
that decides whether the output is correct.

### The autonomy scan of 2026-09-30

On 2026-09-30 the operator asked how close the system was to running on its own. A scan
read `develop` at `15e909d4c` (#1290) that day with four parallel code reviews, of the
product pipeline, runtime resilience, the self-development loop and the safety
controls, and with live evidence from the forge and the local queue database. Its page,
*vibey Autonomy Scan*, is kept outside the repository. We read every figure below again
for this revision: from the forge on 2026-10-01 (captured at 11:39:49Z), from the code
at `15e909d4c`, and from the review lane's run records. The tracked record
`docs/architecture/evidence/autonomy-2026-10-01.md` holds the queries and their output,
with two JSON records beside it. One of the scan's readings did not survive the second
reading, and we say which.

**Only BUILD ran without a person.** At `15e909d4c` one phase of the six carried a
project forward with nobody present: BUILD, whose per-job rotation, retries, circuit
breakers and no-loss gate were wired and working. DESIGN parks its interview and its
acceptance for a person unless the bridge is told to answer with defaults. REVIEW's
approval and deployment-choice gates wait for a person by design, and nothing answered
them, so a project could not reach DONE unattended. And a gate's stored
`default_answer` and `timeout_at` were acted on by nothing: `vibey gates` printed the
time (`src/vibey/cli/gates.py:108`) and no code compared it with the clock, so an
unanswered gate waited forever. Part of this is the model working as designed, since
sub-doctrine 12.d bounds unattended authority by a gate and REVIEW's gate is one. The
rest was defects.

**The forge.** The integration branch shows the same thing from the other side.

```latex
\begin{table}[t]
\centering\small
\begin{tabular}{@{}p{1.75in}p{1.45in}@{}}
\textbf{Measure, read 2026-10-01} & \textbf{Value}\\
The 40 pull requests merged into \texttt{develop} up to \#1290 (\#1226 to \#1290) & 0 reviewed; all 40 merged by the operator's account\\
What both \texttt{develop} rulesets require & one approving review; their bypass actors may bypass \emph{always}\\
Rule-suite evaluations of pushes to \texttt{develop}, the week to capture & 280, every one by the operator's account and every one a bypass\\
Reviews by the delegated approver's account (\texttt{thevibeyproject}, write role) & 0\\
PR review, the 15 runs created before 2026-10-01T00:00Z & 10 failed (9 in the sovereign diff review), 3 succeeded, 2 cancelled\\
Merge train, the 30 runs created before 2026-10-01T00:00Z & 22 dispatched, 7 after a review run, 1 on its schedule\\
\end{tabular}
\caption{The forge's record of who merged into the integration branch, read on 2026-10-01 at 11:39:49Z. The queries and their output are in the tracked evidence record of 2026-10-01.}
\label{tab:autonomy-forge}
\end{table}
```

Every merge into the integration branch in that window was the operator's, made through
the ruleset bypass: a merge with no review cannot satisfy a rule that requires one, and
the forge records each push as a bypass. The storm audit above found that no lane
reached `develop` without a human step; the scan finds the same of the product's own
loop. The delegated approver of sub-doctrine 12.f existed, with its grant enabled, and
no workflow called it. The scan read the 22 dispatched merge-train runs as started by
hand. They were not. Each names `github-actions[bot]` as its triggering actor, because
the PR-review workflow dispatches the train itself once its gate is green
(`gh workflow run merge-train.yml` in `.github/workflows/pr-review.yml`). The merges were made by
hand; the train's runs were not. It is the storm audit's lesson at a smaller scale: a
capable first reading of complete records was wrong on a headline figure, and going
back to the source, not the analysis, caught it.

**Seven gaps in the code.** The code reviews found these at `15e909d4c`. Each was
checked at that revision, and each repair is named with its state at this one.

```latex
\begin{table*}[t]
\centering\small
\begin{tabular}{@{}p{3.15in}p{2.75in}p{0.7in}@{}}
\textbf{Gap at \texttt{15e909d4c}} & \textbf{Repair} & \textbf{At \texttt{4acb9be5c}}\\
REVIEW was shown evidence nobody measured: \texttt{review.demo} was queued with no payload (\texttt{build\_integrate\_handler.py:187}), and its handler fell back to a JUnit report of \texttt{failures='0'} and a coverage file claiming 100\% (\texttt{review\_demo\_handler.py:42,104}) & \#1294: each integration ledgers every verification command, its exit code and its output tail; REVIEW renders only that record, and coverage is never claimed & merged\\
The evidence guards on BUILD to REVIEW and REVIEW to DONE (\texttt{phase.py:239,262}) were reached only from tests, and BUILD to REVIEW was a bare compare-and-set & none yet; \#1294 names it a follow-up, since nothing produces the first guard's inputs & open\\
A paid engine's login was trusted only while younger than 24 hours (\texttt{engine\_selector.py:36}) and refreshed only at startup or by \texttt{vibey doctor}, so after a day every job that needed a paid engine was deferred every five minutes, indefinitely & \#1295: an ageing login is rechecked at half its life, a failing one at most every 15 minutes & merged\\
A BUILD session had no wall-clock limit (\texttt{build\_engine\_run.py}), and the worker's heartbeat kept its lease alive & \#1296: stopped at 240 minutes by default and failed as an engine fault & merged\\
\texttt{stop()} terminated the runner alone, in the worker's own process group, inside a bare \texttt{except} (\texttt{loop\_process\_adapter.py:654}) & \#1297: each session leads its own process group, which the stop ends & merged\\
No work item's worktree was ever removed: the removal methods (\texttt{worktree\_manager.py:121,191}) had no callers & \#1298: retired after a clean integration & open pull request\\
A gate's \texttt{timeout\_at} and \texttt{default\_answer} were stored and shown (\texttt{cli/gates.py:108}) and acted on by nothing & \#1299: a gate times out only where a project declares its kind & merged\\
\end{tabular}
\caption{Seven gaps the scan's code reviews found at \texttt{15e909d4c}, each checked again at that revision, with its repair and the repair's state at \texttt{4acb9be5c}. Paths are under \texttt{src/vibey}; the evidence record of 2026-10-01 gives every file and line.}
\label{tab:autonomy-gaps}
\end{table*}
```

Three of the seven are failures of evidence, not of capacity: a review shown numbers
nobody measured, guards nobody asked, and a deadline nobody read. Sub-doctrine 10.f names
the first exactly, since a marker is never evidence of completion, and every human
REVIEW in production had been shown one. The gate timeouts took a ruling, not just a
fix. Defaulting every gate on timeout would make silence consent, which 12.d forbids,
and some defaults act for the operator: `deploy_demo_review` defaults to `approve`. The
operator ruled on 2026-09-30 that a gate times out only where a project declares its
kind under `[human_gates] timeout_defaults` (#1299). The declaration is the consent, the
table is empty by default, and REVIEW's `approval` has no default and never times out.
Three further changes prepared the approver to run unattended. #1300 declared the
operator's standing grant in `.vibey-gh.toml` (`[autonomy]`), with what it never covers:
`--admin`, `--no-verify`, a force-push or a direct write to a permanent branch, approving
its own pull request, an irreversible real-world act without a person, and ratifying a
change to the canon. #1302 added 21 paths to the approver's forbidden list, among them
what the review gate measures, what an engine may see, and the code and tests that hold
the non-negotiables, for 72 in all. #1303 gave the sovereign review the files it judges,
below. Every one of these repairs merged through the bypass the table records, so at
this revision the repairs are themselves evidence of the gap they address.

**A merge train that closed what it merged.** `develop` allows auto-merge and requires
an approving review. With the approval missing, `gh pr merge --squash` does not fail: it
enables auto-merge and exits 0. The merge train's `merge()` read that exit as a merge,
printed `merged 1`, and deleted the head branch, and the forge then closed the pull
request. Between 01:24Z and 06:47Z on 2026-10-01 this closed six pull requests eight
times: #1295 and #1298 twice each, and #1293, #1301, #1302 and #1297 once. #1301 was the fix
for this very defect. Each closure shows the same four events within four seconds
(`auto_merge_enabled`, `closed`, `auto_merge_disabled`, `head_ref_deleted`), 16 to 24
seconds after a merge-train run started, and
`gh api repos/the-vibey-project/vibey/issues/<n>/events` reproduces them. Every branch
was restored and every pull request reopened, the last at 09:17Z. No
`head_ref_force_pushed` event appears on any of the six, which is what restoring each at
the head it had when it was closed would leave. #1301 merged at 09:27:44Z: after any
`gh pr merge` that exits 0, `merge()` now reads the pull request's state and counts only
`MERGED`, and an `OPEN` one is reported as queued and left alone, branch included. In the
storm audit the train logged *merged 0* on every pass; here it logged a merge that had
not happened. Sub-doctrine 12.e names the failure: automation that reports a success it
did not observe.

**The review lane, measured.** Nine of the ten failed review runs failed in the
sovereign reviewer (#1086), `gpt-oss:20b` on the operator's machine, which answers the
whole review because no paid lane is declared (8.b). The model server's own log, which
is not tracked, shows why. From 09:00 to 15:00 US Eastern on 2026-09-30, the window of
those runs, fifteen requests with prompts of 32,273 to 47,181 tokens were cut off after
ten minutes, the limit the review workflow sets, having generated 5,353 to 11,755 tokens
(median 7,789). The eighteen requests with prompts of at least 30,000 tokens that
finished on 2026-09-30 and 2026-10-01 generated a median of 2,661. The requests were not
stuck: they were still generating, at about three times the length of a finished answer,
when time ran out. Why nothing stopped them sooner, and how the lane now bounds them,
#1316 found later the same day; the section on exact-head evaluation gives both.

To find what would let the reviewer finish, and whether its verdicts held when it did,
eight merged pull requests were replayed at their exact heads, one run each. Each run
used the workflow's own arguments except a 900-second limit and no retry. The gate had
passed four of them (#1274, #1287, #1289, #1295) and blocked four (#1267, #1272, #1276,
#1277).

```latex
\begin{table}[t]
\centering\small
\begin{tabular}{@{}p{1.05in}p{0.55in}p{0.65in}p{0.7in}@{}}
\textbf{Setting} & \textbf{Verdicts} & \textbf{The 4 the gate passed} & \textbf{The 4 it blocked}\\
\texttt{think=low}, diff only & 8 of 8 & passed 4 & passed 4\\
\texttt{think=medium}, diff only & 5 of 8 & passed 3 & failed 2\\
default effort, with the changed files' full text (\#1303) & 8 of 8 & passed 4 & passed 3, failed 1\\
\end{tabular}
\caption{The sovereign reviewer replayed on eight merged pull requests at their exact heads, one run each, with the workflow's arguments except a 900-second limit and no retry. \emph{Diff only} means the diff and the declared documents. The runs are in the tracked review-lane record of 2026-10-01.}
\label{tab:review-lane}
\end{table}
```

Low effort finished, and it passed everything, including the four the gate had blocked:
a rubber stamp. Medium effort agreed with the gate wherever it answered, but it failed
to answer three times in eight: once at the time limit, and twice out of room after more
than 61,000 characters of reasoning, with no answer.

The gate's blocks did not deserve that agreement. We checked its eight findings on the
four blocked pull requests against the files at the reviewed heads, and seven name
something the file contains:

- `math` imported at `config.py:45`, and `rulesets as rs` and the `INTEGRATION` and `RELEASE` constants defined in the very test files said to lack them (#1277);
- the string "draining on SIGTERM", printed at `src/vibey/cli/main.py:1919` (#1272, twice);
- a test body that is present (#1276).

Six of the seven name lines outside the diff's hunks, which the reviewer was never shown.
#1276's is in a function the diff adds, and we did not establish why the reviewer missed
its body. The eighth, a missing configuration example on #1267, we did not adjudicate.

The fix was therefore not less thought but more sight. #1303 gives the reviewer the full
text at the head of each file the diff changes, as reference only. At default effort
with those files, the reviewer reached a verdict on all eight, and none of the seven
false findings came back. One new finding remained, that #1272's drain on SIGTERM is
undocumented, and we did not adjudicate it either.

The limits are these. Each setting ran once per pull request, so nothing here measures
repeatability. No pull request in the sample carries a known-true defect, so the lane's
recall is unmeasured: we have not shown whether it blocks a real defect, with the files
or without them, and agreement with the gate is agreement, not correctness. The review
canary has since measured recall on small planted defects (under
*Exact-head evaluation*); on large diffs it is still unmeasured. The replays
allowed 900 seconds where the workflow allows 600, and two of the eight source-context
runs took longer (678 s and 872 s). Under the workflow as it then stood, those attempts
would have ended without a verdict and gone to its one retry; since #1316 its limit grows
with the request and is never under 600 s. The study's records were first kept only in
the session's scratch space. Sub-doctrine 10.h is why they are now tracked beside the
scan's (`docs/architecture/evidence/review-lane-2026-10-01.json`).

**One file every pull request edits.** Every change edits the same `## [Unreleased]`
lines of `CHANGELOG.md`, so any two open pull requests conflict. `.gitattributes`
declared `CHANGELOG.md merge=union` to absorb that. But the forge computes mergeability
without running a custom merge driver (#1305), so a pull request shows as conflicting
even when a local merge is clean, and where the driver does run it keeps both sides and
can duplicate an entry. The four fixes #1295, #1297, #1298 and #1299 each edit
`CHANGELOG.md`, and together they carry ten commits that merge `develop` in, against four
of their own. #1305, open at `4acb9be5c` and merged later that day, replaces the union
merge with fragments: each change adds its own file, `changelog.d/<slug>.<type>.md`, which no other change names,
the release folds them in, and CI checks them.

**After the scan's revision.** The two repairs the table shows open at `4acb9be5c` merged
later on 2026-10-01, #1298 at 12:06Z and #1305 at 12:09Z. Three further defects surfaced
the same day. One was in a repair. #1297's stop ends every engine session at shutdown by
awaiting a reap of each process in a registry shared by the whole module, and an entry
registered under another event loop cannot be awaited from this one, so shutdown raised
and a clean exit became exit 1; `develop`'s gates job failed intermittently on it until
#1309 ended each session on its own and made the call unable to raise. The second was
older: the reconciler's revoke of the replication role lost a race across databases and
swallowed the failure (#1310, #1314, under *Enforcement, and what it does not cover*).
CI, not a review, found both. The third was the review lane's, whose timeouts had a cause
the measurement above did not reach (#1316, under *Exact-head evaluation*). The forge's
record of who merges did not change. The fourteen pull requests merged into `develop`
after `4acb9be5c`, up to #1319 at `2b17eb71`, were all merged by the operator's account and
none carries a review (read on 2026-10-01 at 20:41Z), so each went in through the bypass,
the revision of this paper before the last (#1307) among them. So did the twenty-one after
them, #1321 to #1341, up to `ca9e47452` (read on 2026-10-02 at about 03:50Z), the
previous revision (#1324) and every change this revision reports among them; #1334 was
merged at 02:40Z, half an hour before its sovereign review ended without a verdict. The ten
after those, from the paper's 3.3.0 revision (#1342) and the 3.3.0 promotion into `main`
(#1343) to #1354, up to `3bb577a4e`, went in the same way: each merged by the operator's
account with no review (read on 2026-10-02 at about 11:10Z).

**The scan, repeated weekly.** The scan was one reading. Since this revision its questions
are asked again each week by `scripts/autonomy_scorecard.py`. It declares the stages of the
delivery loop in `scripts/autonomy_scorecard.toml`, each with the figures that judge it and
the threshold at which it counts as running without a person. It observes those figures
from the forge, the review canary, the code and the local queue, and appends each reading
to an append-only record. The sentence and the table below are generated from the latest
reading; neither is edited by hand. The scorecard's weekly workflow had not yet run at our
cutoff: both readings in the record, at 01:33Z and 11:07Z on 2026-10-02, were taken by hand
with the same script, the second for this revision, and the stage verdicts did not change
between them.

<!-- BEGIN GENERATED autonomy:paper — regenerated by scripts/autonomy_scorecard.py -->
At the latest measurement's cutoff, 2026-10-02 11:39Z, 1 of the 11 declared stages of the delivery loop met every threshold for running without a person; not yet autonomous: DESIGN resolves without a person (partial), BUILD runs unattended (unknown), Paid engines stay available (manual), REVIEW resolves without a person (partial), The pull-request review reaches a verdict (manual), Approval comes from the delegated approver (manual), Merges land without the operator (manual), Promotion and release run without hand steps (manual), CI stays green without human re-runs (partial), The queue delivers projects to DONE (manual). The record is `docs/architecture/evidence/autonomy-scorecard.jsonl`.

```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{1.55in}p{2.2in}p{1.25in}p{0.75in}p{0.65in}@{}}
\textbf{Stage} & \textbf{Metric} & \textbf{Value} & \textbf{Threshold} & \textbf{Status}\\
\hline
DESIGN resolves without a person & DESIGN gates answered without a person & 14 of 23 (61\%) (stale, measured 2026-10-02) & $\geq$ 95\%, n $\geq$ 5 & partial\\
BUILD runs unattended & BUILD jobs finished per finished job or escalation & 1 of 3 (33\%) (stale, measured 2026-10-02) & $\geq$ 90\%, n $\geq$ 10 & unknown\\
Paid engines stay available & paid engines with a login check inside its time-to-live & 0 of 4 (0\%) (stale, measured 2026-10-02) & $\geq$ 100\% & manual\\
REVIEW resolves without a person & REVIEW gate kinds that may resolve without a person & 1 of 2 (50\%) & $\geq$ 100\% & partial\\
REVIEW resolves without a person & REVIEW gates answered without a person & unknown & $\geq$ 95\%, n $\geq$ 3 & partial\\
The pull-request review reaches a verdict & merged PRs with a review verdict at their head & 27 of 313 (9\%) & $\geq$ 95\%, n $\geq$ 5 & manual\\
The review's verdict is trustworthy & the latest review-canary measurement meets its floor & yes & yes & autonomous\\
Approval comes from the delegated approver & merged PRs approved by the delegated approver & 0 of 313 (0\%) & $\geq$ 95\%, n $\geq$ 5 & manual\\
Approval comes from the delegated approver & the review gate is a required check on the integration branch & no & yes & manual\\
Merges land without the operator & merged PRs merged by an account other than the operator's & 5 of 313 (2\%) & $\geq$ 95\%, n $\geq$ 5 & manual\\
Merges land without the operator & merged PRs carrying an approving review (no bypass) & 0 of 313 (0\%) & $\geq$ 95\%, n $\geq$ 5 & manual\\
Promotion and release run without hand steps & promotion runs a person dispatched by hand & 8 & $\leq$ 0 & manual\\
Promotion and release run without hand steps & promotions merged into the release branch by an account other than the operator's & 0 of 15 (0\%) & $\geq$ 95\%, n $\geq$ 2 & manual\\
Promotion and release run without hand steps & release publishes that succeeded & 5 of 6 (83\%) & $\geq$ 90\%, n $\geq$ 2 & manual\\
CI stays green without human re-runs & CI runs on the integration branch that succeeded & 195 of 288 (68\%) & $\geq$ 90\%, n $\geq$ 10 & partial\\
CI stays green without human re-runs & CI runs on the integration branch that were re-run & 0 of 343 (0\%) & $\leq$ 5\%, n $\geq$ 10 & partial\\
The queue delivers projects to DONE & projects that reached DONE & 0 (stale, measured 2026-10-02) & $\geq$ 1 & manual\\
The queue delivers projects to DONE & hours since the queue's latest event & 50.1 h (stale, measured 2026-10-02) & $\leq$ 24 h & manual\\
\end{tabular}
\caption{The autonomy scorecard: each declared stage of the delivery loop, the figures that judge it, and the threshold at which it counts as running without a person. A stage is as far along as its weakest criterion, and unknown when nothing judged falls short but something could not be judged. Cutoff 2026-10-02 11:39Z; forge figures over the 14 days before it, queue figures over 30. A stale value is the last good one, with the date it was measured. Record docs/architecture/evidence/autonomy-scorecard.jsonl, regenerated by scripts/autonomy\_scorecard.py.}
\label{tab:autonomy-scorecard}
\end{table*}
```
<!-- END GENERATED autonomy:paper -->

**What the scan adds.** Nothing it found was a shortage of production: BUILD ran. What
stopped the loop at every other link was evidence (a review shown unmeasured numbers,
guards and a deadline nobody evaluated), authority (every merge a bypass, an approver
nobody called), or automation that misreported its own act. The repairs took a day of
changes. The judgment about which to make, and which gates stay, was the operator's: the
gate timeouts became opt-in, and REVIEW keeps its person. Every merge into `develop` up to
`ca9e47452` (#1341) was still the operator's, through the bypass, so the repairs are not
yet evidence that the loop will deliver a change with nobody present.

### Six materials and the modulators of the rate

`vibey-gh` postulates that every dilemma in the practice of software engineering
decomposes into six materials, each with three properties, plus the pairwise
couplings between them.

| Material | Available | Stable | Reliable |
|---|---|---|---|
| Network | reachable | steady | delivers |
| Hardware | capacity | no drift | computes |
| Software | installed | pinned | to spec |
| Agent | present | rested | correct |
| Information | at hand | fresh | true |
| Agency | permitted | unrevoked | honoured |

Write the state as $x \in \mathbb{R}^{18}$, one coordinate per material and property,
and let $x^{*}$ be the state of long-term stable peak performance. The
*dilemma vector* is $d = x^{*} - x$. Agency is not agent: an agent may be present, rested,
correct and informed and still lack the power to act, which the release calculus's
trust separation imposes by design on the credential that reviews. Coordination is a
coupling rather than a seventh material, since it consumes information transfer,
agent waiting and authority resolution. For an operation $o$ with requirement vector
$r_o$,

$$\mathrm{feasible}(o) \iff x \succeq r_o$$

$$T(o) = T_0(o) \prod_i \phi_i(d_i)$$

$$C(o) = \int_0^{T(o)} c(x(t))\, dt$$

where $\phi_i$ is the dilation that a shortfall in coordinate $i$ imposes on duration:
unity at $d_i = 0$, and divergent as the coordinate approaches its floor. The gradient
$-\nabla_d T$ ranks which shortfall to repair first. The postulate is falsified by
exhibiting a real dilemma that does not decompose into these coordinates and their
couplings; it is a postulate, not a law. The six materials and their pairwise couplings
are illustrated in [Fig. 32](#fig:six-materials).

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  % ---------------------------------------------------------------- lanes
  \begin{scope}[on background layer]
    \node[vibeylane,fit={(0.3,0.35) (8.9,7.05)}] (lane1) {};
    \node[vibeylane,fit={(11.2,0.35) (17.5,7.05)}] (lane2) {};
  \end{scope}
  \node[vibeylanelabel] at (lane1.north west) {Six materials};
  \node[vibeylanelabel] at (lane2.north west) {Feasibility and duration};

  % ---------------------------------------------------------------- the six materials on a hexagon
  \coordinate (hub) at (4.6,3.75);
  \node[vibeysoft,minimum width=2.3cm] (m1) at ($(hub)+(0,2.55)$)      {\textbf{Network}\\$x_1,\,x_2,\,x_3$};
  \node[vibeysoft,minimum width=2.3cm] (m2) at ($(hub)+(2.21,1.275)$)  {\textbf{Hardware}\\$x_4,\,x_5,\,x_6$};
  \node[vibeysoft,minimum width=2.3cm] (m3) at ($(hub)+(2.21,-1.275)$) {\textbf{Software}\\$x_7,\,x_8,\,x_9$};
  \node[vibeysoft,minimum width=2.3cm] (m4) at ($(hub)+(0,-2.55)$)     {\textbf{Agent}\\$x_{10},\,x_{11},\,x_{12}$};
  \node[vibeysoft,minimum width=2.3cm] (m5) at ($(hub)+(-2.21,-1.275)$){\textbf{Information}\\$x_{13},\,x_{14},\,x_{15}$};
  \node[vibeygate,minimum width=2.3cm] (m6) at ($(hub)+(-2.21,1.275)$) {\textbf{Agency}\\$x_{16},\,x_{17},\,x_{18}$};

  % the operation at the hub: feasible when the state dominates its requirement
  \node[vibeycore,minimum width=2.5cm] (op) at (hub) {operation $o$\\feasible $\iff x \succeq r_o$};

  % each material contributes to the operation
  \foreach \m in {m1,m2,m3,m4,m5,m6}
    \draw[vibeyarrow,draw=vibeyblue!85,line width=.55pt,shorten <=1pt] (\m) -- (op);

  % pairwise couplings around the perimeter: coordination, not a seventh material
  \draw[vibeylink] (m1) -- (m2);
  \draw[vibeylink] (m2) -- (m3) node[midway,vibeypill,right=2pt] {$\mathcal{C}_{23}$};
  \draw[vibeylink] (m3) -- (m4);
  \draw[vibeylink] (m4) -- (m5);
  \draw[vibeylink] (m5) -- (m6) node[midway,vibeypill,left=2pt] {$\mathcal{C}_{56}$};
  \draw[vibeylink] (m6) -- (m1);
  \node[vibeynote,anchor=south east] at (8.8,0.45)
    {links $\mathcal{C}_{ij}$:\\coordination is a coupling,\\not a seventh material};

  % ---------------------------------------------------------------- from state to duration
  \node[vibeybox,minimum width=5.4cm] (S) at (14.35,5.7)
    {state $x$: 18 coordinates\\six materials $\times$ \{availability, stability, reliability\}};
  \node[vibeywarn,minimum width=5.4cm] (D) at (14.35,4.3)
    {dilemma vector $d = x^{*} - x$\\shortfall from the stable peak $x^{*}$};
  \node[vibeybox,minimum width=5.4cm] (T) at (14.35,2.65)
    {$T(o) = T_0(o)\,\prod_i \phi_i(d_i)$ \quad $C(o) = \int_0^{T(o)} c(x(t))\,dt$\\
     $\phi_i(0)=1$; $\phi_i \to \infty$ as coordinate $i$ nears its floor};
  \node[vibeypill] (G) at (14.35,1.2) {$-\nabla_d T$ ranks which shortfall to repair first};

  \draw[vibeyflow] (lane1.east |- S) -- (S.west)
    node[midway,above=1pt,font=\sffamily\scriptsize,text=vibeyink] {state};
  \draw[vibeyarrow] (S) -- (D);
  \draw[vibeyarrow] (D) -- (T);
  \draw[vibeyarrow] (T) -- (G);
\end{tikzpicture}
\caption{Network, hardware, software, agent, information and agency each supply three coordinates (availability, stability, reliability) of the state $x \in \mathbb{R}^{18}$. An operation is feasible when $x$ meets its requirement $r_o$. Agency, the permission to act, is gold because governance sets it through human gates. Grey links are couplings: coordination, not a seventh material. Right: shortfalls $d$ stretch the duration $T(o)$.}
\label{fig:six-materials}
\end{figure*}
```

The regularity holds its substrate fixed. Relaxing each modulator moves the band, and
each maps to a coordinate of $d$:

- **Hardware** maps to the hardware material's availability and stability, and is measured. Memory was the eventual constraint: paging space reached 99.1% during the rung at $N = 128$, where the collapse and the crashes coincide, and the serving process died under context pressure at rungs 64 and 128 and was restarted automatically each time.
- **Network stability** maps to the network material's stability, and is not measured, because the stress run was local by construction. For the paid engines it is designed for rather than measured: a window is re-probed under a deadline, and a handoff moves the work to another engine.
- **Operator availability, including rest** maps to the agent material's availability and stability, and is not measured. Authorship in the history does not record whether an agent or the operator did the work (automated repair commits appear under both the bot's name and the operator's), so it cannot separate the two; what it shows is production at every hour, described below.
- **Governance and agency** maps to the agency material's availability, and is set rather than measured: the deadline and admission rule of the stress run, and the human gates and merge authority of the delivery process.
- **Information freshness** maps to the information material's stability and reliability, and has one measured instance, corrected by this revision: the stale figures above.

### Time to completion

The regularity's use is prediction. Let $r_{\min}$ and $r_{\max}$ bound the measured
band. For $W$ units of the task class admitted in the stable region, with every
coordinate at its target ($d = 0$, so each $\phi_i = 1$),

$$T_0 \in \left[ \frac{W}{r_{\max}}, \frac{W}{r_{\min}} \right]$$

and in any state $T = T_0 \prod_i \phi_i(d_i) \geq T_0$, since every $\phi_i \geq 1$.
$T_0$ is the zero-shortfall time-to-completion: the ideal time, against which every
shortfall is a dilation. For the record's substrate and $W = 100$ units, the band
$[0.99, 2.00]$ gives $T_0$ between 50 and 101 minutes, where the serial rate alone
would give 278. The interval is wide because the band is, and replication would narrow
it. Because the held-out check exceeded the ceiling, the firm half of the prediction
is the upper end: with every coordinate at its target, the work should take no longer
than $W / r_{\min}$, as plotted in [Fig. 33](#fig:completion-band).

<!-- BEGIN GENERATED figure:completion-band rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\draw[vibeyink,line width=.6pt] (0,0) -- (7.8,0);
\draw[vibeyink] (0.00,0) -- (0.00,-0.08) node[vibeynote,anchor=north] {0}; \draw[vibeyink] (1.27,0) -- (1.27,-0.08) node[vibeynote,anchor=north] {50}; \draw[vibeyink] (2.53,0) -- (2.53,-0.08) node[vibeynote,anchor=north] {100}; \draw[vibeyink] (3.80,0) -- (3.80,-0.08) node[vibeynote,anchor=north] {150}; \draw[vibeyink] (5.07,0) -- (5.07,-0.08) node[vibeynote,anchor=north] {200}; \draw[vibeyink] (6.33,0) -- (6.33,-0.08) node[vibeynote,anchor=north] {250}; \draw[vibeyink] (7.60,0) -- (7.60,-0.08) node[vibeynote,anchor=north] {300};
\node[vibeynote,anchor=north] at (8.0,-0.08) {min};
\shade[left color=vibeyblue!35,right color=vibeyblue!10] (1.27,0.35) rectangle (2.56,0.75);
\draw[vibeyblue,line width=1pt] (1.27,0.35) rectangle (2.56,0.75);
\node[vibeynote,text=vibeyblue,anchor=south] at (1.91,0.8) {stable band: $T_0 \in [50, 101]$ min for $W = 100$};
\node[vibeynote,anchor=north] at (1.27,0.3) {50};
\node[vibeynote,anchor=north] at (2.56,0.3) {101};
\draw[vibeyred,line width=1.2pt] (7.04,0.35) -- (7.04,0.75);
\node[vibeycallout,anchor=south,align=center] at (7.04,0.8) {serial substrate\\278 min};
\draw[vibeyarrow,draw=vibeygray] (2.66,1.55) -- (6.94,1.55) node[midway,vibeynote,anchor=south] {every shortfall dilates $T_0$; none shortens it};
\end{tikzpicture}
\caption{The completion-time prediction. At the stable band's rates, 100 units of the task class take between 50 and 101 minutes on the fixed substrate with every coordinate at its target; the serial rung alone would take about 278. Shortfalls in any material coordinate stretch the interval to the right and never shorten it.}
\label{fig:completion-band}
\end{figure}
```
<!-- END GENERATED figure:completion-band -->

Beyond single-task completion bands, project delivery velocity is tracked over time
in the delivery-estimate ledger, shown in [Fig. 34](#fig:forecast).

<!-- BEGIN GENERATED figure:forecast rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.7cm},vibeyaxis,width=7.9cm,height=4.6cm,
  xmin=0.5,xmax=23.5,xtick={1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23},xticklabels={19,,,20,21,23,,24,,,25,,,26,,,,,,27,,29,30},xlabel={forecast record, by day (September 2026)}]
\nextgroupplot[title={a. Work units in the tracker},ylabel={units},ymin=0,ymax=890,legend pos=south east]
\addplot[vibeyred,line width=1pt,mark=*,mark size=1.3pt] coordinates {(1,0) (2,24) (3,24) (4,24) (5,25) (6,708) (7,706) (8,709) (9,710) (10,711) (11,712) (12,706) (13,711) (14,706) (15,699) (16,681) (17,687) (18,686) (19,693) (20,688) (21,688) (22,693) (23,690)};
\addlegendentry{remaining}
\addplot[vibeygreen,line width=1pt,mark=square*,mark size=1.2pt] coordinates {(1,235) (2,235) (3,235) (4,238) (5,247) (6,264) (7,279) (8,340) (9,342) (10,349) (11,351) (12,366) (13,376) (14,385) (15,386) (16,389) (17,393) (18,396) (19,400) (20,408) (21,415) (22,436) (23,455)};
\addlegendentry{completed}
\nextgroupplot[title={b. Forecast active days to completion},ylabel={active days},ymin=0,ymax=90,legend pos=south east]
\addplot[fill=vibeyblue!14,draw=none,forget plot] coordinates {(1,0.00) (2,1.94) (3,1.94) (4,1.92) (5,2.13) (6,59.00) (7,58.20) (8,50.05) (9,49.82) (10,48.89) (11,48.68) (12,48.22) (13,47.27) (14,45.84) (15,47.08) (16,45.52) (17,45.45) (18,45.04) (19,45.05) (20,45.53) (21,44.76) (22,46.09) (23,45.49) (23,57.50) (22,57.75) (21,62.55) (20,62.55) (19,60.26) (18,62.36) (17,65.43) (16,64.86) (15,66.57) (14,64.18) (13,64.64) (12,64.18) (11,67.81) (10,67.71) (9,67.62) (8,67.52) (7,70.60) (6,78.67) (5,3.12) (4,3.00) (3,3.00) (2,3.00) (1,0.00)} -- cycle;
\addplot[vibeyblue,line width=1pt,mark=*,mark size=1.2pt] coordinates {(1,0.00) (2,1.94) (3,1.94) (4,1.92) (5,2.13) (6,59.00) (7,58.20) (8,50.05) (9,49.82) (10,48.89) (11,48.68) (12,48.22) (13,47.27) (14,45.84) (15,47.08) (16,45.52) (17,45.45) (18,45.04) (19,45.05) (20,45.53) (21,44.76) (22,46.09) (23,45.49)};
\addlegendentry{$W/r_{\max}$}
\addplot[vibeyblue!60,line width=1pt,mark=o,mark size=1.2pt] coordinates {(1,0.00) (2,3.00) (3,3.00) (4,3.00) (5,3.12) (6,78.67) (7,70.60) (8,67.52) (9,67.62) (10,67.71) (11,67.81) (12,64.18) (13,64.64) (14,64.18) (15,66.57) (16,64.86) (17,65.43) (18,62.36) (19,60.26) (20,62.55) (21,62.55) (22,57.75) (23,57.50)};
\addlegendentry{$W/r_{\min}$}
\end{groupplot}
\end{tikzpicture}
\caption{The delivery-estimate ledger, one forecast per record. (a) Remaining and completed work units as the tracker held them: remaining jumped from 25 to 708 on Sep 23, as open issues rose from 23 to 706 when the storm filed its lanes as issues. (b) The zero-shortfall time to completion the forecast derives from the observed merge rate, 45--58 active days at the last record, with every material coordinate unmeasured and so at $\phi_i = 1$. Read from the ledger at the pinned revision, 23 records through 2026-09-30 13:44Z; records appended after the pin appear when the paper is re-pinned.}
\label{fig:forecast}
\end{figure*}
```
<!-- END GENERATED figure:forecast -->

Governance has a price in time, and the price can be lowered without lowering the bar.
The workstream that parallelised the orchestrator's test suite measured the four
per-layer coverage gates falling from about 1,530 s (four sequential suite runs) to
136 s, an 11.3-fold reduction, by computing all four floors from one instrumented run,
and the bare suite falling from 383 s to 135 s, without removing a gate
(`docs/runbooks/expansion/evidence/13-front1-validation.md`), as illustrated in [Fig. 35](#fig:governance-time).
That is a governance dilation made smaller while the requirement stayed the same.

<!-- BEGIN GENERATED figure:governance-time rev:d4c4e1f899d56ddb9ecf3166eeb6d6513998bc01 tree:cdef6169664ab0887ec2bf25872e8e64f3f08143 — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeybars,width=8.6cm,height=4.8cm,bar width=13pt,bar shift=0pt,xmin=-0.6,xmax=3.6,ymin=0,ymax=1836,
  xtick={0,1,2,3},xticklabels={four gates before,four gates after,suite before,suite after},
  x tick label style={font=\sffamily\tiny,align=center,text width=1.6cm},ylabel={seconds},
  nodes near coords,every node near coord/.append style={font=\sffamily\tiny,text=vibeygray}]
\addplot[fill=vibeyred!70,draw=none,bar shift=0pt] coordinates {(0,1530)};
\addplot[fill=vibeygreen!80,draw=none,bar shift=0pt] coordinates {(1,136)};
\addplot[fill=vibeyred!70,draw=none,bar shift=0pt] coordinates {(2,383)};
\addplot[fill=vibeygreen!80,draw=none,bar shift=0pt] coordinates {(3,135)};
\node[vibeycallout,anchor=south,align=center] at (axis cs:0.5,356) {$11.3\times$\\faster};
\node[vibeycallout,anchor=south,align=center] at (axis cs:2.5,355) {$2.8\times$\\faster};
\end{axis}
\end{tikzpicture}
\caption{A governance dilation made smaller without lowering the bar. Computing the four per-layer coverage floors from one instrumented run took the gates from about 1,530\,s to 136\,s, and the suite itself from 383\,s to 135\,s, with no gate removed.}
\label{fig:governance-time}
\end{figure}
```
<!-- END GENERATED figure:governance-time -->

### Falsification

The regularity is falsified, for its substrate, by any of the following:

- a replication on the same substrate and task pool in which a stable-region rung (success at least 87.5%) runs below 0.99 per minute, or in which the band's mean moves by more than its measured spread of 0.33 per minute;
- a log-log slope of throughput on $N$ near 1 in the stable region, which would make the rate demand-set rather than substrate-set;
- a set of $W$ units, admitted in the stable region with every coordinate at its target, that takes longer than $W / r_{\min}$ to complete.

The commodity thesis is falsified by a stall, in the tracked record, that was caused
by a shortage of production capacity while every governance coordinate stood at its
target: a funded, permitted, rested and informed system that simply could not
produce.

### Scope

This is evidence, not proof, and its scope is narrow: one machine, one model served
one way, one deadline, one artifact pool whose payload mix was not balanced across
rungs (the record names payload size, not concurrency, as what decided survival), one
stress session, one local Qwen pilot, and one operator. The field data is one project's
history. Neither the stress record nor the Qwen pilot measures network state or
operator availability, so two of the five modulators are named, mapped and unmeasured.
We do not claim a natural law, and we do not claim that the rate is constant. We claim
a band, on a substrate, together with the conditions under which the claim would fail,
and report the Qwen pilot only as a bounded reliability observation. The storm audit
is narrower still: one storm, one model slot, one host, read from local logs that were
never tracked and are now gone, and a record kept outside the repository. We
recomputed its run, turn, model-time and overlap figures and its count of started
lanes from those logs before they were lost; its conversion, control and refutation
figures are cited from the audit with its date. The account of merging ahead of review
covers one day of one project, and it is drawn from the forge's times and the
release-gate record, not from a controlled comparison. The autonomy scan is one
revision of one repository, read again a day later. Its forge figures count one
project's pull requests and runs. Its review-lane measurement is eight pull requests
run once each, with no known-true defect among them, so it bounds what the lane did on
those eight and says nothing of its recall. The cause later found for the lane's
missing verdicts on large diffs rests on one host's server log, and under its repair,
at our cutoff, every verdict was on a diff reviewed in one request. The canary's recall
is two runs on one host, at two commits, over 41 small single-file diffs written by one author, matched by a
lexical rule. The large-diff study is in progress, and its screening rests on four diffs of
one repository, on one host; nothing in it is yet a rate, and none of its arms has a
measured recall. The autonomy scorecard held three
readings and the host's health record two at our cutoff, all within two days, so neither
yet shows a trend. The account of the 3.3.0 release
rests on its workflows' runs and on one verification by the operator, recorded on the
release plan; 3.4.0's macOS and iOS builds rest on one dry run, whose two new files we
read, and on none of a person installing them.

```latex
\begin{plainwords}
We pushed one small computer harder and harder, giving it 1, 2, 4, 8 and finally 128 jobs at once. Up to 32 jobs, almost everything finished, and the computer produced about one or two finished pieces of work every minute no matter how many we asked for at once. Past that, jobs began to run out of time, and at 128 most of them failed. The computer was never broken; it was full. Only a person could decide what to do next: ask for less, allow more time, or buy a bigger computer. That is why we say the machine part is cheap and the deciding part is the hard part. Later we checked the busy season of the project's own robot helpers. Nearly all of their time went into waiting for one small brain that could think about one job at a time, so adding more helpers would have bought almost nothing, and not one job made it all the way to the finished pile without a person stepping in. When we double-checked our own first conclusions, most of them turned out to be wrong, which is itself a lesson. On the busiest day, changes were accepted faster than they could be checked, and every problem the checkers later found had to be fixed afterwards. And when the computer restarted, everything kept only in its scratch space vanished, which is why the notebook matters. Later still we asked how far the whole system could go with nobody watching. Only the building step could. The checking step showed people a green report that nobody had measured, a helper whose sign-in grew old stopped quietly, a stuck helper was never stopped, and the merging robot once threw away finished work while saying it had saved it. Each of these was fixed within a day, but every change still went in by the owner's own hand. A small local grader, shown whole files instead of only the changed lines, stopped making up problems in our small test. When we later planted mistakes for it on purpose, it caught 18 of the 25 small ones it graded, and 23 of 27 the second time, though on long changes it still often gives no grade at all. We now also count, every week, how many steps of the whole job can run with nobody watching: at each of the first three counts, one of eleven. Checking takes time, and that time is the price of being right.
\end{plainwords}
```

## The 3.0.0 operational atlas

The work after the paper's cutoff is not one feature. It changes where the system can
be stopped, where it can be wrong without saying so, and who may act at each step. The
ten figures of this section draw those changes from the code rather than the changelog.
Each shows a contract: what is recorded, what is refused, and what a failure turns
into. None of them asserts that every path has been exercised on a live run, and the
text says where one has not.

**The delivery path.** 3.0.0 adds a bridge from the forge's issue list to the
six-phase machine: `scripts/triaged_delivery.py`, run once or on an interval, claims
one triaged issue, creates a vibey project for it in a worktree of its own, drives the
normal worker on the sovereign engine, and publishes the result as a draft pull
request, which the pull-request automation promotes once its head is stable
([Fig. 36](#fig:delivery-pipeline)). Since 3.1.0 an issue a stranger wrote, edited or
labelled is held for a person and never dispatched (`scripts/intake_trust.py`, #1248).
The bridge never edits a branch itself; the worker writes the code and the phase
machine decides when it may. Every step writes its observations to a per-project
evidence file under `.vibey/delivery-evidence/`, and every exit from the path that is
not success is recorded there as what it was: a timeout, a pause for capacity, a parked
gate, a design waiting for acceptance, an untrusted issue held, an abandoned project,
or a pull request whose checks have not passed. None of them is recorded as a
completion.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  stp/.style={minimum width=2.45cm,minimum height=1.3cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  % ---- the forward path
  \node[vibeysoft,stp]      (tri)   at (0,0)     {\textbf{Triaged issue}\\forge labels\\order derived};
  \node[vibeysoft,stp]      (lease) at (3.05,0)  {\textbf{Ticket lease}\\PostgreSQL row\\900\,s lease};
  \node[vibeyvioletbox,stp] (des)   at (6.1,0)   {\textbf{Design}\\parks for a person;\\defaults on opt-in only};
  \node[vibeytealbox,stp]   (bld)   at (9.15,0)  {\textbf{Build}\\gptossloop worker\\own worktree};
  \node[vibeygate,stp]      (rev)   at (12.2,0)  {\textbf{Review}\\human gate\\project parks};
  \node[vibeybox,stp]       (pub)   at (15.25,0) {\textbf{Publish}\\push gate, PR\\train on green};
  \foreach \a/\b in {tri/lease,lease/des,des/bld,bld/rev,rev/pub}{\draw[vibeyflow] (\a) -- (\b);}
  % ---- the evidence rail every exit lands on
  \node[vibeywarn,minimum width=17.5cm,minimum height=.6cm] (ev) at (7.625,-2.35)
    {\textbf{evidence record} \texttt{.vibey/delivery-evidence/<project>.json}: every exit is recorded as what it was, never as a completion};
  \draw[vibeyback] (lease.south) -- node[redlab,right] {lease expired:\\ticket back to ready} (lease.south |- ev.north);
  \draw[vibeyback] (bld.south) -- node[redlab,right] {deadline: tree reaped;\\capacity short: paused} (bld.south |- ev.north);
  \draw[vibeyback] (rev.south) -- node[redlab,right] {gate open:\\project parked} (rev.south |- ev.north);
  \draw[vibeyback] (pub.south) -- node[redlab,left] {checks not green:\\PR left open} (pub.south |- ev.north);
  % ---- the rule above it
  \node[lab,anchor=south] at (7.625,0.85) {the bridge never edits a branch: the worker writes code, the phase machine decides when it may, the forge decides when it merges};
\end{tikzpicture}
\caption{The durable delivery path. A triaged issue is claimed under a lease, becomes an ordinary vibey project in its own worktree, is built by the sovereign engine, stops at the human review gate, and is published through the push gate as a draft pull request, promoted by the pull-request automation, that the merge train takes only when every check is green. Each non-success exit (dashed) is written to the project's evidence record as what it was.}
\label{fig:delivery-pipeline}
\end{figure*}
```

**Ordering and claiming.** The bridge keeps its tickets in PostgreSQL, not in a
process's memory ([Fig. 37](#fig:queue-state)). A reconcile pass mirrors the forge's
open, triaged issues into rows, and a claim takes the first `ready` row under a
900-second lease with `FOR UPDATE SKIP LOCKED`, the same primitive the job queue uses.
The order is derived, never edited: issues a person has bumped come first, in the order
they were bumped, then the priority label from critical to low, then the issue least
recently updated, then the issue number. Each pass of the bridge first returns expired
leases to `ready`, so an expired lease is released on the next pass without an
operator. A dispatch is also marked on the issue
itself, by a comment carrying the project's identity, so a second bridge that lost its
database would still not dispatch the same issue twice.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  st/.style={minimum width=1.85cm,minimum height=.8cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeysoft,st] (ready) at (0,0)     {\textbf{ready}\\claimable};
  \node[vibeysoft,st] (leased) at (2.9,0)  {\textbf{leased}\\900\,s owner};
  \node[vibeytealbox,st] (disp) at (5.8,0) {\textbf{dispatched}\\project made};
  \node[vibeygood,st] (done) at (5.8,-2.05) {\textbf{completed}\\PR published};
  \node[vibeyghost,st] (blk) at (2.9,-2.05) {\textbf{blocked}\\untrusted, abandoned,\\retired, or by hand};
  \node[vibeybox,minimum width=1.85cm] (gh) at (0,1.6) {forge: open issues\\labelled triaged};
  \draw[vibeyflow] (gh) -- node[lab,right] {reconcile} (ready);
  \draw[vibeyflow] (ready) -- node[lab,above] {claim,\\skip locked} (leased);
  \draw[vibeyflow] (leased) -- node[lab,above] {dispatch} (disp);
  \draw[vibeyflow] (disp) -- node[lab,right] {publish} (done);
  \draw[vibeyback] (leased.south) to[bend left=40] node[redlab,below] {reap: lease expired} (ready.south);
  \draw[vibeydashed,-{Stealth[length=1.8mm]}] (disp) -- (blk);
  \node[vibeypill] at (2.9,-3.25) {claim order: bumped first, then critical $\to$ low,\\then least recently updated, then issue number};
\end{tikzpicture}
\caption{The triage ticket. Rows mirror the forge's triaged issues and are claimed under a lease with \texttt{FOR UPDATE SKIP LOCKED}; an expired lease returns the row to ready. The claim order is derived from labels and update time, so no one reorders the queue by hand. Blocked is set by the bridge for an untrusted, abandoned or retired issue, after three failed dispatches, or by a person.}
\label{fig:queue-state}
\end{figure}
```

**Who may act.** The six-phase machine names the gates; the bridge adds actors who
were not in the original model ([Fig. 38](#fig:authority-map)). A person labels and
prioritises issues, answers the review gate, approves the merge unless the operator's
grant lets the delegated approver of sub-doctrine 12.f give that approval in their place
(`[unattended_approval]`, with a standing grant declared since #1300; no workflow calls
the approver, and its account had reviewed no pull request by 2026-10-01), and is the only party
who can opt a project into deployment, which is never inferred. The bridge claims,
orders and publishes. The engine writes code only inside BUILD and only in its own
worktree. The forge's required checks decide whether the merge train may take a pull
request. One cell of the map needs stating plainly, because it departed from the
original model: the DESIGN interview. At this atlas's cutoff the bridge answered the
design interview's question gates with their declared defaults and then accepted the
design itself, so on this path DESIGN did not wait for a person, and the answers were
recorded under the operator's own name with trusted provenance: on the first delivered
issue three of the four interview gates were answered within a second of being raised,
and the ledger could not tell those answers from a person's. We reported it as a
defect of the bridge, not a property of the model, and it is repaired. DESIGN gates
now park for a person by default; answering them with defaults is an explicit opt-in,
recorded under the automation's own name, `automation:triaged-delivery`; and even then
the design is accepted only once its research, synthesis and spec jobs have settled
(#1258), from defaults declared at the narrowest scope that still delivers the issue
(#1261, #1270). Two rows join the map since 3.1.0: the bridge admits an issue only when
every account that wrote, edited or labelled it is trusted (#1248), and a person can
end any project short of done with `vibey abandon` (#1263).

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  rowl/.style={font=\sffamily\scriptsize,text=vibeyink,anchor=east},
  colh/.style={font=\sffamily\tiny\bfseries,text=vibeyink,align=center},
  yes/.style={circle,fill=vibeyblue,inner sep=2.1pt},
  hum/.style={circle,fill=vibeygold!90!black,inner sep=2.1pt},
  flag/.style={circle,fill=vibeyred,inner sep=2.1pt}]
  \foreach \x/\h in {3.35/{person},4.6/{delivery\\bridge},5.85/{engine},7.1/{forge\\checks}}
    {\node[colh] at (\x,0.45) {\h};}
  \foreach \y/\r in {0/{label and prioritise an issue},
                     -0.45/{admit the issue (trust check)},
                     -0.9/{claim, order and lease},
                     -1.35/{answer the design interview},
                     -1.8/{accept the design},
                     -2.25/{write code in BUILD},
                     -2.7/{give the review verdict},
                     -3.15/{push, open the pull request},
                     -3.6/{merge into develop},
                     -4.05/{opt into deployment},
                     -4.5/{abandon a project}}
    {\node[rowl] at (2.65,\y) {\r};
     \draw[vibeyedge] (0.2,\y-0.225) -- (7.65,\y-0.225);}
  \node[hum] at (3.35,0) {};
  \node[yes] at (4.6,-0.45) {};
  \node[yes] at (4.6,-0.9) {};
  \node[hum] at (3.35,-1.35) {};
  \node[flag] at (4.6,-1.35) {};
  \node[hum] at (3.35,-1.8) {};
  \node[flag] at (4.6,-1.8) {};
  \node[yes] at (5.85,-2.25) {};
  \node[hum] at (3.35,-2.7) {};
  \node[yes] at (4.6,-3.15) {};
  \node[hum] at (3.35,-3.6) {};
  \node[yes] at (7.1,-3.6) {};
  \node[hum] at (3.35,-4.05) {};
  \node[hum] at (3.35,-4.5) {};
  \node[font=\sffamily\tiny,text=vibeygray,align=left,anchor=north west] at (0.2,-4.9)
    {\tikz\node[hum]{}; a person's recorded decision\quad \tikz\node[yes]{}; automated\\
     \tikz\node[flag]{}; automated only on the operator's opt-in,\\
     recorded under the automation's own name};
\end{tikzpicture}
\caption{The authority map of the delivery path. Gold marks a decision a person records, blue an automated step. The two design steps are a person's by default; red marks that the bridge performs them, with declared defaults recorded under its own name, only when the operator opts in. The bridge admits an issue only when everyone who wrote, edited or labelled it is trusted. Review, deployment and abandoning a project remain a person's; merge approval is a person's or, under the operator's grant, the delegated approver's (12.f), never the bridge's; and deployment is never inferred.}
\label{fig:authority-map}
\end{figure}
```

**A worker that overruns.** The bridge gives each worker run a deadline, 900 seconds
by default ([Fig. 39](#fig:process-reaping)). A worker that overruns is not merely
signalled: the bridge walks its process tree, sends the terminate signal to the
deepest descendants first and the worker last, waits two seconds, and kills whatever
is still alive, because `uv run` starts children that outlive a signal sent only to
their parent (a defect fixed in the 3.0.0 release, #1244). Only then does it record the
timeout, and it leaves the job's lease to expire rather than releasing it; on its next
pass it runs the queue's own reaper for that project (`vibey queue reap --project`)
before it drives the project again, so the job returns to the queue by the same path a
crashed worker's does and is fenced the same way: a late acknowledgement from the old
worker is refused.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  r/.style={minimum width=3.4cm,minimum height=.7cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt}]
  \node[vibeysoft,r] (run) at (0,0) {\textbf{worker run}\\own session, own process group};
  \node[vibeywarn,r] (dl) at (0,-1.25) {\textbf{deadline passes}\\900\,s by default};
  \node[vibeybox,r] (term) at (0,-2.5) {\textbf{terminate the tree}\\deepest descendants first};
  \node[vibeybox,r] (kill) at (0,-3.75) {\textbf{kill survivors}\\after a 2\,s grace};
  \node[vibeytealbox,r] (ev) at (0,-5.0) {\textbf{record the timeout}\\in the evidence file};
  \node[vibeysoft,r] (reap) at (0,-6.25) {\textbf{lease left to expire}\\next pass reaps; late ack refused};
  \draw[vibeyflow] (run) -- (dl);
  \draw[vibeyflow] (dl) -- (term);
  \draw[vibeyflow] (term) -- (kill);
  \draw[vibeyflow] (kill) -- (ev);
  \draw[vibeyflow] (ev) -- (reap);
  \node[lab,anchor=west,align=left] at (1.95,-3.1) {no process of the old\\run is left alive to\\write after the timeout\\is recorded};
\end{tikzpicture}
\caption{Worker timeout handling in the delivery bridge. The whole process tree is stopped before the timeout is recorded, and the lease is left to expire and reaped by the queue's own reaper on the bridge's next pass, so a timed-out job returns to the queue by the same fenced path as a crashed worker's.}
\label{fig:process-reaping}
\end{figure}
```

**Capacity before completion.** The bridge applies the session-runner rule of
[Fig. 12](#fig:capacity-taxonomy) at its own level ([Fig. 40](#fig:capacity-precedence)).
After every worker run it reads the project's status, and if any job is awaiting
capacity or any engine's circuit reports a capacity state other than available, it
records a pause for capacity and stops before it acts on the phase or the open gates.
The run's phase is acted on only on the branch where capacity was available. The same order holds
inside each runner, where a capacity verdict outranks a completion claim, so a starved
run cannot be laundered into success at either level.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  n/.style={minimum width=2.6cm,minimum height=.75cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeysoft,n] (end) at (0,0) {\textbf{worker run ends}\\status and gates read};
  \node[vibeycore,diamond,aspect=2.2,inner sep=1pt,font=\sffamily\tiny\bfseries] (cap) at (0,-1.55) {capacity\\available?};
  \node[vibeywarn,n] (pause) at (3.55,-1.55) {\textbf{paused for capacity}\\phase not acted on};
  \node[vibeybox,n] (claim) at (0,-3.1) {\textbf{act on the phase}\\answer, accept, publish};
  \node[vibeygood,n] (done) at (0,-4.45) {\textbf{progress recorded}};
  \draw[vibeyflow] (end) -- (cap);
  \draw[vibeyback] (cap) -- node[redlab,above] {no} (pause);
  \draw[vibeyflow] (cap) -- node[lab,right] {yes} (claim);
  \draw[vibeyflow] (claim) -- (done);
  \node[lab,anchor=north,text width=3.1cm] at (3.55,-2.15) {awaiting-capacity jobs, or any engine circuit not available};
\end{tikzpicture}
\caption{Capacity precedence in the delivery bridge. The capacity check runs before the bridge acts on the run's phase, so an exhausted or busy engine records a pause, never progress; the same order holds inside each session runner, where a capacity verdict outranks a completion claim.}
\label{fig:capacity-precedence}
\end{figure}
```

**Measured local capacity.** A sovereign engine's context and output ceilings are no
longer guessed ([Fig. 41](#fig:probe-lifecycle)). A probe (`scripts/sovereign_probe.py`,
also reachable as a doctor check) runs a grid of context and output sizes against the
local server and writes a record: the endpoint, the model, the source revision, the
shape of the prompt it measured, and the fastest fit that answered validly. At start,
the chat client loads that record only if its endpoint and model match the running
configuration, its revision matches too when the running revision is named
(`VIBEY_REVISION`, which nothing in vibey sets, so by default the revision is recorded
but not checked), and its fit is marked valid; any mismatch, a missing field, or
an unreadable file drops back to the configured ceilings. At each request the client
applies the fit only if the prompt is no larger than the shape it was measured on; a
longer prompt runs under the conservative defaults of 8,192 context tokens and 2,048
output tokens. The fit is therefore a measurement about one host, one model and one
revision, and it is never carried to a place it was not measured.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  s/.style={minimum width=2.9cm,minimum height=.7cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeysoft,s] (probe) at (0,0) {\textbf{probe a grid}\\contexts $\times$ outputs};
  \node[vibeysoft,s] (rec) at (0,-1.3) {\textbf{record the fit}\\endpoint, model, revision,\\prompt shape, fastest valid};
  \node[vibeybox,s] (load) at (0,-2.75) {\textbf{load at start}\\endpoint, model, valid fit;\\revision when named};
  \node[vibeybox,s] (req) at (0,-4.05) {\textbf{each request}\\prompt within the shape?};
  \node[vibeytealbox,s] (fit) at (0,-5.35) {\textbf{measured ceilings}};
  \node[vibeywarn,minimum width=2.4cm,minimum height=.7cm] (fb) at (3.6,-3.4) {\textbf{configured ceilings}\\8,192 in, 2,048 out};
  \draw[vibeyflow] (probe) -- (rec);
  \draw[vibeyflow] (rec) -- (load);
  \draw[vibeyflow] (load) -- (req);
  \draw[vibeyflow] (req) -- node[lab,right] {yes} (fit);
  \draw[vibeyback] (load.east) -| node[redlab,pos=.25,above] {stale or malformed} (fb.north);
  \draw[vibeyback] (req.east) -| node[redlab,pos=.25,below] {longer prompt} (fb.south);
\end{tikzpicture}
\caption{The measured-capacity lifecycle. A probed fit is bound to its endpoint, model and prompt shape, and to its revision when the running revision is named; any mismatch at load falls back to the configured ceilings, and a prompt longer than the one measured to the conservative defaults, rather than to a guess.}
\label{fig:probe-lifecycle}
\end{figure}
```

**The engine's environment.** An engine session runs commands the model chooses, so
what it can see of the worker's environment is a boundary, and in 3.0.0 it is built
from an allow-list rather than copied ([Fig. 42](#fig:environment-boundary)). Three
sources may add a variable: the system basics every process needs, the engine's own
declared variables and its own API credential, and whatever the project's stored
configuration declares under `engine_environment`, for every engine or for one. Beneath
all three sits a forbidden set: vibey's own variables, among them the queue and ledger
connection string, libpq's variables, and anything shaped like a database credential.
A declaration that names one of them is refused when the worker is built, not when the
first session would have received it. A forge token or a cloud credential is not
forbidden, but it is on no default list; it reaches only an engine a project declares
it for.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  src/.style={minimum width=2.25cm,minimum height=.95cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeysoft,src] (sys) at (0,0) {\textbf{system basics}\\every process};
  \node[vibeysoft,src] (eng) at (2.75,0) {\textbf{engine's own}\\declared vars,\\its credential};
  \node[vibeysoft,src] (proj) at (5.5,0) {\textbf{project config}\\\texttt{engine\_}\\\texttt{environment}};
  \node[vibeycore,minimum width=7.75cm,minimum height=.7cm] (al) at (2.75,-1.6) {allow-list, checked when the worker is built};
  \node[vibeytealbox,minimum width=3.3cm,minimum height=.8cm] (sess) at (1.1,-3.1) {\textbf{engine session}\\sees only the list};
  \node[vibeywarn,minimum width=3.3cm,minimum height=.8cm] (forb) at (4.75,-3.1) {\textbf{refused}\\a forbidden name};
  \foreach \s in {sys,eng,proj}{\draw[vibeyflow] (\s) -- (\s |- al.north);}
  \draw[vibeyflow] (sess.north |- al.south) -- (sess);
  \draw[vibeyback] (forb.north |- al.south) -- (forb);
  \node[lab,anchor=north] at (2.75,-3.65) {forbidden: vibey's own variables (the queue and ledger DSN among them),\\libpq's, and anything shaped like a database credential; forge and cloud\\tokens are on no default list and reach only an engine the project names};
\end{tikzpicture}
\caption{The engine environment boundary. A session's environment is assembled from three allow-listed sources, never copied from the worker, and a declaration that names a forbidden variable fails when the worker is built.}
\label{fig:environment-boundary}
\end{figure}
```

**What a verdict is about.** [Fig. 15](#fig:exact-head) binds a claim to the revision it
evaluated. The sovereign reviewer adds the second binding described in the section on
the release calculus: to the input the model actually read ([Fig. 43](#fig:exact-head-lifecycle)).
A verdict on head $h$ is admitted only if it passes four checks in order. Each part of
the diff must fit the window: since 3.1.0 a diff too large for one request is split by
file, then by hunk, and since 3.2.0 an added-only hunk between lines, into at most six
parts by default, each held to every check below, and only a diff that cannot be split
that far is never sent and goes to a person (#1252, #1278). The server must be told to refuse rather than truncate, so a cut is reported in the
server's own words. The answer must echo both random check codes, one placed at the
start of the system prompt and one after the diff, so a silent cut at either end is
caught. And if a supporting document had to be cut or left out, the verdict may claim
only the half of the review the diff alone can ground. Each failure is a refusal with
its reason, and none is a pass. After 3.2.0 the reviewer is also shown the full text at
the head of the files the diff changes (#1303), as reference only: it may report nothing
on a line the diff did not change. A source too large for the room left after the diff
and the documents is shown as an excerpt around each change, with every gap marked, and
a source cut or left out is named in the prompt and in the verdict's summary; unlike a
document, it does not narrow the verdict. Since #1316 a part must also finish in the room
it was sized with: its answer is capped at the reserve, and a model that fills the
reserve without answering is refused as `done_reason=length`, not passed and not
reported as a timeout.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  c/.style={minimum width=3.3cm,minimum height=.65cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred,anchor=west}]
  \node[vibeysoft,c] (h) at (0,0) {\textbf{review of head $h$}\\exact head: $r = h$};
  \node[vibeybox,c] (fit) at (0,-1.15) {each part fits the window};
  \node[vibeybox,c] (trunc) at (0,-2.05) {server told: refuse, never cut};
  \node[vibeybox,c] (codes) at (0,-2.95) {both check codes echoed};
  \node[vibeybox,c] (docs) at (0,-3.85) {supporting documents whole};
  \node[vibeygood,c] (ok) at (0,-5.0) {\textbf{verdict admitted}\\about what was read};
  \draw[vibeyflow] (h) -- (fit);
  \draw[vibeyflow] (fit) -- (trunc);
  \draw[vibeyflow] (trunc) -- (codes);
  \draw[vibeyflow] (codes) -- (docs);
  \draw[vibeyflow] (docs) -- (ok);
  \draw[vibeyback] (fit.east) -- ++(.35,0) node[redlab] {unsplittable: not sent};
  \draw[vibeyback] (trunc.east) -- ++(.35,0) node[redlab] {refusal, in its words};
  \draw[vibeyback] (codes.east) -- ++(.35,0) node[redlab] {verdict discarded};
  \draw[vibeyback] (docs.east) -- ++(.35,0) node[redlab] {half review only};
\end{tikzpicture}
\caption{The exact-head lifecycle extended to the reviewer's input. After $r = h$, a sovereign verdict must survive four checks, each of which refuses rather than passes: every part of the diff fits (a large diff is reviewed in at most six parts, and only one that cannot be split that far goes unsent to a person), the server may not truncate, both check codes return, and the supporting documents were read whole.}
\label{fig:exact-head-lifecycle}
\end{figure}
```

**Context in slices.** The same no-silent-truncation rule is proposed for everything
the system loads into a finite window: skills, guides, decisions, prompts and
specifications ([Fig. 44](#fig:microslice-contract)). Under the proposed ADR-0075, a
converter (`slice_markdown.py`) turns a source document into numbered slices without
changing the source; each slice it writes carries a stable identity, a purpose, its
source, and explicit `requires` and `links` relations to its neighbours, and an index
records them. The contract adds a measured size to each slice and a retriever that
starts at the slice that matches the request, follows its required safety and
acceptance slices, measures the whole closure against the budget, and records the
identities and size it loaded; neither is implemented yet. A closure over budget is split or parked,
never cut, and optional links are followed only when needed. The converter's slice
boundaries are mechanical and still need review; a split is not a claim that each
slice reads well on its own.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  n/.style={minimum width=2.3cm,minimum height=1.35cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeybox,n] (src) at (0,0) {\textbf{source}\\unchanged,\\authoritative};
  \node[vibeysoft,n] (conv) at (3.0,0) {\textbf{converter}\\\texttt{slice\_}\\\texttt{markdown.py}};
  \node[vibeysoft,n] (sl) at (6.0,0) {\textbf{numbered slices}\\id, purpose,\\provenance, size,\\requires, links};
  \node[vibeybox,n] (q) at (9.0,0) {\textbf{retrieval}\\matching slice,\\then its required\\slices};
  \node[vibeycore,diamond,aspect=1.9,inner sep=1pt,font=\sffamily\tiny\bfseries] (b) at (12.1,0) {closure\\within\\budget?};
  \node[vibeygood,n] (load) at (15.2,0) {\textbf{load, record}\\slice ids,\\measured size};
  \node[vibeywarn,n,minimum height=.9cm] (split) at (12.1,-2.15) {\textbf{split or park}\\never truncate};
  \draw[vibeyflow] (src) -- (conv);
  \draw[vibeyflow] (conv) -- (sl);
  \draw[vibeyflow] (sl) -- (q);
  \draw[vibeyflow] (q) -- (b);
  \draw[vibeyflow] (b) -- node[lab,above] {yes} (load);
  \draw[vibeyback] (b) -- node[redlab,right] {no} (split);
  \draw[vibeyback,rounded corners=3pt] (split.west) -| node[redlab,pos=.3,below] {smaller slices, or the request parks} (sl.south);
  \node[lab,anchor=north] at (3.0,-0.85) {mechanical boundaries;\\each split is reviewed};
\end{tikzpicture}
\caption{The context-microslice contract (proposed ADR-0075). Source material is converted into identified, bounded slices with provenance and explicit links; retrieval loads a slice with its required closure only when the closure fits the budget, and otherwise splits or parks it rather than dropping the tail.}
\label{fig:microslice-contract}
\end{figure*}
```

**How this paper is published.** The paper itself follows the discipline it describes
([Fig. 45](#fig:publication-ladder)). `docs/paper.md` is the one source. Evidence is
recomputed by `scripts/paper_evidence.py`, and every computed figure is written between
revision-pinned markers by `scripts/paper_figures.py`, whose `--check` mode fails CI
when a block has drifted from the records. From that source `vibey-gh paper` writes the
LaTeX and DOCX, the pinned Tectonic typesets the PDF, and `vibey-gh paper-figures`
compiles each figure on its own and turns it into SVG for the site and the book. Two
steps are not automated and we do not claim they are. A figure that fails to compile
for the site keeps its source and shows its caption, with a warning in the build log,
rather than failing the release; and whether a drawing is legible, with no label on a
line and no box on another, is judged by a person looking at it, which is how the
defects repaired in this revision were found.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  n/.style={minimum width=2.45cm,minimum height=1.05cm},
  lab/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.5pt},
  redlab/.style={lab,text=vibeyred}]
  \node[vibeysoft,n] (ev) at (0,1.2) {\textbf{evidence}\\\texttt{paper\_evidence.py}};
  \node[vibeysoft,n] (fg) at (0,-1.2) {\textbf{computed figures}\\\texttt{paper\_figures.py}\\revision-pinned};
  \node[vibeycore,n] (md) at (3.35,0) {\textbf{docs/paper.md}\\the one source};
  \node[vibeybox,n] (tex) at (6.7,1.2) {\textbf{LaTeX, DOCX}\\\texttt{vibey-gh paper}};
  \node[vibeybox,n] (svg) at (6.7,-1.2) {\textbf{per-figure SVG}\\\texttt{paper-figures}};
  \node[vibeytealbox,n] (pdf) at (10.05,1.2) {\textbf{PDF}\\pinned Tectonic};
  \node[vibeytealbox,n] (site) at (10.05,-1.2) {\textbf{site and book}\\HTML, EPUB, PDF};
  \node[vibeygate,n] (eye) at (13.7,0) {\textbf{visual inspection}\\a person looks};
  \draw[vibeyflow] (ev.east) -- ++(.35,0) |- ([yshift=5pt]md.west);
  \draw[vibeyflow] (fg.east) -- ++(.35,0) |- ([yshift=-5pt]md.west);
  \draw[vibeyflow] ([yshift=5pt]md.east) -- ++(.35,0) |- (tex.west);
  \draw[vibeyflow] ([yshift=-5pt]md.east) -- ++(.35,0) |- (svg.west);
  \draw[vibeyflow] (tex) -- (pdf);
  \draw[vibeyflow] (svg) -- (site);
  \draw[vibeyflow] (pdf.east) -| (eye.north);
  \draw[vibeyflow] (site.east) -| (eye.south);
  \draw[vibeyback,rounded corners=3pt] (eye.east) -- ++(.35,0) |- (3.35,-2.55) -- (md.south);
  \node[redlab,anchor=north] at (8.5,-2.6) {a defect found by eye is fixed in the source, never in an output};
  \node[redlab,anchor=north] at (svg.south) {fails to compile: caption shown,\\warning logged};
  \node[lab,anchor=south] at (ev.north) {\texttt{--check} fails CI on drift};
\end{tikzpicture}
\caption{Publication provenance. Evidence and computed figures are written into the one source, from which every output is derived by a pinned tool; the legibility of a drawing is still judged by a person, and a defect found that way is repaired in the source.}
\label{fig:publication-ladder}
\end{figure*}
```

Read together, the ten figures draw one boundary: durable work is distinct from live
work, and nothing crosses from one to the other on a claim alone. A ticket, a lease, a
measured fit and a verdict are each bound to what they were measured on, and each
failure is recorded as what it was. They also draw the limits. The atlas does not
claim that an open issue will be delivered, that a fit measured on one host holds on
another, that the bridge's opt-in defaults for the design interview are the answers a
person would give, or that a generated figure is a legible one.

### Changes in 3.1.0 and 3.2.0

The atlas is drawn at 3.0.0. Within its scope, the delivery path, who may act, how a
worker is handled and what a verdict is about, releases 3.1.0 and 3.2.0 changed the
following, each named with where it lives.

- **An operator's exit.** `vibey abandon` withdraws a project's gates, cancels its jobs and records the reason (#1263, `src/vibey/cli/abandon.py`); since 3.2.0 a project still in intake can be abandoned too (#1276). The bridge then frees its one slot and blocks the ticket.
- **Checkouts released.** An abandoned project lets its checkout go (migration 0021, #1279), and `vibey new` on a checkout a live project holds is refused as `CheckoutHeld`, exit 3.
- **Redispatch from the current base.** A fresh dispatch moves a leftover `triaged-<issue>` checkout to `--base`, and refuses one with changes (#1269).
- **Branches a project owns.** BUILD branches are `vibey/<project8>/<cycle>/<item>`, each recording its project and base in the repository's config; one that cannot prove it is the project's own parks on a `foreign_branch` gate, and the bridge publishes the integration branch only after the same check (#1269, `src/vibey/domain/worktree.py`).
- **Plans that name real files.** A plan whose verification runs or reads a file nothing provides is refused before BUILD (#1270, `vibey.domain.plan_references`).
- **The host named.** The local runner tells the model which host its shell commands run on and keeps file edits in `edit_file` (#1270, `HostPlatform`).
- **Tool results cut by a key.** `max_tool_result_chars`, 24,000 characters by default, replaces the fixed 8,000 (#1270).
- **Research gaps recorded.** `[design.research] on_unavailable = "record_gap"` records a topic no evidence exists for as a gap stated in the spec; the bridge opts in only with `--record-research-gaps` (#1259).
- **Narrowest defaults.** A DESIGN question's declared default is the narrowest scope that still delivers the change, and the bridge always creates projects that way (#1261, #1270).
- **Acceptance waits for the design.** `vibey design accept` refuses while any DESIGN job of the cycle is unsettled, and the bridge waits likewise (#1258).
- **Telling a person is evidence.** Every gate notice ends in `GateNotified` or `GateNoticeUndeliverable`, stale gates are reminded about, and `vibey gates --remind` and a `gate-notices` doctor line report them (#1251, `src/vibey/application/gate_notices.py`).
- **The defect gate.** A job whose last failures share one signature parks on `defect` rather than retrying (#1251, `vibey.domain.defect`).
- **Parallel loops stopped together.** With `-j 2` or more, a drive loop that raises stops its siblings before the worker closes its pool (#1272).
- **Review at scale.** The sovereign review works in bounded parts, retries an unreachable model and records every outcome as a code (#1252), and splits an added-only hunk between lines (#1278).
- **The trust seam.** An issue a stranger wrote, edited or labelled is held, and an admitted one reaches DESIGN framed by `PromptShield` (#1248, `scripts/intake_trust.py`).
- **One worker for every project.** `vibey worker --all-projects` serves every project's queue, and `vibey supervisor install` runs it and the bridge supervised (#1249).
- **Draft publication.** Delivery pull requests open as drafts that the pull-request automation promotes; this one landed with the 3.0.0 release itself (#1244), after the atlas's cutoff (`scripts/triaged_delivery.py`).

### Changes in 3.3.0

Released on 2026-10-02 (`main` at `4188aad66`, promoted by #1343). Each item is reported in
the section named.

- **REVIEW shown what ran.** Each integration ledgers its verification commands, their exit codes and output tails, and REVIEW renders only that record (#1294; *The autonomy scan of 2026-09-30*).
- **Gates that time out by declaration.** A gate resolves to its stored default only for the kinds a project declares, and REVIEW's approval never does (#1299).
- **Workers bounded.** A BUILD session stops at a wall-clock limit (#1296), a stop ends the session's whole process group (#1297), shutdown cannot crash on a session it cannot reap (#1309), an ageing paid login is rechecked (#1295), and an integrated work item's worktree is retired (#1298).
- **Merges that are confirmed.** The merge train counts a merge only when the forge reports it merged (#1301).
- **The approver's grant, declared.** The operator's standing grant and what it never covers are in `[autonomy]` (#1300), and the approver may not approve the code that defines what its gates measure (#1302).
- **A reviewer that sees more and stops in time.** The sovereign review reads the full text of the files it judges (#1303), its output is capped and its deadline grows with the request (#1316; *Exact-head evaluation*), and its recall on planted defects is measured by an offline canary (#1325, #1331).
- **One file per change.** Changelog entries are fragments assembled at release (#1305), and the coverage floor reaches the forge's rulesets (#1321).
- **Clients on every release.** A release carries a build of every client, with checksums and per-file provenance attestations; 3.3.0 attached eleven, and the VS Code extension was first listed on Open VSX (#1317; *Exact-head evaluation*).
- **Requirements, health and distance from autonomy, measured.** Linux requirements as a matrix of distributions and architectures (#1313; *Rolling minimum system requirements*), the host's weekly health, forecast and declared tuning (#1330, #1334; *Host health and the memory budget*), and the weekly autonomy scorecard (#1335).
- **The revoke race and the gates around CI.** The replication-role revoke retries all three messages of its race and the tests serialize their grants (#1310, #1314, #1326, #1332); the KEDA contract no longer races a drain (#1327), the Arch job survives a failing mirror (#1333), and dependency advisories may be excepted only by a declared, expiring entry (#1336; *Validation*).
- **The large-diff study.** A preregistered study of the reviewer's large-diff failures, in progress: mechanism and screening only (#1328, #1340, #1341; *Exact-head evaluation*).

### Changes after 3.3.0

What follows is on `develop` at `4d51a764c`, planned for 3.4.0 (#1349) and not yet
released. Each item is reported in the section named.

- **A macOS desktop app.** krypton desktop is built for Apple silicon on macOS 15 or newer as a self-contained `krypton.app` in a `.dmg`, verified to name nothing outside itself and launched with Homebrew hidden; ad-hoc signed until the Developer ID secrets exist, and Intel Macs declared unsupported with the reason (#1351, `scripts/macos_app_bundle.py`; *Exact-head evaluation*).
- **An iOS build.** The app is registered with EAS under its Expo organisation and EAS keeps its build number, so a release builds an `.ipa` signed for the App Store while `EXPO_TOKEN` is set (#1346, #1347, #1348, #1350, #1351; *Exact-head evaluation*).
- **Client changes are releasable.** `clients/` is in the version's code paths, so a change to the clients alone derives a patch release (#1348).
- **Desktop pairing.** krypton desktop pairs with a hub by its one-time code, to the hub's own protocol: a device key returned once, every request signed with it, and the hub's certificate pinned (#1359; *Exact-head evaluation*).
- **Weekly measurements that land.** The review canary's and the minimum requirements' weekly runs hand their results over where they are committed from, a fresh measurement that changes nothing fails, and the first runs' dropped results were recovered (#1360, #1361, #1365; *Exact-head evaluation*, *Rolling minimum system requirements*).
- **The large-diff study, continued.** Its sibling tracks' write-ups are committed, its production arms are pinned to the registered settings at run time, and Stage 1 is complete, with five arms answering on all four screening hosts; still mechanism and screening only, and production is unchanged (#1352, #1354, #1362, #1364; *Exact-head evaluation*).

```latex
\begin{plainwords}
This part of the paper is a picture book of the newest machinery. A robot helper now takes a job from the project's to-do list, but only after a person has sorted and labelled it, and it holds the job for fifteen minutes at a time so that a stuck helper cannot keep it forever. The helper builds the change in its own copy of the project, and then it stops and waits for a person to check the work. If a helper runs too long, it is stopped completely, every little process it started included, before anything is written down. If the computer is too busy or out of allowance, the helper writes down that it paused, not that it finished. The helper only uses as much memory as was actually measured on this computer, and it only sees the secrets it was allowed to see. A grader must prove it read the whole change. One thing we tell you straight: on this path the helper used to fill in the first design questions with standard answers by itself, under the owner's name. Now it waits for a person to answer them, unless it has been told it may fill in the standard answers, and then it signs them with its own name. It also refuses to start on a job that a stranger wrote or changed. And the pictures in this paper are checked by a person with their own eyes, which is how we found the ones we fixed.
\end{plainwords}
```

## Validation

The model is validated at three levels. At the *property* level, the gate, the phase
guards and the selector are pure functions under a 100% branch-coverage floor per
architectural layer, with property tests on the selector and the credits type. At the
*chaos* level, concurrent workers process a job set against a real PostgreSQL while
each randomly abandons claimed jobs mid-flight and a concurrent reaper reclaims the
expired leases; the verified property is no double commit, no lost job, and every
job terminal. Execution itself is at-least-once: a worker that outlives its lease
may run a job that another worker has reclaimed, but the acknowledgement is fenced
on the lease owner, so the stale one is refused and exactly one commits per job.
At the *live* level, a runbook drives one project from design through
build and review to local completion on two paid engines, `claudeloop` and
`agyloop`, including a forced rotation between them. Live runs over the other
engines are not yet reported here. Where the binaries are installed, a scripted-binary
conformance suite drives `claudeloop` and `codexloop`, and `cursorloop` as a strict
expected failure, through their own offline agents and holds each to the nine
conformance checks; `agyloop` and the local engines have no offline agent and rest on
the in-memory double. The production-rate
claims are validated separately, by the stress record and the evidence script above;
the local Qwen pilot is reported as an operational reliability observation with its
own cutoff and does not enlarge the throughput claim.

The 3.0.0 additions are validated the same three ways, and each also went through an
independent adversarial review whose probes are review records rather than tracked
tests. At the property level, a Hypothesis state machine drives the priority lane
through random, overlapping bumps, un-bumps and job endings and checks the derivation
after every step (#1095, #1103), and the sovereign reviewer's refusals are pinned by a
stub server that answers the way the real one was seen to answer: the half-window
count, the HTTP 400 in the server's words, and a reply that echoes only one check code
(#1101). At the chaos level, the whole orchestrator suite now runs as the restricted
application role, so any query that needs an undeclared privilege fails as
`permission denied` (#1100); five workers claim concurrently against a bumped queue
and take exactly the front five in order (#1091); and a hung test is dumped at 240 s
and failed by name at 300 s (#1105). At the cluster level, a new cluster-smoke step
checks that, as the worker's role, an update, a delete and a truncation of the ledger
are refused for want of privilege and disabling a trigger is refused as not the owner,
and that, as the owner, all three are refused by the triggers (#1100). The full suite
at #1105's head passed 3,627 tests, with 18 skipped and 1 expected failure, and the
four per-layer branch-coverage floors at 100% (#1105); that count is a dated figure of
that head, not of this revision.

The 3.1.0 and 3.2.0 additions carry their own tests under the same four floors, which
since 3.2.0 are also declared to the forge as a coverage rule on both permanent branches
(`minimum_coverage = 100`, #1277), though the forge refused every reconcile of that rule
until #1321, after 3.2.0; read on 2026-10-02, both branches' rulesets carry it.
Abandonment is tested from the phase machine through
the store and the command line (`tests/domain/test_abandonment.py`,
`tests/cli/test_abandon_cli.py`); the defect signature and the plan-reference rule are
pure functions with tests of their own (`tests/domain/test_defect.py`,
`tests/domain/test_plan_references.py`). Two regressions of packaging and deployment
are pinned where they happened: `tests/meta/test_wheel_ships_migrations.py` builds the
real wheel and asserts that every migration is in it, and
`tests/infrastructure/db/test_keda_scaler_query.py` holds the KEDA scaler's query to
the claim's own conditions, word for word. `tests/meta/test_minimum_specs.py` holds the
requirements table to its record, `tests/meta/test_first_screen.py` the README's first
screen to its contract and its links to what they name, and
`tests/meta/test_published_figures.py` the figures it quotes to the test they come
from. One measurement is reported as it came out rather
than as hoped: on a canary-injection issue, the frame that quotes an admitted issue to
DESIGN did not stop the canary (4 of 10 runs with the raw intake, 5 of 10 framed), so
the trust check that holds a stranger's issue, not the frame, is the control that holds
(`CHANGELOG.md`, 3.1.0).

The changes after 3.2.0 are validated more narrowly than they are built, and we say
where. The review lane's repair (#1316) is held by 31 tests of its own
(`src/vibey_tools/gh/test/test_local_review_budget.py`), but its rates and its 900 s wait
come from the model server's log, and in production, at our cutoff, every verdict it gave
was on a diff reviewed in one request. The review canary (#1325) is held by its own tests
(`src/vibey_tools/gh/test/test_review_canary.py`): the corpus builds with its pin
reachable, each planted defect is located by its anchor and by its line, and the ledger
refuses an edited line; its measurement is one run, and the weekly workflow that would
repeat it has not run. The autonomy scorecard (#1335) and the host's health and tuning
(#1330, #1334) are tested against fixture records, with every host input injectable and a
guard that fails any test that reaches the real host (`tests/scripts/test_autonomy_scorecard.py`,
`tests/scripts/test_host_health.py`, `tests/scripts/test_host_tuning.py`); the scorecard's
workflow has not run, both its readings were taken outside it, and the host's Linux probes
have run only on fixture trees. The stage that builds every client for a
release (#1317) ran in earnest for the first time on 3.3.0: it attached eleven files, and
the operator found each matching its checksum and carrying an attestation (#1320). Its
macOS bundler (#1351) is held by tests over a fake command runner
(`tests/scripts/test_macos_app_bundle.py`) and by CI's macOS cell, which builds, verifies
and launches the app; its Developer ID signing and notarisation have run only against that fake, because no
credential exists, and the release workflow's tracking issue for them has never been
raised, because no release has built the app yet. The iOS build has run only in dry runs. The Linux requirements (#1313) were seeded in containers on one Mac, and the
native matrix has not run. The shutdown repair (#1309) reproduces the cross-loop error CI
saw before its fix, and the database repairs (#1310, #1314, #1326) reproduce each of the
race's three messages; all were found by CI rather than by review. The race in the tests
behind them was closed by #1332, and green runs alone cannot show that, because the race
was intermittent: the fix holds by construction, since no other worker's reconcile can
now fall between a test's grant and its revoke.

CI itself changed in three places. The KEDA contract of the cluster smoke test raced a
worker's drain (#1327). Under Helm 4, whose `--wait` counts a terminating pod as still in
progress, an upgrade that replaced a worker in the middle of a job timed out while the
worker, correctly, kept draining, so whether the step passed depended on whether a job was
in flight. It now waits for what it checks, the deployment's availability and the
scaler's readiness, and Helm's version is pinned, so a new release cannot change how the
upgrade waits without a commit. The Arch Linux desktop job failed before building
anything when its image's one package mirror failed (#1333); it now falls through four
official mirrors and retries the install three times, so a real failure still fails. And
the dependency gate no longer runs `npm audit --audit-level=high` itself (#1336).
`vibey-gh advisory-check` fails on the same advisories, except one declared in
`.github/advisory-exceptions.toml`, a protected path that needs the code owner and a human
merge. An exception names one advisory in one package in one workspace, states why the
vulnerable code is not reached, and expires within 30 days; the check prints every
exception it honours, and fails when one has expired, matches nothing, or its package has
a patched release. The one exception is GHSA-86w9-cpqp-85rv, a signature forgery against
low-exponent RSA keys in node-forge 1.4.0, which has no patched release, excepted from
2026-10-01 until 2026-10-31. Its evidence is that node-forge reaches the app only through
Expo's developer command line, that neither the exported web bundle nor the Android bundle
contains it, and that the command line verifies only the developer's own certificate and
signatures it has just made, with keys generated at the default exponent of 65,537. That
is a risk accepted with a date on it, not a fix (`SECURITY.md`).

```latex
\begin{plainwords}
We check the system three ways. Tests that walk every branch of the important code. A chaos test where helpers crash on purpose while a real database is running, to prove that no job is lost and no job is done twice. And a live run of a whole project on two different robot helpers, including a forced switch from one to the other in the middle. The newest parts were also attacked on purpose by separate reviewers, who tried to break them before we wrote about them here.
\end{plainwords}
```

## Related work

Queue-based job schedulers built on `SKIP LOCKED` provide claims, leases and retries
but no delivery semantics; the ledger here is event sourcing applied above the queue,
with the write-ahead discipline of ARIES and the lease bound of Gray and Cheriton.
Agent frameworks such as SWE-agent and AutoGen provide sessions and tool loops but
bind state to one vendor's context window; here the session is disposable and the
ledger is not. Selection reuses nginx's smooth weighted round robin and the circuit
breaker pattern. Platform-native automation (merge queues and required checks)
enforces revision-bound *checks* but leaves verdict freshness to its consumers; the
exact-head calculus closes that gap. Yanking semantics for published artifacts (PEP
592) informed the report-only supersession of releases, and keyless publishing through
PyPI's Trusted Publishers removes stored release credentials. Degraded-mode design
follows the fail-operational tradition, with the difference that our refusals include
commercial ones, which is why fallback lattices are ordered by how hard a lane is to
refuse rather than by mean time between failures. The retrieval engine is lexical
over SQLite FTS5; dense retrieval would reintroduce the nondeterminism the
reviewability invariant forbids. The upward drift of the throughput band is the
continuous batching of Orca, and the coordination cost that the six-material postulate
treats as a coupling is the one Brooks described for human teams. The bound on what
more lanes sharing one model slot could buy is Amdahl's. The ledger guard uses
PostgreSQL's own trigger and privilege machinery rather than rules, whose documented
behaviour on partitions and `TRUNCATE` is what left the earlier guard open.

## Conclusion

Putting the ledger, not the session, at the center makes autonomous delivery
survivable and auditable: engines become fungible, crashes become replays, and
human authority is a structural property of the state machine rather than a
prompt-engineering hope. The same discipline, binding every claim to the state it
describes, governs the runners beneath the orchestrator and the release calculus above
it. In the project's controlled record, production kept to a band set by its
substrate, and the inputs that stopped work were decisions and judgments. The 3.0.0
record says the same from three more directions. A local storm was bound by one model
slot and converted no lane without a person; the audit that found this was mostly wrong
until it was verified; and on the day the release's fixes landed, the step that
limited delivery was independent review, which merging outran and then had to repay.
The guarantees added in 3.0.0, a ledger the database refuses to rewrite, a queue
order that cannot be moved from outside, an engine that cannot see the worker's
secrets, and a reviewer that will not grade what it did not read, are each stated here
with the limits they do not cross. Releases 3.1.0 and 3.2.0 add an exit that stops a
project cleanly and releases what it held, branches a project must prove are its own,
a trust check before an issue reaches the delivery path, a gate for a failure that
repeats, and notices to a person recorded as evidence rather than assumed. A scan of the
integration branch after 3.2.0 found the loop autonomous only in BUILD, every merge made
through the ruleset bypass, and seven defects, three of them failures of evidence, among
them a review shown numbers nobody measured; the repairs landed within a day, and still
through the bypass. After it, the local reviewer's missing verdicts on large diffs were
traced to an answer nothing bounded and a deadline that did not grow with the request,
and a release learned to carry a build of every client. The first now names why it gives
no verdict but has yet to bring a large diff to one in production; the second did it for
real in 3.3.0, eleven files whose checksums and attestations all held, and 3.4.0 is to add a
macOS app and an iOS build to them. The reviewer's recall has now been measured once, on
small planted defects, and it showed a reviewer that can describe a defect and still pass
it; why it fails on large diffs is under a preregistered study that has reached its
mechanism and finished screening four diffs, not its result, and production is unchanged
until it does. On those four diffs the model failed to answer in three different ways, and
five arms answered on all of them, every arm that bounds its reasoning and then forces a
verdict among them. The distance
from running without a person is now measured weekly rather than written once, and at each
of its first three readings one of eleven stages met its thresholds. The
engineering that remains is less about producing faster than about deciding well and
cheaply.

```latex
\begin{plainwords}
Put the notebook, not the robot, at the centre. Then any robot can be swapped out, a crash just means reading the notebook again, and people stay in charge at the right moments. The machines are already fast enough. The work ahead is helping people decide well, cheaply, and on time.
\end{plainwords}
```

## References

- PostgreSQL Global Development Group, *SELECT — The Locking Clause* (`FOR UPDATE SKIP LOCKED`, available since PostgreSQL 9.5). PostgreSQL documentation, `https://www.postgresql.org/docs/current/sql-select.html`.
- M. Fowler, *Event Sourcing*, 2005. `https://martinfowler.com/eaaDev/EventSourcing.html`.
- P. Helland, "Immutability Changes Everything," *Communications of the ACM* 59(1):64–70, 2016. doi:10.1145/2844112.
- C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh, and P. Schwarz, "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging," *ACM Transactions on Database Systems* 17(1):94–162, 1992. doi:10.1145/128765.128770.
- C. Gray and D. Cheriton, "Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency," *Proceedings of the 12th ACM Symposium on Operating Systems Principles*, 1989, pp. 202–210. doi:10.1145/74850.74870.
- nginx, smooth weighted round-robin upstream balancing, introduced in nginx 1.3.1 (2012), `ngx_http_upstream_round_robin.c`.
- M. T. Nygard, *Release It! Design and Deploy Production-Ready Software*, 2nd ed., Pragmatic Bookshelf, 2018 (the circuit breaker pattern).
- J. Yang, C. E. Jimenez, A. Wettig, K. Lieret, S. Yao, K. Narasimhan, and O. Press, "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering," *NeurIPS*, 2024. arXiv:2405.15793.
- Q. Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," 2023. arXiv:2308.08155.
- G.-I. Yu, J. S. Jeong, G.-W. Kim, S. Kim, and B.-G. Chun, "Orca: A Distributed Serving System for Transformer-Based Generative Models," *16th USENIX Symposium on Operating Systems Design and Implementation (OSDI)*, 2022.
- F. P. Brooks, Jr., *The Mythical Man-Month: Essays on Software Engineering*, Addison-Wesley, 1975.
- PEP 592, *Adding "Yank" Support to the Simple API*, Python Packaging Authority, 2019.
- PyPI, *Trusted Publishers*, `https://docs.pypi.org/trusted-publishers/`, 2023.
- GitHub, *About protected branches and rulesets*, GitHub Docs, 2024.
- SQLite, *FTS5 Extension*, `https://www.sqlite.org/fts5.html`.
- G. M. Amdahl, "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities," *Proceedings of the AFIPS Spring Joint Computer Conference*, 1967, pp. 483–485. doi:10.1145/1465482.1465560.
- PostgreSQL Global Development Group, *The Rule System* and *CREATE TRIGGER* (rules and row-level triggers on partitioned tables; `TRUNCATE` triggers). PostgreSQL documentation, `https://www.postgresql.org/docs/current/`.
- The vibey repository: the sovereignty stress record, `src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md`; the evidence script, `scripts/paper_evidence.py`; the figure generator, `scripts/paper_figures.py`; the minimum-requirements record and its generator, `docs/architecture/evidence/minimum-specs.json` and `scripts/minimum_specs.py`; the review canary's corpus and ledger, `docs/architecture/evidence/review-canary/`; the autonomy scorecard's record and its generator, `docs/architecture/evidence/autonomy-scorecard.jsonl` and `scripts/autonomy_scorecard.py`; the host-health record, `docs/architecture/evidence/host-health.jsonl`; the large-diff study's preregistration, log and data, `research/large-diff-review/experiments/`; the architecture decision records, `docs/architecture/decisions/`; `https://github.com/the-vibey-project/vibey`, 2026.

## Citing this work

To cite this paper, use the entry below; the repository's `CITATION.cff` carries the
same record for citation managers and for GitHub's *Cite this repository* button. No
DOI or preprint identifier has been assigned yet, so the entry points at the published
PDF.

```bibtex
@misc{steinberger2026ledger,
  author = {Steinberger, Adam Matthew},
  title  = {Ledger-Mediated Orchestration:
            Vendor-Independent Autonomous
            Software Delivery over a Pool
            of Coding Agents},
  year   = {2026},
  url    = {https://the-vibey-project.github.io/vibey/main/paper.pdf},
  note   = {Source: docs/paper.md in
            github.com/the-vibey-project/vibey}
}
```

## A call to FOSS developers

Everything in this paper is free and open-source software, built in the open, and it
is not finished. The machines that write code are cheap now; what is scarce is
infrastructure a person can own, governance that holds up when nobody is watching, and
evidence honest enough to publish. If you write software and any of that speaks to
you, come and build it with us.

- Join the conversation on Discord: [discord.gg/Qvu8aYnVS](https://discord.gg/Qvu8aYnVS).
- Read how to join me and what to work on first: [vibewithadam.matthewsteinberger.com/join-me](https://vibewithadam.matthewsteinberger.com/join-me).

- Start with the contribution guide, [`CONTRIBUTING.md`](https://github.com/the-vibey-project/vibey/blob/develop/CONTRIBUTING.md), or the first-hour path at the top of the README.

Bring your questions, your critiques and your pull requests. Whether you care about
queues and ledgers, sovereign local models, reproducible benchmarks, or the young field
of Biodigitology, there is a lane for you.
