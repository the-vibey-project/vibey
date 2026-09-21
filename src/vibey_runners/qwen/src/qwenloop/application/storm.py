# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Storm-mode plan text: one repo's open backlog turned into one qwenloop plan.

Storm mode deliberately stays focused on the live issue and pull-request backlog. A
paper or book is work only when a listed backlog item explicitly requires it; generic
documentation sweeps distract a local model from the work the operator asked it to do.
"""

from qwenloop.domain.model import RepoItem

StormPlan = tuple[str, str]


_CDD_PROTOCOL = """## Convergence-Driven Development (CDD)
CDD is the delivery loop above Specification-Driven Development (SDD) and
Test-Driven Development (TDD). SDD supplies the intent and acceptance criteria;
TDD supplies executable checks; CDD repeatedly reconciles the actual repository
with both until the feature is genuinely deliverable.

For this item, follow this order: ground yourself in the tracked repository
layout and its existing tests; map every acceptance criterion to actual code,
tests, and evidence; implement in the repository's real language and package
boundaries; run the focused tests and relevant gates; inspect the diff and
working tree for unrelated artifacts; then repair any failed criterion. Never
invent a new language, manifest, source tree, or platform merely because the
issue text uses a different term. The tracked repository is the authority on
where the feature belongs.

At every iteration, explicitly classify the trajectory as CONVERGING, NEUTRAL,
or DIVERGING against the remaining acceptance criteria and failing checks at all
four nested scopes: overall project vision, phase or milestone vision, feature
set or epic, and feature, unit, or user story. A locally converging item must
not conceal divergence at a wider scope. Treat these scopes as concentric
orbits: seek a lower unresolved-work state at every level. A small divergence
is allowed only when its bounded next step has an explicit path back to a more
convergent state. A large divergence, or any divergence without a credible
reconvergence path, must be abandoned and the work returned to the last sound
state. Never infer convergence from activity, file count, token use, or a
completion marker.

If this repository participates in a multi-project product or platform, also
inspect the software chemical structure around it. Interfaces, dependencies,
data ownership, security, release timing, and operational contracts can create
unique molecule-level properties; a locally converging atom must not hide a
diverging composition. Any interaction divergence needs a bounded
reconvergence path.

When enough interacting chemicals form a suite of suites, inspect it as a
software organism and state whether it is alive in the digital realm: identity,
resource metabolism, sensing and memory, homeostasis, adaptation and repair,
and reproduction or exchange must be grounded in observable contracts and
operating signals. This is a systems claim, not a claim of carbon biology or
subjective experience. The World Wide Web is the largest familiar example of
this higher-order structure. A locally converging project cannot conceal an
organism-level loss of coherence, feedback, repair or delivery.

