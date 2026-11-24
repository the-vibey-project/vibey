# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams of the MCP client (ADR-0016). They may name the records their signatures carry,
never the classes that implement them: an import-linter contract in this package's
`pyproject.toml` forbids `stdio_transport`, `http_transport`, `http_opener`,
`mcp_transport_factory`, `mcp_session` and `mcp_session_pool` here."""
