# Documentation

Published site:
[https://the-vibey-project.github.io/cursorloop/](https://the-vibey-project.github.io/cursorloop/)

Built with MkDocs Material and deployed from `main` by
[`.github/workflows/docs.yml`](https://github.com/the-vibey-project/cursorloop/blob/main/.github/workflows/docs.yml)
to GitHub Pages.

```bash
pip install -e ".[docs]"
mkdocs serve
mkdocs build --strict
```

`mkdocs build --strict` fails on broken internal links — the same gate CI
runs before every Pages deploy.

## Link rules (GitHub / GitHub.io / PyPI)

- **In `docs/`** use repo-relative Markdown links between pages
  (`getting-started/installation.md`). MkDocs rewrites them for the site;
  they also work when browsing the tree on GitHub.
- **In `README.md`** (rendered outside this directory) use **absolute** `https://`
  URLs for docs, license, and badges — relative paths break wherever it is rendered
  from another root.
- **`[project.urls]`** in `pyproject.toml` already points Documentation at
  the GitHub.io root; keep that URL in sync with `site_url` in `mkdocs.yml`.
