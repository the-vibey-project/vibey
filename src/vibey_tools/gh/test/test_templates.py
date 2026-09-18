# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The shipped templates are product, so they get tested like product.

A workflow template that does not parse installs cleanly and then fails in the consuming
repository, where GitHub reports it only as the file path with no log — which is a
miserable thing to debug from the other end. Cheaper to catch here.
"""

from __future__ import annotations

import dataclasses
import json
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

from vibey_gh.config import (
    DEFAULT_SCAN_WORKFLOWS,
    AiConfig,
    DocumentationConfig,
    GhConfig,
    load_config,
)
from vibey_gh.install import (
    FALLBACK_DISTRIBUTION,
    FALLBACK_INSTALL,
    TEMPLATES,
    WORKFLOWS,
    installed,
    render_workflow,
)

WORKFLOW_TEMPLATES = sorted(WORKFLOWS.glob("*.yml"))
REPO_WORKFLOWS = sorted(
    (Path(__file__).resolve().parent.parent / ".github/workflows").glob("*.yml")
)


def _workspace_workflows() -> list[Path]:
    """The monorepo root's own deployed copies, when this tenant is checked out inside it.

    vibey-gh ships as a standalone sdist too, where nothing above this tenant exists -- so
    this walks up looking for a `.github/workflows` that is not the tenant's own and
    returns nothing when there is none. That path matters: the file GitHub actually
    rejected was the workspace root's copy, rendered from this tenant's template with the
    ROOT repository's configuration, which substitutes longer values than the tenant's own.
    """
    tenant = Path(__file__).resolve().parent.parent
    for parent in tenant.parents:
        candidate = parent / ".github/workflows"
        if candidate.is_dir():
            return sorted(candidate.glob("*.yml"))
    return []


WORKSPACE_WORKFLOWS = _workspace_workflows()


@pytest.mark.parametrize("path", WORKFLOW_TEMPLATES, ids=lambda p: p.name)
def test_every_shipped_workflow_template_parses(path):
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert parsed.get("jobs")


def test_every_claude_json_schema_survives_argument_tokenization():
    """Read from the RENDERED templates, because that is what runs: the exact-head review's
    schema is a placeholder in the template, filled from `ReviewContract.json_schema()` at
    install time, so the raw file holds six schemas and a marker rather than seven."""
    schemas = []
    for path in WORKFLOW_TEMPLATES:
        rendered = render_workflow(path, GhConfig(root=Path(".")))
        for line in rendered.splitlines():
            if "--json-schema " not in line:
                continue
            tokens = shlex.split(line.strip())
            index = tokens.index("--json-schema")
            schema = json.loads(tokens[index + 1])
            assert schema["type"] == "object"
            assert schema["properties"]
            schemas.append((path.name, schema))
    assert len(schemas) == 7


def test_every_claude_tool_list_survives_argument_tokenization():
    """The sibling of the schema check above, and the one that was missing.

    `claude_args` is tokenized shell-style, so a permission spec containing a SPACE --
    `Bash(gh pr diff:*)` -- becomes three arguments unless the value is quoted. The
    runtime then receives `Bash(gh` as a rule, which is unbalanced, and fails while
    parsing its permissions: 490ms, one turn, no model usage, no cost, no structured
    output.

    Nothing in that failure names this line. The action reports only
    "--json-schema was provided but Claude did not return structured_output", which
    blames the flag on the NEXT line and is already quoted correctly. Meanwhile the gate
    posts its check-run against the head SHA, so the failure also surfaces on unrelated
    workflow runs that merely share that commit -- which is where it was eventually
    noticed, after every exact-head review on this repository had silently failed.

    The check above proved this repository already knew argument tokenization was the
    hazard here. It was simply never applied to the tool lists.
    """
    lists = []
    for path in WORKFLOW_TEMPLATES:
        for line in path.read_text(encoding="utf-8").splitlines():
            for flag in ("--allowedTools", "--disallowedTools"):
                if f"{flag} " not in line:
                    continue
                tokens = shlex.split(line.strip())
                index = tokens.index(flag)
                assert len(tokens) == index + 2, (
                    f"{path.name}: {flag} must tokenize to exactly one argument, but "
                    f"became {tokens[index + 1 :]} -- quote the value"
                )
                for spec in tokens[index + 1].split(","):
                    assert spec, f"{path.name}: {flag} has an empty entry"
                    assert spec == spec.strip(), f"{path.name}: padded entry {spec!r}"
                    # Bound to a local so neither formatter needs to wrap it: black and
                    # ruff format both run over this file and disagree about where to.
                    balanced = spec.count("(") == spec.count(")")
                    assert balanced, f"{path.name}: unbalanced rule {spec!r}"
                lists.append((path.name, flag))
    # Every template that drives Claude constrains it; losing one is a finding, not a diff.
    assert len(lists) == 10


# GitHub's cap on ONE expression. Any workflow scalar containing `${{ }}` -- a `run:`
# script, a `with:` input, an `env:` value -- is compiled as a SINGLE expression, so the
# whole scalar is what gets measured against this.
GITHUB_MAX_EXPRESSION_LENGTH = 21_000
# The budget this repository holds itself to, keeping 5,000 characters -- a quarter of the
# cap -- in reserve. Justified twice. First, the template is not what GitHub reads: the
# deployed copy is `render_workflow` output, and a consumer's configuration can render a
# `__VIBEY_GH_*__` placeholder far longer than the placeholder it replaced, so a scalar
# that fits here can still fail there. Second, the failure is invisible from the run (see
# below), so the guard has to fire in CI well before GitHub would. The reserve costs
# nothing: the largest interpolated scalar in the tree is under 10,000 characters.
RUN_SCALAR_BUDGET = 16_000
# A budget above the cap would guard nothing. Pinned so it cannot be raised through it.
assert RUN_SCALAR_BUDGET < GITHUB_MAX_EXPRESSION_LENGTH
EXPRESSION_MARKER = "${{"
_EXPRESSION = re.compile(r"\$\{\{(.*?)\}\}", re.DOTALL)


def _compiled_expression_length(scalar: str) -> int | None:
    """What GitHub measures: the scalar compiled to `format('...', ...)`, or None if plain.

    An interpolated scalar is not measured as written. GitHub splits it into literals and
    expressions and emits one `format()` call, and the literals are escaped on the way --
    every `{`, `}` and `'` doubles. On this repository's content that costs 1-4%, and it
    is not cosmetic: the commit that first bricked release-surfaces.yml carried a 20,786
    character scalar, comfortably under the cap, which compiled to 21,064 and was refused.
    Measuring the raw scalar would have passed it.
    """
    literals, expressions, last = [], [], 0
    for match in _EXPRESSION.finditer(scalar):
        literals.append(scalar[last : match.start()])
        expressions.append(match.group(1).strip())
        last = match.end()
    literals.append(scalar[last:])
    if not expressions:
        return None
    body = ""
    for index, literal in enumerate(literals):
        body += literal.replace("{", "{{").replace("}", "}}").replace("'", "''")
        if index < len(expressions):
            # A literal placeholder, not a format call: these braces stay single.
            body += "{" + str(index) + "}"
    arguments = "".join(", " + expression for expression in expressions)
    return len("format('" + body + "'" + arguments + ")")


def _interpolated_scalars(path: Path) -> list[tuple[str, str]]:
    """Every string a workflow may interpolate, labelled by its YAML path.

    ENUMERATING KEYS IS HOW THIS GUARD GOES BLIND, and it already did once. The first
    version visited four -- job `env`, and step `run`, `with` and `env` -- chosen because
    that is where the known problems lived, while describing itself as covering every
    interpolated string. release-surfaces.yml alone carries six expression-bearing fields
    it never reached: `jobs.*.outputs`, `jobs.*.name`, `jobs.*.concurrency` and
    `jobs.*.environment`. An oversized expression in any of them bricks the whole file the
    way the channel-restore script did, and the guard would have passed.

    So the document is walked. A field nobody thought of, or one GitHub adds next year, is
    covered the day it appears rather than the day someone remembers to extend a list.
    """
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    scalars: list[tuple[str, str]] = []

    def visit(value: object, where: str) -> None:
        if isinstance(value, str):
            scalars.append((where, value))
        elif isinstance(value, dict):
            for key, child in value.items():
                visit(child, f"{where}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{where}[{index}]")

    visit(parsed, path.name)
    return scalars


def test_the_scalar_sweep_reaches_fields_no_enumeration_listed():
    """The sweep must WALK the document, not visit a list of keys someone maintains.

    The walk is already here; what was missing is anything that keeps it. These four labels
    are real expression-bearing scalars in the shipped templates that the enumeration this
    replaced could not reach. Pinning them by path makes a regression to any hand-kept list
    fail here, rather than in GitHub's parser months later -- where it presents as a
    workflow named by file path, with no jobs and no logs.
    """
    labels = {label for path in WORKFLOW_TEMPLATES for label, _ in _interpolated_scalars(path)}
    for unreachable in (
        "conversation.yml.jobs.evaluate.outputs.state",
        "release-surfaces.yml.jobs.package.name",
        "release-surfaces.yml.jobs.docs.concurrency.group",
        "release-surfaces.yml.jobs.docs.environment.url",
    ):
        assert unreachable in labels, f"the sweep no longer reaches {unreachable}"


def test_no_interpolated_workflow_scalar_exceeds_githubs_expression_limit():
    """The third GitHub-side limit guarded here, and the one that bricked a whole file.

    A scalar containing `${{ }}` is not a string handed to bash or to an action. It is a
    template, compiled as a SINGLE expression, and one expression may not exceed 21,000
    characters. release-surfaces.yml's channel-restore step compiled to 21,599 -- from a
    21,315-character block scalar, 21,208 in the template -- and GitHub refused the entire
    file:

        Invalid workflow file
        .github/workflows/release-surfaces.yml
        (Line: 670, Col: 14): Exceeded max expression length 21000

    MIND THE UNIT, because two wrong ones are easy to reach for. Counting the raw file
    bytes with the YAML block indentation still attached reads 26,354, which over-counts by
    a quarter; counting the parsed scalar reads 21,315, which under-counts, because the
    literals are escaped into `format()` first. Only the compiled length is the number
    GitHub compares, which is why `_compiled_expression_length` builds it.

    PARSING PROVES NOTHING ABOUT THIS. The file was perfectly valid YAML the whole time --
    PyYAML loads it, `test_every_shipped_workflow_template_parses` passes, `installed()`
    reports no drift -- and it was still an invalid WORKFLOW. Neither does the run report
    it: an invalid workflow file produces a run named by FILE PATH, with no jobs and no
    retrievable logs, so it reads as "release-surfaces.yml is failing on every push" when
    in truth it never ran at all. The documentation site, the book, the paper and the OCI
    bundle went unpublished behind exactly that misreading.

    Two ways to satisfy this: split the step, or move the expressions into the step's
    `env:` and read them as ordinary shell variables. The second is the better fix where it
    applies -- with no inline `${{ }}` the scalar is not a template and the cap stops
    applying at all, which is why `Build the channel site with ProperDocs` may sit at
    21,958 characters and break nothing. That exemption is not an assumption. Run
    35158652570 (develop @ d7fadd1e, 2026-09-16T22:38:28Z) is a real run with real jobs
    from a file carrying that same 21,958-character expression-free block, 958 over the
    cap; the very next commit pushed the interpolated restore step to 21,064 compiled, 64
    over, and every run from there on was named by file path instead. The cap tracks the
    marker, not the length, so this test does too.

    Splitting has its own hazard, which no length check can see. Each `run:` is a separate
    shell, so a variable assigned in one step is the empty string in the next. Anything a
    later step needs must cross through `env:` or `$GITHUB_ENV`; files under the workspace
    cross by themselves.
    """
    # The templates are the source of truth. This tenant's deployed copies and the
    # workspace root's are what GitHub actually reads, and rendering changes their length,
    # so a render is never assumed to be the template's size. Sweep all three -- the file
    # GitHub named in the rejection was the workspace root's.
    sources = {
        "templates": WORKFLOW_TEMPLATES,
        "tenant": REPO_WORKFLOWS,
        "workspace": WORKSPACE_WORKFLOWS,
    }
    swept = {name: 0 for name in sources}
    checked = {name: 0 for name in sources}
    for name, paths in sources.items():
        for path in paths:
            for where, scalar in _interpolated_scalars(path):
                swept[name] += 1
                if EXPRESSION_MARKER not in scalar:
                    continue
                size = _compiled_expression_length(scalar)
                assert size is not None, f"{where}: unbalanced {EXPRESSION_MARKER}"
                checked[name] += 1
                detail = (
                    f"{where}: compiles to {size} characters because the scalar contains "
                    f"{EXPRESSION_MARKER}, so GitHub evaluates the whole of it as one "
                    f"expression and rejects the file above "
                    f"{GITHUB_MAX_EXPRESSION_LENGTH}; the budget here is "
                    f"{RUN_SCALAR_BUDGET}. Split the step, or move its expressions into "
                    f"the step's env: block."
                )
                assert size <= RUN_SCALAR_BUDGET, detail
    # Floors, not pins: adding a step should not mean editing this test, but a sweep that
    # silently measured nothing has to fail rather than pass. Both halves are floored,
    # because `swept` counts scalars the marker filter then skips -- a mistyped marker
    # would leave `checked` at zero while `swept` stayed healthy, which is the exact
    # silent no-op these floors exist to catch. The workspace list is empty in a
    # standalone sdist checkout, so it is floored only when it resolved to something.
    assert swept["templates"] > 900, swept
    assert checked["templates"] > 300, checked
    assert swept["tenant"] > 900, swept
    assert checked["tenant"] > 300, checked
    if WORKSPACE_WORKFLOWS:
        assert swept["workspace"] > 250, swept
        assert checked["workspace"] > 150, checked


@pytest.mark.parametrize("path", REPO_WORKFLOWS, ids=lambda p: p.name)
def test_this_repository_s_own_workflows_parse(path):
    """Dogfooding: the tool's own CI is subject to the rule it enforces elsewhere."""
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    assert parsed.get("jobs")


def test_release_environments_are_disjoint_by_branch():
    """main must never request TestPyPI, whose environment permits only develop."""
    release = yaml.safe_load(
        (Path(__file__).resolve().parent.parent / ".github/workflows/release.yml").read_text(
            encoding="utf-8"
        )
    )
    jobs = release["jobs"]
    assert jobs["testpypi"]["if"] == "github.ref == 'refs/heads/develop'"
    assert jobs["testpypi"]["environment"] == "testpypi"
    assert jobs["testpypi"]["needs"] == "build"
    assert jobs["pypi"]["if"] == "github.ref == 'refs/heads/main'"
    assert jobs["pypi"]["environment"] == "pypi"
    assert jobs["pypi"]["needs"] == "build"
    assert "verify" not in jobs


