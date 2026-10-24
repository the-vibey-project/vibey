* **A web-search query no longer keeps the gaps a file path leaves behind:** the whitespace pattern in
  `web/research.py` had been written as `\\s+`, which matches a literal backslash and `s`, so a context such as
  "Fold `/ministry` from /Users/x/y into this site" reached the search backend with runs of spaces and was never cut to
  its 160 characters. The pattern is `\s+` again. Found when `develop` went red, #1713.
