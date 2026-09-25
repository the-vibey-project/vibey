# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads `design/tokens/*.tokens.json` (DTCG 2025.10) and measures the colour pairs it promises.

Stdlib only: the token graph is small, and the family ships nothing that reads DTCG, so a
resolver of a hundred lines beats a Node toolchain (Style Dictionary) that nothing else in the
repository needs. The references (`{color.violet.400}`) are followed recursively, inside
composite values too, and a cycle or a dangling reference fails loudly with its path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from interfaces.design_interface import (
    ContrastAuditInterface,
    ContrastResult,
    Token,
    TokenSetInterface,
)

REFERENCE = re.compile(r"^\{([^{}]+)\}$")
THEMES: tuple[str, ...] = ("dark", "light")


class TokenError(ValueError):
    """The token source is malformed; the message names the token and what is wrong."""


class TokenSet(TokenSetInterface):
    """Every token under a directory of `*.tokens.json` files, references resolved."""

    def __init__(self, directory: Path) -> None:
        self._raw: dict[str, tuple[str, Any, str]] = {}
        for path in sorted(directory.glob("*.tokens.json")):
            self._walk(json.loads(path.read_text(encoding="utf-8")), [], None, path.name)
        if not self._raw:
            raise TokenError(f"no *.tokens.json files under {directory}")
        self._resolved: dict[str, Token] = {}
        for name in self._raw:
            self._resolved[name] = self._resolve(name, ())

    def _walk(self, node: dict[str, Any], trail: list[str], kind: str | None, source: str) -> None:
        kind = node.get("$type", kind)
        if "$value" in node:
            name = ".".join(trail)
            if kind is None:
                raise TokenError(f"{source}: {name} has no $type, on itself or a parent group")
            if name in self._raw:
                raise TokenError(f"{source}: {name} is defined twice")
            self._raw[name] = (kind, node["$value"], node.get("$description", ""))
            return
        for key, child in node.items():
            if key.startswith("$"):
                continue
            if not isinstance(child, dict):
                raise TokenError(f"{source}: {'.'.join([*trail, key])} is neither token nor group")
            self._walk(child, [*trail, key], kind, source)

    def _resolve(self, name: str, seen: tuple[str, ...]) -> Token:
        if name in self._resolved:
            return self._resolved[name]
        if name in seen:
            raise TokenError(f"reference cycle: {' -> '.join((*seen, name))}")
        if name not in self._raw:
            raise TokenError(f"{seen[-1] if seen else '?'} references {name}, which does not exist")
        kind, value, description = self._raw[name]
        return Token(name, kind, self._deep(value, (*seen, name)), description)

    def _deep(self, value: Any, seen: tuple[str, ...]) -> Any:
        if isinstance(value, str):
            match = REFERENCE.match(value)
            return self._resolve(match.group(1), seen).value if match else value
        if isinstance(value, list):
            return [self._deep(item, seen) for item in value]
        if isinstance(value, dict):
            return {key: self._deep(item, seen) for key, item in value.items()}
        return value

    def tokens(self) -> tuple[Token, ...]:
        return tuple(self._resolved.values())

    def get(self, path: str) -> Token:
        try:
            return self._resolved[path]
        except KeyError:
            raise KeyError(f"no design token named {path}") from None

    def hex(self, path: str) -> str:
        token = self.get(path)
        if token.type != "color":
            raise TokenError(f"{path} is a {token.type}, not a color")
        return Colour.hex_of(token.value)

    def group(self, prefix: str) -> tuple[Token, ...]:
        return tuple(t for t in self._resolved.values() if t.path.startswith(prefix + "."))


class Colour:
    """A DTCG sRGB colour value, and the WCAG 2.2 arithmetic on it."""

    @staticmethod
    def hex_of(value: dict[str, Any]) -> str:
        """`#rrggbb`, or `#rrggbbaa` when the colour carries an alpha below one."""
        if value.get("colorSpace") != "srgb":
            raise TokenError(f"only srgb colours are supported, got {value.get('colorSpace')}")
        rgb = "".join(f"{round(c * 255):02x}" for c in value["components"])
        stated = str(value.get("hex", "")).lower()
        if stated and stated != f"#{rgb}":
            raise TokenError(f"hex {stated} disagrees with components #{rgb}")
        alpha = float(value.get("alpha", 1))
        return f"#{rgb}" if alpha >= 1 else f"#{rgb}{round(alpha * 255):02x}"

    @staticmethod
    def rgb(hex_value: str) -> tuple[int, int, int]:
        """The 8-bit channels of `#rrggbb`."""
        return int(hex_value[1:3], 16), int(hex_value[3:5], 16), int(hex_value[5:7], 16)

    @staticmethod
    def luminance(hex_value: str) -> float:
        """WCAG relative luminance."""
        channels = []
        for c in Colour.rgb(hex_value):
            s = c / 255
            channels.append(s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    @staticmethod
    def contrast(foreground: str, background: str) -> float:
        """WCAG 2.2 contrast ratio, 1.0 to 21.0."""
        a, b = sorted((Colour.luminance(foreground), Colour.luminance(background)), reverse=True)
        return (a + 0.05) / (b + 0.05)


class ContrastAudit(ContrastAuditInterface):
    """Every pair `design/contrast.json` declares, measured in every theme."""

    def __init__(self, tokens: TokenSetInterface, rules: Path) -> None:
        self._tokens = tokens
        self._spec = json.loads(rules.read_text(encoding="utf-8"))

    def results(self) -> tuple[ContrastResult, ...]:
        out: list[ContrastResult] = []
        for theme in self._spec["themes"]:
            for rule in self._spec["rules"]:
                for fg in rule["foreground"]:
                    for bg in rule["background"]:
                        fg_hex = self._tokens.hex(f"theme.{theme}.{fg}")
                        bg_hex = self._tokens.hex(f"theme.{theme}.{bg}")
                        if len(fg_hex) != 7 or len(bg_hex) != 7:
                            raise TokenError(f"{theme}.{fg} on {bg}: contrast needs opaque colours")
                        out.append(
                            ContrastResult(
                                theme=theme,
                                rule=rule["name"],
                                foreground=fg,
                                background=bg,
                                foreground_hex=fg_hex,
                                background_hex=bg_hex,
                                ratio=Colour.contrast(fg_hex, bg_hex),
                                minimum=float(rule["minimum"]),
                            )
                        )
        return tuple(out)
