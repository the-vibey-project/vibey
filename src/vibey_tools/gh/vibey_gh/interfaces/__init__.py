# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seams of `vibey_gh` (vibey ADR-0016).

Interfaces declare; they never consume. A module here may import the standard library,
`vibey_gh.config` (data, not behaviour) and other interfaces — nothing else from this
tree. `.importlinter` enforces it.
"""

from __future__ import annotations

from vibey_gh.interfaces.book_interface import MainExtractorInterface
from vibey_gh.interfaces.chapter_sanitizer_interface import ChapterSanitizerInterface
from vibey_gh.interfaces.review_contract_interface import ReviewContractPort

__all__ = ["ChapterSanitizerInterface", "MainExtractorInterface", "ReviewContractPort"]
