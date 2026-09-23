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
by `scripts/paper_evidence.py`. The conceptual visual atlas is authored as
deterministic TikZ in this source, so the PDF, its labels and its operational diagrams
are reviewable and reproducible rather than screenshots detached from the model.

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
own paper. This paper consolidates them. Its contributions are:

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
explicit operator override. A handoff that fails the gate is therefore a retry, an
escalation, or a human decision, never a silent partial.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=2.2cm] (intent) at (-5.1,0.8)
    {specification\\or finding};
  \node[vibeycore,minimum width=2.2cm] (ledger) at (-2.25,0.8)
    {append-only\\ledger};
  \node[vibeysoft,minimum width=2.2cm] (queue) at (0.6,0.8)
    {queue + lease\\SKIP LOCKED};
  \node[vibeysoft,minimum width=2.2cm] (engine) at (3.45,0.8)
    {engine\\turns};
  \node[vibeybox,minimum width=2.2cm] (brief) at (-0.8,-1.15)
    {handoff brief\\digest + open sets};
  \node[vibeywarn,minimum width=2.2cm] (gate) at (2.05,-1.15)
    {no-loss gate\\R1--R10};
  \node[vibeycore,minimum width=2.2cm] (successor) at (4.85,-1.15)
    {successor\\or human gate};
  \draw[vibeyarrow] (intent) -- (ledger);
  \draw[vibeyarrow] (ledger) -- (queue);
  \draw[vibeyarrow] (queue) -- (engine);
  \draw[vibeyarrow] (engine.south) -- (brief.north);
  \draw[vibeyarrow] (brief) -- (gate);
  \draw[vibeyarrow] (gate) -- (successor);
  \draw[vibeydashed,-{Latex[length=2mm]}] (gate.north) -- ++(0,0.9) -| (ledger.south);
  \node[font=\tiny,align=center,text=vibeygray] at (-3.65,-0.05)
    {record before\\effect};
  \node[font=\tiny,align=center,text=vibeyred] at (3.45,-2.0)
    {failure = retry, escalation, or park\\never silent loss};
\end{tikzpicture}
\caption{The append-before-act path. Durable intent enters the ledger before the
queue, engine, handoff or delivery effect; the no-loss gate checks completeness and
the digest before a successor may act.}
\label{fig:ledger-handoff}
\end{figure*}
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

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=1.65cm] (design) at (-5.2,0) {DESIGN\\human gate};
  \node[vibeybox,minimum width=1.65cm] (visual) at (-3.1,0) {VISUAL\\DESIGN\\optional};
  \node[vibeysoft,minimum width=1.65cm] (build) at (-0.9,0) {BUILD\\unattended};
  \node[vibeybox,minimum width=1.65cm] (review) at (1.3,0) {REVIEW\\human gate};
  \node[vibeybox,minimum width=1.65cm] (deployd) at (3.45,0) {DEPLOY\\DESIGN};
  \node[vibeysoft,minimum width=1.65cm] (deployx) at (5.6,0) {DEPLOY\\EXECUTE};
  \node[vibeycore,minimum width=1.65cm] (done) at (3.45,-1.45) {DEPLOY\\REVIEW / DONE};
  \draw[vibeyarrow] (design) -- (visual);
  \draw[vibeyarrow] (visual) -- (build);
  \draw[vibeyarrow] (build) -- (review);
  \draw[vibeyarrow] (review) -- (deployd);
  \draw[vibeyarrow] (deployd) -- (deployx);
  \draw[vibeyarrow] (deployx) -- (done);
  \draw[vibeyarrow] (review.south) -- ++(0,-0.65) -| (done.west);
  \node[font=\tiny,align=center,text=vibeygray] at (-4.15,-1.15)
    {acceptance\\criteria};
  \node[font=\tiny,align=center,text=vibeygray] at (0.2,-1.15)
    {leases +\\ledger};
  \node[font=\tiny,align=center,text=vibeygray] at (2.25,0.85)
    {consent\\required};
  \node[vibeywarn,minimum width=2.2cm] at (-0.9,-1.45)
    {open findings\\loop back};
  \draw[vibeydashed,-{Latex[length=2mm]}] (review.south) -- (build.south);
