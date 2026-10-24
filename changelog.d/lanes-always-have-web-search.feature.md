* **Every claudeloop lane is launched with web search:** `run --web-search` is off unless asked for, and the BUILD
  path never asked. Engines now declare `skills` and `web_search` with their evidence, `vibey` reports what each lane
  is not shown to have, and the known gaps (the local runner has no MCP, codexloop is unknown) are pinned in a test so
  they cannot widen unseen. `claudeloop-local` is unchanged: its backend refuses web search. ADR-0092, #1666.
