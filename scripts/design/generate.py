# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Generate every design-system output from `design/tokens/`, or check that none has drifted.

    python3 scripts/design/generate.py              # write the text outputs and SVG masters
    python3 scripts/design/generate.py --rasters    # ...and re-render every PNG (a minute or so)
    python3 scripts/design/generate.py --check      # exit 1, naming each stale file
    python3 scripts/design/generate.py --contrast   # print every declared pair's WCAG ratio

Sub-doctrine 12.e: keeping a dozen copies of a stylesheet, a C header and a TikZ palette in step
with one set of decisions is toil, so it is automated, and `--check` says out loud when the step
was missed. Rasters are expensive to draw, so the check proves them another way: the manifest
records the SVG each PNG was drawn from, the check recomputes that SVG from the tokens, and the
two smallest icons are re-drawn in full to prove the renderer itself has not moved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from interfaces.design_interface import DesignGeneratorInterface  # noqa: E402

from design.emitters import (  # noqa: E402
    CHeader,
    CopiedAsset,
    CssTokens,
    GtkCss,
    PaperPalette,
    SharedStylesheet,
    TypeScriptTokens,
)
from design.identity import IdentityEmitter  # noqa: E402
from design.tokens import ContrastAudit, TokenSet  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
CONFIG = Path("design/design.json")
VERIFY_IN_FULL = ("design/dist/icons/web/favicon-16.png", "design/dist/icons/web/favicon-32.png")


