# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The vibey mark, wordmark and app icons: one geometry, drawn as SVG and rasterised as PNG.

The mark is the extension's "V" glyph (`clients/vscode/media/vibey.svg`) refined: the V is two
converging strokes, the bar above it is the queue it drains, and the dot where they meet is the
nucleus (sub-doctrine 9.c) with an orbit around it. Every colour comes from the token set.

Rasterising needs no imaging library. Each shape is a signed distance field, so coverage at a
pixel is `clamp(0.5 - distance)`: exact anti-aliasing for strokes, circles and rounded tiles,
deterministic to the byte, written as PNG with `zlib`. That is what lets the drift test prove a
committed icon came from these tokens without a renderer installed anywhere.
"""

from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from interfaces.design_interface import EmitterInterface, TokenSetInterface

RGBA = tuple[float, float, float, float]
Point = tuple[float, float]
UNITS = 1024.0


def _rgba(hex_value: str, alpha: float = 1.0) -> RGBA:
    """A `#rrggbb[aa]` string as 0-1 floats. A module function: a pure conversion helper."""
    r, g, b = (int(hex_value[i : i + 2], 16) / 255 for i in (1, 3, 5))
    a = int(hex_value[7:9], 16) / 255 if len(hex_value) == 9 else 1.0
    return (r, g, b, a * alpha)


@dataclass(frozen=True)
class Linear:
    """A linear gradient between two points, evenly spaced stops."""

    start: Point
    end: Point
    stops: tuple[RGBA, ...]

    def at(self, x: float, y: float) -> RGBA:
        dx, dy = self.end[0] - self.start[0], self.end[1] - self.start[1]
        t = ((x - self.start[0]) * dx + (y - self.start[1]) * dy) / (dx * dx + dy * dy)
        t = min(1.0, max(0.0, t)) * (len(self.stops) - 1)
        i = min(int(t), len(self.stops) - 2)
        f = t - i
        a, b = self.stops[i], self.stops[i + 1]
        return (
            a[0] + (b[0] - a[0]) * f,
            a[1] + (b[1] - a[1]) * f,
            a[2] + (b[2] - a[2]) * f,
            a[3] + (b[3] - a[3]) * f,
        )


Paint = RGBA | Linear


@dataclass(frozen=True)
class Shape:
    """One filled or stroked primitive. `kind` picks the distance function."""

    kind: str  # "capsule" | "circle" | "arc" | "rect" | "ellipse-ring" | "glow"
    paint: Paint
    points: tuple[Point, ...] = ()
    radius: float = 0.0
    width: float = 0.0
    extra: tuple[
        float, ...
    ] = ()  # arc: (start, end) radians; rect: (w, h, r); ellipse: (rx, ry, rot)
    # glow clip: a rounded rect (x, y, w, h, r)
    clip: tuple[float, float, float, float, float] | None = None
    # "electron": `extra` is then its orbit (cx, cy, rx, ry, rotation, phase)
    role: str = ""

    def bounds(self) -> tuple[float, float, float, float]:
        pad = self.width / 2 + self.radius + 2
        if self.kind == "rect":
            (x, y), (w, h, _r) = self.points[0], self.extra
            return x - 1, y - 1, x + w + 1, y + h + 1
        if self.kind == "ellipse-ring":
            (cx, cy), (rx, ry, _rot) = self.points[0], self.extra
            m = max(rx, ry) + self.width
            return cx - m, cy - m, cx + m, cy + m
        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        if self.clip is not None:
            cx, cy, cw, ch, _ = self.clip
            return cx, cy, cx + cw, cy + ch
        return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad

    def distance(self, x: float, y: float) -> float:
        """Signed distance in master units: negative inside the painted area."""
        if self.kind == "capsule":
            (ax, ay), (bx, by) = self.points
            dx, dy = bx - ax, by - ay
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
            return math.hypot(x - ax - dx * t, y - ay - dy * t) - self.width / 2
        if self.kind == "circle":
            (cx, cy) = self.points[0]
            return math.hypot(x - cx, y - cy) - self.radius
        if self.kind == "arc":
            (cx, cy), (a0, a1) = self.points[0], self.extra
            angle = math.atan2(y - cy, x - cx) % math.tau
            lo, hi = a0 % math.tau, (a0 + ((a1 - a0) % math.tau))
            within = lo <= angle <= hi or lo <= angle + math.tau <= hi
            if within:
                return abs(math.hypot(x - cx, y - cy) - self.radius) - self.width / 2
            ends = [
                (cx + self.radius * math.cos(a), cy + self.radius * math.sin(a)) for a in (a0, a1)
            ]
            return min(math.hypot(x - ex, y - ey) for ex, ey in ends) - self.width / 2
        if self.kind == "rect":
            (x0, y0), (w, h, r) = self.points[0], self.extra
            qx = abs(x - (x0 + w / 2)) - (w / 2 - r)
            qy = abs(y - (y0 + h / 2)) - (h / 2 - r)
            return math.hypot(max(qx, 0.0), max(qy, 0.0)) + min(max(qx, qy), 0.0) - r
        if self.kind == "ellipse-ring":
            (cx, cy), (rx, ry, rot) = self.points[0], self.extra
            c, s = math.cos(-rot), math.sin(-rot)
            px, py = (x - cx) * c - (y - cy) * s, (x - cx) * s + (y - cy) * c
            f = (px / rx) ** 2 + (py / ry) ** 2 - 1
            grad = math.hypot(2 * px / rx**2, 2 * py / ry**2) or 1e-9
            return abs(f / grad) - self.width / 2
        raise ValueError(f"unknown shape kind {self.kind}")

    def colour(self, x: float, y: float) -> RGBA:
        base = self.paint.at(x, y) if isinstance(self.paint, Linear) else self.paint
        if self.kind == "glow":
            (cx, cy) = self.points[0]
            t = min(1.0, math.hypot(x - cx, y - cy) / self.radius)
            return (base[0], base[1], base[2], base[3] * (1 - t) ** 2)
        return base


@dataclass
class Scene:
    """Shapes painted in order over a transparent (or opaque) canvas of `width` x `height` units."""

    width: float
    height: float
    shapes: list[Shape] = field(default_factory=list)
    title: str = "vibey"
    key: str = "vibey"
    orbit: float = 0.0  # namespaces gradient ids, so two inlined SVGs never share one

    # -- SVG ---------------------------------------------------------------------------------

    def svg(self, *, orbit_seconds: float = 0.0) -> str:
        """The scene as SVG. `orbit_seconds` > 0 sets the electrons orbiting in CSS; under
        `prefers-reduced-motion` each rests exactly where the static mark draws it."""
        defs: list[str] = []
        body: list[str] = []
        self.orbit = orbit_seconds
        if orbit_seconds:
            defs.append(
                f"<style>.{self.key}-e{{animation:{self.key}-orbit {_num(orbit_seconds)}s linear infinite}}"
                f"@keyframes {self.key}-orbit{{to{{offset-distance:100%}}}}"
                f"@media (prefers-reduced-motion:reduce){{.{self.key}-e{{animation:none}}}}</style>\n"
            )
        for n, shape in enumerate(self.shapes):
            fill = self._svg_paint(shape, n, defs)
            if orbit_seconds and shape.role == "electron":
                body.append(self._svg_electron(shape, fill))
            else:
                body.append(self._svg_shape(shape, fill))
        w, h = _num(self.width), _num(self.height)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img" aria-label="{self.title}">\n<title>{self.title}</title>\n'
            + (f"<defs>\n{''.join(defs)}</defs>\n" if defs else "")
            + "".join(body)
            + "</svg>\n"
        )

    @staticmethod
    def _svg_colour(c: RGBA) -> tuple[str, str]:
        hx = "#" + "".join(f"{round(v * 255):02x}" for v in c[:3])
        return hx, _num(round(c[3], 3))

    def _svg_paint(self, shape: Shape, n: int, defs: list[str]) -> str:
        if shape.kind == "glow":
            hx, a = self._svg_colour(
                shape.paint if not isinstance(shape.paint, Linear) else shape.paint.stops[0]
            )
            (cx, cy) = shape.points[0]
            stops = "".join(
                f'<stop offset="{_num(t)}" stop-color="{hx}" stop-opacity="{_num(round(float(a) * (1 - t) ** 2, 4))}"/>'
                for t in (0, 0.25, 0.5, 0.75, 1)
            )
            defs.append(
                f'<radialGradient id="{self.key}-g{n}" cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(shape.radius)}" '
                f'gradientUnits="userSpaceOnUse">{stops}</radialGradient>\n'
            )
            return f"url(#{self.key}-g{n})"
        if isinstance(shape.paint, Linear):
            p = shape.paint
            last = len(p.stops) - 1
            stops = ""
            for i, c in enumerate(p.stops):
                hx, a = self._svg_colour(c)
                stops += f'<stop offset="{_num(round(i / last, 4))}" stop-color="{hx}" stop-opacity="{a}"/>'
            defs.append(
                f'<linearGradient id="{self.key}-g{n}" x1="{_num(p.start[0])}" y1="{_num(p.start[1])}" '
                f'x2="{_num(p.end[0])}" y2="{_num(p.end[1])}" gradientUnits="userSpaceOnUse">{stops}</linearGradient>\n'
            )
            return f"url(#{self.key}-g{n})"
        hx, a = self._svg_colour(shape.paint)
        return hx if a == "1" else f"{hx};{a}"

    def _svg_electron(self, shape: Shape, fill: str) -> str:
        """An electron riding its orbit: a CSS offset-path along the rotated ellipse."""
        cx, cy, rx, ry, rot, phase, period = shape.extra
        points = []
        for i in range(73):
            t = phase + math.tau * i / 72
            ex, ey = rx * math.cos(t), ry * math.sin(t)
            points.append(
                f"{_num(cx + ex * math.cos(rot) - ey * math.sin(rot))} "
                f"{_num(cy + ex * math.sin(rot) + ey * math.cos(rot))}"
            )
        path = "M" + " L".join(points) + " Z"
        paint, _, opacity = fill.partition(";")
        alpha = f' fill-opacity="{opacity}"' if opacity else ""
        return (
            f'<circle class="{self.key}-e" r="{_num(shape.radius)}" fill="{paint}"{alpha} '
            f"style=\"offset-path:path('{path}');offset-rotate:0deg;animation-duration:{_num(round(self.orbit * period, 2))}s\"/>\n"
        )

    @staticmethod
    def _svg_shape(shape: Shape, fill: str) -> str:
        paint, _, opacity = fill.partition(";")
        stroke_opacity = f' stroke-opacity="{opacity}"' if opacity else ""
        fill_opacity = f' fill-opacity="{opacity}"' if opacity else ""
        if shape.kind == "capsule":
            (ax, ay), (bx, by) = shape.points
            return (
                f'<line x1="{_num(ax)}" y1="{_num(ay)}" x2="{_num(bx)}" y2="{_num(by)}" stroke="{paint}"'
                f'{stroke_opacity} stroke-width="{_num(shape.width)}" stroke-linecap="round"/>\n'
            )
        if shape.kind == "circle":
            (cx, cy) = shape.points[0]
            return f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(shape.radius)}" fill="{paint}"{fill_opacity}/>\n'
        if shape.kind == "glow":
            (cx, cy) = shape.points[0]
            if shape.clip is not None:
                x, y, w, h, r = shape.clip
                return (
                    f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" rx="{_num(r)}" '
                    f'fill="{paint}"/>\n'
                )
            return f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(shape.radius)}" fill="{paint}"/>\n'
        if shape.kind == "arc":
            (cx, cy), (a0, a1) = shape.points[0], shape.extra
            if (a1 - a0) % math.tau > math.tau - 1e-3 or (a1 - a0) % math.tau < 1e-9:
                # A closed arc's endpoints coincide, and SVG draws such an arc as nothing.
                return (
                    f'<circle cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(shape.radius)}" fill="none" '
                    f'stroke="{paint}"{stroke_opacity} stroke-width="{_num(shape.width)}"/>\n'
                )
            sx, sy = cx + shape.radius * math.cos(a0), cy + shape.radius * math.sin(a0)
            ex, ey = cx + shape.radius * math.cos(a1), cy + shape.radius * math.sin(a1)
            large = 1 if ((a1 - a0) % math.tau) > math.pi else 0
            r = _num(shape.radius)
            return (
                f'<path d="M{_num(sx)} {_num(sy)}A{r} {r} 0 {large} 1 {_num(ex)} {_num(ey)}" fill="none" '
                f'stroke="{paint}"{stroke_opacity} stroke-width="{_num(shape.width)}" stroke-linecap="round"/>\n'
            )
        if shape.kind == "rect":
            (x, y), (w, h, r) = shape.points[0], shape.extra
            return (
                f'<rect x="{_num(x)}" y="{_num(y)}" width="{_num(w)}" height="{_num(h)}" rx="{_num(r)}" '
                f'fill="{paint}"{fill_opacity}/>\n'
            )
        if shape.kind == "ellipse-ring":
            (cx, cy), (rx, ry, rot) = shape.points[0], shape.extra
            return (
                f'<ellipse cx="{_num(cx)}" cy="{_num(cy)}" rx="{_num(rx)}" ry="{_num(ry)}" '
                f'transform="rotate({_num(round(math.degrees(rot), 3))} {_num(cx)} {_num(cy)})" fill="none" '
                f'stroke="{paint}"{stroke_opacity} stroke-width="{_num(shape.width)}"/>\n'
            )
        raise ValueError(shape.kind)

    # -- raster ------------------------------------------------------------------------------

    def png(self, width: int, height: int, *, opaque: bool = False) -> bytes:
        """Rasterise at `width` x `height` pixels. `opaque` drops the alpha channel (iOS)."""
        sx, sy = self.width / width, self.height / height
        scale = max(sx, sy)
        pixels = [[0.0, 0.0, 0.0, 0.0] for _ in range(width * height)]
        for shape in self.shapes:
            x0, y0, x1, y1 = shape.bounds()
            if shape.kind == "glow" and shape.clip is None:
                (cx, cy) = shape.points[0]
                x0, y0, x1, y1 = (
                    cx - shape.radius,
                    cy - shape.radius,
                    cx + shape.radius,
                    cy + shape.radius,
                )
            px0, px1 = max(0, int(x0 / sx)), min(width, int(math.ceil(x1 / sx)) + 1)
            py0, py1 = max(0, int(y0 / sy)), min(height, int(math.ceil(y1 / sy)) + 1)
            for py in range(py0, py1):
                uy = (py + 0.5) * sy
                row = py * width
                for px in range(px0, px1):
                    ux = (px + 0.5) * sx
                    if shape.kind == "glow":
                        cover = 1.0
                        if shape.clip is not None:
                            gx, gy, gw, gh, gr = shape.clip
                            edge = Shape("rect", (0, 0, 0, 0), ((gx, gy),), extra=(gw, gh, gr))
                            cover = min(1.0, 0.5 - edge.distance(ux, uy) / scale)
                            if cover <= 0:
                                continue
                    else:
                        cover = 0.5 - shape.distance(ux, uy) / scale
                        if cover <= 0:
                            continue
                        cover = min(cover, 1.0)
                    r, g, b, a = shape.colour(ux, uy)
                    a *= cover
                    if a <= 0:
                        continue
                    dst = pixels[row + px]
                    out_a = a + dst[3] * (1 - a)
                    for i, c in enumerate((r, g, b)):
                        dst[i] = (c * a + dst[i] * dst[3] * (1 - a)) / out_a
                    dst[3] = out_a
        return _png(pixels, width, height, opaque)


def _num(value: float) -> str:
    """Shortest decimal for an SVG attribute. A module function: pure formatting."""
    text = f"{value:.3f}".rstrip("0").rstrip(".")
    return text if text not in ("-0", "") else "0"


def _png(pixels: list[list[float]], width: int, height: int, opaque: bool) -> bytes:
    """Encode straight-alpha pixels as an 8-bit PNG. A module function: a pure encoder."""
    channels = 3 if opaque else 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for p in pixels[y * width : (y + 1) * width]:
            raw += bytes(max(0, min(255, round(v * 255))) for v in p[:channels])

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

    colour_type = 2 if opaque else 6
    header = struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


@dataclass(frozen=True)
class Palette:
    """The colours one rendering of the identity uses: on the night tile, or on a light page."""

    shell_from: RGBA
    shell_to: RGBA
    word_to: RGBA
    proton: RGBA
    neutron: RGBA
    electron: RGBA
    halo: RGBA


#: krypton-84: Z = 36 protons, N = 48 neutrons, and 36 electrons in four Bohr shells.
PROTONS, NEUTRONS = 36, 48
SHELLS = (2, 8, 18, 8)

#: How much of the atom a size can carry. `full` is the real Kr-84 (every nucleon, every
#: electron) from 128 px up; `medium` keeps four shells with fewer electrons and a nucleus of
#: a dozen visible nucleons (48-64 px, and the dot on the i); `small` (22-32 px) keeps the four
#: shells, a nucleus blob with a few nucleons, and one or two electrons a shell. `tiny` (16 px)
#: keeps two shells: four circles a pixel apart alias into a moire, measured, not guessed. Radii follow the Bohr model's n-squared growth, relaxed so the nucleus fits inside
#: the first shell, and relaxed further at small sizes so four shells stay four lines.
ATOM_DETAIL: dict[str, dict[str, object]] = {
    "full": {
        "radii": tuple(0.253 + 0.0467 * n * n for n in (1, 2, 3, 4)),
        "nucleus": 0.19,
        "nucleons": PROTONS + NEUTRONS,
        "electrons": SHELLS,
        "stroke": 0.009,
        "electron": 0.017,
    },
    "medium": {
        "radii": (0.36, 0.53, 0.74, 1.0),
        "nucleus": 0.22,
        "nucleons": 12,
        "electrons": (2, 4, 6, 4),
        "stroke": 0.022,
        "electron": 0.04,
    },
    "small": {
        "radii": (0.4, 0.6, 0.8, 1.0),
        "nucleus": 0.24,
        "nucleons": 5,
        "electrons": (1, 2, 2, 2),
        "stroke": 0.058,
        "electron": 0.065,
    },
    "tiny": {
        "radii": (0.62, 1.0),
        "nucleus": 0.34,
        "nucleons": 3,
        "electrons": (0, 1),
        "stroke": 0.13,
        "electron": 0.13,
    },
}

#: Each shell's electrons are turned by this much (degrees) so the whole reads balanced:
#: the pair stands vertical, the two octets interleave, the eighteen start at the right.
SHELL_OFFSET = (90.0, 22.5, 0.0, 0.0)  # tiny's two shells take the first two
#: Relative orbit periods in animated contexts: outer shells turn more slowly.
SHELL_PERIOD = (0.55, 0.8, 1.15, 1.6)
GOLDEN = math.pi * (3 - math.sqrt(5))


class Identity:
    """Builds every identity scene from the token set."""

    def __init__(self, tokens: TokenSetInterface) -> None:
        t = tokens.hex
        self.night = _rgba(t("theme.dark.bg.canvas"))
        self.night_raised = _rgba(t("theme.dark.bg.overlay"))
        self.print_ink = _rgba(t("print.vibeyink"))
        self.glow_violet = _rgba(t("color.violet.425"), 0.62)
        self.glow_cyan = _rgba(t("theme.dark.status.info"), 0.34)
        self.dark = Palette(
            shell_from=_rgba(t("theme.dark.accent.hover")),
            shell_to=_rgba(t("theme.dark.status.info")),
            word_to=_rgba(t("theme.dark.status.success")),
            proton=_rgba(t("theme.dark.accent.default")),
            neutron=_rgba(t("theme.dark.status.success")),
            electron=_rgba(t("theme.dark.text.primary")),
            halo=_rgba(t("theme.dark.accent.default"), 0.7),
        )
        self.light = Palette(
            shell_from=_rgba(t("theme.light.accent.default")),
            shell_to=_rgba(t("theme.light.status.info")),
            word_to=_rgba(t("theme.light.status.success")),
            proton=_rgba(t("theme.light.accent.default")),
            neutron=_rgba(t("theme.light.status.success")),
            electron=_rgba(t("theme.light.accent.hover")),
            halo=_rgba(t("theme.light.accent.default"), 0.18),
        )

    @staticmethod
    def _lit(c: RGBA, amount: float) -> RGBA:
        """The colour moved toward white: a sphere's highlight."""
        return (
            c[0] + (1 - c[0]) * amount,
            c[1] + (1 - c[1]) * amount,
            c[2] + (1 - c[2]) * amount,
            c[3],
        )

    def _nucleus(
        self, cx: float, cy: float, radius: float, count: int, pal: Palette, mono: RGBA | None
    ) -> list[Shape]:
        """`count` nucleons packed on a sunflower spiral, protons evenly interleaved.

        At full detail that is Kr-84's 36 protons and 48 neutrons. Each nucleon is a small
        sphere: a disc lit from the top left. They are drawn from the outside in, so the core
        sits on top and the cluster reads as a ball rather than a flat disc.
        """
        shapes: list[Shape] = []
        step = radius / math.sqrt(count + 0.5)
        ball = step * (1.08 if count > 20 else 0.9)
        placed = []
        for i in range(count):
            r = step * math.sqrt(i + 0.5)
            a = i * GOLDEN
            proton = math.floor((i + 1) * PROTONS / (PROTONS + NEUTRONS)) > math.floor(
                i * PROTONS / (PROTONS + NEUTRONS)
            )
            placed.append((r, cx + r * math.cos(a), cy + r * math.sin(a), proton))
        if count <= 12:
            # A blob behind the few nucleons a small size can show, so it still reads as a nucleus.
            base = mono or pal.proton
            shapes.append(
                Shape(
                    "circle",
                    mono
                    or Linear(
                        (cx - radius, cy - radius),
                        (cx + radius, cy + radius),
                        (self._lit(base, 0.35), base),
                    ),
                    ((cx, cy),),
                    radius=radius,
                )
            )
        for _r, x, y, proton in sorted(placed, key=lambda p: -p[0]):
            base = mono or (pal.proton if proton else pal.neutron)
            paint: Paint = (
                base
                if mono
                else Linear(
                    (x - ball, y - ball), (x + ball, y + ball), (self._lit(base, 0.55), base, base)
                )
            )
            shapes.append(Shape("circle", paint, ((x, y),), radius=ball))
        return shapes

    def atom(
        self,
        centre: Point,
        radius: float,
        *,
        detail: str = "full",
        palette: Palette | None = None,
        mono: RGBA | None = None,
    ) -> list[Shape]:
        """krypton: a nucleus of packed nucleons, four concentric shells, electrons on each."""
        if detail not in ATOM_DETAIL:
            raise ValueError(f"atom detail is one of {tuple(ATOM_DETAIL)}, not {detail}")
        spec = ATOM_DETAIL[detail]
        radii = [radius * float(r) for r in spec["radii"]]  # type: ignore[attr-defined]
        pal = palette or self.dark
        cx, cy = centre
        stroke = radius * float(spec["stroke"])  # type: ignore[arg-type]
        ring: Paint = mono or Linear(
            (cx - radius, cy - radius), (cx + radius, cy + radius), (pal.shell_from, pal.shell_to)
        )
        shapes: list[Shape] = []
        if mono is None and detail in ("full", "medium"):
            shapes.append(
                Shape("glow", pal.halo, (centre,), radius=radius * float(spec["nucleus"]) * 3.2)
            )  # type: ignore[arg-type]
        for r in radii:
            shapes.append(Shape("ellipse-ring", ring, (centre,), width=stroke, extra=(r, r, 0.0)))
        shapes += self._nucleus(
            cx, cy, radius * float(spec["nucleus"]), int(spec["nucleons"]), pal, mono
        )  # type: ignore[call-overload]
        size = radius * float(spec["electron"])  # type: ignore[arg-type]
        for shell, (r, count) in enumerate(zip(radii, spec["electrons"], strict=True)):  # type: ignore[call-overload]
            for j in range(count):
                phase = math.radians(SHELL_OFFSET[shell]) + math.tau * j / count
                shapes.append(
                    Shape(
                        "circle",
                        mono or pal.electron,
                        ((cx + r * math.cos(phase), cy + r * math.sin(phase)),),
                        radius=size,
                        extra=(cx, cy, r, r, 0.0, phase, SHELL_PERIOD[shell]),
                        role="electron",
                    )
                )
        return shapes

    def _mark(
        self,
        cx: float,
        cy: float,
        radius: float,
        *,
        detail: str = "full",
        palette: Palette | None = None,
        mono: RGBA | None = None,
    ) -> list[Shape]:
        """The mark is the atom and nothing else."""
        return self.atom((cx, cy), radius, detail=detail, palette=palette, mono=mono)

    def _tile(self, size: float, radius: float) -> list[Shape]:
        return [
            Shape(
                "rect",
                Linear((0, 0), (size, size), (self.night_raised, self.night)),
                ((0, 0),),
                extra=(size, size, radius),
            ),
            Shape("glow", self.glow_violet, ((size * 0.28, size * 0.22),), radius=size * 0.62),
            Shape("glow", self.glow_cyan, ((size * 0.86, size * 0.9),), radius=size * 0.5),
        ]

    def icon(self, *, detail: str = "full", radius: float = 228) -> Scene:
        """The app icon master: the atom on the night tile, 1024 units square."""
        tile = _clip_glows(self._tile(UNITS, radius), UNITS, radius)
        size = {"full": 395.0, "medium": 405.0, "small": 420.0, "tiny": 430.0}[detail]
        return Scene(UNITS, UNITS, tile + self._mark(512, 512, size, detail=detail))

    def mark(
        self, *, detail: str = "full", palette: Palette | None = None, mono: RGBA | None = None
    ) -> Scene:
        """The mark alone on transparent ground."""
        return Scene(
            UNITS, UNITS, self._mark(512, 512, 470, detail=detail, palette=palette, mono=mono)
        )

    def adaptive_foreground(self) -> Scene:
        """Android adaptive foreground: the atom inside the 66/108 safe circle."""
        return Scene(UNITS, UNITS, self._mark(512, 512, 300, detail="full"))

    def adaptive_background(self) -> Scene:
        return Scene(UNITS, UNITS, _clip_glows(self._tile(UNITS, 0), UNITS, 0))

    def wordmark(
        self, *, palette: Palette | None = None, mono: RGBA | None = None, k: float = 20.0
    ) -> Scene:
        """`vibey` in the mark's monoline stroke; the dot on the i is the atom."""
        pal = palette or self.dark
        w = 2.35 * k
        pad = w
        ox, oy = pad, pad + 6.4 * k  # x-height top at oy; baseline at oy + 10k

        def p(x: float, y: float) -> Point:
            return (ox + x * k, oy + y * k)

        paint: Paint = mono or Linear(
            p(0, 0), p(46, 10), (pal.shell_from, pal.shell_to, pal.word_to)
        )
        shapes = [
            Shape("capsule", paint, (p(0, 0), p(4, 10)), width=w),
            Shape("capsule", paint, (p(8, 0), p(4, 10)), width=w),
            Shape("capsule", paint, (p(11.6, 0), p(11.6, 10)), width=w),
            Shape("capsule", paint, (p(15.2, -5.5), p(15.2, 10)), width=w),
            Shape(
                "arc", paint, (p(19.9, 5),), radius=4.7 * k, width=w, extra=(0.0, math.tau - 1e-6)
            ),
            Shape("capsule", paint, (p(27.2, 5), p(36.2, 5)), width=w),
            Shape(
                "arc",
                paint,
                (p(31.7, 5),),
                radius=4.5 * k,
                width=w,
                extra=(math.radians(40), math.tau),
            ),
            Shape("capsule", paint, (p(39.4, 0), p(43.4, 10)), width=w),
            Shape("capsule", paint, (p(47.4, 0), p(40.9, 16)), width=w),
        ]
        shapes += self.atom(p(11.6, -3.7), 1.95 * k, detail="small", palette=pal, mono=mono)
        return Scene(47.4 * k + 2 * pad, 22.4 * k + 2 * pad, shapes, title="vibey")

    def krypton(
        self, *, palette: Palette | None = None, mono: RGBA | None = None, k: float = 20.0
    ) -> Scene:
        """`krypton`, the apps' name, in the same monoline stroke; its o is the atom."""
        pal = palette or self.dark
        w = 2.35 * k
        pad = w
        ox, oy = pad, pad + 6.4 * k

        def p(x: float, y: float) -> Point:
            return (ox + x * k, oy + y * k)

        paint: Paint = mono or Linear(
            p(0, 0), p(67, 10), (pal.shell_from, pal.shell_to, pal.word_to)
        )
        shapes = [
            # k: an ascender stem, an arm from the x-height, a leg to the baseline
            Shape("capsule", paint, (p(0, -5.5), p(0, 10)), width=w),
            Shape("capsule", paint, (p(6.8, 0), p(0.6, 5.6)), width=w),
            Shape("capsule", paint, (p(3.0, 3.5), p(7.2, 10)), width=w),
            # r
            Shape("capsule", paint, (p(11.2, 0), p(11.2, 10)), width=w),
            Shape(
                "arc",
                paint,
                (p(15.0, 3.9),),
                radius=3.8 * k,
                width=w,
                extra=(math.radians(180), math.radians(292)),
            ),
            # y
            Shape("capsule", paint, (p(19.2, 0), p(23.2, 10)), width=w),
            Shape("capsule", paint, (p(27.2, 0), p(20.7, 16)), width=w),
            # p
            Shape("capsule", paint, (p(30.8, 0), p(30.8, 16)), width=w),
            Shape(
                "arc", paint, (p(35.5, 5),), radius=4.7 * k, width=w, extra=(0.0, math.tau - 1e-6)
            ),
            # t
            Shape("capsule", paint, (p(44.0, -4.2), p(44.0, 10)), width=w),
            Shape("capsule", paint, (p(41.0, 0), p(47.0, 0)), width=w),
            # n
            Shape("capsule", paint, (p(62.2, 0), p(62.2, 10)), width=w),
            Shape(
                "arc",
                paint,
                (p(66.5, 4.4),),
                radius=4.3 * k,
                width=w,
                extra=(math.radians(180), math.radians(360)),
            ),
            Shape("capsule", paint, (p(70.8, 4.4), p(70.8, 10)), width=w),
        ]
        # o: a full-weight ring, the p's bowl in size, with the atom inside it.
        shapes.append(
            Shape(
                "arc", paint, (p(53.2, 5),), radius=4.7 * k, width=w, extra=(0.0, math.tau - 1e-6)
            )
        )
        shapes += self.atom(p(53.2, 5), 2.75 * k, detail="small", palette=pal, mono=mono)
        return Scene(70.8 * k + 2 * pad, 22.4 * k + 2 * pad, shapes, title="krypton")

    def krypton_lockup(self, *, palette: Palette | None = None) -> Scene:
        """The apps' logo: the krypton icon tile beside the krypton wordmark."""
        tile_size = 520.0
        tile = _clip_glows(self._tile(tile_size, tile_size * 0.223), tile_size, tile_size * 0.223)
        mark = self._mark(tile_size / 2, tile_size / 2, 205)
        word = self.krypton(palette=palette, k=15.0)
        dx = tile_size + 70
        dy = (tile_size - word.height) / 2 + 20
        moved = [_translate(s, dx, dy) for s in word.shapes]
        return Scene(dx + word.width, tile_size, tile + mark + moved, title="krypton")

    def lockup(self, *, palette: Palette | None = None) -> Scene:
        """Mark tile and wordmark side by side: the logo. The tile is always night."""
        tile_size = 520.0
        tile = _clip_glows(self._tile(tile_size, tile_size * 0.223), tile_size, tile_size * 0.223)
        mark = self._mark(tile_size / 2, tile_size / 2, 205)
        word = self.wordmark(palette=palette, k=17.0)
        dx = tile_size + 70
        dy = (tile_size - word.height) / 2 + 20
        moved = [_translate(s, dx, dy) for s in word.shapes]
        return Scene(dx + word.width, tile_size, tile + mark + moved)

    def social(self) -> Scene:
        """The 1200 x 630 link-preview image: night sky, the icon, the wordmark."""
        w, h = 1200.0, 630.0
        shapes = [
            Shape(
                "rect",
                Linear((0, 0), (w, h), (self.night_raised, self.night, self.night)),
                ((0, 0),),
                extra=(w, h, 0),
            ),
            Shape("glow", self.glow_violet, ((200, 120),), radius=620, clip=(0, 0, w, h, 0)),
            Shape("glow", self.glow_cyan, ((1080, 560),), radius=520, clip=(0, 0, w, h, 0)),
        ]
        for x in range(60, int(w), 60):
            shapes.append(Shape("capsule", (1, 1, 1, 0.035), ((x, 0), (x, h)), width=1.4))
        for y in range(60, int(h), 60):
            shapes.append(Shape("capsule", (1, 1, 1, 0.035), ((0, y), (w, y)), width=1.4))
        size = 330.0
        tx, ty = 110.0, (h - size) / 2
        tile = [
            _translate(s, tx, ty)
            for s in _clip_glows(self._tile(size, size * 0.223), size, size * 0.223)
        ]
        mark = self._mark(tx + size / 2, ty + size / 2, 130)
        word = self.wordmark(k=11.6)
        moved = [_translate(s, 510, (h - word.height) / 2 + 18) for s in word.shapes]
        return Scene(
            w,
            h,
            shapes + tile + mark + moved,
            title="vibey: a six-phase conductor for autonomous software delivery",
        )


