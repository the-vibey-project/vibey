# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The declared seams of `vibey_gh` (vibey ADR-0016).

Interfaces declare; they never consume. A module here may import the standard library,
other interfaces, and the frozen data records a seam is stated in terms of — including
`vibey_gh.config` — nothing else from this tree, and nothing that is behaviour rather
than data. `.importlinter` enforces it.
"""