\end{tikzpicture}
\caption{The six-phase delivery machine. DESIGN, REVIEW, DEPLOY-DESIGN and
DEPLOY-REVIEW are human-gated; BUILD and DEPLOY-EXECUTE remain unattended, and
open findings route back rather than disappearing into a transcript.}
\label{fig:six-phase-machine}
\end{figure*}
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
not a physical claim or a substitute for evidence.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \draw[draw=vibeyblue!70,thick] (0,0) ellipse (6.15 and 2.65);
  \draw[draw=vibeyteal!75,thick] (0,0) ellipse (5.05 and 2.15);
  \draw[draw=vibeygreen!80,thick] (0,0) ellipse (3.85 and 1.62);
  \draw[draw=vibeygold!85,thick] (0,0) ellipse (2.65 and 1.08);
  \node[font=\scriptsize\bfseries,text=vibeyblue] at (-4.35,2.15) {project vision};
  \node[font=\scriptsize\bfseries,text=vibeyteal] at (3.35,1.78) {phase / milestone};
  \node[font=\scriptsize\bfseries,text=vibeygreen] at (-2.65,1.30) {feature set / epic};
  \node[font=\scriptsize\bfseries,text=vibeygold] at (2.05,0.78) {feature / unit / story};
  \filldraw[draw=vibeyink,fill=vibeyink] (0,0) circle (0.86);
  \node[align=center,text=white,font=\scriptsize\bfseries] at (0,0)
    {CORE\\software};
  \draw[vibeyarrow] (3.4,-2.05) arc[start angle=-32,end angle=32,x radius=3.4,y radius=2.05];
  \node[align=center,font=\scriptsize,text=vibeyink] at (4.8,-1.15)
    {CDD pulls every\\scope toward\\lower unresolved work};
\end{tikzpicture}
\caption{Convergence-Driven Development as nested digital orbitals. The nucleus is
the confirmed working core; the four orbitals are active scopes whose direction is
measured independently and whose energy is the unresolved-work distance.}
\label{fig:cdd-orbits}
\end{figure*}
```

The orbit metaphor is a control surface, not decoration: each scope can move in a
different direction, and an apparently healthy inner orbit cannot conceal a
diverging outer one. The smallest useful report therefore names the current
distance, evidence and next reconvergence move at every level.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=2.25cm] (ground) at (-4.8,0.65)
    {ground in\\actual repository};
  \node[vibeybox,minimum width=2.25cm] (map) at (-1.6,0.65)
    {map criteria\\to code and tests};
  \node[vibeybox,minimum width=2.25cm] (build) at (1.6,0.65)
    {implement\\smallest slice};
  \node[vibeybox,minimum width=2.25cm] (check) at (4.8,0.65)
    {run gates,\\inspect diff};
  \draw[vibeyarrow] (ground) -- (map);
  \draw[vibeyarrow] (map) -- (build);
  \draw[vibeyarrow] (build) -- (check);
  \draw[vibeyarrow] (check.south) -- ++(0,-0.55) -| (ground.south);
  \node[vibeycore,minimum width=2.25cm] (deliver) at (1.6,-1.35)
    {commit, review,\\publish evidence};
  \draw[vibeyarrow] (check.south) -- (deliver.north);
  \node[vibeywarn,minimum width=2.8cm] (diverge) at (-2.0,-1.35)
    {DIVERGENCE?\\bound it or scrap it};
  \draw[vibeydashed,-{Latex[length=2mm]}] (check.south) -- (diverge.north);
  \draw[vibeyarrow] (diverge.west) |- (map.south);
  \node[font=\tiny\bfseries,text=vibeyred,align=center] at (4.55,-1.35)
    {evidence\\beats activity};
\end{tikzpicture}
\caption{The CDD control loop. Discovery is allowed to be temporarily neutral or
slightly divergent only when its bound and reconvergence step are explicit; an
unbounded divergence is discarded and the work returns to the last sound state.}
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
evidence remains an atom with active orbitals and must continue the loop.

```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \draw[draw=vibeyblue!70,thick] (0,0) ellipse (2.25 and 1.55);
  \draw[draw=vibeyteal!75,thick] (0,0) ellipse (1.65 and 1.12);
  \draw[draw=vibeygreen!80,thick] (0,0) ellipse (1.05 and 0.72);
  \filldraw[draw=vibeyink,fill=vibeyink] (0,0) circle (0.52);
  \node[align=center,text=white,font=\tiny\bfseries] at (0,0) {core\\software};
  \node[font=\tiny,text=vibeyblue,align=center] at (0,1.37) {vision\\orbital};
  \node[font=\tiny,text=vibeyteal,align=center] at (1.58,0.85) {milestone\\orbital};
  \node[font=\tiny,text=vibeygreen,align=center] at (-1.45,-0.78) {epic /\\story orbital};
  \node[vibeybox,anchor=west,minimum width=2.0cm] at (2.35,0.72)
    {digital labels:};
  \node[align=left,font=\tiny,anchor=north west] at (2.48,0.36)
    {confirmed core\\open criteria\\tests and gates\\delivery evidence};
  \draw[vibeyarrow] (2.2,0.15) -- (0.50,0.12);
