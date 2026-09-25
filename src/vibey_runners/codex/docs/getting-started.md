# Getting started

## Install

`codexloop` is not a PyPI project of its own. It ships inside the `vibey`
distribution, which installs every `*loop` runner and every family tool in one
step (vibey ADR-0037):

```bash
pipx install vibey-engine
```

From a clone (contributors), in `src/vibey_runners/codex`:

```bash
pip install -e ../common && pip install -e ".[dev,docs]"
```

## Preflight

```bash
codexloop doctor
codexloop capacity
```

## Run a plan

```bash
codexloop run path/to/plan.md --max-turns 20
```

Default transport is `codex exec --json`. Optional `--transport app-server`
probes the experimental app-server and falls back to exec when unavailable.

!!! note "Roadmap"
    Live app-server interrupt/steer against production `codex` builds still
    tracks the experimental protocol; the shim-backed adapter is covered in CI.
