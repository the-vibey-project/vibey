* **`vibey search` and `vibey fetch`, and web search for every loop:** vibey now owns a web
  search, so a DESIGN stage with no operator reading no longer ends in a `research_evidence`
  gate for lack of evidence a search would have found, and any engine that can run a command can
  look things up. Backends are SearXNG (`VIBEY_SEARXNG_URL`, keyless, reaches sessions) and
  Brave (`VIBEY_BRAVE_API_KEY`, the research stage only; the key is never passed to a session).
  `fetch` refuses private, loopback and metadata addresses on every redirect hop. Results carry
  an untrusted banner and evidence is quoted text with its URLs, never a summary. `vibey worker`
  adds a "Web access" note, with the absolute path of the running `vibey`, to every run's plan
  and passes the non-secret `WEBSEARCH_*` settings to sessions (the qwenloop and gptossloop
  runner's shell now admits them). gptossloop and qwenloop also get native `web_search` and
  `web_fetch` tools, which run the same `vibey` commands. codexloop and claudeloop-local have no
  engine-level search beyond the command in their plan. Before, the only way past a research gap was to write reading
  material by hand.
