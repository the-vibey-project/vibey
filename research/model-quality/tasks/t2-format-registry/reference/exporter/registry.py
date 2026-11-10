from collections.abc import Callable

from exporter.render import Row, render_csv, render_json, render_markdown

Renderer = Callable[[list[Row]], str]


class FormatRegistry:
    def __init__(self) -> None:
        self._renderers: dict[str, Renderer] = {}

    def register(self, name: str, renderer: Renderer, replace: bool = False) -> None:
        key = name.lower()
        if key in self._renderers and not replace:
            raise ValueError(f"format already registered: {key}")
        self._renderers[key] = renderer

    def get(self, name: str) -> Renderer:
        return self._renderers[name.lower()]

    def names(self) -> list[str]:
        return sorted(self._renderers)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name.lower() in self._renderers


def default_registry() -> FormatRegistry:
    registry = FormatRegistry()
    registry.register("json", render_json)
    registry.register("csv", render_csv)
    registry.register("md", render_markdown)
    return registry
