- **Feature:** `vibey_gh.markdown_fences.MarkdownFences` finds a Markdown fenced code block that
  never closes, read the way CommonMark reads it: backtick and tilde fences, a closer of the same
  character at least as long as the opener, and fences inside block quotes, list items and HTML
  blocks. The documentation deep scan uses it instead of counting backticks, which failed a
  correct file every night from 2026-09-28, and names every unclosed fence instead of the first.
