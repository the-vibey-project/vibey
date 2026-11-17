# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey-gh pin-actions`: pin every GitHub Actions `uses:` to the commit it names today.

A `uses: owner/repo@v4` is a moving name: whoever controls the tag controls what runs in
our pipeline. This command finds every such reference in the workflows and composite actions
and rewrites it to `owner/repo@<40-hex commit> # v4`, the tag kept as a comment so the pin
stays readable and bumpable. It is the toil automated (sub-doctrine 12.e): nobody looks up a
SHA by hand, and the check mode says out loud when one was missed.

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
from pathlib import Path
from urllib.parse import quote

from vibey_gh.gh_transport import GhTransport
from vibey_gh.interfaces.gh_transport_interface import GhTransportInterface
from vibey_gh.interfaces.pin_actions_interface import ActionUse, PinActionsInterface

__all__ = ["ActionUse", "PinActions"]

_COMMIT = re.compile(r"[0-9a-f]{40}")
# `- uses: x@y`, `uses: "x@y"` and an indented `uses:` key; group `spec` is the reference.
_USES = re.compile(r"^(?P<head>\s*(?:-\s+)?uses:\s*[\"']?)(?P<spec>[^\s#\"']+)(?P<tail>.*)$")
# What may follow the reference: a closing quote, then optionally a comment.
_TAIL = re.compile(r"^(?P<quote>[\"']?)(?P<space>\s*)(?P<comment>#.*)?$")
# `run: |`, `script: >-` and the like: a key whose value is a block scalar.
_BLOCK = re.compile(r"^(?P<indent>\s*(?:-\s+)?)[^\s#:][^#]*:\s*[|>][+-]?\d*\s*(?:#.*)?$")
_WORKFLOWS = ".github/workflows/*.yml"
_ACTIONS = ".github/actions/*/action.yml"


class PinActions(PinActionsInterface):
    """Implements `PinActionsInterface` over the forge's REST API."""

    def __init__(self, *, transport: GhTransportInterface | None = None) -> None:
        self._transport: GhTransportInterface = transport or GhTransport()

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
        answer = self._transport.json(["api", f"repos/{owner_repo}/commits/{quote(ref, safe='/')}"])
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
        shas: dict[tuple[str, str], str] = {}
        failures: list[str] = []
        for key in dict.fromkeys((use.action, use.ref) for use in uses):
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
            path.write_text(rewritten, encoding="utf-8")
            stuck.extend(self.unpinned(rewritten, path))
        if stuck:
            for use in stuck:
                print(f"{use.path}:{use.line}: {use.action}@{use.ref} could not be rewritten")
            print(f"vibey-gh: pin-actions: {len(stuck)} could not be pinned; the rest were written")
            return 1
        print(f"vibey-gh: pin-actions: pinned {len(uses)} uses to {len(shas)} commits")
        return 0

    @staticmethod
    def declare(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="resolve each ref and rewrite the files; without it, only check (no network)",
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
        return cls().run(paths, apply=args.apply)
