from report import summary
from settings import DEFAULTS, load_settings


def test_nested_override_merges_keys() -> None:
    cfg = load_settings({"editor": {"tabs": 2}})
    assert cfg["editor"] == {"tabs": 2, "wrap": True}


def test_override_does_not_change_defaults_constant() -> None:
    load_settings({"editor": {"tabs": 8, "ruler": 80}})
    assert DEFAULTS["editor"] == {"tabs": 4, "wrap": True}


def test_later_loads_are_unaffected_by_an_override() -> None:
    load_settings({"editor": {"wrap": False}})
    assert load_settings()["editor"] == {"tabs": 4, "wrap": True}


def test_mutating_a_returned_list_does_not_leak() -> None:
    cfg = load_settings()
    cfg["plugins"].append("extra")
    assert load_settings()["plugins"] == ["core"]
    assert DEFAULTS["plugins"] == ["core"]


def test_mutating_a_returned_nested_dict_does_not_leak() -> None:
    cfg = load_settings()
    cfg["editor"]["tabs"] = 99
    assert load_settings()["editor"]["tabs"] == 4


def test_two_results_are_independent() -> None:
    a = load_settings()
    b = load_settings()
    a["editor"]["wrap"] = False
    a["plugins"].append("x")
    assert b["editor"]["wrap"] is True
    assert b["plugins"] == ["core"]


def test_top_level_override_replaces_scalar_and_list() -> None:
    cfg = load_settings({"theme": "dark", "plugins": ["a", "b"]})
    assert cfg["theme"] == "dark"
    assert cfg["plugins"] == ["a", "b"]


def test_unknown_key_is_added() -> None:
    assert load_settings({"lang": "en"})["lang"] == "en"


def test_summary_repeats_identically() -> None:
    assert summary({"editor": {"tabs": 2}}) == "theme=light tabs=2 plugins=core"
    assert summary() == "theme=light tabs=4 plugins=core"
    assert summary({"plugins": ["a", "b"]}) == "theme=light tabs=4 plugins=a,b"