def test_release_surfaces_preserve_both_docs_channels_and_publish_oci_packages():
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    assert 'workflows: ["Release"]' in render_workflow(
        WORKFLOWS / "release-surfaces.yml", GhConfig(root=Path("."))
    )
    assert "github.event.workflow_run.conclusion == 'success'" in text
    assert "channel=develop" in text and "channel=main" in text
    assert "pages/${CHANNEL}" in text
    assert "pages/${OTHER_CHANNEL}" in text
    assert "while read -r other_run" in text
    assert '--name "docs-${OTHER_CHANNEL}"' in text
    assert "docs-${OTHER_CHANNEL}" in text
    # Both the version and any extra site packages are rendered from configuration, so the
    # template carries placeholders rather than a pinned literal.
    assert "properdocs==__VIBEY_GH_PROPERDOCS_VERSION__" in text
    assert "properdocs-theme-mkdocs==__VIBEY_GH_PROPERDOCS_VERSION__" in text
    assert "__VIBEY_GH_DOC_SITE_REQUIREMENTS__" in text
    assert "packages: write" in text
    assert "ghcr.io/${GITHUB_REPOSITORY,,}/python" in text
    assert "application/vnd.pypi.project.release.v1" in text
    assert 'oras tag "${package}:${VERSION}" "$CHANNEL" "sha-${RELEASE_SHA}"' in text
    assert 'oras tag "${package}:${VERSION}" latest' in text
    assert "--delete" not in text
    assert "Build boldly." in text
    assert "prefers-reduced-motion" in text
    assert "Documentation channels" in text
    assert "color-scheme: dark" in text
    assert "__REPOSITORY_NAME__" in text
    assert "__REPOSITORY_URL__" in text
    assert "__RELEASE_SHA__" in text
    assert "vibey-gh:repository" in text
    assert "managed release theme is missing" in text
    assert "Made with ❤️ by" in text
    assert "https://the-vibey-project.github.io/vibey/" in text
    assert "https://vibewithadam.matthewsteinberger.com" in text
    assert "pages/robots.txt" in text
    assert "pages/sitemap.xml" in text
    assert "pages/llms.txt" in text and "pages/llms-full.txt" in text
    assert 'rel="canonical"' in text
    assert "application/ld+json" in text
    assert "noindex,nofollow" in text


def test_release_surfaces_google_analytics_is_generic_and_off_by_default(tmp_path: Path):
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    assert "__VIBEY_GH_DOC_GOOGLE_ANALYTICS_ID__" in text
    assert "googletagmanager.com/gtag/js" in text
    assert "__GA_SNIPPET__" in text
    # An explicitly-default config, NOT load_config(): that read this repository's own
    # .vibey-gh.toml, so the assertion silently tested repo state rather than the default
    # — and broke the day the repo legitimately configured its own analytics id.
    disabled = render_workflow(WORKFLOWS / "release-surfaces.yml", GhConfig(root=tmp_path))
    assert "__VIBEY_GH_DOC_GOOGLE_ANALYTICS_ID__" not in disabled
    assert 'GA_ID=""' in disabled
    enabled = render_workflow(
        WORKFLOWS / "release-surfaces.yml",
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(google_analytics_id="G-ABC1234567"),
        ),
    )
    assert 'GA_ID="G-ABC1234567"' in enabled


def test_release_surfaces_installs_the_packages_the_site_actually_declares(tmp_path: Path):
    """ProperDocs depends on none of the plugins a real site configures.

    The install line named exactly `properdocs` and its theme, with no way to extend it, so
    a repository whose `properdocs.yml` declared `mkdocs-gen-files` or `pymdownx.*` failed
    `--strict` on the first one it met — the packages are simply absent. A site's
    dependencies follow from its own configuration, so they can only be the adopter's to
    declare.
    """
    rendered = render_workflow(
        WORKFLOWS / "release-surfaces.yml",
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(
                site_requirements=(
                    "mkdocs-gen-files",
                    "pymdown-extensions>=10.7",
                    "mkdocs-material[imaging] >= 9.5",
                ),
                properdocs_version="1.7.0",
            ),
        ),
    )
    assert "__VIBEY_GH" not in rendered
    assert "'properdocs==1.7.0'" in rendered
    assert "mkdocs-gen-files" in rendered
    # Quoted, so a specifier carrying spaces or brackets stays one argument to pip rather
    # than splitting into three or being read as a glob.
    assert shlex.quote("mkdocs-material[imaging] >= 9.5") in rendered
    assert shlex.quote("pymdown-extensions>=10.7") in rendered
    install_line = next(line for line in rendered.split("\n") if "mkdocs-material[imaging]" in line)
    assert shlex.split(install_line) == [
        "properdocs==1.7.0",
        "properdocs-theme-mkdocs==1.7.0",
        "mkdocs-gen-files",
        "pymdown-extensions>=10.7",
        "mkdocs-material[imaging] >= 9.5",
    ]


def test_release_surfaces_adds_nothing_to_the_install_by_default(tmp_path: Path):
    """The default must stay a no-op: an adopter declaring nothing installs nothing extra."""
    rendered = render_workflow(WORKFLOWS / "release-surfaces.yml", GhConfig(root=tmp_path))
    assert "__VIBEY_GH" not in rendered
    assert "'properdocs==1.6.7'" in rendered
    # The requirements-file hook is guarded by its own existence check, so a repository
    # without one runs an install of exactly the two packages and nothing else.
    assert 'if [ -n "docs/requirements.txt" ]' in rendered
    assert '[ -f "docs/requirements.txt" ]' in rendered


def test_documentation_workflow_authors_guarded_refresh_prs():
    text = (WORKFLOWS / "documentation.yml").read_text(encoding="utf-8")
    assert "name: Docs" in text
    assert "vibey-gh check --ci" in text
    assert "anthropics/claude-code-action@a874e9ecd7bb36efdad65429c6b35815f5a08f10" in text
    assert "This is an authoring" in text
    assert "--allowedTools Read,Glob,Grep,Edit,Write" in text
    assert 'branch="vibey-gh/docs/refresh-${RUN_ID}"' in text
    assert 'git push origin "HEAD:refs/heads/${BRANCH}"' in text
    assert "gh pr create" in text
    assert ".complete == true" in text
    assert "gaps_remaining // []" in text
    assert "gh pr create" in text and '--body "$body" || true' not in text
    assert "Never execute repository code" in text
    assert "git push --delete" not in text
    assert "--force" not in text


def test_pr_gate_requires_exact_head_semantic_documentation_review_for_every_author():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "Exact-head code and documentation review" in text
    assert "needs.evaluate.outputs.state == 'ready'" in text
    assert "repository-wide semantic documentation audit" in text
    assert "complete, approachable guide" in text
    assert "--disallowedTools Agent" in text
    assert "Bash(gh pr diff:*)" in text
    assert "Bash(gh:pr:diff:*)" not in text


def test_the_five_surface_self_test_is_this_project_s_own_and_ships_to_nobody():
    """`api-drift.yml` tests vibey-gh, so it is hand-authored here and shipped to no one.

    It ran `from vibey_gh.surfaces import …` and asserted *this* project's capability
    registry — while being installed into every adopting repository as a managed workflow
    and named in the default `scan_workflows`. An adopter got a required-looking gate that
    tested a library rather than their product, and had to work out for themselves that it
    should come back out. `ci.yml` and `release.yml` set the precedent: what is specific to
    one repository is that repository's to author.
    """
    assert not (WORKFLOWS / "api-drift.yml").exists()
    assert "API drift (Cloud Agents OpenAPI)" not in DEFAULT_SCAN_WORKFLOWS
    drift = Path(__file__).resolve().parent.parent / ".github/workflows/api-drift.yml"
    assert drift.is_file(), "this repository still needs its own five-surface self-test"
    text = drift.read_text(encoding="utf-8")
    assert "name: API drift (Cloud Agents OpenAPI)" in text
    assert "MCP, API, CLI, SDK, and webhook parity" in text
    assert "from vibey_gh.surfaces import CAPABILITIES, SURFACES, parity" in text
    assert "if tuple(actual) != expected_capabilities:" in text
    assert "if tuple(surfaces) != expected_surfaces" in text
    assert "if tuple(actual) != tuple(SURFACES):" not in text


def test_security_and_api_drift_workflows_are_real_managed_gates():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    codeql = (WORKFLOWS / "codeql.yml").read_text(encoding="utf-8")
    assert "name: CodeQL" in codeql
    assert "github/codeql-action/init@6d786de4d6f3531a740e445b53a42b622bbbace8" in codeql
    assert "github/codeql-action/analyze@6d786de4d6f3531a740e445b53a42b622bbbace8" in codeql
    assert "Do not spawn subagents" in text
    assert text.count("GH_REPO: ${{ github.repository }}") >= 2
    assert "isolated temporary" in text
    assert text.count("Create credential-free Claude git context") == 3
    assert text.count("Remove credential-free Claude git context") == 3
    assert (
        text.count('git remote add origin "https://github.com/${{ github.repository }}.git"') == 3
    )
    assert text.count('allowed_non_write_users: "__vibey_gh_no_nonwrite_users__"') == 3
    assert text.count("persist-credentials: false") >= 3
    assert "gitdir: $GITHUB_WORKSPACE/target/.git" not in text
    assert "TRUSTED: ${{ needs.evaluate.outputs.trusted }}" not in text
    assert '[ "$STATE" = ready ] || [ "$STATE" = review ]' in text
    # Only an explicit `true` verdict may pass the gate; every other value, including
    # the empty string a failed review job leaves behind, fails closed.
    assert re.search(r'case "\$REVIEW_PASSED" in\n\s+true\)\n\s+conclusion=success\n', text)
    assert "full_claude_output:" in text
    assert "Validate diagnostic output policy" in text
    assert "github.event.repository.visibility == 'private'" in text
    assert text.count("track_progress: ${{ __VIBEY_GH_SANITIZED_PROGRESS__ &&") == 3
    assert text.count("github.event_name == 'pull_request_review'") == 3
    assert "github.event_name == 'workflow_dispatch') }}" not in text
    assert text.count("show_full_output:") == 3
    assert text.count("__VIBEY_GH_ALLOW_PRIVATE_FULL_OUTPUT__") == 4
    assert text.count("__VIBEY_GH_ARCHIVE_EXECUTION_FILE__") == 3
    assert "Full Claude output is disabled or unsafe" in text
    assert "Collect exact-head failed-check evidence" in text
    assert "repos/${REPO}/commits/${HEAD_SHA}/check-runs" in text
    assert "diagnostics/failed-checks.txt" in text
    assert "--log-failed" in text
    assert "diagnostic bundle truncated at 200000 bytes" in text
    assert "Read that file before" in text
    # The schema is rendered from the review contract at install time, so the quoted field
    # names are looked for where they actually appear; the jq that aggregates them is not.
    rendered = render_workflow(WORKFLOWS / "pr-automation.yml", GhConfig(root=Path(".")))
    for field in (
        "complete",
        "accurate",
        "human_readable",
        "opening_accessible",
        "opening_bluf",
        "audience_order",
        "architecture_diagram_complete",
        "all_capabilities_documented",
        "all_commands_documented",
        "all_configuration_documented",
        "examples_sufficient",
        "onboarding_sufficient",
        "operations_sufficient",
        "security_sufficient",
        "release_process_sufficient",
        "links_valid",
    ):
        assert f'"{field}"' in rendered
        assert f".{field} == true" in text
    assert "((.findings // []) | length == 0)" in text
    assert "Exact-head semantic review result:" in text
    # Only an explicit `true` verdict may pass the gate; every other value, including
    # the empty string a failed review job leaves behind, fails closed.
    assert re.search(r'case "\$REVIEW_PASSED" in\n\s+true\)\n\s+conclusion=success\n', text)


