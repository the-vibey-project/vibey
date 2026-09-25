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
    clip: tuple[float, float, float, float, float] | None = (
        None  # glow clip: rounded rect (x, y, w, h, r)
    )

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

    # -- SVG ---------------------------------------------------------------------------------

    def svg(self) -> str:
        defs: list[str] = []
        body: list[str] = []
        for n, shape in enumerate(self.shapes):
            fill = self._svg_paint(shape, n, defs)
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
                f'<radialGradient id="g{n}" cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(shape.radius)}" '
                f'gradientUnits="userSpaceOnUse">{stops}</radialGradient>\n'
            )
            return f"url(#g{n})"
        if isinstance(shape.paint, Linear):
            p = shape.paint
            last = len(p.stops) - 1
            stops = ""
            for i, c in enumerate(p.stops):
                hx, a = self._svg_colour(c)
                stops += f'<stop offset="{_num(round(i / last, 4))}" stop-color="{hx}" stop-opacity="{a}"/>'
            defs.append(
                f'<linearGradient id="g{n}" x1="{_num(p.start[0])}" y1="{_num(p.start[1])}" '
                f'x2="{_num(p.end[0])}" y2="{_num(p.end[1])}" gradientUnits="userSpaceOnUse">{stops}</linearGradient>\n'
            )
            return f"url(#g{n})"
        hx, a = self._svg_colour(shape.paint)
        return hx if a == "1" else f"{hx};{a}"

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