\end{tikzpicture}
\caption{A project atom in the digital realm. The nucleus is the high-quality,
confirmed core; active orbitals are the maintained scopes still seeking evidence,
integration and delivery.}
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
a bounded reconvergence path or the composition is abandoned.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \draw[vibeydashed] (-5.7,-2.05) rectangle (5.7,2.05);
  \node[font=\scriptsize\bfseries,text=vibeyink] at (-4.6,1.72) {software molecule};
  \node[vibeysoft,circle,minimum size=1.25cm] (a) at (-3.55,0.35) {project\\A};
  \node[vibeysoft,circle,minimum size=1.25cm] (b) at (0,0.95) {project\\B};
  \node[vibeysoft,circle,minimum size=1.25cm] (c) at (3.55,0.35) {project\\C};
  \draw[vibeyarrow] (a) -- (b) node[midway,above,sloped,font=\tiny] {API contract};
  \draw[vibeyarrow] (b) -- (c) node[midway,above,sloped,font=\tiny] {release timing};
  \draw[vibeyarrow] (a) -- (c) node[midway,below,sloped,font=\tiny] {security boundary};
  \node[vibeycore,minimum width=3.7cm] (emerge) at (0,-1.15)
    {emergent properties\\not present in one atom};
  \draw[vibeyarrow] (a.south) -- (emerge.west);
  \draw[vibeyarrow] (b.south) -- (emerge.north);
  \draw[vibeyarrow] (c.south) -- (emerge.east);
  \node[vibeywarn,minimum width=2.5cm] at (-3.5,-1.28)
    {data ownership\\can diverge};
  \node[vibeybox,minimum width=2.6cm] at (3.55,-1.28)
    {composition check\\must reconverge};
\end{tikzpicture}
\caption{A software molecule is a connected composition of project atoms. Bonds
represent interaction contracts; the molecule has properties such as composability,
security and release coherence that are not the sum of the atoms.}
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

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=2.25cm] (story) at (-5.2,0)
    {feature / unit / story\\one acceptance slice};
  \node[vibeysoft,minimum width=2.25cm] (atom) at (-2.6,0)
    {project atom\\nucleus + orbitals};
  \node[vibeysoft,minimum width=2.25cm] (molecule) at (0,0)
    {product molecule\\interacting atoms};
  \node[vibeysoft,minimum width=2.25cm] (organism) at (2.6,0)
    {software organism\\suite of suites};
  \node[vibeycore,minimum width=2.25cm] (ecology) at (5.2,0)
    {digital ecology\\Web-scale field};
  \draw[vibeyarrow] (story) -- (atom);
  \draw[vibeyarrow] (atom) -- (molecule);
  \draw[vibeyarrow] (molecule) -- (organism);
  \draw[vibeyarrow] (organism) -- (ecology);
  \node[font=\tiny,align=center,text=vibeygray] at (-3.9,-0.92)
    {code + test +\\delivery evidence};
  \node[font=\tiny,align=center,text=vibeygray] at (-1.3,-0.92)
    {contracts +\\shared state};
  \node[font=\tiny,align=center,text=vibeygray] at (1.3,-0.92)
    {feedback +\\repair + memory};
  \node[font=\tiny,align=center,text=vibeygray] at (3.9,-0.92)
    {protocols +\\participants};
