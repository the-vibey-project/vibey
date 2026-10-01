# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Changelog fragments: one new file per change, folded into the changelog at release.

Every pull request used to add its entry under the same `## [Unreleased]` heading, so any
two open pull requests touched the same lines and the second to merge conflicted. The
`merge=union` attribute meant to absorb that does nothing on GitHub -- its mergeability
never runs a custom merge driver, so a pull request shows CONFLICTING while a local merge
is clean -- and where it does run it can keep both sides of a heading and silently
duplicate it. On 2026-10-01 that cost repeated re-merges of four pull requests in one night.

A fragment cannot conflict: it is a new file, `<slug>.<type>.md`, in a fragments directory
beside its changelog (`[changelog] files`), and no other change names it. Its content is
the entry exactly as it will read in the changelog. `assemble` files every fragment under
its type's `### ` heading in the unreleased section -- creating the section or the heading
where absent, in `[changelog] types` order, never a second heading of the same name -- and
deletes it, so running it twice changes nothing the second time. `release` does that and
then turns the unreleased section of each versioned changelog into the version's own,
which is what `vibey-gh promote` runs in the release commit: a release needs no hand step.

`check` is the pull request's side (`changelog.yml`): a change to a `require_for` path must
add at least one well-formed fragment unless it carries the skip label, no fragment may be
malformed, and no unreleased section may be edited by hand -- the conflict this exists to
end. A release cut, which empties the section into a new version's, is not an edit.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from pathlib import Path

from vibey_gh.config import GhConfig, load_config
from vibey_gh.interfaces.changelog_interface import (
    ChangelogFinding,
    ChangelogInterface,
    Fragment,
)
from vibey_gh.protected_paths import ProtectedPathsGuard

__all__ = ["Changelog"]

# `<slug>.<type>.md`. The type is checked against `[changelog] types` separately, so a
# misspelt one is named as unknown rather than as a bad file name.
_NAME = re.compile(r"(?P<slug>[A-Za-z0-9][A-Za-z0-9_-]*)\.(?P<kind>[^./]+)\.md")
_HEADING = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<title>.*?)[ \t]*$")
_FENCE = re.compile(r"^[ \t]{0,3}(?:```|~~~)")
# What a changelog that does not exist yet starts as when a fragment is folded into it.
NEW_CHANGELOG = "# Changelog\n"
# How many changed paths a refusal names before summarising the rest.
_SHOWN = 3
# The skip label as `changelog ensure-label` creates it: a pale grey, because it marks an
# exemption rather than a state anyone has to act on.
SKIP_LABEL_COLOUR = "EDEDED"
SKIP_LABEL_DESCRIPTION = "This pull request needs no changelog fragment"


