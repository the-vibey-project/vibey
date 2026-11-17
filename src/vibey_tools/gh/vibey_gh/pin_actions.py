# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh pin-actions`: pin every GitHub Actions `uses:` to the commit it names today.

A `uses: owner/repo@v4` is a moving name: whoever controls the tag controls what runs in
our pipeline. This command finds every such reference in the workflows and composite actions
and rewrites it to `owner/repo@<40-hex commit> # v4`, the tag kept as a comment so the pin
stays readable: the comment is also what `--refresh` re-resolves. It is the toil automated
(sub-doctrine 12.e): nobody looks up a SHA by hand, and the check mode says out loud when one
was missed.

A pin does not move by itself, and Dependabot cannot be told to skip only the managed
workflows (it ignores a dependency, not a file), so nothing else refreshes the pins in the
hand-written files. `--refresh` re-resolves each `# <ref>` and moves a pin whose ref now names
another commit (a floating `v4` legitimately follows the newest v4.x); `--check-stale` does the
same without writing, and with `--tracking-issue` keeps ONE issue open while any pin is stale
or cannot be checked. Why an issue and not an unattended pull request: moving a pin changes
what runs in the pipeline, so a person reads the diff; the issue names the one command that
makes it. `[pin_actions]` in `.vibey-gh.toml` holds back actions and labels the issue.

Two rules shape the code:

* **Line by line, never a YAML round trip.** Loading and dumping a workflow reformats it
  (quotes, indentation, comments), so the file is read as text, the `uses:` lines are found
  with a regex, and only those lines are edited. A `uses:` inside a `run:` block scalar, or
  in a comment, is text and not a key, so it is left alone.
* **The commits endpoint, not the tag ref.** `GET repos/{owner}/{repo}/commits/{ref}`
  answers with the commit for a branch, a lightweight tag or an annotated tag alike. The
  tag-ref endpoint answers an annotated tag with the tag OBJECT's SHA, which is not a commit
  and which `uses:` would then reject.
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

from vibey_gh.config import load_config
from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.pin_actions_interface import ActionUse, PinActionsInterface, PinnedUse
from vibey_gh.interfaces.tracking_issue_interface import TrackingIssueInterface
from vibey_gh.tracking_issue import TrackingIssue

__all__ = ["ActionUse", "PinActions", "PinnedUse"]

_COMMIT = re.compile(r"[0-9a-f]{40}")
# `- uses: x@y`, `uses: "x@y"` and an indented `uses:` key; group `spec` is the reference.
_USES = re.compile(r"^(?P<head>\s*(?:-\s+)?uses:\s*[\"']?)(?P<spec>[^\s#\"']+)(?P<tail>.*)$")
# What may follow the reference: a closing quote, then optionally a comment.
_TAIL = re.compile(r"^(?P<quote>[\"']?)(?P<space>\s*)(?P<comment>#.*)?$")
# `run: |`, `script: >-` and the like: a key whose value is a block scalar.
_BLOCK = re.compile(r"^(?P<indent>\s*(?:-\s+)?)[^\s#:][^#]*:\s*[|>][+-]?\d*\s*(?:#.*)?$")
# The first word of a pin's comment is its ref: a name, or an expression (`${{ ... }}`).
_REF = re.compile(r"[A-Za-z0-9$]\S*")
_ISSUE_KEY = "pin-freshness"
_WORKFLOWS = ".github/workflows/*.yml"
_ACTIONS = ".github/actions/*/action.yml"


@dataclass
class _Survey:
    """What looking at every pin found: the moves, the pins left alone and the ones it could
    not check. `lines` is the report, in the order it is printed."""

    texts: dict[Path, str] = field(default_factory=dict)
    stale: list[tuple[PinnedUse, str]] = field(default_factory=list)
    held: list[PinnedUse] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    shas: dict[tuple[str, str], str] = field(default_factory=dict)
    lines: list[str] = field(default_factory=list)


