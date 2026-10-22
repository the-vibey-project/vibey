import pathlib


def test_issue_label_correction_present():
    path = pathlib.Path("docs/plans/qwenstorm-3.0.0/issue-audit/updates/301.md")
    content = path.read_text(encoding="utf-8")
    assert "The issue label is corrected from `bug` to a documentation/enhancement label." in content
