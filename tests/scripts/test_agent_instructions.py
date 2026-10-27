# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/agent_instructions.py`: one source, three doors, and a check that says when one drifted (#1688).

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from scripts import agent_instructions as ai
from scripts.interfaces.agent_instructions_interface import AgentInstructionsInterface

BLOCK = "<!-- vibey:begin -->\nprovisioned by vibey\n<!-- vibey:end -->"

SOURCE: dict[str, Any] = {
    "agents": {
        "claude": {"file": "C.md", "title": "C.md", "edition": "full"},
        "gem": {"file": "G.md", "title": "G.md", "edition": "brief"},
    },
    "render": {"banner": "<!-- generated -->"},
    "intro": {"full": "The long intro.", "brief": "Short intro."},
    "section": [
        {
            "id": "rules",
            "heading": "Rules",
            "heading_brief": "Rules (short)",
            "item": [
                {"id": "a", "full": "- **A** in full", "brief": "- A, briefly"},
                {"id": "b", "full": "- **B** only full"},
                {"id": "c", "full": "- **C** claude only", "agents": ["claude"]},
                {"id": "d", "full": "- **D** not in brief", "brief": "", "note": "covered by A"},
            ],
        },
        {"id": "map", "heading": "Map", "full": "The whole map.", "brief": "A map."},
        {"id": "plain", "heading": "Plain", "full": "No brief here."},
    ],
    "appendix": {"id": "sd", "agents": ["claude"], "full": "## Appendix\n\nverbatim"},
}


def build(tmp_path: Path, source: dict[str, Any] | None = None) -> ai.AgentInstructions:
    return ai.AgentInstructions(source or SOURCE, tmp_path, "src.toml")


def test_it_honours_its_interface(tmp_path: Path) -> None:
    assert isinstance(build(tmp_path), AgentInstructionsInterface)
    assert build(tmp_path).agents() == ["claude", "gem"]


def test_the_full_edition_takes_full_text_in_the_sources_order(tmp_path: Path) -> None:
    assert build(tmp_path).render("claude") == (
        "# C.md\n\n<!-- generated -->\n\nThe long intro.\n\n"
        "## Rules\n\n- **A** in full\n- **B** only full\n- **C** claude only\n- **D** not in brief\n\n"
        "## Map\n\nThe whole map.\n\n## Plain\n\nNo brief here.\n\n## Appendix\n\nverbatim\n"
    )


def test_the_brief_edition_condenses_drops_and_falls_back_to_full(tmp_path: Path) -> None:
    text = build(tmp_path).render("gem")
    assert text == (
        "# G.md\n\n<!-- generated -->\n\nShort intro.\n\n"
        "## Rules (short)\n\n- A, briefly\n- **B** only full\n\n"
        "## Map\n\nA map.\n\n## Plain\n\nNo brief here.\n"
    )
    assert "claude only" not in text and "not in brief" not in text and "verbatim" not in text


def test_the_provisioners_block_is_carried_over_from_the_file_on_disk(tmp_path: Path) -> None:
    (tmp_path / "C.md").write_text(
        "# old\n\nhand text\n\n" + BLOCK + "\n\ntrailing\n", encoding="utf-8"
    )
    text = build(tmp_path).render("claude")
    assert BLOCK in text
    assert text.index("No brief here.") < text.index(BLOCK) < text.index("## Appendix")
    assert "hand text" not in text and "trailing" not in text


@pytest.mark.parametrize(
    "disk",
    [None, "no markers here\n", "<!-- vibey:end -->\n<!-- vibey:begin -->\n"],
)
def test_a_file_without_a_usable_block_gets_none(tmp_path: Path, disk: str | None) -> None:
    if disk is not None:
        (tmp_path / "C.md").write_text(disk, encoding="utf-8")
    assert "vibey:begin" not in build(tmp_path).render("claude")


def test_differing_names_each_file_that_is_not_what_the_source_makes(tmp_path: Path) -> None:
    instructions = build(tmp_path)
    assert len(instructions.differing()) == 2  # neither file exists yet
    instructions.write()
    assert instructions.differing() == []
    (tmp_path / "G.md").write_text("# G.md\n\nhand-edited\n", encoding="utf-8")
    (found,) = instructions.differing()
    assert found.startswith("G.md is not what src.toml makes of it") and "first difference" in found


