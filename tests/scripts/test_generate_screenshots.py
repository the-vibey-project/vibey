# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the krypton screenshot generation automation."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from scripts.generate_screenshots import ScreenshotGenerator, main
from scripts.interfaces.screenshot_generator_interface import (
    ScreenshotGeneratorInterface,
)


def test_generator_implements_interface() -> None:
    generator = ScreenshotGenerator(chrome_bin="/usr/bin/chrome")
    assert isinstance(generator, ScreenshotGeneratorInterface)


def test_find_chrome_returns_candidate() -> None:
    with patch("os.path.exists", return_value=True), patch("os.access", return_value=True):
        generator = ScreenshotGenerator()
        assert generator._chrome is not None


def test_build_html_generates_valid_markup() -> None:
    generator = ScreenshotGenerator(chrome_bin="/usr/bin/chrome")
    for app_id, screen_id in [
        ("mobile", "chat"),
        ("mobile", "add-session"),
        ("mobile", "usage"),
        ("mobile", "settings"),
        ("mobile", "home"),
        ("mobile", "gates"),
        ("mobile", "pair"),
        ("desktop", "chat"),
        ("desktop", "inspector"),
        ("desktop", "settings"),
        ("vscode", "panel"),
        ("vscode", "composer"),
        ("unknown", "fallback"),
    ]:
        html = generator._build_html(app_id, screen_id, 800, 600)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html
        assert "width: 800px" in html
        assert "height: 600px" in html


def test_render_screen_calls_chrome(tmp_path: Path) -> None:
    generator = ScreenshotGenerator(chrome_bin="/usr/bin/chrome")
    out_file = tmp_path / "test.png"

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        generator._render_screen("mobile", "chat", 400, 800, out_file)
        assert mock_run.called
        args = mock_run.call_args[0][0]
        assert args[0] == "/usr/bin/chrome"
        assert "--headless" in args
        assert "--window-size=400,800" in args
        assert f"--screenshot={out_file.resolve()}" in args


def test_generate_screen(tmp_path: Path) -> None:
    generator = ScreenshotGenerator(chrome_bin="/usr/bin/chrome")
    out_file = tmp_path / "screen.png"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = generator.generate_screen("mobile", "chat", out_file)
        assert res == out_file
        assert mock_run.called


def test_generate_all(tmp_path: Path) -> None:
    generator = ScreenshotGenerator(chrome_bin="/usr/bin/chrome")
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        generated = generator.generate_all(tmp_path)
        assert len(generated) == 12
        assert all(p.parent == tmp_path for p in generated)


def test_main(tmp_path: Path) -> None:
    with (
        patch("scripts.generate_screenshots.ScreenshotGenerator") as mock_cls,
        patch("shutil.copy2") as mock_copy,
    ):
        mock_instance = MagicMock()
        mock_instance.generate_all.return_value = [tmp_path / "01.png", tmp_path / "02.png"]
        mock_cls.return_value = mock_instance
        main()
        assert mock_instance.generate_all.called
        assert mock_copy.call_count == 2
