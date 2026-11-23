# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Shared fixtures for the capability tests."""

from __future__ import annotations

import pytest
from fakes import RecordingReader


@pytest.fixture
def reader() -> RecordingReader:
    return RecordingReader()