\end{tikzpicture}
\caption{The proposed digital hierarchy. Each level preserves the lower level but
adds interaction contracts and a new convergence question; a local success cannot
prove convergence of its containing structure.}
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
contracts and operating signals of the structures within it.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeycore,minimum width=2.7cm] (web) at (0,0)
    {WORLD WIDE WEB\\digital ecology};
  \node[vibeysoft,minimum width=1.65cm] (browser) at (-4.0,1.55) {browsers};
  \node[vibeysoft,minimum width=1.65cm] (dns) at (-1.55,2.05) {DNS};
  \node[vibeysoft,minimum width=1.65cm] (tls) at (1.55,2.05) {TLS +\\certificates};
  \node[vibeysoft,minimum width=1.65cm] (server) at (4.0,1.55) {servers};
  \node[vibeysoft,minimum width=1.65cm] (cdn) at (-4.0,-1.55) {CDNs};
  \node[vibeysoft,minimum width=1.65cm] (search) at (-1.55,-2.05) {search};
  \node[vibeysoft,minimum width=1.65cm] (app) at (1.55,-2.05) {applications};
  \node[vibeysoft,minimum width=1.65cm] (people) at (4.0,-1.55) {people +\\operators};
  \foreach \n in {browser,dns,tls,server,cdn,search,app,people}
    {\draw[vibeyarrow] (\n) -- (web);}
  \draw[vibeydashed,<->] (browser) -- (server) node[midway,above,font=\tiny] {HTTP};
  \draw[vibeydashed,<->] (people) -- (app) node[midway,below,font=\tiny] {signals};
  \node[font=\tiny,align=center,text=vibeygray] at (0,-0.58)
    {shared protocols\\memory, metabolism, repair, adaptation};
\end{tikzpicture}
\caption{The Web as a digital ecology. Its organism properties are distributed
across projects, protocols, operators and users; the arrows are interaction contracts
through which the ecology senses, exchanges resources, repairs and changes.}
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
but none was evidence of a finished Python feature.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=2.0cm] (context) at (-5.1,0.7)
    {derive\\tracked context};
  \node[vibeybox,minimum width=2.0cm] (edit) at (-2.55,0.7)
    {edit actual\\Python repo};
  \node[vibeybox,minimum width=2.0cm] (tests) at (0,0.7)
    {run tests\\and gates};
  \node[vibeybox,minimum width=2.0cm] (diff) at (2.55,0.7)
    {inspect diff\\and artifacts};
  \node[vibeycore,minimum width=2.0cm] (deliver) at (5.1,0.7)
    {commit + PR\\delivery evidence};
  \draw[vibeyarrow] (context) -- (edit);
  \draw[vibeyarrow] (edit) -- (tests);
  \draw[vibeyarrow] (tests) -- (diff);
  \draw[vibeyarrow] (diff) -- (deliver);
  \node[vibeywarn,minimum width=2.5cm] (backlog) at (0,-1.25)
    {failed / unfinished\\return to backlog};
  \draw[vibeydashed,-{Latex[length=2mm]}] (tests.south) -- (backlog.north);
  \draw[vibeydashed,-{Latex[length=2mm]}] (diff.south) -- (backlog.north);
  \draw[vibeyarrow] (backlog.west) |- (context.south);
  \node[font=\tiny,align=center,text=vibeygray] at (2.55,-1.25)
    {marker alone is not\\completion evidence};
\end{tikzpicture}
\caption{Per-item convergence in a Qwen storm. Each item independently traverses
repository grounding, implementation, tests, diff inspection and delivery; a partial
verdict or generated artifact routes back instead of advancing the backlog.}
\label{fig:qwen-cdd}
\end{figure*}
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
credits with a reset time. The runners classify in the same order of precedence.
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
every handoff has a well-defined ledger range $\rho$.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeycore,minimum width=2.5cm] (selector) at (0,0)
    {EngineSelector\\SWRR policy};
  \node[vibeysoft,minimum width=1.65cm] (qwen) at (-4.5,1.55) {qwenloop\\LOCAL};
  \node[vibeysoft,minimum width=1.65cm] (claude) at (-1.5,2.05) {claudeloop\\PAID};
  \node[vibeysoft,minimum width=1.65cm] (codex) at (1.5,2.05) {codexloop\\PAID};
  \node[vibeysoft,minimum width=1.65cm] (cursor) at (4.5,1.55) {cursorloop\\PAID};
  \node[vibeysoft,minimum width=1.65cm] (agy) at (4.5,-1.55) {agyloop\\PAID};
  \node[vibeybox,minimum width=1.65cm] (work) at (0,-2.0) {work item\\boundary};
  \foreach \n in {qwen,claude,codex,cursor,agy}
    {\draw[vibeyarrow] (\n) -- (selector);}
  \draw[vibeyarrow] (selector) -- (work);
  \draw[vibeydashed,-{Latex[length=2mm]}] (work.east) -- (agy.west);
  \node[font=\tiny,align=center,text=vibeygray] at (2.65,-2.45)
    {capacity rejection\\handoff at boundary};
  \node[font=\tiny,align=center,text=vibeygray] at (-2.7,-1.05)
    {weights combine\\health, fidelity, cost, affinity};
  \node[font=\tiny,align=center,text=vibeyred] at (2.7,-1.05)
    {rotation only\\at a safe boundary};
