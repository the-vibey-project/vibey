# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory fakes for qwenloop's declared seams, shared by the tests (no outside service)."""

from qwenloop.application.interfaces import OllamaProbeInterface


class FakeOllamaProbe:
    """An in-memory stand-in for the local-Ollama probe: answers as told, counts asks."""

    def __init__(self, available: bool = False) -> None:
        self.answer = available
        self.asked = 0

    def available(self) -> bool:
        self.asked += 1
        return self.answer


assert isinstance(FakeOllamaProbe(), OllamaProbeInterface)
