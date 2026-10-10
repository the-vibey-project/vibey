* **`vibey llm tail` and the LLM wire log:** `-vvv` documented "full payloads" and the
  sovereign DESIGN and DECOMPOSE providers' traffic to Ollama reached no log at all, so a call
  that ran for fifteen minutes showed nothing until it returned. With `-vvv` (or
  `VIBEY_LLM_WIRE_LOG=path`) the client now streams the reply and appends every request, every
  streamed piece of reasoning and answer, and the model's counts and timings to a JSON-lines
  wire log; `vibey llm tail` follows it live, starting at the latest call (`--all`,
  `--no-follow`, `--raw` and `--max-chars` adjust it). The log is redacted by the ledger's
  redactor, with streamed text held to a whitespace boundary so a credential cannot be split
  across two pieces, and is created readable by its owner alone. Without the switch nothing
  changes: one blocking request, no file.