\end{tikzpicture}
\caption{Engine selection and handoff. Local Qwen is preferred when eligible;
smooth weighted round robin distributes boundary-level work, while capacity failure
routes the same ledger-backed item to another engine without rotating mid-turn.}
\label{fig:engine-pool}
\end{figure*}
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

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeybox,minimum width=1.55cm] (h0) at (-4.2,0.6) {$h_0$\\reviewed};
  \node[vibeybox,minimum width=1.55cm] (h1) at (-1.4,0.6) {$h_1$\\repair};
  \node[vibeybox,minimum width=1.55cm] (h2) at (1.4,0.6) {$h_2$\\repair};
  \node[vibeycore,minimum width=1.55cm] (h3) at (4.2,0.6) {$h_3$\\current head};
  \draw[vibeyarrow] (h0) -- (h1) node[midway,above,font=\tiny] {push};
  \draw[vibeyarrow] (h1) -- (h2) node[midway,above,font=\tiny] {push};
  \draw[vibeyarrow] (h2) -- (h3) node[midway,above,font=\tiny] {push};
  \node[vibeysoft,minimum width=2.1cm] (claimold) at (-0.2,-1.2)
    {claim\\
    $(c,h_2)$};
  \node[vibeywarn,minimum width=2.1cm] (decision) at (3.5,-1.2)
    {decision on $h_3$\\must re-review};
  \draw[vibeydashed,-{Latex[length=2mm]}] (claimold) -- (decision);
  \node[font=\tiny,align=center,text=vibeygray] at (1.65,-1.88)
    {stale claim rejected};
  \node[font=\scriptsize\bfseries,text=vibeyred] at (-3.1,-1.2)
    {exact-head boundary};
  \draw[vibeyarrow] (h3.south) -- (decision.north);
\end{tikzpicture}
\caption{Exact-head evaluation treats every claim as $(c,h_i)$ rather than as a
property of a pull request in the abstract. A repair advances the head and invalidates
the old claim; the current head must be reviewed again before merge or release.}
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
self-approve. Untrusted third-party revisions are data to all three principals.

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
record.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeycore,minimum width=2.2cm] (record) at (-4.9,0) {record intent\\first};
  \node[vibeysoft,minimum width=2.2cm] (ledger) at (-1.65,1.05) {delivery ledger\\state projection};
  \node[vibeysoft,minimum width=2.2cm] (outbox) at (-1.65,-1.05) {transactional outbox\\at-least-once};
  \node[vibeysoft,minimum width=2.2cm] (audit) at (1.65,1.05) {audit hash chain\\tamper evidence};
  \node[vibeysoft,minimum width=2.2cm] (bootstrap) at (1.65,-1.05) {bootstrap\\fail-closed};
  \node[vibeybox,minimum width=2.2cm] (effect) at (4.9,0) {effect\\derived state};
  \draw[vibeyarrow] (record) -- (ledger);
  \draw[vibeyarrow] (record) -- (outbox);
  \draw[vibeyarrow] (ledger) -- (audit);
  \draw[vibeyarrow] (outbox) -- (bootstrap);
  \draw[vibeyarrow] (audit) -- (effect);
  \draw[vibeyarrow] (bootstrap) -- (effect);
  \node[font=\scriptsize\bfseries,text=vibeyred] at (0,-2.05)
    {append before act; missing evidence stops the effect};