class DesignGenerator(DesignGeneratorInterface):
    """All emitters over one token set, rooted at a repository checkout."""

    def __init__(self, repo: Path = REPO) -> None:
        self.repo = repo
        self.config = json.loads((repo / CONFIG).read_text(encoding="utf-8"))
        self.tokens = TokenSet(repo / self.config["tokens"])
        self.identity = IdentityEmitter(self.tokens, self.config["identity"])
        self.manifest_path = Path(self.config["rasters"])

    def outputs(self) -> dict[Path, bytes]:
        """Every text output and SVG master: cheap, always fully regenerated."""
        out: dict[Path, bytes] = {}
        identity = self.identity.outputs()
        out.update(identity)
        mark = identity[Path(self.config["identity"]) / "icon-small.svg"].decode()
        out.update(
            SharedStylesheet(self.tokens, self.config["stylesheet"], mark).outputs_for(self.repo)
        )
        out.update(CopiedAsset(self.config["script"], "//").outputs_for(self.repo))
        for emitter in (
            CssTokens(self.tokens),
            TypeScriptTokens(self.tokens),
            GtkCss(self.tokens),
            CHeader(self.tokens),
            PaperPalette(self.tokens),
        ):
            out.update(emitter.outputs())
        out[Path("design/dist/icons/favicon.svg")] = mark.encode()
        return out

    def _manifest(self) -> dict[str, dict[str, object]]:
        path = self.repo / self.manifest_path
        return json.loads(path.read_text(encoding="utf-8"))["rasters"] if path.is_file() else {}

    def write(self, *, rasters: bool = False) -> list[Path]:
        written: list[Path] = []
        for rel, data in self.outputs().items():
            target = self.repo / rel
            if not target.is_file() or target.read_bytes() != data:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                written.append(rel)
        if rasters:
            written += self._write_rasters()
        return written

    def _write_rasters(self) -> list[Path]:
        scenes = self.identity.scenes()
        svg = {name: scene.svg() for name, scene in scenes.items()}
        entries: dict[str, dict[str, object]] = {}
        written: list[Path] = []
        cache: dict[tuple[str, int, int, bool], bytes] = {}
        for rel, (scene, w, h, opaque) in self.identity.rasters().items():
            key = (scene, w, h, opaque)
            if key not in cache:
                print(f"  drawing {scene} at {w}x{h}", file=sys.stderr)
                cache[key] = scenes[scene].png(w, h, opaque=opaque)
            data = cache[key]
            target = self.repo / rel
            if not target.is_file() or target.read_bytes() != data:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                written.append(rel)
            entries[rel.as_posix()] = {
                "scene": scene,
                "width": w,
                "height": h,
                "opaque": opaque,
                "scene_sha256": hashlib.sha256(svg[scene].encode()).hexdigest(),
                "png_sha256": hashlib.sha256(data).hexdigest(),
            }
        manifest = (
            json.dumps(
                {
                    "$description": "Every PNG the design ships, the scene it was drawn from and a hash of that scene's SVG. Regenerate with `python3 scripts/design/generate.py --rasters`.",
                    "rasters": entries,
                },
                indent=2,
            )
            + "\n"
        )
        (self.repo / self.manifest_path).write_text(manifest, encoding="utf-8")
        return written

    def check(self) -> list[str]:
        problems = []
        for rel, data in self.outputs().items():
            target = self.repo / rel
            if not target.is_file():
                problems.append(f"{rel} is missing")
            elif target.read_bytes() != data:
                problems.append(f"{rel} is out of date")
        problems += self._check_rasters()
        return problems

    def _check_rasters(self) -> list[str]:
        manifest = self._manifest()
        declared = {rel.as_posix(): spec for rel, spec in self.identity.rasters().items()}
        if not manifest:
            return [f"{self.manifest_path} is missing; run with --rasters"]
        problems = []
        scenes = self.identity.scenes()
        svg_hash = {
            name: hashlib.sha256(scene.svg().encode()).hexdigest() for name, scene in scenes.items()
        }
        for rel, (scene, w, h, opaque) in declared.items():
            entry = manifest.get(rel)
            path = self.repo / rel
            if entry is None or not path.is_file():
                problems.append(f"{rel} is missing; run with --rasters")
                continue
            if (entry["scene"], entry["width"], entry["height"], entry["opaque"]) != (
                scene,
                w,
                h,
                opaque,
            ):
                problems.append(
                    f"{rel} was drawn at another size or from another scene; run with --rasters"
                )
            if entry["scene_sha256"] != svg_hash[scene]:
                problems.append(f"{rel} was drawn from an older {scene} design; run with --rasters")
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["png_sha256"]:
                problems.append(f"{rel} was edited by hand or corrupted; run with --rasters")
            if rel in VERIFY_IN_FULL and path.read_bytes() != scenes[scene].png(
                w, h, opaque=opaque
            ):
                problems.append(f"{rel} no longer matches a fresh render; run with --rasters")
        for rel in sorted(set(manifest) - set(declared)):
            problems.append(f"{rel} is in the manifest but no longer declared")
        return problems

    def contrast(self) -> ContrastAudit:
        return ContrastAudit(self.tokens, self.repo / self.config["contrast"])


# A bare function because it is this script's `__main__` entry point (ADR-0016).
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report drift; write nothing")
    mode.add_argument("--contrast", action="store_true", help="print every declared contrast pair")
    parser.add_argument("--rasters", action="store_true", help="also re-render every PNG")
    args = parser.parse_args(argv)
    generator = DesignGenerator()
    failing = [r for r in generator.contrast().results() if not r.passes]
    if args.contrast:
        for r in generator.contrast().results():
            mark = "ok  " if r.passes else "FAIL"
            print(
                f"{mark} {r.theme:5} {r.ratio:5.2f}:1 (>= {r.minimum}) {r.foreground} {r.foreground_hex} on {r.background} {r.background_hex}"
            )
        return 1 if failing else 0
    if args.check:
        problems = generator.check()
        problems += [
            f"contrast: {r.theme} {r.foreground} on {r.background} is {r.ratio:.2f}:1, below {r.minimum}"
            for r in failing
        ]
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0
    if failing:
        for r in failing:
            print(
                f"contrast: {r.theme} {r.foreground} on {r.background} is {r.ratio:.2f}:1, below {r.minimum}",
                file=sys.stderr,
            )
        return 1
    for path in generator.write(rasters=args.rasters):
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
