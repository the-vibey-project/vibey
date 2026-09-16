# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Seams the domain layer declares. Interfaces declare; they never consume."""

from vibey.domain.interfaces.delivery_interface import (
    DeliveryCorrelationInterface,
    DeliveryIdInterface,
)

__all__ = ["DeliveryCorrelationInterface", "DeliveryIdInterface"]
