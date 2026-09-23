# QwenStorm 3.0.0 — run state

Snapshot 2026-09-23T01:25:27Z. Written by hand at a pause, not by the runner.

The runner's own durable record is `integrated.txt` and `abandoned.txt`: a lane in
neither is unsettled, whatever exists under `lanes/`. `lanes/` lives in /tmp and is wiped
between sessions, so nothing here depends on it surviving.

- queue: **594 lanes**
- integrated: **8** · abandoned: **2**
- lanes attempted this session: **11**

## How to resume

```bash
cd /private/tmp/claude-501/storm/qwenstorm-3.0.0
touch UNATTENDED                      # batch review; a finished lane does not block the queue
nohup bash tools/storm-queue.sh > scratch/storm-run.log 2>&1 < /dev/null & disown
```
macOS has no `setsid`; `nohup ... & disown` is what survives the launching shell. The
runner re-reads queue.txt every pass, so the queue can grow while it runs. A lane with a
`.qwenstorm/result.json` is treated as finished and awaiting review; delete that file to
have it run again.

## Lanes attempted

| lane | claim | turns per attempt | lane-verify |
|---|---|---|---|
| `chart-operator-forgejo-p1` | completed | 40,40,18 | 2 problem(s) |
| `engines-pool` | failed | 28,40,19 | 3 problem(s) |
| `installer-catalogue` | completed | 46 | 3 problem(s) |
| `orm-bootstrap-async-engine` | completed | 34 | 4 problem(s) |
| `rmq-r01-queue-config` | failed | 40,11,40 | 4 problem(s) |
| `rmq-r02-wakeup-composition` | completed | 16,39 | 4 problem(s) |
| `rmq-r03-amqp-dependency` | completed | 40,22,16 | 2 problem(s) |
| `rmq-r06-job-dispatch-envelope` | failed | 43,39,60 | - |
| `split-332-1-transport-seams` | failed | 4,29,40 | 4 problem(s) |
| `surfaces-env` | failed | 40,40,40 | 1 problem(s) |
| `visual-design-provider` | completed | 40,34 | 1 problem(s) |

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
