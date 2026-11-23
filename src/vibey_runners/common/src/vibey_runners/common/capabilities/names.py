# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one rule for a capability name: a marketplace, plugin, MCP server or skill.

A name later becomes a folder name and a lock key, so it is a plain identifier: letters, digits,
`.`, `_` and `-`, starting with a letter or digit (never `.`, `..` or an option), at most 128
characters. The bundle, the manifest reader and the skill index all hold names to this.
"""

import re
from typing import Final

NAME_PATTERN: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
"""Match with `fullmatch`."""