def test_a_workflow_scope_rejection_is_named_not_buried():
    """Observed on three pin-bump PRs at once: the repair committed cleanly, the push
    was rejected because the automation token lacked the Workflows permission, and the
    only trace was one line in a log nobody reads while the PR silently stopped
    advancing (#172). The template must warn before the doomed push and, on the
    rejection, say the operator-actionable sentence in the error and the job summary."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "this repair edits .github/workflows/**" in text
    assert "Workflows (read-write) permission" in text
    assert "the repair itself succeeded" in text
    assert "grep -q '^\\.github/workflows/'" in text
    # the summary line reaches the operator surface, not just stderr
    assert text.count("GITHUB_STEP_SUMMARY") >= 1


def test_bot_initiated_chains_may_invoke_the_ai_steps():
    """Observed on qwenloop#13: the conflict-resolve job, reached through a
    workflow_run chain that CI's completion initiated, was refused wholesale --
    "Workflow initiated by non-human actor: github-actions" -- because the action
    gates bot actors behind an explicit allowlist. Every AI call site must name the
    platform's own actor, and ONLY that actor: "*" would extend the trust to
    arbitrary third-party bots."""
    for name in ("pr-automation.yml", "issue-automation.yml", "conversation.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        uses = text.count("anthropics/claude-code-action@")
        allowed = text.count('allowed_bots: "github-actions,github-actions[bot]"')
        assert uses == allowed, f"{name}: {uses} AI call sites, {allowed} allowed_bots"
        assert 'allowed_bots: "*"' not in text


def test_recovery_reprobes_parked_prs_on_a_schedule_without_burning_budget():
    """The auto-heal engine (#206): parked pull requests — an infra-failed gate
    (review incomplete, operator block) or no gate on the current head — get their
    evaluation re-dispatched every two hours, so the first pass after credits return
    simply succeeds. A gate red with REAL review findings is excluded: repair owns
    that path, and re-probing an unchanged head every cycle would burn the bounded
    repair budget on nothing new. The observed alternative was tonight's: five pull
    requests parked for hours with a human re-dispatching by hand."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    # The cadence is injected by install.py at the __VIBEY_GH_SCHEDULE__ placeholder —
    # never hardcoded in the template. A literal block alongside the placeholder gives
    # a rendered repository TWO `schedule:` keys under `on:`, which fails Actions'
    # YAML parse and silently unlists the whole workflow: no evaluation, no gate,
    # every pull request hard-blocked. Exactly the outage vibey-gh itself hit on
    # 2026-08-29.
    assert "\n  schedule:" not in text, "cadence must come from the placeholder only"
    assert "# __VIBEY_GH_SCHEDULE__" in text
    assert "if: github.event_name == 'schedule'" in text
    assert "if: github.event_name != 'schedule'" in text, "the pipeline must not run on schedule"
    flat = " ".join(text.split())
    assert "review incomplete" in flat and "no gate on the current head" in flat
    assert "burn the bounded repair budget on nothing new" in flat
    # findings-red gates fall through to `continue`, never a dispatch
    assert flat.count("gh workflow run pr-automation.yml") >= 1


def test_rendered_pr_automation_carries_exactly_one_schedule_key(tmp_path):
    """Render with the backstop on: exactly one `schedule:` under `on:`, at the
    auto-heal cadence. Render with it off: none at all. Two keys is not a style
    problem — Actions refuses to parse the file and the workflow disappears from
    the repository, taking the required gate with it."""
    on = render_workflow(WORKFLOWS / "pr-automation.yml", GhConfig(root=tmp_path))
    assert on.count("\n  schedule:") == 1
    assert 'cron: "37 */2 * * *"' in on
    assert "47 */6" not in on
    base = GhConfig(root=tmp_path)
    cfg = dataclasses.replace(
        base, pr_automation=dataclasses.replace(base.pr_automation, retain_schedule_backstop=False)
    )
    off = render_workflow(WORKFLOWS / "pr-automation.yml", cfg)
    assert "\n  schedule:" not in off
    assert "schedule backstop disabled by .vibey-gh.toml" in off


def test_review_prompt_enforces_the_government_channel():
    """Sub-doctrine 2.a: everything assigned to industry or executives is also
    created for governments — the review judges channel parity on every head."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "Enforce the government channel (sub-doctrine 2.a)" in flat
    assert "a government edition stands beside it" in flat
    assert "its primary emphasis is the government's military arm" in flat


def test_every_workflow_name_is_configurable_and_renders_consistently(tmp_path):
    """A `workflow_run` trigger matches on a workflow's display NAME. Hardcoding
    those names assumed every adopter calls its pipeline "CI" and its publish step
    "Release" — vibey-bootstrap calls its pipeline "CI/CD Pipeline", so the trigger
    never matched, its channel site never deployed, and its Pages URL served a
    fossil, silently, because a trigger that never matches simply never runs."""
    import dataclasses

    from vibey_gh.config import WorkflowNamesConfig

    base = GhConfig(root=tmp_path)
    for name in sorted(p.name for p in WORKFLOWS.glob("*.yml")):
        rendered = render_workflow(WORKFLOWS / name, base)
        assert "__VIBEY_GH_WF_" not in rendered, f"{name} left a name unrendered"

    renamed = dataclasses.replace(
        base,
        workflow_names=WorkflowNamesConfig(
            ci="CI/CD Pipeline", release="Publish", merge_train="Train"
        ),
    )
    surfaces = render_workflow(WORKFLOWS / "release-surfaces.yml", renamed)
    assert 'workflows: ["Publish"]' in surfaces
    repair = render_workflow(WORKFLOWS / "release-repair.yml", renamed)
    assert "CI/CD Pipeline" in repair and "Publish" in repair
    # A template's own name and the triggers watching it move together.
    train = render_workflow(WORKFLOWS / "merge-train.yml", renamed)
    promote = render_workflow(WORKFLOWS / "promote-to-main.yml", renamed)
    assert "name: Train" in train
    assert 'workflows: ["Train"]' in promote


def test_workflow_names_load_from_toml(tmp_path):
    from vibey_gh.config import load_config

    (tmp_path / ".vibey-gh.toml").write_text(
        '[workflow_names]\nci = "CI/CD Pipeline"\nrelease = "Publish"\n', encoding="utf-8"
    )
    names = load_config(tmp_path).workflow_names
    assert names.ci == "CI/CD Pipeline" and names.release == "Publish"
    assert names.provenance == "Provenance"  # unnamed fields keep their defaults
    (tmp_path / ".vibey-gh.toml").write_text("", encoding="utf-8")
    assert load_config(tmp_path).workflow_names.ci == "CI"


def test_release_surfaces_ships_the_corpus_index():
    """#249: the governance corpus index rides the channel site, so a fully-local
    deployment carries its law searchable and integrity-checkable offline."""
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert 'cp "__VIBEY_GH_DOC_CORPUS_INDEX__" channel-site/corpus-index.json' in flat
    # After the build, which cleans the site directory: copied before it, the index was
    # deleted again (or the copy failed outright, the directory not yet existing).
    assert flat.index("channel-site/corpus-index.json") > flat.index("properdocs build --strict")


def test_only_the_tooling_repository_self_hosts_the_install():
    """#242's root cause: the self-hosting grep matched vibey-bootstrap too, so an
    ADOPTER installed itself instead of the pinned tool — its floating vibey-gh
    dependency then supplied a checker NEWER than its renders, and 'out of date'
    phantoms followed. Exactly one repository provides the tooling."""
    for name in (
        "provenance.yml",
        "promote-to-main.yml",
        "merge-train.yml",
        "conventional-commits.yml",
        "github-release.yml",
        "release-surfaces.yml",
    ):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "vibey-(gh|bootstrap)" not in text, name
        if "installing from source" in text:
            assert 'name = "vibey-gh"' in text, name


def test_review_prompt_enforces_the_clean_repo():
    """Sub-doctrine 9.a: technical clutter blocks; human messiness is expressly
    welcome and never a finding."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "Enforce the clean repo (sub-doctrine 9.a)" in flat
    assert "Human messiness is expressly welcome and never a finding" in flat


def test_review_prompt_enforces_the_social_signals_oath():
    """Sub-doctrine 4.a: rendered social proof is attested human speech or it blocks —
    machine-manufactured testimony is false witness."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "Enforce the social-signals oath (sub-doctrine 4.a)" in flat
    assert "machine-authored, synthetic, unattributed, or unverifiable is FALSE WITNESS" in flat


def test_review_prompt_enforces_unwind_immunity_with_the_minyan_of_ten():
    """Article IV.5-6: no unwind may degrade the ratified governance corpus, and only
    ten or more named humans — a minyan — can approve an exception; machine
    approvals are worthless toward the quorum. The review is the enforcement
    surface, so the prompt must state the rule, the quorum, and the not-an-unwind
    carve-out."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "Enforce unwind immunity (Article IV.5-6)" in flat
    assert "no fewer than TEN named humans — a minyan" in flat
    assert "Machine approvals count for nothing" in flat
    assert "A pure addition or a strengthening rewrite is not an unwind" in flat


def test_review_prompt_judges_the_living_roadmap():
    """#211: the exact-head review owns roadmap LIVENESS — presence is the
    deterministic contract's job. The prompt must demand an existing roadmap that
    matches the repository's real trajectory, and must reserve 'done' for humans."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    assert "Verify the living roadmap under complete" in flat
    assert "docs/roadmap.md or ROADMAP.md" in flat
    assert "stale against CHANGELOG.md or the release history" in flat
    assert "A machine never declares a project done" in flat


def test_readability_gate_judges_the_opening_and_the_audience_order():
    """The three copy-doctrine judgments: the first screens of README.md and the docs
    landing page must survive a reader with zero project context (opening_accessible)
    and state the problem before any project vocabulary (opening_bluf), and the README
    plus the published documentation suite — landing page and nav order included — must
    serve beginners first, then engineers, then scholars, with executive framing
    essentially absent (audience_order). Each is a required schema boolean the jq
    aggregation folds into `.pass`, so a reviewer cannot skip a judgment and still pass
    the gate. Phrases are asserted against wrap-normalized text: the prompt is prose and
    its line breaks are not part of the contract."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    flat = " ".join(text.split())
    for phrase in (
        "as if you had never seen this repository",
        "BEFORE any project vocabulary",
        "opens with what it IS before what it FIXES fails",
        "and so does a marketing tagline",
        # The document arc: BLUF, zero-code beginner, the engineering ladder,
        # maximal-density theory, BLUF reprise + call to action.
        "NEVER written a single line of code",
        "the floor is zero programming context",
        "junior, mid, senior, staff, senior staff, principal, senior staff principal, CTO",
        "Ivy-league coursework register",
        "proofs or proof sketches, citations",
        "restatement of the BLUF followed by a call to action",
        "skips the zero-code rung, climbs out of order, thins the theory",
        "never a sales pitch",
        "essentially absent",
        # The never-lost reader: no orientation gaps, no external lookups, and the
        # absolute priority order — human first, AI second, business last if at all.
        "the never-lost contract",
        "across EVERY FORM of documentation this repository ships",
        "docstrings, CLI --help text, error and log messages",
        "needing their own chat, a dictionary, or a web search",
        "defined at first use IN THAT DOCUMENT",
        "HUMAN\n            reader is served first, always; the AI reader second".replace(
            "\n            ", " "
        ),
        "never contorted for machine",
        "industry or business needs come absolutely last, if at all",
        # Hyperlinks are first-class: outside material is clickable at the point of
        # reference, never only from a distant references section.
        "Hyperlinks are a first-class citizen",
        "ALONGSIDE the referencing copy",
        "not only in a references section",
        # The judgments cover the published site, not just README.md: the landing
        # page's first screen and the nav order are inside the contract, because the
        # site is where a beginner actually lands.
        "documentation site's landing page",
        "nav order declared in the site configuration",
        "engineering reference before the beginner on-ramp fails",
        # The examples doctrine: every exposed platform surface gets at least one
        # fully working, fully comprehensible example, verified against the source.
        "Judge examples_sufficient against every platform surface",
        "API, CLI, MCP, webhook, SDK, and Moltbook where present",
        "copy-paste-runnable against this exact head",
        "example naming anything that does not exist fails this judgment",
    ):
        assert phrase in flat, phrase
    # The judgments gate `.pass` in the aggregation, not just the schema.
    for field in ("opening_accessible", "opening_bluf", "audience_order"):
        assert f".{field} == true" in text
    # The local fallback never asserts them: a diff-only model has no basis to certify a
    # README's opening, so they are reported unevaluated instead.
    from vibey_gh import local_review

    for field in ("opening_accessible", "opening_bluf", "audience_order"):
        assert field in local_review.UNEVALUATED_FIELDS
        assert field not in local_review.REVIEW_SCHEMA["properties"]


def test_the_site_publishes_its_own_book_and_paper_when_enabled(tmp_path):
    """The doctrine's end results belong on the docs site itself — a reader downloads
    /book.epub and /paper.pdf from the documentation they mirror, not from a release
    page. Off by default; the TeX engine is one pinned, checksummed binary because a
    full TeX Live costs minutes per deploy for one PDF."""
    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    off = render_workflow(source, GhConfig(root=tmp_path))
    assert '[ "false" = "true" ]' in off or "__VIBEY_GH_DOC_BOOK__" not in off

    on = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(generate_book=True, generate_paper=True),
        ),
    )
    assert "vibey-gh book --site-dir channel-site" in on
    # The exporters must be installed before they are invoked: the build step's venv
    # holds only ProperDocs, and the first dogfooded deploy failed with exit 127.
    assert on.index('pip install --quiet -e "$self"') < on.index("vibey-gh book --site-dir")
    assert "cp book-out/book.epub channel-site/book.epub" in on
    # The finished KDP interior: one headless-Chromium print of the 6x9 print HTML.
    # Soft-fails to the print HTML rather than killing a docs deploy over one artifact.
    assert '--print-to-pdf="$PWD/book-out/book.pdf"' in on
    assert "--no-pdf-header-footer" in on
    assert "book.pdf was not produced" in on
    assert "vibey-gh paper --author" in on
    assert "cp paper-out/paper.pdf channel-site/paper.pdf" in on
    # The engine is pinned by version AND checksum, and verification precedes use.
    assert "tectonic%400.15.0" in on
    assert "875fbbc9ab48560d7776088c608e0beee49197b57ab4a2f6c5385b2c661c842f" in on
    assert on.index("sha256sum -c") < on.index("tar -xzf /tmp/tectonic.tar.gz")


def test_the_book_and_the_paper_are_findable_on_every_published_surface(tmp_path):
    """The two end results of the documentation doctrine must be as easy to find as the
    documentation itself: linked from every page's navigation and footer, from the
    channel chooser, from the LLM-facing index, and kept as immutable assets on the
    GitHub Release for that exact version. Every link is rendered from what the deploy
    actually produced -- file presence in the built site -- never from configuration, so
    a page can never link a PDF that was not built."""
    from vibey_gh.config import DocumentationConfig, GhConfig, GithubReleaseConfig
    from vibey_gh.install import SOURCE_RELEASE_ASSETS, render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    on = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(generate_book=True, generate_paper=True),
        ),
    )
    # Every page: the theme script learns which forms exist from the built site.
    assert '"paper_pdf": (site / "paper.pdf").is_file()' in on
    assert '"book_epub": (site / "book.epub").is_file()' in on
    assert 'replace("__DOC_SURFACES__", encoded)' in on
    script = (SOURCE_RELEASE_ASSETS / "javascripts" / "channel.js").read_text(encoding="utf-8")
    assert "'__DOC_SURFACES__'" in script
    # An unsubstituted placeholder must degrade to "nothing to show", never a syntax error.
    assert 'surfacesRaw.startsWith("{") ? JSON.parse(surfacesRaw) : {}' in script
    assert 'className = "nav-link surface-link"' in script
    assert 'className = "release-surfaces"' in script
    # The channel chooser: a section filled per channel from pages/<channel>/.
    assert "__SURFACES_HTML__" in on
    assert 'aria-label="Read it offline"' in on
    assert "(base / file).is_file()" in on
    # The LLM-facing index, only where the files exist.
    assert "[ -f pages/main/paper.pdf ] && SURFACE_LINES=" in on
    assert "${SURFACE_LINES}- Provenance:" in on
    # Every book format that can be produced is listed, not a subset.
    for produced in ("book.pdf", "book.epub", "book-print.html", "paper/index.html"):
        assert f"[ -f pages/main/{produced} ] && SURFACE_LINES=" in on, produced
    # Immutable copies: an attach job, and the only job allowed to write contents.
    parsed = yaml.safe_load(on)
    attach = parsed["jobs"]["attach"]
    assert attach["needs"] == ["context", "package", "docs"]
    assert attach["permissions"] == {"actions": "read", "contents": "write"}
    assert "true && (true || true) && needs.context.outputs.branch == 'main'" in attach["if"]
    for name, job in parsed["jobs"].items():
        if name != "attach":
            assert job.get("permissions", {}).get("contents") != "write", name
    assert (
        parsed["jobs"]["package"]["outputs"]["version"] == "${{ steps.metadata.outputs.version }}"
    )
    assert "TAG: v${{ needs.package.outputs.version }}" in on
    assert 'gh release upload "$TAG" "${present[@]}" --clobber' in on
    # It waits a bounded while for the Release rather than assuming an order, and a
    # missing Release is a warning, not a failed docs deploy.
    assert "no GitHub Release $TAG appeared within 10 minutes" in on

    # GitHub Releases off, or a different tag prefix: the gate and the tag follow.
    off = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            github_release=GithubReleaseConfig(enabled=False, tag_prefix="release-"),
        ),
    )
    off_attach = yaml.safe_load(off)["jobs"]["attach"]
    assert off_attach["if"].startswith("false &&")
    assert "TAG: release-${{ needs.package.outputs.version }}" in off


