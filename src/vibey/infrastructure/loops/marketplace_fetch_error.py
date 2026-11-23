# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A marketplace that could not be fetched, copied or checked; nothing was locked (SP-LOOPS Task 7).

The message may quote what a remote said (git's last words), so whoever prints it to a terminal
cleans it first (`SafeText`)."""


class MarketplaceFetchError(Exception):
    """Raised by the fetchers and `MarketplaceStore.update`; the old copy and lock are kept."""