class Changelog(ChangelogInterface):
    """Implements `ChangelogInterface`."""

    def __init__(
        self,
        *,
        config: Callable[[], GhConfig] = load_config,
        git: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
        gh: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self._config = config
        self._git = git
        self._gh = gh

    # ------------------------------------------------------------------ fragments

    def fragment_problems(self, name: str, text: str, kinds: Sequence[str]) -> tuple[str, ...]:
        problems: list[str] = []
        match = _NAME.fullmatch(name)
        if match is None:
            problems.append(
                "the name must be <slug>.<type>.md, the slug made of letters, digits, '-' and '_'"
            )
        elif match["kind"] not in kinds:
            problems.append(f"unknown type {match['kind']!r}; one of {', '.join(kinds)}")
        if not text.strip():
            problems.append("it is empty")
        elif self._headings(text.splitlines()):
            problems.append(
                "it carries a heading; a fragment is the entry alone, and assemble files it "
                "under its type's heading"
            )
        return tuple(problems)

    def fragments(self, root: Path, directory: str, kinds: Sequence[str]) -> tuple[Fragment, ...]:
        folder = root / directory
        if not folder.is_dir():
            return ()
        found: list[Fragment] = []
        problems: list[str] = []
        for path in sorted(folder.iterdir()):
            if path.name.startswith("."):
                continue
            where = f"{directory}/{path.name}"
            if not path.is_file():
                problems.append(f"{where}: fragments are files directly in {directory}/")
                continue
            text = path.read_text(encoding="utf-8")
            issues = self.fragment_problems(path.name, text, kinds)
            if issues:
                problems.extend(f"{where}: {issue}" for issue in issues)
                continue
            match = _NAME.fullmatch(path.name)
            assert match is not None  # fragment_problems has just accepted the name
            found.append(Fragment(where, match["slug"], match["kind"], text))
        if problems:
            raise ValueError("; ".join(problems))
        return tuple(found)

    # ------------------------------------------------------------------ the text

    def unreleased_section(self, text: str, unreleased: str) -> str | None:
        lines = text.splitlines()
        bounds = self._section(lines, unreleased)
        if bounds is None:
            return None
        start, end = bounds
        return "\n".join(self._trim([line.rstrip() for line in lines[start + 1 : end]]))

    def fold(
        self,
        text: str,
        unreleased: str,
        fragments: Sequence[Fragment],
        titles: Mapping[str, str],
    ) -> str:
        if not fragments:
            return text
        unknown = sorted({fragment.kind for fragment in fragments} - set(titles))
        if unknown:
            # Folding drops nothing silently: an entry with no heading to go under would be
            # deleted with its fragment and appear nowhere.
            raise ValueError(f"no heading is configured for type(s) {', '.join(unknown)}")
        lines, start, end = self._ensure_section(text.splitlines(), unreleased)
        preamble, blocks = self._blocks(lines[start + 1 : end])
        order = [title.strip().lower() for title in titles.values()]
        for kind, title in titles.items():
            entries = [line for f in fragments if f.kind == kind for line in self._entry(f.text)]
            if not entries:
                continue
            key = title.strip().lower()
            block = next((b for b in blocks if b[0].strip().lower() == key), None)
            if block is None:
                rank = order.index(key)
                at = next(
                    (
                        index
                        for index, (name, _) in enumerate(blocks)
                        if name.strip().lower() in order
                        and order.index(name.strip().lower()) > rank
                    ),
                    len(blocks),
                )
                block = (title, [])
                blocks.insert(at, block)
            body = self._trim(block[1])
            block[1][:] = [*body, *entries]
        section = [lines[start], ""]
        if self._trim(preamble):
            section += [*self._trim(preamble), ""]
        for name, body in blocks:
            section += [f"### {name}", ""]
            if self._trim(body):
                section += [*self._trim(body), ""]
        if end == len(lines):
            section = self._trim(section)
        return "\n".join([*lines[:start], *section, *lines[end:]]) + "\n"

    def cut(self, text: str, unreleased: str, heading: str, version: str, released: date) -> str:
        lines = text.splitlines()
        already = self._release_pattern(heading, version)
        if any(
            level == 2 and already.fullmatch(title) for _, level, title in self._headings(lines)
        ):
            return text
        title = heading.replace("{version}", version).replace("{date}", released.isoformat())
        lines, start, _ = self._ensure_section(lines, unreleased)
        lines[start : start + 1] = [lines[start], "", f"## {title}"]
        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------ the files

    def assemble(self, cfg: GhConfig) -> tuple[str, ...]:
        settings = cfg.changelog
        if not settings.enabled:
            return ()
        kinds = [kind for kind, _ in settings.types]
        pending = []
        problems = []
        # Every directory is read before anything is written: one malformed fragment
        # anywhere stops the whole fold, rather than leaving one changelog folded and the
        # other not.
        for entry in settings.files:
            try:
                found = self.fragments(cfg.root, entry.fragments, kinds)
            except ValueError as exc:
                problems.append(str(exc))
                continue
            if found:
                pending.append((entry, found))
        if problems:
            raise ValueError("; ".join(problems))
        touched: list[str] = []
        for entry, found in pending:
            path = cfg.root / entry.changelog
            text = path.read_text(encoding="utf-8") if path.is_file() else NEW_CHANGELOG
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                self.fold(text, entry.unreleased, found, settings.titles), encoding="utf-8"
            )
            touched.append(entry.changelog)
            for fragment in found:
                (cfg.root / fragment.path).unlink()
                touched.append(fragment.path)
            # Emptied, the directory goes too; one still holding a dotfile stays.
            with contextlib.suppress(OSError):
                (cfg.root / entry.fragments).rmdir()
        return tuple(touched)

    def release(self, cfg: GhConfig, version: str, released: date) -> tuple[str, ...]:
        settings = cfg.changelog
        if not settings.enabled:
            return ()
        touched = list(self.assemble(cfg))
        for entry in settings.files:
            path = cfg.root / entry.changelog
            if not entry.versioned or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            cut = self.cut(text, entry.unreleased, settings.release_heading, version, released)
            if cut != text:
                path.write_text(cut, encoding="utf-8")
                touched.append(entry.changelog)
        return tuple(dict.fromkeys(touched))

    # ------------------------------------------------------------------ the pull request

    def check(
        self,
        cfg: GhConfig,
        base: str,
        head: str,
        labels: Sequence[str],
        checkout: Path | None = None,
    ) -> tuple[ChangelogFinding, ...]:
        settings = cfg.changelog
        root = checkout or cfg.root
        span = f"{base}...{head}"
        merge_base = self._run(root, "merge-base", base, head)
        if merge_base.returncode:
            # Refused, not passed: a change the check could not read is a change it never
            # judged, and "no problem found" about it would be a false green.
            return (ChangelogFinding(span, f"could not be read: {merge_base.stderr.strip()}"),)
        since = merge_base.stdout.strip()
        diff = self._run(root, "diff", "--name-status", "--no-renames", "-z", since, head)
        if diff.returncode:
            return (ChangelogFinding(span, f"could not be read: {diff.stderr.strip()}"),)
        tokens = diff.stdout.split("\0")
        changes = [(tokens[i], tokens[i + 1]) for i in range(0, len(tokens) - 1, 2)]
        kinds = [kind for kind, _ in settings.types]
        folders = [entry.fragments for entry in settings.files]
        found: list[ChangelogFinding] = []
        added = 0
        others: list[str] = []
        for status, path in changes:
            folder = next((name for name in folders if path.startswith(f"{name}/")), None)
            if folder is None:
                others.append(path)
                continue
            name = path[len(folder) + 1 :]
            if status.startswith("D") or name.startswith("."):
                continue
            if "/" in name:
                found.append(ChangelogFinding(path, f"fragments are files directly in {folder}/"))
                continue
            problems = self.fragment_problems(name, self._show(root, head, path) or "", kinds)
            found.extend(ChangelogFinding(path, problem) for problem in problems)
            if status.startswith("A") and not problems:
                added += 1
        changed = {path for _, path in changes}
        releasing = False
        for entry in settings.files:
            if entry.changelog not in changed:
                continue
            before = self._show(root, since, entry.changelog) or ""
            after = self._show(root, head, entry.changelog) or ""
            was = self.unreleased_section(before, entry.unreleased) or ""
            now = self.unreleased_section(after, entry.unreleased) or ""
            if was == now:
                continue
            if now == "" and self._versions(after, entry.unreleased) - self._versions(
                before, entry.unreleased
            ):
                # A release cut: the section was emptied into a new version's own.
                releasing = True
                continue
            found.append(
                ChangelogFinding(
                    entry.changelog,
                    f"edits its `## {entry.unreleased}` section directly; write the entry as "
                    f"a fragment in {entry.fragments}/ instead, which the release files "
                    "under its heading",
                )
            )
        touched = ProtectedPathsGuard().touched(settings.require_for, others)
        skipped = bool(settings.skip_label) and settings.skip_label in labels
        if touched and not added and not skipped and not releasing:
            shown = ", ".join(touched[:_SHOWN])
            if len(touched) > _SHOWN:
                shown += f" and {len(touched) - _SHOWN} more"
            label = f", or label it {settings.skip_label!r}" if settings.skip_label else ""
            found.append(
                ChangelogFinding(
                    "the pull request",
                    f"changes {shown} but adds no changelog fragment; add one as "
                    f"<slug>.<type>.md in {' or '.join(f'{f}/' for f in folders)}"
                    f"{label} when no reader of the changelog would miss the change",
                )
            )
        return tuple(found)

    def ensure_label(self, cfg: GhConfig) -> bool:
        settings = cfg.changelog
        if not settings.enabled or not settings.skip_label:
            return False
        # `--force` makes it idempotent: an existing label is brought to this colour and
        # description rather than refused, so every run converges on the same label.
        run = self._gh(
            [
                "gh",
                "label",
                "create",
                settings.skip_label,
                "--color",
                SKIP_LABEL_COLOUR,
                "--description",
                SKIP_LABEL_DESCRIPTION,
                "--force",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode:
            raise RuntimeError(run.stderr.strip() or "gh label create failed")
        return True

    # ------------------------------------------------------------------ the command

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        actions = parser.add_subparsers(dest="changelog_action", required=True)
        actions.add_parser(
            "assemble",
            help="fold every fragment into its changelog's unreleased section and delete it",
        )
        actions.add_parser(
            "ensure-label",
            help="create or update the [changelog] skip label, so it can be applied",
        )
        check = actions.add_parser(
            "check",
            help="refuse a change with no fragment, a malformed one, or a hand-edited section",
        )
        check.add_argument("--base", required=True, help="the commit the change is measured from")
        check.add_argument("--head", default="HEAD", help="the change's head (default HEAD)")
        check.add_argument(
            "--label",
            action="append",
            default=[],
            dest="labels",
            metavar="NAME",
            help="a label the pull request carries; repeatable",
        )
        check.add_argument(
            "--labels-json",
            default="",
            metavar="JSON",
            help="the pull request's labels as a JSON array of names, as toJSON() writes it",
        )
        check.add_argument(
            "--checkout",
            type=Path,
            default=None,
            help="the clone holding the change (default: this repository). A workflow runs "
            "from its trusted checkout, so the configuration read is never the pull "
            "request's own, and points here at the pull request's clone",
        )
        return parser

    @classmethod
    def dispatch(cls, args: argparse.Namespace) -> int:
        tool = cls()
        if args.changelog_action == "assemble":
            return tool.run_assemble()
        if args.changelog_action == "ensure-label":
            return tool.run_ensure_label()
        return tool.run_check(args.base, args.head, args.labels, args.labels_json, args.checkout)

    def run_assemble(self) -> int:
        """Fold the fragments in and say what changed: 0 done, 1 refused."""
        cfg = self._config()
        if not cfg.changelog.enabled:
            print("vibey-gh: [changelog] is disabled; nothing assembled")
            return 0
        try:
            touched = self.assemble(cfg)
        except ValueError as exc:
            print(f"::error::vibey-gh: nothing assembled: {exc}")
            return 1
        if not touched:
            print("vibey-gh: no changelog fragments to assemble")
            return 0
        for path in touched:
            print(f"  {path}")
        print(f"vibey-gh: assembled {len(touched)} path(s)")
        return 0

    def run_ensure_label(self) -> int:
        """Make the skip label exist: 0 done or nothing to do, 1 refused by the forge."""
        cfg = self._config()
        try:
            created = self.ensure_label(cfg)
        except RuntimeError as exc:
            print(f"::error::vibey-gh: the changelog skip label could not be ensured: {exc}")
            return 1
        if not created:
            print("vibey-gh: [changelog] declares no skip label in use; nothing to ensure")
            return 0
        print(f"vibey-gh: the changelog skip label {cfg.changelog.skip_label!r} exists")
        return 0

    def run_check(
        self,
        base: str,
        head: str,
        labels: Sequence[str],
        labels_json: str = "",
        checkout: Path | None = None,
    ) -> int:
        """Print every finding and return the exit status: 0 clean, 1 refused."""
        cfg = self._config()
        if not cfg.changelog.enabled:
            print("vibey-gh: [changelog] is disabled; nothing checked")
            return 0
        names = list(labels)
        if labels_json.strip():
            try:
                parsed = json.loads(labels_json)
            except json.JSONDecodeError as exc:
                print(f"::error::vibey-gh: --labels-json is not JSON: {exc}")
                return 1
            if not isinstance(parsed, list) or not all(isinstance(n, str) for n in parsed):
                print("::error::vibey-gh: --labels-json must be a JSON array of label names")
                return 1
            names.extend(parsed)
        found = self.check(cfg, base, head, names, checkout)
        if not found:
            print(f"vibey-gh: the changelog of {base}...{head} is in order")
            return 0
        for finding in found:
            print(f"  {finding.where}: {finding.problem}")
        print(
            "::error::The changelog is written as fragments: one new file per change, "
            "<slug>.<type>.md, holding the entry as it should read. A fragment cannot "
            "conflict with another pull request's; an edit to the unreleased section always "
            "can. Fix every place listed above."
        )
        return 1

    # ------------------------------------------------------------------ helpers

    def _run(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return self._git(["git", *args], cwd=root, capture_output=True, text=True, check=False)

    def _show(self, root: Path, revision: str, path: str) -> str | None:
        """`path` as it stands at `revision`, or None where it does not exist there."""
        run = self._run(root, "show", f"{revision}:{path}")
        return None if run.returncode else run.stdout

    def _versions(self, text: str, unreleased: str) -> set[str]:
        """Every level-two heading but the unreleased one: the released versions."""
        lines = text.splitlines()
        return {
            title.strip().lower()
            for _, level, title in self._headings(lines)
            if level == 2 and title.strip().lower() != unreleased.strip().lower()
        }

    @staticmethod
    def _headings(lines: Sequence[str]) -> list[tuple[int, int, str]]:
        """Each ATX heading outside a fenced code block: (line index, level, title)."""
        found = []
        fenced = False
        for index, line in enumerate(lines):
            if _FENCE.match(line):
                fenced = not fenced
                continue
            match = None if fenced else _HEADING.match(line)
            if match is not None:
                found.append((index, len(match["marks"]), match["title"]))
        return found

    def _section(self, lines: Sequence[str], unreleased: str) -> tuple[int, int] | None:
        """The unreleased heading's line and the line after its section ends."""
        want = unreleased.strip().lower()
        heads = self._headings(lines)
        for position, (index, level, title) in enumerate(heads):
            if level == 2 and title.strip().lower() == want:
                end = next((i for i, lvl, _ in heads[position + 1 :] if lvl <= 2), len(lines))
                return index, end
        return None

    def _ensure_section(self, lines: list[str], unreleased: str) -> tuple[list[str], int, int]:
        """`lines` with an unreleased section, added before the first version's if absent."""
        bounds = self._section(lines, unreleased)
        if bounds is None:
            at = next((i for i, level, _ in self._headings(lines) if level == 2), len(lines))
            block = [f"## {unreleased}", ""]
            if at and lines[at - 1].strip():
                block.insert(0, "")
            lines = [*lines[:at], *block, *lines[at:]]
            bounds = self._section(lines, unreleased)
            assert bounds is not None  # just written
        return lines, bounds[0], bounds[1]

    def _blocks(self, body: Sequence[str]) -> tuple[list[str], list[tuple[str, list[str]]]]:
        """A section's lines before its first `### ` heading, then each heading's lines."""
        heads = [(index, title) for index, level, title in self._headings(body) if level == 3]
        if not heads:
            return list(body), []
        blocks = []
        for position, (index, title) in enumerate(heads):
            end = heads[position + 1][0] if position + 1 < len(heads) else len(body)
            blocks.append((title, list(body[index + 1 : end])))
        return list(body[: heads[0][0]]), blocks

    @staticmethod
    def _trim(lines: Sequence[str]) -> list[str]:
        """`lines` without their leading and trailing blank lines."""
        kept = list(lines)
        while kept and not kept[0].strip():
            kept.pop(0)
        while kept and not kept[-1].strip():
            kept.pop()
        return kept

    def _entry(self, text: str) -> list[str]:
        return self._trim([line.rstrip() for line in text.splitlines()])

    @staticmethod
    def _release_pattern(heading: str, version: str) -> re.Pattern[str]:
        """The version's heading, whatever day it was cut on."""
        fills = {"{version}": re.escape(version), "{date}": ".*?"}
        parts = re.split(r"(\{version\}|\{date\})", heading)
        return re.compile("".join(fills.get(part, re.escape(part)) for part in parts))