\end{tikzpicture}
\caption{Append-before-act at three implementation scales. The delivery ledger,
transactional outbox, audit chain and bootstrap layer all make intent durable before
an external or derived effect is allowed to proceed.}
\label{fig:record-effect}
\end{figure*}
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
sources; history figures are stated at revision `559638f4`, which the script's
`--rev 559638f4` reproduces.

### The stress record

A harness fired $N$ simultaneous generations at `qwen2.5-coder:14b`, served by ollama
on one machine with 24 GB of memory and 10 cores, for $N$ from 1 to 128, with a 900 s
deadline per generation. Each generation was a real unit of work, an issue triaged or
a pull-request diff reviewed, drawn from a pool of seven artifacts of 2 to 22 KB.
Throughput is successful generations per minute of rung wall clock.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=0.47cm,y=0.85cm]
  \begin{scope}
    \draw[vibeyarrow] (0,0) -- (13.4,0);
    \draw[vibeyarrow] (0,0) -- (0,4.1);
    \draw[vibeydashed] (0,0.99) -- (13.2,0.99);
    \draw[vibeydashed] (0,2.00) -- (13.2,2.00);
    \draw[vibeyblue,very thick] plot coordinates
      {(0,0.36) (1,0.99) (2,0.99) (3,1.17) (4,1.72) (5,1.27)
       (6,1.54) (7,1.37) (8,1.40) (9,2.00) (10,1.60) (11,2.66)
       (12,3.52) (13,1.53)};
    \foreach \x/\n in {0/1,1/2,2/3,3/4,4/6,5/8,6/12,7/16,8/24,9/32,10/48,11/64,12/96,13/128}
      {\filldraw[fill=vibeyblue,draw=white] (\x,0) circle (0.08);
       \node[font=\tiny,rotate=60,anchor=north] at (\x,-0.08) {\n};}
    \node[font=\scriptsize\bfseries,anchor=south west] at (0,4.05)
      {successful throughput (generations / min)};
    \node[font=\tiny,anchor=west] at (13.0,0.99) {stable floor};
    \node[font=\tiny,anchor=west] at (13.0,2.00) {stable ceiling};
  \end{scope}
  \begin{scope}[xshift=7.7cm]
    \draw[vibeyarrow] (0,0) -- (13.4,0);
    \draw[vibeyarrow] (0,0) -- (0,1.15);
    \fill[vibeygreen] (0,0) rectangle (0.55,1.00);
    \fill[vibeygreen] (1,0) rectangle (1.55,1.00);
    \fill[vibeygreen] (2,0) rectangle (2.55,1.00);
    \fill[vibeygreen] (3,0) rectangle (3.55,1.00);
    \fill[vibeygreen] (4,0) rectangle (4.55,1.00);
    \fill[vibeygreen] (5,0) rectangle (5.55,1.00);
    \fill[vibeygreen] (6,0) rectangle (6.55,1.00);
    \fill[vibeygreen] (7,0) rectangle (7.55,1.00);
    \fill[vibeygold] (8,0) rectangle (8.55,0.875);
    \fill[vibeygold] (9,0) rectangle (9.55,0.938);
    \fill[vibeyred] (10,0) rectangle (10.55,0.500);
    \fill[vibeyred] (11,0) rectangle (11.55,0.625);
    \fill[vibeyred] (12,0) rectangle (12.55,0.552);
    \fill[vibeyred] (13,0) rectangle (13.55,0.180);
    \foreach \x/\n in {0/1,1/2,2/3,3/4,4/6,5/8,6/12,7/16,8/24,9/32,10/48,11/64,12/96,13/128}
      {\node[font=\tiny,rotate=60,anchor=north] at (\x,-0.08) {\n};}
    \node[font=\scriptsize\bfseries,anchor=south west] at (0,1.1)
      {success fraction by offered concurrency};
    \node[font=\tiny,align=left,anchor=north west] at (0,-0.72)
      {green = 100\%\\gold = 87.5--93.8\%\\red = overloaded};
  \end{scope}
