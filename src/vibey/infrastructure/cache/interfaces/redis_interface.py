# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Redis cache seam.

Mirrors `vibey/infrastructure/cache/redis.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.cache import CachePort


@runtime_checkable
class RedisCacheAdapterInterface(CachePort, Protocol):
    """The self-hosted Redis implementation of the Cache port."""