def _translate(shape: Shape, dx: float, dy: float) -> Shape:
    """The same shape moved; gradients move with it. A module function: a pure transform."""
    paint = shape.paint
    if isinstance(paint, Linear):
        paint = Linear(
            (paint.start[0] + dx, paint.start[1] + dy),
            (paint.end[0] + dx, paint.end[1] + dy),
            paint.stops,
        )
    clip = None if shape.clip is None else (shape.clip[0] + dx, shape.clip[1] + dy, *shape.clip[2:])
    extra = shape.extra
    if shape.role == "electron":
        extra = (extra[0] + dx, extra[1] + dy, *extra[2:])
    return Shape(
        shape.kind,
        paint,
        tuple((x + dx, y + dy) for x, y in shape.points),
        shape.radius,
        shape.width,
        extra,
        clip,
        shape.role,
    )


def _clip_glows(tile: list[Shape], size: float, radius: float) -> list[Shape]:
    """Glows limited to the tile's square (and, in SVG, drawn as squares). A module function."""
    out = [tile[0]]
    for glow in tile[1:]:
        out.append(
            Shape(
                "glow", glow.paint, glow.points, radius=glow.radius, clip=(0, 0, size, size, radius)
            )
        )
    return out


#: Raster targets: output path -> (scene name, pixel width, pixel height, opaque).
ICON_SIZES_HICOLOR = (16, 22, 24, 32, 48, 64, 128, 256, 512)
ICONSET = (
    (16, 1),
    (16, 2),
    (32, 1),
    (32, 2),
    (128, 1),
    (128, 2),
    (256, 1),
    (256, 2),
    (512, 1),
    (512, 2),
)


