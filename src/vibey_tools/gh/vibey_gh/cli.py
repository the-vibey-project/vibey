# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh` — the command the hooks and the CI workflows call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from vibey_gh import (
    conversation,
    debugging,
    documentation,
    fingerprints,
    flatten,
    github_release,
    install,
    issue_automation,
    merge_train,
    operation_estimate,
    pr_automation,
    promote,
    realign,
    reconcile,
    rulesets,
    surfaces,
    versioning,
)
from vibey_gh.approval_check import ApprovalCheck
from vibey_gh.config import load_config
from vibey_gh.fallback_pin import FallbackPinResolver
from vibey_gh.interfaces.fallback_pin_resolver_interface import FallbackPinResolverInterface
from vibey_gh.interfaces.marketplace_renderer_interface import MarketplaceRendererInterface
from vibey_gh.interfaces.paper_interface import RevisionReaderInterface
from vibey_gh.review_composition import PAID_HALVES, REVIEW_COMPOSER


def _cloud_clutter(cfg, surveyed: bool) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Sub-doctrine 9.a's cloud clutter classes, named for `check`: merged-and-undeleted
    remote branches (a closed pull request's head among them, once its work landed),
    draft releases, orphan tags. Returns `(clutter, unsurveyable)` — the second is why
    the survey could not judge, which is a notice and never a verdict.

    Reporting only, and read-only twice over. `check` is what a hook and every pull
    request and every promotion run, so it deletes nothing, ever — `vibey-gh tidy
    --apply` is the only thing that removes anything — and it passes `refresh=False`
    so the survey does not `fetch --prune` either. A verification command does not
    mutate the clone it is verifying, not even its remote-tracking refs, and not even
    helpfully: someone's stale `origin/*` landmarks are theirs. The cost is that a
    long-unfetched clone judges the refs it already has, which can only misreport, and
    a misreport here is an advisory line by default.

    Surveyed under `--ci` alone: one survey costs two `gh` calls, which a pre-commit
    hook must not pay, and the local classes need a durable clone to mean anything.
    Module-level to match every other `check` collaborator here, which argparse
    dispatch already makes module-level functions.
    """
    if not surveyed or not cfg.tidy.enabled:
        return (), ()
    from vibey_gh import tidy

    report = tidy.survey(cfg, local=False, refresh=False)
    clutter = tuple(
        f"{label}: {', '.join(items)}"
        for label, items in (
            ("merged remote branches, never deleted", report.remote_merged),
            ("draft releases", report.draft_releases),
            ("orphan tags", report.orphan_tags),
        )
        if items
    )
    return clutter, report.problems


def _check(args, resolver: FallbackPinResolverInterface | None = None) -> int:
    cfg = load_config()
    # Resolved once, so the drift verdict and the notice below describe the same pin.
    pin = (resolver or FallbackPinResolver()).resolve(cfg)
    ok, problems = install.installed(cfg, local=not args.ci, fallback_pin=pin)
    report = fingerprints.check(cfg, rev_range=args.commits, apply=args.apply)
    docs = documentation.check(cfg)
    scan = pr_automation.check_scan_workflows(cfg)
    # The root marketplace is a rendered file like the workflows: when the repository
    # declares members, the manifest on disk must be what they render to.
    marketplace_ok, marketplace_problem = True, ""
    if cfg.marketplace.members:
        from vibey_gh.marketplace import MarketplaceRenderer

        marketplace_ok, marketplace_problem = MarketplaceRenderer().check(cfg)
    # `--quiet` prints nothing, so two forge round trips are worth paying for only when
    # they can still move the exit code — which is exactly when `[tidy] fail_check` is on.
    clutter, unsurveyable = _cloud_clutter(
        cfg, surveyed=args.ci and (not args.quiet or cfg.tidy.fail_check)
    )
    clutter_ok = not clutter or not cfg.tidy.fail_check
    clean = ok and report.ok and docs.ok and scan.ok and marketplace_ok and clutter_ok

    if args.quiet:
        return 0 if clean else 1

    for problem in problems:
        print(f"  hooks: {problem}", file=sys.stderr)
    for path in report.missing_header:
        print(f"  {path.relative_to(cfg.root)}: missing the fingerprint header", file=sys.stderr)
    for path in report.superseded_header:
        print(
            f"  {path.relative_to(cfg.root)}: carries a superseded fingerprint header "
            "(`check --apply` replaces it with the current one)",
            file=sys.stderr,
        )
    for path in report.duplicate_header:
        print(
            f"  {path.relative_to(cfg.root)}: fingerprint header appears more than once",
            file=sys.stderr,
        )
    for commit in report.missing_trailer:
        print(f"  commit {commit}: missing the `{cfg.trailer_key}:` trailer", file=sys.stderr)
    for commit in report.invalid_subject:
        print(f"  commit {commit}: subject is not a Conventional Commit", file=sys.stderr)
    for problem in report.branch_logging:
        print(f"  debug logging: {problem}", file=sys.stderr)
    for problem in docs.problems:
        print(f"  documentation: {problem}", file=sys.stderr)
    for problem in scan.problems:
        print(f"  {problem}", file=sys.stderr)
    if not marketplace_ok:
        print(f"  marketplace: {marketplace_problem}", file=sys.stderr)
    for problem in unsurveyable:
        print(f"  clutter: not surveyed — {problem}", file=sys.stderr)
    for item in clutter:
        print(f"  clutter: {item}", file=sys.stderr)
    if clutter:
        print(
            "  clutter: `vibey-gh tidy --apply` removes the provably-lossless classes"
            + ("" if cfg.tidy.fail_check else " (advisory; `[tidy] fail_check = true` fails)"),
            file=sys.stderr,
        )
    # Advisory, never a verdict: a floating install still resolves. Printed because a pin
    # that cannot resolve renders floating, so a deployed workflow that still carries the
    # pin reads "out of date" above with no cause named, and a drift report with no cause
    # named is how one diagnosis went through three wrong hypotheses (#273).
    if pin.notice:
        print(f"  notice: {pin.notice}", file=sys.stderr)

    if clean:
        scope = f"{report.checked_files} source file(s)"
        if args.commits:
            scope += f" and every commit in {args.commits}"
        print(f"vibey-gh: ok — hooks installed; {scope} carry the fingerprint")
        return 0

    print("\nvibey-gh: FAILED", file=sys.stderr)
    print(f"\n  header:  {cfg.header}", file=sys.stderr)
    print(f"  trailer: {cfg.trailer}", file=sys.stderr)
    print(
        "\n  `vibey-gh check --apply` adds missing headers; `vibey-gh install` installs the hooks.",
        file=sys.stderr,
    )
    return 1


def _install(args, resolver: FallbackPinResolverInterface | None = None) -> int:
    cfg = load_config()
    pin = (resolver or FallbackPinResolver()).resolve(cfg)
    for action in install.install(cfg, fallback_pin=pin):
        print(f"  {action.hook}: {action.outcome}")
    for notice in install.installation_notices():
        print(f"  notice: {notice}")
    if pin.notice:
        print(f"  notice: {pin.notice}")
    print(f"vibey-gh: installed into {cfg.root}")
    return 0


def _conventional_message(args) -> int:
    if args.file:
        message = args.file.read_text(encoding="utf-8")
        args.file.write_text(fingerprints.normalize_commit_message(message), encoding="utf-8")
    else:
        print(fingerprints.normalize_commit_message(sys.stdin.read()), end="")
    return 0


def _conventional_check(args) -> int:
    invalid = fingerprints.commits_with_invalid_subject(args.commits, load_config())
    for commit in invalid:
        print(commit)
    return 1 if invalid else 0


def _version(args) -> int:
    cfg = load_config(config=args.config)
    if args.dev is not None:
        dev = versioning.dev_version(cfg, args.dev)
        if args.apply:
            versioning.apply_version(cfg, dev)
        print(dev)
        return 0
    new, why = versioning.decide(cfg, args.since)
    if args.explain or not new:
        print(f"vibey-gh: {why}", file=sys.stderr)
    if not new:
        print("none")
        return 0
    if args.apply:
        versioning.apply_version(cfg, new)
    print(new)
    return 0


def _summary_rows(rows: list[tuple[int, str, str]], merged: int, skipped: int) -> str:
    """A markdown table for the job summary. A run that merged nothing still has to say
    what it looked at, or the only way to find out is to read the log."""
    lines = ["| PR | Title | Outcome |", "|---|---|---|"]
    lines += [f"| #{n} | {t} | {outcome} |" for n, t, outcome in rows]
    lines += ["", f"Merged {merged}, skipped {skipped}."]
    return "\n".join(lines) + "\n"


def _merge_train(args) -> int:
    cfg = load_config()
    prs = (
        merge_train.open_pull_requests(cfg, number=args.pr)
        if args.pr is not None
        else merge_train.open_pull_requests(cfg)
    )
    if not prs:
        print(f"vibey-gh: no open pull requests into {cfg.integration_branch}")
        _write_summary(args, "No open pull requests.\n")
        return 0

    merged = skipped = 0
    rows: list[tuple[int, str, str]] = []
    for pr in prs:
        v = merge_train.judge(pr, cfg)

        if not v.ready:
            # A conflicting or behind head is the one obstacle the train can clear for
            # itself, and the one it used to hand straight back. Every merge into the
            # integration branch puts the NEXT pull request behind it, so a train that
            # refuses to restack merges exactly one change per run and asks a person to
            # unblock every subsequent one by hand -- the conflict is manufactured by the
            # train's own previous merge. `merge_forward` merges locally, where this
            # repository's merge drivers apply, and pushes an ordinary commit.
            #
            # The restacked pull request is NOT merged on this pass. Its tree just
            # changed, so its green checks describe a tree that no longer exists; the
            # next train takes it once they have re-run against what is actually there.
            if v.restackable and cfg.restack_conflicts and not args.dry_run:
                head = str(pr.get("headRefName") or "")
                try:
                    moved, detail = reconcile.merge_forward(cfg, head)
                except ValueError as exc:
                    # A protected or otherwise unwritable ref. Never a reason to stop the
                    # train; the pull request is simply reported as it was before.
                    moved, detail = False, str(exc)
                if moved:
                    note = f"restacked — {detail}; merges once its checks re-run"
                    print(f"  #{v.number} {note}")
                    rows.append((v.number, v.title, note))
                    skipped += 1
                    continue
                v.reason = f"{v.reason} (restack declined: {detail})"
            # Only a pull request holding outside code -- an author not in
            # `trusted_authors`, or the external-repair label -- gets labelled and
            # announced, approved or not and whatever its gates say: the train will never
            # merge it, so a person must. A draft or a red build is the contributor's to
            # fix and needs no notification; this one waits on somebody who does not
            # know yet (ADR-0053).
            if v.held_for_review and not args.dry_run and args.label != "":
                merge_train.hold_for_review(v, cfg, label=args.label)
            print(f"  #{v.number} skipped — {v.reason}")
            rows.append((v.number, v.title, f"skipped — {v.reason}"))
            skipped += 1
            continue

        if args.dry_run:
            print(f"  #{v.number} would merge ({args.method})")
            rows.append((v.number, v.title, f"would {args.method}-merge"))
            continue

        method = merge_train.method_for(pr, cfg, args.method)
        # A squash commit takes its body from the pull request, and a bot's pull request
        # never carries the Made-With trailer — so supply a body that does, or the
        # provenance check rejects the very commit this train creates. A rebase preserves
        # the branch's own commits, which the push hooks already stamped.
        squash_body = None
        if method == "squash" and cfg.trailer not in (pr.get("body") or ""):
            existing = (pr.get("body") or "").strip()
            squash_body = (existing + "\n\n" if existing else "") + cfg.trailer
        ok, bypassed, error = merge_train.merge(
            v.number, method, squash_body, admin_fallback=args.admin_fallback
        )
        if ok:
            note = " (review requirement bypassed)" if bypassed else ""
            cleanup = ""
            if merge_train.should_delete_head(pr, cfg):
                cleanup = (
                    "; deleted merged topic branch"
                    if merge_train.delete_head_branch(pr)
                    else "; topic-branch cleanup failed"
                )
            print(f"  #{v.number} {method}-merged{note}{cleanup}")
            rows.append((v.number, v.title, f"{method}-merged{note}{cleanup}"))
            merged += 1
        else:
            # The stderr is the diagnosis: "refused it" alone once cost an hour of
            # ruleset archaeology when the real cause was a token missing the repository.
            # Without `--admin-fallback` a refusal is the gate working, not a fault: the
            # pull request waits for a person and the pass carries on (ADR-0053, 12.d).
            reason = f"needs a human merge: {error or 'the ruleset refused it'}"
            print(f"  #{v.number} {reason}")
            rows.append((v.number, v.title, reason[:160]))
            skipped += 1

    print(f"vibey-gh: merged {merged}, skipped {skipped}")
    _write_summary(args, _summary_rows(rows, merged, skipped))
    return 0


def _read_json(value: str) -> dict:
    parsed = json.loads(_read_text(value))
    if not isinstance(parsed, dict):
        raise TypeError("input JSON must be an object")
    return parsed


def _pr_automation(args) -> int:
    cfg = load_config()
    try:
        if args.action == "evaluate":
            print(pr_automation.evaluate_pr(args.pr, args.head_sha, cfg).to_json())
        elif args.action == "ready-draft":
            result = pr_automation.ready_draft(args.pr, args.head_sha, cfg)
            print(json.dumps(result, sort_keys=True))
        elif args.action in {"record-review", "record-repair"}:
            kind = args.action.removeprefix("record-")
            state = pr_automation.record(args.pr, _read_json(args.input), kind)
            print(json.dumps(asdict(state), sort_keys=True))
        elif args.action == "combine":
            # An empty --sovereign is how the workflow says the sovereign lane produced no
            # verdict; the composer then refuses a wider-half-only answer rather than
            # passing a review whose diff half nobody carried. An empty --paid is the paid
            # lane returning nothing -- or, under `--half none`, no paid review declared.
            sovereign = _read_json(args.sovereign) if args.sovereign else None
            paid = _read_json(args.paid) if args.paid else None
            envelope = REVIEW_COMPOSER.compose(
                paid, half=args.half, sovereign=sovereign, head_sha=args.head_sha
            )
            print(json.dumps(envelope, ensure_ascii=False))
        elif args.action == "mirror-fork":
            print(json.dumps(pr_automation.mirror_fork(args.pr, cfg), sort_keys=True))
        elif args.action == "self-heal":
            numbers = [args.pr] if args.pr else pr_automation.exhausted_pull_requests(cfg)
            results = [pr_automation.self_heal(number, cfg) for number in numbers]
            print(json.dumps(results, sort_keys=True))
        elif args.action == "ensure-labels":
            pr_automation.ensure_labels()
            print("vibey-gh: PR automation labels are ready")
        else:  # pragma: no cover - argparse constrains this
            raise ValueError(f"unknown action: {args.action}")
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    return 0


def _issue_automation(args) -> int:
    cfg = load_config()
    try:
        if args.action == "evaluate":
            print(issue_automation.evaluate_issue(args.issue, cfg).to_json())
        elif args.action == "context":
            document = issue_automation.context(
                issue_automation.fetch_issue(args.issue), max_bytes=args.max_bytes
            )
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(document, encoding="utf-8")
                print(f"vibey-gh: wrote {len(document.encode())} bytes to {args.output}")
            else:
                print(document, end="")
        elif args.action == "record-solution":
            state = issue_automation.record(args.issue, _read_json(args.input))
            print(json.dumps(asdict(state), sort_keys=True))
        elif args.action == "list-eligible":
            print(
                json.dumps(
                    [json.loads(item.to_json()) for item in issue_automation.eligible_issues(cfg)],
                    sort_keys=True,
                )
            )
        elif args.action == "ensure-labels":
            issue_automation.ensure_labels()
            print("vibey-gh: issue automation labels are ready")
        else:  # pragma: no cover - argparse constrains this
            raise ValueError(f"unknown action: {args.action}")
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    return 0


def _github_release(args) -> int:
    cfg = load_config()
    try:
        result = github_release.publish(cfg, target=args.target, version=args.version)
    except (RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(result), sort_keys=True))
    return 0


def _write_summary(args, text: str) -> None:
    """Append to the job summary when running in Actions. Best-effort: a summary that
    cannot be written is not a reason to fail a train that merged correctly."""
    path = args.summary or os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text)
    except OSError as exc:
        print(f"vibey-gh: could not write the summary: {exc}", file=sys.stderr)


def _flatten(args) -> int:
    try:
        plan, notes = flatten.Flattener().flatten(
            load_config(),
            onto=args.onto,
            message=args.message,
            push=args.push,
            dry_run=args.dry_run,
            orphan_comments=args.orphan_comments,
        )
    except flatten.FlattenError as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    for note in notes:
        print(f"  {note}")
    outcome = "would be flattened onto" if args.dry_run else "flattened onto"
    print(f"vibey-gh: {plan.branch} {outcome} {plan.base}")
    return 0


def _promote(args) -> int:
    if args.admin_fallback and not args.wait:
        # Without --wait nothing merges here (the merge train does), so the flag would be
        # accepted and silently ignored -- refused instead, so nobody believes it applied.
        print("vibey-gh: --admin-fallback only applies with --wait", file=sys.stderr)
        return 2
    try:
        result = promote.promote(
            load_config(),
            dry_run=args.dry_run,
            method=args.method,
            wait=args.wait,
            admin_fallback=args.admin_fallback,
        )
    except RuntimeError as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    for note in result.notes:
        print(f"  {note}")
    print(f"vibey-gh: {result.changed_files} file(s) differ; version {result.version}")
    _write_summary(args, _promotion_summary(result))
    return 0


def _promotion_summary(result) -> str:
    lines = ["## Promotion", ""]
    lines += [f"- {note}" for note in result.notes]
    lines += ["", f"Files differing: {result.changed_files}", f"Version: `{result.version}`"]
    return "\n".join(lines) + "\n"


def _realign(args) -> int:
    try:
        _changed, message = realign.realign(load_config())
    except RuntimeError as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    print(f"vibey-gh: {message}")
    return 0


def _report_superseded(args) -> int:
    import subprocess

    from vibey_gh import yank

    cfg = load_config()
    changed: list[str] | None = None
    if args.governance_since:
        # The ratifying merge is one push; its range names what it changed. An unreadable
        # range is reported loudly rather than silently waiving Article V.4 — but it never
        # fails the release: the publish already happened, and the amendment is enforced
        # by the review and the humans as well as by this bookkeeping.
        run = subprocess.run(
            ["git", "diff", "--name-only", f"{args.governance_since}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cfg.root,
            check=False,
        )
        if run.returncode == 0:
            changed = [line for line in run.stdout.splitlines() if line.strip()]
        else:
            print(
                "vibey-gh: could not read the governance range "
                f"{args.governance_since!r}: {run.stderr.strip()} — Article V.4 was NOT "
                "evaluated for this release; check it by hand",
                file=sys.stderr,
            )
    report = yank.report_superseded(cfg, args.index, args.project, args.version, changed)
    if report.governance:
        print(
            "vibey-gh: RATIFIED GOVERNANCE CHANGE — Article V.4 of the Constitution: no"
            " artifact circulates under superseded law. Every previous release is named"
            " below, zero exceptions, retention window overridden."
        )
    for problem in report.problems:
        print(f"vibey-gh: {problem}", file=sys.stderr)
    if report.skipped:
        print(f"vibey-gh: {args.index} — {', '.join(report.skipped)}")
    if report.superseded:
        print(
            f"vibey-gh: {len(report.superseded)} release(s) on {args.index} superseded by {args.version}:"
        )
        for version in report.superseded:
            print(f"  - {version}")
        # PyPI has no yank API, so the only thing that can be automated is working out the
        # list. Print where to act on it; see vibey_gh/yank.py for why.
        print(f"\n  Yank at: {report.manage_url}")
    # A publish has already succeeded by the time this runs. Reporting a bookkeeping failure
    # as a failed release would misrepresent it, so problems are printed, not fatal.
    return 0


def _failover(args) -> int:
    from vibey_gh import failover

    cfg = failover.load(Path(args.config).expanduser() if args.config else None)
    state = Path(args.state).expanduser() if args.state else None
    failover.run(cfg, state_path=state, once=args.once)
    return 0


def _tidy(args) -> int:
    from vibey_gh import tidy

    cfg = load_config()
    report = tidy.survey(cfg, local=not args.ci)
    for problem in report.problems:
        print(f"vibey-gh tidy: {problem}", file=sys.stderr)
        return 1
    rows = (
        ("merged remote branches", report.remote_merged),
        ("merged local branches", report.local_merged),
        ("gone-upstream local branches", report.local_gone),
        ("prunable worktrees", report.prunable_worktrees),
        ("draft releases (human decision)", report.draft_releases),
        ("orphan tags (human decision)", report.orphan_tags),
    )
    for label, items in rows:
        if items:
            print(f"vibey-gh tidy: {label}: {', '.join(items)}")
    if report.stashes:
        print(f"vibey-gh tidy: {report.stashes} stash(es) — yours, untouched")
    if report.untracked:
        print(f"vibey-gh tidy: {report.untracked} untracked path(s) — yours, untouched")
    if report.clean:
        print("vibey-gh tidy: clean — no technical clutter (9.a)")
        return 0
    if args.apply:
        for action in tidy.apply(cfg, report):
            print(f"vibey-gh tidy: {action}")
        # Drafts and orphan tags remain: reported above, removed only by a human.
        return 0
    print(
        "vibey-gh tidy: technical clutter present (sub-doctrine 9.a) —"
        " `vibey-gh tidy --apply` removes the provably-lossless classes"
    )
    return 1


def _forge_snapshot(args) -> int:
    """Capture the forge's state into `--out` (vibey#136, slice S1); read-only against the forge.

    Exit 0 when every selected class was captured, 1 when any could not be looked at (the
    rest are still written, and the manifest says which), 2 for arguments that name no
    capture at all. A class the forge would not answer for is reported by name with the
    forge's reason, never as a class with nothing in it.
    """
    from datetime import timedelta

    from vibey_gh import github_state
    from vibey_gh.forge_snapshot import (
        RESUME,
        ForgeSnapshot,
        GithubForgeReader,
        JsonlSnapshotStore,
        SnapshotStoreError,
    )
    from vibey_gh.gh_transport import GhTransport

    prefix = "vibey-gh forge-snapshot:"
    classes = None
    if args.classes is not None:
        classes = [name.strip() for name in args.classes.split(",") if name.strip()]
    try:
        repository = args.repo or github_state.repository()
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"{prefix} could not tell which repository to read: {exc}", file=sys.stderr)
        return 1
    out = Path(args.out)
    try:
        reader = GithubForgeReader(GhTransport(), repository, per_page=args.per_page)
        store = JsonlSnapshotStore(out, forge=reader.forge, repository=reader.repository)
        capture = ForgeSnapshot(reader, store, clock_skew=timedelta(seconds=args.clock_skew))
        manifest = capture.capture(classes=classes, since=args.since)
    except (SnapshotStoreError, OSError) as exc:
        print(f"{prefix} {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"{prefix} {exc}", file=sys.stderr)
        return 2
    print(f"{prefix} {manifest['forge']} {manifest['repository']} into {out}")
    if args.since == RESUME and manifest["since"] is None:
        print(f"{prefix} no resume point was recorded, so this capture is a full one")
    for name, entry in manifest["classes"].items():
        if entry["status"] == "captured":
            head = (entry["head"] or "none")[:12]
            print(
                f"  {name}: {entry['observed']} observed, {entry['appended']} appended,"
                f" {entry['unchanged']} unchanged; {entry['records']} record(s), head {head}"
            )
        elif entry["status"] == "could-not-look":
            print(f"  {name}: COULD NOT LOOK, nothing written: {entry['problem']}", file=sys.stderr)
        else:
            print(f"  {name}: not selected")
    print(
        f"{prefix} {len(manifest['excluded'])} artifact class(es) not captured, each named"
        f" with its reason in {out / 'manifest.json'}"
    )
    if manifest["resume_since"] is not None:
        print(f"{prefix} resume with --since {manifest['resume_since']} (or --since {RESUME})")
    return 0 if manifest["complete"] else 1


def _corpus_index(args) -> int:
    from vibey_gh import corpus

    cfg = load_config()
    if args.check:
        ok, message = corpus.check(cfg)
        print(f"vibey-gh corpus-index: {message}", file=None if ok else sys.stderr)
        return 0 if ok else 1
    target = corpus.write(cfg)
    index = corpus.build(cfg)
    print(
        f"vibey-gh corpus-index: wrote {target.name} — {len(index['chunks'])} chunk(s)"
        f" across {len(index['documents'])} document(s), corpus"
        f" {index['corpus_sha256'][:12]}…"
    )
    return 0


def _marketplace(args, renderer: MarketplaceRendererInterface | None = None) -> int:
    from vibey_gh.marketplace import MarketplaceError, MarketplaceRenderer

    cfg = load_config()
    renderer = renderer or MarketplaceRenderer()
    if args.check:
        ok, message = renderer.check(cfg)
        print(f"vibey-gh marketplace: {message}", file=None if ok else sys.stderr)
        return 0 if ok else 1
    try:
        manifest = renderer.build(cfg)
        target = renderer.write(cfg)
    except MarketplaceError as exc:
        print(f"vibey-gh marketplace: {exc}", file=sys.stderr)
        return 1
    print(
        f"vibey-gh marketplace: wrote {target.relative_to(cfg.root).as_posix()} —"
        f" {len(manifest['plugins'])} plugin(s) from {len(cfg.marketplace.members)}"
        f" member(s) as {manifest['name']!r}"
    )
    return 0


def _push_scope(args) -> int:
    """Judge the refs a pre-push hook was handed: does this push carry code at all?

    Reads git's pre-push standard input. Prints `NO_CODE` on stdout and exits 0 only when
    every ref is outside `refs/heads/` and `refs/tags/` and every commit is an empty tree
    with no parents; the reason goes to stderr so the person pushing sees why the heavy
    stage did not run. Any other push prints nothing and exits 1, and the gate runs in full.
    """
    from vibey_gh.push_scope import NO_CODE, PushScope

    verdict = PushScope().judge(sys.stdin.read())
    if verdict.carries_code:
        return 1
    print(
        f"vibey-gh push-scope: {verdict.reason}; nothing for the pre-push gate to judge",
        file=sys.stderr,
    )
    print(NO_CODE)
    return 0


def _sovereign(args) -> int:
    """Publish or read the sovereign heartbeat (doctrine 8.a).

    `--beat` is what the operator's supervisor runs on a timer; the bare form is what
    a workflow runs to decide whether it may schedule the sovereign lane at all. The
    probe prints its verdict and, under Actions, writes `ready=` to `$GITHUB_OUTPUT`
    so a job `if:` can consume it.
    """
    import os

    from vibey_gh import sovereign

    fallback = load_config().pr_automation.fallback
    if args.beat:
        result = sovereign.beat(fallback.heartbeat_ref, remote=args.remote)
    else:
        result = sovereign.probe(
            fallback.heartbeat_ref,
            max_age_minutes=fallback.heartbeat_max_age_minutes,
            remote=args.remote,
        )
        output = os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output, "a", encoding="utf-8") as handle:
                handle.write(f"ready={'true' if result.ready else 'false'}\n")
                # Why, as well as whether: the gate names it when the lane is not offered.
                # Every reason is this module's own one-line sentence, never forge text.
                handle.write(f"reason={' '.join(result.reason.split())}\n")
    print(f"vibey-gh sovereign: {result.reason}")
    # A probe that finds no runner is a fact, not a failure: exiting non-zero would
    # turn "the sovereign lane is not available right now" into a red job.
    return 0 if (result.ready or not args.beat) else 1


def _runner(args, launchctl=None) -> int:
    """Stand the sovereign review runner up from `[runners]`, or check or remove it (12.c).

    Only `install --load` and `--apply` touch launchd; every other form reads or writes
    files and prints what the operator runs next. `launchctl` is the seam tests replace.
    """
    from vibey_gh.sovereign_runner import PAT_PERMISSION, SovereignRunner

    runner = SovereignRunner(load_config(), home=Path.home(), uid=os.getuid(), launchctl=launchctl)
    plan, problem = runner.render()
    if plan is None:
        print(f"vibey-gh runner: {problem}", file=sys.stderr)
        return 1
    if args.action == "check":
        problems = runner.check(plan)
        for line in problems:
            print(line, file=sys.stderr)
        if problems:
            return 1
        print(f"vibey-gh runner: {plan.label} matches the tree and its credential is usable")
        return 0
    if args.action == "install":
        lines, loaded = runner.install(plan, load=args.load)
        for line in lines:
            print(line)
        if not loaded:
            return 1
        if not args.load:
            print("nothing was loaded. Next, in order:")
            print(
                f"  0. create a fine-grained token: repository {plan.repository} only,"
                f" {PAT_PERMISSION} (docs/runbooks/sovereign-review-runner.md)"
            )
            for number, step in enumerate(runner.next_steps(plan), start=1):
                print(f"  {number}. {step}")
        return 0
    if args.action == "cleanup":
        lines = runner.remove(runner.strays(plan), apply=args.apply)
    else:
        lines = runner.uninstall(plan, apply=args.apply)
    for line in lines:
        print(line)
    if not args.apply:
        print("dry run: nothing was changed; pass --apply to do it")
    return 0


def _fit(args) -> int:
    from pathlib import Path

    from vibey_gh import fit
    from vibey_gh.fitloop import FitLoop

    # The runner the model is read from: --base-url, else VIBEY_OLLAMA_URL, else the one
    # the local review is configured to call -- so the fit describes the runner it gates.
    base_url = fit.OllamaModelSampler.resolve_base_url(
        args.base_url, fallback=load_config().pr_automation.fallback.base_url
    )
    machine = fit.sample_machine()
    model = fit.sample_model(args.model, base_url)
    # The decision is recorded with everything needed to re-derive it, and prior
    # observations in the journal inform this projection — which is what makes repeated
    # Unless --no-journal:
    # --journal, else VIBEY_GH_FIT_JOURNAL, else ~/.local/state/vibey-gh/fit.jsonl.
    if args.no_journal:
        journal = None
    elif args.journal:
        journal = Path(args.journal)
    else:
        journal = FitLoop.default_journal()
    loop = FitLoop(args.model, journal=journal, base_url=base_url)
    loop.replay()
    if args.observed_seconds is not None:
        loop.observe(
            payload_bytes=args.payload_bytes,
            elapsed_s=args.observed_seconds,
            concurrent=max(args.queue, 1),
        )
    verdict = loop.admit(
        payload_bytes=args.payload_bytes,
        deadline_s=args.deadline,
        queue_depth=args.queue,
        machine=machine,
        model=model,
    )
    print(
        f"vibey-gh fit: machine {machine.total_gb} GB total, {machine.free_gb} GB free,"
        f" swap {machine.swap_used_gb}/{machine.swap_total_gb} GB —"
        f" {machine.available_gb} GB available"
    )
    if not machine.readable:
        print("vibey-gh fit: machine memory could not be read — that reading is unknown, not empty")
    if model is None:
        print(f"vibey-gh fit: model {args.model} could not be read from the runner at {base_url}")
    else:
        print(
            f"vibey-gh fit: model {model.name} {model.size_gb} GB, context {model.context_length}"
            + ("" if model.resident else " — not loaded; size is its weights on disk")
        )
    print(f"vibey-gh fit: {verdict.verdict.upper()} — {verdict.reason}")
    if journal is not None:
        print(f"vibey-gh fit: journal {journal}")
    if verdict.headroom_gb:
        print(f"vibey-gh fit: headroom wanted: {verdict.headroom_gb} GB")
    for note in verdict.notes:
        print(f"vibey-gh fit: note — {note}")
    advice = loop.recommendation()
    if advice:
        print(f"vibey-gh fit: ACTION NEEDED — {advice}")
    return 0 if verdict.ok else 1


def _estimate(args) -> int:
    # Module-level like every other handler in this file: argparse dispatches through
    # `set_defaults(func=...)`. It only resolves configuration and prints; the estimate
    # itself is `OperationEstimator`'s (ADR-0016).
    from vibey_gh import fit
    from vibey_gh.feasibility import FeasibilityEvaluator, Pipeline
    from vibey_gh.fitloop import FitLoop

    cfg = load_config()
    try:
        pipeline = Pipeline.from_config(cfg.estimate)
        evaluator = FeasibilityEvaluator(report_first=cfg.estimate.report_first)
    except ValueError as exc:
        print(f"vibey-gh estimate: {exc}", file=sys.stderr)
        return 2
    # The same runner and model the local lane uses, unless told otherwise: --base-url,
    # else VIBEY_OLLAMA_URL, else [pr_automation.fallback] base_url; --model, else
    # [estimate] model, else [pr_automation.fallback] model.
    base_url = fit.OllamaModelSampler.resolve_base_url(
        args.base_url, fallback=cfg.pr_automation.fallback.base_url
    )
    model = args.model or cfg.estimate.model or cfg.pr_automation.fallback.model
    # Read, never written: the fit loop's own observations inform the duration.
    if args.no_journal:
        journal = None
    elif args.journal:
        journal = Path(args.journal)
    else:
        journal = FitLoop.default_journal()
    estimator = operation_estimate.OperationEstimator(
        model,
        base_url=base_url,
        offline=cfg.estimate.offline and not args.online,
        journal=journal,
        pipeline=pipeline,
        evaluator=evaluator,
    )
    try:
        result = estimator.estimate(
            args.operation, start=args.start, payload_bytes=args.payload_bytes
        )
    except ValueError as exc:
        print(f"vibey-gh estimate: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print("\n".join(result.lines()))
    return result.exit_code


def _forecast(args) -> int:
    """Refresh the append-only delivery estimate and its human report."""
    from vibey_gh import github_state
    from vibey_gh.delivery_estimate import DeliveryEstimator, PhiConfig, WorkHistoryCalculator
    from vibey_gh.delivery_sources import DeliverySourceReader
    from vibey_gh.estimate_ledger import BillingLedgerReader, DeliveryEstimateLedger
    from vibey_gh.gh_transport import GhTransport

    cfg = load_config()
    try:
        repository = args.repo or cfg.platform.repository or github_state.repository()
        host = cfg.platform.host if cfg.platform.host != "github.com" else None
        source = DeliverySourceReader(transport=GhTransport(host=host)).read(
            repository, root=cfg.root, limit=args.limit
        )
        history = WorkHistoryCalculator(cfg.estimate.forecast_size_weights).calculate(source)
        billing_reference = Path(args.billing_ledger or cfg.estimate.forecast_billing_ledger)
        billing_path = (
            billing_reference if billing_reference.is_absolute() else cfg.root / billing_reference
        )
        billing = BillingLedgerReader().read(billing_path)
        billing_problems = tuple(
            problem.replace(str(billing_path), str(billing_reference))
            for problem in billing.problems
        )
        ledger = DeliveryEstimateLedger()
        ledger_path = Path(args.record) if args.record else cfg.root / cfg.estimate.forecast_ledger
        prior_records = ledger.read(ledger_path) if not args.no_record else ()
        state = _forecast_state(args.materials)
        estimator = DeliveryEstimator(
            phi=PhiConfig(
                floor=cfg.estimate.forecast_phi_floor,
                epsilon=cfg.estimate.forecast_phi_epsilon,
                exponent=cfg.estimate.forecast_phi_exponent,
                unknown_factor=cfg.estimate.forecast_phi_unknown_factor,
            )
        )
        at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        forecast = estimator.calculate(
            history,
            billing.usage,
            state=state,
            recorded_at=at,
            source_fingerprint=source.fingerprint,
            prior_records=prior_records,
            assumptions=(
                f"repository={repository}",
                f"source_revision={source.source_revision}",
                f"billing_ledger={billing_reference}",
            ),
            problems=(*source.problems, *billing_problems),
        )
        if not args.no_record:
            ledger.record(forecast, ledger_path)
        report_path = Path(args.report) if args.report else cfg.root / cfg.estimate.forecast_report
        if not args.no_report:
            ledger.write_report(forecast, report_path)
        summary = Path(args.summary) if args.summary else _summary_path()
        if summary is not None:
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text("\n".join(forecast.lines()) + "\n", encoding="utf-8")
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as exc:
        print(f"vibey-gh forecast: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(forecast.as_dict(), indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print("\n".join(forecast.lines()))
    return 1 if args.strict and forecast.problems else 0


def _forecast_state(path: Path | None):
    from vibey_gh.feasibility import Coordinate, StateVector

    if path is None:
        return StateVector.unknown()
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document.get("materials") if isinstance(document, dict) else document
    if not isinstance(rows, list):
        raise TypeError("materials input must be a list or an object with a materials list")
    measurements = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("each material reading must be an object")
        coordinate = row.get("coordinate")
        if not isinstance(coordinate, str) or coordinate.count(".") != 1:
            raise ValueError("each material reading needs coordinate='material.property'")
        material, prop = coordinate.split(".")
        raw_value = row.get("value")
        value = None if raw_value is None else float(raw_value)
        measurements.append(
            Coordinate(
                material,
                prop,
                value,
                str(row.get("source", "provided by --materials")),
                float(row["measured_at"]) if row.get("measured_at") is not None else None,
            )
        )
    return StateVector.unknown().with_measurements(measurements)


def _summary_path() -> Path | None:
    value = os.environ.get("GITHUB_STEP_SUMMARY", "")
    return Path(value) if value else None


def _doctor(args) -> int:
    from vibey_gh import doctor

    findings = doctor.diagnose(root=None)
    for f in findings:
        print(
            f"  {f.severity}: {f.message}", file=sys.stderr if f.severity == "error" else sys.stdout
        )
    errors = sum(1 for f in findings if f.severity == "error")
    if errors:
        print(
            f"vibey-gh doctor: {errors} problem(s) that will break the automation", file=sys.stderr
        )
        return 1
    # An "info" finding is printed above but is not a warning, so it is not counted as one.
    warnings = sum(1 for f in findings if f.severity == "warning")
    if warnings:
        print(f"vibey-gh doctor: no blockers; {warnings} warning(s)")
    else:
        print("vibey-gh doctor: the automation should function")
    return 0


def _paper_provenance(args, reader: RevisionReaderInterface | None = None):
    """The article's provenance from the flags and, with `--provenance`, from git and the clock.

    Nothing here is typed by a person: the revision and its commit time come from the
    checkout (or the `--revision` the workflow already holds), the render time from the
    clock, and the names, addresses and links from configuration.
    """
    from vibey_gh import paper

    if not args.provenance:
        return None
    selected = reader if reader is not None else paper.RevisionReader(Path.cwd())
    sha, committed_at, committed_unix = selected.read(args.revision or "HEAD")
    now = datetime.now(UTC).replace(microsecond=0)
    return paper.Provenance(
        author=args.author,
        email=args.email,
        affiliation=args.affiliation,
        author_url=args.author_url,
        site_url=args.site,
        repository_url=args.repository,
        revision=sha,
        committed_at=committed_at,
        committed_unix=committed_unix,
        rendered_at=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        rendered_unix=int(now.timestamp()),
    )


def _paper(args, reader: RevisionReaderInterface | None = None) -> int:
    from vibey_gh import paper
    from vibey_gh.docx import DocxError

    out = Path(args.output)
    source = Path(args.source)
    output_format = args.format or ("docx" if out.suffix.casefold() == ".docx" else "tex")
    try:
        markdown = source.read_text(encoding="utf-8")
        provenance = _paper_provenance(args, reader)
        out.parent.mkdir(parents=True, exist_ok=True)
        if output_format == "docx":
            paper.write_docx(
                markdown,
                out,
                author=args.author,
                journal=args.journal,
                keywords=args.keywords,
                provenance=provenance,
            )
            print(f"docx: {out}")
            return 0
        tex = paper.render_paper(
            markdown,
            author=args.author,
            journal=args.journal,
            keywords=args.keywords,
            provenance=provenance,
        )
    except (paper.PaperError, DocxError, OSError) as error:
        print(f"vibey-gh paper: {error}", file=sys.stderr)
        return 1
    out.write_text(tex, encoding="utf-8")
    print(f"tex: {out}")
    return 0


def _paper_figures(args) -> int:
    """Emit the paper's figures as standalone TeX, or inline their SVG renderings.

    Two halves of one pipeline that a TeX engine sits between. `--emit DIR` writes one
    standalone document per figure plus a manifest; the workflow compiles each with the
    pinned Tectonic and converts the page to SVG. `--inline SVGDIR --output FILE` then
    writes the paper with every rendered figure embedded, for the site and the book.
    """
    from vibey_gh import paper

    source = Path(args.source)
    try:
        markdown = source.read_text(encoding="utf-8")
        found = paper.figures(markdown)
        if args.emit is not None:
            target = Path(args.emit)
            target.mkdir(parents=True, exist_ok=True)
            manifest = []
            for figure in found:
                stem = figure.label.replace(":", "-")
                (target / f"{stem}.tex").write_text(paper.figure_document(figure), encoding="utf-8")
                manifest.append(
                    {
                        "label": figure.label,
                        "file": f"{stem}.tex",
                        "environment": figure.environment,
                    }
                )
            (target / "manifest.json").write_text(
                json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
            )
            print(f"figures: {len(manifest)} emitted into {target}")
            return 0
        svg_dir = Path(args.inline)
        rendered = {}
        for figure in found:
            candidate = svg_dir / f"{figure.label.replace(':', '-')}.svg"
            if candidate.is_file():
                rendered[figure.label] = candidate.read_text(encoding="utf-8")
        output = Path(args.output) if args.output else source
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(paper.inline_figures(markdown, rendered), encoding="utf-8")
        missing = [f.label for f in found if f.label not in rendered]
        print(f"figures: {len(rendered)} of {len(found)} inlined into {output}")
        if missing:
            print("figures without a rendering, kept as source: " + ", ".join(missing))
    except (paper.PaperError, OSError) as error:
        print(f"vibey-gh paper-figures: {error}", file=sys.stderr)
        return 1
    return 0


def _book(args) -> int:
    from vibey_gh import book
    from vibey_gh.docx import DocxError

    meta = {
        "title": args.title,
        "author": args.author,
        "subtitle": args.subtitle,
        "publisher": args.publisher,
        "description": args.description,
        "language": args.language,
        "edition": args.edition,
        "identifier": args.identifier,
        "date": args.date,
    }
    # Only the layout flags actually given: an absent one is the interior's own default,
    # so the defaults live in one place and are not restated here.
    layout = {
        name: getattr(args, name)
        for name in (
            "margin_top",
            "margin_bottom",
            "margin_outside",
            "gutter",
            "font_size",
            "line_height",
            "font_family",
            "code_font_family",
            "running_head_length",
        )
        if getattr(args, name) is not None
    }
    try:
        if args.trim is not None:
            layout["trim_width"], layout["trim_height"] = book.PrintInterior.parse_trim(args.trim)
        written = book.build_book(
            site_dir=Path(args.site_dir),
            config_text=Path(args.config_file).read_text(encoding="utf-8"),
            output_dir=Path(args.output_dir),
            meta={k: v for k, v in meta.items() if v},
            interior=book.PrintInterior(**layout),
        )
    except (book.BookError, DocxError, OSError) as error:
        print(f"vibey-gh book: {error}", file=sys.stderr)
        return 1
    for kind, path in written.items():
        print(f"{kind}: {path}")
    return 0


def _local_authority(args) -> int:
    from vibey_gh import local_authority

    paths = (
        [Path(p) for p in args.repos]
        if args.repos
        else local_authority.discover(Path(args.root).expanduser())
    )
    if not paths:
        print("vibey-gh local-authority: no repositories found", file=sys.stderr)
        return 1
    protected = tuple(b for b in (args.protected or "").split(",") if b)
    local_authority.run(
        paths,
        interval=args.interval,
        once=args.once,
        protected=protected,
        check=not args.no_check,
    )
    return 0


def _local_triage(args) -> int:
    from vibey_gh import local_review

    forwarded: list[str] = []
    if args.issue:
        forwarded += ["--issue", args.issue]
    forwarded += ["--model", args.model] if args.model else []
    forwarded += ["--base-url", args.base_url] if args.base_url else []
    if args.max_chars is not None:
        forwarded += ["--max-chars", str(args.max_chars)]
    if args.timeout is not None:
        forwarded += ["--timeout", str(args.timeout)]
    return local_review.triage(forwarded)


def _local_review(args) -> int:
    from vibey_gh import local_review

    forwarded: list[str] = []
    for flag, value in (
        ("--diff", args.diff),
        ("--model", args.model),
        ("--base-url", args.base_url),
        ("--max-chars", args.max_chars),
        ("--timeout", args.timeout),
        ("--role", args.role),
        ("--scope", args.scope),
        ("--context-dir", args.context_dir),
        ("--context-paths", args.context_paths),
        ("--context-window", args.context_window),
        ("--reasoning-reserve", args.reasoning_reserve),
        ("--chars-per-token", args.chars_per_token),
        ("--think", args.think),
    ):
        if value is not None:
            forwarded += [flag, str(value)]
    return local_review.review(forwarded)


def _conversation(args) -> int:
    cfg = load_config()
    try:
        if args.action in ("evaluate", "context"):
            subject = conversation.fetch_subject(args.subject)
            # Resolved, never guessed: an ID naming no comment on this thread or its review
            # is an error here, not a licence to answer the newest comment in its place.
            comment = conversation.ConversationThread(subject).comment(args.comment_id or "")
            if args.action == "evaluate":
                comments = list(subject.get("comments") or [])
                decision = conversation.evaluate(
                    comment, subject, cfg, stored=conversation.parse_state(comments)
                )
                print(decision.to_json())
            else:
                document = conversation.context(subject, comment, cfg, max_bytes=args.max_bytes)
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(document, encoding="utf-8")
                    print(f"vibey-gh: wrote {len(document.encode())} bytes to {args.output}")
                else:
                    print(document, end="")
        elif args.action == "reply":
            body = _read_text(args.body)
            if not conversation.reply(args.subject, body, cfg):
                raise RuntimeError("could not post the reply")
            print(f"vibey-gh: replied on #{args.subject}")
        else:  # record-response
            state = conversation.record(args.subject, _read_json(args.input))
            print(json.dumps(asdict(state), sort_keys=True))
    except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    return 0


def _read_text(value: str) -> str:
    """A literal value, the contents of a file at that path, or stdin for `-`."""
    if value == "-":
        return sys.stdin.read()
    path = Path(value)
    try:
        is_file = path.is_file()
    except OSError:
        # An inline value may exceed the platform's filename length limit. A failed path
        # probe must not prevent using the value itself.
        is_file = False
    return path.read_text(encoding="utf-8") if is_file else value


def _reconcile(args) -> int:
    cfg = load_config()
    try:
        outcomes = reconcile.reconcile(cfg, dry_run=args.dry_run)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    stalled = 0
    for outcome in outcomes:
        print(
            f"  #{outcome['pr']} ({outcome['branch']}): {outcome['action']} — {outcome['reason']}"
        )
        # Deciding an action and performing it are different things: a rebase can conflict
        # and abort, a push can be refused by a lease, GitHub can decline an update. Print
        # the decision and the outcome separately, because a decision reported alone reads
        # exactly like a success and hides a branch that never moved.
        if "applied" in outcome and not outcome["applied"]:
            stalled += 1
            print(f"      not applied: {outcome.get('detail', 'no detail reported')}")
        elif outcome.get("deleted") is False:
            print("      branch deletion was refused by GitHub")
    summary = f"vibey-gh: reconciled {len(outcomes)} open pull request(s)"
    if stalled:
        summary += f"; {stalled} action(s) did not take effect"
    print(summary)
    return 0


def _rulesets(args) -> int:
    cfg = load_config()
    try:
        outcomes = rulesets.reconcile(cfg, dry_run=args.dry_run)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    for outcome in outcomes:
        state = "changed" if outcome["changed"] else "current"
        note = ""
        if outcome["unexpected_rules"]:
            note = f" — unexpected rule(s) preserved: {', '.join(outcome['unexpected_rules'])}"
        print(f"  {outcome['ruleset']} ({outcome['branch']}): {state}{note}")
    print(f"vibey-gh: reconciled {len(outcomes)} ruleset(s)")
    return 0


def _surface(args) -> int:
    try:
        arguments = json.loads(args.arguments)
        if not isinstance(arguments, list):
            raise TypeError("arguments must be a JSON array")
        capability_exit = 0
        if args.cmd == "api":
            status, payload = surfaces.api_dispatch(
                "POST",
                f"/v1/capabilities/{args.capability}",
                json.dumps({"arguments": arguments}).encode(),
            )
            if status == 200:
                capability_exit = int(payload["exit_code"])
        elif args.cmd == "mcp":
            payload = surfaces.mcp_dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": args.capability, "arguments": {"arguments": arguments}},
                }
            )
            status = 200 if "result" in payload else 400
            if status == 200:
                result_text = payload["result"]["content"][0]["text"]
                capability_exit = int(json.loads(result_text)["exit_code"])
        elif args.cmd == "sdk":
            result = surfaces.invoke(args.capability, arguments)
            status, payload = 200, result.as_dict()
            capability_exit = result.exit_code
        else:
            secret = os.environ.get("VIBEY_GH_WEBHOOK_SECRET", "").encode()
            body = json.dumps({"capability": args.capability, "arguments": arguments}).encode()
            signature = (
                "sha256="
                + __import__("hmac").new(secret, body, __import__("hashlib").sha256).hexdigest()
            )
            state_dir = Path(
                os.environ.get(
                    "VIBEY_GH_WEBHOOK_STATE_DIR",
                    str(load_config().root / ".vibey-gh" / "webhook-deliveries"),
                )
            )
            status, payload = surfaces.WebhookDispatcher(secret, delivery_dir=state_dir).dispatch(
                args.delivery, signature, body
            )
            if status == 200:
                capability_exit = int(payload["exit_code"])
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"vibey-gh: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, sort_keys=True))
    return capability_exit if status == 200 else 1


def main(argv: list[str] | None = None) -> int:
    debugging.enable()
    parser = argparse.ArgumentParser(prog="vibey-gh", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="verify hooks and fingerprints")
    c.add_argument("--apply", action="store_true", help="add missing file headers")
    c.add_argument("--commits", metavar="RANGE", help="also check commit trailers, e.g. main..HEAD")
    c.add_argument("--quiet", action="store_true", help="exit status only, for hooks")
    c.add_argument(
        "--ci",
        action="store_true",
        help="skip the local core.hooksPath check, which no runner can satisfy",
    )
    c.set_defaults(func=_check)

    i = sub.add_parser("install", help="install the git hooks")
    i.set_defaults(func=_install)

    v = sub.add_parser("version", help="derive the version to release")
    v.add_argument(
        "--config",
        type=Path,
        metavar="PATH",
        help="derive against an alternate configuration — a second distribution this "
        "repository publishes. Repository-root-relative, and it does not move the root.",
    )
    v.add_argument("--since", default="origin/main")
    v.add_argument("--dev", metavar="BUILD", help="print <release>.dev<BUILD> instead")
    v.add_argument("--apply", action="store_true")
    v.add_argument("--explain", action="store_true")
    v.set_defaults(func=_version)

    for name, attr in (("trailer", "trailer"), ("trailer-key", "trailer_key")):
        p = sub.add_parser(name, help=f"print the {name}")
        p.set_defaults(func=lambda a, _attr=attr: (print(getattr(load_config(), _attr)), 0)[1])

    conventional = sub.add_parser(
        "conventional-message", help="normalize a commit message to Conventional Commits"
    )
    conventional.add_argument("--file", type=Path, help="rewrite this commit-message file")
    conventional.set_defaults(func=_conventional_message)

    conventional_check = sub.add_parser(
        "conventional-check", help="verify Conventional Commit subjects in a range"
    )
    conventional_check.add_argument("--commits", required=True, metavar="RANGE")
    conventional_check.set_defaults(func=_conventional_check)

    m = sub.add_parser("merge-train", help="merge every ready pull request")
    m.add_argument("--method", default="squash", choices=("squash", "rebase", "merge"))
    m.add_argument("--pr", type=int, help="evaluate only this pull request")
    m.add_argument("--dry-run", action="store_true")
    m.add_argument(
        "--label",
        default=merge_train.NEEDS_REVIEW_LABEL,
        help="label applied to a pull request held for the owner's review; "
        "pass an empty string to apply none",
    )
    m.add_argument(
        "--summary",
        metavar="FILE",
        help="write a markdown table here (default: $GITHUB_STEP_SUMMARY)",
    )
    # A flag and never a configuration key: a declared default-on would re-enable the
    # bypass for every unattended caller (CI, the storm tools). ADR-0053, sub-doctrine 12.d.
    m.add_argument(
        "--admin-fallback",
        action="store_true",
        help="retry a merge GitHub refuses with `gh pr merge --admin`, bypassing the "
        "ruleset. Off by default; for a person at the keyboard, for this run only. "
        "Unattended callers must never pass it",
    )
    m.set_defaults(func=_merge_train)

    automation = sub.add_parser(
        "pr-automation", help="evaluate and persist event-driven PR automation state"
    )
    automation_sub = automation.add_subparsers(dest="action", required=True)
    evaluate = automation_sub.add_parser("evaluate", help="classify one exact PR head")
    evaluate.add_argument("--pr", type=int, required=True)
    evaluate.add_argument("--head-sha", required=True)
    evaluate.set_defaults(func=_pr_automation)
    ready = automation_sub.add_parser(
        "ready-draft", help="mark an exact stable draft head ready for review"
    )
    ready.add_argument("--pr", type=int, required=True)
    ready.add_argument("--head-sha", required=True)
    ready.set_defaults(func=_pr_automation)
    for command in ("record-review", "record-repair"):
        record = automation_sub.add_parser(command, help=f"persist a structured {command[7:]}")
        record.add_argument("--pr", type=int, required=True)
        record.add_argument("--input", required=True, help="JSON object, file, or - for stdin")
        record.set_defaults(func=_pr_automation)
    combine = automation_sub.add_parser(
        "combine",
        help="compose one review verdict from the lane or lanes that answered it",
    )
    combine.add_argument(
        "--paid",
        default="",
        help=(
            "the paid reviewer's answer: JSON object, file, or -; empty when it returned"
            " nothing, and always empty with --half none"
        ),
    )
    combine.add_argument(
        "--half",
        required=True,
        choices=PAID_HALVES,
        help=(
            "what the paid reviewer answered: the full schema, the wider half alone, or"
            " 'none' when no paid review is declared and the sovereign verdict is the whole"
            " review (8.b)"
        ),
    )
    combine.add_argument(
        "--sovereign",
        default="",
        help=(
            "the sovereign lane's verdict (JSON object or file): its diff half, required with"
            " --half requires-wider-context; its whole review, required with --half none;"
            " empty when that lane produced none"
        ),
    )
    combine.add_argument("--head-sha", required=True)
    combine.set_defaults(func=_pr_automation)
    mirror = automation_sub.add_parser(
        "mirror-fork", help="open a repository-owned replacement for a fork PR"
    )
    mirror.add_argument("--pr", type=int, required=True)
    mirror.set_defaults(func=_pr_automation)
    heal = automation_sub.add_parser(
        "self-heal", help="refill an exhausted repair budget, itself bounded"
    )
    heal.add_argument("--pr", type=int, help="one pull request; omit to sweep every exhausted one")
    heal.set_defaults(func=_pr_automation)
    labels = automation_sub.add_parser("ensure-labels", help="create or update automation labels")
    labels.set_defaults(func=_pr_automation)

    issues = sub.add_parser(
        "issue-automation", help="evaluate issues and persist autonomous solution state"
    )
    issues_sub = issues.add_subparsers(dest="action", required=True)
    issue_evaluate = issues_sub.add_parser("evaluate", help="classify one issue")
    issue_evaluate.add_argument("--issue", type=int, required=True)
    issue_evaluate.set_defaults(func=_issue_automation)
    issue_context = issues_sub.add_parser(
        "context", help="render one issue as a bounded, explicitly untrusted briefing"
    )
    issue_context.add_argument("--issue", type=int, required=True)
    issue_context.add_argument("--output", type=Path, help="write here instead of stdout")
    issue_context.add_argument(
        "--max-bytes", type=int, default=issue_automation.DEFAULT_CONTEXT_BYTES
    )
    issue_context.set_defaults(func=_issue_automation)
    issue_record = issues_sub.add_parser(
        "record-solution", help="persist a structured solution attempt"
    )
    issue_record.add_argument("--issue", type=int, required=True)
    issue_record.add_argument("--input", required=True, help="JSON object, file, or - for stdin")
    issue_record.set_defaults(func=_issue_automation)
    issue_list = issues_sub.add_parser(
        "list-eligible", help="every open issue a recovery sweep should dispatch"
    )
    issue_list.set_defaults(func=_issue_automation)
    issue_labels = issues_sub.add_parser(
        "ensure-labels", help="create or update issue automation labels"
    )
    issue_labels.set_defaults(func=_issue_automation)

    release = sub.add_parser(
        "github-release", help="idempotently create an immutable version tag and GitHub Release"
    )
    release.add_argument("--target", required=True, help="exact main commit SHA to tag")
    release.add_argument("--version", help="version override (default: configured version file)")
    release.set_defaults(func=_github_release)

    p = sub.add_parser("promote", help="promote the integration branch to the release branch")
    p.add_argument(
        "--method", default=promote.DEFAULT_METHOD, choices=("rebase", "squash", "merge")
    )
    p.add_argument("--dry-run", action="store_true")
    wait_mode = p.add_mutually_exclusive_group()
    wait_mode.add_argument(
        "--wait",
        action="store_true",
        help="legacy synchronous mode: wait for checks and merge in this process",
    )
    wait_mode.add_argument(
        "--no-wait",
        action="store_false",
        dest="wait",
        help="open the promotion PR and let event-driven automation merge it (default)",
    )
    p.add_argument(
        "--summary", metavar="FILE", help="write markdown here (default: $GITHUB_STEP_SUMMARY)"
    )
    # A flag and never a configuration key, as for merge-train (ADR-0053, 12.d).
    p.add_argument(
        "--admin-fallback",
        action="store_true",
        help="with --wait: retry a merge GitHub refuses with `gh pr merge --admin`, "
        "bypassing the ruleset. Off by default; for a person at the keyboard, for this "
        "run only. Unattended callers must never pass it",
    )
    p.set_defaults(func=_promote)

    f = sub.add_parser(
        "flatten",
        help="rewrite the current branch as one commit on its base, trailers re-derived",
    )
    f.add_argument(
        "--onto",
        metavar="REF",
        help="the base to flatten onto (default: origin/<integration branch>), fetched first "
        "from the remote its own name gives — a fetch that fails refuses the flatten, because "
        "a stale base defeats the check that keeps this from reverting merged work",
    )
    f.add_argument(
        "--message",
        metavar="TEXT",
        help="the commit message; by default the first non-merge commit's, minus its trailers",
    )
    f.add_argument(
        "--push",
        action="store_true",
        help="push the rewritten branch to its own upstream remote (default `origin`; "
        "never the base's) with a lease pinned to what this clone last saw that remote "
        "holding (a branch the remote does not have yet is created without one); without "
        "it the exact push command is printed instead",
    )
    f.add_argument(
        "--orphan-comments",
        action="store_true",
        help="flatten even though the branch's open pull request has unresolved review "
        "threads. They are anchored to the commits being replaced, so the force-push marks "
        "every one of them outdated: each thread detaches from the code it was about, "
        "collapses, and stops prompting anyone to answer it. Without this flag such a "
        "branch is refused and the threads are listed instead",
    )
    f.add_argument(
        "--dry-run",
        action="store_true",
        help="report what it would do and change nothing at all, the base included: no fetch, "
        "so the plan reads the base as this clone already has it and says so",
    )
    f.set_defaults(func=_flatten)

    r = sub.add_parser("realign", help="realign the integration branch with the release branch")
    r.set_defaults(func=_realign)

    y = sub.add_parser(
        "report-superseded",
        help="report which releases the published one supersedes (PyPI has no yank API)",
    )
    y.add_argument("--index", choices=["pypi", "testpypi"], required=True)
    y.add_argument("--project", required=True, help="the distribution name on the index")
    y.add_argument("--version", required=True, help="the version just published; never listed")
    y.add_argument(
        "--governance-since",
        default="",
        help=(
            "git ref opening the release range; if the range touches a governance file"
            " (constitution, commandments, bill of rights, standing subdoctrines), every"
            " previous release is reported superseded — Article V.4, zero exceptions"
        ),
    )
    y.set_defaults(func=_report_superseded)

    local = sub.add_parser(
        "local-review",
        help="review a diff with a local model: the sovereign lane's diff half, or the fallback",
    )
    local.add_argument("--diff", help="path to a diff file (default: stdin)")
    local.add_argument("--model", help="override [pr_automation.fallback] model")
    local.add_argument("--base-url", help="override [pr_automation.fallback] base_url")
    local.add_argument("--max-chars", type=int, help="override max_diff_chars")
    local.add_argument("--timeout", type=int, help="override timeout_seconds")
    local.add_argument(
        "--role",
        choices=("fallback", "sovereign"),
        help=(
            "how the verdict labels itself: 'sovereign' when it carries the diff half,"
            " 'fallback' (the default) when it stands in for a paid review that failed"
        ),
    )
    local.add_argument(
        "--scope",
        choices=("diff-groundable", "full"),
        help=(
            "what to answer: the diff-groundable half (the default), or 'full' -- the whole"
            " review, asked of the sovereign lane when no paid review is declared (8.b)"
        ),
    )
    local.add_argument(
        "--context-dir",
        help="documents a whole review judges the documentation contract against",
    )
    local.add_argument(
        "--context-paths",
        help=(
            "override [pr_automation.fallback] context_paths, space-separated: the order the"
            " documents give way in, the last first"
        ),
    )
    local.add_argument(
        "--context-window",
        type=int,
        help="override [pr_automation.fallback] context_window: the model's window, in tokens",
    )
    local.add_argument(
        "--reasoning-reserve",
        type=int,
        help="override reasoning_reserve_tokens: room kept for reasoning and the answer",
    )
    local.add_argument("--chars-per-token", type=int, help="override chars_per_token")
    local.add_argument(
        "--think",
        choices=("", "low", "medium", "high"),
        help="override think: the reasoning effort sent to the model (empty sends none)",
    )
    local.set_defaults(func=_local_review)

    doc = sub.add_parser(
        "doctor",
        help="will the automation actually work? — the adoption preflight, offline",
    )
    doc.set_defaults(func=_doctor)

    ty = sub.add_parser(
        "tidy",
        help="the clean repo (9.a): survey technical clutter; --apply removes the lossless classes",
    )
    ty.add_argument(
        "--apply", action="store_true", help="delete merged/gone refs and prune worktrees"
    )
    ty.add_argument(
        "--ci", action="store_true", help="cloud classes only (no local-clone judgments)"
    )
    ty.set_defaults(func=_tidy)

    la = sub.add_parser(
        "local-authority",
        help="keep remotes tracking green local branches — the capped-lane sync loop",
    )
    la.add_argument("--repos", nargs="*", help="explicit repository paths (default: scan --root)")
    la.add_argument(
        "--root", default="~/git", help="scanned for work trees carrying .vibey-gh.toml"
    )
    la.add_argument("--interval", type=int, default=120, help="seconds between passes")
    la.add_argument("--once", action="store_true", help="one pass, then exit")
    la.add_argument(
        "--protected",
        default="",
        help="comma-separated branches never pushed (default: each repo's own integration and release branches)",
    )
    la.add_argument("--no-check", action="store_true", help="skip the per-repo provenance check")
    la.set_defaults(func=_local_authority)

    fo = sub.add_parser(
        "failover",
        help="hand the operator seat to a local agent while the paid lane is out of credit",
    )
    fo.add_argument(
        "--config",
        default="",
        help="machine-level TOML (default ~/.config/vibey-gh/failover.toml); missing file = disabled",
    )
    fo.add_argument(
        "--state",
        default="",
        help="seat-state file (default ~/.local/state/vibey-gh/failover.json)",
    )
    fo.add_argument("--once", action="store_true", help="one probe and transition, then exit")
    fo.set_defaults(func=_failover)

    fs = sub.add_parser(
        "forge-snapshot",
        help="read-only capture of issues, change requests, reviews, releases and more into"
        " hash-chained JSONL (#136)",
    )
    fs.add_argument("--out", required=True, help="the snapshot directory; created if missing")
    fs.add_argument(
        "--classes",
        help="comma-separated artifact classes (default: every supported class), e.g."
        " issue,comment,change-request",
    )
    fs.add_argument(
        "--since",
        help="ISO 8601 moment to capture from, or 'resume' for the manifest's resume point;"
        " omitted, the capture is a full one",
    )
    fs.add_argument("--repo", default="", help="owner/name (default: $GH_REPO, then gh's own)")
    fs.add_argument("--per-page", type=int, default=100, help="listing page size, 1 to 100")
    fs.add_argument(
        "--clock-skew",
        type=int,
        default=300,
        metavar="SECONDS",
        help="how far this machine's clock may run ahead of the forge's; a cursor taken from"
        " it is set back this far (default 300)",
    )
    fs.set_defaults(func=_forge_snapshot)

    ci_ = sub.add_parser(
        "corpus-index",
        help="build the governance corpus index — chunked, hashed, deterministic (#249)",
    )
    ci_.add_argument("--check", action="store_true", help="fail loudly on corpus drift")
    ci_.set_defaults(func=_corpus_index)

    mk = sub.add_parser(
        "marketplace",
        help="render the root Claude Code marketplace from the workspace members",
    )
    mk.add_argument(
        "--check", action="store_true", help="fail loudly when the root manifest drifts"
    )
    mk.set_defaults(func=_marketplace)

    ps = sub.add_parser(
        "push-scope",
        help="read pre-push refs on stdin; print carries-no-code when none of it is code",
    )
    ps.set_defaults(func=_push_scope)

    sv = sub.add_parser(
        "sovereign",
        help="sovereign readiness (8.a): publish or read the local runner's heartbeat",
    )
    sv.add_argument("--beat", action="store_true", help="publish a heartbeat (run on a timer)")
    sv.add_argument("--remote", default="origin", help="git remote carrying the heartbeat ref")
    sv.set_defaults(func=_sovereign)

    rn = sub.add_parser(
        "runner",
        help="stand the sovereign review runner up from [runners], or check or remove it",
    )
    rn_sub = rn.add_subparsers(dest="action", required=True)
    rn_install = rn_sub.add_parser(
        "install", help="render the LaunchAgent and supervisor; print the next commands"
    )
    rn_install.add_argument(
        "--load", action="store_true", help="also (re)load the LaunchAgent with launchctl"
    )
    rn_sub.add_parser("check", help="compare the installed runner and its credential with the tree")
    for action, helptext in (
        ("cleanup", "unload agents under unit_prefix the tree no longer declares"),
        ("uninstall", "unload the declared agent and delete the files install wrote"),
    ):
        removal = rn_sub.add_parser(action, help=f"{helptext} (dry run by default)")
        removal.add_argument("--apply", action="store_true", help="do it, rather than list it")
    rn.set_defaults(func=_runner, load=False, apply=False)

    ft = sub.add_parser(
        "fit",
        help="the fit calculus (#263): both sides measured, the projection stated",
    )
    ft.add_argument("--model", default="gpt-oss:20b", help="the model actually wanted")
    ft.add_argument("--queue", type=int, default=0, help="jobs already ahead of this one")
    ft.add_argument("--payload-bytes", type=int, default=8192, help="size of the work")
    ft.add_argument("--deadline", type=float, default=900.0, help="the caller's deadline")
    ft.add_argument(
        "--observed-seconds",
        type=float,
        help="record what this payload ACTUALLY took, feeding the estimate (#263)",
    )
    ft.add_argument(
        "--base-url",
        default="",
        help="the Ollama runner to read the model from (default: $VIBEY_OLLAMA_URL, else"
        " [pr_automation.fallback] base_url)",
    )
    ft_journal = ft.add_mutually_exclusive_group()
    ft_journal.add_argument(
        "--journal",
        help="record this decision, and read prior ones back, so repeated calls"
        " form a self-adjusting loop (#263) (default: $VIBEY_GH_FIT_JOURNAL, else"
        " ~/.local/state/vibey-gh/fit.jsonl)",
    )
    ft_journal.add_argument(
        "--no-journal",
        action="store_true",
        help="decide from this call alone: record nothing and read nothing back",
    )
    ft.set_defaults(func=_fit)

    es = sub.add_parser(
        "estimate",
        help="before a run (#134): feasibility along the whole pipeline, duration, cost,"
        " and each coordinate's distance from peak -- unknown where unmeasured",
    )
    es.add_argument(
        "--operation",
        required=True,
        help="the stage the run must reach, e.g. develop or main (default stages: install,"
        " interview, feature-branch, develop, develop-deployment, develop-validation, main,"
        " main-deployment, main-validation; [estimate] stages replaces them)",
    )
    es.add_argument(
        "--from",
        dest="start",
        default=None,
        help="the stage the run starts at (default: the first stage)",
    )
    es.add_argument("--json", action="store_true", help="print the estimate as JSON")
    es.add_argument(
        "--model",
        default="",
        help="the local model the fit coordinates are measured against (default: [estimate]"
        " model, else [pr_automation.fallback] model)",
    )
    es.add_argument(
        "--base-url",
        default="",
        help="the Ollama runner to read the model from (default: $VIBEY_OLLAMA_URL, else"
        " [pr_automation.fallback] base_url)",
    )
    es.add_argument(
        "--payload-bytes",
        type=int,
        default=operation_estimate.DEFAULT_PAYLOAD_BYTES,
        help="size of the work the local model's service time is projected for",
    )
    es.add_argument(
        "--online",
        action="store_true",
        help="also read a runner that is not on this machine (default: offline, unless"
        " [estimate] offline = false)",
    )
    es_journal = es.add_mutually_exclusive_group()
    es_journal.add_argument(
        "--journal",
        help="the fit journal whose observations inform the duration; read, never written"
        " (default: $VIBEY_GH_FIT_JOURNAL, else ~/.local/state/vibey-gh/fit.jsonl)",
    )
    es_journal.add_argument(
        "--no-journal",
        action="store_true",
        help="read no observations: the duration is unknown",
    )
    es.set_defaults(func=_estimate)

    fc = sub.add_parser(
        "forecast",
        help="continuously estimate remaining delivery time and all billing-system usage",
    )
    fc.add_argument("--repo", default="", help="owner/name (default: configured forge repository)")
    fc.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="maximum historical issues and pull requests to read (default: 1000)",
    )
    fc.add_argument(
        "--billing-ledger",
        type=Path,
        help="core `vibey ledger export` JSONL used for actual dollars, turns and event usage",
    )
    fc.add_argument(
        "--materials",
        type=Path,
        help="JSON material readings: a list of {coordinate, value, source} objects",
    )
    record_mode = fc.add_mutually_exclusive_group()
    record_mode.add_argument(
        "--record",
        type=Path,
        help="append to this estimate ledger (default: [estimate.forecast] ledger)",
    )
    record_mode.add_argument(
        "--no-record",
        action="store_true",
        help="calculate without reading or appending the estimate ledger",
    )
    report_mode = fc.add_mutually_exclusive_group()
    report_mode.add_argument(
        "--report",
        type=Path,
        help="write the human report here (default: [estimate.forecast] report)",
    )
    report_mode.add_argument(
        "--no-report",
        action="store_true",
        help="do not write the human report",
    )
    fc.add_argument(
        "--summary",
        type=Path,
        help="also write the report lines to this path (default: $GITHUB_STEP_SUMMARY)",
    )
    fc.add_argument("--json", action="store_true", help="print the complete forecast as JSON")
    fc.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when a source could not be read; default keeps the forecast visible",
    )
    fc.set_defaults(func=_forecast)

    pp = sub.add_parser(
        "paper",
        help="render docs/paper.md as a journal-class LaTeX document (IEEEtran)",
    )
    pp.add_argument("--source", default="docs/paper.md")
    pp.add_argument("--output", default="paper/paper.tex")
    pp.add_argument(
        "--format",
        choices=("tex", "docx"),
        help="output format; inferred from .docx output names, otherwise tex",
    )
    pp.add_argument("--author", required=True)
    pp.add_argument("--journal", action="store_true", help="journal layout instead of conference")
    pp.add_argument("--keywords", default="")
    # What a submitted article states about itself, never typed by hand: with
    # --provenance the revision and its commit time are read from git (or --revision),
    # the render time from the clock, and the rest from these flags.
    pp.add_argument(
        "--provenance",
        action="store_true",
        help="state the revision, dates and authorship in the byline, first-page note and"
        " wherever the source writes <!-- vibey:provenance -->",
    )
    pp.add_argument("--revision", default="", help="the revision to state (default: HEAD)")
    pp.add_argument("--email", default="", help="the corresponding author's email address")
    pp.add_argument("--affiliation", default="", help="the author's affiliation line")
    pp.add_argument("--author-url", default="", help="the author's own address")
    pp.add_argument("--site", default="", help="the published documentation site")
    pp.add_argument("--repository", default="", help="the repository the revision belongs to")
    pp.set_defaults(func=_paper)
    pf = sub.add_parser(
        "paper-figures",
        help="emit the paper's figures as standalone TeX, or inline their SVG renderings",
    )
    pf.add_argument("--source", default="docs/paper.md")
    mode = pf.add_mutually_exclusive_group(required=True)
    mode.add_argument("--emit", help="write one standalone .tex per figure into this directory")
    mode.add_argument("--inline", help="read <label>.svg files from this directory and inline them")
    pf.add_argument(
        "--output", default="", help="with --inline: where to write (default: the source)"
    )
    pf.set_defaults(func=_paper_figures)
    bk = sub.add_parser(
        "book",
        help="export the built docs site as an EPUB and a KDP print-ready HTML",
    )
    bk.add_argument("--site-dir", required=True, help="the built site directory")
    bk.add_argument(
        "--config-file",
        default="properdocs.yml",
        help="site configuration whose nav orders the chapters",
    )
    bk.add_argument("--output-dir", default="book", help="where book files are written")
    bk.add_argument("--title", required=True)
    bk.add_argument("--author", required=True)
    bk.add_argument("--subtitle", default="")
    bk.add_argument("--publisher", default="")
    bk.add_argument("--description", default="")
    bk.add_argument("--language", default="en", help="BCP 47 tag: <html lang>, xml:lang")
    bk.add_argument(
        "--edition",
        default="",
        help="folded into the derived EPUB identifier: a new edition is a new book",
    )
    bk.add_argument(
        "--identifier",
        default="",
        help="the EPUB dc:identifier as given (e.g. urn:isbn:...); default derived and stable",
    )
    bk.add_argument("--date", default="", help="publication date YYYY-MM-DD (default: today)")
    # The print interior's physical parameters (ADR-0018). Omitted, each is the interior's
    # own default -- the standard KDP 6x9in paperback -- quoted from it in the help.
    from vibey_gh import book

    bk.add_argument(
        "--trim",
        help="trim size WIDTHxHEIGHT, bare numbers in inches, e.g. 5.5x8.5 or 148mmx210mm"
        f" (default {book.DEFAULT_TRIM_WIDTH}x{book.DEFAULT_TRIM_HEIGHT})",
    )
    bk.add_argument(
        "--gutter",
        help="inside (binding) margin; KDP's minimum grows with page count: 24-150 pages"
        " 0.375in, 151-300 0.5in, 301-500 0.625in, 501-700 0.75in, 701-828 0.875in"
        f" (default {book.DEFAULT_GUTTER})",
    )
    for flag, default, what in (
        ("--margin-top", book.DEFAULT_MARGIN_TOP, "top margin"),
        ("--margin-bottom", book.DEFAULT_MARGIN_BOTTOM, "bottom margin"),
        ("--margin-outside", book.DEFAULT_MARGIN_OUTSIDE, "outside (fore-edge) margin"),
        ("--font-size", book.DEFAULT_FONT_SIZE, "body type size, bare numbers in pt"),
        ("--line-height", book.DEFAULT_LINE_HEIGHT, "body leading"),
        ("--font-family", book.DEFAULT_FONT_FAMILY, "body CSS font stack"),
        ("--code-font-family", book.DEFAULT_CODE_FONT_FAMILY, "code CSS font stack"),
    ):
        bk.add_argument(flag, help=f"{what} (default {default})")
    bk.add_argument(
        "--running-head-length",
        type=int,
        help="characters of a chapter title kept in its running head"
        f" (default {book.DEFAULT_RUNNING_HEAD_LENGTH})",
    )
    bk.set_defaults(func=_book)

    lt = sub.add_parser(
        "local-triage",
        help="triage an issue with a local model when the paid solver produced nothing",
    )
    lt.add_argument("--issue", help="path to a file with the issue text (default: stdin)")
    lt.add_argument("--model", default="")
    lt.add_argument("--base-url", default="")
    lt.add_argument("--max-chars", type=int, default=None)
    lt.add_argument("--timeout", type=int, default=None)
    lt.set_defaults(func=_local_triage)

    talk = sub.add_parser("conversation", help="respond to a mention in a comment")
    talk_sub = talk.add_subparsers(dest="action", required=True)
    for name, helptext in (
        ("evaluate", "decide whether one comment gets a response"),
        ("context", "render the thread as a bounded, untrusted briefing"),
        ("reply", "post an answer as a comment"),
        ("record-response", "persist one interaction against the thread"),
    ):
        item = talk_sub.add_parser(name, help=helptext)
        item.add_argument("--subject", type=int, required=True, help="issue or PR number")
        item.add_argument("--comment-id", help="exact comment; omit for the newest")
        if name == "context":
            item.add_argument("--output", type=Path)
            item.add_argument("--max-bytes", type=int, default=conversation.DEFAULT_CONTEXT_BYTES)
        if name == "reply":
            item.add_argument("--body", required=True, help="text, file, or - for stdin")
        if name == "record-response":
            item.add_argument("--input", required=True, help="JSON object, file, or - for stdin")
        item.set_defaults(func=_conversation)

    rec = sub.add_parser(
        "reconcile-branches",
        help="rebase, close, or leave open branches stranded by a realign rewrite",
    )
    rec.add_argument("--dry-run", action="store_true", help="decide without mutating anything")
    rec.set_defaults(func=_reconcile)

    rs = sub.add_parser("rulesets", help="reconcile the integration and release branch rulesets")
    rs.add_argument("--dry-run", action="store_true", help="decide without applying anything")
    rs.set_defaults(func=_rulesets)

    # A thin delegate for people. The delegated approver never comes this way: it runs
    # `python -m vibey_gh.approval_check`, so this module is not on its trust path.
    ac = sub.add_parser(
        "approve-check",
        help="exit 0 only if every [unattended_approval] condition holds for a pull request",
    )
    ApprovalCheck.declare(ac).set_defaults(func=ApprovalCheck.dispatch)

    for surface in ("api", "mcp", "sdk", "webhook"):
        adapter = sub.add_parser(surface, help=f"invoke a capability through the {surface} adapter")
        adapter.add_argument("capability", choices=surfaces.CAPABILITIES)
        adapter.add_argument("--arguments", default="[]", help="JSON array of capability arguments")
        if surface == "webhook":
            adapter.add_argument("--delivery", required=True, help="unique webhook delivery ID")
        adapter.set_defaults(func=_surface)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
