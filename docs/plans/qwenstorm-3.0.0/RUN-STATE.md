# QwenStorm 3.0.0 — run state

Snapshot 2026-09-23T06:48:28Z, written by `tools/storm-snapshot.py`.

The runner's durable record is `integrated.txt` and `abandoned.txt`: a lane in neither is
unsettled, whatever exists under `lanes/`. `lanes/` lives in /tmp and is wiped between
sessions, so nothing here depends on it surviving.

- queue: **594 lanes** · integrated: **8** · abandoned: **2**
- lane worktrees: **22** · finished awaiting review: **21** · unsettled: **22**
- integration branch: `876fee98`
- last line of progress.log: `2026-09-23T06:39:10Z start gap-aws-secrets #493 on integration@876fee98`

Still running or never finished (1): `gap-aws-secrets`


## How to resume

```bash
cd /private/tmp/claude-501/storm/qwenstorm-3.0.0
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
abandoned   opencodeloop-parity-p1
abandoned   opencodeloop-parity-p2
```