\end{tikzpicture}
\caption{The sovereignty stress record in two views. Throughput rises into a broad
stable band from offered concurrency $N=2$ through $N=32$, while the success fraction
collapses beyond the substrate's sustainable region. The points and bars reproduce the
paper's rung table; the second panel makes the throughput/success trade-off visible.}
\label{fig:stress-rate}
\end{figure*}
```

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
timeout; not one response was malformed or corrupt.

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
file-write calls totalling 32,073 bytes. Thus the accepted completion rate at the
cutoff was 4/13, or 30.8%, while a verdict alone would have suggested 6/13, or 46.2%.

This is a runner-reliability observation, not a model-quality or throughput estimate.
It is nevertheless an empirical check of the completion contract: a verdict without
the completion marker did not count as success, and unfinished event trails remained
unfinished rather than being promoted to completed work. The run also exposed a
configuration observation worth preserving: the requested context setting was 32,768
tokens, while the local server reported 40,960 at the cutoff. The paper therefore makes
no claim about a controlled context-window effect from this pilot. The raw logs remain
local operational artifacts; the compact tracked extraction is the reproducible source
used by `scripts/paper_evidence.py`.

```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[x=0.55cm,y=1cm]
  \node[font=\scriptsize\bfseries,anchor=west,text=vibeyink] at (0,1.55)
    {13 run directories at the evidence cutoff};
  \draw[draw=vibeyink,line width=.65pt,rounded corners=2pt]
    (0,0) rectangle (13,0.72);
  \fill[vibeygreen] (0,0) rectangle (4,0.72);
  \fill[vibeygold] (4,0) rectangle (6,0.72);
  \fill[vibeyred] (6,0) rectangle (8,0.72);
  \fill[vibeygray] (8,0) rectangle (9,0.72);
  \fill[vibeygray!35] (9,0) rectangle (13,0.72);
  \foreach \x in {4,6,8,9}
    {\draw[white,line width=.65pt] (\x,0) -- (\x,0.72);}
  \node[font=\tiny,text=white,align=center] at (2,0.36) {4\\complete};
  \node[font=\tiny,text=white,align=center] at (5,0.36) {2\\verdict only};
  \node[font=\tiny,text=white,align=center] at (7,0.36) {2\\no verdict};
  \node[font=\tiny,text=white,align=center] at (8.5,0.36) {1\\tool error};
  \node[font=\tiny,text=vibeyink,align=center] at (11,0.36) {4\\no events};
  \node[vibeywarn,minimum width=2.3cm,anchor=west] at (8.4,2.25)
    {+1 active\\storm process};
  \draw[vibeydashed,-{Latex[length=2mm]}] (8.9,2.05) -- (8.9,0.8);
  \node[font=\tiny,align=left,anchor=north west] at (0,-0.38)
    {verdicts: 6\\completion markers: 4\\accepted rate: 4/13};
\end{tikzpicture}
\caption{Cutoff-bounded Qwen storm dispositions. A verdict-only run remains
incomplete, and an active process is independent of the resolved or empty
directories; counting all visible artifacts as completed would overstate delivery.}
\label{fig:qwen-disposition}
\end{figure}
```

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
couplings; it is a postulate, not a law.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=1cm,y=1cm]
  \node[vibeycore,minimum width=2.25cm] (operation) at (0,0)
    {operation\\feasible?};
  \node[vibeysoft,minimum width=1.55cm] (network) at (0,2.2) {NETWORK\\reachable};
  \node[vibeysoft,minimum width=1.55cm] (hardware) at (2.65,1.15) {HARDWARE\\capacity};
  \node[vibeysoft,minimum width=1.55cm] (software) at (2.65,-1.15) {SOFTWARE\\installed};
  \node[vibeysoft,minimum width=1.55cm] (agent) at (0,-2.2) {AGENT\\present};
  \node[vibeysoft,minimum width=1.55cm] (information) at (-2.65,-1.15) {INFORMATION\\fresh};
  \node[vibeysoft,minimum width=1.55cm] (agency) at (-2.65,1.15) {AGENCY\\permitted};
  \foreach \n in {network,hardware,software,agent,information,agency}
    {\draw[vibeyarrow] (\n) -- (operation);}
  \node[font=\tiny,align=center,text=vibeyred] at (0,-3.05)
    {couplings between materials are where coordination shortfalls appear};
\end{tikzpicture}
\caption{The six-material feasibility model. Network, hardware, software, agent,
information and agency each contribute availability, stability and reliability;
coordination is a coupling among them rather than a seventh material.}
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
than $W / r_{\min}$.

```latex
\begin{figure*}[t]
\centering
\begin{tikzpicture}[x=0.05cm,y=1cm]
  \draw[vibeyarrow] (0,0) -- (310,0);
  \draw[vibeyarrow] (0,0) -- (0,1.8);
  \draw[vibeyblue,very thick] (50,0.65) -- (101,0.65);
  \filldraw[fill=vibeyblue,draw=vibeyblue] (50,0.65) circle (0.07);
  \filldraw[fill=vibeyblue,draw=vibeyblue] (101,0.65) circle (0.07);
  \node[font=\scriptsize,anchor=south] at (75.5,0.78)
    {stable-band prediction for $W=100$};
  \node[font=\tiny,anchor=north] at (50,0.45) {50 min};
  \node[font=\tiny,anchor=north] at (101,0.45) {101 min};
  \draw[vibeyred,very thick] (278,1.05) -- (278,1.45);
  \node[font=\tiny,text=vibeyred,anchor=south] at (278,1.5)
    {serial substrate: 278 min};
  \draw[vibeydashed] (0,0.28) -- (310,0.28);
  \node[font=\tiny,anchor=north west] at (0,0.18)
    {zero-shortfall time $T_0$; shortfalls dilate it};
  \foreach \x in {0,50,100,150,200,250,300}
    {\draw[vibeyink] (\x,0) -- (\x,-0.08);}
  \node[font=\scriptsize\bfseries,anchor=west] at (312,0) {minutes};
\end{tikzpicture}
\caption{The completion-time prediction. At the measured stable-band rates, 100
units require roughly 50--101 minutes on the fixed substrate; the serial rung alone
would require about 278 minutes. The higher scale is a dilation from shortfalls,
not a second definition of completion.}
\label{fig:completion-band}
\end{figure*}
```

Governance has a price in time, and the price can be lowered without lowering the bar.
The workstream that parallelised the orchestrator's test suite measured the four
per-layer coverage gates falling from about 1,530 s (four sequential suite runs) to
136 s, an 11.3-fold reduction, by computing all four floors from one instrumented run,
and the bare suite falling from 383 s to 135 s, without removing a gate
(`docs/runbooks/expansion/evidence/13-front1-validation.md`). That is a governance
dilation made smaller while the requirement stayed the same.

### Field data

The git history is field data: nothing in it was held fixed. At revision `559638f4`,
1,103 commits are reachable across nine root histories, the absorbed histories of the
family's packages. Since 2026-08-09, when the family's own development begins, 1,091
commits landed on 28 active days, between 1 and 130 per day (median 31, mean 39.0,
sample standard deviation 31.7). Commits landed in all 24 hours of the day in US
Eastern time, with the fewest (15) in the 09:00 hour and the most (82) in the 02:00
hour. The longest
pause was nine days with no commit, from 2026-08-31 to 2026-09-08, and nothing in the
repository records its cause. Eleven `vibey` release tags point at commits dated
between 2026-08-16 and 2026-09-18, and 503 commit subjects across the absorbed
histories end in a pull-request reference.

The daily rate's spread is 81% of its mean, against 24% in the controlled region.
That is what the model predicts when the coordinates of $d$ vary freely, but it is
also what almost any model would predict of an uncontrolled process, so the history
does not test the regularity. We report it so that the controlled band is never
mistaken for a field rate.

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

<!-- BEGIN GENERATED storm-evidence — regenerated by tools/storm-evidence.py -->

*Derived from `docs/plans/qwenstorm-3.0.0/evidence/ledger.jsonl`, an append-only record
consumed under sub-doctrine 10.g. Regenerated automatically; do not edit inside these
markers. This block states figures only — every claim about them is written by a person
outside it.*

| quantity | value |
|---|---|
| ledger records | 183 |
| span consumed | 2026-09-23T04:40:49Z to 2026-09-23T05:20:56Z |
| lanes observed | 15 |
| lanes claiming completion | 9 |
| lane starts / ends logged | 33 / 27 |
| lanes integrated / abandoned | 8 / 2 |
| recorded attempts | 37 |
| total turns across attempts | 1373 |

**Gaps in this span:** none; every byte and record between the watermarks was read.

<!-- END GENERATED storm-evidence -->
