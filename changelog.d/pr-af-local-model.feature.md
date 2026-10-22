* **pr-af on a local model, balanced with OpenRouter:** the venue now chooses pr-af's
  model. `[pr_automation.pr_af] host_provider = "local"` has the operator's own runner
  review on the model the sovereign lane already serves (free) while its heartbeat is
  fresh, and the hosted runner keeps the inexpensive OpenRouter model otherwise.
  `hosted_enabled = false` drops the paid venue, so a repository can review on its own
  hardware and never hold an OpenRouter key. The local path is a compose override layered on
  the pinned checkout, and it blanks the router key inside the container. A local model may
  block the gate but does not pass it alone (`local_verdict_passes`, false by default).
  Off by default and not enabled in this repository: a one-file bump took over 45 minutes on
  `gpt-oss:20b`. ADR-0090.