def test_a_manual_release_must_prove_its_commit_and_never_runs_its_code(tmp_path):
    """A dispatcher chooses the target SHA. Nothing with write access may run until that
    SHA is proven to be on the release branch with a successful release run for exactly
    that commit, and even then the code executed is the protected release branch's
    tooling -- the target is only ever read as data."""
    from vibey_gh.config import GhConfig
    from vibey_gh.install import render_workflow

    rendered = render_workflow(WORKFLOWS / "github-release.yml", GhConfig(root=tmp_path))
    parsed = yaml.safe_load(rendered)
    assert parsed["permissions"] == {"contents": "read"}
    verify, publish = parsed["jobs"]["verify"], parsed["jobs"]["publish"]
    assert verify["permissions"] == {"actions": "read", "contents": "read"}
    assert publish["permissions"] == {"contents": "write"}
    assert publish["needs"] == "verify"
    assert "if" not in publish, "publish must not be reachable except through verify"
    prove = verify["steps"][0]["run"]
    assert "grep -qE '^[0-9a-f]{40}$'" in prove
    assert "compare/${target}...${RELEASE_BRANCH}" in prove
    assert "identical|ahead) ;;" in prove
    assert '--commit "$target" --status success' in prove
    assert verify["steps"][0]["env"]["RELEASE_WORKFLOW"] == "Release"
    tooling, target = publish["steps"][0]["with"], publish["steps"][1]["with"]
    assert tooling["ref"] == "main" and tooling["path"] == "tooling"
    assert target["ref"] == "${{ needs.verify.outputs.target }}" and target["path"] == "target"
    assert tooling["persist-credentials"] is False and target["persist-credentials"] is False
    install, release = publish["steps"][3], publish["steps"][4]
    assert install["working-directory"] == "tooling"
    assert release["working-directory"] == "target"
    assert release["env"]["TARGET"] == "${{ needs.verify.outputs.target }}"


def test_review_plugins_are_configured_never_hard_coded(tmp_path):
    """The plugin marketplace these templates once named is gone, and a marketplace that
    cannot be cloned fails the review outright. So nothing is loaded by default; what a
    repository names is rendered into all three plugin-loading jobs, and a local
    marketplace resolves inside the trusted default-branch checkout, never the pull
    request's own tree."""
    from vibey_gh.config import GhConfig, PrAutomationConfig
    from vibey_gh.install import render_workflow

    source = WORKFLOWS / "pr-automation.yml"
    default = render_workflow(source, GhConfig(root=tmp_path))
    assert "vibey-skills.git" not in default
    assert "__VIBEY_GH_PLUGIN" not in default
    jobs = yaml.safe_load(default)["jobs"]
    loading = [
        step["with"]
        for job in jobs.values()
        for step in job.get("steps", [])
        if "plugin_marketplaces" in step.get("with", {})
    ]
    assert len(loading) == 3
    assert all(not w["plugin_marketplaces"].strip() and not w["plugins"].strip() for w in loading)

    configured = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            pr_automation=PrAutomationConfig(
                plugin_marketplaces=("src/tools/skills", "https://example.com/m.git"),
                plugins=("a@skills", "b@skills"),
            ),
        ),
    )
    for w in [
        step["with"]
        for job in yaml.safe_load(configured)["jobs"].values()
        for step in job.get("steps", [])
        if "plugin_marketplaces" in step.get("with", {})
    ]:
        assert w["plugin_marketplaces"].splitlines() == [
            "${{ github.workspace }}/automation/src/tools/skills",
            "https://example.com/m.git",
        ]
        assert w["plugins"].splitlines() == ["a@skills", "b@skills"]


@pytest.mark.parametrize(
    ("marketplaces", "plugins", "message"),
    [
        (("",), (), "entries must be non-empty"),
        (("a", "a"), (), "entries must be unique"),
        (("/abs/path",), (), "repository-relative path"),
        (("~/home",), (), "repository-relative path"),
        (("../escape",), (), "repository-relative path"),
        (("git://host/r.git",), (), "repository-relative path"),
        (("has space",), (), "repository-relative path"),
        (("https://host/r .git",), (), "URL contains whitespace"),
        (("skills",), ("no-marketplace",), "'<plugin>@<marketplace>'"),
        (("skills",), ("@skills",), "'<plugin>@<marketplace>'"),
        (("skills",), ("a@ skills",), "'<plugin>@<marketplace>'"),
        ((), ("a@skills",), "needs at least one plugin_marketplaces entry"),
    ],
)
def test_review_plugin_configuration_is_validated(marketplaces, plugins, message):
    from vibey_gh.config import PrAutomationConfig

    with pytest.raises(ValueError, match=re.escape(message)):
        PrAutomationConfig(plugin_marketplaces=marketplaces, plugins=plugins)


def test_review_plugins_load_from_the_config_file(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        "[pr_automation]\n"
        'plugin_marketplaces = ["src/skills"]\n'
        'plugins = ["quality-engineering@vibey-skills"]\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.pr_automation.plugin_marketplaces == ("src/skills",)
    assert cfg.pr_automation.plugins == ("quality-engineering@vibey-skills",)


def test_governance_is_published_on_every_surface_when_configured(tmp_path):
    """Sub-doctrine 7.b: the governance corpus is as easy to find as possible. When a
    source is configured, every channel site publishes it as a Governance section --
    and so as chapters of the book -- copied from its single source at build time; the
    theme links only the pages that were published; the chooser and llms.txt link it;
    and the corpus index ships after the build, from its configured path."""
    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import SOURCE_RELEASE_ASSETS, render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    off = render_workflow(source, GhConfig(root=tmp_path))
    assert 'governance_source = ""' in off
    assert 'if [ -f "corpus-index.json" ]; then' in off
    on = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(
                governance_source="src/tools/gh/docs", corpus_index="src/tools/gh/corpus-index.json"
            ),
        ),
    )
    assert 'governance_source = "src/tools/gh/docs"' in on
    assert (
        'names = ["constitution.md", "doctrines.md", "commandments.md", "bill-of-rights.md"]' in on
    )
    assert 're.fullmatch(r"sd-[a-z0-9][a-z0-9-]*\\.md", p.name)' in on
    assert 'raise SystemExit(f"governance source is missing {origin}")' in on
    assert "shutil.copyfile(origin, published / page)" in on
    assert 'data["nav"] = [*data.get("nav", []), {"Governance": entries}]' in on
    assert 'heading.replace(":", " —")' in on
    assert "allow_unicode=True, width=1_000_000" in on
    # The index ships AFTER the build, which cleans the site directory first.
    ship = on.index('cp "src/tools/gh/corpus-index.json" channel-site/corpus-index.json')
    assert ship > on.index("properdocs build --strict")
    assert "Ship the governance corpus index" not in on
    assert 'if re.fullmatch(r"[a-z0-9][a-z0-9-]*", p.parent.name)' in on
    assert "<strong>Governance</strong>" in on
    assert "[ -f pages/main/governance/constitution/index.html ] && SURFACE_LINES=" in on
    script = (SOURCE_RELEASE_ASSETS / "javascripts" / "channel.js").read_text(encoding="utf-8")
    assert "/^[a-z0-9][a-z0-9-]*$/.test(slug)" in script
    assert "encodeURIComponent(slug)" in script and "escapeText(" in script
    assert 'governanceLinks ? `<strong>Governance</strong> ${governanceLinks}` : ""' in script


@pytest.mark.parametrize("key", ["governance_source", "corpus_index"])
@pytest.mark.parametrize("value", ["/abs", "~/home", "../escape", "has space", "quo'te", "do$llar"])
def test_governance_paths_are_validated(key, value):
    from vibey_gh.config import DocumentationConfig

    with pytest.raises(ValueError, match=key):
        DocumentationConfig(**{key: value})


def test_corpus_index_path_must_not_be_empty():
    from vibey_gh.config import DocumentationConfig

    with pytest.raises(ValueError, match="corpus_index must not be empty"):
        DocumentationConfig(corpus_index="")


def test_governance_settings_load_from_the_config_file(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[documentation]\ngovernance_source = "src/gh/docs"\ncorpus_index = "src/gh/corpus-index.json"\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.documentation.governance_source == "src/gh/docs"
    assert cfg.documentation.corpus_index == "src/gh/corpus-index.json"


def test_latex_renders_on_the_site_from_a_verified_self_served_mathjax(tmp_path):
    """documentation.math: math survives Markdown (arithmatex), and the reader's browser
    typesets it with a MathJax the site serves itself -- fetched at build time, pinned by
    version and checksum, verified before use -- never from a third-party CDN."""
    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import SOURCE_RELEASE_ASSETS, render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    off = render_workflow(source, GhConfig(root=tmp_path))
    assert (
        'if [ "false" = "true" ]; then\n            python -m pip install --quiet \'pymdown-extensions==12.0\''
        in off
    )
    assert 'if "false" == "true":' in off
    on = render_workflow(
        source, GhConfig(root=tmp_path, documentation=DocumentationConfig(math=True))
    )
    assert "python -m pip install --quiet 'pymdown-extensions==12.0'" in on
    assert "https://registry.npmjs.org/mathjax/-/mathjax-3.2.2.tgz" in on
    assert "1b9c0a1c44df864e915690558e72adb9cc5203360daefd385084ced3b6c64c09" in on
    assert on.index("hexdigest()") < on.index('extractfile("package/es5/tex-svg.js")')
    assert '("javascripts/math.js", "javascripts/vendor/mathjax-tex-svg.js")' in on
    assert '{"pymdownx.arithmatex": {"generic": True}}' in on
    assert "cdn.jsdelivr" not in on and "cdnjs" not in on
    script = (SOURCE_RELEASE_ASSETS / "javascripts" / "math.js").read_text(encoding="utf-8")
    assert 'processHtmlClass: "arithmatex"' in script
    assert "convertLatexFences();" in script
    assert "\\begin\\{verbatim\\}" in script


def test_math_loads_from_the_config_file(tmp_path):
    (tmp_path / ".vibey-gh.toml").write_text("[documentation]\nmath = true\n", encoding="utf-8")
    assert load_config(tmp_path).documentation.math is True


def test_promotion_installs_uv_before_it_bumps_and_relocks(tmp_path):
    """`vibey-gh promote` bumps pyproject.toml and re-locks uv.lock in the same commit,
    which runs `uv lock`; without uv on the runner the promotion fails outright."""
    from vibey_gh.config import GhConfig
    from vibey_gh.install import render_workflow

    rendered = render_workflow(WORKFLOWS / "promote-to-main.yml", GhConfig(root=tmp_path))
    assert "astral-sh/setup-uv@85856786d1ce8acfbcc2f13a5f3fbd6b938f9f41 # v7.1.2" in rendered
    assert rendered.index("astral-sh/setup-uv@") < rendered.index("          vibey-gh promote ${{")


def test_funding_signage_is_opt_in_validated_and_verbatim(tmp_path):
    """#198: an opt-in contribution line beside the footer provenance. Off by default —
    no default address ever ships, because a payment default is one typo away from
    someone else's wallet. Shape-validated at config load per currency; rendered
    verbatim from reviewed config as text with a copy affordance, never a
    payment-processor link."""
    import pytest as _pytest

    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    off = render_workflow(source, GhConfig(root=tmp_path))
    assert "FUNDING_BITCOIN=''" in off and "FUNDING_MONERO=''" in off
    assert "FUNDING_ETHEREUM=''" in off

    on = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(
                funding_bitcoin="bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
                funding_ethereum="0x" + "ab" * 20,
                funding_label="Fuel the work",
            ),
        ),
    )
    assert "FUNDING_BITCOIN='bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4'" in on
    assert "FUNDING_LABEL='Fuel the work'" in on
    assert 'class="vibey-funding"' in on
    assert "navigator.clipboard.writeText" in on

    # Malformed addresses are configuration ERRORS, never rendered.
    for field, bad in (
        ("funding_bitcoin", "bc1-notanaddress"),
        ("funding_monero", "4short"),
        ("funding_ethereum", "0x1234"),
    ):
        with _pytest.raises(ValueError, match=field):
            DocumentationConfig(**{field: bad})

    # Real-shaped addresses for every currency pass validation.
    DocumentationConfig(
        funding_bitcoin="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa",
        funding_monero="4" + "A" * 94,
        funding_ethereum="0x" + "0" * 40,
    )


def test_release_surfaces_smoke_checks_search_at_build_time():
    """A channel site can build --strict with a dead search: assets that 404 or an index
    with zero documents only surface when a human types a query into a silent box. The
    build step must therefore prove the index parses and is non-empty, and that every
    search asset landed, before the site is uploaded."""
    text = (WORKFLOWS / "release-surfaces.yml").read_text(encoding="utf-8")
    smoke = text.index("search smoke:")
    build = text.index("properdocs build --strict --config-file .properdocs-channel.yml")
    assert build < smoke, "the smoke test must run against the built channel site"
    for asset in (
        "search/search_index.json",
        "search/lunr.js",
        "search/main.js",
        "search/worker.js",
    ):
        assert asset in text
    assert "the index contains zero documents" in text
    assert "documents indexed, all assets present" in text


def test_branch_intake_reopens_a_reused_branch_name_without_duplicating_open_prs():
    text = (WORKFLOWS / "branch-intake.yml").read_text(encoding="utf-8")
    assert "github.event.created == true" not in text
    assert "github.event.deleted != true" in text
    assert 'gh pr list --repo "$REPO" --state open --head "$HEAD_REF"' in text
    assert "historical closed PR must never suppress intake" in text


def test_automation_bootstrap_is_explicit_exact_head_and_permanent_branch_safe():
    text = render_workflow(WORKFLOWS / "automation-bootstrap.yml", GhConfig(root=Path(".")))
    assert "workflow_dispatch:" in text
    assert "inputs.authorize == true" in text
    assert 'test "$permission" = admin' in text
    assert 'test "$(jq -r .headRefOid' in text
    assert '--match-head-commit "$EXPECTED_SHA"' in text
    for required in (
        "Documentation contract",
        "Provenance",
        "Build",
        "Lint",
        "Analyze Python",
        "MCP, API, CLI, SDK, and webhook parity",
    ):
        assert required in text
    assert '[ "$head" != "$INTEGRATION_BRANCH" ]' in text
    assert '[ "$head" != "$RELEASE_BRANCH" ]' in text
    assert '[ "$head" != develop ]' in text
    assert '[ "$head" != main ]' in text
    assert "--delete-branch" not in text


