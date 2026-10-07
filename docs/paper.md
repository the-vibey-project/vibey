# Ledger-Mediated Orchestration: Vendor-Independent Autonomous Software Delivery over a Pool of Coding Agents

**Abstract.** A single autonomous coding session is not autonomous software delivery:
it loses its state when it crashes, it dies when one vendor's quota is exhausted
mid-task, and it has no place where a person is required to decide. We present a
ledger-mediated orchestration model built on three constraints and one calculus. All
delivery state is a pure function of an append-only ledger,
$\mathrm{state}(t) = f(\mathrm{ledger}_{\leq t})$, so a handoff between engines is a
scheduling event rather than a loss of state; the database now enforces the invariant,
and we state what it still cannot refuse. A handoff is admitted only by a pure, model-free no-loss predicate. Four human
gates in a six-phase machine each require a recorded verdict, which silence never
supplies. And an exact-head calculus binds every automated verdict to the revision it
judged, with a production trace in which a budget guard ran before the freshness test
and escalated a head that no longer existed. Beside these, a capacity taxonomy gives a
rate window a deadline and exhausted credits none, and lets a capacity verdict outrank a
completion claim. Supporting mechanisms follow: a leased PostgreSQL queue, an
allow-listed engine environment, and a reviewer bound to what it read. The evidence is
one project's tracked records. On one 24 GB machine with a fixed local model and a 900 s
deadline, successful throughput sat between 0.99 and 2.00 generations per minute for
offered concurrency 2 through 32, left that band at 64 and 96, and collapsed at 128: a
single-slot saturation curve, not a general law. The local reviewer caught 18 of 25 small
planted defects (Wilson 95% interval 0.524 to 0.857), blocked none of 14 clean changes,
and twice passed a defect its own summary named. A scan of the integration branch found
that only BUILD ran without a person and that the forty merges before it went in through
the ruleset bypass. Adversarial verifiers refuted 16 of 18 leading claims of a storm
audit. We say what the records do not show, including that no controlled comparison with
another delivery system has been run.

