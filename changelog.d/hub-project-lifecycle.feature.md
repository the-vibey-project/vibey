* **A paired phone or desktop app can start, pause, resume and unwind a project:** four hub routes
  (`POST /api/v1/projects`, `.../work/start`, `.../work/pause`, `.../abandon`) need the existing `run` scope and run
  the audited CLI commands on the host (ADR-0091). A device sends a name and a sentence of intake, never a path:
  the folder is `<[hub] projects_root>/<name>`, and `projects_root` is unset by default, so nothing can be started
  from a device until the host says where. Unwinding shows a dry run first and records the reason on the ledger.
