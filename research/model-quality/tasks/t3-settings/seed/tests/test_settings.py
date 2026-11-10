from settings import load_settings


def test_defaults() -> None:
    cfg = load_settings()
    assert cfg["theme"] == "light"
    assert cfg["editor"] == {"tabs": 4, "wrap": True}


def test_an_override_does_not_leak_into_later_loads() -> None:
    first = load_settings({"editor": {"tabs": 2}})
    assert first["editor"] == {"tabs": 2, "wrap": True}
    assert load_settings()["editor"]["tabs"] == 4