class Identity:
    """Builds every identity scene from the token set."""

    def __init__(self, tokens: TokenSetInterface) -> None:
        t = tokens.hex
        self.night = _rgba(t("theme.dark.bg.canvas"))
        self.night_raised = _rgba(t("theme.dark.bg.overlay"))
        self.violet = _rgba(t("theme.dark.accent.hover"))
        self.violet_deep = _rgba(t("theme.light.accent.default"))
        self.cyan = _rgba(t("theme.dark.status.info"))
        self.mint = _rgba(t("theme.dark.status.success"))
        self.ink = _rgba(t("theme.dark.text.primary"))
        self.print_ink = _rgba(t("print.vibeyink"))
        self.glow_violet = _rgba(t("color.violet.425"), 0.62)
        self.glow_cyan = _rgba(t("theme.dark.status.info"), 0.34)

    # The mark on a 24-unit grid (the extension glyph's own), placed in a 1024 master.
    def _mark(
        self, cx: float, cy: float, k: float, *, orbit: bool, mono: RGBA | None = None
    ) -> list[Shape]:
        def p(x: float, y: float) -> Point:
            return (cx + (x - 12) * k, cy + (y - 12.6) * k)

        stroke = 2.35 * k
        v_paint: Paint = mono or Linear(p(4, 5), p(20, 17), (self.violet, self.cyan))
        shapes: list[Shape] = []
        if orbit and mono is None:
            shapes.append(Shape("glow", _rgba("#75f0c2", 0.55), (p(12, 19),), radius=4.2 * k))
        shapes += [
            Shape("capsule", v_paint, (p(4, 5), p(12, 19)), width=stroke),
            Shape("capsule", v_paint, (p(20, 5), p(12, 19)), width=stroke),
            Shape("capsule", mono or self.ink, (p(8.9, 5), p(15.1, 5)), width=stroke * 0.82),
        ]
        if orbit:
            shapes.append(
                Shape(
                    "ellipse-ring",
                    mono or (self.cyan[0], self.cyan[1], self.cyan[2], 0.78),
                    (p(12, 19),),
                    width=0.42 * k,
                    extra=(4.3 * k, 1.55 * k, math.radians(-16)),
                )
            )
        shapes.append(Shape("circle", mono or self.mint, (p(12, 19),), radius=1.55 * k))
        return shapes

    def _tile(self, size: float, radius: float) -> list[Shape]:
        return [
            Shape(
                "rect",
                Linear((0, 0), (size, size), (self.night_raised, self.night)),
                ((0, 0),),
                extra=(size, size, radius),
            ),
            Shape(
                "glow",
                self.glow_violet,
                ((size * 0.28, size * 0.22),),
                radius=size * 0.62,
                clip=None,
            ),
            Shape(
                "glow", self.glow_cyan, ((size * 0.86, size * 0.9),), radius=size * 0.5, clip=None
            ),
        ]

    def icon(self, *, orbit: bool = True, radius: float = 228) -> Scene:
        """The app icon master: the mark on the night tile, 1024 units square."""
        tile = self._tile(UNITS, radius)
        # Glows must stay inside the rounded tile: they are clipped by drawing them as
        # separate shapes whose coverage is the tile's (see `_clip_glows`).
        return Scene(
            UNITS, UNITS, _clip_glows(tile, UNITS, radius) + self._mark(512, 520, 31, orbit=orbit)
        )

    def mark(self, *, mono: RGBA | None = None) -> Scene:
        """The mark alone on transparent ground (24-unit glyph at 1024)."""
        return Scene(UNITS, UNITS, self._mark(512, 512, 40, orbit=True, mono=mono))

    def adaptive_foreground(self) -> Scene:
        """Android adaptive foreground: the mark inside the 66/108 safe zone."""
        return Scene(UNITS, UNITS, self._mark(512, 512, 22, orbit=True))

    def adaptive_background(self) -> Scene:
        return Scene(UNITS, UNITS, _clip_glows(self._tile(UNITS, 0), UNITS, 0))

    def wordmark(self, *, mono: RGBA | None = None, k: float = 20.0) -> Scene:
        """`vibey` in the mark's own monoline stroke: v, i, b, e, y from lines, circles and arcs."""
        w = 2.35 * k
        pad = w
        ox, oy = pad, pad + 6 * k  # x-height top at oy; baseline at oy + 10k

        def p(x: float, y: float) -> Point:
            return (ox + x * k, oy + y * k)

        paint: Paint = mono or Linear(p(0, 0), p(46, 10), (self.violet, self.cyan, self.mint))
        shapes = [
            Shape("capsule", paint, (p(0, 0), p(4, 10)), width=w),
            Shape("capsule", paint, (p(8, 0), p(4, 10)), width=w),
            Shape("capsule", paint, (p(11.6, 0), p(11.6, 10)), width=w),
            Shape("circle", mono or self.mint, (p(11.6, -3.6),), radius=w * 0.62),
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
        return Scene(
            47.4 * k + 2 * pad, 22 * k + 2 * pad + 5.5 * k - 6 * k + 6 * k, shapes, title="vibey"
        )

    def lockup(self) -> Scene:
        """Mark tile and wordmark side by side: the logo."""
        tile_size = 520.0
        tile = self._tile(tile_size, tile_size * 0.223)
        mark = self._mark(tile_size / 2, tile_size / 2, 17.5, orbit=True)
        word = self.wordmark(k=17.0)
        dx = tile_size + 70
        dy = (tile_size - word.height) / 2 + 30
        moved = [_translate(s, dx, dy) for s in word.shapes]
        return Scene(
            dx + word.width,
            tile_size,
            _clip_glows(tile, tile_size, tile_size * 0.223) + mark + moved,
        )

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
        tx, ty = 120.0, (h - size) / 2
        tile = [
            _translate(s, tx, ty)
            for s in _clip_glows(self._tile(size, size * 0.223), size, size * 0.223)
        ]
        mark = self._mark(tx + size / 2, ty + size / 2, 11.0, orbit=True)
        word = self.wordmark(k=11.6)
        moved = [_translate(s, 530, (h - word.height) / 2 + 20) for s in word.shapes]
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
    return Shape(
        shape.kind,
        paint,
        tuple((x + dx, y + dy) for x, y in shape.points),
        shape.radius,
        shape.width,
        shape.extra,
        clip,
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


class IdentityEmitter(EmitterInterface):
    """SVG masters (cheap, always checked) and the declared raster set."""

    def __init__(self, tokens: TokenSetInterface, root: str = "design/identity") -> None:
        self._identity = Identity(tokens)
        self._root = Path(root)

    def scenes(self) -> dict[str, Scene]:
        i = self._identity
        return {
            "mark": i.mark(),
            "mark-mono": i.mark(mono=(0, 0, 0, 1)),
            "wordmark": i.wordmark(),
            "wordmark-ink": i.wordmark(mono=i.print_ink),
            "logo": i.lockup(),
            "icon": i.icon(),
            "icon-small": i.icon(orbit=False),
            "android-foreground": i.adaptive_foreground(),
            "android-background": i.adaptive_background(),
            "social": i.social(),
        }

    def outputs(self) -> dict[Path, bytes]:
        return {
            self._root / f"{name}.svg": scene.svg().encode()
            for name, scene in self.scenes().items()
        }

    def rasters(self) -> dict[Path, tuple[str, int, int, bool]]:
        """Every PNG this design ships, and the scene and size it is drawn from."""
        out: dict[Path, tuple[str, int, int, bool]] = {}
        base = Path("design/dist/icons")
        for n in ICON_SIZES_HICOLOR:
            scene = "icon-small" if n <= 32 else "icon"
            out[base / f"hicolor/{n}x{n}/apps/vibey.png"] = (scene, n, n, False)
        for n, scale in ICONSET:
            px = n * scale
            name = f"icon_{n}x{n}{'@2x' if scale == 2 else ''}.png"
            out[base / f"macos/vibey.iconset/{name}"] = (
                "icon-small" if px <= 32 else "icon",
                px,
                px,
                False,
            )
        out[base / "ios/AppIcon-1024.png"] = ("icon", 1024, 1024, True)
        out[base / "android/ic_launcher_foreground.png"] = ("android-foreground", 432, 432, False)
        out[base / "android/ic_launcher_background.png"] = ("android-background", 432, 432, True)
        out[base / "android/ic_launcher_legacy-512.png"] = ("icon", 512, 512, False)
        out[base / "web/favicon-16.png"] = ("icon-small", 16, 16, False)
        out[base / "web/favicon-32.png"] = ("icon-small", 32, 32, False)
        out[base / "web/apple-touch-icon.png"] = ("icon", 180, 180, True)
        out[base / "web/icon-192.png"] = ("icon", 192, 192, False)
        out[base / "web/icon-512.png"] = ("icon", 512, 512, False)
        out[base / "web/social-preview.png"] = ("social", 1200, 630, True)
        return out
