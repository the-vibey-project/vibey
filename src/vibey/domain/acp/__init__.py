# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Agent Client Protocol's pure half: protocol vocabulary, `[acp]` settings, the observe
and drive modes, and the per-session turn state machine (SP-ACP, ADR-0100).

Pure: no I/O, no async, no clock, no network. The official SDK is a dev dependency used only
by the tests that validate these shapes."""
