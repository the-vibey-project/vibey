# QwenStorm 3.0.0 — run state

Snapshot 2026-09-23T03:46Z, at a deliberate pause. Written by hand, not by the runner.

The storm was stopped on purpose so three branches could clear the pre-push gate on an
unloaded machine: the full suite was flaking under the storm's own CPU and memory load,
failing three times on three *different* tests with 2959 of 2960 passing each time. Removing
the load is the fix; retrying was not.

The runner's own durable record is `integrated.txt` and `abandoned.txt`: a lane in neither is
unsettled, whatever exists under `lanes/`. `lanes/` lives in /tmp and is wiped between
sessions, so nothing here depends on it surviving.

- queue: **594 lanes** · integrated: **8** · abandoned: **2**
- lane worktrees present at the pause: **17**
- integration branch: `d10ac25b`, identical to `origin/develop`

## How it was stopped

`SIGTERM` to `storm-queue.sh`, the in-flight `qwenlane.py`, and `storm-cycle.py`, in that
order — the queue first so no new lane starts, then the runner, then the outer loop. All
three exited; nothing was `SIGKILL`ed and no lane directory was touched.

`split-367-1-run-dir` was nine minutes into a run and has no `result.json`, so it is
unfinished and will simply run again. Nothing else was in flight.

## How to resume

```bash
cd /private/tmp/claude-501/storm/qwenstorm-3.0.0
touch UNATTENDED                      # batch review; a finished lane does not block the queue
nohup bash tools/storm-queue.sh > scratch/storm-run.log 2>&1 < /dev/null & disown
```

macOS has no `setsid`; `nohup ... & disown` is what survives the launching shell. `storm-queue.sh`
starts `storm-cycle.py` itself if it is not already running, so the outer loop needs no separate
command. The runner re-reads `queue.txt` every pass, so the queue can grow while it runs. A lane
with a `.qwenstorm/result.json` is treated as finished and awaiting review; delete that file to
have it run again.

Health, any time, without needing `ps` (which the sandbox refuses):

```bash
python3 tools/storm-watch.py            # one report; exit 0 healthy, 1 wrong, 2 cannot tell
python3 tools/storm-watch.py --watch    # silent until something is wrong, then exits
```

## What changed at this pause

Two gates could not pass, and both read as the lane's failure:

- **argv quoting.** `checks_of()` split spec commands with `str.split()`, so
  `--include='src/vibey/domain/*'` reached coverage with the apostrophes still attached and
  matched no file. Every lane with a coverage gate answered "No data to report". Now
  `shlex.split`.
- **a coverage run narrowed to one test path.** 33 specs measured a slice
  (`--cov-report= tests/domain`) and then judged a whole layer at `--fail-under=100`. That
  reports 78% and always will. The path is dropped; `lint-specs.py` now refuses the shape.

Lanes repaired or reverted by hand at the pause:

| lane | action |
|---|---|
| `rmq-r02-wakeup-composition` | repaired — kept its real work (tightening `object` return types to `EngineHealthServiceInterface` / `EngineSelectorInterface`), removed the `}` and `*** End Of File ***` debris, restored the `build_ledger` property it had corrupted |
| `installer-catalogue` | repaired — one untyped `set()`; now mypy-strict clean over 341 files, ruff clean, 13/13 of its own tests passing |
| `rmq-r01-queue-config` | reverted and re-queued — it deleted three working Protocol interfaces its package's `__init__.py` imports, and added five referencing dataclasses that do not exist |
| `chart-operator-forgejo-p1` | reverted and re-queued — it wrote tests for a ServiceAccount, ClusterRole and Deployment it never created |

## Lanes attempted

| lane | claim | turns per attempt | lane-verify |
|---|---|---|---|
| `chart-operator-forgejo-p1` | completed | 40,40,18 | reverted, re-queued |
| `engines-pool` | failed | 28,40,19 | 3 problem(s) |
| `fakes-harness-decouple` | completed | — | import moved above first use |
| `installer-catalogue` | completed | 46 | clean after repair |
| `loops-residency-policy` | — | — | — |
| `orm-bootstrap-async-engine` | completed | 34 | 4 problem(s) — missing sibling modules |
| `orm-tables` | completed | — | 5 problem(s) — missing sibling modules |
| `rmq-r01-queue-config` | failed | 40,11,40 | reverted, re-queued |
| `rmq-r02-wakeup-composition` | completed | 16,39 | clean after repair |
| `rmq-r03-amqp-dependency` | completed | 40,22,16 | changed nothing |
| `rmq-r06-job-dispatch-envelope` | failed | 43,39,60 | ruff only |
| `split-332-1-transport-seams` | failed | 4,29,40 | ruff only |
| `split-351-1-amqp-contract` | failed | 60,42,… | — |
| `split-367-1-run-dir` | in flight at the pause | — | no result; will re-run |
| `surfaces-env` | failed | 40,40,40 | changed nothing |
| `visual-design-provider` | completed | 40,34 | named tests it never wrote |

## The standing bottleneck

Six of fifteen finished lanes were held by a module that would not import. Four of those ten
failures were debris on top of working code and are now repaired mechanically; the rest were
the model's work being incomplete — a module importing a sibling nobody wrote, an unterminated
string, tests a spec named and the lane never produced. No repair tooling addresses that, and
it is the honest measure of what `gpt-oss:20b` currently delivers.

## Settled

```
integrated  engines-provider
integrated  qwenloop-edit-tool
integrated  qwenloop-request-timeout
integrated  qwenloop-run-telemetry
integrated  qwenloop-toolcall-retry
integrated  default-model-p1
integrated  default-model-p2
integrated  default-model-p3
abandoned   opencodeloop-parity-p1
abandoned   opencodeloop-parity-p2
```
