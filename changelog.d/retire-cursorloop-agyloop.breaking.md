- **Engines:** `cursorloop` and `agyloop` are retired and deleted with their runners, console
  scripts and vendor SDK dependencies (ADR-0078, #1376); the paid loop is `claudeloop` and
  `codexloop`. A `vibey.toml`, `--engines` allow-list, `engine_environment` or
  `VibeyProject.spec.engines` that still names either is refused with an error naming
  ADR-0078 -- remove the name. Ledger rows, health rows and rotation cursors that name them
  stay valid history and keep loading.