def test_write_reports_only_what_it_changed(tmp_path: Path) -> None:
    instructions = build(tmp_path)
    assert instructions.write() == ["C.md", "G.md"]
    assert instructions.write() == []
    (tmp_path / "C.md").write_text("changed\n", encoding="utf-8")
    assert instructions.write() == ["C.md"]


def test_a_sound_source_has_no_problems(tmp_path: Path) -> None:
    assert build(tmp_path).problems() == []


def broken(**edit: Any) -> dict[str, Any]:
    source = copy.deepcopy(SOURCE)
    for key, value in edit.items():
        source[key] = value
    return source


@pytest.mark.parametrize(
    "mutate, fragment",
    [
        (lambda s: s["agents"]["claude"].update(edition="long"), "edition must be one of"),
        (lambda s: s["agents"]["claude"].pop("title"), "needs a file and a title"),
        (lambda s: s["section"][1].update(id="rules"), "empty or used twice"),
        (lambda s: s["section"][1].update(id=""), "empty or used twice"),
        (lambda s: s["section"][1].pop("heading"), "has no heading"),
        (lambda s: s["section"][1].update(full="  "), "neither a body nor items"),
        (lambda s: s["section"][0]["item"][1].update(id="a"), "item id 'a' in section rules"),
        (lambda s: s["section"][0]["item"][1].update(full=""), "has no full text"),
        (lambda s: s["section"][0]["item"][3].pop("note"), "without a note"),
        (lambda s: s["section"][0]["item"][2].update(agents=["nobody"]), "unknown agent 'nobody'"),
        (lambda s: s["appendix"].update(agents=["ghost"]), "the appendix names an unknown agent"),
    ],
)
def test_a_broken_source_is_reported_not_rendered(
    tmp_path: Path, mutate: Any, fragment: str
) -> None:
    source = copy.deepcopy(SOURCE)
    mutate(source)
    assert any(fragment in problem for problem in build(tmp_path, source).problems())


def test_load_reads_the_declared_source(tmp_path: Path) -> None:
    (tmp_path / "src.toml").write_text(
        '[agents.x]\nfile = "X.md"\ntitle = "X"\nedition = "full"\n'
        '[render]\nbanner = "b"\n[intro]\nfull = "i"\n',
        encoding="utf-8",
    )
    config = tmp_path / "cfg.toml"
    config.write_text('[agent_instructions]\nsource = "src.toml"\n', encoding="utf-8")
    loaded = ai.AgentInstructions.load(config, tmp_path)
    assert loaded.agents() == ["x"] and loaded.render("x") == "# X\n\nb\n\ni\n"


def test_main_renders_then_checks_then_says_what_drifted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "src.toml").write_text(
        '[agents.x]\nfile = "X.md"\ntitle = "X"\nedition = "full"\n'
        '[render]\nbanner = "b"\n[intro]\nfull = "i"\n',
        encoding="utf-8",
    )
    config = tmp_path / "cfg.toml"
    config.write_text('[agent_instructions]\nsource = "src.toml"\n', encoding="utf-8")
    base = ["--root", str(tmp_path), "--config", str(config)]
    assert ai.main(["check", *base]) == 1
    assert "run `python scripts/agent_instructions.py render`" in capsys.readouterr().err
    assert ai.main(["render", *base]) == 0
    assert "rewrote: X.md" in capsys.readouterr().out
    assert ai.main(["render", *base]) == 0
    assert capsys.readouterr().out.strip() == "up to date"
    assert ai.main(["check", *base]) == 0
    (tmp_path / "src.toml").write_text(
        '[agents.x]\nfile = "X.md"\ntitle = "X"\nedition = "wide"\n'
        '[render]\nbanner = "b"\n[intro]\nfull = "i"\n',
        encoding="utf-8",
    )
    assert ai.main(["check", *base]) == 1
    assert "edition must be one of" in capsys.readouterr().err