def _icon_for(pixels: int) -> str:
    """Which level of atom detail an icon of this size carries. A module function: a lookup."""
    if pixels <= 16:
        return "icon-tiny"
    if pixels <= 32:
        return "icon-small"
    if pixels <= 64:
        return "icon-medium"
    return "icon"


class IdentityEmitter(EmitterInterface):
    """SVG masters (cheap, always checked) and the declared raster set."""

    def __init__(self, tokens: TokenSetInterface, root: str = "design/identity") -> None:
        self._identity = Identity(tokens)
        self._orbit_seconds = 4 * tokens.get("motion.duration.ambient").value["value"] / 1000
        self._root = Path(root)

    def scenes(self) -> dict[str, Scene]:
        i = self._identity
        scenes = {
            "mark": i.mark(),
            "mark-light": i.mark(palette=i.light),
            "mark-mono": i.mark(mono=(0, 0, 0, 1)),
            "atom": Scene(UNITS, UNITS, i.atom((512, 512), 440)),
            "atom-medium": Scene(UNITS, UNITS, i.atom((512, 512), 440, detail="medium")),
            "atom-light": Scene(UNITS, UNITS, i.atom((512, 512), 440, palette=i.light)),
            "wordmark": i.wordmark(),
            "wordmark-light": i.wordmark(palette=i.light),
            "wordmark-ink": i.wordmark(mono=i.print_ink),
            "logo": i.lockup(),
            "logo-light": i.lockup(palette=i.light),
            "krypton": i.krypton(),
            "krypton-light": i.krypton(palette=i.light),
            "krypton-ink": i.krypton(mono=i.print_ink),
            "krypton-logo": i.krypton_lockup(),
            "krypton-logo-light": i.krypton_lockup(palette=i.light),
            "icon": i.icon(),
            "icon-medium": i.icon(detail="medium"),
            "icon-small": i.icon(detail="small"),
            "icon-tiny": i.icon(detail="tiny"),
            "android-foreground": i.adaptive_foreground(),
            "android-background": i.adaptive_background(),
            "social": i.social(),
        }
        for name, scene in scenes.items():
            scene.key = f"vibey-{name}"
            if name.startswith(("icon", "android")):
                scene.title = "krypton"  # the app icons are the apps', and the apps are krypton
        return scenes

    #: Scenes that also ship animated: the electrons orbit, and rest under reduced motion.
    ANIMATED = (
        "mark",
        "mark-light",
        "atom",
        "atom-light",
        "logo",
        "logo-light",
        "wordmark",
        "wordmark-light",
        "krypton",
        "krypton-light",
        "krypton-logo",
        "krypton-logo-light",
    )

    def outputs(self) -> dict[Path, bytes]:
        scenes = self.scenes()
        out = {self._root / f"{name}.svg": scene.svg().encode() for name, scene in scenes.items()}
        # The editor's activity-bar glyph: 24 units, one colour, and that colour is the theme's.
        glyph = Scene(
            24, 24, self._identity.atom((12, 12), 10.6, detail="small", mono=(0, 0, 0, 1))
        )
        glyph.key = "vibey-glyph"
        out[Path("clients/vscode/media/vibey.svg")] = (
            glyph.svg().replace("#000000", "currentColor").encode()
        )
        for name in self.ANIMATED:
            svg = scenes[name].svg(orbit_seconds=self._orbit_seconds)
            out[self._root / f"{name}-animated.svg"] = svg.encode()
        return out

    def rasters(self) -> dict[Path, tuple[str, int, int, bool]]:
        """Every PNG this design ships, and the scene and size it is drawn from."""
        out: dict[Path, tuple[str, int, int, bool]] = {}
        base = Path("design/dist/icons")
        for n in ICON_SIZES_HICOLOR:
            scene = _icon_for(n)
            out[base / f"hicolor/{n}x{n}/apps/vibey.png"] = (scene, n, n, False)
        for n, scale in ICONSET:
            px = n * scale
            name = f"icon_{n}x{n}{'@2x' if scale == 2 else ''}.png"
            out[base / f"macos/vibey.iconset/{name}"] = (
                _icon_for(px),
                px,
                px,
                False,
            )
        out[base / "ios/AppIcon-1024.png"] = ("icon", 1024, 1024, True)
        out[base / "android/ic_launcher_foreground.png"] = ("android-foreground", 432, 432, False)
        out[base / "android/ic_launcher_background.png"] = ("android-background", 432, 432, True)
        out[base / "android/ic_launcher_legacy-512.png"] = ("icon", 512, 512, False)
        out[base / "web/favicon-16.png"] = ("icon-tiny", 16, 16, False)
        out[base / "web/favicon-32.png"] = (_icon_for(32), 32, 32, False)
        out[base / "web/apple-touch-icon.png"] = ("icon", 180, 180, True)
        out[base / "web/icon-192.png"] = ("icon", 192, 192, False)
        out[base / "web/icon-512.png"] = ("icon", 512, 512, False)
        out[base / "web/social-preview.png"] = ("social", 1200, 630, True)
        return out