The final plain-text qwenloop-verdict must contain these fields: criteria,
tests, repository, levels, trajectory, composition, and delivery. Composition
must say whether this item is an atom, part of a multi-project chemical
structure, or part of a higher-order software organism, and describe the
interaction trajectory (or explicitly say not applicable). Delivery must state whether
the change is verified and commit-ready; remote push and pull-request publication
remain an explicit operator-authorized step unless the caller selected a
publish mode. Do not claim completion while any criterion is unverified or
blocked, and do not move to another backlog item until this one has converged
or has been reported as a concrete blocker.
"""


def _indent_body(body: str) -> str:
    return body.replace("\n", "\n  ")


def _render_items(items: list[RepoItem] | None, unavailable_message: str) -> str:
    """Format an issue/PR list for the plan.

    None (the fetch failed, or issues/PRs are disabled) renders as `unavailable_message`.
    An empty list (the fetch succeeded; there is simply nothing open) renders as nothing,
    the same way the bash script's `gh ... --jq` pipeline produced no output for zero
    results without ever reaching its `|| echo` fallback.

    The return value always either is empty or ends with its own trailing newline, exactly
    like the bash script's per-item jq output and its `echo` fallback both did — so the
    caller can join sections with a single separating "\n" and get one blank line between
    them regardless of which case applies.
    """
    if items is None:
        return f"{unavailable_message}\n"
    if not items:
        return ""
    return "\n".join(
        f"- #{item.number} {item.title}\n\n  {_indent_body(item.body)}\n"
        for item in sorted(items, key=lambda item: item.number)
    )


def build_plan(
    *,
    repo: str,
    issues: list[RepoItem] | None,
    pull_requests: list[RepoItem] | None,
    author: str,
    repository_context: str = "",
) -> str:
    """Build the qwenloop plan text for one repo's storm-mode run."""
    issues_block = _render_items(issues, "(none, or issues disabled)")
    prs_block = _render_items(pull_requests, "(none)")
    context = (
        repository_context.strip()
        or "Repository grounding was unavailable; inspect git-tracked files first."
    )
    return (
        f"# qwenstorm plan for {repo}\n\n"
        "## 1. Clear the backlog\n"
        "This section is mandatory and is the only active workstream. Do not start a\n"
        "generic paper or book sweep: handle those only when a listed backlog item\n"
        "explicitly requires it. The first tool call must inspect source or tests relevant to the first\n"
        "listed backlog item, not general documentation.\n"
        "Work every open issue and PR below locally, one item at a time, smallest first.\n"
        "For each item, inspect the current source and relevant tests/docs, implement or\n"
        "verify the appropriate change, run a focused test, and then continue to the next\n"
        "item. The operator will handle commits, pull requests, merges, and issue state;\n"
        "never push, create a pull request, mutate GitHub, switch branches, or pull from\n"
        "the network from inside the run. Do not claim an item is merged or closed: report\n"
        "what was implemented, verified, blocked, or still open. The first action must\n"
        "inspect repository source or tests with a coding tool, not emit a completion\n"
        "marker. The qwenloop-verdict label is a plain-text final fence, never a tool.\n\n"
        f"{_CDD_PROTOCOL}\n"
        f"### Repository grounding\n{context}\n\n"
        "### Open issues\n"
        f"{issues_block}"
        "\n### Open PRs\n"
        f"{prs_block}"
        "\n## Completion\n"
        "Only finish after every listed issue and PR has a local outcome. If an item is\n"
        "already satisfied, verify it with source/tests and say so; if it is blocked,\n"
        "record the concrete blocker. Never emit the completion marker after inspection\n"
        "alone.\n"
    )


def build_item_plans(
    *,
    repo: str,
    issues: list[RepoItem] | None,
    pull_requests: list[RepoItem] | None,
    author: str,
    repository_context: str = "",
) -> list[StormPlan]:
    """Split one live backlog into bounded plans, one issue or PR per model run.

    A fetch failure remains one diagnostic plan so the caller reports it honestly. A
    successful empty fetch returns no plans, while a populated fetch keeps each model
    context focused on one item instead of asking a local model to hold the whole repo's
    backlog and unrelated documentation in one transcript.
    """
    if issues is None or pull_requests is None:
        return [
            (
                "backlog",
                build_plan(
                    repo=repo,
                    issues=issues,
                    pull_requests=pull_requests,
                    author=author,
                    repository_context=repository_context,
                ),
            )
        ]
    plans: list[StormPlan] = []
    for item in sorted(issues, key=lambda candidate: candidate.number):
        plans.append(
            (
                f"issue#{item.number}",
                build_plan(
                    repo=repo,
                    issues=[item],
                    pull_requests=[],
                    author=author,
                    repository_context=repository_context,
                ),
            )
        )
    for item in sorted(pull_requests, key=lambda candidate: candidate.number):
        plans.append(
            (
                f"pr#{item.number}",
                build_plan(
                    repo=repo,
                    issues=[],
                    pull_requests=[item],
                    author=author,
                    repository_context=repository_context,
                ),
            )
        )
    return plans