def test_automation_bootstrap_scope_check_rejects_files_outside_automation_core():
    import subprocess

    text = (WORKFLOWS / "automation-bootstrap.yml").read_text(encoding="utf-8")
    match = re.search(
        r"if grep -Ev '([^']+)' changed-files\.txt; then\n"
        r"\s*echo \"::error::changed files are not confined to automation-core paths\" >&2\n"
        r"\s*exit 1\n"
        r"\s*fi",
        text,
    )
    assert match, "expected a fail-closed scope check in automation-bootstrap.yml"
    pattern = match.group(1)

    in_scope_only = (
        "vibey_gh/templates/workflows/automation-bootstrap.yml\ntest/test_templates.py\n"
    )
    mixed_scope = in_scope_only + "vibey_gh/versioning.py\n"

    def confinement_check_passes(changed_files: str) -> bool:
        # Mirrors the workflow's own gate: `if grep -Ev ...; then <fail>; fi` fails the
        # step when grep finds an out-of-scope line (exit 0), and passes when grep finds
        # none (exit 1, no matches).
        script = f"grep -Ev '{pattern}' <<'EOF'\n{changed_files}EOF\n"
        result = subprocess.run(["sh", "-c", script], capture_output=True, text=True, check=False)
        return result.returncode != 0

    assert confinement_check_passes(in_scope_only)
    assert not confinement_check_passes(mixed_scope)


def test_pr_review_requires_verified_repository_paths():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")

    assert "Inspect target/ with Read, Glob, and Grep only" in text
    assert "verify its path exists under target/ with Read or Glob" in text
    assert "Never return schema" in text
    assert "fail the review action so infrastructure recovery can retry it" in text


def _relative_luminance(hex_colour: str) -> float:
    value = hex_colour.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(foreground: str, background: str) -> float:
    first, second = _relative_luminance(foreground), _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def _resolver(hook: str) -> str:
    """The `vibey_gh_self` function as the hook template actually carries it."""
    text = (TEMPLATES / hook).read_text(encoding="utf-8")
    start = text.index("vibey_gh_self() {")
    return text[start : text.index("\n}\n", start) + 3]


def _run_resolver(hook: str, cwd) -> str:
    script = _resolver(hook) + "\nvibey_gh_self\n"
    # `set -eu` on purpose: pre-push runs under it, and an unguarded test inside the
    # resolver would abort the hook instead of falling through.
    done = subprocess.run(
        ["sh", "-c", "set -eu\n" + script], cwd=cwd, capture_output=True, text=True, check=False
    )
    assert done.returncode == 0, done.stderr
    return done.stdout


def _tree(root, *, config: str | None, at: str = "src/tools/gh") -> None:
    (root / at / "vibey_gh").mkdir(parents=True, exist_ok=True)
    (root / "pyproject.toml").write_text('name = "vibey"\n')
    (root / at / "pyproject.toml").write_text('name = "vibey-gh"\n')
    if config is not None:
        (root / ".vibey-gh.toml").write_text(f'[install]\nself_source = "{config}"\n')


@pytest.mark.parametrize("hook", ["pre-push", "commit-msg"])
def test_the_hook_runs_the_tooling_this_repository_declares(hook, tmp_path):
    """A declared path, so a monorepo tenant is found and a standalone repo is unchanged."""
    mono = tmp_path / "mono"
    _tree(mono, config="src/tools/gh")
    assert _run_resolver(hook, mono) == "src/tools/gh"

    standalone = tmp_path / "standalone"
    (standalone / "vibey_gh").mkdir(parents=True)
    (standalone / "pyproject.toml").write_text('name = "vibey-gh"\n')
    (standalone / ".vibey-gh.toml").write_text("[install]\n")
    assert _run_resolver(hook, standalone) == "."

    adopter = tmp_path / "adopter"
    adopter.mkdir()
    (adopter / "pyproject.toml").write_text('name = "something-else"\n')
    assert _run_resolver(hook, adopter) == ""


@pytest.mark.parametrize("hook", ["pre-push", "commit-msg"])
def test_the_hook_never_discovers_a_tool_a_branch_added(hook, tmp_path):
    """The resolver must not search the tree.

    A hook executes what it resolves. Searching for "the first tracked pyproject.toml
    declaring name = vibey-gh" reads whatever is in the working tree, which on a
    contributor's branch is whatever they put there.
    """
    root = tmp_path / "repo"
    _tree(root, config=None)
    (root / "evil" / "vibey_gh").mkdir(parents=True)
    (root / "evil" / "pyproject.toml").write_text('name = "vibey-gh"\n')

    # No declaration: nothing is used, even though two candidates exist on disk.
    assert _run_resolver(hook, root) == ""

    # Declared: exactly what was declared, never the planted one.
    (root / ".vibey-gh.toml").write_text('[install]\nself_source = "src/tools/gh"\n')
    assert _run_resolver(hook, root) == "src/tools/gh"


@pytest.mark.parametrize("bad", ["/etc", "../outside", "src/tools/absent"])
def test_the_hook_refuses_a_path_that_escapes_or_is_not_the_tooling(bad, tmp_path):
    root = tmp_path / "repo"
    _tree(root, config=bad)
    assert _run_resolver("pre-push", root) == ""


@pytest.mark.parametrize("hook", ["pre-push", "commit-msg"])
def test_a_repository_that_is_vibey_gh_runs_its_own_working_tree(hook):
    """An installed copy must never be what validates the tool's own repository.

    `develop` here is ahead of the last release nearly always, so a globally installed
    vibey-gh compares this repository's managed assets against the older ones it bundles,
    calls them out of date, and refuses the push. That is not hypothetical: installing the
    CLI the obvious way to satisfy an adopter's hook immediately made every push from this
    repository fail, with a provenance error that had nothing wrong behind it.

    The package is dependency-free stdlib, so running the checkout needs no install and no
    virtualenv — only that this branch is tried before `command -v`.
    """
    text = (TEMPLATES / hook).read_text(encoding="utf-8")
    self_hosting = text.find("vibey_gh_self")
    installed_copy = text.find("command -v vibey-gh")
    assert self_hosting != -1, "the self-hosting branch is gone"
    assert installed_copy != -1
    assert self_hosting < installed_copy, (
        "an installed vibey-gh would shadow the working tree and judge this repository "
        "against whatever it last released"
    )
    # Narrow on purpose: an adopting repository must fall straight through to its
    # installed CLI, so the test is the package name *and* the package directory.
    assert '[ -d "$dir/vibey_gh" ]' in text


def test_no_code_token_can_keep_a_colour_meant_for_a_white_page():
    """The gap the contrast test alone could not close.

    Measuring the colours a stylesheet declares says nothing about the tokens it never
    mentions. The first pass at this passed green while `.hljs-subst` was still inheriting
    github-light's near-black — so `$(git rev-parse HEAD)` sat at 1.33:1 inside the very
    example that tells a reader how to list their check names.

    A catch-all fixes the class rather than the instance: any token, including ones this
    stylesheet has never heard of, starts legible. It has to come *before* the palette,
    because an attribute selector and a class have equal specificity and source order is
    what decides between them.
    """
    css = (Path(__file__).resolve().parent.parent / "docs/stylesheets/vibey.css").read_text(
        encoding="utf-8"
    )
    catch_all = css.find('[class*="hljs-"]')
    assert catch_all != -1, "no catch-all: an unlisted token would inherit the light theme"
    assert ".highlight span" in css, "Pygments needs the same catch-all"
    first_token_rule = css.find(".hljs-string,")
    assert first_token_rule != -1
    assert catch_all < first_token_rule, (
        "the catch-all must precede the palette, or equal specificity lets it win and "
        "every token collapses to one colour"
    )


def test_code_blocks_are_legible_against_the_background_this_theme_forces():
    """Forcing a dark code background obliges this stylesheet to own the token colours.

    The mkdocs theme ships two highlight.js palettes and enables the *light* one by
    default — `#hljs-dark` carries `disabled` — so its tokens are picked for a white page.
    This stylesheet then paints the block `#080c17`. github-light renders a string as
    `#032f62`, which against that background is 1.48:1: not low-contrast but genuinely
    unreadable, and every configuration sample in these docs is mostly string literals.

    Measured rather than eyeballed, because "looks fine to me" is what shipped it.
    """
    css = (Path(__file__).resolve().parent.parent / "docs/stylesheets/vibey.css").read_text(
        encoding="utf-8"
    )
    background = re.search(r"background:\s*(#[0-9a-fA-F]{6})\s*!important", css)
    assert background, "the forced code-block background is gone; this test needs rewriting"
    dark = background.group(1)
    # Every colour declared in a rule that mentions a syntax token, whichever highlighter
    # produced it: `.hljs-*` for the client-side theme, `.highlight .x` for Pygments.
    tokens = re.findall(
        r"((?:[^{}]*(?:\.hljs-|\.highlight\s+\.)[^{}]*)\{[^}]*?color:\s*(#[0-9a-fA-F]{6}))",
        css,
    )
    assert len(tokens) >= 8, f"expected the token palette to be present, found {len(tokens)}"
    for rule, colour in tokens:
        ratio = _contrast(colour, dark)
        selector = rule.split("{")[0].strip().splitlines()[-1].strip()
        assert ratio >= 4.5, f"{selector} {colour} is {ratio:.2f}:1 on {dark}, below AA"


def test_properdocs_theme_is_channel_aware_and_accessible():
    root = Path(__file__).resolve().parent.parent
    config = (root / "properdocs.yml").read_text(encoding="utf-8")
    css = (root / "docs/stylesheets/vibey.css").read_text(encoding="utf-8")
    script = (root / "docs/javascripts/channel.js").read_text(encoding="utf-8")
    assert "stylesheets/vibey.css" in config
    assert "javascripts/channel.js" in config
    assert "md_in_html" in config and "attr_list" in config
    assert 'body[data-release-channel="main"]' in css
    assert 'body[data-release-channel="develop"]' in css
    assert "prefers-reduced-motion" in css
    assert "padding-top: 0" in css
    assert "position: sticky" in css
    assert "top: 0" in css
    assert 'dataset.bsTheme = "dark"' in script
    assert 'segments.includes("develop")' in script
    assert "/edit/${channel}/" in script
    assert "__REPOSITORY__@__SHORT_SHA__" in script
    assert "__RELEASE_BRANCH__" in script
    assert "__RELEASE_CHANNEL__" in script
    assert "Made with ❤️ by" in script
    assert "https://the-vibey-project.github.io/vibey/" in script
    assert "https://vibewithadam.matthewsteinberger.com" in script
    assert "https://github.com/adammatthewsteinberger/" in script
    assert "__PAGES_ROOT__" in script
    assert "link.href = pagesRoot" in script
    assert '["__PRODUCTION_LABEL__", "main"]' in script
    assert '["__PREVIEW_LABEL__", "develop"]' in script
    assert "Release channels: release-channels.md" not in config
    index = (root / "docs/index.md").read_text(encoding="utf-8")
    assert 'data-release-target="main"' in index
    assert 'data-release-target="develop"' in index
    assert "link.dataset.releaseTarget" in script


def test_repository_profile_is_configurable_and_never_mutates_branches():
    text = (WORKFLOWS / "repository-profile.yml").read_text(encoding="utf-8")
    assert 'workflows: ["Release surfaces"]' in render_workflow(
        WORKFLOWS / "repository-profile.yml", GhConfig(root=Path("."))
    )
    assert "__VIBEY_GH_PROFILE_DESCRIPTION__" in text
    assert "__VIBEY_GH_PROFILE_TOPICS__" in text
    assert '--arg homepage "$pages_url"' in text
    assert "repos/${REPO}/topics" in text
    assert "__VIBEY_GH_PROFILE_SETTINGS__" in text
    assert "vulnerability-alerts" in text
    assert "automated-security-fixes" in text
    # A cap, not a count: every occurrence is a step handed the elevated token, so the
    # number may grow as this workflow reconciles more repository state, but not
    # unnoticed. Raising it should be a deliberate decision about privileged surface.
    assert text.count("secrets.AUTOMERGE_TOKEN || github.token") <= 5
    assert "Unable to verify ${setting}" in text
    assert "HTTP 404" in text
    assert "branches/${branch}" in text
    assert "--jq .protected" in text
    assert "https://${OWNER}.github.io/${REPO_NAME}/" in text
    assert "curl --fail --silent --show-error" in text
    assert "repos/${REPO}/releases?per_page=1" in text
    assert "repos/${REPO}/deployments?per_page=1" in text
    assert "scope=repository:${package}:pull" in text
    assert "https://ghcr.io/v2/${package}/manifests/${channel}" in text
    assert "git push" not in text
    assert "--delete" not in text


def test_failed_permanent_branch_scans_use_a_guarded_repair_pr():
    text = render_workflow(WORKFLOWS / "release-repair.yml", GhConfig(root=Path(".")))
    assert (
        'workflows: ["CI", "Provenance", "Release", "Release surfaces", "GitHub Release"]' in text
    )
    assert "github.event.workflow_run.conclusion == 'failure'" in text
    assert '"$INTEGRATION_BRANCH"|"$RELEASE_BRANCH"' in text
    assert "mcp__github_ci__download_job_log" in text
    assert "Never execute package managers" in text
    assert "Never lower coverage" in text
    assert "Create credential-free Claude git context" in text
    assert "Remove credential-free Claude git context" in text
    assert 'git remote add origin "https://github.com/${{ github.repository }}.git"' in text
    assert 'allowed_non_write_users: "__vibey_gh_no_nonwrite_users__"' in text
    assert "persist-credentials: false" in text
    assert "gitdir: $GITHUB_WORKSPACE/target/.git" not in text
    assert 'repair_branch="vibey-gh/repair/release-' in text
    assert 'git -C target push origin "HEAD:refs/heads/${REPAIR_BRANCH}"' in text
    assert 'gh pr create --repo "$REPO" --base "$BASE_BRANCH"' in text
    assert "git push --delete" not in text
    assert "git branch -D" not in text
    assert "HEAD:refs/heads/${BASE_BRANCH}" not in text


@pytest.mark.parametrize(
    "paths,match",
    [
        (("/abs/CHANGELOG.md",), "repository-relative"),
        (("../outside.md",), "repository-relative"),
        (("a", "a"), "must be unique"),
        ((" ",), "must be non-empty"),
    ],
)
def test_unsafe_union_merge_paths_are_rejected(tmp_path, paths, match):
    from vibey_gh.config import GhConfig

    with pytest.raises(ValueError, match=match):
        GhConfig(root=tmp_path, union_merge_paths=paths)


AI_TEMPLATES = (
    "conversation.yml",
    "documentation.yml",
    "issue-automation.yml",
    "pr-automation.yml",
    "release-repair.yml",
)


