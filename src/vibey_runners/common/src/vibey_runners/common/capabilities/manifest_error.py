# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A marketplace that cannot be read safely: refused whole, so no part of it is used."""


class ManifestError(ValueError):
    """Raised by `MarketplaceManifest.read`; the message names the marketplace and the entry."""
