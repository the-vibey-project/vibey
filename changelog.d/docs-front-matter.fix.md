* **docs:** the backlog and documentation continuation pages no longer print their
  `description:` front matter as text. Each unquoted description held a second colon, which
  YAML refuses, so the site showed the block instead of reading it. Both are quoted, and
  `tests/meta/test_docs_front_matter.py` now parses every page's front matter.
