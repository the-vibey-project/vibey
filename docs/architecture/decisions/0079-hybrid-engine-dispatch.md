# 0079 — Hybrid engine dispatch: paid engines in tandem with sovereign ones, measured and capped

**Status:** proposed · **Date:** 2026-10-03 · **Applies:** ADR-0074 (measured dispatch) to the engine pool · **Amends:** ADR-0038 (tier-first selection gains an overflow path) · **Cites:** sub-doctrines 8.a, 8.b, 7.c, 10.e, 10.f, 12.c, 12.l, and 8.k which this record implements · **Related:** ADR-0005, ADR-0015, ADR-0016, ADR-0038, ADR-0056, ADR-0070 · **Issue:** #1376 (part 2) · **Evidence:** `develop` at `588c69b3f`, read 2026-10-03; the storm throughput audit of 2026-09-23 (one local model slot binding 96.7% of the time)

**Owes:** sub-doctrine 8.k, drafted in the same pull request in a commit of its own and
**not ratified by this record** — only the operator's merge ratifies it (Constitution
Article II.3, ADR-0020). Also the advertised ADR count, the `properdocs.yml` nav entry,
`docs/llms.txt`, `docs/reference/configuration.md`, `docs/plans/rotation-and-engines.md` and
the engine-adapters skill in all four agent trees, all in the change that carries this
record.

## Context

`domain/rotation.py::eligible()` filters on installation, conformance, login, circuit,
exclusions and capabilities. It has no notion of how many jobs an engine is already
running. `preferred_tier()` then offers SWRR the LOCAL tier whenever any local candidate
has positive weight (ADR-0038, sub-doctrine 8.a). So a local model slot that is already
busy stays eligible, every BUILD job is assigned to it, and the jobs queue inside Ollama
one behind another; a paid engine runs only when no local engine can take a job at all.
The audit of 2026-09-23 measured the one local slot binding 96.7% of the time: the
sovereign path was not failing, it was full.

8.a allows a paid engine only where the sovereign path "provably cannot carry the work".
A full slot is not obviously that, and treating it as that without a bound would turn
8.a's exception into a preference by the back door. The operator decided (2026-10-03)
that paid engines may supplement sovereign ones, under a measured mode, a daily cap and a
record of every overflow — and that the law must say so before the code may.

## Decision

### 1. Three modes, `auto` by default

`[engines] mode` is `singleton`, `hybrid` or `auto` (default `auto`).

- **`singleton`** is today's selection exactly. With no dispatch store wired, or with a
  policy that resolves to `singleton`, `SelectingEngineProvider` makes the same
  `EngineSelector.select_engine` call it always made; a property test holds the domain
  plan byte-for-byte equal to `preferred_tier(candidates)`.
- **`hybrid`** keeps local first and adds overflow (§2).
- **`auto`** chooses between the two from a recorded measurement (§4).

### 2. Overflow, and only overflow

Each engine has declared concurrent **slots**: `[engines.slots]`, defaulting to 1 for a
local engine (one Ollama serves one request at a time unless `OLLAMA_NUM_PARALLEL` says
otherwise) and 2 for a paid one. Under `hybrid`, `domain/engine_dispatch.py::EngineDispatcher`
plans a selection from the same candidates `select_engine` builds:

1. A local candidate with a free slot exists → SWRR over the local candidates with a free
   slot. A paid engine is never offered while a local slot is free (property-tested).
2. No local candidate can win a round at all → today's fallback, unchanged and not counted
   as overflow: that is the case 8.a already allowed.
3. Every eligible local slot is occupied, and overflow **could** follow — a paid
   candidate with a free slot exists and the cap allows one — but the job has waited less
   than `[engines] overflow_after_seconds` → **hold**: the job is deferred as a capacity
   defer (no attempt is burned) and looked at again after
   `min(remaining wait, slot_poll_seconds)`.
4. The same, and the job has waited long enough → SWRR over the paid candidates with a
   free slot, marked as **overflow**.
5. Overflow cannot follow (no paid engine free, or the cap reached) → today's plan: the
   job is assigned to local and queues behind it, as it always has. A job is never held
   for something that cannot happen.

The provider then reserves the overflow against the cap (§3). A reservation another worker
beat to the last overflow defers the job for one poll; the cap holds.

