# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The wiring of `review.publish`: it exists to be handled, and has the time it needs."""

from datetime import timedelta

from vibey.bootstrap import lease_for_kind


def test_publishing_has_a_lease_longer_than_the_default_for_its_network_calls() -> None:
    assert lease_for_kind("review.publish") == timedelta(minutes=15)
    assert lease_for_kind("review.publish") > lease_for_kind("review.collect")
