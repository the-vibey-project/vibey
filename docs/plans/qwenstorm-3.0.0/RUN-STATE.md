# QwenStorm 3.0.0 — run state

Snapshot 2026-09-23T13:32:54Z, written by `tools/storm-snapshot.py`.

The runner's durable record is `integrated.txt` and `abandoned.txt`: a lane in neither is
unsettled, whatever exists under `lanes/`. `lanes/` lives in the storm root, on durable
storage under the storm home (sub-doctrine 10.h), but it is working material rather than the
record, so nothing here depends on it surviving.

- queue: **594 lanes** · integrated: **12** · abandoned: **14**
- lane worktrees: **31** · finished awaiting review: **30** · unsettled: **15**
- integration branch: `023ec2c8`
- last line of progress.log: `2026-09-23T13:32:38Z reaped surfaces-env: the runner gave up after 3 attempt(s), and nothing was ever publishe`

Still running or never finished (1): `gap-ci-tenants-arch-macos-2`

## How it was stopped

- all stopped


## How to resume

```bash
cd "${VIBEY_STORM_HOME:-$HOME/git/vibey-storm}/qwenstorm-3.0.0"   # the storm root (10.h)
touch UNATTENDED                      # batch review; a finished lane does not block the queue
nohup bash tools/storm-queue.sh > scratch/storm-run.log 2>&1 < /dev/null & disown
```

macOS has no `setsid`; `nohup ... & disown` is what survives the launching shell.
`storm-queue.sh` starts `storm-cycle.py` itself, so the outer loop needs no separate command.
A lane with a `.qwenstorm/result.json` is treated as finished and awaiting review; delete that
file to have it run again.

Health, without needing `ps` (which the sandbox refuses):

```bash
python3 tools/storm-watch.py            # exit 0 healthy, 1 wrong, 2 cannot tell
python3 tools/storm-stop.py --stop      # pause: quiet the watch, stop softly, record it
```

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
integrated  gap-agent-tree-parity
integrated  installer-catalogue
integrated  loops-residency-policy
integrated  split-332-1-transport-seams
abandoned   opencodeloop-parity-p1
abandoned   opencodeloop-parity-p2
abandoned   engines-pool
abandoned   gap-cdd-build-trajectory
abandoned   gap-cdd-distance
abandoned   gap-ci-arch-gates
abandoned   gap-ci-macos-gates
abandoned   gap-ci-tenants-arch-macos-1
abandoned   rmq-r01-queue-config
abandoned   rmq-r06-job-dispatch-envelope
abandoned   rmq-r08-dispatch-migration
abandoned   split-351-1-amqp-contract
abandoned   split-367-1-run-dir
abandoned   surfaces-env
```