**Slots in use** are the queue's own: jobs `leased` with `lease_expires_at > now()` and an
assigned engine, counted across every project (an engine's slots belong to its backend,
and one Ollama serves the whole host), excluding the job being selected. An expired lease
is not a slot in use, which is what keeps the count right under replay and lease expiry.
Counts are read in the infrastructure and handed to the pure domain as data.

**How long a job has waited** is the time since its first hold *on this attempt*. The
first hold appends `EngineSlotWaitStarted` (job, attempt, the slots it found occupied, the
cap); later holds of the same job and attempt append nothing. A hold keeps the attempt
number (a capacity defer refunds the claim's increment), so the wait accumulates across
holds and starts afresh only on a real retry.

### 3. The daily cap, counted from the ledger

`[engines] paid_daily_cap` (default **10**, overridable by `VIBEY_ENGINES_PAID_DAILY_CAP`)
bounds the overflows one project takes per UTC day. It is counted from durable records —
the project's `EngineOverflowSelected` events since UTC midnight — never from process
memory, so it survives restarts. A reservation takes the project row `FOR NO KEY UPDATE`,
counts again under the lock, and appends one more event only while the count is below the
cap, in one transaction: two workers cannot both take the last overflow (an integration
test races eight reservations against a cap of three and gets exactly three). Each event
names the paid engine, the job and attempt, the occupied local slots, how long the job
waited, the threshold, the cap, the count it was granted on and what is left
(`cap_remaining_after`), and the mode and why it is in force — evidence-bounded status
(10.f) for every overflow.

The cap is a count and never a switch-off: zero means no overflow, and **there is no
value that means "uncapped"**. 8.b allows an uncapped paid declaration by one six-step path only, and a
configuration key is not that path.

The cap is per project because `[engines]` is project configuration and every overflow
event is on a project's ledger. An installation-wide cap would need a key outside any
project; that is left to the operator (below).

### 4. `auto`: measured, per ADR-0074

ADR-0074 requires every queue-backed dispatch choice to be measured where it runs:
missing, stale, invalid or failed measurement → `singleton`; the measurement durable,
inspectable and invalidated when the workload or implementation changes; no winner claimed
without one. This record applies that to the engine pool.

**What is measured.** Not a synthetic benchmark. The only experiment that could run both
modes live is one that buys paid sessions to find out, which no unattended default may do
(8.a, 8.b). The measurement is passive, over the project's own BUILD history for the last
`auto_window_hours` (default 168): each job's first and last ledger event on each enabled
local engine is one **session**. A session is **contended** when it began while every
local engine had all its slots occupied by other sessions; its **would-wait** is how long
until a slot freed. `hybrid` wins only when at least `auto_min_sessions` (20) sessions were
seen, at least `auto_min_contention` (0.25) of them were contended, and the median
contended session would have waited at least `overflow_after_seconds`. Otherwise hybrid
would hold jobs and overflow none, and `singleton` stands. This is the same evidence the
throughput audit read by hand, recorded by the machine.

**Where it lives.** An append-only `EngineDispatchMeasured` event on the project's ledger:
the winner, the sessions, the contended sessions, the median wait, the reason, the
algorithm (`local-slot-contention/1`) and a fingerprint. It is inspectable with `vibey
ledger`, shared by every worker of the project, and outlives the machine (10.h).

**When it is current.** While its fingerprint matches — the local engines and their slots,
the overflow threshold, the window and both thresholds, the algorithm and the running
`vibey-engine` version — and it is younger than `auto_max_age_hours` (24) and not in the
future. Otherwise the next selection measures again and records the new one before using
it. A measurement that cannot be taken or recorded resolves to `singleton`, with the
failure logged; a payload this version cannot read is no measurement.

**Capability gap (10.e).** ADR-0074's machinery for `[bus] mode` —
`BusDispatchBenchmark`, `BusDispatchSelection`, `WeeklyBusDispatchRecomputer` — and
qwenloop's `HybridTurnMultiplexer` were the first place looked, and are not reused, for
reasons that are gaps rather than taste: the benchmark measures by running synthetic load,
and the engine pool's only synthetic load is paid; its winner lives in one machine's user
cache with no workload or implementation check, where every worker of a project must read
one answer and a changed slot count must invalidate it; and the multiplexer's semaphore is
per process, where slots are shared by every worker on the queue. The gap is written at
the call site (`application/engine_dispatch_service.py`).

The **multiplexer** policy ADR-0074 asks for where it is semantically available is not
available here: an unbounded paid dispatch is exactly what 8.a and the cap forbid. That is
the "document why one is semantically impossible" its consequences allow.

### 5. Where it lives in the code

- `domain/engine_dispatch.py` — the dispatcher, the policy, the grounds, the hold, the
  measurement and its judge, the UTC day. Pure: counts, waits and instants arrive as data.
- `domain/config.py::EngineDispatchConfig` — the keys, validated.
- `application/engine_selector.py::EngineSelector.select_dispatched` — the same candidates,
  planned; raises `SlotHeld` before any cursor moves.
- `application/engine_dispatch_service.py::EngineDispatchService` — resolves the policy,
  reads the load, records holds and reservations.
- `application/engine_selection.py::SelectingEngineProvider` — `dispatch=None` is today's
  selection, unconditionally.
- `infrastructure/db/engine_dispatch_store.py` — the queries and the three trusted events.
- `infrastructure/config_loader.py` — `[engines]`'s dispatch keys are copied into the
  project record at `vibey new` (only those keys), and `VIBEY_ENGINES_MODE`,
  `VIBEY_ENGINES_OVERFLOW_AFTER_SECONDS` and `VIBEY_ENGINES_PAID_DAILY_CAP` overlay them.

The three new event kinds are withheld from ledger publication: they name the operator's
engines, slots and paid cap.

## Defaults, and why — each the operator's to change

| Key | Default | Why |
|---|---|---|
| `mode` | `auto` | The operator's decision: measured, falling back to `singleton`. |
| `slots` (local) | 1 | Ollama's default concurrency; 8.j measures more where a host can carry it. |
| `slots` (paid) | 2 | A bounded burst per paid engine; the daily cap bounds the total. |
| `overflow_after_seconds` | 600 | Long enough that a short local job finishing frees the slot; short against local BUILD sessions measured in tens of minutes. |
| `paid_daily_cap` | 10 | A day's worst case is ten paid sessions per project, each still under the per-cycle dollar brake; enough to relieve the measured peak, small enough to stay a supplement. |
| `slot_poll_seconds` | 30 | A held job is looked at again often enough to take a slot that frees, rarely enough that a local `doctor` per look is cheap. |
| `auto_window_hours` / `auto_min_sessions` / `auto_min_contention` / `auto_max_age_hours` | 168 / 20 / 0.25 / 24 | A week of history, enough sessions to mean something, contention that is common rather than rare, re-measured daily. |

## Consequences

- With `mode = "singleton"`, or before `auto` has a measurement that chooses `hybrid`,
  selection is exactly what it was. `auto` appends one `EngineDispatchMeasured` event per
  project per day (or per change of workload or version).
- Under `hybrid`, a job that cannot have a local slot now waits in the database queue
  rather than inside Ollama, and is looked at again every `slot_poll_seconds`, each look
  running the local engines' `doctor` as every selection does.
- The paid daily cap is exact across workers and restarts. A worker that dies after its
  reservation but before the job ran leaves the overflow counted: the cap errs toward
  sovereign.
- **Known imprecision, stated.** Slots in use count jobs by their assigned engine, so a job
  re-claimed for a retry carries its previous attempt's engine until it is selected again
  — a moment, during which that engine looks one slot busier. DESIGN and DECOMPOSE on the
  sovereign providers use the local model without a lease that names it, so they are not
  counted. The measurement treats a job's whole BUILD history on an engine as one session.
  A database shared by hosts with separate Ollama servers would count their slots as one.
  None of these can make paid preferred: each only delays or narrows overflow, or makes
  `auto` choose from coarser evidence.
- 12.l asks for a bounded experiment. This record measures passively over a bounded window
  of the surface's own recorded workload, for the reason in §4; whether that satisfies
  12.l as written, or 12.l should say so, is the operator's to rule.

## Left to the operator

1. Ratify 8.k by merging, or decline it — without it this code must not ship enabled.
2. The defaults above, the cap above all.
3. Whether the cap should be per installation rather than per project.
4. Whether paid selections made under 8.a's existing fallback (no local engine eligible at
   all) should count toward the daily cap. They do not today: they are not overflow, and
   they were never capped.
5. Whether passive measurement satisfies 12.l.
