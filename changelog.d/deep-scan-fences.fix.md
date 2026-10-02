- **Documentation deep scan:** reads fenced code blocks the way CommonMark does instead of
  counting backticks, which had failed the scan every night since 2026-09-28 on a correct file.
  It now names every Markdown file whose fence really never closes.
- **Context microslices:** the converter (`src/vibey_tools/skills/tools/slice_markdown.py`) no
  longer splits a document at a `## ` line inside fenced code. Four skills that show a heading
  inside a code block had been cut mid-fence into eight slices that opened a block they never
  closed. Their slice sets are regenerated, and the deep scan now finds no unclosed fence.