*Artifacts.* This paper is typeset from `docs/paper.md` and published as
[PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/paper.docx) and
[HTML](https://the-vibey-project.github.io/vibey/main/paper/). The complete
documentation is published as a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/book.docx),
[EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) and
[print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html). Every
empirical figure in the section on what the records measure is recomputed from tracked
sources: `scripts/paper_evidence.py` recomputes its numbers, `scripts/paper_figures.py`
redraws its figures, the storm's `storm-evidence.py` regenerates its evidence table,
`scripts/minimum_specs.py` its tables of minimum requirements, and
`scripts/autonomy_scorecard.py` its autonomy scorecard. The one exception, the storm
throughput audit, is named where we use it. The large-diff study we report is in
progress, and its committed record is cited at the cutoff its own log gives. Unless a
passage names its own, the evidence cutoff is `develop` at `3bb577a4e` (#1354), with
the forge read on 2026-10-02 between about 10:55 and 11:20Z; what the paper says of the
3.4.0 release is at `develop` at `4d51a764c` (#1365), with the forge read at about
17:45Z. This revision restructures the paper after an external review, at `develop` at
`c8d8d2cce` (#1440) on 2026-10-06; it adds no measurement, and where it names the 4.0.0
and 4.1.0 releases it reads `CHANGELOG.md` at that revision. The visual atlas holds forty
figures: twenty-five drawn from the model as deterministic TikZ in this source, and
fifteen computed from tracked repository records, so the PDF, its labels and its diagrams
are reviewable and reproducible rather than screenshots detached from the system. An
executive summary follows, naming the section that carries each claim. Every section
from the Introduction to the Appendix closes with a box headed
*In plain words* that restates it for a reader who is not a specialist; the boxes add
nothing the formal text does not say, and a specialist may skip them.

<!-- vibey:provenance -->

## Executive summary

Each item names the section that carries it.

- **Introduction.** A coding session is not a delivery system: it loses its state on a crash, dies with one vendor's quota, and has no place where a person must decide. The paper's three contributions are the ledger invariant with what the database does and does not enforce, the no-loss handoff gate, and exact-head evaluation with its production counterexample, with the capacity taxonomy beside them; everything else is a supporting mechanism or a measurement.
- **The ledger invariant.** All delivery state is a pure function of an append-only ledger, so a crash is a replay and a handoff is a scheduling event. The invariant was a convention of the application until 3.0.0; the database now refuses updates, deletes and truncation of the ledger, and still cannot stop the application role from forging provenance.
- **The no-loss handoff gate.** A handoff between engines is admitted only by a pure, model-free predicate over the brief and the ledger. A failing handoff is retried, escalated to the full transcript, or parked for a person, never a silent partial.
- **Capacity verdicts.** A rate window may carry a deadline; exhausted credits never acquire one, which the type, a property test and a database constraint each enforce. A capacity verdict outranks a completion claim, in the orchestrator and inside every runner.
- **Exact-head evaluation and the release calculus.** Every automated verdict is a claim about one exact commit and speaks for no other; the review and repair loop terminates in a bounded number of repairs; a production trace shows a budget guard that ran before the freshness test and escalated a head that no longer existed. The local reviewer is bound to what it read, caught 18 of 25 small planted defects (Wilson 95% interval 0.524 to 0.857) and blocked none of 14 clean changes, and its failures on large diffs are under a preregistered study (`research/large-diff-review/experiments/`) with production unchanged.
- **Queue semantics.** Work is claimed with `FOR UPDATE SKIP LOCKED` under renewable leases; execution is at least once and the acknowledgement is fenced so exactly one commit lands per job; a priority lane is derived from the record, never remembered, and never admits past a gate.
- **The six-phase machine.** Four human gates, each a parked job plus a recorded verdict; silence never decides unless a project has declared, kind by kind, that a deployment gate may resolve to its stored default; an operator can abandon a project from any phase.
- **The engine family.** One bounded, never-blocking core under every runner; an environment assembled from an allow-list, never copied from the worker; a sovereign local driver with a measured fit; local engines chosen first by smooth weighted round robin, paid engines as the fallback.
- **Deterministic retrieval and fail-closed bootstrap.** Lexical retrieval a reviewer can replay, and a bootstrap layer that appends before it acts.
- **What the records measure.** A single-slot saturation curve on one 24 GB machine: 0.99 to 2.00 generations per minute from offered concurrency 2 through 32, leaving the band at 64 and 96 and collapsing at 128. A local pilot; a storm ledger whose audit adversarial verifiers refuted in 16 of 18 leading claims; host benchmarks and weekly minimum requirements; the repository's own history; an autonomy scan that found only BUILD running without a person and forty merges made through the ruleset bypass; and a completion-time prediction that holds inside the band only, with what would falsify it and what it does not cover.
- **Comparison with alternatives.** How ledger-mediated orchestration differs in kind from a session runner that keeps its transcript as truth, from an outbox plus a workflow engine, and from a CI ruleset plus a human approval; and that no controlled head-to-head has been run.
- **Discussion.** Convergence-Driven Development kept as a scoreboard, and the claim that governance is the scarce input narrowed to this project's record.
- **Validation.** The property, chaos and live levels at which the model is checked, and how the paper's own figures are reproduced.
- **Related work.** Where the ledger, the gate and the calculus sit beside schedulers, event sourcing, agent frameworks, workflow engines and platform automation.
- **Conclusion.** The ledger, not the session, at the centre; and what remains to be measured.
- **Declarations.** Where the data and code are, how generative AI was used, who the author is and under what funding and interests, and which reporting guidelines and registrations apply.
- **Appendix.** The operational record from 3.0.0 to 4.1.0, for an operator of this repository.

```latex
\begin{plainwords}[The paper in plain words]
Computers can now write computer programs. But one robot programmer working alone is not enough to finish a real project. It forgets everything when it crashes. It runs out of its allowance in the middle of a job. And it does not know when a person needs to make a decision. Vibey fixes this with three ideas. First, a notebook that nobody can erase: every decision, every finding and every handoff is written in the notebook before it counts, so a new helper can pick up exactly where the old one stopped. Second, a queue with rules: jobs wait in line, a helper borrows a job for a short time and must keep renewing it, and a job that a crashed helper dropped goes back in the line by itself. Third, six checkpoints, and at four of them a person must say ``yes'' out loud before the work moves on. We also timed one small computer. Asked to do more at once, it finished about one or two pieces a minute until it was overloaded, and then it fell over. That says what one machine can do, not what the world can do. And we say plainly what we have not yet measured. Every section below ends with a box like this one.
\end{plainwords}
```

## Introduction

Let an *engine* be an autonomous coding session runner over one vendor's model, and
let $E = \{e_1, \dots, e_m\}$ be a pool of such engines with independent failure and
capacity behavior. A coding session is not a delivery system: it loses its state when
the process holding it crashes, it dies with the quota of the one vendor it runs on,
and it has no place at which a person must decide. The delivery problem is to carry a
specification from human intent to deployed software over $E$ under three constraints
that single-session tooling violates: (i) no vendor session may be the source of
truth; (ii) human decisions must occur at defined points, not wherever a session
stalls; (iii) exhaustion of one vendor's capacity must not lose work.

We answer them with three rules, each stated formally below and checked against the
project's own records. First, state is a pure function of an append-only ledger:
nothing is updated or deleted, a correction is a new event that supersedes an earlier
one, and a worker that dies is replaced by one that replays. Second, a handoff from an
exhausted engine to the next is admitted only by a model-free no-loss predicate, a
check on the brief that no model evaluates; a brief that fails it is never passed on
as a silent partial. Third, silence never counts as a verdict, and a parked job is a
row in the database, not a thread waiting on a terminal: a gate no person has answered
stays open unless a project has declared, kind by kind, that a deployment gate may
resolve to its stored default.

The system that embodies these rules is one repository holding a family of packages:
the orchestrator; session runners over paid vendor models and over a local model; a
tool that owns provenance, merging and release; a retrieval engine over a skill
library; and a bootstrap layer for cloud workloads. [Fig. 1](#fig:delivery-pipeline)
shows the path a unit of work takes: a triaged issue is claimed under a lease held in
PostgreSQL, becomes a project in its own worktree, is built by the local engine, stops
at a human review gate, and is published as a draft pull request that the merge train
takes only when every check is green. The bridge that feeds the machine never edits a
branch: the worker writes code, the phase machine decides when it may, and the forge
decides when it merges. Every exit that is not a success (an expired lease, a capacity
pause, an open gate, a red check) is written to the project's evidence record as what
it was, never as a completion.

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

Our contributions are three. The first contribution is the ledger invariant, with a
soundness argument and a statement of what the database enforces about it and what it
does not: an application role can still write provenance it did not earn. The second
contribution is the no-loss handoff gate, a predicate on a handoff brief that no model
evaluates. The third contribution is exact-head evaluation, a release calculus that
binds a verdict to the revision it judged, with a repair bound, the condition under
which it terminates, and a recorded production counterexample. Beside these three sits
the capacity taxonomy: a credit balance is never given a clock, and a capacity verdict
always outranks a completion claim.

Supporting mechanisms carry the contributions into a running system, each stated below
with its own evidence: the onion architecture of the orchestrator; a queue on
PostgreSQL with leases, so a dead worker's job is reclaimed; the six-phase machine and
its four human gates; an environment every engine starts from by allow-list; a
priority lane whose contents are derived from the record rather than remembered, so
that it orders work without preempting it or admitting it past a gate; the checks that
bind a reviewer's verdict to the input the model actually read; and the sovereign
driver that runs the local model.

The evidence is one project's records: a single-slot saturation curve measured on one
machine; a canary that measured the local reviewer's recall on planted defects; an
audit of a local storm that located its binding constraint, its conversion losses and
its declared but unenforced controls; and a scan, on 2026-09-30, of how far the
delivery loop ran without a person.

The orchestrator itself is an onion of four layers with dependencies pointing inward
only ([Fig. 2](#fig:layer-map)): a pure `domain` with no I/O, no clock and no network;
an `application` layer of services; an `infrastructure` layer that talks to
PostgreSQL, the bus and telemetry; and the `cli` and `tui` shells. A single
composition root, `bootstrap.py`, wires them. The rule is enforced by an import linter
in CI, and four of the five layers fail the build under 100% branch coverage.

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

What the body does not do matters as much. We ran no controlled head-to-head against
another system. Every measurement is one project's records read at a named cutoff, and
none is a claim about other projects or other models. Convergence-Driven Development
appears only as a scoreboard in *Discussion*. The operational record from release
3.0.0 to 4.1.0 is an appendix.

```latex
\begin{plainwords}
Think of a team of robot helpers, each from a different company. Any of them can quit halfway through a job, and none of them remembers anything once it crashes. Vibey is the team captain. It keeps one shared notebook that nobody may erase, hands out jobs one at a time so that a job whose helper quit can be picked up by the next one, and stops at fixed moments to ask a person. The rest of this paper explains each part, and then checks the whole design against real records from the project's own history, including the places where it did not work.
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

The ledger admits inserts and nothing else: no updates, no deletes. A correction is a
new event that supersedes the one it corrects, and the record of the mistake stays. The
per-project sequence number is claimed inside the same transaction as the insert, so
every ledger range has a well-defined digest. Every event also carries a link, the
SHA-256 of the link before it and of every stored field of the event, from a genesis of
the project's own; the chain is derived from the rows rather than stored, so it covers
all of history, and a published ledger shard carries its verified chain head. The chain
detects a rewrite. It does not detect a forged append, a limit we return to below. The
function $f$ is a set of pure projections (the open items, the decision log, the cost
report) computed from the event sequence alone.

Two properties follow from the invariant rather than from any worker: a crash is a
replay, and a handoff is a scheduling event. Every job is idempotent under replay: a
worker that dies mid-job has recorded its intent before each effect, its lease expires,
and the next worker re-derives the same state from the record and continues, with
duplicates dropped by identity. Crash recovery and engine handoff follow as
corollaries: a successor engine re-derives its context from the ledger alone, so a
credit exhaustion on $e_i$ between turns of an item reschedules the item onto $e_j$
with the open-question set intact. [Fig. 3](#fig:ledger-handoff) draws the cycle: each
engine turn appends its events before anything acts on them, and when an engine runs
dry the brief that seeds its successor is checked against that ledger by the no-loss
gate (see *The no-loss handoff gate*), then retried, escalated or parked for a person,
never silently dropped.

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

The same rule holds at two further scales, in two other parts of the system, and
[Fig. 4](#fig:record-effect) shows the three side by side. At the orchestrator scale the
ledger event is appended, the state is projected from it, and only then may the job
proceed. At the service scale a transactional outbox row is committed in the same
transaction as the state change it announces, a dispatcher reads committed rows only,
and the external call is made at least once and marked delivered once. At the audit
scale a chain link $c_i = H(c_{i-1} \| r_i)$ is appended, a verifier re-hashes from
$c_0 = H(r_0)$, and any edit breaks every later link. In each lane the record is durable
before the effect is allowed, and a crash at any step replays from the record.

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

### What the database enforces, and what it does not

Until 3.0.0 the invariant was manners, a convention of the application. It held
against vibey's own queries and against little else: two `DO INSTEAD NOTHING` rules on
the partitioned parent table `event`.
ADR-0055 records what a scratch database with every migration applied (PostgreSQL 18)
did on 2026-09-24 when addressed as the role vibey connected as. An `UPDATE` of `event`
changed nothing, silently, so the attempt was hidden rather than refused. An `UPDATE`
and a `DELETE` addressed to the default partition changed and deleted rows, because a
rule on a partitioned parent does not fire for a statement aimed at a partition.
`TRUNCATE event` emptied the ledger, because rules never fire on `TRUNCATE`. After
`DISABLE RULE` an update went through. The role that connected owned the table, and in
the Helm chart it was also the image's superuser; the same DSN had reached every engine
session (*What an engine may see*), so a session steered by text a model had read held
the means to erase the ledger unrecorded.

The repair (#1100, ADR-0055) has two parts, because neither alone is a boundary. First,
triggers replace the rules: a row trigger before update or delete and a statement
trigger before truncate refuse every rewrite, the owner's included, with an error rather
than a silent no-op. PostgreSQL clones the row trigger onto every partition, present and
future, but not the statement trigger, so a function attaches the truncate guard to
every partition on every migration run. Second, the roles split. The owner's DSN runs
migrations and nothing else. The application role, which every worker, command,
operator and scaler connects as, owns nothing and holds on `event` only `SELECT` and
`INSERT`, with no `DELETE` or `TRUNCATE` anywhere. Its grants are declared in code,
derived from the application's own queries, and reconciled on every migration run, so
a grant added by hand does not survive the next one. The whole test suite now runs as
that restricted role; its first run found 35 failures, none a missing grant in
application code, all of them test setup doing owner-only work or assertions of the
old silent no-op.

What the guard refuses is recorded three ways. The independent review of #1100, as the
application role, tried updates, deletes and truncations of the parent and of
partitions, disabling, re-enabling as replica and dropping the triggers, detaching and
attaching partitions, and switching the session to replica mode, and every one was
refused (review probes of 2026-09-24). The merged tests pin the refusals of updates,
deletes and truncations of the parent and of a partition, and of disabling or dropping
the triggers; the rest remain review probes, not tracked tests. At the cluster level a
cluster-smoke step checks the same contract: as the worker's role, an update, a delete
and a truncation of the ledger are refused for want of privilege and disabling a
trigger is refused as not the owner; as the owner, all three are refused by the
triggers (#1100).

The guard's reach is narrower than the word *append-only* suggests, and we state it.
The triggers refuse the owner's rewrites of rows, not the owner's schema changes: the
owner can still disable a trigger, drop a partition, detach one and delete from it, or
truncate a partition created since the last migration run, so the owner's DSN is the
thing to guard. Event triggers that would refuse such changes need a superuser to
install and are future work; a superuser can do anything. The application role cannot
rewrite what is there, but it can still insert into `event` directly, so it can forge
an event's provenance, sequence number or production time, and it can update the
sequence counter; an append function running with the owner's rights, as the only
write path, would close that, and it is the next step, not a done one (ADR-0055). And
the split protects the ledger only once the owner and every superuser need a password:
a local PostgreSQL that trusts its socket, the common developer default, lets any
process running as the right operating-system user connect as a superuser with no DSN
at all, and ADR-0055 records exactly that on the operator's machine. Same user, same
authority: no grant separates processes of one operating-system account.

The record of the repair is not clean, and we keep it. The review found the design
sound and five defects in its first implementation, two rated high, and #1100 had
merged while the review said *not yet*; #1112 closed all five on 2026-09-24. The worst:
where the application role may create objects in the `public` schema, the PostgreSQL 14
default and that of any database upgraded from it, it could plant an operator that the
owner's unqualified catalog query resolved during migration, run code as the owner,
and leave a backdoor that erased the ledger while the migration reported the guard in
force. ADR-0055, as first merged, had judged that privilege harmless to the ledger, and
was wrong; the repair pins the search path of the guard functions and of the owner's
session and takes `CREATE` on `public` from every role but its owner, and the appendix
records the migration that does so. The second: the owner's DSN reached any process
whose shell exported it, because the application's start-up read it and the README
exported it; now only the migration command reads it. #1112 promised an independent
re-review before the operator's merge; no verdict on the merged result is recorded in a
tracked source, so we report the fix, not a review of it.

One privilege the guard must revoke is not per database. The grant that lets a role set
`session_replication_role`, which silences every trigger, the ledger's guard included,
lives in one `pg_parameter_acl` row for the whole cluster, so two reconciles on
different databases of one cluster race on it, and the per-database migration lock
cannot serialize them. Until #1310 the loser's revoke failed and the reconciler
swallowed every database error at that step, so the grant could stay in place without
a word. It was CI, not the authors, that found it: a pull request's checks on
PostgreSQL 16 showed the application role still able to set the parameter after a
reconcile. One race then produced three distinct error messages, and chasing them one
at a time sent us after its cause in the tests (#1332); the tests now serialize their
grants of that privilege, which repairs the tests only. In production the race remains,
and what holds is a bounded retry that matches the three messages; a lock that spans
the cluster is a recorded follow-up, not a repair (#1326, #1332).

```latex
\begin{plainwords}
The ledger is a diary written in pen. You can add a page but never tear one out; a mistake gets a new page that says so. Because the diary is the only source of truth, any helper can read it and catch up. Until recently that promise was only good manners: anyone with the main key could tear pages out. Now the database itself refuses, helpers hold a key that can only read and add pages, and the key that could switch the refusal off is kept from them. A helper can still add a page that lies about who wrote it; closing that is the next job, and the computer's owner can still do almost anything.
\end{plainwords}
```

## The no-loss handoff gate

A handoff from engine $e_i$ to engine $e_j$ carries a *brief* $\beta$: objective,
constraints, done and remaining work, open questions, decisions, assumptions, findings,
artifacts, and a reference $\rho$ to the ledger range it summarises. The brief is
admitted only if a pure predicate $\mathrm{gate}(\mathrm{ledger}_{\rho}, \beta)$ holds,
evaluated without any model call. Pure means the predicate is a function of its two
inputs, the ledger range and the brief, and of nothing else.

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

The gate has modes. In *strict* mode all ten rules apply. A failing brief is
regenerated with the specific violations fed back, up to three strict attempts. The
gate then escalates to *full-transcript* mode, which makes the brief advisory: the
successor is to work from the whole range $\rho$, so the gate stops checking R1--R5, R7
and R9, while R6, R8 and R10 still run, because they check facts about the range and
the brief's containment rather than its completeness. Further failure parks the item on
a *human* gate, a parked job that a person decides. A fourth, *forced* mode is reserved
for an explicit operator override. As [Fig. 3](#fig:ledger-handoff) shows, a handoff
that fails the gate is a retry, an escalation, or a human decision, never a silent
partial.

The full ledger range is always written to disk inside the receiving worktree, and the
seed prompt names it. In the current implementation that file is how the range reaches
the successor; it is not inlined into the seed. In full-transcript mode, therefore,
completeness rests on the successor reading the file, not on the gate. Inlining the
range into the seed, or keeping the closure rules enabled until it is inlined, is open
work.

The same gate guards a second handoff that never touches the project ledger
(ADR-0070): the operator's own driving session, on a capacity rejection, fails over to
the sovereign engine and later hands back. Its brief names the session transcript by
path, line count and SHA-256 with the repository head, and the gate checks that digest
against the transcript as it stands (`vibey.domain.driver_brief`). The modes are the
same; the failover is appended to the driver's own append-only, hash-chained ledger
before the local run starts; the handback is allowed only after a successful probe of
the exhausted engine is recorded, and its return brief is gated the same way; nothing
starts on a failed gate.

```latex
\begin{plainwords}
When one helper hands a job to another, it writes a short note: what the job is, what is done, what is left, and which questions are still open. Before the new helper may start, a strict checker compares the note with the diary. If the note forgot an open question, the checker says no and asks for a better note, up to three times. After that it tells the new helper to read the whole diary instead. If even that fails, a person is asked. Nothing is ever quietly lost.
\end{plainwords}
```

## Capacity verdicts

Every answer an engine returns is sorted into a capacity value before its completion
claim is read. The discrimination the family is built around separates a *window*, a
rate limit that will reopen, from exhausted *credits*, a balance that no amount of
waiting refills.

```latex
\begin{invariant}[Waitability]
A window is waitable under a deadline: a bounded probe re-tests capacity and the
excursion is capped by $W_{\max}$. A credits state carries no deadline at all. It may
be re-probed on a bounded backoff in case a human tops the balance up, but it is never
scheduled as if it will reopen at a time.
\end{invariant}
```

In the orchestrator capacity is four-valued: available, a waitable window with an
optional reset time, exhausted credits, and failed authentication. The rule that
credits have no clock is enforced at three independent layers. The credits type has no
reset field; a property test asserts that no credits state ever produces a deadline;
and a database `CHECK` constraint rejects an engine-health row that pairs exhausted
credits with a reset time.

The runners classify in the same order of precedence. `claudeloop` checks credit
signals before the window path, so a billing failure is never read as a waitable
window even when a stray reset time rides along with it. `codexloop` keys on the
vendor's machine-readable error code and type before anything else
(`insufficient_quota` is an exhausted quota, never a window), consults the HTTP status
only when neither decides it, and never lets a status, a retry header or a completion
claim outrank a body-level billing marker.

```latex
\begin{theorem}[Capacity outranks completion]
A completion claim observed while capacity is not available is recorded but not
believed: a starved model emits plausible final output, so a run that ends for
capacity is always attributed to capacity and never laundered into success.
\end{theorem}
```

Completion is read from a structured per-turn verdict where the vendor supports one,
with an explicit done marker as the fallback, and the capacity verdict is consulted
first either way ([Fig. 5](#fig:capacity-taxonomy)).

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
  \node[runner] (agy)    at (11.3,1.9)  {agyloop (retired, ADR-0078) $\cdot$ 5 states\\quota day in Pacific time};
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

The taxonomy was stretched at both ends. The Gemini runner still drawn in the figure,
retired by ADR-0078 on 2026-10-03, metered per-model quotas whose dimensions did not
collapse, so it carried a five-member state and computed quota boundaries from the
vendor's Pacific-time day; its probes could tune *when* the next probe fired, never
*whether* a wait ended, and every excursion stayed capped by $W_{\max}$. The local
runner has no vendor. Its capacity is hardware, with the states available, locally busy
and misconfigured, and nobody refills it by adding a payment method. Model acquisition
is explicit: the install-health check never downloads weights, and installing a model
is a separate, deliberate command, because a surprise multi-gigabyte download is itself
a capacity event on the constrained machine the runner exists to respect.

The same order holds above the runners. A capacity rejection defers the job and opens
the rejecting engine's circuit until its backoff passes, and the queue counts a
capacity deferral among the conditions that decide whether an item may run at all,
which a priority bump can never override (*Queue semantics*). The delivery bridge that
feeds the six phases from the forge applies the rule once more
([Fig. 6](#fig:capacity-precedence)): after every worker run it reads the project's
status, and if any job is awaiting capacity or any engine's circuit reports a capacity
state other than available, it records a pause for capacity and stops before it acts
on the run's phase or its open gates. The phase is acted on only on the branch where
capacity was available, so a starved run cannot be laundered into success at either
level.

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

```latex
\begin{plainwords}
An engine can stop for two very different reasons. Sometimes it has hit a speed limit
that lifts by itself, so waiting a bounded time is sensible. Sometimes the account is
simply empty, and no amount of waiting fills it. The system keeps those two apart in
three places at once, so nobody can mark an empty account as ``try again at four
o'clock''. And whenever an engine says ``I finished'' while it was also out of
capacity, the system believes the capacity signal and not the finish, because a
starved model still produces confident-looking output. The same check runs again one
level up, before any stage of the work is marked done.
\end{plainwords}
```

## Exact-head evaluation and the release calculus

The orchestrator's output is a pull request, and what happens to it is governed by
`vibey-gh`. Let a pull request's evolution be the finite sequence of *heads*
$H = \langle h_0, h_1, \dots, h_n \rangle$. An automation system emits *claims* (scan
results, review verdicts, gate conclusions) and acts on them by merging, releasing, or
halting for an operator. The folk assumption is that a claim about $h_i$ speaks for the
pull request. It does not: it speaks for $h_i$ alone.

```latex
\begin{invariant}[Exact-head]
Every claim is a pair $(c, h_i)$, and no decision procedure over head $h_j$ may
consume a claim $(c, h_i)$ with $i \neq j$.
\end{invariant}
```

### The calculus and its termination

Evaluation is a pure function over the head, its check results, and a persisted state
$\sigma = (a, r, v, k)$: attempts consumed, last-reviewed revision, its verdict, and
refills used. For head $h$ and repair budget $A$,

$$E(h, \sigma) = \begin{cases} \mathsf{pending} & \text{checks incomplete} \\ \mathsf{review} & r \neq h \\ \mathsf{ready} & r = h \land v = \top \\ \mathsf{repair} & r = h \land v = \bot \land a < A \\ \mathsf{blocked} & r = h \land v = \bot \land a \geq A \end{cases}$$

```latex
\begin{invariant}[Budget placement]
The guard $a \geq A$ is evaluated only where a repair would be spent, strictly
after the freshness test $r \neq h$. Reviews are free; only repairs are counted.
\end{invariant}
```

The implementation refines $E$. It adds a sixth state, $\mathsf{conflict}$, for a head
that no longer merges with its base, budgeted by the same counter as $\mathsf{repair}$.
A failing verdict whose only findings came from the sovereign lane never spends a
repair: the head returns to $\mathsf{review}$. Where no paid lane is declared, as in
this repository, $\mathsf{repair}$ and $\mathsf{conflict}$ are answered by a person, and
a review that reaches no verdict is recorded with a code from a closed vocabulary, never
as a pass. A branch-sync workflow can refill the budget, resetting $a$ to zero, at most
$k_{\max}$ times per lineage (default 2, at most 10); this repository refills only by
hand, under the same bound. [Fig. 7](#fig:evaluation-automaton) draws the function as a
state machine.

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

The hypothesis of the second claim is not a formality, and we state the case it excludes
as a limitation rather than prove past it. A failing verdict whose only findings come
from the sovereign lane returns the head to $\mathsf{review}$ with $(a, k)$ unchanged,
so $\mu$ does not decrease: the lineage spends no repair, but nothing in the calculus
makes it terminate, and the implementation keeps no bound on those re-reviews. The same
holds where no paid lane is declared. [Fig. 8](#fig:exact-head) shows stale claims
invalidated across heads.

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

### A production violation

With the budget guard evaluated *before* the freshness test, the following trace is
reachable: reviews of $h_0$ to $h_2$ fail with findings, repairs produce $h_3$
addressing all of them, $a = A$, and evaluation of $h_3$ hits the budget guard first and
emits $\mathsf{blocked}$. The lineage is escalated as unrepairable on the verdict of
$h_2$, a revision that no longer exists in the pull request. This trace occurred in
production, and its terminal artifact, the escalation report, listed an empty set of
remaining failures. That report is not tracked in this repository. Commit `4afafbae`
reordered the two guards, restoring the budget-placement invariant, and its regression
test asserts that the counterexample now yields $\mathsf{review}$.

### Trust separation and release monotonicity

Four principals operate the loop, and the separation that matters is between judging and
acting. The per-job platform token publishes claims. The reviewers judge: the paid
reviewer through its API key, the sovereign lane on the self-hosted runner. The merge
train merges with the automation token, and the same token pushes the guarded repair and
conflict-resolution commits, so proposing revisions and merging are not held by disjoint
credentials; in this repository paid repair and conflict resolution are declared off, so
that path is dormant here. The fourth principal is bounded by a grant: a delegated
approver, refused by `vibey-gh approve-check` on any change its own account wrote; it is
declared, and by 2026-10-01 its account had approved no merge. The non-collusion
property follows: a compromised judge cannot ship, and a compromised actor cannot write
itself a passing verdict, though it could push a revision that must then be judged
afresh. Third-party revisions are data to every principal
([Fig. 9](#fig:trust-separation)).

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

Versions are derived, not remembered: for mainline $M$ and change set $\Delta$,
$\mathrm{ver}(M \cup \Delta) \geq \mathrm{ver}(M)$, with equality exactly when $\Delta$
carries no shippable content, and the derivation is idempotent, so re-promoting
identical content never compounds a bump. Published versions form a monotone sequence,
and publishing an already-published version is a no-op, never an error.

### Binding the reviewer to what it read

The exact-head invariant binds a claim to the revision it evaluated. A reviewer running
on a local model needs a second binding, to the input the model actually read, because a
local server can read less than it was sent without saying so. In 3.0.0 the review lane
became sovereign by declaration (#1087, #1088): paid review, repair and conflict
resolution are off, and a self-hosted runner, declared as code (#1086), answers the
whole review.

Its first review, of #1090, failed with an unparseable answer. The first diagnosis
(#1094) was silent truncation: at an estimated three characters per token the prompt
came to about 41,000 tokens against a 32,768-token window. That diagnosis was wrong,
and #1101 restates it: the server's counters show 31,765 prompt tokens read and 1,004
generated, the whole window, so the model read its entire prompt and ran out of room to
answer. The error was in the estimate, which now decides only what to trim; the request
itself refuses to be cut. Real truncation looks different, and #1101 reproduced it: a
prompt the server counted as 36,798 tokens was answered with HTTP 200 and a prompt count
of 16,386, about half the window, and refused once truncation was disabled. An
upper-bound check on the server's count cannot see this cut.

The fixes refuse a verdict on a cut prompt four ways (#1094, #1101;
[Fig. 10](#fig:exact-head-lifecycle)). Every request asks the server to refuse rather
than truncate. Every request carries a fresh random check code at the start of the
system prompt and another after the diff, and the answer must echo both, so a cut at
either end is caught. A diff too large for one request is never cut: since 3.1.0 it is
reviewed whole in a bounded number of parts, six by default, split by file and hunk
under every guard, and a pass needs every part to pass at the one head reviewed (#1252);
since 3.2.0 a hunk that only adds lines is split between lines (#1278); a diff that
still cannot be reviewed whole is refused before anything is sent, and the gate asks a
person. And when a supporting document was cut or left out, the verdict claims only the
diff-grounded half of the review and is refused as the whole. A verdict on a prompt the
model did not read in full is refused.

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

Still unmeasured are the check codes' false-refusal rate on live reviews and whether any
pull request has passed the gate on the sovereign verdict alone, which the repository
does not record. The 3.1.0 promotion's own head got no sovereign verdict: one added file
was a single hunk of 136,308 characters.

Bounded parts were not enough for a large diff. The review of #1312 ended with no
verdict, coded `model_timeout` after two attempts. The model server's untracked log,
quoted in #1316, shows a free model that wrote about 9,950 tokens on the first part,
past the 8,192 the request had reserved for reasoning and answer. Nothing capped the
output, and a fixed 600 s deadline that did not grow with the request cut the answer off
unfinished; the retry at temperature 0 ran the same way. The same log holds the failure
this one had been taken for: on 2026-09-30 a review waited about ten minutes behind
another client's request and was then cut off seconds into its own work. Two causes
shared one code.

Pull request #1316, merged on 2026-10-01, separates them and bounds both. The reserve is
sent as the request's output cap, 16,384 tokens by default, and a model that fills it is
refused as out of room, never as a timeout. The deadline grows with the request,
$t = \max(t_0,\; p/r_p + R/r_o)$ for $p$ prompt tokens, reserve $R$, fixed $t_0 = 600$ s
and declared rates $r_p = 200$ and $r_o = 20$ tokens per second. A one-token probe first
waits up to 900 s for the model's one slot, so a busy model is coded `model_busy` and
retried, while a request that started on a free slot and still ran past its deadline is
coded `model_timeout` and is not retried, because at temperature 0 the same request
would run the same way.

In every review run between #1316's merge at 18:16Z on 2026-10-01 and 03:50Z on
2026-10-02, the lane gave seven verdicts, every one on a diff reviewed in a single
request, and blocked one; it gave none on six: three filled the reserve with reasoning
and no answer, two were refused before anything was sent because a hunk or the part
count exceeded what a review may carry, and one part missed its deadline. Two of the six
had been merged before their review ended, #1317 before its review began. Under #1316 no
diff needing more than one request has reached a sovereign verdict; before it one had, a
documentation change passed in four parts, one verdict and not a rate. The repair did
what it promised, a bounded attempt and a refusal that names its cause, and not what it
was for: no large diff has been brought to a verdict in production under it, and what
would let one finish is not known.

### What the record shows against the model

Until 2026-10-01 nothing had measured the reviewer's recall; earlier studies measured
agreement on pull requests with no known defect. `vibey-gh review-canary` (#1325)
measures it on a fixed corpus of 41 small single-file diffs against this repository's
own code, 27 planted defects in nine classes and 14 controls, each sent through the
production entry point. A defect counts as caught only when the verdict blocks and a
finding names the planted file, its lines or an anchor, and the defect's class; a review
with no verdict is counted apart. The first measurement (#1331), on 2026-10-01, caught
18 of the 25 defects that drew a verdict (Wilson 95% interval 0.524 to 0.857), blocked
none of the 14 controls (0 to 0.215), and gave no verdict on 2 of 41. It is one run on
one host at temperature 0, on small diffs, and it meets a floor set low on purpose (a
recall lower bound of at least 0.5). By hand, two of the seven misses are real catches
the matching rule refused, so hand recall is 20 of 25. Five passed with no findings, and
in two the reviewer's own summary named the defect, one as "introducing a potential SQL
injection vulnerability", while `pass` was true; the gate reads `pass`, so those two
would have merged. The response schema writes `pass` before `findings`, and a rule that
lets the findings decide recovers neither, because those verdicts carry none.

The weekly workflow repeated the measurement on 2026-10-02 on the self-hosted runner,
over the same corpus and settings: 23 of 27 (0.675 to 0.941), every case a verdict, no
control blocked, its misses not adjudicated by hand. The runs differ in their commit and
in where the client ran, so the second repeats the procedure, not the conditions, and we
do not read the difference as an improvement. It was recorded only after the workflow
that dropped it was repaired: the artifact handover had put the new ledger beside the
tracked one, so the job read the unchanged file and reported no change, and the figures
were recovered from the retained artifacts.

Why the lane gives no verdict on a large diff is the subject of a study in progress,
preregistered before any data on 2026-10-01 (`research/large-diff-review/experiments/`)
over 45 diffs that production cannot review in one request; we report mechanism and screening, not result. Screening finished on
four diffs and saw three failure modes: at temperature 0 the reasoning loops to the
output cap with no answer (on the one part measured, 86% of its word 8-grams were
repeats); under sampling the loop ends but an answer can escape the response grammar or
come back empty. Five arms answered on all four diffs, every arm that bounds the
reasoning and then forces a verdict among them, the one remedy seen to repair a failed
answer; four of four bounds an arm's answering rate from below only at 0.51, no finding
has been adjudicated, and no arm's recall has been measured. Production is unchanged.

The record also speaks against the model. The forty merges before the 2026-09-30 scan
went in through the ruleset bypass with no review, as *What the records measure*
records. The reviewer's own summary named a SQL injection while `pass` stayed true, and
the gate reads `pass`. The merge train closed pull requests it reported as merged, and
since #1301 it counts a merge only when the forge reports one; the incident's record is
in *What the records measure*. The first diagnosis of the #1090 failure was wrong,
and #1312's two timeouts were at first taken for the earlier failure of a review that
had only waited its turn. And a lineage that a sovereign-only verdict sends back to
review has no termination bound in the calculus or the implementation.

```latex
\begin{plainwords}
A pull request is rewritten over time, and a grade belongs to one draft, never a later one. Once a draft was failed on a vanished draft's grade; that was fixed and tested. Only repairs count, so a draft only the local grader fails is graded again, and nothing yet stops that repeating. The grading key never merges. The local grader proves it read the whole draft by repeating two hidden words. Our first guess at one failed grade was wrong: it had read everything and run out of room. On short drafts with planted mistakes it caught 18 of 25 and failed no clean one, but twice named the mistake and still passed. Long drafts still get no grade.
\end{plainwords}
```

## Queue semantics

Work items form a relation $Q$ in PostgreSQL. Workers claim with

```latex
\begin{verbatim}SELECT ... FOR UPDATE SKIP LOCKED\end{verbatim}
```

which yields two properties without any global lock: *mutual exclusion per item*, at
most one worker holds item $w$ at any instant, and *non-blocking progress*, a worker
never waits on a peer's claim, so the rate of claims scales as
$\min(|Q|, |\mathrm{workers}|)$; the rate of finished work is bounded by the engines,
as *What the records measure* shows. The backend is PostgreSQL, never SQLite, which
has no row-level locking, hence no `SKIP LOCKED`, and whose usual substitute, a row
marked taken and returned, leaks when the worker dies after the mark
(`docs/architecture/decisions/0002-postgres-not-sqlite.md`).

A claim skips items whose dependencies have not succeeded or whose phase this vibey
does not know; the rest are ordered by the priority lane below, then earliest
permitted run time, then id.

Every hold by a worker that dies is bounded by a lease: a claim sets the expiry to
$\mathrm{now} + L$, a live worker renews it, and a reaper returns an expired lease to
ready while the item's attempts remain and parks it for a person once they are spent,
so a crashed worker costs at most $L$ of delay and never a lost item. A lease bounds a
crash, not a hang, since a live worker renews it whether or not its engine progresses:
until #1296 a BUILD session whose event stream never ended held its job indefinitely,
and nothing reported it; since #1296 it stops at a wall-clock limit, 240 minutes by
default with no value that switches it off. Since 3.1.0 a job whose last three
failures share one normalized signature parks on a *defect* gate rather than retrying
until its attempts run out (#1251). Because workers die and leases expire, every job
is idempotent under replay.

Execution itself is at-least-once: a worker that outlives its lease may run a job that
another worker has reclaimed, but the acknowledgement is fenced on the lease owner, so
the stale one is refused and exactly one commits per job. It is checked under chaos,
as *Validation* describes: concurrent workers process a job set against a real
PostgreSQL, each randomly abandoning claimed jobs mid-flight while a concurrent reaper
reclaims expired leases; the verified property is no double commit, no lost job and
every job terminal.

Every reap is a `QueueReaped` ledger event; a lease reap writes it in the row's
transaction. 3.0.0 extended the lease reaper by measured rule to everything a queue
guards (ADR-0056, *proposed*), with faults on record: for an ownerless lock the
push-gate reaper can signal processes other than the push, the worst of seven defects
its re-review found, fixed on an unmerged branch; on 2026-10-02 a real push waited 30
minutes behind a lock a test held; the bus port acknowledges on take, so a dying
consumer loses its message; one bad lease row halted every reap while the broker
policy was reported verified when not in force, both repaired by #1203, and whether it
covers two further findings cannot be settled from tracked sources.

The same primitive serves the bridge from a forge's triaged issues to delivery
([Fig. 11](#fig:queue-state)): a reconcile pass mirrors the open ones into rows, a
claim takes the first ready row under a 900 s lease, and a dispatch is marked on the
issue by a comment naming the project, so a bridge that lost its database would not
dispatch an issue twice.

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

### The derived priority lane

A bumped item runs next rather than waiting its turn, in the PostgreSQL job queue and
the storm's lane queue alike, under one contract (ADR-0054). *Next* means next after
whatever is running: a bump never preempts a claimed or leased item or touches its
lease (sub-doctrine 8.c), and never admits: phases, human gates, admission, capacity
deferral, budget brake and handoff gate still decide whether an item may run; it
decides only which runnable item runs first, never making one runnable before its
dependencies finish. The lane is derived, never remembered.

```latex
\begin{invariant}[Derived priority lane]
Let $B$ be the unfinished items bumped, or enqueued prioritised, by name and not since
un-bumped. The lane is exactly $B$ together with every unfinished transitive dependency
of a member of $B$, ordered first-in-first-out by when each item first entered the lane.
Un-bumping $x$ removes $x$ from $B$, and is refused, naming them, while another member
of $B$ depends on $x$.
\end{invariant}
```

A named item that ends cancelled or failed leaves $B$ by the derivation. The one
exception is a job whose phase or state a newer vibey wrote: it stays in the lane
unwritten with what it needs, named in the request's record, and un-bumping what it
needs is refused (ADR-0054, item 6). The derived form replaced a first rule,
*un-bump undoes what that bump moved*, after an independent review of #1091 found an
orphan: with $a$ and $b$ both needing $d$, bumping and un-bumping both left $d$ in the
lane with nothing needing it. Every admitted request re-derives the lane and sweeps
what is no longer derived (#1103); a refused one changes nothing but its own record.

Only the operator, the operating-system account owning the queue's reviewed
declaration, checked by process user id, or an automation it lists running as that
account, may bump or un-bump; nothing reads the forge to decide priority, so no label,
issue or comment moves work forward (sub-doctrine 12.j). The grant separates
operating-system accounts, not the operator's own processes, which reach the queue
below it whenever they can reach the database; since #1093 an engine's environment no
longer carries the means, but such a process can still reach a local server trusting
its socket (see *What an engine may see*). Every request is recorded,
authorisation preceding lookup so a stranger learns nothing about any item: in vibey a
ledger event in the row change's transaction, in the storm an append-only log,
loss-evident but not tamper-evident, as its code says.

A Hypothesis state machine runs random, overlapping bumps and un-bumps with jobs
finishing, failing or cancelled part-way, and asserts after every step that the stored
lane equals the derivation, except what this vibey cannot write and what it still
needs, and that un-bumping every named job clears the rest; breaking the derivation on
purpose makes it fail (#1095, #1103). Five workers claiming at once under
`SKIP LOCKED` take exactly the first five in order. Reviewers' untracked probes found
no double claim with five workers claiming through 450 random bumps and un-bumps on a
real database, and no false *order unknown* in over 9,000 concurrent reads of the
storm's log.

```latex
\begin{plainwords}
Jobs wait in a line in a database. A helper takes the front job with a timer and renews it while working. If the helper crashes, the timer runs out and the job goes back into the line, so it is never lost; a job that keeps crashing its helpers, or fails the same way three times running, goes to a person instead. Helpers never wait for each other, and a late helper cannot finish a job another helper already took. The owner can say ``do this one next'': that job goes to the front with what it needs, never out of a helper's hands or past a checkpoint, and every such request is written down, even the refused ones.
\end{plainwords}
```

## The six-phase machine

A human gate is a parked job plus a recorded row, never a thread waiting on input. The
machine is

$$\Sigma = \langle D, B, R, D_d, D_e, D_r \rangle$$

design, build, review, deploy-design, deploy-execute and deploy-review. The four in the
human-gated subset $G = \{D, R, D_d, D_r\}$ talk to a person; build and deploy-execute
run unattended. The deployment triple is entered only on an explicit opt-in recorded in
the ledger; declining it records a successful local completion. An optional
visual-design interstitial $V$ is gated likewise. [Fig. 12](#fig:six-phase-machine) draws
the path, omitting intake, abandonment, the return from build to design on an item
blocked by ambiguity, and the loop-backs out of deploy review.

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

A review finding therefore cannot vanish into a transcript: it is a ledger row holding
$\mathrm{open}(R) \neq \varnothing$, and the machine cannot leave $R$ for completion
until a person closes it. Loop-back is a ledger transition: an unambiguous finding
routes to $B$; one that needs clarification, or a project configured for strict
loop-back, routes to $D$.

Silence never supplies a verdict. A gate resolves to its stored default only for a kind
the project has declared, after a declared wait, and only the deployment choice and the
deployment gates are declarable; the worker answers it as `gate-timeout` by the path
every answer takes. DESIGN's gates and REVIEW's approval never time out; the table is
empty by default (#1299).

A handler that needs a human returns a park value; the worker records a gate row, marks
the item awaiting a person, releases its lease and claims the next. The answer is itself
a ledger row that re-readies the item; human latency never holds a queue slot. An answer
is a compare-and-set: a replay is a no-op, a second answer refused. Since 3.1.0 whether
a person was told is itself evidence: every gate notice ends in a `GateNotified` or
`GateNoticeUndeliverable` event with its reason, never an assumption (#1251).

The verdict row names who gave it; [Fig. 13](#fig:authority-map) maps that authority
over the delivery path of *Introduction*, which the bridge feeds from the forge. A
person labels and prioritises an issue, gives the review verdict, approves the merge
unless the operator's declared grant lets the delegated approver do so, and alone opts
into deployment, which is never inferred; the bridge admits, claims, orders and
publishes; the engine writes code only inside BUILD, in its own worktree; the forge's
required checks gate the merge. On an explicit opt-in only, the bridge answers the
design interview with its declared defaults under its own name,
`automation:triaged-delivery`, and accepts the design once the design chain has settled
(#1258). The rule is a repair: on the first delivered issue the bridge answered three of
the four interview gates within a second under the operator's own name, and the ledger
could not tell them from a person's: a bridge defect, not a property of the model, and
the concrete instance of the limit in *The ledger invariant*. The approver's grant
exists in declaration only: no workflow calls it, and its account had reviewed no pull
request by 2026-10-01.

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

Two edges bound the path. Before an issue enters it, a trust check: since 3.1.0 an issue
a stranger wrote, edited or labelled is held for a person, never dispatched; an
admitted one reaches DESIGN framed by `PromptShield` (#1248). Every phase short of
done, intake included since 3.2.0, has an edge to *abandoned*, the operator's exit: one
transaction withdraws every open gate, recorded as `GateWithdrawn` and never deleted,
cancels every unsettled job, and records one `PhaseTransitioned` with the reason; an
abandoned project also releases its checkout, and the claim never hands out an abandoned
project's jobs (#1263, #1276, #1279).

```latex
\begin{plainwords}
Every job takes six steps: plan it, build it, check it, and, only if the person wants, plan the launch, launch it and check it. Four of the six are gates where a person says yes. Saying nothing is not saying yes, unless the owner wrote down in advance that one kind of launch checkpoint may take its usual answer after a set wait. A busy person's job waits in the notebook while the helpers do other jobs. A stranger's request waits for a person before it is taken up. The owner can stop a project at any step before the end: its open questions are withdrawn, its waiting jobs cancelled, and the stop written down with the reason.
\end{plainwords}
```

## The engine family

ADR-0078 (4.0.0, 2026-10-03) retired `cursorloop` and `agyloop`; a configuration that
still names either is refused, and [Fig. 14](#fig:family-tree) is redrawn without them.
Since then three runner packages implement the family and the orchestrator declares
five engine identities (`src/vibey/domain/engine.py`):
`claudeloop` over Claude Code and `codexloop` over OpenAI Codex, the paid tier;
`gptossloop`, the sovereign default on GPT-OSS 20B, and opt-in `qwenloop` on a Qwen
model, one runner package over Ollama; and `claudeloop-local`, the claudeloop binary on
a local backend profile.

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
  \node[vibeysoft,run] (r1) at (6.45,-2.55)   {\textbf{claudeloop}\\paid tier};
  \node[vibeysoft,run] (r2) at (9.1,-2.55)    {\textbf{codexloop}\\paid tier};
  \node[vibeytealbox,minimum width=5.1cm,minimum height=1.15cm] (r5) at (7.775,-4.2)
    {\textbf{local runner package}\\gptossloop default $\cdot$ qwenloop opt-in};
  \node[vibeypill] at (r1.south) {Python 3.12+};
  \node[vibeypill] at (r2.south) {Python 3.12+};
  \node[vibeypill] at (r5.south) {Python 3.12+};
  \node[vibeybox,minimum width=7.75cm,minimum height=.7cm] (bar) at (7.775,-5.75)
    {\textbf{vibey-runners-common}\quad shared library of claudeloop and codexloop};
  \node[vibeypill] at (bar.south) {Python 3.12+};
  % ---------------------------------------------------------------- tools
  \node[vibeyvioletbox,tool] (t1) at (15.0,-2.55)
    {\textbf{vibey-gh}\\provenance, merge train,\\promotion, release, governance canon};
  \node[vibeyvioletbox,tool] (t2) at (15.0,-4.15)
    {\textbf{vibey-skills}\\retrieval engine over\\the skills catalogue};
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
    \node[vibeylane,fit=(r1)(r2)(r5)(bar)(p2t)(p2b)] (L2) {};
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
\caption{The two-package publication surface and the engine family. The dark box names the engine distribution; the apps publish separately as \texttt{krypton-app}. Beneath it sit the orchestrator, three runner packages (claudeloop and codexloop on their shared library, and the local runner package), and three tools. Every tenant requires Python 3.12 or newer. The teal package exposes \texttt{gptossloop}, the sovereign default on GPT-OSS 20B, and opt-in \texttt{qwenloop}; \texttt{claudeloop-local}, the claudeloop binary on a local backend profile, is the fifth selectable identity. \texttt{cursorloop} and \texttt{agyloop}, retired by ADR-0078 in 4.0.0, are no longer drawn.}
\label{fig:family-tree}
\end{figure*}
```

The identities form exactly two loops, `sovereignloop` (local) and `paidloop` (paid),
and every runner honours one narrow contract: a bounded run, a done marker, an event
vocabulary, a capacity mapping, and a shared wind-down exit code (75) meaning the engine
ran out of window capacity mid-item and stopped cleanly after writing its state.

### Bounded runs that never block

Unattended operation needs three things: no turn waits on a person, every metered
resource is bounded by the operator rather than the model, and a run's outcome is
auditable from durable state rather than a vendor transcript. A run is admitted only
under an explicit bound vector (turns, spend, wall clock, per-turn and output-silence
watchdogs, and a ceiling $W_{\max}$ on any single capacity wait; the exact members vary
by runner) and ends at the first bound reached, that bound recorded. Budgets are
checked only at turn boundaries, so a run can pass a dollar cap by at most the turn
that crossed it. Above the runners, the orchestrator bounds every BUILD session on its
own clock, 240 minutes by default, and a stop ends the session's whole process group
(#1296, #1297); before those changes a session whose event stream never ended held its
job with nothing reporting it (*Queue semantics*).

```latex
\begin{invariant}[No interactive waits]
No execution path may block on standard input. Where the vendor's tool can prompt,
managed hooks pre-answer it and the session preamble declares unattended operation;
everywhere, the watchdogs convert any residual hang into a loud, bounded failure.
\end{invariant}
```

Each turn, verdict and spend entry is one JSON line in an append-only trail under the
run directory: write-ahead at session scale.

The delivery bridge treats an overrunning worker the same way
([Fig. 15](#fig:process-reaping)): past a 900-second default deadline it terminates the
worker's process tree deepest descendants first, waits two seconds and kills what
survives; only then is the timeout recorded, and the lease is left to expire rather
than released, so the queue's own reaper returns the job by a crashed worker's fenced
path and a late acknowledgement is refused.

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

### What an engine may see

A bound on spend is not a bound on reach: until 3.0.0 every engine process started from
a copy of the worker's whole environment with four Python variables removed, so the
shell commands a model chose held the queue and ledger connection string, every
`VIBEY_*` secret, libpq's `PG*` variables and the worker's GitHub and cloud credentials,
and could rewrite queue rows and, before the guard of *The ledger invariant*, the
ledger, unrecorded (#1093).

Since 3.0.0 every child's environment is assembled from an allow-list and never copied
([Fig. 16](#fig:environment-boundary)): the system basics every process needs, the
engine's own declared variables and credential, and what the project declares in
reviewed configuration. Beneath them sits a forbidden set, `VIBEY_*` and `PG*` for every
child, `GIT_*` for gates, and for engines any name containing `DSN`, `DATABASE_URL`,
`PASSWORD` or `PASSWD`; a declaration naming one fails when the worker is built. A
forge or cloud token is on no default list and reaches only an engine the project
names.

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

The independent review of #1093 found planted programs running with the connection
string in hand, rated critical, and a notifier that could run injected shell commands;
both are reproduced in tests that failed before the fix. No verdict on the merged
result is recorded in a tracked source.

The control keeps secrets out of a child's *environment*; it is not a boundary between
the worker and the processes it starts, which share its operating-system user
(ADR-0055 calls the list hygiene, not a boundary). A local PostgreSQL with `trust` or
`peer` authentication needs no connection string, so there the allow-list does not keep
an engine from the queue and `vibey doctor` fails. A same-user process can read the
worker's environment and files; the container boundary that would separate them is
implemented but not wired in, and a separate low-privilege user is in no release through
3.2.0.

### The sovereign driver and measured fit

The editor driver, a VS Code extension (ADR-0059), adds no agent loop of its own: a task
is a run of a family runner, on `sovereignloop` by default and on `paidloop` only after
paid use is declared.

The driver makes the local fit explicit ([Fig. 17](#fig:probe-lifecycle)). A
probe runs a grid of context and output sizes against the local server and records the
endpoint, model, source revision, prompt shape and the fastest fit that answered
validly. The runtime loads that record only if endpoint and model match, the fit is
marked valid, and the revision matches when the running revision is named
(`VIBEY_REVISION`, which nothing in vibey sets, so the revision is recorded but not
checked by default); a stale, malformed or mismatched record falls back to the
configured ceilings, and a prompt larger than the measured shape runs under the
defaults of 8,192 context and 2,048 output tokens.

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

### Budgets and selection

The transplant thesis held: everything vendor-specific fits in the lexicons that read a
vendor's failure text and the transport that speaks to it. Four retargets of
`claudeloop`'s core, two since retired, kept the invariants while the capacity
vocabularies differed, from three members in `qwenloop` to six in `codexloop`, so the
orchestrator can treat the pool as substitutable executors and choose by policy rather
than by state.

Budget caps are per cycle, in dollars and turns, summed from the cost and turns the
engines report on each completed turn and read afresh at every BUILD session; engines
carry cost rates, not caps. An exhausted budget parks the item on a `budget_exhausted`
gate before a session starts, never after, and a per-item turn cap exists only as a
configuration key nothing reads.

Local engines are preferred (sub-doctrine 8.a); paid engines are the fallback when none
is eligible, and the selector does not yet read the paid declaration sub-doctrine 8.b
asks for ([Fig. 18](#fig:engine-pool)). Within a tier the eligible engines are ranked by
smooth weighted round robin under
$w_i = \max(1, \mathrm{round}(b_i h_i f_i c_i a_i))$, its cost factor fixed at 1 in the
current implementation; the sequence is deterministic and spreads load in proportion to
weight. Rotation fires only at a boundary (a new item, a capacity rejection, which
opens that engine's circuit, a wind-down, an effort escalation, a crash or a phase
transition), never inside a turn, so every handoff has a well-defined ledger range
$\rho$. A wind-down sends a handoff brief, checked as *The no-loss handoff gate*
describes, to a successor that excludes the outgoing engine; a capacity rejection defers
the job instead, and no brief is produced on that path yet (ADR-0007).

Release 4.0.0 adds a hybrid mode (ADR-0079): local engines fill their declared slots
first; a paid engine takes a BUILD job only once every eligible local slot is
occupied, the job has waited a configured overflow delay and the project's paid cap for
the UTC day is not reached. `singleton` is the selection above; `auto`, the default,
chooses between them from a ledger measurement of local-slot contention and falls back
to `singleton` when that measurement is missing, stale, invalid or failed. Every
overflow, slot wait and measurement is a ledger event, and the cap is counted from the
ledger under the project row's lock, so it holds across restarts and workers.

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
  % lane extents: shared x-range, headroom for the lane label
  \coordinate (p1a) at (0.05,3.2);  \coordinate (p1b) at (7.95,1.4);
  \coordinate (p2a) at (0.05,0.3);  \coordinate (p2b) at (7.95,-1.2);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(qwen)(qwen2)(cll)(p1a)(p1b)] (L1) {};
    \node[vibeylane,fit=(claude)(codex)(p2a)(p2b)] (L2) {};
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
\caption{Choosing an engine. Local engines (teal) are preferred; paid engines (blue) are the fallback, and the selector does not yet read the paid declaration sub-doctrine 8.b asks for. Under the hybrid dispatch mode of ADR-0079 (4.0.0) a paid engine may also take a BUILD job once every declared local slot is occupied, the job has waited its overflow delay and the day's paid cap is not reached; \texttt{cursorloop} and \texttt{agyloop}, retired by ADR-0078, are no longer drawn. The selector ranks eligible engines by smooth weighted round robin. A graceful wind-down (exit 75, out of window capacity mid-item) sends a handoff brief through the no-loss gate to the next engine, excluding the one that wound down; a capacity rejection instead defers the job and opens that engine's circuit, and no brief is produced on that path yet (ADR-0007). Rotation happens only at a boundary, so each handoff has a well-defined ledger range $\rho$.}
\label{fig:engine-pool}
\end{figure*}
```

### Dispatch experiments

On 2026-09-26 we timed three dispatch paths on one laptop, Ollama with `gpt-oss:20b` and
RabbitMQ 4.3.6 on loopback; the table gives the rates. The model-turn experiment used
two samples at hybrid concurrency $2$ and the orchestration-bus experiment twelve
messages; hybrid won model turns and the multiplexer won the bus. The model-turn result
was persisted as per-machine benchmark evidence and the bus result as that machine's
`auto` winner; the two bus runs agree on the winner while their rates vary, so the
implementation recomputes rather than fixing one measurement. They are machine-local
observations of dispatch paths only, establishing no model quality, paid-provider
quality or cross-machine performance. Paid-provider experiments were not run and no
live paid-provider result is claimed: the provider benchmark executor and the durable
global paid budget guard are implemented and unit-tested, but a live result needs an
enabled adapter, a representative run, reported usage and charging within the
authorized cap. The raw results were kept on the machine, not committed, so the table
cannot be recomputed from the repository.

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

```latex
\begin{plainwords}
A runner lets one robot helper work by itself. Every run has limits on turns, money and time; the runners never wait for a person to type, and a helper that runs too long is stopped, all of it, before its timeout is written down. Each helper is handed only the keys its job needs, never the whole key ring, though a helper running as the same computer user could still go looking, and we say so. Local helpers are tried first and a fair rotation shares the work. We also timed three ways of handing out work on one laptop: two local jobs side by side beat one after another, but those are one afternoon's numbers from one machine.
\end{plainwords}
```

## Deterministic retrieval and fail-closed bootstrap

Two further components apply the ledger's rule, append before acting and fail closed,
at other scales.

A skill library of 745 documents across 138 plugins at the source cutoff cannot be
loaded whole into a context window, and a fragment of safety-critical guidance is
worse than none.

```latex
\begin{invariant}[Deterministic, whole, fail-closed retrieval]
The index is a pure function of the corpus: identical corpus bytes yield identical
manifests, chunk identifiers and scores. The retrieval unit is a heading-bounded
section, returned whole with its path, line range and content hash. For a request
with mandatory content $M$ and budget $B$, if $\mathrm{tokens}(M) > B$ assembly returns
\texttt{budget\_insufficient} and never truncates a mandatory section to fit.
\end{invariant}
```

The engine is lexical, over SQLite FTS5; dense retrieval would reintroduce the
nondeterminism the reviewability invariant forbids. Over-budget mandatory content
yields no packet; omitted optional content is listed in the manifest, and a
low-confidence flag returns the caller to native full-skill activation. No retrieval
metric is reported here, and none is the objective: the criterion is cost per accepted
work item, unmeasured here, since a packet that halves token spend but raises rework
is a regression.

The bootstrap layer starts a cloud workload in one call under one rule: a missing
required precondition halts the start, named, and an optional capability degrades as
a recorded decision, never a silent absence. Above it a transactional outbox commits
intent beside the state change, so every committed intent is delivered at least once
and marked delivered exactly once, and audit records form a hash chain,
$c_0 = H(r_0)$ and $c_i = H(c_{i-1} \| r_i)$, so any edit, insertion or truncation
breaks every later link and verification needs no trust in the writer. Ledger, outbox
and chain are one principle at three scales ([Fig. 4](#fig:record-effect)): intent is
durable before its effect, state is derived from it, and a crashed worker replays from
it, duplicates dropped by identity. These guarantees are stated, not measured here.

A proposed contract (ADR-0075, [Fig. 19](#fig:microslice-contract)) extends the rule to
everything loaded into a window: a converter cuts a source into numbered slices
carrying identity, purpose, provenance and explicit requires and links relations; a
retriever loads the matching slice with its required closure only when that closure
fits the budget, otherwise splitting or parking it. Neither the measured size nor the
retriever is implemented, the slice boundaries are mechanical and still need review,
and a split is no claim that each slice reads well alone.

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

```latex
\begin{plainwords}
Two smaller tools follow the same rule of writing things down before acting. One looks
up instructions in a large library and always returns whole pages, never half a page;
when the pages it must include do not fit, it says so instead of cutting them. The
other starts cloud programs and refuses to start at all if something it needs is
missing, rather than limping along quietly, and it notes what it is about to do before
doing it, so a crash can be replayed from the note. A planned extension would cut every
document into numbered, linked pieces so the same rule applies to everything the
system reads. It is not built yet.
\end{plainwords}
```

## What the records measure

Every measurement we
recompute here is read from one project's tracked records at a named cutoff: the
sovereignty stress record of 2026-08-30, a controlled escalation of the local review
lane; the local Qwen pilot record of 2026-09-20; and the QwenStorm 3.0.0 evidence
ledger of 2026-09-22 and 2026-09-23. `scripts/paper_evidence.py` recomputes the stress
and Qwen figures, `scripts/paper_figures.py` redraws every computed figure from the
tracked files, and the storm's own `storm-evidence.py` regenerates its evidence table
between markers that no sentence of ours lies inside. Two sources we cite are not
tracked, and we name them where we use them: the storm throughput audit of 2026-09-23
and the forge's own records of pull requests and their merge times.

### A single-slot saturation curve

A harness fired $N$ simultaneous generations at `qwen2.5-coder:14b`, served by ollama
on one machine with 24 GB of memory and 10 cores, for $N$ from 1 to 128, with a 900 s
deadline per generation. Each generation was a real unit of work, an issue triaged or
a pull-request diff reviewed, drawn from a pool of seven artifacts of 2 to 22 KB.
Throughput is successful generations per minute of rung wall clock; every rung's
throughput and success fraction is in [Fig. 20](#fig:stress-rate).

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

The serial rung ran at 0.36 per minute: one job cannot saturate the substrate. Across
the nine rungs from $N = 2$ to $N = 32$ (107 generations, 102 succeeded, every rung at
or above 87.5%), throughput stayed between 0.99 and 2.00 per minute while offered
concurrency rose sixteen-fold; the least-squares slope of log throughput on $\log N$
over those rungs is 0.20, where output that scaled with demand would have slope 1. The
band is a band, not a constant: its spread is a quarter of its mean, and it drifts
upward with $N$ because the server batches concurrent sequences into shared forward
passes. A band fitted on the rungs with $N \leq 16$ is $[0.99, 1.72]$; of the two
stable rungs held out, $N = 24$ (1.40) fell inside and $N = 32$ (2.00) fell 16% above,
in the direction batching predicts, so we claim the floor and the scale of the ceiling,
not a tight window. Above the band the success fraction gives way before the
throughput does: 1.60 per minute at $N = 48$ with 50.0% success; 2.66 at $N = 64$ with
62.5%, where the server crashed and restarted itself; a peak of 3.52 at $N = 96$ with
55.2%; and at $N = 128$ a fall to 1.53 at 18.0%, with paging space at 99.1% and the
server restarting again. Free memory stayed in a narrow band throughout; paging space,
not free memory, marked the collapse. In all, 243 of 444 generations succeeded over
2.18 hours ([Fig. 21](#fig:stress-cumulative)), and every failure was a clean timeout,
none malformed.

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

This is what one local model slot does when more clients are offered to it, with
hardware, model, serving stack, deadline and admission rule held fixed on one machine.
The completion-time prediction of *Time to completion and what modulates it* takes its
zero-shortfall rate from this band and holds inside the band, for this workload, only.
The curve is not evidence about another host, model or task class, and not evidence
that governance rather than the model is the scarce input in general. The host's own
memory budget, measured in *Host benchmarks and context headroom*,
confounds every timing here. One correction: the `vibey-gh` tenant paper once reported
this experiment as 61 generations at a success rate of 1.00 with throughput held to
$1.4 \pm 0.25$ per minute; neither survives comparison with the record, and that paper
now carries a dated correction.

### The local Qwen pilot

A local storm on 2026-09-20 ran the then-latest qwenloop runner against
the open backlog with `qwen3:14b` through Ollama. It is not a replication of the stress
record: the work items were heterogeneous, the offered concurrency was not controlled,
and several runs were still alive or had produced no events at the evidence cutoff,
`2026-09-21T00:19:23-04:00`.

Thirteen run directories were observed. Four completed with both a verdict and the
completion marker; two emitted verdicts without the marker; two ended without a
verdict, one of them after exhausting its 40-turn limit with a `failed` terminal event;
one produced a tool error after one turn; four had no events; and one storm process was
still alive. Across the thirteen the logs hold 105 model turns, 85 tool calls, 550,576
input tokens, 83,609 output tokens and 42 file writes totalling 32,073 bytes
([Fig. 22](#fig:qwen-runs)). The accepted completion rate at the cutoff was therefore
4/13, or 30.8%, where a verdict alone would have suggested 6/13, or 46.2%.

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

This is a runner-reliability observation, not a model-quality or throughput estimate,
and it does not enlarge the throughput claim above. It is an empirical check of the
completion contract: a verdict without the marker did not count, and unfinished event
trails stayed unfinished rather than being promoted to completed work
([Fig. 23](#fig:qwen-disposition)). The requested context setting was 32,768 tokens
while the server reported 40,960 at the cutoff, so no claim about a controlled
context-window effect is made.

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

### The storm evidence ledger and its audit

The QwenStorm 3.0.0 run of 2026-09-22 and 2026-09-23 drove the open backlog through one
local model, `gpt-oss:20b` on Ollama, one lane at a time, each lane one issue, one
source file with its interface and one test file, reviewed against its specification
and its diff before it may become a pull request, with at most three attempts. The
record is an append-only evidence ledger that a consumer fills from the storm's progress
log and lane results. Its 30 lanes logged 70 attempts and 2,606 model turns. Seventeen
lanes ended in a completion claim, and a claim is not delivery: of the 30, four were
integrated (three claimants and one that had failed all three attempts), twelve were
abandoned, and fourteen, all of them claimants, were unsettled at the cutoff; the
reviewer's totals of 12 integrated and 14 abandoned reach beyond the ledger's 30.

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

The consumer reads by position, never by time ([Fig. 24](#fig:evidence-watermark)): its
watermark is a byte offset into each source plus an identity set over the records,
since records that share the cutoff second, arrive late or out of order fall
through a timestamp comparison silently; it appends and flushes before advancing, so a
crash re-reads rather than skips, duplicates are dropped by identity, and a source
shorter than its offset is reported as a gap, never reset. The table's no-gap statement
was proved on the storm's host and cannot be re-proved from a checkout: the repository
tracks the ledger (277 records, no identity repeated) but only an early copy of the
progress log, 3,821 bytes against a recorded offset of 15,087, so the check reports that
copy as short and we leave the block as the host generated it. Recounting the ledger
reproduces every row, after one correction to the lane-start counter, whose pattern
required a space after the issue number and so skipped the storm's first start line
(49 starts, not 48).

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

[Fig. 25](#fig:storm-lanes) draws every lane with its attempts. One model instance
served every lane in turn, so attempts never overlapped: the bars of
[Fig. 26](#fig:storm-timeline) never overlap, and the blank stretches are the
reviewer's and the operator's time, not the machine's.

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

An audit on 2026-09-23 asked why the storm could not run more lanes and which safety
controls had to hold first. Its working record is not tracked: a page kept outside the
repository, fed by lane run logs that were never tracked and that a reboot of the host
on 2026-09-24 erased, by the progress log, the model server's log and the forge. Every
figure is the audit's unless we say we recomputed it. Across the 82 run directories
then on disk, model calls took 9.68 of the 10.01 hours those runs spanned, 96.7%, and
the progress log's 41 closed lane intervals never overlap; we recomputed both from the
local files on 2026-09-24, before the reboot, and they agree. Three serialisers stack:
the queue script waited for any running lane on the host, the project's rule gave a
model on the operator's own hardware one run at a time, and the server had one slot.
Amdahl's law then bounds what more lanes sharing that slot could buy at
$1/0.967 \approx 1.03$. These 82 runs are not the ledger's population, and we
reconcile neither to the other.

No lane reached the integration branch without a human step. Of 40 lanes started, 13
had work on the branch at the audit, three through the automated path; but none of the
last 60 merged pull requests had a successful required review gate, the merge train
logged *merged 0* on every pass, so every merge was made by hand, and ten lanes needed
a hand-built pull request. More lanes multiply this conversion rate rather than
escaping it, and the hand repair is capacity nothing records. Seven safety controls
existed in configuration or documentation and were read by nothing, or bound only in a
mode not in use, among them an unattended merge fallback with `--admin`; none was
exploited, because every one of the 594 queued issues was the operator's. All seven
were enforced by merged code on 2026-09-24, beside the yield fixes the audit ranked (a
retry on an empty reply, a per-lane time limit, real search and file tools); the storm
had not run since, so their effect on yield is unmeasured. One control stayed
unsettled: the rulesets carried a bypass actor nobody declared, and 78 of the last 200
merges went in while the forge reported a review still required; who and how needs the
organisation's audit log, and *The autonomy scan of 2026-09-30* returns to it.

Most of the audit's first claims were wrong. Twenty-five agents audited six dimensions;
adversarial verifiers then checked the leading claims before anything was written up
and refuted 16 of 18. Some corrections were of degree and some of kind: the claimed
serialisation point was the wrong line, the single slot is serialised by code, canon
and configuration rather than by hardware, and the account of #1090 as a silently
truncated prompt was wrong, as *Exact-head evaluation and the release calculus*
records. This is a finding about method: a first pass by capable agents over complete
logs was wrong more often than right on its headline numbers, and verification, not
analysis, made the audit usable. It applies to this paper: an earlier revision claimed
that a 64k context window generated 16% faster; the same verifiers found decode speed
varying from 26 to 34 tokens per second within one allocation, so the difference is
inside the noise and no longer claimed.

```latex
\begin{plainwords}
We measured three things, all from one project's saved records. First, we gave one
local model on one computer more and more jobs at once: from two to thirty-two jobs at
a time it finished about one to two a minute however many we offered, and past that it
began failing and finally crashed. That says what one model on one machine can do, and
nothing more. Second, a trial of the local runner finished only four of thirteen jobs
properly. Third, an overnight run of thirty tasks claimed seventeen done, but only four
were integrated, and a re-check of the audit of that run found most of its first
conclusions were wrong.
\end{plainwords}
```

### Host benchmarks and context headroom

On 2026-09-22 the same ten-turn session was replayed against five server
configurations on the one 24 GB Apple M5 host that every timing in this section comes
from ([Fig. 27](#fig:bench-hosts)). For every llama.cpp configuration of
Qwen2.5-Coder-14B, generation fell as the context grew, from about 11 tokens per second
on the first turn to between 6 and 9 on the tenth, and the four finished in 212 to
220 s; gpt-oss:20b on Ollama finished in 86 s, and the same model on llama.cpp at a 64k
context did not load. The record does not separate the model from the serving stack,
so the difference is reported, not explained.

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

On Apple Silicon a model's weights and key-value cache are wired memory, reserved in
proportion to the context window: at 131,072 tokens the server wired 18.55 GB of the
24 GB. The storm's run ledgers record what 838 real turns used, a median of 20,070
tokens, a 99th percentile of 42,979 and a maximum of 49,118
([Fig. 28](#fig:host-context)). A 32k window would have truncated 71 turns; the 64k
window chosen covers every recorded turn with a third again as headroom and wires
1.3 GB less than the 128k baseline, which no turn reached.

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

The minimum requirements follow from the same host. Memory was the binding constraint,
set by the context rather than the model file: with vibey, PostgreSQL and the operating
system the host needs 24 GB at minimum and 32 GB recommended, and a GPU is not optional
for BUILD, since on the CPU alone the worst BUILD turn does not fit the 900 s timeout.
These are seed measurements from 2026-09-29 and 2026-09-30; the weekly workflow that
would refresh them had not run at our cutoff, so every figure is stale since its seed.
The full tables are in the appendix, and the record is
`docs/architecture/evidence/minimum-specs.json`.

The host's health record held two points at our cutoff, too few for a trend; memory
sat exactly at the 24 GB minimum, and swap in use was 0.60 and then 0.68 of memory,
past its 0.5 threshold in two of the three records that would confirm it. A
measurement on 2026-10-02 with the model loaded found process footprints of about
49 GiB on the 24 GiB machine, 18.5 GiB of it the model server, and the SSD taking
152.5 GB of writes an hour, 85% of them swap-outs: by elimination rather than by
trace, its 36.55 TB written in 337 power-on hours is mostly the price of overcommitted
memory. It is a confound for every timing in *What the records measure*: the rate at
which a review generates depends on what else the host holds.

### Field data from the repository

The git history is field data: nothing in it was held fixed. At the pinned revision,
`d4c4e1f8`, 1,331 commits are reachable across nine root histories; since 2026-08-09,
when the family's own development begins, 1,319 landed on 34 active days, between 1 and
191 a day, and the longest pause, nine days, has no recorded cause
([Fig. 29](#fig:commits-daily)). Every count is lower than at the previous pin,
`c78049b6`, although the work grew: the 3.0.0 release reached `develop` as one squash
commit (#1244) in place of the 213 commits of its cycle, so the week of 2026-09-21
reads as the quietest when it held 218. The daily figures record how commits reached
the integration branch, not when the work was done.

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

The daily rate's spread is 106% of its mean, against 24% inside the saturated region
of *A single-slot saturation curve*; almost any model predicts that of an uncontrolled
process, so the history does not test the curve; we report it so the controlled band
is never mistaken for a field rate. [Fig. 30](#fig:commit-rhythm) gives the hour,
weekday and Conventional Commit type of every commit.

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

[Fig. 31](#fig:cumulative-commits) sets the 538 commits whose subject closes a pull
request against the whole.

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

Nineteen `vibey` release tags run from 2026-08-16 to 2026-09-30; one version number
ships the whole family ([Fig. 32](#fig:release-cadence)).

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

[Fig. 33](#fig:codebase-shape) is the shape of the tree at the pin, 420,679 lines of
Python in 2,364 files and 11,384 test functions; it still lists two engine packages
that ADR-0078 has since retired.

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

### The autonomy scan of 2026-09-30

On 2026-09-30 a scan read `develop` at `15e909d4c` (#1290) with four parallel code
reviews and live evidence from the forge and the local queue, asking how close the
system was to running on its own; we read every figure again on 2026-10-01, and the
queries are tracked beside the paper.

Only BUILD ran without a person. DESIGN parks its interview for a person unless told to
answer with defaults; REVIEW's gates wait for a person by design, and nothing answered
them, so no project could reach DONE unattended; and a gate's stored deadline was read
by nothing, so an unanswered gate waited forever. Part of that is design, since
sub-doctrine 12.d bounds unattended authority by a gate; the rest was defects. The
forge shows the same from the other side.

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

The forty pull requests merged into `develop` up to the scan's revision carried no
review; every one was merged by the operator's account through the ruleset bypass, and
the delegated approver, its grant enabled, was never called. One reading did not
survive the second pass: the 22 dispatched merge-train runs were not started by hand,
as the scan read them, but by the review workflow once its gate was green. The first
diagnosis of the sovereign reviewer's failure on #1090, a silently truncated prompt,
was also wrong, as *Exact-head evaluation and the release calculus* records; in each
case going back to the source, not the analysis, caught it.

The code reviews found seven defects, three of them failures of evidence rather than
capacity: REVIEW was shown a test report and a coverage figure nobody had measured, a
fallback supplied when the handler's payload was empty, so every human REVIEW in
production had seen a fabricated report; the evidence guards between phases were
reached only from tests; and the deadline nobody read. The other four were a paid
engine's login trusted for 24 hours and every job needing one deferred indefinitely
thereafter, a BUILD session with no wall-clock limit, a stop that ended the runner
alone, and worktrees never removed. The repairs landed within a day, every one through
the bypass the table records, so at this revision they are themselves evidence of the
gap they address.

The merge train added a defect of its own: with the approval missing, the forge's merge
command enables auto-merge and exits 0, which the train read as a merge, printing
`merged 1` and deleting the head branch, so the forge closed the pull request. On
2026-10-01 it closed six pull requests eight times, the fix for this very defect among
them, before the train was made to count only a pull request whose state reads merged
(#1301): automation reporting a success it did not observe, which sub-doctrine 12.e
names. Replaying eight merged pull requests at their exact heads, once each, showed the
sovereign reviewer passing all eight at low effort, the four the gate had blocked
included, while seven of the gate's own eight block findings named something the file
contains, six of them on lines outside the diff the reviewer was shown; given each
changed file's full text (#1303), none of the seven came back. No pull request in the
sample carries a known defect, so recall is unmeasured here, and agreement with the
gate is agreement, not correctness.

The scan's questions are now asked weekly by a script whose stages, figures and
thresholds are declared in configuration; the sentence and table below are generated
from its append-only record, never edited by hand. At our cutoff the weekly workflow
had not yet run, the readings were taken by hand with the same script, and at each of
the three, one of the eleven declared stages met its thresholds.

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

Nothing the scan found was a shortage of production: BUILD ran. What stopped the loop
at every other link was evidence, authority, or automation that misreported its own
act. Gate timeouts became opt-in, and REVIEW keeps its person. Every merge into
`develop` up to `ca9e47452` (#1341) was still the operator's, through the bypass, this
paper's own revisions among them, so the repairs are not yet evidence that the loop
will deliver a change with nobody present.

### Time to completion and what modulates it

`vibey-gh` postulates six materials, network, hardware, software, agent, information
and agency, each available, stable and reliable, so a state is $x \in \mathbb{R}^{18}$
and the shortfall from the stable peak $x^{*}$ is $d = x^{*} - x$; agency is not agent,
since an agent may be present, rested, correct and informed and still lack the power to
act, as the release calculus imposes on the credential that reviews. An operation is
feasible when $x \succeq r_o$, and its duration is
$T(o) = T_0(o) \prod_i \phi_i(d_i)$, where $\phi_i$ is unity at $d_i = 0$ and diverges
as the coordinate nears its floor ([Fig. 34](#fig:six-materials)). It is a postulate,
not a law, and it carries no measurement of its own.

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

The prediction it supports holds inside the saturation band only. Let $r_{\min}$ and
$r_{\max}$ bound the band measured in *A single-slot saturation curve*. For $W$ units
of the same task class, admitted in the saturated region with every coordinate at its
target,

$$T_0 \in \left[ \frac{W}{r_{\max}}, \frac{W}{r_{\min}} \right]$$

and in any other state $T = T_0 \prod_i \phi_i(d_i) \geq T_0$: every shortfall dilates
$T_0$ and none shortens it. For that substrate and $W = 100$, the band $[0.99, 2.00]$
per minute gives $T_0$ between 50 and 101 minutes, where the serial rate alone would
give 278 ([Fig. 35](#fig:completion-band)). The interval is wide because the band is,
and replication would narrow it; because the held-out check exceeded the band's
ceiling, only the upper end is firm.

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

Of the modulators that would move the band, only hardware is measured: paging space
reached 99.1% at $N = 128$, where the collapse and the crashes coincide, and the
serving process died and was restarted at rungs 64 and 128. Network stability and
operator availability are not measured, governance is set rather than measured, and
information freshness has one measured instance, the stale figures this revision
corrected. The delivery-estimate ledger applies the same form to the project
([Fig. 36](#fig:forecast)): from the observed merge rate it forecast 45 to 58 active
days to completion at its last record, with every coordinate unmeasured and so at
$\phi_i = 1$, after the remaining work jumped from 25 to 708 units on 2026-09-23 when
the storm filed its lanes as issues.

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

Governance has a price in time, and the price can be lowered without lowering the bar:
computing the four per-layer coverage floors from one instrumented run took the gates
from about 1,530 s to 136 s, an 11.3-fold reduction, and the bare suite from 383 s to
135 s, with no gate removed ([Fig. 37](#fig:governance-time)), a governance dilation
made smaller while the requirement stayed the same.

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

### Falsification and scope

The saturation band is falsified, for its substrate, by any of the following:

- a replication on the same substrate and task pool in which a saturated rung, one with success at or above 87.5%, runs below 0.99 per minute, or in which the band's mean moves by more than its measured spread of 0.33 per minute;
- a log-log slope of throughput on $N$ near 1 inside the region, which would make the rate demand-set rather than substrate-set;
- a set of $W$ units, admitted in the region with every coordinate at its target, that takes longer than $W / r_{\min}$ to complete.

This is evidence, not proof, and narrow: one machine, one model served one way, one
deadline, one artifact pool whose payload mix was not balanced across rungs, one
stress session, one local Qwen pilot and one operator, with two of the five modulators
named, mapped and unmeasured. We claim neither a natural law nor a constant rate, only
a band on a substrate with the conditions under which it fails. The storm audit is
narrower still, one storm on one model slot read from local logs never tracked and now
gone, and merging ahead of review is one day of one project, not a controlled
comparison. The autonomy scan is one revision read again a day later, and its
review-lane replay is eight pull requests run once each with no known defect, so it
says nothing of recall. The canary's recall is two runs on one host over 41 small
single-file diffs by one author, matched by a lexical rule, and the large-diff study
has no arm with a measured recall. The scorecard held three readings and the host's
health record two, all within two days, so neither shows a trend.

```latex
\begin{plainwords}
We also measured the one computer all of this ran on. It is full: the model takes most
of its memory, the rest spills to disk, and that slows everything else we timed. Our
list of what a machine needs is measured again every week, and most of it is still
marked as old. Only the building step of the whole job runs with nobody watching; every
change still went in by the owner's own hand, and some of our own first conclusions
were wrong until we re-read the records. From the saturation curve we predict how long
a batch of work should take on that machine, and we list exactly what would prove us
wrong.
\end{plainwords}
```

## Comparison with alternatives

A reader who grants every invariant can still ask whether the machine does more than
its parts. We compare it with three alternatives on five axes: a session runner whose
transcript is its source of truth, as Claude Code and Codex CLI are (the engines of
*The engine family* wrap such runners); a transactional outbox (Richardson) under a
workflow engine such as Temporal or Cadence, which never mentions agents; and a forge
ruleset of required checks and a required approving review, as on this repository's
integration branch. The table sets the four side by side.

```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{0.95in}p{1.45in}p{1.4in}p{1.45in}p{1.6in}@{}}
\textbf{Axis} & \textbf{(a) Session runner} & \textbf{(b) Outbox and workflow engine} & \textbf{(c) Ruleset and approval} & \textbf{Ledger-mediated}\\
Source of truth & the vendor's transcript, read by no other vendor & a durable record the engine replays & the repository and the forge's record & the append-only ledger; transcripts are attachments\\
Survives a crash & the run directory; resume by session id & replay of the durable record & the pull request and its check runs & the lease: at most $L$ of delay, no lost item, no double commit\\
A vendor's capacity exhausted & the run waits; moving it means a model-written summary & a failed step, retried or timed out & out of scope & a capacity verdict; credits carry no deadline; handoff only through the gate\\
Where a person decides, and the record & none defined; a denied question becomes a stated assumption & a waiting step; its timeout means what the author chose & the approving review, unless a bypass actor merges & a parked job and a \texttt{human\_gate} row before the lease is released; silence counts only where declared\\
What binds a verdict to a revision & a run-directory verdict, no completion evidence by its own docs & not in scope & checks bound to a revision; freshness left to the consumer & exact head: a verdict speaks for one revision\\
\end{tabular}
\caption{Three alternatives beside ledger-mediated orchestration on five axes. The (b) column describes the pattern generically; no tracked record of this repository measures it.}
\label{tab:comparison-axes}
\end{table*}
```

Against (a) the difference is in kind: a run's decisions, assumptions and open questions
sit in a transcript shaped by one vendor, which the next engine cannot read, and a
model-written summary drops them silently
(`docs/case-studies/how-vibey-survives-a-crashed-agent.md`); a deterministic check over
a log is feasible, over a chat transcript it is not
(`docs/architecture/decisions/0003-event-sourced-ledger.md`). There it does not differ:
the runner alone keeps an append-only trail and save points, tells a window from
exhausted credits, and resumes by session id. The ledger's price: every meaningful
engine output must be translated into events.

Against (b) the difference is not the durable record. By design the family's own job
dispatch writes its outbox row in the transaction of the state change
(`docs/architecture/decisions/0044-job-queue-port-and-loop-services.md`, a proposed
record), a dispatch that
`docs/architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md`
records as declared, not wired; and a durable-execution library was rejected as
Postgres-backed anyway (`docs/architecture/decisions/0002-postgres-not-sqlite.md`). The
difference is what the record admits: a model-free predicate over minted ids at every
handoff (`docs/architecture/decisions/0004-no-loss-gate-on-handoff.md`), a capacity
taxonomy in which a window may carry a deadline and exhausted credits may not, held by
a database constraint, and gates whose silence is a verdict only where the project
declared it (`src/vibey/domain/gate_timeout.py`).

Against (c) the difference is narrowest. The forge's checks are revision-bound; it
leaves the verdict's freshness to its consumers, and a green branch is not a green
merge (`docs/architecture/decisions/0036-the-merge-queue-is-declared-not-clicked.md`).
*Exact-head evaluation and the release calculus* adds the freshness test, the budget
guard after it, and a judging credential separate from the merging one. This
repository's loop ran as (c) with its approval bypassed rather than given: seven pull
requests each reached fifty-one passing checks and landed only when the operator woke
and merged them (`docs/architecture/decisions/0049-the-delegated-approver.md`), and the
forty merged into the integration branch in the 2026-09-30 scan's window carried no
review, each through the ruleset bypass
(`docs/architecture/evidence/autonomy-2026-10-01.md`).

No controlled head-to-head was run. The chaos test proves the lease fence's property,
no double commit and no lost job over 500 jobs and 8 workers, by abandoning claims
in-process, not under a kill (`tests/infrastructure/db/test_chaos.py`); it compares
nothing, and no record kills a runner alone and counts what survives. The live forced
rotation has no tracked run record, and the gated handoff has run only on the wind-down
path: the capacity-rejection path produces no brief
(`docs/architecture/decisions/0007-rotate-at-boundaries.md`) and hard credits
exhaustion is not wired (`docs/plans/handoff-protocol.md`). The autonomy scan is
evidence about this project's loop, not the model: only BUILD ran unattended, merges
ran ahead of review, and its repairs merged the same way; at the 2026-10-02 11:39Z
cutoff one of eleven stages met every threshold for running without a person
(`docs/reference/autonomy.md`).

The comparison that would settle it is only outlined. Hold fixed one host and a pinned
`gpt-oss:20b`, an item pool fixed before the run, the deadline, and a kill schedule, kills at
fixed turn boundaries and injected credits exhaustion, and run three arms on identical
items: a lone runner resumed from its save points, the same runner behind the queue and
ledger with gated handoffs, and the same work landed only through the ruleset and a
human approval. Count, per item and before analysis, items lost or committed twice
after a kill, closable items scored by the gate's id-set rules as an external key to
every arm, wall clock to terminal state including gate waits, and changes merged
without a verdict at their exact head, every run appended to the evidence ledger before
scoring.

```latex
\begin{plainwords}
We set our system beside three familiar things: a coding assistant whose chat is its record, a job system that saves each step first, and a hosting rule demanding green tests and one human approval. Ours keeps a notebook no vendor owns, checks a handover by rule, not by a model's opinion, treats "out of money" differently from "wait an hour", and reads silence as a yes only where a project opted in. The job system shares the notebook; the hosting rule already ties tests to one version. We have not raced them, and one person merged our changes past the approval; we describe the race, not its result.
\end{plainwords}
```

## Discussion

### Convergence-Driven Development as a scoreboard

Specification-driven development states acceptance criteria and test-driven
development makes them executable; neither says whether an unattended worker edited
the tracked repository, kept its package boundaries, removed exploratory artifacts,
or produced something deliverable. Convergence-Driven Development (ADR-0039) encloses
both: ground in the tracked tree, map criteria to code and tests, implement, test,
inspect, repair and deliver, until the evidence agrees. For an item let

```latex
\begin{equation}
D = U + F + B + A,
\end{equation}
```

where $U$ is the set of unmet acceptance criteria, $F$ the failing or missing checks,
$B$ the unresolved blockers and assumptions, and $A$ the unreviewed or unrelated
repository changes. An iteration is *converging* when it lowers $D$, or when a bounded
discovery step turns an unknown into a criterion, test or blocker; *neutral*
when it gathers needed evidence without changing $D$; *diverging* when it adds
unresolved work, leaves the tracked stack, loses a known fact, or widens the change
without a delivery path. A divergence bounded in size and duration is kept only with a
named step back to a lower $D$; an unbounded one is discarded and work resumes from
the last sound state ([Fig. 38](#fig:cdd-loop)). Activity is not a proxy: elapsed
time, model confidence, a verdict or a done marker lowers $D$ by nothing. The score is
kept at four nested scopes, story, epic, phase and project, with missing parent
context recorded as `unknown`, never invented, since a pass at one scope proves
nothing about the one around it.

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
    {\textbf{Deliver}\\commit, review,\\publish evidence};
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
\caption{Each pass reads the tracked repository, turns criteria into tests, builds the smallest slice, runs the tests and classifies its trajectory. Converging work is delivered: committed, reviewed and published with its evidence. Neutral or slightly divergent work continues only with a written bound and reconvergence step. Unbounded divergence is discarded and work resumes from the last sound state; activity alone is never evidence.}
\label{fig:cdd-loop}
\end{figure*}
```

The scoreboard is a useful instrument and nothing more: it does not make a model's
final sentence true, a local marker cannot prove remote delivery, and a generated file
cannot prove a feature exists in the tracked product. The project's governance canon
extends this scoreboard into a broader biological philosophy, recorded in ADR-0041 and
set out on the documentation site's page *The biological philosophy*, which this paper
neither relies on nor argues for. *The local Qwen pilot* applied it per backlog item
([Fig. 39](#fig:qwen-cdd)): a verdict naming criteria, tests, trajectory and delivery,
bounded retries, no advance past an unresolved item; partial verdicts, a failed
forty-turn run and a live process were observable; none was evidence of a finished
Python feature.

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

### Governance as the scarce input, in this record

An earlier revision read the stress record as a thesis that production is a commodity
and governance the scarce input; here we say only what this project's records show.
The design treats executors as substitutable and priced; the inputs that stopped
work in the tracked record were decisions and judgments. The stress run's collapse
was the substrate's bound exceeded, not a malfunction; at the break the heal probe
recorded `lane responsive; no heal needed`. Every remedy is an operator's decision;
the lasting correction was a rule: admission should gate on payload size, not on
concurrency count. ADR-0035 records the same shape: a review-independence rule made
absolute in two places deadlocked BUILD on a one-engine pool, deferring one job
forever with nothing in the ledger; capacity to produce was present, and the repair
was a decision about the rule.

In this record, judgment is the other scarce input: self-grading is the weakest check
(ADR-0035), and a human gate needs an explicit verdict, not an absence of objections.
The record shows why: the production violation in
*Exact-head evaluation and the release calculus* was automation acting correctly on a
stale verdict, and the throughput figures corrected in *What the records measure* were
a confident, wrong claim that stood unchallenged in a tracked paper until this revision.

On 2026-09-24 every change for 3.0.0 was sent for independent review and merging
outran the reviews: the day's release-gate record, which is not tracked, counts seven
pull requests merged before or during their reviews, open between 30 s and
49 min 44 s. Each finding went into a rescue pull request or branch while live on
`develop` and published to the development package index, the worst being two high
findings in the ledger guard; two changes that each passed their own gates broke
`develop` together. None of this is a claim about anyone's care: producing the changes
was cheap and fast that day, independent judgment took tens of minutes each, and where
a merge ran ahead of it the judgment was still paid later. The storm audit and the
autonomy scan in *What the records measure* say the same of this loop: the inputs that
stopped work were decisions and judgments. The stress curve cannot say it about
systems in general; it is a single-slot saturation curve on one machine, and which
input is scarce elsewhere is beyond this record.

```latex
\begin{plainwords}
Being busy is not the same as being done. The loop keeps a simple score: how many
promises are not yet kept, how many tests still fail, how many questions are still
open, and how many stray changes were made. Every step must lower that score, or say
how the next one will; otherwise the work goes back to the last good state. In this
project's record the workers had not broken; what stopped work was a rule that needed
changing, a decision that needed making, or a check that needed a person. On the day
merges ran ahead of reviews, the reviews still had to be done, only later.
\end{plainwords}
```

## Validation

The model is checked at three levels, and the paper's own figures are reproduced. At the *property* level, the
gate, the phase guards and the selector are pure functions under a 100% branch-coverage
floor per architectural layer, with property tests on the selector and the credits type.
At the *chaos* level, concurrent workers process a job set against a real PostgreSQL
while each randomly abandons claimed jobs mid-flight and a concurrent reaper reclaims
the expired leases; the verified property is no double commit, no lost job, and every
job terminal. Execution is at-least-once: a worker that outlives its lease may run a job
another worker has reclaimed, but the acknowledgement is fenced on the lease owner, so
the stale one is refused and exactly one commits per job. At the *live* level, a runbook
drives one project from design to local completion on two paid engines, `claudeloop` and
`agyloop`, with a forced rotation. That run is dated: `agyloop` has since been retired
(ADR-0078), and live runs over the other engines are not reported here. Where the
binaries are installed, a conformance suite drives `claudeloop` and `codexloop` through
their own offline agents; `agyloop` and the local engines have none and rest on an
in-memory double. Production-rate claims are validated separately by the stress record
(*What the records measure*), and the local Qwen pilot does not enlarge them.

The 3.0.0 additions are validated the same three ways, and each went through an
independent adversarial review. Its probes are review records, not tracked tests. The
orchestrator suite runs as the restricted application role, so a query needing an
undeclared privilege fails as `permission denied`, and a cluster-smoke step checks that
the ledger refuses update, delete and truncation to the worker's role for want of
privilege and to the owner by its triggers (#1100). The full suite at #1105's head
passed 3,627 tests, with 18 skipped and 1 expected failure, under the four floors at
100%; the count is dated to that head, not this revision.

The 3.1.0 and 3.2.0 additions carry their own tests under the same four floors, declared
since 3.2.0 as a forge rule on both permanent branches (#1277), though the forge refused
every reconcile of it until #1321, after 3.2.0; read on 2026-10-02, both rulesets carry
it. One measurement is reported as it came out, not as hoped: on a canary-injection
issue, the frame that quotes an admitted issue to DESIGN did not stop the canary
(4 of 10 runs with the raw intake, 5 of 10 framed), so the trust check that holds a
stranger's issue, not the frame, is the control that holds (`CHANGELOG.md`, 3.1.0).

The changes after 3.2.0 are validated more narrowly than they are built, and we say
where. The review lane's repair (#1316) is held by 31 tests, but its rates and 900 s
wait come from the model server's log, and at our cutoff every production verdict was on
a diff reviewed in one request. The review canary (#1325) has one measured run, and the
weekly workflow that would repeat it has not run. The autonomy scorecard (#1335) and the
host's health and tuning (#1330, #1334) are tested against fixture records; the
scorecard's workflow has not run, its readings were taken outside it, and the Linux
probes have seen only fixture trees. The client-build stage first ran in earnest on
3.3.0 (#1317, #1320); macOS signing and notarisation have run only against a fake,
because no credential exists, the iOS build only in dry runs, and the Linux requirements
(#1313) only in containers on one Mac; the native matrix has not run. The shutdown and
database repairs were found by CI, not by review (#1309, #1310, #1314, #1326); the
intermittent test race behind them was closed by #1332, which green runs alone cannot
show; the fix holds by construction.

The paper is held to the same discipline ([Fig. 40](#fig:publication-ladder)).
`docs/paper.md` is its one source: one script recomputes the evidence, another writes
the computed figures between revision-pinned markers and in check mode fails CI on
drift, and pinned tools write the LaTeX, DOCX and PDF and compile each figure into SVG
for the site and book. Two steps are not automated: a figure that fails to compile for
the site shows its caption with a warning rather than failing the release, and a
drawing's legibility is judged by a person, which is how this revision's figure defects
were found.

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

```latex
\begin{plainwords}
We check the system three ways. Tests walk every branch of the important code. A chaos test crashes helpers on purpose while a real database is running, to show that no job is lost and none is finished twice. A live run takes one whole project through two different robot helpers, with a forced switch between them in the middle; that run is old, and we do not report one on the newer helpers. The newest parts were also attacked on purpose by separate reviewers. Where a newer part was tested less than it was built, we say so. The paper itself is rebuilt from its records by pinned tools, and a person still checks that the pictures are readable.
\end{plainwords}
```

## Related work

Queue-based job schedulers built on `SKIP LOCKED` provide claims, leases and retries
but no delivery semantics. The ledger here is event sourcing in Fowler's and Helland's
sense applied above the queue, with the write-ahead discipline of ARIES and the lease
bound of Gray and Cheriton. Selection reuses nginx's smooth weighted round robin and
the circuit breaker pattern as Nygard describes it.

*Session runners and agent frameworks.* SWE-agent drives one model through a
thought, action and observation loop and saves each run as a trajectory file. During
the run its state is the model's context; the trajectory is a record to inspect, not a
state another model resumes from. Session runners such as Claude Code and Codex CLI go
further: they persist each session's transcript on disk and can resume it by session
id. When a long session fills the context window, older turns are replaced by a
summary that the model itself writes. AutoGen coordinates several agents in
conversation, and the conversation is again the state. In all of them the unit that
survives is a transcript in one vendor's shape. Moving the work to another vendor's
model, or past a context limit, passes through a summary that no procedure checks.
Here a transcript is copied in as an attachment that events reference. It is evidence
rather than state, so the session is disposable and the ledger is not.

*Durable workflow engines.* Temporal, and Cadence before it, persist an event history
for every workflow execution. When a worker dies, another worker replays that history
through deterministic workflow code and rebuilds the workflow's state exactly.
Activities run at least once under retry policies and timeouts, and signals and timers
let a workflow wait for a person. For crash recovery this is the guarantee the lease
and the ledger replay give here, and a team already running Temporal would get it from
Temporal. The transactional outbox pattern (Richardson) gives the matching guarantee for
messages; this family's own job dispatch is designed around one, though it is not yet wired. What these engines
record about a step is that it completed and what it returned. If the step is a coding
agent, the returned value is opaque to the engine. Replay restores the fact that the
agent finished and the payload it handed on, but nothing checks that the payload kept
every question the agent had opened. Capacity is opaque as well: a rate window and
exhausted credits are both failed activities. They are retried under whatever policy
the author wrote, unless the author declared one error type non-retryable.

*The property the gate adds.* Neither family admits a handoff between two
nondeterministic workers on a checked condition. The no-loss predicate of
*The no-loss handoff gate* does. It computes without a model the ids opened and not
closed in the summarised ledger range, for questions, decisions, assumptions, findings
and artifacts. The brief is admitted only if it carries every one of them, together
with the range's recomputed digest. "The successor knows what the predecessor knew" thus
becomes a set inclusion a reviewer can re-run, instead of a property of a model's
summary. It is one predicate, and a workflow engine could host it as a step. We claim
the predicate and its placement at every engine boundary, not the durable record
beneath it, which *Comparison with alternatives* sets out row by row.

Platform-native automation, merge queues and required checks, enforces revision-bound
*checks* but leaves verdict freshness to its consumers. A ruleset that also requires
an approving review, alternative (c), binds the checks to a revision but still not the
verdict's freshness: a pull request whose checks passed against an older base proves
only that that combination was green. The exact-head calculus closes that gap. Yanking
semantics for published artifacts (PEP 592) informed the report-only supersession of
releases, whose monotone sequence of published versions
*Trust separation and release monotonicity* states, and keyless publishing through
PyPI's Trusted Publishers removes stored release credentials.

Degraded-mode design follows the fail-operational tradition, with the difference that
our refusals include commercial ones, which is why the order in which a lane falls
back is set by how hard each fallback is to refuse rather than by mean time between
failures. The retrieval engine is lexical over SQLite FTS5; dense retrieval would
reintroduce the nondeterminism the reviewability invariant forbids.

The upward drift within the curve of *A single-slot saturation curve* is the
continuous batching of Orca, and the coordination cost that the six-material
postulate of *Time to completion and what modulates it* treats as a coupling rather
than a seventh material is the one Brooks described for human teams. The bound on what more lanes
sharing one model slot could buy is Amdahl's. The ledger guard uses PostgreSQL's own
trigger and privilege machinery rather than rules, whose documented behaviour on
partitions and `TRUNCATE` is what left the earlier guard open.

```latex
\begin{plainwords}
Other people have built pieces of this before: queues that hand out jobs, notebooks that are never erased, tools that let robots write code, and systems that replay work after a crash. What is different here is the combination: a strict rule for when a handoff counts, a strict line between ``slow down'' and ``out of money'', and checkpoints where silence never means yes. This section says where each borrowed idea came from.
\end{plainwords}
```

## Conclusion

Putting the ledger, not the session, at the centre makes autonomous
delivery survivable and auditable: engines become fungible, crashes become replays, and
human authority is a structural property of the state machine rather than a
prompt-engineering hope. The same discipline, binding every claim to the state it
describes, governs the runners beneath the orchestrator and the release calculus above
it, and the guarantees that 3.0.0 added, a ledger the database refuses to rewrite among
them, are each stated with the limits they do not cross.

What the records show is narrower than the model. The throughput measurement is a
single-slot saturation curve on one machine, not evidence that production is bounded in
general; in this project's records, the inputs that stopped work were decisions and
judgments. A local storm bound by one model slot converted no lane without a person,
and the audit that found this was mostly wrong until it was verified. On the day a
release's fixes landed, the step that limited delivery was independent review, which
merging outran and then had to repay. A scan of the integration branch on 2026-09-30
found this project's loop autonomous only in BUILD, every merge made through the ruleset
bypass, and seven defects, three of them failures of evidence, among them a review shown
numbers nobody measured; the repairs landed within a day, still through the bypass. The
reviewer's recall has been measured once, on small planted defects, and it showed a
reviewer that can describe a defect and still pass it. Why it fails on large diffs is
under a preregistered study, its registration kept in
`research/large-diff-review/experiments/`, that has reached its mechanism and finished
screening four diffs, not its result; production is unchanged until it does. The
distance from running without a person is now measured again rather than written once,
and at each of its first three readings one of eleven stages met its thresholds.

The engineering that remains is less about producing faster than about deciding well
and cheaply.

```latex
\begin{plainwords}
Put the notebook, not the robot, at the centre. Then any robot can be swapped out, a crash just means reading the notebook again, and people stay in charge at the moments that need them. The measurements here are modest: one machine, one reading of how fast it could go, one test of a reviewer that noticed a defect and let it through anyway, and a study of why that is not yet finished. One mistake we found was a review shown numbers nobody had measured. In this project's own records, what held work up was a decision nobody had made yet. The work ahead is making those decisions easier to reach and cheaper to get right.
\end{plainwords}
```

## Declarations

### Data and code availability

Every record this paper measures is tracked in the repository at
`https://github.com/the-vibey-project/vibey`, and every figure and table computed from
one is regenerated from it by a named script: `scripts/paper_evidence.py` recomputes the
numbers, `scripts/paper_figures.py` redraws the computed figures,
`scripts/minimum_specs.py` the requirements tables, `scripts/autonomy_scorecard.py` the
autonomy scorecard, and the storm's `storm-evidence.py` its evidence table. The sources
are the stress record (`src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md`), the
evidence records under `docs/architecture/evidence/` (the review canary's corpus and
ledger, the autonomy scorecard, the host-health record, the minimum-specs record), the
storm ledger under `docs/plans/qwenstorm-3.0.0/`, the large-diff study under
`research/large-diff-review/experiments/`, and the git history itself. The one record
the paper draws on that is not tracked, the storm throughput audit, is named as untracked
where it is used. The source of this paper is `docs/paper.md`, and the renderer that
typesets it, `vibey-gh paper`, ships in the same repository.

### Use of generative AI

The text of this paper was drafted and revised with large language models used as
writing and analysis assistants under the author's direction: Anthropic's Claude
through Claude Code, OpenAI's Codex, and the GPT-OSS and Qwen models that vibey's own
local runners drive. The same tools wrote much of the software the paper describes,
which is the subject of the paper rather than a confound of it. No AI tool is an author.
Every empirical statement was checked against the tracked records named above, and the
author takes full responsibility for all of the content, including the parts those tools
produced and every citation.

### Authorship, funding and competing interests

Adam Matthew Steinberger is the sole author: he conceived and designed the system and
the studies, built and operated the system, analysed the records, drafted and revised
the text, approves this version and is accountable for all of it, which are the four
criteria the International Committee of Medical Journal Editors sets for authorship. The
repository records no funding source for this work, which ran on the author's own
hardware and on GitHub-hosted runners, and the author declares no competing interests.

### Reporting guidelines and registrations

No reporting guideline in the EQUATOR Network's library covers a systems paper of this
kind; the library's checklists are written for health-research designs, and computer
science runs its work through conference review. We therefore follow the basic level of
the Transparency and Openness Promotion guidelines (TOP 2025) and state, above, where the
data, code and materials are. One study here is registered: the large-diff review study,
whose preregistration, log and data are tracked under
`research/large-diff-review/experiments/` and which is reported as in progress. No other
study in this paper was registered; the remaining measurements are observational records
of one project, read at the cutoffs each passage names.

```latex
\begin{plainwords}
Everything we measured is in the open repository, with the scripts that redraw every figure from it. We used AI writing and coding tools to help write this paper and to build the system it describes, and we say which ones; the author checked every claim and answers for all of it, and no tool is an author. The project's records show no one paying for this work, and the author has no competing interest to declare. The medical-style reporting checklists do not fit a systems paper, so we follow the open-science rule of saying where the data and code are; one study was registered in advance and is still running.
\end{plainwords}
```

## References

- PostgreSQL Global Development Group, *SELECT — The Locking Clause* (`FOR UPDATE SKIP LOCKED`, available since PostgreSQL 9.5). PostgreSQL documentation, `https://www.postgresql.org/docs/current/sql-select.html`, accessed 2026-10-06.
- M. Fowler, *Event Sourcing*, 2005. `https://martinfowler.com/eaaDev/EventSourcing.html`.
- P. Helland, "Immutability Changes Everything," *Communications of the ACM* 59(1):64–70, 2016. doi:10.1145/2844112.
- C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh, and P. Schwarz, "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging," *ACM Transactions on Database Systems* 17(1):94–162, 1992. doi:10.1145/128765.128770.
- C. Gray and D. Cheriton, "Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency," *Proceedings of the 12th ACM Symposium on Operating Systems Principles*, 1989, pp. 202–210. doi:10.1145/74850.74870.
- C. Richardson, *Microservices Patterns: With Examples in Java*, Manning, 2018 (the transactional outbox pattern; `https://microservices.io/patterns/data/transactional-outbox.html`).
- Temporal Technologies, *Temporal documentation: Workflows and durable execution*, `https://docs.temporal.io/workflows`, 2024; and Uber Engineering, *Cadence*, `https://cadenceworkflow.io/`, 2017.
- Anthropic, *Claude Code documentation*, `https://docs.claude.com/en/docs/claude-code/overview`, 2026; and OpenAI, *Codex CLI*, `https://github.com/openai/codex`, 2026 (session runners whose transcript is their state).
- nginx, smooth weighted round-robin upstream balancing, introduced in nginx 1.3.1 (2012), `ngx_http_upstream_round_robin.c`.
- M. T. Nygard, *Release It! Design and Deploy Production-Ready Software*, 2nd ed., Pragmatic Bookshelf, 2018 (the circuit breaker pattern).
- J. Yang, C. E. Jimenez, A. Wettig, K. Lieret, S. Yao, K. Narasimhan, and O. Press, "SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering," *NeurIPS*, 2024. arXiv:2405.15793.
- Q. Wu et al., "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," 2023. arXiv:2308.08155.
- G.-I. Yu, J. S. Jeong, G.-W. Kim, S. Kim, and B.-G. Chun, "Orca: A Distributed Serving System for Transformer-Based Generative Models," *16th USENIX Symposium on Operating Systems Design and Implementation (OSDI)*, 2022.
- F. P. Brooks, Jr., *The Mythical Man-Month: Essays on Software Engineering*, Addison-Wesley, 1975.
- PEP 592, *Adding "Yank" Support to the Simple API*, Python Packaging Authority, 2019.
- PyPI, *Trusted Publishers*, `https://docs.pypi.org/trusted-publishers/`, 2023.
- GitHub, *About protected branches and rulesets*, GitHub Docs, 2024.
- SQLite, *FTS5 Extension*, `https://www.sqlite.org/fts5.html`, accessed 2026-10-06.
- G. M. Amdahl, "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities," *Proceedings of the AFIPS Spring Joint Computer Conference*, 1967, pp. 483–485. doi:10.1145/1465482.1465560.
- PostgreSQL Global Development Group, *The Rule System* and *CREATE TRIGGER* (rules and row-level triggers on partitioned tables; `TRUNCATE` triggers). PostgreSQL documentation, `https://www.postgresql.org/docs/current/`, accessed 2026-10-06.
- International Committee of Medical Journal Editors, *Recommendations for the Conduct, Reporting, Editing, and Publication of Scholarly Work in Medical Journals*, 2026. `https://www.icmje.org/icmje-recommendations.pdf`.
- Center for Open Science, *Transparency and Openness Promotion (TOP) Guidelines*, 2025. `https://www.cos.io/initiatives/top-guidelines`.
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

## Appendix. The operational record from 3.0.0 to 4.1.0

The operator's record by release, each fact with its pull request, issue, ADR or
migration.

### Minimum system requirements

The minimum requirements are measured weekly, and the table is regenerated from a
record that keeps *measured*, *declared* and *derived* figures apart and marks a
figure it could not re-measure stale, with its date. At our cutoff, 2026-10-02, the
weekly workflow had never run: every figure comes from three seed passes on one host
on 2026-09-29 and 2026-09-30, and every row is a dated measurement, not a statement
about this revision.

<!-- BEGIN GENERATED specs:minimum-requirements — regenerated by scripts/minimum_specs.py -->
```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{1.3in}p{2.3in}p{2.0in}p{0.9in}@{}}
\textbf{Requirement} & \textbf{Minimum} & \textbf{Recommended} & \textbf{Basis}\\
\hline
Memory, Apple Silicon (unified) & 24 GB (stale since 2026-09-30: derived from stale input(s): ram.minimum\_need\_gib) (needs 20.29 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx32768)) & 32 GB (stale since 2026-09-30: derived from stale input(s): ram.recommended\_need\_gib) (needs 27.45 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx131072)) & derived, stale\\
Memory, 16 GB Mac & insufficient (stale since 2026-09-30: derived from stale input(s): ram.design\_only\_need\_gib): DESIGN alone needs 19.63 GiB (stale since 2026-09-30: derived from stale input(s): ram.model\_process.ctx8192); the GPU part is -6,344.0 MiB (stale since 2026-09-30: derived from stale input(s): bench.gpt-oss:20b.ctx8192.device\_mib, gpu.metal\_limit\_16gb\_mib) over its limit at 8,192 & - & derived, stale\\
GPU memory for gpt-oss:20b & 12,339 MiB (stale since 2026-09-30: no accounting line in the log) at 8,192; 12,974 MiB (stale since 2026-09-30: no accounting line in the log) at 32,768 & discrete GPU: 16 GB (stale since 2026-09-30: derived from stale input(s): bench.gpt-oss:20b.ctx32768.device\_mib) card (not verified on CUDA) & measured, stale; derived, stale\\
Model throughput at 24k depth & 10 tok/s generation, 100 tok/s prompt (worst BUILD turn 512 s of 900 s) & 25 / 500 tok/s (worst turn 143 s); measured here 18.1 tok/s (stale since 2026-10-02: Ollama failed at depth, num\_ctx 32768: timed out) / 379 tok/s (stale since 2026-10-02: Ollama failed at depth, num\_ctx 32768: timed out) & derived; measured, stale\\
CPU only (no GPU) & DESIGN call 373 s (fits: yes); worst BUILD turn 4,814 s (fits: no) & use a GPU; CPU only measured 4.2 tok/s generation, 7.1 tok/s prompt & derived; measured\\
Free disk & 20 GB (stale since 2026-09-30: derived from stale input(s): disk.minimum\_need\_gb) (needs 17.2 GB (stale since 2026-09-30: derived from stale input(s): disk.ollama\_app\_bytes)) & 50 GB (stale since 2026-09-30: derived from stale input(s): disk.recommended\_need\_gb) (needs 44.6 GB (stale since 2026-09-30: derived from stale input(s): disk.minimum\_need\_gb)) & derived, stale\\
Python & 3.12 (declared $\geq$3.12) & works on 3.12, 3.13, 3.14 & derived; declared\\
PostgreSQL & 14 (checked on connect) & measured on 14.24: 21 migrations applied & declared; measured\\
Ollama with gpt-oss:20b (sovereign default) & required unless a paid engine is set up; measured on 0.35.1 & - & measured\\
Model download, gpt-oss:20b & 13.79 GB & qwen3:14b 9.28 GB (opt-in) & measured\\
Install download, vibey-engine & 135.9 MB & with {[}hub{]} 137.5 MB; krypton-app 137.5 MB & measured\\
Internet at runtime (sovereign path) & none & - & measured\\
\end{tabular}
\caption{Minimum and recommended requirements for the sovereign default (vibey, gpt-oss:20b on Ollama and PostgreSQL on one host), as the weekly measurement last recorded them. Measured on GitHub-hosted ubuntu-24.04-arm, Mac17,2 $\cdot$ Apple M5 $\cdot$ 24 GiB $\cdot$ macOS 26.6.2 (25G83), aarch64 $\cdot$ unknown chip $\cdot$ 23 GiB $\cdot$ Ubuntu 24.04.4 LTS, figures dated 2026-09-29 to 2026-10-05 (UTC); record \texttt{docs/architecture/evidence/minimum-specs.json}. A stale figure is the last good value, marked with the date it was last measured.}
\label{tab:minimum-requirements}
\end{table*}
```
<!-- END GENERATED specs:minimum-requirements -->

At the seed, memory was the binding constraint, set by the context rather than the
model file; with vibey, PostgreSQL and the operating system the host needs 24 GB at
minimum and 32 GB recommended. A 16 GB Mac cannot run the sovereign default, a verdict
that is derived, since no 16 GB machine was measured. And a GPU is not optional for
BUILD: on the CPU alone, at about 4 tokens per second, a DESIGN call fits the 900 s
timeout and the worst BUILD turn does not. Linux is measured as a matrix of
distributions and architectures, each in its own container image.

<!-- BEGIN GENERATED specs:linux-requirements — regenerated by scripts/minimum_specs.py -->
```latex
\begin{table*}[t]
\centering\footnotesize
\begin{tabular}{@{}p{1.2in}p{0.55in}p{0.65in}p{0.8in}p{0.8in}p{0.9in}p{1.5in}@{}}
\textbf{Distribution} & \textbf{Arch} & \textbf{Run} & \textbf{Cores min / rec} & \textbf{Disk min / rec} & \textbf{PostgreSQL} & \textbf{glibc}\\
\hline
Ubuntu 24.04 LTS & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 16 ($\geq$ 14: yes) & 2.39 (wheels need 2.34: yes)\\
Ubuntu 24.04 LTS & aarch64 & native & unreachable (stale) / 5 (stale) & 20 GB / 50 GB & 16 ($\geq$ 14: yes) & 2.39 (wheels need 2.34: yes)\\
Ubuntu 26.04 LTS & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Ubuntu 26.04 LTS & aarch64 & native & unreachable (stale) / 5 (stale) & 20 GB / 50 GB & 18 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Arch Linux & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.44 (wheels need 2.34: yes)\\
Arch Linux & aarch64 & not run & unreachable (stale) / 5 (stale) & - & - & -\\
Fedora (current release) & x86\_64 & native & not measured / not measured & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
Fedora (current release) & aarch64 & native & unreachable (stale) / 5 (stale) & 20 GB / 50 GB & 18.6 ($\geq$ 14: yes) & 2.43 (wheels need 2.34: yes)\\
\end{tabular}
\caption{The Linux matrix: each supported distribution on each architecture, measured in the distribution's own container image. Memory is the same for every cell, 24 GB (stale) minimum and 32 GB (stale) recommended, from the least-squares line $M(c) = M_0 + kc$ fitted to the measured model memory ($M_0$ = 15,679 MiB (stale), $k$ = 33.02 (stale) KiB/token, $R^2$ = 0.999421 (stale)) with a declared headroom factor. Cores come from Amdahl's law fitted per architecture: the minimum reaches the minimum generation rate, the recommended is the knee where $dT/dn$ falls to a declared threshold. An emulated cell's sizes and versions stand; its timings are refused. Measured on GitHub-hosted ubuntu-24.04-arm, Mac17,2 $\cdot$ Apple M5 $\cdot$ 24 GiB $\cdot$ macOS 26.6.2 (25G83), aarch64 $\cdot$ unknown chip $\cdot$ 23 GiB $\cdot$ Ubuntu 24.04.4 LTS, archlinux:latest (linux/amd64, native) on GitHub-hosted ubuntu-24.04, fedora:latest (linux/amd64, native) on GitHub-hosted ubuntu-24.04, fedora:latest (linux/arm64, native) on GitHub-hosted ubuntu-24.04-arm, ubuntu:24.04 (linux/amd64, native) on GitHub-hosted ubuntu-24.04, ubuntu:24.04 (linux/arm64, native) on GitHub-hosted ubuntu-24.04-arm, ubuntu:26.04 (linux/amd64, native) on GitHub-hosted ubuntu-24.04, ubuntu:26.04 (linux/arm64, native) on GitHub-hosted ubuntu-24.04-arm, figures dated 2026-09-29 to 2026-10-05 (UTC).}
\label{tab:linux-requirements}
\end{table*}
```
<!-- END GENERATED specs:linux-requirements -->

Most of what the method promises is not yet in the table: no native runner has run a
cell, the x86_64 cells ran under emulation, where the installer crashed, and no Linux
memory, core count or ledger growth has been measured. What stands is that every cell
that ran packages a Python, a PostgreSQL and desktop libraries that meet the floors.

### 3.0.0

**The ledger guard** (#1100, ADR-0055; amended by #1112, merged 15:18Z 2026-09-24).
Migration 0016 replaces the rules with a `BEFORE UPDATE OR DELETE` row trigger and a
`BEFORE TRUNCATE` statement trigger that refuse every rewrite of `event`. Migration
0017 pins the guard functions and the owner's session to
`search_path = pg_catalog, pg_temp`; `vibey migrate` itself takes `CREATE` on `public`
from every role but the owner before any migration runs; and the `ledger-guard` doctor
check fails when the application role may create objects, owns any, may call a
`SECURITY DEFINER` function or may set `session_replication_role`. Migration 0019's
`AFTER INSERT` trigger only announces appends. A one-role install fails `ledger-guard`
and exits `migrate` with 1.

**Merges that outran review, 2026-09-24.** The release-gate record (12:22Z, untracked)
counts seven pull requests merged before or during their reviews
(#1094, #1095, #1100, #1101, #1102, #1103, #1105); #1089 merged 30 s after opening
and #1092 while its review said *not yet*. #1100 and #1103 passed separately and
broke `develop` together (repaired by #1109). #1106, a rewrite of the merged
migration 0015, closed unmerged at 13:24Z; ADR-0054 records the gap.

**The priority lane.** ADR-0054 states one contract for the job queue (#1091, #1095)
and the storm's lane queue (#1089, #1092), with follow-ups #1102, #1103, #1111
and #1122.

**The engine environment** is assembled from system basics, the engine's own variables
and credential, and the project's `engine_environment`; a declaration naming a
forbidden variable (vibey's own, libpq's, anything shaped like a database credential)
is refused when the worker is built; a forge or cloud token reaches only an engine the
project names.

**The delivery bridge** (`scripts/triaged_delivery.py`) terminates an overrunning
worker's tree deepest first with a 2 s grace, because `uv run` children outlive a
signal to their parent, then reaps with `vibey queue reap --project` (#1244); the
DESIGN-interview repair is #1258, #1261 and #1270; the fit probe is
`scripts/sovereign_probe.py`.

**The review lane** became sovereign by declaration (#1086, #1087, #1088) and refuses
a cut prompt four ways (#1094, #1101). #1101 corrects #1094's misdiagnosis of #1090,
records #1090's 3.95 characters per token, and reproduces a silent half-window read on
Ollama 0.34.2 (an 80,060-character prompt, counted as 36,798 tokens, answered HTTP 200
with `prompt_eval_count` 16,386; with `truncate: false` and `shift: false`, HTTP 400
in 0.3 s); five rounded ratios for denser text sit beside `chars_per_token` in
`src/vibey_tools/gh/docs/configuration.md`.

### 3.1.0 and 3.2.0

`vibey abandon` (#1263; from intake since #1276) releases the checkout (migration
0021, #1279). BUILD branches are `vibey/<project8>/<cycle>/<item>`; an unprovable one
parks on `foreign_branch` (#1269). Review runs in at most `max_chunks` parts, six by
default, refused pre-send as `diff_exceeds_window` or `chunk_budget_exceeded` (#1252);
`split_added_hunks` (#1278) exists because the 3.1.0 promotion's 136,308-character
`CHANGELOG.md` hunk got no verdict. The trust seam is #1248
(`scripts/intake_trust.py`).

### 3.3.0

Released 2026-10-02 (`main` at `4188aad66`, promoted by #1343).

**The scan's seven gaps** at `15e909d4c`, repair state at `4acb9be5c`. `review.demo`
was queued with no payload and its handler fell back to a JUnit report of
`failures='0'` and 100% coverage (#1294, merged). The two evidence guards were reached
only from tests (open). A paid login trusted only while younger than 24 hours deferred
paid jobs indefinitely (#1295, merged: rechecked at half its life). A BUILD session had
no wall-clock limit (#1296, merged: 240 minutes). `stop()` terminated the runner alone
(#1297, merged: a process group per session). No worktree was ever removed (#1298, open
at `4acb9be5c`, merged 12:06Z 2026-10-01; #1305 at 12:09Z). A gate's `timeout_at` and
`default_answer` were acted on by nothing (#1299, merged). #1300 declares the standing
grant in `[autonomy]`; #1302 adds 21 forbidden paths for the approver.

**The merge train's own incident.** With the required approval missing,
`gh pr merge --squash` enables auto-merge and exits 0; `merge()` read that as a merge
and deleted the head branch. Between 01:24Z and 06:47Z on 2026-10-01 six pull requests
were closed eight times (#1295 and #1298 twice; #1293, #1297, #1301, #1302 once); every
branch was restored and every pull request reopened by 09:17Z. #1301, merged 09:27:44Z,
counts only a forge-reported `MERGED` state and leaves an `OPEN` one queued.

**Repairs found by CI, not review.** #1309 reproduces the cross-loop shutdown error
(#1297's stop awaited a reap from another event loop). The `session_replication_role`
grant is one `pg_parameter_acl` row per cluster, so parallel reconciles race on
it: #1310 (`tuple concurrently updated`, PostgreSQL 16; retried up to five times with
a linear backoff, other errors raised), #1314 (`tuple concurrently deleted`), #1326
(a parameter-ACL cache-lookup failure on PostgreSQL 18, run 36925371389); #1332
serializes the tests' grants. That repairs the tests only:
production databases sharing a cluster still race on the row, the per-database
migration lock cannot serialize them, the bounded three-message retry is what holds,
and a cluster-wide lock is a recorded follow-up, not a repair (#1326, #1332).

**CI.** The KEDA contract raced a worker's drain under Helm 4, whose `--wait` counts a
terminating pod as in progress; it now waits for deployment availability and scaler
readiness, with Helm pinned (#1327). The Arch desktop job falls through four official
mirrors and retries the install three times (#1333). `vibey-gh advisory-check`
replaces `npm audit --audit-level=high`; an exception in
`.github/advisory-exceptions.toml` names one advisory in one package, expires within
30 days, and fails when expired, unmatched or patched upstream (#1336); the one,
GHSA-86w9-cpqp-85rv in node-forge 1.4.0, runs 2026-10-01 to 2026-10-31, a risk
accepted with a date, not a fix.

**The reviewer.** #1312 (run 36879717279) got two `model_timeout` attempts on a free
model: nothing enforced the output reserve, and a queued review had worn the same
code. #1316 sends the reserve as `num_predict` (16,384), refuses a filled reserve as
`done_reason=length`, sets the deadline $t = \max(t_0, p/r_p + R/r_o)$ with
$t_0 = 600$ s, $r_p = 200$ and $r_o = 20$ tokens per second, and retries `model_busy`
but not `model_timeout`; its re-plan of #1312 (deadlines 1,065 s and 1,044 s) is a
plan, not a run. #1317 was merged at 19:53Z on 2026-10-01 before its review started
and #1334 at 02:40Z before its ended. Canary (#1325): first measurement #1331
(2026-10-01), weekly run 37002135164 (2026-10-02), corpus pinned at `0f88412` (first
`2b17eb7`), ledger `docs/architecture/evidence/review-canary/ledger.jsonl`. Cut for
room: the lane's per-pull-request verdicts and run ids to 03:50Z 2026-10-02, and the
study's arms, thresholds and Stage 0 and 1 figures
(`research/large-diff-review/experiments/`).

**Clients.** The release attached eleven client files, each checked by the operator
against its checksum and attestation (#1317, #1320), and first listed the extension on
Open VSX.

### After 3.3.0, and 3.4.0

At the body's cutoff 3.4.0 was not cut and this work was planned for it (#1349) on
`develop` at `4d51a764c`; `CHANGELOG.md` at this revision dates 3.4.0 to 2026-10-02, a
later cutoff. It adds krypton desktop for Apple silicon on macOS 15 or newer, ad-hoc
signed until the Developer ID secrets exist, Intel Macs unsupported (#1351); an iOS
build through EAS (#1346, #1347, #1348, #1350); `clients/` among the version's code
paths (#1348); and desktop pairing by one-time code (#1359). The dry run 36976031188
on #1351's head was a rehearsal: no Developer ID or notarisation credential, nothing
submitted to TestFlight, Gatekeeper on a quarantined `.dmg` unexercised. Weekly canary
and minimum-requirements results lost to an artifact path were recovered
(#1361, #1365; #1360 holds downloads to their uploads' root).

### 4.0.0 and 4.1.0

4.0.0 (2026-10-03) retires and deletes `cursorloop` and `agyloop` (ADR-0078, #1376):
configuration naming either is refused, and old ledger, health and rotation rows stay
valid. Hybrid dispatch (ADR-0079) adds `[engines] mode`: `singleton`; `hybrid`, where
a paid engine takes a BUILD job only once every eligible local slot is occupied, the
job has waited `overflow_after_seconds` and the UTC day's `paid_daily_cap` is
unreached; or `auto`, the default, which falls back to `singleton` when its ledger
measurement of local-slot contention is missing, stale, invalid or failed;
sub-doctrine 8.a's overflow clause awaits the operator's ratifying merge.
`scripts/install.sh` installs vibey in one command, repairs it when run again, and
copies the whole codebase with `--from-source`; `scripts/uninstall-krypton.sh` removes
every krypton interface and never touches vibey-engine's core (sub-doctrine 10.m,
ADR-0082). The backlog loop now compares an issue against its latest verdict, after
issue #1204 received six identical reports (2026-09-27 to 2026-09-29). The 4.1.0 entry
(2026-10-05) is a heading with nothing under it.

```latex
\begin{plainwords}
This last part is the logbook for the people who run the system, version by version, with the ticket numbers to look each fact up by. It says what each guard now refuses, which changes were merged before their reviews had finished, how the merge robot once closed six changes by mistake and how every one was put back, which bugs the test computers found that no reviewer did, and which apps each release ships. Where a fix mends only the tests and not the running system, it says so.
\end{plainwords}
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
queues and ledgers, sovereign local models, reproducible benchmarks, or the measurement
of a delivery loop that is honest about what it has not yet shown, there is a lane for
you.

```latex
\begin{plainwords}
All of this is free software that anyone can read, run and improve. If you like queues, notebooks that cannot be erased, running models on your own computer, or honest measurements, there is work here for you, and the links above are where to start.
\end{plainwords}
```
