## Title
feat(pypi): declare `keywords` and `classifiers` in pyproject.toml, sourced from the repository's own declared topics

## Why
`pyproject.toml`'s `[project]` table has neither `keywords` nor `classifiers`
(`grep -cE '^(keywords|classifiers)' pyproject.toml` is 0). PyPI's search ranking, its
topic-browse pages, and most LLM/RAG ingestion of a package's PyPI page facet almost
entirely on these two fields; without them `vibey` cannot be found by PyPI's own
category browsing and carries no machine-readable signal of what it is or runs on.

`.vibey-gh.toml`'s `[repository_profile]` (line 66 at integration HEAD) already
declares a 15-term `topics` list for GitHub's own repository topics:
```
topics = [
  "agents", "ai-agents", "autonomous-agents", "claude", "claude-code", "cli",
  "delivery-automation", "devtools", "gemini", "gpt", "llm", "mit-license",
  "orchestration", "postgresql", "python",
]
```
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md`) says a thing declared once
must not be redeclared as a second, independently-drifting copy — so PyPI's `keywords`
must be that exact list, not a fresh invention that immediately falls out of sync with
the repository's own topics the moment one changes.

`classifiers` has zero entries. Sub-doctrine 8.h names Arch Linux and macOS the two
default operating systems; README.md's own Install section (`README.md:68`) states
"Windows is not a supported target"; and CI's `gates` job
(`.github/workflows/ci.yml:30-58`) installs and tests only Python 3.12
(`uv python install 3.12`, no version matrix) even though `requires-python = ">=3.12"`
(`pyproject.toml:10`) permits newer interpreters. Sub-doctrine 10.f (status is
evidence-bounded) means the classifiers must name only what CI actually proves: no
Windows classifier, and no Python version classifier above 3.12 until `gates` tests one.

## Required behaviour
1. In `pyproject.toml`, under `[project]`, immediately after the `license = { text = "MIT" }`
   line (`pyproject.toml:11`) and before the `# One distribution ships...` comment
   (`pyproject.toml:12`), add:
   ```toml
   keywords = [
       "agents", "ai-agents", "autonomous-agents", "claude", "claude-code", "cli",
       "delivery-automation", "devtools", "gemini", "gpt", "llm", "mit-license",
       "orchestration", "postgresql", "python",
   ]
   classifiers = [
       "Development Status :: 5 - Production/Stable",
       "Intended Audience :: Developers",
       "Topic :: Software Development :: Build Tools",
       "Topic :: Software Development :: Quality Assurance",
       "Topic :: System :: Distributed Computing",
       "License :: OSI Approved :: MIT License",
       "Programming Language :: Python :: 3",
       "Programming Language :: Python :: 3 :: Only",
       "Programming Language :: Python :: 3.12",
       "Operating System :: POSIX :: Linux",
       "Operating System :: MacOS",
       "Operating System :: MacOS :: MacOS X",
   ]
   ```
   `keywords` is a byte-for-byte copy of `.vibey-gh.toml`'s `[repository_profile] topics`
   list at the time this lane runs — copy it from the live file, not from this spec, in
   case another lane has changed it first.
2. `Development Status :: 5 - Production/Stable` is justified by README.md's own
   "Upgrading" section: "From 1.0.0 vibey follows semantic versioning" — a commitment
   made at 1.0.0 and still in force at the current 2.x version. Do not weaken it to Beta
   without flagging that in the commit body as a deliberate downgrade.
3. No classifier may contain the substring `Windows`, and no
   `Programming Language :: Python :: 3.1x` classifier may name a version higher than
   the one `gates` actually installs (read it from `.github/workflows/ci.yml`'s `gates`
   job at the time this lane runs, in case it has changed).

## Where to change
- `pyproject.toml`: add the `keywords` and `classifiers` arrays from "Required behaviour"
  item 1, under `[project]`.
- Create `tests/meta/test_pypi_metadata.py`. Copy the provenance header from
  `tests/meta/test_adr_counts.py:1` byte for byte.

## Acceptance criteria
- [ ] `python3 -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']; print(bool(d.get('keywords')), bool(d.get('classifiers')))"` prints `True True`.
- [ ] `keywords` in `pyproject.toml` equals, as a set, `repository_profile.topics` in `.vibey-gh.toml`.
- [ ] `classifiers` contains at least one entry starting with each of: `Development Status ::`, `Intended Audience ::`, `Topic ::`, `License ::`, `Programming Language ::`, `Operating System ::`.
- [ ] `classifiers` contains `License :: OSI Approved :: MIT License`.
- [ ] No entry in `classifiers` contains `Windows`.
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes.
- [ ] `uv lock --check` still passes (adding metadata fields must not touch `dependencies`).

## Tests to write first (TDD)
`tests/meta/test_pypi_metadata.py`:
- `test_keywords_and_classifiers_are_declared`: both keys exist and are non-empty lists of strings.
- `test_keywords_match_repository_profile_topics`: parse both TOML files with `tomllib`;
  assert `set(pyproject["project"]["keywords"]) == set(vibey_gh_toml["repository_profile"]["topics"])`.
  This is the regression guard against the two lists drifting apart (12.c).
- `test_classifiers_cover_every_required_family`: for each prefix in
  `("Development Status ::", "Intended Audience ::", "Topic ::", "License ::",
  "Programming Language ::", "Operating System ::")`, at least one classifier starts with it.
- `test_classifiers_include_the_declared_license`: `"License :: OSI Approved :: MIT License"` is present.
- `test_no_windows_classifier_since_windows_is_unsupported`: no classifier contains `"Windows"`
  (cites README.md's own "Windows is not a supported target" as the reason in the test docstring).
- `test_python_version_classifiers_do_not_outrun_ci`: parse `.github/workflows/ci.yml`'s `gates`
  job for its `uv python install X.Y` line (a simple regex is enough — this test does not need a
  YAML parser); assert every `Programming Language :: Python :: 3.N` classifier's `N` is `<=`
  the tested minor version.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    uv lock --check

## Out of scope
- Changing `.vibey-gh.toml`'s `[repository_profile] topics` list itself — this lane only reads it.
  Growing the keyword set is a separate decision made once, in that file, that this lane's
  regression test then keeps `pyproject.toml` honest against.
- `[project.urls]`, which is already complete (`Homepage`, `Documentation`, `"Research paper"`,
  `Book`, `Source`, `Issues`, `Changelog` are all present at `pyproject.toml:53-62`) — do not
  add, rename, or reorder these.
- Turning on the `repository-profile.yml` reconciliation workflow that would push GitHub's own
  repository topics/description to match `.vibey-gh.toml` — that is lane `seo-repo-profile-activation`.
- `README.md`, `docs/`, CHANGELOG.md, ADRs, and CLAUDE.md/AGENTS.md/GEMINI.md — other lanes in
  this same SEO/LEO wave, or (for CLAUDE.md/AGENTS.md/GEMINI.md's generated section) the
  provisioning system, not this lane.

Commit as `feat(pypi): declare keywords and classifiers in pyproject.toml`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
