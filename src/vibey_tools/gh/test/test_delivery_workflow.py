# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

import yaml


def test_delivery_estimate_publish_is_limited_to_trusted_events() -> None:
    root = Path(__file__).resolve().parents[4]
    workflow = yaml.safe_load(
        (root / ".github/workflows/delivery-estimate.yml").read_text(encoding="utf-8")
    )
    publish = workflow["jobs"]["publish"]
    condition = publish["if"]
    assert "github.event_name == 'push'" in condition
    assert "github.event_name == 'schedule'" in condition
    assert "github.event_name == 'workflow_dispatch'" in condition
    assert "github.event_name == 'issues'" not in condition
    assert "github.event_name == 'pull_request'" not in condition