def test_every_ai_step_can_be_pointed_at_another_endpoint():
    """One marker per AI step, or a repository can only redirect some of its spending.

    Claude Code honours `ANTHROPIC_BASE_URL`, so a gateway serving the Anthropic Messages
    API is the whole of what it takes to run this somewhere other than Anthropic. That is
    only true if *every* step carries the hook: a missed one keeps billing the original
    endpoint, and silently.
    """
    marked = tokens = 0
    for name in AI_TEMPLATES:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        marked += text.count("# __VIBEY_GH_AI_ENV__")
        tokens += text.count("secrets.__VIBEY_GH_AI_AUTH_SECRET__")
    call_sites = sum(
        (WORKFLOWS / name).read_text(encoding="utf-8").count("uses: anthropics/claude-code-action")
        for name in AI_TEMPLATES
    )
    assert call_sites == 7
    assert marked == call_sites
    assert tokens == call_sites


@pytest.mark.parametrize("name", AI_TEMPLATES)
def test_the_default_endpoint_is_unchanged_and_no_base_url_is_set(name, tmp_path: Path):
    """Empty is not the same as unset: an empty `ANTHROPIC_BASE_URL` points at nothing."""
    rendered = render_workflow(WORKFLOWS / name, GhConfig(root=tmp_path))
    assert "__VIBEY_GH" not in rendered
    assert yaml.safe_load(rendered)
    assert "ANTHROPIC_BASE_URL" not in rendered
    assert "${{ secrets.ANTHROPIC_API_KEY }}" in rendered


@pytest.mark.parametrize("name", AI_TEMPLATES)
def test_a_gateway_endpoint_reaches_every_step_with_both_header_conventions(name, tmp_path: Path):
    rendered = render_workflow(
        WORKFLOWS / name,
        GhConfig(
            root=tmp_path,
            ai=AiConfig(base_url="https://gateway.example.test/v1", auth_secret="LITELLM_KEY"),
        ),
    )
    assert "__VIBEY_GH" not in rendered
    assert yaml.safe_load(rendered)
    calls = rendered.count("uses: anthropics/claude-code-action")
    assert rendered.count('ANTHROPIC_BASE_URL: "https://gateway.example.test/v1"') == calls
    # Claude Code sends `x-api-key`; some gateways read `Authorization`. One secret fills
    # both, so a gateway works without the repository having to know which it wants.
    assert rendered.count("ANTHROPIC_AUTH_TOKEN: ${{ secrets.LITELLM_KEY }}") == calls
    assert "ANTHROPIC_API_KEY" not in rendered


@pytest.mark.parametrize(
    "kwargs,match",
    [
        # A name that could close the expression and append another would be an injection
        # into a privileged workflow, so only a bare secret identifier is accepted.
        ({"auth_secret": "A }} ${{ secrets.OTHER"}, "not a valid secret name"),
        ({"auth_secret": "9LEADING_DIGIT"}, "not a valid secret name"),
        ({"auth_secret": ""}, "not a valid secret name"),
        ({"base_url": "ftp://gateway.example.test"}, "must be an http"),
        ({"base_url": "gateway.example.test"}, "must be an http"),
        ({"base_url": "https://gateway.example.test\nkey: value"}, "no whitespace"),
    ],
)
def test_an_unsafe_ai_endpoint_is_rejected(kwargs, match):
    with pytest.raises(ValueError, match=match):
        AiConfig(**kwargs)


@pytest.mark.parametrize(
    "kwargs,match",
    [
        ({"site_requirements": ("a", "a")}, "must be unique"),
        ({"site_requirements": (" ",)}, "must be non-empty"),
        # Quoting makes ordinary specifier punctuation safe, but a newline would end the
        # `pip install` line and start an arbitrary command inside the workflow.
        ({"site_requirements": ("mkdocs\nrm -rf /",)}, "spans lines"),
        ({"site_requirements": ("mkdocs\rwhoami",)}, "spans lines"),
        ({"site_requirements_file": "/etc/requirements.txt"}, "repository-relative"),
        ({"site_requirements_file": "../elsewhere/requirements.txt"}, "repository-relative"),
        ({"properdocs_version": "  "}, "must not be empty"),
    ],
)
def test_unsafe_site_requirements_are_rejected(kwargs, match):
    with pytest.raises(ValueError, match=match):
        DocumentationConfig(**kwargs)


def test_a_repository_may_decline_the_site_requirements_file_entirely(tmp_path):
    """An empty path is a supported way to say "no requirements file", not a broken one."""
    rendered = render_workflow(
        WORKFLOWS / "release-surfaces.yml",
        GhConfig(root=tmp_path, documentation=DocumentationConfig(site_requirements_file="")),
    )
    assert "__VIBEY_GH" not in rendered
    # The guard survives with an empty operand, so the branch is simply never taken.
    assert 'if [ -n "" ]' in rendered


def test_a_repository_can_decline_the_union_merge_rule_entirely(tmp_path):
    from vibey_gh.config import GhConfig
    from vibey_gh.install import apply_union_merge, missing_union_merge_lines

    cfg = GhConfig(root=tmp_path, union_merge_paths=())
    assert apply_union_merge(cfg) is None
    assert missing_union_merge_lines(cfg) == []
    assert not (tmp_path / ".gitattributes").exists()


def test_append_only_files_merge_instead_of_conflicting(tmp_path):
    """Every branch appends to the changelog, so every merge stranded every other branch
    on a conflict carrying no information. `merge=union` keeps both sides."""
    import subprocess

    from vibey_gh.config import GhConfig
    from vibey_gh.install import apply_union_merge

    def git(*args, cwd=tmp_path):
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)

    git("init", "-q", "-b", "main", ".")
    git("config", "user.email", "t@e.com")
    git("config", "user.name", "t")
    cfg = GhConfig(root=tmp_path)
    assert apply_union_merge(cfg) == "installed"
    log = tmp_path / "CHANGELOG.md"
    log.write_text("# Changelog\n\n## Unreleased\n\n- base\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-qm", "base")

    git("switch", "-qc", "topic")
    log.write_text("# Changelog\n\n## Unreleased\n\n- base\n- from the topic\n", encoding="utf-8")
    git("commit", "-qam", "topic")
    git("switch", "-q", "main")
    log.write_text("# Changelog\n\n## Unreleased\n\n- base\n- from develop\n", encoding="utf-8")
    git("commit", "-qam", "develop")

    git("switch", "-q", "topic")
    assert git("rebase", "main").returncode == 0, "the union driver should absorb this"
    settled = log.read_text(encoding="utf-8")
    assert "- from develop" in settled and "- from the topic" in settled
    assert "<<<<<<<" not in settled


def test_the_union_declaration_never_rewrites_an_adopters_own_attributes(tmp_path):
    from vibey_gh.config import GhConfig
    from vibey_gh.install import GITATTRIBUTES, apply_union_merge, missing_union_merge_lines

    theirs = tmp_path / GITATTRIBUTES
    theirs.write_text("*.png binary\n", encoding="utf-8")
    cfg = GhConfig(root=tmp_path)
    assert apply_union_merge(cfg) == "updated"
    text = theirs.read_text(encoding="utf-8")
    assert "*.png binary" in text, "an adopter's own rules must survive adoption"
    assert "CHANGELOG.md merge=union" in text
    # Idempotent: a second install changes nothing and reports nothing missing.
    assert apply_union_merge(cfg) is None
    assert missing_union_merge_lines(cfg) == []
    assert theirs.read_text(encoding="utf-8") == text


def test_an_attributes_file_without_a_trailing_newline_is_appended_safely(tmp_path):
    from vibey_gh.config import GhConfig
    from vibey_gh.install import GITATTRIBUTES, apply_union_merge

    (tmp_path / GITATTRIBUTES).write_text("*.png binary", encoding="utf-8")
    cfg = GhConfig(root=tmp_path)
    apply_union_merge(cfg)
    lines = (tmp_path / GITATTRIBUTES).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "*.png binary"
    assert "CHANGELOG.md merge=union" in lines


def test_repository_dogfoods_the_exact_rendered_workflows_and_hooks():
    root = Path(__file__).resolve().parent.parent
    ok, problems = installed(load_config(root), local=False)
    assert ok, problems


def test_managed_automation_can_update_but_never_delete_develop_or_main():
    text = "\n".join(path.read_text(encoding="utf-8") for path in WORKFLOW_TEMPLATES)
    assert "HEAD:refs/heads/${HEAD_REF}" in text
    assert "--delete-branch" not in text
    assert "git push --delete" not in text
    assert "git branch -D" not in text
    assert "DELETE /git/refs" not in text


