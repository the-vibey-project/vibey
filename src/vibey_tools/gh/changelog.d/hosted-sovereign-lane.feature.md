* **sovereign review:** `[pr_automation.fallback] runs_on` runs the sovereign lane on a
  GitHub-hosted runner: the review job starts Ollama and pulls its model there, and is ready
  without a heartbeat, since a hosted runner cannot be offline. Empty, the lane stays on the
  self-hosted runner exactly as before.
