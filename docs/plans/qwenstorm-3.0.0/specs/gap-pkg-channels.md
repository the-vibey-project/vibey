## Title
build(packaging): the release channels are declared in packaging/channels.toml, and a meta-test holds every declaration to the tree

## Why
Sub-doctrine 2.b (`src/vibey_tools/gh/docs/doctrines.md:30`): "a release is not finished when
the canonical index has the artifact; it is finished when every channel that carries the
project has it ... Every packaging definition lives in the repository as code ... The
packaging is honest about what the install does not include." Today no file says which
channels vibey is published to. PyPI, TestPyPI, the OCI artifact and the GitHub Release are
each implied by a workflow job (`.github/workflows/release.yml:99-113`, `:165-178`;
`release-surfaces.yml:97-160`; `github-release.yml:86-136`), and nothing else is declared
(`issue-audit/gaps.md` G3, lines 399-414).

This lane creates the registry that `gap-gh-release-channels-1` defined the format of,
declaring the four channels that already exist. Every later channel lane (`gap-release-*`,
`gap-pkg-*`) appends its own `[[channel]]` block. Sub-doctrine 7.b (`doctrines.md:80`)
requires every package listing to carry a direct path to the governance, and the meta-test
enforces that for every template a channel publishes.

## Required behaviour
1. New `packaging/channels.toml`. Line 1 is the provenance line (copy from
   `.github/workflows/release.yml:1`). Then a short comment block saying:
   - this is the declared list of release channels (sub-doctrine 2.b, ADR-0019);
   - `vibey-gh release-channels` publishes the channels whose publisher is not `workflow`;
   - `vibey-gh channel-lag` fails a release that a channel does not carry past its `grace_hours`;
   - credentials are secret NAMES; their values live only in repository or sovereign secrets.

   Then exactly this content:
   ```toml
   schema = 1
   repository = "the-vibey-project/vibey"
   governance_url = "https://the-vibey-project.github.io/vibey/main/governance/constitution/"
   governance_path = "src/vibey_tools/gh/docs/constitution.md"
   release_tag = "vibey-v{version}"
   release_url = "https://github.com/the-vibey-project/vibey/releases/download/vibey-v{version}"
   committer_name = "vibey[bot]"
   committer_email = "adam@matthewsteinberger.com"

   [[channel]]
   name = "pypi"
   ecosystem = "pypi"
   publisher = "workflow"
   workflow = ".github/workflows/release.yml"
   job = "pypi"
   branches = ["main"]
   definition = ["pyproject.toml", ".github/workflows/release.yml"]
   excludes = "PostgreSQL, Ollama and its model, and the vendor engine CLIs (Claude Code, Codex, Cursor, Antigravity); vibey doctor reports what is missing."
   grace_hours = 2
   probe = { url = "https://pypi.org/pypi/vibey/{version}/json" }
   enabled = true

   [[channel]]
   name = "testpypi"
   ecosystem = "pypi"
   publisher = "workflow"
   workflow = ".github/workflows/release.yml"
   job = "testpypi"
   branches = ["develop"]
   definition = ["pyproject.toml", ".github/workflows/release.yml"]
   excludes = "The rehearsal build, as vibey-dev: PostgreSQL, Ollama and its model, and the vendor engine CLIs are not included."
   grace_hours = 2
   probe = { url = "https://test.pypi.org/pypi/vibey-dev/{version}/json" }
   enabled = true

   [[channel]]
   name = "ghcr-python"
   ecosystem = "oci-artifact"
   publisher = "workflow"
   workflow = ".github/workflows/release-surfaces.yml"
   job = "package"
   branches = ["develop", "main"]
   definition = [".github/workflows/release-surfaces.yml"]
   excludes = "Only the wheel and the sdist as an OCI artifact, not a runnable image (that is the oci-image channel)."
   grace_hours = 2
   probe = { url = "https://ghcr.io/v2/the-vibey-project/vibey/python/manifests/{version}", accept = "application/vnd.oci.image.manifest.v1+json" }
   enabled = true

   [[channel]]
   name = "github-release"
   ecosystem = "github-release"
   publisher = "workflow"
   workflow = ".github/workflows/github-release.yml"
   job = "publish"
   branches = ["main"]
   definition = [".github/workflows/github-release.yml"]
   excludes = "Not an install: the tag and the release notes, the book and the paper; the executables are the single-file channel."
   grace_hours = 2
   probe = { url = "https://api.github.com/repos/the-vibey-project/vibey/releases/tags/vibey-v{version}", accept = "application/vnd.github+json" }
   enabled = true
   ```
2. New meta-test `tests/meta/test_packaging_channels.py` (provenance line 1, a docstring
   naming sub-doctrines 2.b and 7.b). It loads the file with
   `vibey_gh.channels.CHANNEL_REGISTRY_LOADER.load(REPO / "packaging/channels.toml")`, so the
   format is checked once, by the family's own loader (10.e). It then checks the tree:
   - `test_the_registry_loads_and_names_the_governance`: `governance_url` is exactly the URL
     above, and `REPO / governance_path` exists.
   - `test_the_registry_is_this_repositorys`: `repository` equals the path of
     `[project.urls] Source` in `pyproject.toml` (`https://github.com/the-vibey-project/vibey`
     gives `the-vibey-project/vibey`). `release_tag` equals `.vibey-gh.toml`
     `[github_release] tag_prefix` + `"{version}"`.
   - `test_every_definition_is_in_the_tree`: every path in every `definition` exists (2.b:
     "Every packaging definition lives in the repository as code").
   - `test_every_template_is_part_of_its_definition`: every template in `files` exists and is
     also listed in that channel's `definition`.
   - `test_every_file_under_packaging_is_declared`: every file under `packaging/` except
     `channels.toml` is in some channel's `definition`. Nothing is added that is not published.
   - `test_every_workflow_channel_names_a_real_job`: for `publisher == "workflow"`, the
     workflow file exists and `job` is a key of its `jobs` (`yaml.safe_load`).
   - `test_every_channel_publishes_from_a_declared_branch`: every `branches` entry is
     `.vibey-gh.toml` `[branches] integration` or `release`.
   - `test_every_published_template_carries_the_governance_and_what_is_not_included`: for
     each channel with `files`, the joined text of its templates contains `@GOVERNANCE_URL@`
     or the literal governance URL, and `@EXCLUDES@` or the literal `excludes` (7.b, 2.b).
   Every failure message names the channel and quotes the sub-doctrine it enforces.

## Where to change
- New `packaging/channels.toml`.
- New `tests/meta/test_packaging_channels.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta/test_packaging_channels.py` passes.
- [ ] Each test fails on a scratch edit, then the edit is reverted:
      - point one `definition` entry at a path that does not exist;
      - set `job = "nope"`;
      - add an empty file `packaging/orphan.txt`;
      - set `branches = ["trunk"]`.
- [ ] `python -c "import tomllib;tomllib.load(open('packaging/channels.toml','rb'))"` succeeds.

## Tests to write first (TDD)
`tests/meta/test_packaging_channels.py`, with the eight tests named in item 2.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- New channels: `gap-release-image-publish`, `gap-release-single-file-3` and the `gap-pkg-*` lanes each append their own block.
- Publishing and the lag check (`gap-gh-release-channels-*`, `gap-gh-channel-lag-*`).
- The README's install matrix and the governance link on the PyPI page (docs wave).

Commit as `build(packaging): declare the release channels in packaging/channels.toml`. Do not push.

## Lane card
- **Depends on:** `gap-gh-release-channels-1` (the loader and the format).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