def test_conventional_commits_self_heal_only_guarded_topic_history():
    text = (WORKFLOWS / "conventional-commits.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" in text
    assert "vibey-gh conventional-check" in text
    assert "vibey-gh conventional-message" in text
    assert "working-directory: target" in text
    assert '--force-with-lease="refs/heads/${HEAD_REF}:${HEAD_SHA}"' in text
    assert '"$INTEGRATION_BRANCH"|"$RELEASE_BRANCH"|develop|main' in text
    assert "permanent branch history is never rewritten" in text
    assert "github.event.pull_request.head.ref != '__VIBEY_GH_INTEGRATION_BRANCH__'" in text
    assert "github.event.pull_request.head.ref != '__VIBEY_GH_RELEASE_BRANCH__'" in text
    assert "Refusing automatic rewrite of merge commits" in text
    assert "./target" not in text
    assert "git push --delete" not in text
    assert "--delete-branch" not in text


def test_provenance_walks_the_pull_requests_head_not_the_merge_ref():
    """A first-parent walk from `refs/pull/N/merge` examines nothing.

    On a pull_request event `actions/checkout` gives you a synthetic merge commit whose
    FIRST parent is the base branch. `git log --first-parent BASE..HEAD` from there walks
    straight into the base and reports zero commits -- a green provenance gate that looked
    at nothing. Measured on the repository where this was found: 0 commits from the merge
    ref, 16 from the branch head.

    The commit checks need first-parent to skip imported subtree history, so the fix is
    the endpoint rather than the traversal.
    """
    text = (WORKFLOWS / "provenance.yml").read_text(encoding="utf-8")
    assert "HEAD_SHA: ${{ github.event.pull_request.head.sha }}" in text
    assert '--commits "${BASE_SHA}..${HEAD_SHA}"' in text
    # ...and the head has to be fetchable before it can be walked.
    assert 'git fetch --quiet --depth=50 origin "${HEAD_SHA}"' in text
    assert '--commits "${BASE_SHA}..HEAD"' not in text


def test_conventional_commits_installs_the_published_package_not_the_adopting_repo():
    """A repo with `dependencies = []` that only pulls in vibey-gh as a CI tool must not
    have this step assume its own `pip install .` yields the vibey-gh CLI.
    """
    text = (WORKFLOWS / "conventional-commits.yml").read_text(encoding="utf-8")
    assert "pip install --quiet ./automation" not in text
    assert 'self="__VIBEY_GH_SELF_SOURCE__"' in text
    assert 'python -m pip install --quiet -e "$self"' in text
    assert FALLBACK_INSTALL in text
    assert "name: Check out trusted automation" in text
    assert "name: Check out trusted normalizer" not in text

    # The step that actually decides whether commits conform must fail loudly, not
    # treat "vibey-gh: command not found" as a false `if` condition that then barrels
    # ahead into a doomed git filter-branch.
    deciding = text.split("name: Check every commit subject", 1)[1]
    guard = deciding.split("if vibey-gh conventional-check", 1)[0]
    assert "command -v vibey-gh" in guard
    assert "exit 1" in guard


def test_normalising_a_subject_is_a_key_and_the_check_runs_either_way(tmp_path: Path):
    """Rewriting is opt-out; checking is not.

    An explicitly-default config, NOT `load_config()`: that would read this repository's
    own `.vibey-gh.toml`, which sets the key false, so the default arm would silently
    assert repo state rather than the default an adopter gets.
    """
    from vibey_gh.config import PrAutomationConfig

    default = render_workflow(WORKFLOWS / "conventional-commits.yml", GhConfig(root=tmp_path))
    off = render_workflow(
        WORKFLOWS / "conventional-commits.yml",
        GhConfig(root=tmp_path, pr_automation=PrAutomationConfig(normalise_commit_subjects=False)),
    )

    assert "__VIBEY_GH_NORMALISE_SUBJECTS__" not in default + off
    # Default keeps the behaviour adopters already have: rewrite on, refusal off.
    assert "conforms == 'false' && true" in default
    assert "conforms == 'false' && !true" in default
    # Off inverts exactly those two, and nothing else.
    assert "conforms == 'false' && false" in off
    assert "conforms == 'false' && !false" in off
    # The check itself is not behind the switch in either rendering -- a repository that
    # declines the rewrite still has its subjects judged, which is the point of the job.
    for rendered in (default, off):
        assert "name: Check every commit subject" in rendered
        assert "vibey-gh conventional-check --commits" in rendered


def test_pr_automation_never_assumes_the_adopting_repos_own_package_is_vibey_gh():
    """Every `automation/` checkout of the adopting repo's default branch must detect
    self-hosting before installing from it, the same class of bug as the conventional-
    commits template: a repo with `dependencies = []` does not yield the vibey-gh CLI
    from `pip install ./automation`.
    """
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "pip install --quiet ./automation" not in text
    checks = re.findall(r'self="automation/__VIBEY_GH_SELF_SOURCE__"', text)
    assert len(checks) == 5  # review, repair, resolve-conflict, escalate, review-fallback
    lines = text.splitlines(keepends=True)
    installs = [line for line in lines if line.endswith(FALLBACK_INSTALL)]
    assert len(installs) == 6  # the five guarded installs above plus the evaluate job's own


def test_promotion_checks_provenance_without_rewriting_or_reauditing_history():
    text = (WORKFLOWS / "provenance.yml").read_text(encoding="utf-8")
    assert 'if [ "$HEAD_REF" = "$INTEGRATION_BRANCH" ]' in text
    assert '[ "$BASE_REF" = "$RELEASE_BRANCH" ]' in text
    assert "Promotion PR: checking repository provenance" in text
    assert "vibey-gh check --ci" in text
    assert 'vibey-gh check --ci --commits "${BASE_SHA}..${HEAD_SHA}"' in text


def test_the_provenance_job_carries_no_forge_credential():
    """The job that runs contributor-controlled code must never hold a token.

    `provenance.yml` installs the tooling from the CHECKED-OUT TREE where a repository
    self-hosts (`self_source`), and it runs on `pull_request`. So the step that invokes
    `vibey-gh` is running the contributor's own code, and any credential in that
    environment is a credential handed to whatever the pull request contains.

    This was almost lost once: `check --ci` also surveys cloud clutter through `gh`, that
    survey reports "not surveyed" without a token, and the obvious repair is to add
    `GH_TOKEN` and `pull-requests: read` right here. The obvious repair is the
    vulnerability. This test exists so the next person making that fix is stopped by a
    red suite rather than by a reviewer who happens to notice -- the survey belongs in a
    job whose checkout is trusted, not in this one.
    """
    text = (WORKFLOWS / "provenance.yml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)

    # Structural, not textual: the comment above the permissions block names `GH_TOKEN`
    # precisely so nobody re-adds it, and a raw substring search would read that warning
    # as the very thing it warns about. What matters is what is ASSIGNED.
    declared: list[dict] = [workflow.get("env") or {}]
    for job in workflow["jobs"].values():
        declared.append(job.get("env") or {})
        declared.extend(step.get("env") or {} for step in job.get("steps", []))

    for env in declared:
        assert "GH_TOKEN" not in env, "the provenance job must not receive a forge credential"
        secrets = [value for value in env.values() if "secrets." in str(value)]
        assert not secrets, "the provenance job must not receive any secret"

    # Read-only on contents alone. Anything wider is a wider grant to that same code.
    assert workflow["permissions"] == {"contents": "read"}
    # The premise the assertions above rest on: this job really does install and run the
    # checkout's own tooling, so if that ever stops being true these can be revisited.
    assert 'python -m pip install --quiet -e "$self"' in text


def _is_the_fallback_distribution(root: Path, version: str) -> None:
    """Make `root` the distribution the fallback installs, at `version`."""
    root.joinpath("pyproject.toml").write_text(
        f'[project]\nname = "{FALLBACK_DISTRIBUTION}"\nversion = "{version}"\n',
        encoding="utf-8",
    )


def test_pin_version_pins_every_managed_templates_tooling_install(tmp_path: Path):
    """`install.pin_version` must reach every managed workflow, not just the ones the
    issue happened to confirm — a config key that only fixes some templates leaves the
    same outage waiting in whichever one it missed.
    """
    _is_the_fallback_distribution(tmp_path, "4.5.6")
    cfg = GhConfig(root=tmp_path, pin_version=True)
    for path in WORKFLOW_TEMPLATES:
        text = render_workflow(path, cfg)
        if FALLBACK_INSTALL not in path.read_text(encoding="utf-8"):
            continue  # this template never installed the floating tooling to begin with
        assert FALLBACK_INSTALL not in text, f"{path.name}: an unpinned install survived"
        assert f'"{FALLBACK_DISTRIBUTION}==4.5.6"' in text


def test_pin_version_unset_leaves_every_managed_template_floating(tmp_path: Path):
    _is_the_fallback_distribution(tmp_path, "4.5.6")
    cfg = GhConfig(root=tmp_path)
    for path in WORKFLOW_TEMPLATES:
        text = render_workflow(path, cfg)
        assert f"{FALLBACK_DISTRIBUTION}==" not in text


@pytest.mark.parametrize(
    "pyproject",
    [
        pytest.param(None, id="no pyproject at all"),
        pytest.param("[project\nname = ", id="a pyproject that does not parse"),
        pytest.param('[tool.poetry]\nname = "vibey"\n', id="no [project] table"),
        pytest.param('[project]\nname = "vibey"\n', id="no version declared"),
    ],
)
def test_pin_version_floats_when_the_repository_declares_no_release(tmp_path: Path, pyproject):
    """Anything short of a declared release leaves the fallback floating.

    A renderer that guessed here would write the guess into every managed workflow of a
    repository that never said it, and the job would fail on `pip install` rather than
    on the render anybody could have read.
    """
    if pyproject is not None:
        tmp_path.joinpath("pyproject.toml").write_text(pyproject, encoding="utf-8")
    text = render_workflow(WORKFLOWS / "merge-train.yml", GhConfig(root=tmp_path, pin_version=True))
    assert FALLBACK_INSTALL in text
    assert f"{FALLBACK_DISTRIBUTION}==" not in text


def test_pin_version_cannot_invent_a_release_for_a_repository_that_is_not_it(tmp_path: Path):
    """An adopter turning the key on must not get a version this tooling guessed.

    `vibey_gh.__version__` numbers a package inside `vibey` (ADR-0037), and an adopter's
    own version numbers their project; neither names a `vibey` release. A pin built from
    either resolves to nothing inside the adopter's job. Floating always resolves.
    """
    tmp_path.joinpath("pyproject.toml").write_text(
        '[project]\nname = "somebody-else"\nversion = "9.9.9"\n', encoding="utf-8"
    )
    for path in WORKFLOW_TEMPLATES:
        text = render_workflow(path, GhConfig(root=tmp_path, pin_version=True))
        assert "9.9.9" not in text
        assert f"{FALLBACK_DISTRIBUTION}==" not in text
        if FALLBACK_INSTALL in path.read_text(encoding="utf-8"):
            assert FALLBACK_INSTALL in text


def test_every_managed_third_party_action_is_immutably_pinned():
    for path in [*WORKFLOW_TEMPLATES, *REPO_WORKFLOWS]:
        for action, revision in re.findall(r"uses:\s+([^@\s]+)@([^\s#]+)", path.read_text()):
            assert re.fullmatch(r"[0-9a-f]{40}", revision), f"{path.name}: {action}@{revision}"


def test_privileged_agent_cannot_mutate_git_or_execute_pr_code():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "Bash(git:" not in text
    assert "Never execute package\n" in text
    assert "python -m pip install --quiet ./target" not in text
    assert "run: ./target" not in text
    assert "Resolve merge conflicts" in text
    assert "--allowedTools Read,Glob,Grep,Edit" in text
    assert 'git -C target push origin "HEAD:refs/heads/${HEAD_REF}"' in text
    assert "resolver edited non-conflict path" in text
    assert text.count("secrets.AUTOMERGE_TOKEN || github.token") >= 3
    assert "Skipping stale repair: expected $EXPECTED_SHA, found $current" in text
    assert "Discarding stale repair after concurrent update to $current" in text
    assert "Skipping stale conflict resolution: expected $EXPECTED_SHA, found $current" in text
    assert "Discarding stale conflict resolution after concurrent update to $current" in text
    assert "if: steps.publish.outputs.stale != 'true'" in text
    assert "git -C target push --force" not in text


def test_ai_state_persistence_uses_the_native_github_token():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "steps.claude.outputs.github_token" not in text
    assert text.count("GH_TOKEN: ${{ github.token }}") >= 6


def test_a_review_that_returned_no_verdict_is_not_reported_as_a_source_defect():
    """A failing gate whose summary says everything passed sends people hunting a bug
    that is not there. An unfinished review is an operator failure and must read as one.
    """
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "REVIEW_RESULT: ${{ needs.review.result }}" in text
    # Each review outcome gets its own honest title; only `true` may pass the gate.
    assert 'case "$REVIEW_PASSED" in' in text
    assert "conclusion=success" in text
    assert 'title="PR automation: review findings"' in text
    assert "returned actionable findings" in text
    assert 'title="PR automation: review incomplete"' in text
    assert "infrastructure or operator failure rather than a defect" in text
    assert "API credit balance, credentials, or model availability" in text
    assert '-f "output[title]=${title}"' in text
    assert '-f "output[summary]=${summary} Run ' in text
    assert "review_passed=${REVIEW_PASSED:-<none>}" in text


def test_cancelled_or_pending_evaluations_cannot_publish_a_gate():
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" in text
    assert "types: [opened, reopened, synchronize, ready_for_review]" in text
    assert "github.event.pull_request.number" in text
    assert "github.event.pull_request.head.sha" in text
    assert "always() && !cancelled()" in text
    assert "needs.evaluate.result == 'success'" in text
    assert "needs.evaluate.outputs.state != 'pending'" in text
    assert "needs.evaluate.outputs.state != ''" in text
    assert "needs.evaluate.outputs.evaluated_head_sha == needs.evaluate.outputs.head_sha" in text
    assert "reason=${REASON}" in text
    assert 'select(.state == "open")' in text
    assert "github.event.workflow_run.pull_requests[0].number" in text


def test_draft_evaluation_is_nonterminal_until_ready_draft_promotes_it():
    source = (Path(__file__).resolve().parent.parent / "vibey_gh/pr_automation.py").read_text(
        encoding="utf-8"
    )
    assert 'return result("pending", "pull request is a draft awaiting a stable head")' in source


def test_new_branch_intake_is_draft_idempotent_and_excludes_permanent_branches():
    text = (WORKFLOWS / "branch-intake.yml").read_text(encoding="utf-8")
    assert "github.event.created == true" not in text
    assert "github.event.deleted != true" in text
    assert "gh pr list" in text
    assert "gh pr create" in text and "--draft" in text
    assert "secrets.AUTOMERGE_TOKEN || github.token" in text
    assert "__VIBEY_GH_INTEGRATION_BRANCH__" in text
    assert "__VIBEY_GH_RELEASE_BRANCH__" in text
    assert '"vibey-gh/repair/**"' in text
    assert '"__VIBEY_GH_ISSUE_BRANCH_PREFIX__/**"' in text


@pytest.mark.parametrize("path", WORKFLOW_TEMPLATES, ids=lambda p: p.name)
def test_every_rendered_run_block_is_valid_shell(path):
    """The same argument as the hooks: a broken script fails in somebody else's repo.

    Templates are checked *rendered*, because a marker substituted into the middle of a
    `case` arm or a quoted string is exactly where a syntax error would be introduced.
    """
    import subprocess

    parsed = yaml.safe_load(render_workflow(path, load_config()))
    for job, definition in parsed["jobs"].items():
        for step in definition.get("steps", []):
            script = step.get("run")
            if not script:
                continue
            result = subprocess.run(
                ["bash", "-n"],
                input=script,
                text=True,
                capture_output=True,
                check=False,
            )
            assert result.returncode == 0, f"{path.name}:{job}:{step.get('name')}: {result.stderr}"


def test_the_configured_formatters_agree_with_each_other(tmp_path):
    """`ruff` and `isort` both enforce import order, and left unmatched they disagree.

    A repository whose formatters reject each other's output cannot be made green by any
    number of attempts — which is exactly how an automated repair budget gets spent
    without converging. The shape below is the one that first exposed it: a module
    imported both plainly and under an alias.
    """
    import shutil
    import subprocess

    root = Path(__file__).resolve().parent.parent
    if not shutil.which("ruff") or not shutil.which("isort"):  # pragma: no cover
        pytest.skip("formatters are not installed")
    shutil.copy(root / "pyproject.toml", tmp_path / "pyproject.toml")
    probe = tmp_path / "probe.py"
    probe.write_text(
        "from __future__ import annotations\n\n"
        "from vibey_gh import github_release, merge_train\n"
        "from vibey_gh import realign as realign_mod\n"
        "from vibey_gh import reconcile\n\n"
        "USED = (github_release, merge_train, realign_mod, reconcile)\n",
        encoding="utf-8",
    )

    def run(*command):
        return subprocess.run(command, cwd=tmp_path, capture_output=True, check=False)

    run("isort", "-q", str(probe))
    run("ruff", "check", "--fix", "-q", str(probe))
    run("isort", "-q", str(probe))
    settled = probe.read_text(encoding="utf-8")

    assert run("ruff", "check", str(probe)).returncode == 0, "ruff rejects isort's output"
    assert run("isort", "--check-only", str(probe)).returncode == 0, "isort rejects ruff's"
    # And the pair is stable: another pass of either changes nothing.
    run("ruff", "check", "--fix", "-q", str(probe))
    run("isort", "-q", str(probe))
    assert probe.read_text(encoding="utf-8") == settled, "the formatters oscillate"


def test_a_solution_attempt_that_produced_nothing_still_says_so_on_the_issue():
    """Silence costs the same tokens and minutes as a refusal but leaves the issue looking
    untouched, so nobody knows an attempt was made or why it stopped."""
    text = (WORKFLOWS / "issue-automation.yml").read_text(encoding="utf-8")
    assert "AGENT_RESULT: ${{ steps.claude.outcome }}" in text
    assert 'if [ -z "${STRUCTURED:-}" ]; then' in text
    assert "vibey-gh-issue-attempt-failed" in text
    assert "returned no result (agent step: ${AGENT_RESULT})" in text
    # The advice names the cause the observed failure actually had.
    assert "too large to complete in one attempt" in text
    assert "exhausted API credit balance" in text
    # Commented exactly once, and the issue is labelled so it is visible in a listing.
    assert 'grep -Fq "$marker"' in text
    assert "--add-label vibey-gh:solve-blocked" in text
    # The turn budget is configuration, not a constant nobody can reach.
    assert "--max-turns __VIBEY_GH_ISSUE_MAX_TURNS__" in text


def test_the_repair_job_normalizes_formatting_it_cannot_ask_the_agent_to_run():
    """The agent has no shell, so formatting is the one failure it cannot fix itself."""
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert "Normalize formatting deterministically" in text
    assert "working-directory: target" in text
    assert "ruff check --fix ." in text
    assert "isort ." in text
    assert "black ." in text
    # It must read the repository's own settings rather than guess, and run before the
    # commit that publishes the repair.
    assert text.index("Normalize formatting") < text.index("Publish one guarded repair commit")
    assert "python -m pip install --quiet -e ./target" not in text
    assert "do not execute repository code" in text.lower()


@pytest.mark.parametrize("name", ["pre-push", "commit-msg"])
def test_every_shipped_hook_is_valid_shell(name):
    import subprocess

    result = subprocess.run(
        ["sh", "-n", str(TEMPLATES / name)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_the_merge_train_does_not_filter_on_the_triggering_runs_conclusion():
    """Observed in production: every PR held green and unmerged while credits were out.

    "PR automation" concludes `failure` whenever its exact-head review job fails — which
    is precisely the case the local review fallback exists to cover. The fallback then
    succeeds, publishes a green `PR automation / gate`, and the run as a whole still ends
    `failure` because one job in it did. Filtering the merge train on that conclusion
    skipped it on every such pull request and defeated the fallback at the last step.

    Nothing is relaxed by its absence: `judge()` re-reads each pull request and requires a
    completed, successful gate before merging, which is asserted separately.
    """
    spec = yaml.safe_load((WORKFLOWS / "merge-train.yml").read_text(encoding="utf-8"))
    assert "conclusion" not in str(spec["jobs"]["merge"].get("if", ""))


@pytest.mark.parametrize("name", sorted(p.name for p in WORKFLOWS.glob("*.yml")))
def test_no_rendered_workflow_carries_trailing_whitespace(name, tmp_path):
    """Rendered, not just authored — the defect only appears after substitution.

    Every template is clean in source, so checking the templates proves nothing. A
    placeholder that renders empty mid-line leaves the space that separated it from the
    previous argument dangling: `__VIBEY_GH_DOC_SITE_REQUIREMENTS__` did exactly that with
    the default empty `site_requirements`, which is the default path, not an edge case.

    It matters because `installed()` compares byte-for-byte and the near-universal
    `trailing-whitespace` pre-commit hook strips that space on the adopting repository's
    next commit — after which `check` reports the file out of date and the pre-push hook
    refuses the push. A formatting hook silently breaking provenance. Five repositories hit
    it while adopting 1.38.0.
    """
    from vibey_gh.install import render_workflow

    rendered = render_workflow(WORKFLOWS / name, GhConfig(root=tmp_path))
    offenders = [
        (number, line)
        for number, line in enumerate(rendered.split("\n"), 1)
        if line != line.rstrip()
    ]
    assert not offenders, f"{name} renders trailing whitespace at {[n for n, _ in offenders]}"


def test_the_issue_triage_fallback_renders_only_when_enabled(tmp_path):
    """The issue path's counterpart to the review fallback, with a smaller contract: it
    posts one deduplicated analysis comment and never writes code — a local model must not
    inherit the write access the paid solver earned. Doctrine 8.a made this lane render on
    by DEFAULT; explicitly disabled it renders `false &&`, so the job exists but can never
    run. Either way it is additionally gated on the sovereign readiness probe, so an
    enabled lane with no runner online is skipped rather than queued forever."""
    from vibey_gh.config import GhConfig, IssueAutomationConfig
    from vibey_gh.install import render_workflow

    source = WORKFLOWS / "issue-automation.yml"
    off = render_workflow(
        source,
        GhConfig(root=tmp_path, issue_automation=IssueAutomationConfig(fallback_enabled=False)),
    )
    assert "Local triage fallback" in off
    assert "false &&" in off.split("solve-fallback:")[1].split("runs-on:")[0]

    on = render_workflow(source, GhConfig(root=tmp_path))
    section = on.split("solve-fallback:")[1]
    assert "true &&" in section.split("runs-on:")[0]
    assert "sovereign_ready == 'true'" in section.split("runs-on:")[0]
    assert "vibey-local" in section.split("permissions:")[0]
    # The comment is deduplicated by marker, and the job never pushes code.
    assert "vibey-gh:local-triage" in section
    assert "issues: write" in section
    assert "contents: write" not in section


def test_seo_metadata_is_rendered_configurably(tmp_path):
    """The site ships complete search and social metadata with zero configuration — the
    defaults derive from the repository (GitHub's generated OpenGraph card, repo-derived
    keywords) — and every field is overridable from [documentation]."""
    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import _favicon_links, render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    plain = render_workflow(source, GhConfig(root=tmp_path))
    # Defaults: emoji favicon becomes a data-URI link pair; og:image falls back to
    # GitHub's card at runtime, so the template must carry the fallback expression.
    assert "data:image/svg+xml," in plain
    assert "opengraph.githubassets.com" in plain
    assert "SEO_KEYWORDS=''" in plain

    configured = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(
                favicon="https://example.com/icon.png",
                og_image="https://example.com/card.png",
                twitter_site="@vibey",
                keywords=("alpha", "beta"),
                author="A. Person",
                theme_color="#123abc",
                locale="de_DE",
            ),
        ),
    )
    assert 'href="https://example.com/icon.png"' in configured
    assert "SEO_OG_IMAGE='https://example.com/card.png'" in configured
    assert "SEO_TWITTER_SITE='@vibey'" in configured
    assert "SEO_KEYWORDS='alpha,beta'" in configured
    assert "SEO_AUTHOR='A. Person'" in configured
    assert "SEO_THEME_COLOR='#123abc'" in configured
    assert "SEO_LOCALE='de_DE'" in configured

    # The pure helper: emoji in, matching icon+touch-icon pair out; URLs verbatim.
    pair = _favicon_links("⚙️")
    assert pair.count("data:image/svg+xml,") == 2 and "apple-touch-icon" in pair
    assert _favicon_links("") == ""
    assert _favicon_links("/img/fav.ico") == '<link rel="icon" href="/img/fav.ico">'


def test_seo_fields_refuse_html_injection():
    """These strings land verbatim in rendered pages and workflow YAML; the cheap
    injections are refused at load time rather than discovered on a published site."""
    import pytest as _pytest

    from vibey_gh.config import DocumentationConfig

    with _pytest.raises(ValueError, match="must not contain HTML"):
        DocumentationConfig(author='"><script>x</script>')
    with _pytest.raises(ValueError, match="theme_color"):
        DocumentationConfig(theme_color="blue")
    with _pytest.raises(ValueError, match="plain words"):
        DocumentationConfig(keywords=("ok", "<bad>"))


def test_the_fallback_reconstructs_a_diff_the_api_refuses(tmp_path):
    """GitHub's diff API refuses pull requests beyond roughly 300 files — exactly the
    shape of a migration sweep, observed on a 347-file provenance sweep that could
    therefore never be reviewed at all. The fallback must reconstruct the same merge-base
    diff from fetched refs: read-only, no repository code executed, and --max-chars still
    caps what reaches the model."""
    from vibey_gh.install import render_workflow

    text = render_workflow(WORKFLOWS / "pr-automation.yml", GhConfig(root=tmp_path))
    section = text.split("Fetch the exact-head diff")[1].split("Review with the local model")[0]
    assert "gh pr diff" in section
    assert "reconstructing locally" in section
    assert "merge-base" in section
    # Shallow trusted checkouts must deepen until the histories connect, never guess.
    assert "--unshallow" in section
    assert 'git -C automation diff "$merge_base" "$head_sha"' in section


def test_search_console_verification_survives_redeploys(tmp_path):
    """An uploaded verification FILE is wiped every time release-surfaces rebuilds the
    Pages root — observed as a repeatedly un-verifiable property. The HTML-tag token is
    configuration, rendered into every page and the channel index, so verification
    survives every deploy. Unset, nothing renders."""
    from vibey_gh.config import DocumentationConfig, GhConfig
    from vibey_gh.install import render_workflow

    source = WORKFLOWS / "release-surfaces.yml"
    off = render_workflow(source, GhConfig(root=tmp_path))
    assert "SEO_SITE_VERIFICATION=''" in off
    assert 'name="google-site-verification"' in off  # the injector line, gated at runtime
    assert 'content=""' not in off.split("<title>")[0]

    on = render_workflow(
        source,
        GhConfig(
            root=tmp_path,
            documentation=DocumentationConfig(google_site_verification="tok_ABC-123"),
        ),
    )
    assert "SEO_SITE_VERIFICATION='tok_ABC-123'" in on
    # the channel index carries the full static tag
    assert '<meta name="google-site-verification" content="tok_ABC-123">' in on


def test_search_console_token_refuses_a_whole_tag():
    """People paste the whole <meta> tag; the loader demands the bare token so the render
    cannot double-wrap it into broken HTML."""
    import pytest as _pytest

    from vibey_gh.config import DocumentationConfig

    with _pytest.raises(ValueError, match="bare token"):
        DocumentationConfig(google_site_verification='<meta name="google-site-verification">')


def test_the_gate_tells_a_local_decline_apart_from_no_verdict_at_all():
    """Three states, not two. `FALLBACK_PASSED` can be `true` (local pass), `false` (the
    local lane RAN and reported a blocking finding), or empty (nothing reviewed).

    Collapsing the middle case into the last one is not a wording nit — it inverts the
    message. Observed live on a release promotion: the gate said "an infrastructure or
    operator failure rather than a defect in the pull request. Check the review job log
    for API credit balance", while a reported blocking finding sat unmentioned in the
    fallback job's log. The operator is sent to look at billing instead of at the finding.

    The finding in that case turned out to be a false positive on a truncated diff, which
    is the argument for pointing the reader AT it: a lead they can check in a minute
    beats a claim that nothing was found.
    """
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    assert '[ "$FALLBACK_PASSED" = true ]' in text
    assert '[ -n "$FALLBACK_PASSED" ]' in text
    assert "local fallback found a blocking defect" in text
    # The decline branch must send the reader to the evidence, and must not claim the
    # weaker reviewer's verdict is authoritative.
    decline = text.split('elif [ -n "$FALLBACK_PASSED" ]')[1].split("else")[0]
    assert "Local review fallback" in decline and "TRUNCATED" in decline
    assert "a lead, not a ruling" in decline
    # The genuine no-verdict branch keeps the infrastructure wording, and now says
    # explicitly that the local lane produced nothing either.
    incomplete = text.split('title="PR automation: review incomplete"')[1][:600]
    assert "no local fallback verdict was produced either" in incomplete


def test_a_decline_with_nothing_to_point_at_is_not_called_a_defect():
    """Four states, not three — found by running the real thing.

    After the prompt learned that `${{ secrets.NAME }}` is not an exposure, the same diff
    that had produced a confident false positive came back `pass=false` with **zero
    findings** and a summary explaining it: "the diff was truncated, so only a partial
    review was conducted… no concrete defects were found in the visible changes".

    That is the reviewer declining to certify, not accusing the change of anything. Calling
    it "found a blocking defect" would send someone hunting for a finding that does not
    exist — the same class of misdirection as the bug this branch's predecessor fixed, one
    step further in.
    """
    text = (WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8")
    jobs = yaml.safe_load(text)["jobs"]
    # Asserted on the fallback job ITSELF. A substring search for the output line matched
    # the paid review job's identical declaration instead, so this test passed for as long
    # as the fallback never declared the output -- and the gate read an empty count, which
    # turned every local decline into "could not complete the review".
    assert jobs["review-fallback"]["outputs"]["findings"] == "${{ steps.result.outputs.findings }}"
    fallback = next(s for s in jobs["review-fallback"]["steps"] if s.get("id") == "result")
    assert 'echo "findings=' in fallback["run"]
    gate_env = jobs["gate"]["steps"][0]["env"]
    assert gate_env["FALLBACK_FINDINGS"] == "${{ needs.review-fallback.outputs.findings }}"
    assert '[ "${FALLBACK_FINDINGS:-0}" -gt 0 ]' in text
    assert "local fallback could not complete the review" in text

    cannot = text.split('title="PR automation: local fallback could not complete the review"')[1]
    cannot = cannot.split("else")[0]
    assert "WITHOUT reporting any finding" in cannot
    assert "not a defect claim about the change" in cannot
    assert "split the pull request" in cannot


def test_both_review_lanes_write_every_output_they_declare():
    """A declared output nothing writes is always empty, and an empty string reads as an
    answer: `passed == ''` is how the gate recognises "no verdict at all". Both review jobs
    count their findings the same way, so the next step -- a gate that names which lane
    carried which half of the verdict -- has the same fact from each."""
    jobs = yaml.safe_load((WORKFLOWS / "pr-automation.yml").read_text(encoding="utf-8"))["jobs"]
    for name in ("review", "review-fallback"):
        result = next(s for s in jobs[name]["steps"] if s.get("id") == "result")
        for output in ("passed", "findings"):
            assert jobs[name]["outputs"][output] == f"${{{{ steps.result.outputs.{output} }}}}"
            assert f'echo "{output}=' in result["run"], f"{name} never writes {output}"


@pytest.mark.parametrize("path", WORKFLOW_TEMPLATES, ids=lambda p: p.name)
def test_every_needs_output_a_workflow_reads_is_declared_by_that_job(path):
    """GitHub evaluates `needs.<job>.outputs.<name>` to an empty string when the job never
    declared `<name>` -- no error, no warning, just a value that looks like an answer. That
    is exactly how the gate's fallback-findings branch sat dead: the fallback job wrote the
    count, never declared it, and the gate read ''. `actionlint` reports this as an
    undefined property; this is the same check, where it cannot be skipped."""
    rendered = render_workflow(path, GhConfig(root=Path(".")))
    jobs = yaml.safe_load(rendered)["jobs"]
    for job, output in re.findall(r"needs\.([\w-]+)\.outputs\.([\w-]+)", rendered):
        declared = jobs[job].get("outputs") or {}
        assert output in declared, f"{path.name}: needs.{job}.outputs.{output} is never declared"


def _restore_decision_block() -> str:
    """The `restored != true` branch of release-surfaces' channel-restore step.

    Taken from the RENDERED workflow rather than the template, because the rendered file is
    what actually runs, and extracted by its own markers so that a rewrite of the block
    fails this extraction loudly instead of silently testing nothing.
    """
    rendered = Path(__file__).resolve().parent.parent / ".github/workflows/release-surfaces.yml"
    parsed = yaml.safe_load(rendered.read_text(encoding="utf-8"))
    script = next(
        step["run"]
        for job in parsed["jobs"].values()
        for step in job.get("steps", [])
        if step.get("name", "").startswith("Restore the other release channel")
    )
    lines = script.split("\n")
    start = next(i for i, line in enumerate(lines) if 'if [ "$restored" != true ]' in line)
    depth = 0
    for end, line in enumerate(lines[start:], start):
        stripped = line.strip()
        depth += stripped.startswith("if ")
        depth -= stripped == "fi"
        if depth == 0:
            break
    else:  # pragma: no cover - the extraction below asserts this never happens
        raise AssertionError("the restore decision block is not closed")
    return "\n".join(lines[start : end + 1])


@pytest.mark.parametrize(
    "probe, curl_exit, expect_exit, expect_removed",
    [
        ("200", 0, 1, False),  # live — refuse, this deploy would destroy it
        ("301", 0, 1, False),  # redirect is still something being served
        ("403", 0, 1, False),  # reachable but not readable: not proof of absence
        ("500", 0, 1, False),  # the server is unwell, which proves nothing
        ("000", 7, 1, False),  # transport failure: no answer at all
        ("404", 0, 0, True),  # the only answer that proves it was never published
    ],
)
def test_the_channel_restore_only_treats_an_explicit_404_as_absence(
    tmp_path, probe, curl_exit, expect_exit, expect_removed
):
    """`curl -f` exits non-zero for a timeout, a DNS or TLS failure, a 403 and a 500 alike,
    so keying the decision on its exit status reads a transient blip as "never published"
    and deletes a live channel — failing OPEN in the guard whose whole job is to fail
    closed. Only an explicit 404 may reach the `rmdir`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "curl").write_text(f'#!/bin/sh\nprintf %s "{probe}"\nexit {curl_exit}\n')
    (bin_dir / "curl").chmod(0o755)
    (tmp_path / "pages" / "main").mkdir(parents=True)

    script = "set -euo pipefail\nrestored=false\n" + _restore_decision_block()
    result = subprocess.run(
        ["bash", "-c", script],
        check=False,  # the exit status IS the assertion
        cwd=tmp_path,
        capture_output=True,
        text=True,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "OTHER_CHANNEL": "main",
            "OTHER_BRANCH": "main",
            "OTHER_CHANNEL_URL": "https://example.invalid/vibey/main/",
        },
    )
    assert result.returncode == expect_exit, result.stderr or result.stdout
    assert (not (tmp_path / "pages" / "main").exists()) is expect_removed
    if expect_exit:
        assert "refusing to replace it with an empty directory" in result.stdout
