- **Documentation deep scan:** reads fenced code blocks the way CommonMark does instead of
  counting backticks, which had failed the scan every night since 2026-09-28 on a correct file.
  It now names every Markdown file whose fence really never closes.
