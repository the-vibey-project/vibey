* **`vibey doctor` says what Ollama is holding:** with a local engine switched on, an `ollama`
  line asks the server which models are loaded and warns when the configured model sits at a
  context above `VIBEY_OLLAMA_CONTEXT`. Ollama reloads a model whose context differs from a
  request's, so a model warmed up at a very large window and left resident made the first real
  DESIGN request pay for a reload and time out at 900 seconds, with nothing flagging it: the
  server was healthy and the model was loaded. The line names the fix (`ollama stop MODEL`).
  It prints host and port only, never a URL's credentials, is `SKIP` when no server answers,
  and is never a failure.
