# opencodeloop

`opencodeloop` is the OpenCode process adapter shipped inside `vibey`. It keeps
the runner contract stable while delegating model execution to the external
`opencode` CLI.

The adapter is deliberately honest about its boundary:

- `opencode --version`, `opencode run --help`, and `opencode auth list --format json`
  are checked before execution;
- the external CLI must support `run --format json`;
- OpenCode's provider-specific model and billing settings remain outside this
  package; the preflight only requires a saved provider credential;
- normalized events and terminal state are written to `.opencodeloop/runs/` for
  Vibey's existing `LoopProcessAdapter` to consume.

New runs send the plan as a positional OpenCode message. Resumes use the
provider session id plus a bounded continuation prompt (override it with
`--prompt` when invoking `opencodeloop resume`); this keeps the generic Vibey
resume command from ever waiting for an interactive message.

Install the OpenCode CLI separately, then verify it with:

```bash
opencodeloop doctor
```

The official OpenCode CLI documentation describes the `run --format json`
interface used here: <https://opencode.ai/v2/docs/cli/>.
