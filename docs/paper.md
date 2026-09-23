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
through a six-phase state machine whose four human gates each require an explicit
recorded verdict. Beneath the orchestrator, six session runners share one bounded,
never-blocking core that never gives a credit balance a clock and lets a capacity
verdict outrank a completion claim. Above it, an exact-head release calculus binds
every automated verdict to the revision it evaluated and terminates within a bounded
number of repairs. Beside it, a deterministic retrieval engine and a fail-closed
bootstrap layer apply the same append-before-act discipline. Finally, we report a
measured regularity from the project's own tracked records: on one machine, with the
model and deadline fixed, successful throughput stayed between 0.99 and 2.00
generations per minute while offered concurrency rose sixteen-fold. The regularity
yields a zero-shortfall time-to-completion as a testable prediction. We state what
would falsify it and what it does not cover, and we argue from the same records that
the scarce inputs were governance and correct judgment, not production.

*Artifacts.* This paper is typeset from `docs/paper.md` and published as
[PDF](https://the-vibey-project.github.io/vibey/main/paper.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/paper.docx) and
[HTML](https://the-vibey-project.github.io/vibey/main/paper/). The complete
documentation is published as a book:
[PDF](https://the-vibey-project.github.io/vibey/main/book.pdf),
[DOCX](https://the-vibey-project.github.io/vibey/main/book.docx),
[EPUB](https://the-vibey-project.github.io/vibey/main/book.epub) and
[print HTML](https://the-vibey-project.github.io/vibey/main/book-print.html). Every
empirical figure in the section on production rate is recomputed from tracked sources
by `scripts/paper_figures.py`. The visual atlas holds thirty-five figures: twenty
drawn from the model as deterministic TikZ in this source, and fifteen computed from
tracked repository records, so the PDF, its labels and its diagrams are reviewable and
reproducible rather than screenshots detached from the system. Every section closes
with a box headed *In plain words* that restates it for a reader who is not a
specialist; the boxes add nothing the formal text does not say, and a specialist may
skip them.

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
packages: the orchestrator `vibey`; six session runners, `claudeloop`, `codexloop`,
`cursorloop`, `agyloop`, `opencodeloop` and the local `qwenloop`; `vibey-gh`, which owns provenance,
merging and release; `vibey-skills`, a retrieval engine over a skill library; and
`vibey-bootstrap`, a bootstrap layer for cloud workloads. Each package once carried its
own paper. This paper consolidates them. [Fig. 1](#fig:family-tree) shows the family as
one distribution, with the Python floor each tenant keeps. Its contributions are:

- the ledger invariant, the no-loss handoff gate, the queue semantics and the gated six-phase machine, with their soundness arguments;
- a session-runner core shared by six engines, whose capacity taxonomy never gives a credit balance a clock and whose completion rule a capacity verdict outranks;
- the exact-head release calculus, with a termination bound and a recorded production counterexample;
- Convergence-Driven Development (CDD), an enclosing loop above Specification-Driven
  Development and Test-Driven Development that measures convergence at nested delivery
  scopes, models project atoms and chemical structures, and recognizes a suite of
  suites as alive in the digital realm when its organism-level signals converge;
- deterministic, fail-closed retrieval and bootstrap components built on the same append-before-act discipline;
- Biodigitology, a name for the study of digital life, with operational criteria
  that distinguish software organisms from biological organisms or sentient minds;
- a measured production-rate regularity, its modulators, the time-to-completion prediction it enables, and the observations that would falsify it.

```latex
\begin{figure*}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  run/.style={minimum width=2.45cm,minimum height=1.15cm},
  tool/.style={minimum width=5cm,minimum height=1.15cm}]
  % ---------------------------------------------------------------- the distribution
  \node[vibeycore,minimum width=5.4cm,minimum height=.95cm] (dist) at (8.875,0)
    {pip install vibey\\\mdseries one distribution, twelve console scripts};
  \node[vibeytag,anchor=west] at ($(dist.east)+(0.18,0)$) {ADR-0037};
  % ---------------------------------------------------------------- orchestrator
  \node[vibeybox,minimum width=2.8cm,minimum height=1.15cm] (vibey) at (1.65,-4.0)
    {\textbf{vibey}\\six-phase conductor\\queue on PostgreSQL};
  \node[vibeypill] at (vibey.south) {Python 3.12+};
  % ---------------------------------------------------------------- session runners
  \node[vibeysoft,run] (r1) at (5.125,-2.55)  {\textbf{claudeloop}\\paid tier};
  \node[vibeysoft,run] (r2) at (7.775,-2.55)  {\textbf{codexloop}\\paid tier};
  \node[vibeysoft,run] (r3) at (10.425,-2.55) {\textbf{cursorloop}\\paid tier};
  \node[vibeysoft,run] (r4) at (5.125,-4.2)   {\textbf{agyloop}\\paid tier};
  \node[vibeysoft,run] (r5) at (7.775,-4.2)   {\textbf{opencodeloop}\\paid tier};
  \node[vibeytealbox,run] (r6) at (10.425,-4.2) {\textbf{qwenloop}\\local, sovereign};
  \node[vibeypill] at (r1.south) {Python 3.10+};
  \node[vibeypill] at (r2.south) {Python 3.12+};
  \node[vibeypill] at (r3.south) {Python 3.12+};
  \node[vibeypill] at (r4.south) {Python 3.12+};
  \node[vibeypill] at (r5.south) {Python 3.12+};
  \node[vibeypill] at (r6.south) {Python 3.12+};
  \node[vibeybox,minimum width=7.75cm,minimum height=.7cm] (bar) at (7.775,-5.75)
    {\textbf{vibey-runners-common}\quad shared by all six runners};
  \node[vibeypill] at (bar.south) {Python 3.10+};
  % ---------------------------------------------------------------- tools
  \node[vibeyvioletbox,tool] (t1) at (15.0,-2.55)
    {\textbf{vibey-gh}\\provenance, merge train,\\promotion, release, governance canon};
  \node[vibeyvioletbox,tool] (t2) at (15.0,-4.15)
    {\textbf{vibey-skills}\\retrieval engine over\\710 skill documents in 135 plugins};
  \node[vibeyvioletbox,tool] (t3) at (15.0,-5.75)
    {\textbf{vibey-bootstrap}\\fail-closed bootstrap,\\outbox, audit chain};
  \node[vibeypill] at (t1.south) {Python 3.11+};
  \node[vibeypill] at (t2.south) {Python 3.10+};
  \node[vibeypill] at (t3.south) {Python 3.11+};
  % ---------------------------------------------------------------- lanes
  \coordinate (p1t) at (1.65,-1.5);   \coordinate (p1b) at (1.65,-6.5);
  \coordinate (p2t) at (7.775,-1.5);  \coordinate (p2b) at (7.775,-6.5);
  \coordinate (p3t) at (15.0,-1.5);   \coordinate (p3b) at (15.0,-6.5);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(vibey)(p1t)(p1b)] (L1) {};
    \node[vibeylane,fit=(r1)(r3)(r4)(r6)(bar)(p2t)(p2b)] (L2) {};
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
\caption{One command installs the whole family. The dark box is the single pip package; under it sit the orchestrator, six session runners on their shared library, and three tools. Each pill names the oldest Python a member runs on. The teal runner, qwenloop, is the local, sovereign engine that needs no paid service.}
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
  \node[vibeypill,anchor=north east] at (8.15,5.85) {2,677 + 590 lines $\cdot$ cli 100\% floor $\cdot$ tui exempt};
  \node[vibeypill,anchor=north east] at (7.65,4.8) {15,296 lines $\cdot$ 100\% branch floor};
  \node[vibeypill,anchor=north east] at (7.15,3.75) {10,276 lines $\cdot$ 100\% branch floor};
  \node[vibeypill,anchor=north] at (4.1,1.85) {8,341 lines $\cdot$ 100\% branch floor};
  \node[vibeynote,anchor=west,align=left] at (1.1,4.35) {PostgreSQL, the bus, telemetry};
  \node[vibeynote,anchor=west,align=left] at (1.6,3.3) {services, handoff, wind-down};
  \node[vibeynote,anchor=west,align=left] at (0.6,5.4) {the command line and the terminal UI};
  \draw[vibeyflow] (0.3,2.55) -- (domain.west) node[midway,above,vibeynote,text=vibeyblue,align=center,yshift=1pt] {imports point\\inward only};
  \node[vibeybox,minimum width=4.2cm] (boot) at (4.1,-0.75) {bootstrap.py\\the one composition root};
  \draw[vibeyarrow] (boot.north) -- (4.1,0);
  \node[vibeynote,anchor=west,align=left] at (6.35,-0.75) {enforced by\\import-linter in CI};
\end{tikzpicture}
\caption{The orchestrator is an onion. Code may only depend on the layers inside it, and the pure domain at the centre never touches a database, a clock or the network. One file, bootstrap.py, wires the layers together from outside, and four of the five layers must keep every branch of their code tested.}
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

The invariant is enforced, not conventional: the event relation carries database
rules that turn every `UPDATE` and `DELETE` into a no-op, and the per-project sequence
number is claimed inside the same transaction as the insert, so every ledger range
has a well-defined digest. Corrections are new events that supersede prior ones. The
function $f$ is a set of pure projections (open items, the decision log, the cost
report) computed from the event sequence alone.

Crash recovery and engine handoff follow as corollaries: a successor engine
re-derives context from the ledger alone, so a credit exhaustion on $e_i$ between
turns of an item reschedules the item onto $e_j$ with the open-question set intact.

```latex
\begin{plainwords}
The ledger is a diary written in pen. You can add a page, but you can never tear one out or rub anything out. If you made a mistake, you write a new page that says so. Because the diary is the only source of truth, any helper can read it and know exactly what is going on, even a helper that has never seen the project before.
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
worker never waits on a peer's claim, so throughput scales as
$\min(|Q|, |\mathrm{workers}|)$).

Within a project, claims are ordered by priority descending, then by the earliest
permitted run time, then by id, and they exclude items whose dependencies have not
succeeded. Within one priority class an item can be bypassed only while it is held,
and every hold is bounded by a lease: a claim sets the lease expiry to
$\mathrm{now} + L$, a live worker renews it, and a reaper returns any expired lease to
the ready state. A crashed worker therefore costs at most $L$ of delay and never a
lost item. Across priority classes the discipline is strict priority, not arrival
order. Because workers die and leases expire, every job is idempotent under replay.

```latex
\begin{plainwords}
Jobs wait in a line inside a database. A helper takes the job at the front and gets a timer with it, like a library book with a due date. A working helper keeps renewing the timer. If a helper crashes, the timer runs out and the job goes back into the line, so it is never lost. Helpers never wait for each other, so adding helpers makes the line move faster.
\end{plainwords}
```

## The six-phase machine

$$\Sigma = \langle D, B, R, D_d, D_e, D_r \rangle$$

design, build, review, deploy-design, deploy-execute, deploy-review, with the
human-gated subset $G = \{D, R, D_d, D_r\}$.

```latex
\begin{invariant}[Gate soundness]
For every $\sigma \in G$ the exit guard is a conjunction of an explicit human verdict
recorded as a ledger row and, where the phase accumulates open items, the emptiness
of a ledger-derived open set. $D \to B$ requires at least one acceptance criterion,
every criterion mapped, and an accepting verdict; $R \to \mathrm{Done}$ requires
$\mathrm{open}_{\mathrm{findings}}(R) = \varnothing$ and an accepting verdict; $D_d
\to D_e$ requires the deployment specification accepted and consent recorded; $D_r
\to \mathrm{Done}$ requires the demonstration accepted. Emptiness is never
sufficient: no gate exits on the absence of objections alone.
\end{invariant}
```

A review finding therefore cannot vanish into a transcript: it is a ledger row that
holds $\mathrm{open}(R) \neq \varnothing$, and the machine cannot leave $R$ for
completion until a human closes it. Loop-back is a routing decision over the
findings: an unambiguous finding routes $R \to B$, and a finding that needs
clarification, or a project configured for strict loop-back, routes $R \to D$. Both
are ledger transitions, not ad-hoc prompts.

A gate is not a blocked thread. A handler that needs a human returns a *park* value;
the worker records a gate row, marks the item as awaiting a human, releases its
lease, and claims the next item. The answer is itself a ledger row that re-readies
the item. Human latency therefore never holds a queue slot, and the non-blocking
progress of the previous section survives humans in the loop.

Two refinements do not change the analysis. An optional visual-design interstitial
$V$ may be inserted between $D$ and $B$ on explicit opt-in; it is human-gated on the
same terms, exiting only when the visual plan is accepted or explicitly waived. The
deployment triple $\langle D_d, D_e, D_r \rangle$ is entered only on an explicit
opt-in recorded in the ledger; declining records a successful local completion.
The complete state topology is depicted in [Fig. 4](#fig:six-phase-machine).

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
  \draw[vibeyflow,rounded corners=3pt] ([xshift=10pt]D.south) |- ($(B.south)+(0,-0.38)$) -- ([xshift=-10pt]B.south);
  \path ($(D.south)+(0.35,-0.38)$) -- ($(B.south)+(-0.35,-0.38)$) node[lab,fill=vibeymist,midway] {no visual opt-in};
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
Every job moves through six steps: plan it, build it, check it, and then, only if the person wants, plan the launch, launch it, and check the launch. Four of the six steps are gates where a person must say yes. Saying nothing is not the same as saying yes. And when the person is busy, the job simply waits in the notebook while the helpers work on other jobs.
\end{plainwords}
```

## Convergence-Driven Development

Specification-Driven Development (SDD) states intent, constraints and acceptance
criteria. Test-Driven Development (TDD) turns those criteria into executable
checks. Neither layer alone guarantees that an autonomous worker has edited the
actual repository, used its real language and package boundaries, removed
exploratory artifacts, or produced a result that can be delivered. We therefore
define **Convergence-Driven Development (CDD)** as the enclosing development
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
  \node[vibeypill, fill=vibeyblue!12, text=vibeyink, font=\sffamily\scriptsize, inner ysep=1.2pt] (o1) at (270:0.85) {item};
  \node[vibeynote, text=vibeygreen!60!black, anchor=north] (dl) at (-1.55,-2.02) {delivery merges\\work into core};
  \draw[vibeyarrow, draw=vibeygreen!75!black] (dl.north) -- (core);

  % ---------------------------------------------------------- nucleus-only
  \node[vibeynucleus, minimum size=1cm, inner sep=1pt] (core2) at (4.85,0.55) {confirmed\\core};
  \draw[vibeydashed] (4.85,0.55) circle (0.75);
  \draw[vibeydashed] (4.85,0.55) circle (1.0);
  \node[vibeynote] (tnote) at (4.85,-0.85) {no orbitals left:\\terminal};
  \node[vibeypill, fill=vibeygreen!14, text=vibeygreen!55!black] (tc) at (4.55,-1.5) {complete};
  \node[vibeypill, fill=vibeyred!10, text=vibeyred] (td) at (5.45,-1.5) {dead};

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
in the digital realm. This is a systems claim about digital life, not a claim
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
checkpoints agree. Its companion status rule is evidence-bounded: an active run,
a provisional verdict, a terminal failure, a verified revision and a published
pull request remain distinct states.

The Qwen storm applies this protocol per backlog item. It derives a read-only
context from tracked files, preserves the actual stack instead of inventing a
new one, requires a verdict containing criteria, tests, repository, levels,
trajectory, composition and delivery evidence, retries failed items a bounded number of times,
and refuses to advance past an unresolved item. The cutoff-bounded pilot below
is an illustration of why those guardrails matter: partial verdicts, a failed
forty-turn run, a live process and generated Go artifacts were all observable,
but none was evidence of a finished Python feature, as diagrammed in [Fig. 11](#fig:qwen-cdd).

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
Biodigitologist**, the person credited in this corpus with coining the term and
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

Six runners implement engines: `claudeloop` over Claude Code, `codexloop` over OpenAI
Codex, `cursorloop` over Cursor's agent and its Cloud Agents API, `agyloop` over
Gemini through the Antigravity SDK, `opencodeloop` over the official OpenCode CLI,
and `qwenloop` over a local Qwen model. The pilot below uses `qwen3:14b`; the runner
contract does not depend on that model choice. `claudeloop` came first; the others
transplanted its core. The orchestrator depends on a narrow contract that all six
honour: a bounded run, a done marker, an
event vocabulary, a capacity mapping, and a shared wind-down exit code (75) meaning
that the engine ran out of window capacity mid-item and stopped cleanly after writing
its state. Capabilities beyond the contract (savepoints, unwind, mid-run prompts and
others) differ by runner and are declared per engine.

Over the six runners the orchestrator declares seven engine identities: the six, plus
`claudeloop-local`, the claudeloop binary on a local backend profile. They fall into
two tiers. At this revision the LOCAL tier holds `qwenloop`, `opencode` (declared at
zero cost) and `claudeloop-local`, rotated among themselves before any PAID engine is
offered, and the default engine pool is `qwenloop` with `opencode`; the DESIGN and
DECOMPOSE interviews run on the sovereign provider unconditionally. The canon ratified
after this code was written points further: sub-doctrines 8.b and 8.c name exactly
two loops, `sovereignloop`, which `qwenloop` becomes, and `paidloop`, which gathers the
paid adapters, each a single instance per model fed by a queue, and they repeal
OpenCode. That migration is open work at this revision, and this paper describes the
code, not the destination.

The OpenCode adapter is intentionally provider-neutral: it records the raw JSON
events emitted by `opencode run --format json` and does not invent a model,
authentication variable or price for the provider selected inside OpenCode. The
adapter's unit, static and fake-conformance evidence is present in this tree;
live OpenCode execution remains an explicit preflight item until the external
CLI is installed.

### Bounded runs that never block

Unattended operation imposes three requirements that interactive tooling never meets:
no turn may wait on human input; every resource the vendor meters must be bounded
above by the operator, not the model; and a run's outcome must be auditable from
durable state rather than from a transcript inside a vendor session. A run is
therefore admitted only under an explicit bound vector (turns, spend, wall clock,
per-turn and output-silence watchdogs, and a ceiling $W_{\max}$ on any single
capacity wait; the exact members vary by runner) and ends at the first bound reached,
with that bound recorded. Budget enforcement is preemptive: the run stops before an
overrun, never after.

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
    \draw[vibeyedge] (credits.south) -- (11.3,3.95);
  \end{scope}
  \foreach \y/\txt in {4.72/{\textbf{Type}: no reset field},
                       4.30/{\textbf{Property test}: never a deadline},
                       3.88/{\textbf{CHECK constraint}: no reset time}}{
    \draw[shield] (11.3-1.55,\y+.19) -- (11.3+1.55,\y+.19) -- (11.3+1.55,\y-.06) -- (11.3,\y-.26) -- (11.3-1.55,\y-.06) -- cycle;
    \node[shieldtext] at (11.3,\y-.01) {\txt};
  }
  % ---- runner vocabularies beneath
  \node[runner] (qwen)   at (2.4,1.9)   {qwenloop $\cdot$ 3 states\\hardware, not a balance};
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

`qwenloop` has no vendor. Its capacity is hardware, with the states available, locally
busy and misconfigured, and nobody refills it by adding a payment method. Model
acquisition is explicit: the doctor never downloads weights, and installing a model
is a separate, deliberate command, because a surprise multi-gigabyte download is
itself a capacity event on the constrained machine the runner exists to respect.
Because no external party can revoke its capacity, it is the family's sovereign
fallback: it is an opt-in standby for BUILD, and it is the preferred provider for the
DESIGN interview, which it can run with no vendor account at all.

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

Budget caps are per item (turns) and per cycle (dollars), summed from the cost the
engines report on each completed turn; engines carry cost rates, not caps. An
exhausted budget parks the item before a session starts, never after.

At each rotation point the eligible engines (installed, conformant, authenticated,
circuit not open) are ranked by smooth weighted round robin. Each candidate carries
an effective weight $w_i = \max(1, \mathrm{round}(b_i h_i f_i c_i a_i))$ for base
weight $b_i$, health $h_i$ from a per-engine circuit breaker, fidelity $f_i$ of the
engine's effort projection to the requested effort, a cost factor $c_i$ (fixed at 1
in the current implementation), and a warm-session affinity $a_i$. The selector adds
$w_i$ to each candidate's running total, picks the maximum, and subtracts
$\sum_i w_i$ from the winner, so the sequence is deterministic and spreads load in
proportion to weight without bursts. Rotation fires only at boundaries (a new item, a
capacity rejection, which excludes the rejecting engine, a graceful wind-down, an
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
  \node[vibeytealbox,eng,minimum width=2.45cm] (qwen) at (1.3,2.1)
    {\textbf{qwenloop}\\local Ollama, sovereign};
  \node[vibeytealbox,eng,minimum width=2.7cm] (cll) at (4.05,2.1)
    {\textbf{claudeloop-local}\\local backend profile};
  \node[vibeytealbox,eng,minimum width=2.3cm] (opencode) at (6.75,2.1)
    {\textbf{opencodeloop}\\zero-cost, declared};
  % ------------------------------------------------ paid tier (fallback)
  \node[vibeysoft,eng,minimum width=1.45cm] (claude)   at (0.825,-0.7) {\textbf{claudeloop}\\Anthropic};
  \node[vibeysoft,eng,minimum width=1.4cm]  (codex)    at (2.4,-0.7)   {\textbf{codexloop}\\OpenAI};
  \node[vibeysoft,eng,minimum width=1.4cm]  (cursor)   at (3.95,-0.7)  {\textbf{cursorloop}\\Cursor};
  \node[vibeysoft,eng,minimum width=1.15cm] (agy)      at (5.375,-0.7) {\textbf{agyloop}\\Google};
  \node[lab,font=\sffamily\tiny,text width=1.75cm,align=center] at (7.05,-0.7) {paid engines are declared, never default};
  % lane extents: shared x-range, headroom for the lane label
  \coordinate (p1a) at (0.05,2.905);  \coordinate (p1b) at (7.95,1.675);
  \coordinate (p2a) at (0.05,0.105);  \coordinate (p2b) at (7.95,-1.125);
  \begin{scope}[on background layer]
    \node[vibeylane,fit=(qwen)(cll)(opencode)(p1a)(p1b)] (L1) {};
    \node[vibeylane,fit=(claude)(agy)(p2a)(p2b)] (L2) {};
  \end{scope}
  \node[vibeylanelabel] at (L1.north west) {Local tier};
  \node[vibeylanelabel] at (L2.north west) {Paid tier};
  % ------------------------------------------------ the selector
  \node[vibeycore,minimum width=4.4cm] (sel) at (11.0,0.7)
    {Engine selector\\smooth weighted round robin\\$w_i=\max(1,\mathrm{round}(b_i h_i f_i c_i a_i))$};
  \draw[vibeyflow,rounded corners=3pt] (L1.east) -- ++(0.3,0) |- ([yshift=7pt]sel.west);
  \draw[vibeyflow,rounded corners=3pt] (L2.east) -- ++(0.3,0) |- ([yshift=-7pt]sel.west);
  \node[lab,anchor=west] at (8.62,1.65) {eligible local engines\\first (sub-doctrine 8.a)};
  \node[lab,anchor=west] at (8.62,-0.3) {paid engines only when\\no local engine is eligible};
  % ------------------------------------------------ the session and the handoff
  \node[vibeybox,eng,minimum width=3.6cm] (sess) at (15.75,2.1)
    {\textbf{Turns on the chosen engine}\\unattended; ledger range $\rho$};
  \node[vibeybox,eng,minimum width=3.6cm] (brief) at (15.75,-0.7)
    {\textbf{Handoff brief}\\checked by the no-loss gate};
  \node[vibeygate,minimum width=2.8cm] (gate) at (15.75,-2.45)
    {\textbf{Human gate}\\never a silent partial};
  \draw[vibeyflow,rounded corners=3pt] ([yshift=7pt]sel.east) -- ++(0.4,0) |- (sess.west);
  \node[lab,anchor=east] at (13.45,1.6) {chosen engine};
  \draw[vibeyback] ([xshift=0.95cm]sess.south) -- ([xshift=0.95cm]brief.north);
  \node[redlab,anchor=east] at (16.55,0.7) {capacity rejection\\at a boundary};
  \draw[vibeyback,rounded corners=3pt] (brief.west) -| (sel.south);
  \node[redlab,anchor=north] at (12.5,-0.85) {seeds the successor;\\rejecting engine excluded};
  \draw[vibeyback] ([xshift=0.95cm]brief.south) -- ([xshift=0.95cm]gate.north);
  \node[redlab,anchor=east] at (16.55,-1.56) {gate fails: retry, full\\transcript, or a human};
  % ------------------------------------------------ the boundary rule
  \node[vibeypill] at (4.0,-2.45)
    {rotation fires only at a boundary, never inside a turn:\\
     new item $\cdot$ capacity rejection $\cdot$ wind-down $\cdot$ effort escalation $\cdot$ crash $\cdot$ phase transition};
\end{tikzpicture}
\caption{Choosing an engine. Local engines (teal) are preferred; paid engines (blue) are the fallback. The selector ranks eligible engines by smooth weighted round robin. A capacity rejection sends a handoff brief through the no-loss gate to the next engine, excluding the one that failed. Rotation happens only at a boundary, so each handoff has a well-defined ledger range $\rho$.}
\label{fig:engine-pool}
\end{figure*}
```

```latex
\begin{plainwords}
A runner is a program that lets one robot helper work by itself, safely. Every run has limits: how many turns, how much money, how much time. The runners never sit waiting for a person to type. They also know the difference between ``come back in ten minutes'' and ``you have no money left'', and they never mistake one for the other. A fair rotation shares jobs among the helpers, and a helper that says ``I am out'' is never believed when it also says ``I finished''.
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

[Fig. 14](#fig:evaluation-automaton) draws the same function as a state machine.

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm,
  st/.style={minimum width=1.65cm,minimum height=.8cm},
  g/.style={font=\sffamily\tiny,text=vibeygray,align=center,inner sep=1.2pt}]
  % ---- states: top row
  \node[vibeybox,st]  (P) at (1.0,0)  {\textbf{Pending}\\checks incomplete};
  \node[vibeysoft,st] (R) at (4.25,0) {\textbf{Review}\\$h$ awaits its verdict};
  \node[vibeygood,st] (G) at (7.5,0)  {\textbf{Ready}\\absorbing};
  % ---- states: bottom row
  \node[vibeysoft,st] (F) at (2.3,-2.3) {\textbf{Repair}\\agent pushes $h'$};
  \node[vibeywarn,st] (B) at (6.2,-2.3) {\textbf{Blocked}\\absorbing};
  % ---- start marker
  \node[vibeyanchor] (S) at (-0.2,0) {};
  \draw[vibeyarrow] (S) -- (P);
  % ---- forward flow
  \draw[vibeyflow] (P) -- (R) node[g,midway,above] {checks complete};
  \draw[vibeyarrow,draw=vibeygreen] (R) -- (G) node[g,midway,above,text=vibeygreen] {$r=h,\ v=\top$};
  % ---- fail with budget left: repair, then a new head returns to review
  \draw[vibeyback] (R) to[bend right=22] (F);
  \node[g,text=vibeyred] at (1.95,-1.05) {$r=h,\ v=\bot,\ a<A$\\$a:=a+1$};
  \draw[vibeyflow] (F) to[bend right=22] (R);
  \node[g,text=vibeyblue] at (2.3,-3.1) {repair pushes $h'$: $a:=a+1$\\$r\neq h'$, back to review};
  % ---- fail with budget spent: blocked, until an operator refills
  \draw[vibeyback] (R) to[bend left=22] (B);
  \node[g,text=vibeyred] at (6.55,-1.05) {$r=h,\ v=\bot,\ a\ge A$};
  \draw[vibeyarrow,draw=vibeygold] (B) to[bend left=22] (R);
  \node[g,text=vibeygold!80!black] at (6.2,-3.1) {operator refill, $k\le k_{\max}$\\$a:=0$, back to review};
  % ---- the invariant: freshness is tested before the budget
  \node[vibeypill,fill=vibeygold!22] (pill) at (4.25,0.85) {freshness first: $r\neq h$ is tested before $a\ge A$};
  \draw[vibeydashed] (pill.south) -- (R.north);
  % ---- footnote
  \node[vibeynote] at (4.25,-4.05) {$E(h,\sigma)$ depends only on the head $h$ and $\sigma=(a,r,v,k)$.\\Reviews are free; only repairs count toward the budget $A$.};
\end{tikzpicture}
\caption{The release calculus as a state machine. A pull request waits in Pending until its checks finish, then goes to Review because its newest commit $h$ has no verdict yet. A pass leads to Ready; a fail leads to Repair while attempts remain, and every repair pushes a new commit that must be reviewed again. Only when the fail arrives with the budget spent does it become Blocked, and only an operator refill reopens it.}
\label{fig:evaluation-automaton}
\end{figure}
```

```latex
\begin{theorem}[Bounded convergence]
Absent contributor pushes, every lineage reaches a terminal state in at most
$A\,(1+k_{\max})$ repairs, where $k_{\max}$ bounds operator refills.
\end{theorem}
\begin{proof}[Proof sketch]
Heads advance only via repairs, since a contributor push begins a new lineage by
definition. Each repair increments $a$; $a$ is bounded by $A$; $a$ resets only via
refill, itself bounded by $k_{\max}$. The transition relation admits no cycle that
leaves $(a, k)$ unchanged, so the lexicographic measure
$\mu = (k_{\max} - k,\; A - a)$ strictly decreases across every non-terminal loop,
and $\mathsf{ready}$ and $\mathsf{blocked}$ absorb.
\end{proof}
```

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
request. This trace occurred in production: the escalation's own report listed an
empty set of remaining failures. Commit `4afafbae` reordered the two guards, restoring
the budget-placement invariant, and its regression test asserts that the
counterexample now yields $\mathsf{review}$.

**Trust separation.** Three principals with pairwise-disjoint capabilities operate
the loop: the per-job platform token publishes claims but cannot act; the reviewing
credential proposes revisions on guarded branches but cannot merge; the merging
credential consumes verdicts but can never produce them. No single credential can
both judge and act, so a compromised judge cannot ship and a compromised actor cannot
self-approve. Untrusted third-party revisions are data to all three principals
([Fig. 16](#fig:trust-separation)).

```latex
\begin{figure}[!t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeysoft,minimum width=1.55cm,minimum height=.95cm] (platform) at (3.45,4.4) {platform\\token};
  \node[vibeygate,minimum width=1.55cm,minimum height=.95cm] (reviewer) at (5.15,4.4) {reviewing\\credential};
  \node[vibeycore,minimum width=1.55cm,minimum height=.95cm] (merger) at (6.85,4.4) {merging\\credential};
  \foreach \y/\row in {3.4/publish claims, 2.7/propose revisions, 2.0/merge or release, 1.3/produce a verdict}
    {\node[font=\sffamily\scriptsize,text=vibeyink,anchor=east] at (2.55,\y) {\row};
     \draw[vibeyline] (0.05,\y-0.35) -- (7.75,\y-0.35);}
  \draw[vibeyline] (0.05,3.75) -- (7.75,3.75);
  \newcommand{\yes}{\textcolor{vibeygreen}{\ding{51}}}
  \newcommand{\no}{\textcolor{vibeyred}{\ding{55}}}
  \node at (3.45,3.4) {\yes}; \node at (5.15,3.4) {\no}; \node at (6.85,3.4) {\no};
  \node at (3.45,2.7) {\no};  \node at (5.15,2.7) {\yes}; \node at (6.85,2.7) {\no};
  \node at (3.45,2.0) {\no};  \node at (5.15,2.0) {\no};  \node at (6.85,2.0) {\yes};
  \node at (3.45,1.3) {\no};  \node at (5.15,1.3) {\yes}; \node at (6.85,1.3) {\no};
  \node[vibeypill] at (3.9,0.45) {a judge cannot ship; an actor cannot self-approve};
  \node[vibeyghost,minimum width=2.3cm] (stranger) at (1.3,4.4) {third-party\\revision: data};
\end{tikzpicture}
\caption{Three keys, three different powers. The platform token may only publish what it found, the reviewing key may only propose fixes, and the merging key may only act on verdicts it never wrote. No single stolen key can both grade a change and ship it, and code from strangers is treated as data by all three.}
\label{fig:trust-separation}
\end{figure}
```

**Release monotonicity.** Versions are derived, not remembered: for mainline $M$ and
change set $\Delta$, $\mathrm{ver}(M \cup \Delta) \geq \mathrm{ver}(M)$, with equality
exactly when $\Delta$ carries no shippable content, and the derivation is idempotent,
so re-promoting identical content never compounds a bump. Published versions form a
monotone sequence, and the publish step treats an already-published version as a
no-op, never an error.

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

```latex
\begin{plainwords}
A pull request changes over time, like a homework draft that gets rewritten. A grade belongs to one draft only. Vibey never uses a grade from an old draft to decide about a new one. It counts repairs, not reviews, so the helpers cannot loop forever. And the key that grades a change is never the key that publishes it, so no single stolen key can both cheat and ship.
\end{plainwords}
```

## Deterministic retrieval and fail-closed bootstrap

Two further components apply the ledger's discipline, append before acting and fail
closed rather than degrade silently, at other scales.

**Retrieval.** A skill library cannot be loaded wholesale into a context window, yet
fragmentary retrieval of safety- and correctness-critical guidance is worse than none.
At revision `559638f4` the library holds 710 skill documents across 135 plugins.
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
section asks what, given that, bounds the rate of delivery. It uses three tracked
sources and nothing else: the sovereignty stress record
(`src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md`), the cutoff-bounded local
Qwen storm record
(`src/vibey_tools/gh/docs/qwenloop-storm-2026-09-20.json`), and this repository's git
history, which is field data. The stress record is a controlled escalation of the local
review lane; the Qwen record is an operational reliability observation, not another
throughput experiment.
`scripts/paper_evidence.py` recomputes every figure in this section from those three
sources; history figures are stated at revision `842db09d2e61`, which the script's
`--rev 842db09d2e61` reproduces.

### The stress record

A harness fired $N$ simultaneous generations at `qwen2.5-coder:14b`, served by ollama
on one machine with 24 GB of memory and 10 cores, for $N$ from 1 to 128, with a 900 s
deadline per generation. Each generation was a real unit of work, an issue triaged or
a pull-request diff reviewed, drawn from a pool of seven artifacts of 2 to 22 KB.
Throughput is successful generations per minute of rung wall clock, reported across four views in [Fig. 18](#fig:stress-rate).

<!-- BEGIN GENERATED figure:stress-dashboard rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 2,horizontal sep=1.7cm,vertical sep=1.45cm},
  vibeyaxis,width=7.9cm,height=4.3cm,xmode=log,log basis x=2,xtick={1,2,4,8,16,32,64,128},xticklabels={1,2,4,8,16,32,64,128},
  xmin=0.8,xmax=160,xlabel={offered concurrency $N$}]
\nextgroupplot[title={a. Successful throughput},ylabel={generations / min},ymin=0,ymax=4]
\fill[vibeyblue!9] (axis cs:2,0) rectangle (axis cs:32,4);
\node[vibeynote,text=vibeyblue,anchor=south] at (axis cs:8,3.55) {stable region $N=2$--$32$};
\draw[vibeydashed] (axis cs:0.8,0.99) -- (axis cs:160,0.99) node[vibeynote,anchor=west,text=vibeygray] {0.99};
\draw[vibeydashed] (axis cs:0.8,2.0) -- (axis cs:160,2.0) node[vibeynote,anchor=west,text=vibeygray] {2.00};
\addplot[vibeyblue,line width=1pt,mark=*,mark size=1.4pt,mark options={fill=white,line width=.7pt}] coordinates {(1,0.36) (2,0.99) (3,0.99) (4,1.17) (6,1.72) (8,1.27) (12,1.54) (16,1.37) (24,1.4) (32,2.0) (48,1.6) (64,2.66) (96,3.52) (128,1.53)};
\node[vibeycallout,anchor=south east] at (axis cs:96,3.52) {peak 3.52/min\\55.2\% success};
\node[vibeycallout,anchor=north west] at (axis cs:128,1.53) {collapse};
\nextgroupplot[title={b. Success fraction},ylabel={succeeded (\%)},ymin=0,ymax=124,ytick={0,25,50,75,100}]
\draw[vibeydashed] (axis cs:0.8,87.5) -- (axis cs:160,87.5) node[vibeynote,anchor=west,text=vibeygray] {87.5};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeygreen!80] coordinates {(1,100.0) (2,100.0) (3,100.0) (4,100.0) (6,100.0) (8,100.0) (12,100.0) (16,100.0)};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeygold!90] coordinates {(24,87.5) (32,93.8)};
\addplot[ybar,bar width=5pt,bar shift=0pt,draw=none,fill=vibeyred!75] coordinates {(48,50.0) (64,62.5) (96,55.2) (128,18.0)};
\node[vibeynote,anchor=north west,align=left] at (axis cs:0.9,122) {\textcolor{vibeygreen}{$\blacksquare$} 100\% \quad \textcolor{vibeygold}{$\blacksquare$} 87.5--93.8\% \quad \textcolor{vibeyred}{$\blacksquare$} overloaded};
\nextgroupplot[title={c. Latency against the 900\,s deadline},ylabel={seconds},ymin=0,ymax=1000,legend pos=north west]
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

<!-- BEGIN GENERATED figure:stress-cumulative rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=8.6cm,height=5cm,xmin=1,xmax=14,ymin=0,ymax=474,
  xtick={1,2,3,4,5,6,7,8,9,10,11,12,13,14},xticklabels={1,2,3,4,6,8,12,16,24,32,48,64,96,128},
  xlabel={rung (offered concurrency $N$)},ylabel={generations, cumulative},legend pos=north west]
\addplot[fill=vibeysilver!35,draw=vibeysilver,line width=.5pt] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,76) (10,108) (11,156) (12,220) (13,316) (14,444)} \closedcycle;
\addlegendentry{attempted}
\addplot[fill=vibeygreen!45,draw=vibeygreen,line width=.8pt] coordinates {(1,1) (2,3) (3,6) (4,10) (5,16) (6,24) (7,36) (8,52) (9,73) (10,103) (11,127) (12,167) (13,220) (14,243)} \closedcycle;
\addlegendentry{succeeded}
\node[vibeynote,anchor=south east,align=right] at (axis cs:14,251) {243 of 444\\54.7\% overall};
\end{axis}
\end{tikzpicture}
\caption{Cumulative generations across the fourteen rungs of the stress record: 444 attempted, 243 succeeded. The gap opens only after the stable region; every failure in the run was a clean timeout, never a malformed response.}
\label{fig:stress-cumulative}
\end{figure}
```
<!-- END GENERATED figure:stress-cumulative -->

### The local Qwen storm pilot

The same-day local storm exercised the latest qwenloop runner against the open Vibey
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
tool calls and sixteen writes totalling 13,571 bytes. A fresh run directory had been
allocated at the cutoff but had no events yet. Another produced one tool error after
one turn. Four directories had no events at this cutoff, while one storm process was
still alive. Across all thirteen directories the logs contain 105 model-turn
boundaries, 85 tool calls, 550,576 input tokens, 83,609 output tokens, and 42
file-write calls totalling 32,073 bytes, as detailed across each run in [Fig. 20](#fig:qwen-runs).
Thus the accepted completion rate at the cutoff was 4/13, or 30.8%, while a verdict alone
would have suggested 6/13, or 46.2%.

<!-- BEGIN GENERATED figure:qwen-runs rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.8cm},vibeyaxis,width=8.6cm,height=4.6cm,
  xmin=0.3,xmax=13.7,xtick={1,2,3,4,5,6,7,8,9,10,11,12,13},xlabel={run, in order of start}]
\nextgroupplot[title={a. Turns and tool calls per run},ylabel={count},ymin=0,legend pos=north west,ybar,bar width=4pt]
\addplot[fill=vibeyblue,draw=none] coordinates {(1,11) (2,1) (3,0) (4,0) (5,0) (6,5) (7,9) (8,9) (9,2) (10,6) (11,40) (12,22) (13,0)};
\addlegendentry{model turns}
\addplot[fill=vibeyteal!80,draw=none] coordinates {(1,13) (2,1) (3,0) (4,0) (5,0) (6,4) (7,8) (8,12) (9,2) (10,5) (11,20) (12,20) (13,0)};
\addlegendentry{tool calls}
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:1,-4.5) {};
\node[fill=vibeyred!60,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:2,-4.5) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:3,-4.5) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:4,-4.5) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:5,-4.5) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:6,-4.5) {};
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:7,-4.5) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:8,-4.5) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:9,-4.5) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:10,-4.5) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:11,-4.5) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:12,-4.5) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:13,-4.5) {};
\nextgroupplot[title={b. Tokens per run (thousands)},ylabel={tokens ($\times 10^3$)},ymin=0,legend pos=north west,ybar,bar width=4pt]
\addplot[fill=vibeyviolet!85,draw=none] coordinates {(1,93.4) (2,1.3) (3,0.0) (4,0.0) (5,0.0) (6,23.4) (7,62.3) (8,17.1) (9,4.3) (10,8.6) (11,238.6) (12,101.6) (13,0.0)};
\addlegendentry{input}
\addplot[fill=vibeygold,draw=none] coordinates {(1,9.8) (2,0.4) (3,0.0) (4,0.0) (5,0.0) (6,4.1) (7,8.1) (8,7.5) (9,0.9) (10,5.7) (11,30.5) (12,16.5) (13,0.0)};
\addlegendentry{output}
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:1,-27) {};
\node[fill=vibeyred!60,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:2,-27) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:3,-27) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:4,-27) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:5,-27) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:6,-27) {};
\node[fill=vibeygold,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:7,-27) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:8,-27) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:9,-27) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:10,-27) {};
\node[fill=vibeyred,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:11,-27) {};
\node[fill=vibeygreen,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:12,-27) {};
\node[fill=vibeysilver,minimum width=8pt,minimum height=4pt,inner sep=0pt] at (axis cs:13,-27) {};
\end{groupplot}
\node[vibeynote,anchor=north west,align=left] at ([yshift=-0.85cm]group c1r1.south west)
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
`tools/storm-evidence.py`, fills from the storm's own progress log and lane results.

Each lane was allowed at most three attempts. Across the 30 lanes the ledger holds,
70 attempts and 2,606 model turns were logged ([Fig. 23](#fig:storm-lanes)). Seventeen
lanes ended in a completion claim, and a claim is not delivery: over the same span the
reviewer integrated 8 lanes and abandoned 2, and the rest remained unsettled at the
cutoff. The figures below are the tool's own, regenerated between its markers; every
sentence about them is written outside those markers.

<!-- BEGIN GENERATED storm-evidence — regenerated by tools/storm-evidence.py -->

*Derived from `docs/plans/qwenstorm-3.0.0/evidence/ledger.jsonl`, an append-only record consumed under sub-doctrine 10.g.*
*Regenerated automatically; do not edit inside these markers.*
*This block states figures only — every claim about them is written by a person outside it.*

| quantity | value |
|---|---|
| ledger records | 245 |
| span consumed from | 2026-09-23T04:40:49Z |
| span consumed to | 2026-09-23T11:27:36Z |
| lanes observed | 30 |
| lanes claiming completion | 17 |
| lane starts / ends logged | 49 / 42 |
| lanes integrated / abandoned | 8 / 2 |
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
  \node[vibeynote,anchor=north west] at (6.5,1.7) {offset 13,245};
  % the position watermark
  \draw[vibeyflow,-] (6.45,1.35) -- (6.45,3.15);
  \node[vibeytag,fill=vibeyblue,anchor=south] at (6.45,3.2) {watermark = byte offset};
  \node[vibeynote,text=vibeyblue,anchor=north,align=center] at (3.4,1.35) {everything before the offset\\is in the ledger, by identity};
  % the timestamp cutoff, which loses records
  \draw[vibeyback,-] (7.65,0.55) -- (7.65,2.75);
  \node[vibeycallout,anchor=north,align=center] at (7.5,0.5) {a timestamp cutoff drawn here\\would skip the late record and\\the one that shares its second};
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
<!-- BEGIN GENERATED figure:storm-lanes rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\begin{scope}[on background layer]
\draw[vibeyline] (0.00,-8.95) -- (0.00,0.25) node[vibeynote,anchor=south] {0}; \draw[vibeyline] (2.08,-8.95) -- (2.08,0.25) node[vibeynote,anchor=south] {40}; \draw[vibeyline] (4.16,-8.95) -- (4.16,0.25) node[vibeynote,anchor=south] {80}; \draw[vibeyline] (6.24,-8.95) -- (6.24,0.25) node[vibeynote,anchor=south] {120}; \draw[vibeyline] (8.32,-8.95) -- (8.32,0.25) node[vibeynote,anchor=south] {160};
\end{scope}
\node[vibeyhead] at (-4.0,0.55) {lane};
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
   30 lanes, 70 attempts, 2,606 turns; 17 lanes claimed completion,
   8 were integrated and 2 abandoned by the reviewer};
\end{tikzpicture}
\caption{Every lane of the QwenStorm 3.0.0 evidence ledger, one row per lane in issue order. Each bar is one attempt, its length the turns the local model spent, green where the attempt ended in a completion claim and red where it failed; a lane gets at most three. Of 30 lanes, 17 claimed completion, and a claim is not delivery: the reviewer integrated 8 and abandoned 2 over the same span. Read from the ledger between 2026-09-23T04:40:49Z and 2026-09-23T11:27:36Z with no gaps.}
\label{fig:storm-lanes}
\end{figure*}
```
<!-- END GENERATED figure:storm-lanes -->

Because a single local model instance served every lane in turn, attempts never
overlapped in time. The timeline in [Fig. 24](#fig:storm-timeline) shows the lanes as
the progress log recorded them; the bars never overlap, and the blank stretches between
them are the reviewer's and the operator's time, not the machine's.

<!-- BEGIN GENERATED figure:storm-timeline rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
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
\draw[vibeydashed] (6.41,-9.66) -- (6.41,0.45) node[vibeynote,anchor=south,text=vibeygray] {2026-09-23 UTC};
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
\fill[vibeysilver] (5.39,-0.09) rectangle (5.51,0.09);
\node[vibeynote,anchor=west,text=vibeysilver] at (5.54,0.00) {no end};
\fill[vibeyblue!80,rounded corners=1pt] (5.40,-2.01) rectangle (5.51,-1.83);
\fill[vibeyblue!80,rounded corners=1pt] (5.51,-2.25) rectangle (5.57,-2.07);
\fill[vibeyblue!80,rounded corners=1pt] (5.54,-2.49) rectangle (5.65,-2.31);
\fill[vibeysilver] (5.65,-2.25) rectangle (5.77,-2.07);
\node[vibeynote,anchor=west,text=vibeysilver] at (5.80,-2.16) {no end};
\fill[vibeyblue!80,rounded corners=1pt] (6.04,-2.73) rectangle (6.13,-2.55);
\fill[vibeyblue!80,rounded corners=1pt] (6.13,-2.97) rectangle (6.23,-2.79);
\fill[vibeyblue!80,rounded corners=1pt] (6.23,-3.21) rectangle (6.29,-3.03);
\fill[vibeyblue!80,rounded corners=1pt] (6.29,-3.45) rectangle (6.39,-3.27);
\fill[vibeyblue!80,rounded corners=1pt] (6.39,-3.69) rectangle (6.59,-3.51);
\fill[vibeyblue!80,rounded corners=1pt] (6.59,-3.93) rectangle (6.69,-3.75);
\fill[vibeyblue!80,rounded corners=1pt] (6.69,-3.69) rectangle (6.85,-3.51);
\fill[vibeyblue!80,rounded corners=1pt] (6.85,-4.17) rectangle (6.91,-3.99);
\fill[vibeysilver] (6.89,-4.41) rectangle (7.01,-4.23);
\node[vibeynote,anchor=west,text=vibeysilver] at (7.04,-4.32) {no end};
\fill[vibeysilver] (7.23,-4.65) rectangle (7.35,-4.47);
\node[vibeynote,anchor=west,text=vibeysilver] at (7.38,-4.56) {no end};
\fill[vibeysilver] (7.33,-4.65) rectangle (7.45,-4.47);
\node[vibeynote,anchor=west,text=vibeysilver] at (7.48,-4.56) {no end};
\fill[vibeyblue!80,rounded corners=1pt] (7.34,-4.65) rectangle (7.46,-4.47);
\fill[vibeyblue!80,rounded corners=1pt] (7.46,-4.89) rectangle (7.53,-4.71);
\fill[vibeyblue!80,rounded corners=1pt] (7.53,-5.13) rectangle (7.85,-4.95);
\fill[vibeyblue!80,rounded corners=1pt] (7.85,-5.37) rectangle (8.18,-5.19);
\fill[vibeyblue!80,rounded corners=1pt] (8.18,-5.61) rectangle (8.34,-5.43);
\fill[vibeysilver] (8.34,-5.85) rectangle (8.46,-5.67);
\node[vibeynote,anchor=west,text=vibeysilver] at (8.49,-5.76) {no end};
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
\fill[vibeysilver] (11.25,-9.21) rectangle (11.37,-9.03);
\node[vibeynote,anchor=west,text=vibeysilver] at (11.40,-9.12) {no end};
\fill[vibeyblue!80,rounded corners=1pt] (12.22,-9.21) rectangle (12.40,-9.03);
\fill[vibeysilver] (12.40,-9.45) rectangle (12.52,-9.27);
\node[vibeynote,anchor=west,text=vibeysilver] at (12.55,-9.36) {no end};
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
  {one bar per logged start--end pair; time in UTC from 2026-09-22 12:03; a lane started twice is drawn twice};
\end{tikzpicture}
\caption{Lane starts and ends as the storm's progress log recorded them, over 23.1 hours from 2026-09-22 12:03 UTC. One local model served every lane in turn, one instance per model; the bars therefore never overlap in time, and the blank stretches are the reviewer's and the operator's, not the machine's.}
\label{fig:storm-timeline}
\end{figure*}
```
<!-- END GENERATED figure:storm-timeline -->

### Host hardware benchmarks and context headroom

On 2026-09-22 the storm was paused and the same ten-turn session was replayed against
five server configurations on the one 24 GB host, with the results kept as a tracked
file (`docs/plans/qwenstorm-3.0.0/bench/results.jsonl`). Four configurations served
Qwen2.5-Coder-14B through llama.cpp with different slot counts, cache types and
context windows; the fifth served `gpt-oss:20b` through Ollama.

The record shows two things ([Fig. 25](#fig:bench-hosts)). For every llama.cpp
configuration, generation speed fell as the context grew across the session, from
about 11 tokens per second on the first turn to between 6 and 9 on the tenth, and the
four configurations finished the session within 212 to 221 s of each other's wall
time. The Ollama configuration finished the same session in 86 s, and the same
`gpt-oss:20b` model served by llama.cpp at a 64k context did not load at all. The
record does not separate the model from the serving stack, so the difference is
reported and not explained.

<!-- BEGIN GENERATED figure:bench-hosts rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.8cm},vibeyaxis,width=8.6cm,height=4.8cm,
  xmin=0.5,xmax=10.5,xtick={1,...,10},xlabel={turn of a ten-turn session}]
\nextgroupplot[title={a. Generation speed as the context grows},ylabel={tokens / s},ymin=0,legend pos=south west]
\addplot[vibeyblue,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.2) (2,9.8) (3,9.3) (4,9.6) (5,9.4) (6,9.5) (7,7.6) (8,9.0) (9,8.8) (10,8.4)};
\addlegendentry{A-baseline}
\addplot[vibeyteal,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.2) (2,10.5) (3,10.0) (4,8.8) (5,9.4) (6,9.1) (7,8.0) (8,7.7) (9,6.9) (10,6.2)};
\addlegendentry{B-1slot-q8-48k}
\addplot[vibeygold,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.1) (2,10.8) (3,9.9) (4,9.4) (5,8.7) (6,8.1) (7,7.4) (8,7.5) (9,8.5) (10,7.9)};
\addlegendentry{C-1slot-q8-48k-draft}
\addplot[vibeyviolet,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.3) (2,10.4) (3,10.3) (4,10.1) (5,9.8) (6,8.0) (7,9.2) (8,8.3) (9,7.5) (10,8.5)};
\addlegendentry{D-1slot-f16-32k}
\nextgroupplot[title={b. Wall time per turn},ylabel={seconds},ymin=0,legend pos=north west]
\addplot[vibeyblue,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.44) (2,17.22) (3,18.32) (4,19.09) (5,22.51) (6,23.45) (7,26.94) (8,23.22) (9,25.76) (10,27.07)};
\addlegendentry{A-baseline}
\addplot[vibeyteal,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.63) (2,15.81) (3,17.54) (4,19.0) (5,20.66) (6,23.4) (7,26.1) (8,24.77) (9,29.29) (10,32.29)};
\addlegendentry{B-1slot-q8-48k}
\addplot[vibeygold,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.65) (2,15.3) (3,17.47) (4,18.63) (5,21.39) (6,25.27) (7,26.71) (8,25.26) (9,26.03) (10,27.83)};
\addlegendentry{C-1slot-q8-48k-draft}
\addplot[vibeyviolet,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,11.41) (2,16.36) (3,17.7) (4,18.06) (5,20.31) (6,25.87) (7,24.37) (8,23.61) (9,27.42) (10,27.09)};
\addlegendentry{D-1slot-f16-32k}
\addplot[vibeyred,line width=.9pt,mark=*,mark size=1.1pt] coordinates {(1,8.89) (2,9.64) (3,8.46) (4,6.78) (5,8.43) (6,7.9) (7,8.44) (8,8.03) (9,10.48) (10,8.56)};
\addlegendentry{E-gptoss-20b-ollama}
\end{groupplot}
\node[vibeynote,anchor=north west,align=left] at ([yshift=-0.85cm]group c1r1.south west)
  {whole session: A-baseline: 215\,s; B-1slot-q8-48k: 220\,s; C-1slot-q8-48k-draft: 216\,s; D-1slot-f16-32k: 212\,s; E-gptoss-20b-ollama: 86\,s. E-gptoss-20b-64k: server exited during load, bench failed};
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
again as headroom, wires 1.3 GB less, and generated 16% faster. That is sub-doctrine
8.j, fitted to the iron: a setting moves against a number read from this host, and
the number is recorded beside it.

<!-- BEGIN GENERATED figure:host-context rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\shade[left color=vibeyblue!18,right color=vibeyblue!4] (0,-0.12) rectangle (7.0,0.12);
\draw[vibeyink,line width=.6pt] (0,0) -- (7.0,0);
\draw[vibeyink] (0.00,0) -- (0.00,-0.08); \draw[vibeyink] (0.88,0) -- (0.88,-0.08); \draw[vibeyink] (1.75,0) -- (1.75,-0.08); \draw[vibeyink] (2.62,0) -- (2.62,-0.08); \draw[vibeyink] (3.50,0) -- (3.50,-0.08); \draw[vibeyink] (4.38,0) -- (4.38,-0.08); \draw[vibeyink] (5.25,0) -- (5.25,-0.08); \draw[vibeyink] (6.12,0) -- (6.12,-0.08); \draw[vibeyink] (7.00,0) -- (7.00,-0.08);
\node[vibeynote,anchor=north] at (0,-0.1) {0};
\node[vibeynote,anchor=north east] at (7.0,-0.1) {131,072 tokens};
\draw[vibeyink,line width=.6pt] (1.07,0.12) -- (1.07,0.55) node[vibeynote,anchor=south,text=vibeyink] {p50\\20,070};
\draw[vibeyink,line width=.6pt] (1.71,0.12) -- (1.71,0.87) node[vibeynote,anchor=south,text=vibeyink] {p90\\32,026};
\draw[vibeyink,line width=.6pt] (1.97,0.12) -- (1.97,0.55) node[vibeynote,anchor=south,text=vibeyink] {p95\\36,816};
\draw[vibeyink,line width=.6pt] (2.30,0.12) -- (2.30,0.87) node[vibeynote,anchor=south,text=vibeyink] {p99\\42,979};
\draw[vibeyink,line width=.6pt] (2.62,0.12) -- (2.62,0.55) node[vibeynote,anchor=south,text=vibeyink] {max\\49,118};
\draw[vibeyred,line width=.8pt,densely dashed] (1.75,-0.15) -- (1.75,-0.60) node[vibeynote,anchor=north,text=vibeyred,align=center] {32k: truncates 71 turns};
\draw[vibeygreen,line width=.8pt,densely dashed] (3.50,-0.15) -- (3.50,-0.98) node[vibeynote,anchor=north,text=vibeygreen,align=center] {64k: chosen, 16,418 headroom};
\draw[vibeygray,line width=.8pt,densely dashed] (7.00,-0.15) -- (7.00,-0.60) node[vibeynote,anchor=north,text=vibeygray,align=center] {128k: baseline, never reached};
\node[vibeypill,anchor=south] at (7.00,1.35) {A: 18.55\,GB wired, 28.0 tok/s};
\node[vibeypill,anchor=south] at (3.50,1.63) {B: 17.25\,GB wired, 32.5 tok/s};
\node[vibeypill,anchor=south] at (3.50,1.35) {C: 17.24\,GB wired, 30.9 tok/s, inconclusive};
\node[vibeyhead,anchor=south west] at (0,1.95) {context actually used per turn, 838 storm turns};
\end{tikzpicture}
\caption{Fitting the model to the iron. The percentiles mark how much context 838 real storm turns used; the dashed lines are the three context windows considered. A 32k window would have truncated 71 turns, and the 128k baseline, never reached by any turn, wired 18.55\,GB of a 24\,GB machine. The 64k window chosen covers every recorded turn with a third again as headroom, and the sweep's pills report what each setting cost and delivered.}
\label{fig:host-context}
\end{figure}
```
<!-- END GENERATED figure:host-context -->

### Field data

The git history is field data: nothing in it was held fixed. At revision `842db09d2e61`,
1,356 commits are reachable across nine root histories, the absorbed histories of the
family's packages. Since 2026-08-09, when the family's own development begins, 1,344
commits landed on 33 active days, between 1 and 191 per day (median 27, mean 40.7,
sample standard deviation 40.6). Commits landed in all 24 hours of the day in US
Eastern time, with the fewest (19) in the 09:00 hour and the most (90) in the 18:00
hour. The longest
pause was nine days with no commit, from 2026-08-30 to 2026-09-09, and nothing in the
repository records its cause. Seventeen `vibey` release tags point at commits dated
between 2026-08-16 and 2026-09-21, and 569 commit subjects across the absorbed
histories end in a pull-request reference.

The daily rate's spread is 100% of its mean, against 24% in the controlled region.
That is what the model predicts when the coordinates of $d$ vary freely, but it is
also what almost any model would predict of an uncontrolled process, so the history
does not test the regularity. We report it so that the controlled band is never
mistaken for a field rate.

The daily cadence and release events are tracked in [Fig. 27](#fig:commits-daily).

<!-- BEGIN GENERATED figure:commits-daily rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=17.2cm,height=5.6cm,ybar,bar width=4.2pt,xmin=-0.7,xmax=45.7,ymin=0,ymax=231,
  xtick={0,7,14,21,28,35,42},xticklabels={Aug 9,Aug 16,Aug 23,Aug 30,Sep 6,Sep 13,Sep 20},xlabel={day (2026, 842db09d and earlier)},ylabel={commits}]
\addplot[fill=vibeyblue,draw=none] coordinates {(0,5) (1,41) (3,21) (4,130) (5,27) (6,92) (7,47) (8,22) (9,39) (10,20) (11,52) (12,75) (13,13) (14,61) (15,1) (16,38) (17,3) (18,56) (19,29) (20,91) (21,71) (31,3) (32,13) (36,24) (37,61) (38,33) (39,16) (40,191) (41,7) (42,4) (43,8) (44,23) (45,27)};
\node[vibeyanchor,fill=vibeygold] at (axis cs:7,53) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:7,56) {v0.1.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:11,58) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:11,61) {v0.1.1, v0.1.2};
\node[vibeyanchor,fill=vibeygold] at (axis cs:15,7) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:15,10) {v0.2.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:20,97) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:20,100) {v0.3.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:21,77) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:21,80) {v0.4.0, v0.5.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:36,30) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:36,33) {v0.6.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:37,67) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:37,70) {v0.7.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:38,39) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:38,42) {v0.8.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:40,197) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:40,200) {v1.0.0, v1.1.0, v1.2.0, v1.3.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:41,13) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:41,16) {v1.4.0, v1.5.0};
\node[vibeyanchor,fill=vibeygold] at (axis cs:43,14) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=60,anchor=south west,inner sep=1pt] at (axis cs:43,17) {v2.0.0};
\draw[decorate,decoration={brace,amplitude=3pt},vibeygray] (axis cs:22,6) -- (axis cs:30,6);
\node[vibeynote,anchor=south] at (axis cs:26.0,10) {9 days without a commit};
\node[vibeycallout,anchor=east] at (axis cs:39.4,185) {191 on Sep 18};
\node[vibeynote,anchor=north west,align=left] at (axis description cs:0.01,0.97) {\textcolor{vibeygold}{$\bullet$} vibey release tag};
\end{axis}
\end{tikzpicture}
\caption{Commits per day since 2026-08-09, when the family's own development begins, read at revision 842db09d: 1,344 commits on 33 active days, with the busiest day at 191. Gold marks are the 17 \texttt{vibey} release tags in the window; the brace marks the longest pause.}
\label{fig:commits-daily}
\end{figure*}
```
<!-- END GENERATED figure:commits-daily -->

The circadian rhythm, weekday distribution, and Conventional Commit types are captured in [Fig. 28](#fig:commit-rhythm).

<!-- BEGIN GENERATED figure:commit-rhythm rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{scope}[xshift=-5.4cm]
\draw[vibeyline] (0,0) circle (0.597); \draw[vibeyline] (0,0) circle (1.194); \draw[vibeyline] (0,0) circle (1.792);
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (90:1.218) arc[start angle=90,end angle=75,radius=1.218] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (75:1.194) arc[start angle=75,end angle=60,radius=1.194] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (60:1.983) arc[start angle=60,end angle=45,radius=1.983] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (45:1.314) arc[start angle=45,end angle=30,radius=1.314] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (30:1.792) arc[start angle=30,end angle=15,radius=1.792] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (15:0.860) arc[start angle=15,end angle=0,radius=0.860] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (0:0.908) arc[start angle=0,end angle=-15,radius=0.908] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-15:0.741) arc[start angle=-15,end angle=-30,radius=0.741] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-30:0.741) arc[start angle=-30,end angle=-45,radius=0.741] -- cycle;
\fill[vibeyred!70,draw=white,line width=.4pt] (0,0) -- (-45:0.454) arc[start angle=-45,end angle=-60,radius=0.454] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-60:1.242) arc[start angle=-60,end angle=-75,radius=1.242] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-75:1.218) arc[start angle=-75,end angle=-90,radius=1.218] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-90:1.409) arc[start angle=-90,end angle=-105,radius=1.409] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-105:1.744) arc[start angle=-105,end angle=-120,radius=1.744] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-120:1.887) arc[start angle=-120,end angle=-135,radius=1.887] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-135:1.792) arc[start angle=-135,end angle=-150,radius=1.792] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-150:0.956) arc[start angle=-150,end angle=-165,radius=0.956] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-165:1.839) arc[start angle=-165,end angle=-180,radius=1.839] -- cycle;
\fill[vibeygold,draw=white,line width=.4pt] (0,0) -- (-180:2.150) arc[start angle=-180,end angle=-195,radius=2.150] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-195:1.648) arc[start angle=-195,end angle=-210,radius=1.648] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-210:1.433) arc[start angle=-210,end angle=-225,radius=1.433] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-225:1.744) arc[start angle=-225,end angle=-240,radius=1.744] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-240:1.194) arc[start angle=-240,end angle=-255,radius=1.194] -- cycle;
\fill[vibeyblue!85,draw=white,line width=.4pt] (0,0) -- (-255:0.645) arc[start angle=-255,end angle=-270,radius=0.645] -- cycle;
\node[vibeynote,text=vibeygray] at (82.5:2.42) {0}; \node[vibeynote,text=vibeygray] at (37.5:2.42) {3}; \node[vibeynote,text=vibeygray] at (-7.5:2.42) {6}; \node[vibeynote,text=vibeygray] at (-52.5:2.42) {9}; \node[vibeynote,text=vibeygray] at (-97.5:2.42) {12}; \node[vibeynote,text=vibeygray] at (-142.5:2.42) {15}; \node[vibeynote,text=vibeygray] at (-187.5:2.42) {18}; \node[vibeynote,text=vibeygray] at (-232.5:2.42) {21};
\node[vibeynote,anchor=south west,text=vibeygray] at (-2.6,2.45) {commits by hour, US Eastern};
\node[vibeynote,anchor=north west,text=vibeygray,align=left] at (-2.6,-2.45) {rings at 25, 50, 75 commits\\\textcolor{vibeygold}{$\blacksquare$} busiest 18:00 (90) \; \textcolor{vibeyred!70}{$\blacksquare$} quietest 09:00 (19)};
\end{scope}
\begin{axis}[vibeybars,at={(0.0cm,-2.6cm)},anchor=south west,width=5.3cm,height=5.2cm,bar width=9pt,xmin=-0.6,xmax=6.6,ymin=0,
  xtick={0,...,6},xticklabels={Mon,Tue,Wed,Thu,Fri,Sat,Sun},title={commits by weekday},ylabel={commits}]
\addplot[fill=vibeyblue,draw=none] coordinates {(0,96) (1,161) (2,107) (3,267) (4,322) (5,203) (6,188)};
\end{axis}
\begin{axis}[vibeybars,at={(6.1cm,-2.6cm)},anchor=south west,width=5.3cm,height=5.2cm,bar width=9pt,xmin=-0.6,xmax=7.6,ymin=0,
  xtick={0,...,7},xticklabels={chore,other,fix,feat,docs,ci,test,refactor},x tick label style={rotate=45,anchor=north east,font=\sffamily\tiny},title={Conventional Commit types},ylabel={commits}]
\addplot[fill=vibeyteal!85,draw=none] coordinates {(0,378) (1,266) (2,246) (3,245) (4,125) (5,39) (6,25) (7,8)};
\end{axis}
\end{tikzpicture}
\caption{The rhythm of production since 2026-08-09, at revision 842db09d. Left, a 24-hour clock of commits in US Eastern time: every hour of the day carries commits, the busiest at 18:00 with 90 and the quietest at 09:00 with 19. Centre, the weekday distribution. Right, the Conventional Commit types the pre-commit hook enforces, most common first.}
\label{fig:commit-rhythm}
\end{figure*}
```
<!-- END GENERATED figure:commit-rhythm -->

Cumulative deliveries, including the absorbed package roots and pull requests, appear in [Fig. 29](#fig:cumulative-commits).

<!-- BEGIN GENERATED figure:cumulative-commits rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeyaxis,width=17.2cm,height=5.4cm,xmin=0,xmax=45,ymin=0,ymax=1424,
  xtick={0,7,14,21,28,35,42},xticklabels={Aug 9,Aug 16,Aug 23,Aug 30,Sep 6,Sep 13,Sep 20},xlabel={day},ylabel={cumulative},legend pos=north west]
\addplot[fill=vibeyblue!14,draw=vibeyblue,line width=1pt] coordinates {(0,0) (0,5) (1,46) (2,46) (3,67) (4,197) (5,224) (6,316) (7,363) (8,385) (9,424) (10,444) (11,496) (12,571) (13,584) (14,645) (15,646) (16,684) (17,687) (18,743) (19,772) (20,863) (21,934) (22,934) (23,934) (24,934) (25,934) (26,934) (27,934) (28,934) (29,934) (30,934) (31,937) (32,950) (33,950) (34,950) (35,950) (36,974) (37,1035) (38,1068) (39,1084) (40,1275) (41,1282) (42,1286) (43,1294) (44,1317) (45,1344)} \closedcycle;
\addlegendentry{commits since Aug 9 (1,344; 12 earlier)}
\addplot[vibeyteal,line width=1pt] coordinates {(0,0) (0,0) (1,7) (2,7) (3,9) (4,20) (5,20) (6,31) (7,47) (8,69) (9,104) (10,124) (11,145) (12,181) (13,188) (14,218) (15,218) (16,242) (17,244) (18,281) (19,304) (20,373) (21,426) (22,426) (23,426) (24,426) (25,426) (26,426) (27,426) (28,426) (29,426) (30,426) (31,426) (32,426) (33,426) (34,426) (35,426) (36,434) (37,451) (38,483) (39,494) (40,501) (41,505) (42,508) (43,515) (44,538) (45,565)};
\addlegendentry{commit subjects closing a pull request (565)}
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
\caption{Cumulative production at revision 842db09d: commits since 2026-08-09 and, beneath them, the commits whose subject closes a pull request. The violet marks on the baseline are the days on which the absorbed packages' own histories begin; the family was written as several repositories and merged into one tree with every history preserved.}
\label{fig:cumulative-commits}
\end{figure*}
```
<!-- END GENERATED figure:cumulative-commits -->

The timeline of releases across each package in the family is shown in [Fig. 30](#fig:release-cadence).

<!-- BEGIN GENERATED figure:release-cadence rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
\draw[vibeydashed] (8.07,-2.78) -- (8.07,0.35);\node[vibeynote,anchor=north] at (8.07,-2.80) {Sep 2026};
\node[vibeynote,anchor=north] at (0.00,-2.80) {Aug 10};
\node[vibeynote,anchor=north] at (15.40,-2.80) {Sep 21};
\draw[vibeyline,line width=.5pt] (0,0.00) -- (15.40,0.00);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,0.00) {vibey};
\node[vibeyanchor,fill=vibeyblue] at (2.20,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (2.22,0.06) {0.1.0};
\node[vibeyanchor,fill=vibeyblue] at (3.67,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (3.67,-0.09) {2};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (3.69,0.06) {0.1.1--0.1.2};
\node[vibeyanchor,fill=vibeyblue] at (5.13,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (5.15,0.06) {0.2.0};
\node[vibeyanchor,fill=vibeyblue] at (6.97,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (6.99,0.06) {0.3.0};
\node[vibeyanchor,fill=vibeyblue] at (7.33,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (7.33,-0.09) {2};
\draw[vibeyline] (7.33,0.06) -- (7.33,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (7.35,0.48) {0.4.0--0.5.0};
\node[vibeyanchor,fill=vibeyblue] at (12.83,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (12.85,0.06) {0.6.0};
\node[vibeyanchor,fill=vibeyblue] at (13.20,0.00) {};
\draw[vibeyline] (13.20,0.06) -- (13.20,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (13.22,0.48) {0.7.0};
\node[vibeyanchor,fill=vibeyblue] at (13.57,0.00) {};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (13.59,0.06) {0.8.0};
\node[vibeyanchor,fill=vibeyblue] at (14.30,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (14.30,-0.09) {4};
\draw[vibeyline] (14.30,0.06) -- (14.30,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (14.32,0.48) {1.0.0--1.3.0};
\node[vibeyanchor,fill=vibeyblue] at (14.67,0.00) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyblue,circle,inner sep=.6pt,anchor=north] at (14.67,-0.09) {2};
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (14.69,0.06) {1.4.0--1.5.0};
\node[vibeyanchor,fill=vibeyblue] at (15.40,0.00) {};
\draw[vibeyline] (15.40,0.06) -- (15.40,0.48);
\node[font=\sffamily\tiny,text=vibeyblue,rotate=55,anchor=south west,inner sep=1pt] at (15.42,0.48) {2.0.0};
\draw[vibeyline,line width=.5pt] (0,-0.62) -- (15.40,-0.62);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,-0.62) {claudeloop};
\node[vibeyanchor,fill=vibeyteal] at (0.00,-0.62) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyteal,circle,inner sep=.6pt,anchor=north] at (0.00,-0.71) {5};
\node[font=\sffamily\tiny,text=vibeyteal,rotate=55,anchor=south west,inner sep=1pt] at (0.02,-0.56) {0.2.0--0.4.0};
\node[vibeyanchor,fill=vibeyteal] at (0.73,-0.62) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyteal,circle,inner sep=.6pt,anchor=north] at (0.73,-0.71) {4};
\draw[vibeyline] (0.73,-0.56) -- (0.73,-0.14);
\node[font=\sffamily\tiny,text=vibeyteal,rotate=55,anchor=south west,inner sep=1pt] at (0.75,-0.14) {0.5.0--0.5.3};
\node[vibeyanchor,fill=vibeyteal] at (1.10,-0.62) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyteal,circle,inner sep=.6pt,anchor=north] at (1.10,-0.71) {2};
\node[font=\sffamily\tiny,text=vibeyteal,rotate=55,anchor=south west,inner sep=1pt] at (1.12,-0.56) {0.5.4--0.5.5};
\node[vibeyanchor,fill=vibeyteal] at (3.67,-0.62) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeyteal,circle,inner sep=.6pt,anchor=north] at (3.67,-0.71) {2};
\node[font=\sffamily\tiny,text=vibeyteal,rotate=55,anchor=south west,inner sep=1pt] at (3.69,-0.56) {0.6.0--0.6.1};
\draw[vibeyline,line width=.5pt] (0,-1.24) -- (15.40,-1.24);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,-1.24) {agyloop};
\node[vibeyanchor,fill=vibeyviolet] at (2.20,-1.24) {};
\node[font=\sffamily\tiny,text=vibeyviolet,rotate=55,anchor=south west,inner sep=1pt] at (2.22,-1.18) {0.4.0};
\node[vibeyanchor,fill=vibeyviolet] at (3.67,-1.24) {};
\node[font=\sffamily\tiny,text=vibeyviolet,rotate=55,anchor=south west,inner sep=1pt] at (3.69,-1.18) {0.4.1};
\draw[vibeyline,line width=.5pt] (0,-1.86) -- (15.40,-1.86);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,-1.86) {cursorloop};
\node[vibeyanchor,fill=vibeymint] at (3.67,-1.86) {};
\node[font=\sffamily\tiny,text=vibeymint,rotate=55,anchor=south west,inner sep=1pt] at (3.69,-1.80) {0.6.0};
\draw[vibeyline,line width=.5pt] (0,-2.48) -- (15.40,-2.48);
\node[font=\sffamily\tiny\bfseries,anchor=east,text=vibeyink] at (-0.15,-2.48) {codexloop};
\node[vibeyanchor,fill=vibeygold] at (1.10,-2.48) {};
\node[font=\sffamily\tiny\bfseries,text=white,fill=vibeygold,circle,inner sep=.6pt,anchor=north] at (1.10,-2.57) {2};
\node[font=\sffamily\tiny,text=vibeygold,rotate=55,anchor=south west,inner sep=1pt] at (1.12,-2.42) {0.1.0--0.2.0};
\node[vibeyanchor,fill=vibeygold] at (2.20,-2.48) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=55,anchor=south west,inner sep=1pt] at (2.22,-2.42) {0.3.0};
\node[vibeyanchor,fill=vibeygold] at (3.67,-2.48) {};
\node[font=\sffamily\tiny,text=vibeygold,rotate=55,anchor=south west,inner sep=1pt] at (3.69,-2.42) {0.3.1};
\end{tikzpicture}
\caption{Every release tag reachable at revision 842db09d, one lane per package: 17 for vibey, 13 for claudeloop, 4 for codexloop, 2 for agyloop, 1 for cursorloop. The 17 \texttt{vibey} releases run from vibey-v0.1.0 on 2026-08-16 to vibey-v2.0.0 on 2026-09-21; since the packages were absorbed into one tree, one version number ships the whole family.}
\label{fig:release-cadence}
\end{figure*}
```
<!-- END GENERATED figure:release-cadence -->

Finally, the architectural shape of the consolidated repository across its 11 packages and layers is depicted in [Fig. 31](#fig:codebase-shape).

<!-- BEGIN GENERATED figure:codebase-shape rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=3 by 1,horizontal sep=1.9cm},vibeyaxis,height=5.6cm,
  y dir=reverse,ytick={0,...,10},ymin=-0.7,ymax=10.7,xmin=0,y tick label style={font=\sffamily\tiny},
  scaled x ticks=false,x tick label style={/pgf/number format/fixed,/pgf/number format/1000 sep={{,}}},point meta=x,
  nodes near coords,every node near coord/.append style={font=\sffamily\tiny,text=vibeygray,/pgf/number format/fixed,/pgf/number format/1000 sep={{,}}}]
\nextgroupplot[title={a. Lines of Python per package},xbar,bar width=6pt,width=5.9cm,yticklabels={vibey-gh,vibey,claudeloop,vibey-bootstrap,agyloop,codexloop,cursorloop,qwenloop,vibey-skills,opencodeloop,runners-common},xlabel={lines}]
\addplot[fill=vibeyblue,draw=none] coordinates {(52772,0) (38228,1) (36869,2) (32732,3) (23972,4) (22614,5) (16750,6) (6911,7) (2934,8) (1379,9) (258,10)};
\nextgroupplot[title={b. Test functions per package},xbar,bar width=6pt,width=4.9cm,yticklabels={,,,,,,,,,,,},xlabel={tests}]
\addplot[fill=vibeyteal!85,draw=none] coordinates {(1420,0) (0,1) (1478,2) (971,3) (678,4) (711,5) (562,6) (189,7) (30,8) (43,9) (0,10)};
\nextgroupplot[title={c. The orchestrator's layers},xbar,bar width=6pt,width=4.9cm,ytick={0,...,4},yticklabels={domain,application,infrastructure,cli,tui},ymin=-0.7,ymax=4.7,xlabel={lines},xmax=29062,nodes near coords={}]
\addplot[fill=vibeyviolet!85,draw=none] coordinates {(8341,0) (10276,1) (15296,2) (2677,3) (590,4)};
\node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:9241,0) {8,341 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:11176,1) {10,276 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:16196,2) {15,296 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeygreen!15,text=vibeygreen!60!black] at (axis cs:3577,3) {2,677 $\cdot$ 100\% branch floor}; \node[vibeypill,anchor=west,fill=vibeysilver!30,text=vibeygray] at (axis cs:1490,4) {590 $\cdot$ exempt};
\end{groupplot}
\end{tikzpicture}
\caption{The shape of the tree at revision 842db09d: 297,124 lines of Python in 1,916 files and 8,483 test functions. (a) Lines per package; (b) test functions per package, with 2,401 more in the orchestrator's own top-level suite; (c) the orchestrator's layers, four of which fail the build below 100\% branch coverage.}
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
design: six engines implement one contract, the scheduler chooses among them by
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
  \node[vibeynote,anchor=south east] at (8.75,0.5)
    {links $\mathcal{C}_{ij}$: coordination is a coupling,\\not a seventh material};

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

<!-- BEGIN GENERATED figure:completion-band rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
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

<!-- BEGIN GENERATED figure:forecast rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}
\begin{groupplot}[group style={group size=2 by 1,horizontal sep=1.7cm},vibeyaxis,width=7.9cm,height=4.6cm,
  xmin=0.5,xmax=7.5,xtick={1,2,3,4,5,6,7},xticklabels={Sep 19,Sep 19,Sep 19,Sep 20,Sep 21,Sep 23,Sep 23},x tick label style={rotate=30,anchor=north east},xlabel={forecast record}]
\nextgroupplot[title={a. Work units in the tracker},ylabel={units},ymin=0,ymax=885,legend pos=north west]
\addplot[vibeyred,line width=1pt,mark=*,mark size=1.3pt] coordinates {(1,0) (2,24) (3,24) (4,24) (5,25) (6,708) (7,706)};
\addlegendentry{remaining}
\addplot[vibeygreen,line width=1pt,mark=square*,mark size=1.2pt] coordinates {(1,235) (2,235) (3,235) (4,238) (5,247) (6,264) (7,279)};
\addlegendentry{completed}
\nextgroupplot[title={b. Forecast active days to completion},ylabel={active days},ymin=0,legend pos=north west]
\addplot[fill=vibeyblue!14,draw=none,forget plot] coordinates {(1,0.00) (2,1.94) (3,1.94) (4,1.92) (5,2.13) (6,59.00) (7,58.20) (7,70.60) (6,78.67) (5,3.12) (4,3.00) (3,3.00) (2,3.00) (1,0.00)} -- cycle;
\addplot[vibeyblue,line width=1pt,mark=*,mark size=1.2pt] coordinates {(1,0.00) (2,1.94) (3,1.94) (4,1.92) (5,2.13) (6,59.00) (7,58.20)};
\addlegendentry{$W/r_{\max}$}
\addplot[vibeyblue!60,line width=1pt,mark=o,mark size=1.2pt] coordinates {(1,0.00) (2,3.00) (3,3.00) (4,3.00) (5,3.12) (6,78.67) (7,70.60)};
\addlegendentry{$W/r_{\min}$}
\end{groupplot}
\end{tikzpicture}
\caption{The delivery-estimate ledger, one forecast per record. (a) Remaining and completed work units as the tracker held them: remaining jumped from 25 to 708 when the storm filed its lanes as issues. (b) The zero-shortfall time to completion the forecast derives from the observed merge rate, 58--71 active days at the last record, with every material coordinate unmeasured and so at $\phi_i = 1$.}
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

<!-- BEGIN GENERATED figure:governance-time rev:842db09d2e619ffe9b6f1bbc753dd7686d02ce0e — regenerated by scripts/paper_figures.py -->
```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}
\begin{axis}[vibeybars,width=8.6cm,height=4.8cm,bar width=11pt,xmin=-0.6,xmax=3.6,ymin=0,ymax=1836,
  xtick={0,1,2,3},xticklabels={four gates before,four gates after,suite before,suite after},
  x tick label style={font=\sffamily\tiny,align=center,text width=1.6cm},ylabel={seconds},
  nodes near coords,every node near coord/.append style={font=\sffamily\tiny,text=vibeygray}]
\addplot[fill=vibeyred!70,draw=none] coordinates {(0,1530)};
\addplot[fill=vibeygreen!80,draw=none] coordinates {(1,136)};
\addplot[fill=vibeyred!70,draw=none] coordinates {(2,383)};
\addplot[fill=vibeygreen!80,draw=none] coordinates {(3,135)};
\node[vibeycallout,anchor=south] at (axis cs:1,274) {$11.3\times$ faster};
\node[vibeycallout,anchor=south] at (axis cs:3,273) {$2.8\times$ faster};
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
and report the Qwen pilot only as a bounded reliability observation.

```latex
\begin{plainwords}
We pushed one small computer harder and harder, giving it 1, 2, 4, 8 and finally 128 jobs at once. Up to 32 jobs, almost everything finished, and the computer produced about one or two finished pieces of work every minute no matter how many we asked for at once. Past that, jobs began to run out of time, and at 128 most of them failed. The computer was never broken; it was full. Only a person could decide what to do next: ask for less, allow more time, or buy a bigger computer. That is why we say the machine part is cheap and the deciding part is the hard part.
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
engines rest today on a scripted-binary conformance suite that asserts each runner's
flags, run-directory shape, event vocabulary, capacity mapping and completion marker
against the installed binary; they are not yet reported here. The production-rate
claims are validated separately, by the stress record and the evidence script above;
the local Qwen pilot is reported as an operational reliability observation with its
own cutoff and does not enlarge the throughput claim.

```latex
\begin{plainwords}
We check the system three ways. Tests that walk every branch of the important code. A chaos test where helpers crash on purpose while a real database is running, to prove that no job is lost and no job is done twice. And a live run of a whole project on two different robot helpers, including a forced switch from one to the other in the middle.
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
treats as a coupling is the one Brooks described for human teams.

## Conclusion

Putting the ledger, not the session, at the center makes autonomous delivery
survivable and auditable: engines become fungible, crashes become replays, and
human authority is a structural property of the state machine rather than a
prompt-engineering hope. The same discipline, binding every claim to the state it
describes, governs the runners beneath the orchestrator and the release calculus above
it. In the project's controlled record, production kept to a band set by its
substrate, and the inputs that stopped work were decisions and judgments. The
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
- The vibey repository: the sovereignty stress record, `src/vibey_tools/gh/docs/sovereignty-stress-2026-08-30.md`; the evidence script, `scripts/paper_evidence.py`; the architecture decision records, `docs/architecture/decisions/`; `https://github.com/the-vibey-project/vibey`, 2026.

## A call to FOSS developers

Everything in this paper is free and open-source software, built in the open, and it
is not finished. The machines that write code are cheap now; what is scarce is
infrastructure a person can own, governance that holds up when nobody is watching, and
evidence honest enough to publish. If you write software and any of that speaks to
you, come and build it with us.

- Join the conversation on Discord: [discord.gg/Qvu8aYnVS](https://discord.gg/Qvu8aYnVS).
- Read how to join me and what to work on first: [vibewithadam.matthewsteinberger.com/join-me](https://vibewithadam.matthewsteinberger.com/join-me).

Bring your questions, your critiques and your pull requests. Whether you care about
queues and ledgers, sovereign local models, reproducible benchmarks, or the young field
of Biodigitology, there is a lane for you.
