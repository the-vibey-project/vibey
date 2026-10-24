* **`[build.slicing] max_children` and named epics:** the cap that decides how deep a plan is sliced is a key
  (default 8, at least 2), and a work item may name its feature set in `epic`, which both decomposers now ask the
  model for; consecutive items under one name form one named epic. Every claudeloop lane also gets
  `--deep-research` beside `--web-search` (claudeloop only records it). ADR-0092, #1666.
