# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A shared assertion for the ACP tests: a payload is exactly what the SDK puts on the wire.

The SDK's models accept snake_case field names and ignore unknown keys, so a plain
`model_validate` does not prove a payload carries the protocol's camelCase keys. A round trip
through the model, dumped by alias with unset members dropped, must equal the payload."""

from typing import Any

from pydantic import BaseModel


def assert_wire_exact(model_cls: type[BaseModel], payload: dict[str, Any]) -> None:
    dumped = model_cls.model_validate(payload).model_dump(by_alias=True, exclude_none=True)
    assert dumped == payload