class PinActions(PinActionsInterface):
    """Implements `PinActionsInterface` over the forge's REST API."""

    def __init__(
        self,
        *,
        transport: GhTransportInterface | None = None,
        issues: TrackingIssueInterface | None = None,
        hold: Sequence[str] = (),
        labels: Sequence[str] = (),
    ) -> None:
        self._transport: GhTransportInterface = transport or GhTransport()
        self._issues = issues
        self._hold = frozenset(hold)
        self._labels = tuple(labels)

    @staticmethod
    def default_paths(root: Path) -> list[Path]:
        """The workflows and composite actions under `root`, in a stable order."""
        return sorted(root.glob(_WORKFLOWS)) + sorted(root.glob(_ACTIONS))

    @staticmethod
    def _split(spec: str) -> tuple[str, str] | None:
        """`(action, ref)` of a reference that is not yet a commit pin, else None.

        None for a local `./` action, a `docker://` image, a reference with no `@` and one
        already pinned to a full commit."""
        if spec.startswith(("./", "docker://")) or "@" not in spec:
            return None
        action, ref = spec.rsplit("@", 1)
        return None if _COMMIT.fullmatch(ref) else (action, ref)

    @staticmethod
    def _lines(text: str) -> list[tuple[int, re.Match[str]]]:
        """Every `uses:` key line as `(index, match)`, outside block scalars."""
        found: list[tuple[int, re.Match[str]]] = []
        block_indent: int | None = None
        for index, line in enumerate(text.split("\n")):
            if block_indent is not None:
                if not line.strip() or len(line) - len(line.lstrip()) > block_indent:
                    continue
                block_indent = None
            opened = _BLOCK.match(line)
            if opened:
                block_indent = len(opened.group("indent"))
                continue
            match = _USES.match(line)
            if match:
                found.append((index, match))
        return found

    def unpinned(self, text: str, path: Path) -> list[ActionUse]:
        uses: list[ActionUse] = []
        for index, match in self._lines(text):
            parts = self._split(match.group("spec"))
            if parts:
                uses.append(ActionUse(path, index + 1, parts[0], parts[1]))
        return uses

    def rewrite(self, text: str, shas: Mapping[tuple[str, str], str]) -> str:
        lines = text.split("\n")
        for index, match in self._lines(text):
            parts = self._split(match.group("spec"))
            tail = _TAIL.match(match.group("tail"))
            if parts is None or tail is None or parts not in shas:
                continue
            comment = f" {tail.group('comment')}" if tail.group("comment") else ""
            lines[index] = (
                f"{match.group('head')}{parts[0]}@{shas[parts]}"
                f"{tail.group('quote')} # {parts[1]}{comment}"
            )
        return "\n".join(lines)

    def resolve(self, action: str, ref: str) -> str:
        owner_repo = "/".join(action.split("/")[:2])
        try:
            answer = self._transport.json(
                ["api", f"repos/{owner_repo}/commits/{quote(ref, safe='/')}"]
            )
        except ValueError as exc:  # an answer that is not JSON; `json.JSONDecodeError` is one
            raise RuntimeError(f"{action}@{ref}: {exc}") from exc
        sha = str(answer.get("sha") or "") if isinstance(answer, dict) else ""
        if not _COMMIT.fullmatch(sha):
            raise RuntimeError(f"{action}@{ref} does not name a commit")
        return sha

    def run(self, paths: Sequence[Path], *, apply: bool) -> int:
        texts = {path: path.read_text(encoding="utf-8") for path in paths}
        uses = [use for path, text in texts.items() for use in self.unpinned(text, path)]
        if not uses:
            print("vibey-gh: pin-actions: every uses: is pinned to a commit")
            return 0
        if not apply:
            for use in uses:
                print(f"{use.path}:{use.line}: {use.action}@{use.ref} is not pinned to a commit")
            print(f"vibey-gh: pin-actions: {len(uses)} unpinned; run with --apply to pin them")
            return 1
        dynamic = [use for use in uses if "$" in use.ref]
        for use in dynamic:
            print(
                f"{use.path}:{use.line}: {use.action}@{use.ref} cannot be pinned: the ref is an expression"
            )
        shas: dict[tuple[str, str], str] = {}
        failures: list[str] = []
        for key in dict.fromkeys((use.action, use.ref) for use in uses if use not in dynamic):
            try:
                shas[key] = self.resolve(*key)
            except RuntimeError as exc:
                failures.append(str(exc))
        if failures:
            for failure in failures:
                print(f"vibey-gh: pin-actions: {failure}")
            print("vibey-gh: pin-actions: nothing written; every file is as it was")
            return 1
        stuck: list[ActionUse] = []
        for path, text in texts.items():
            rewritten = self.rewrite(text, shas)
            if rewritten != text:
                path.write_text(rewritten, encoding="utf-8")
            stuck.extend(u for u in self.unpinned(rewritten, path) if "$" not in u.ref)
        if stuck:
            for use in stuck:
                print(f"{use.path}:{use.line}: {use.action}@{use.ref} could not be rewritten")
            print(f"vibey-gh: pin-actions: {len(stuck)} could not be pinned; the rest were written")
            return 1
        pinned = len(uses) - len(dynamic)
        note = f"; {len(dynamic)} cannot be pinned" if dynamic else ""
        print(f"vibey-gh: pin-actions: pinned {pinned} uses to {len(shas)} commits{note}")
        return 1 if dynamic else 0

    @staticmethod
    def _comment_ref(tail: str) -> str | None:
        """The ref a pin's trailing `# <ref>` comment names, if it names one."""
        parsed = _TAIL.match(tail)
        comment = parsed.group("comment") if parsed else None
        words = comment[1:].split() if comment else []
        return words[0] if words and _REF.fullmatch(words[0]) else None

    def pinned(self, text: str, path: Path) -> list[PinnedUse]:
        found: list[PinnedUse] = []
        for index, match in self._lines(text):
            spec = match.group("spec")
            if spec.startswith(("./", "docker://")) or "@" not in spec:
                continue
            action, sha = spec.rsplit("@", 1)
            if _COMMIT.fullmatch(sha):
                found.append(
                    PinnedUse(path, index + 1, action, sha, self._comment_ref(match.group("tail")))
                )
        return found

    def restamp(self, text: str, shas: Mapping[tuple[str, str], str]) -> str:
        lines = text.split("\n")
        for use in self.pinned(text, Path()):
            new = shas.get((use.action, use.ref or ""))
            if new and new != use.sha:
                lines[use.line - 1] = lines[use.line - 1].replace(
                    f"{use.action}@{use.sha}", f"{use.action}@{new}", 1
                )
        return "\n".join(lines)

    def _survey(self, paths: Sequence[Path]) -> _Survey:
        """Read every file, resolve each distinct `(action, ref)` once, and sort the pins into
        moved, held and unchecked. Reads the forge; writes nothing."""
        survey = _Survey({path: path.read_text(encoding="utf-8") for path in paths})
        live: list[PinnedUse] = []
        for path, text in survey.texts.items():
            for use in self.unpinned(text, path):
                survey.problems.append(
                    f"{use.path}:{use.line}: {use.action}@{use.ref} could not be refreshed: "
                    "not pinned to a commit (run --apply first)"
                )
            for pin in self.pinned(text, path):
                if "/".join(pin.action.split("/")[:2]) in self._hold:
                    survey.held.append(pin)
                else:
                    live.append(pin)
        refused: dict[tuple[str, str], str] = {}
        for pin in live:
            where = f"{pin.path}:{pin.line}: {pin.action} could not be refreshed: "
            if pin.ref is None:
                survey.problems.append(where + "no `# <ref>` comment to read the ref from")
            elif "$" in pin.ref:
                survey.problems.append(where + "the ref is an expression")
            else:
                key = (pin.action, pin.ref)
                if key not in survey.shas and key not in refused:
                    try:
                        survey.shas[key] = self.resolve(*key)
                    except RuntimeError as exc:
                        refused[key] = str(exc)
                if key in refused:
                    survey.problems.append(where + refused[key])
                elif survey.shas[key] != pin.sha:
                    survey.stale.append((pin, survey.shas[key]))
        survey.lines = [
            f"{pin.path}:{pin.line}: {pin.action} ({pin.ref}) {pin.sha} -> {new}"
            for pin, new in survey.stale
        ]
        survey.lines += [
            f"{pin.path}:{pin.line}: {pin.action} is held on {pin.sha}" for pin in survey.held
        ]
        survey.lines += survey.problems
        return survey

    @staticmethod
    def _plural(count: int, noun: str) -> str:
        return f"{count} {noun}" if count == 1 else f"{count} {noun}s"

    def _summary(self, survey: _Survey, *, write: bool) -> str:
        parts: list[str] = []
        if not survey.stale and not survey.problems:
            parts.append("every pin is current")
        if survey.stale:
            count = self._plural(len(survey.stale), "pin")
            parts.append(
                f"refreshed {count}"
                if write
                else f"{self._plural(len(survey.stale), 'stale pin')}; run with --refresh to move them"
            )
        if survey.problems:
            parts.append(f"{len(survey.problems)} could not be refreshed")
        if survey.held:
            parts.append(f"{len(survey.held)} held")
        return "vibey-gh: pin-actions: " + "; ".join(parts)

    def refresh(self, paths: Sequence[Path], *, write: bool) -> int:
        survey = self._survey(paths)
        for line in survey.lines:
            print(line)
        if write and survey.stale:
            for path, text in survey.texts.items():
                moved = self.restamp(text, survey.shas)
                if moved != text:
                    path.write_text(moved, encoding="utf-8")
        print(self._summary(survey, write=write))
        return 1 if survey.problems or (survey.stale and not write) else 0

    def announce(self, paths: Sequence[Path]) -> int:
        survey = self._survey(paths)
        for line in survey.lines:
            print(line)
        print(self._summary(survey, write=False))
        issues = self._issues or TrackingIssue()
        try:
            if survey.stale or survey.problems:
                body = (
                    "Pinned `uses:` references whose `# <ref>` now names another commit, or "
                    "that could not be checked:\n\n"
                    + "\n".join(f"- `{line}`" for line in survey.lines)
                    + "\n\nRun `uv run vibey-gh pin-actions --refresh`, read the diff and "
                    "open a pull request. Hold an action back with `[pin_actions] hold` in "
                    ".vibey-gh.toml."
                )
                number, _ = issues.raise_issue(
                    _ISSUE_KEY, "Action pins are stale", body, labels=self._labels
                )
                print(f"vibey-gh: pin-actions: tracking issue #{number} is open")
            else:
                issues.resolve(_ISSUE_KEY, "Every pin is current again.")
        except RuntimeError as exc:
            print(f"vibey-gh: pin-actions: {exc}")
            return 1
        return 0

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument(
            "--apply",
            action="store_true",
            help="resolve each ref and rewrite the files; without it, only check (no network)",
        )
        mode.add_argument(
            "--refresh",
            action="store_true",
            help="re-resolve each pin's `# <ref>` comment and move the pins that are stale",
        )
        mode.add_argument(
            "--check-stale",
            action="store_true",
            help="like --refresh but write nothing; exit 1 when a pin is stale or unchecked",
        )
        parser.add_argument(
            "--tracking-issue",
            action="store_true",
            help="with --check-stale: keep one issue open while pins are stale, exit 0 once told",
        )
        parser.add_argument(
            "paths",
            nargs="*",
            type=Path,
            help=f"files to pin (default: {_WORKFLOWS} and {_ACTIONS})",
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        paths = args.paths or cls.default_paths(Path.cwd())
        if args.tracking_issue and not args.check_stale:
            print("vibey-gh: pin-actions: --tracking-issue goes with --check-stale")
            return 2
        if not (args.refresh or args.check_stale):
            return cls().run(paths, apply=args.apply)
        config = load_config(Path.cwd()).pin_actions
        tool = cls(hold=config.hold, labels=config.labels)
        if args.tracking_issue:
            return tool.announce(paths)
        return tool.refresh(paths, write=args.refresh)
