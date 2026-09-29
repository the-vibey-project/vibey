# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Repository-profile configuration stays portable and refuses invalid metadata."""

from pathlib import Path

import pytest

from vibey_gh import install
from vibey_gh.config import GhConfig, RepositoryProfileConfig, RulesetsConfig, load_config


def test_repository_profile_loads_from_toml(tmp_path: Path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[repository_profile]\nenabled=false\ndescription="A useful project"\n'
        'topics=["python", "automation"]\n'
    )
    assert load_config(tmp_path).repository_profile == RepositoryProfileConfig(
        enabled=False,
        description="A useful project",
        topics=("python", "automation"),
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"description": "x" * 351}, "at most 350"),
        ({"topics": ("",)}, "non-empty"),
        ({"topics": ("same", "same")}, "unique"),
        ({"topics": tuple(f"topic-{index}" for index in range(21))}, "at most 20"),
        ({"topics": ("Has Space",)}, "lowercase"),
    ],
)
def test_repository_profile_rejects_invalid_metadata(kwargs, message):
    with pytest.raises(ValueError, match=message):
        RepositoryProfileConfig(**kwargs)


def test_repository_profile_workflow_renders_disabled_and_json_safe(tmp_path: Path):
    cfg = GhConfig(
        root=tmp_path,
        repository_profile=RepositoryProfileConfig(
            enabled=False,
            description='Quotes "stay" safe',
            topics=("python", "github-actions"),
        ),
    )
    rendered = install.render_workflow(install.WORKFLOWS / "repository-profile.yml", cfg)
    assert "false &&" in rendered
    assert 'CONFIG_DESCRIPTION: "Quotes \\"stay\\" safe"' in rendered
    assert '\'\u007b"names":\u005b"python","github-actions"\u005d\u007d\'' in rendered
    assert '"delete_branch_on_merge":false' in rendered
    assert '"vulnerability_alerts":true' in rendered


def test_repository_profile_workflow_renders_rulesets_disabled(tmp_path: Path):
    cfg = GhConfig(root=tmp_path, rulesets=RulesetsConfig(enabled=False))
    rendered = install.render_workflow(install.WORKFLOWS / "repository-profile.yml", cfg)
    assert "if: false" in rendered
    assert "if: true" not in rendered


def test_repository_profile_workflow_renders_rulesets_enabled_by_default(tmp_path: Path):
    cfg = GhConfig(root=tmp_path)
    rendered = install.render_workflow(install.WORKFLOWS / "repository-profile.yml", cfg)
    assert "if: true" in rendered
    assert "vibey-gh rulesets" in rendered


# ------------------------------------------------------------ the squash commit's message


def test_the_squash_message_is_not_managed_unless_declared(tmp_path: Path):
    """An upgrade must not change an adopter's merges: undeclared, nothing is sent, and
    nothing is verified, so the forge's own default stands."""
    rendered = install.render_workflow(
        install.WORKFLOWS / "repository-profile.yml", GhConfig(root=tmp_path)
    )
    assert "squash_merge_commit" not in rendered


def test_a_declared_squash_message_is_sent_and_verified(tmp_path: Path):
    (tmp_path / ".vibey-gh.toml").write_text(
        '[repository_profile]\nsquash_merge_commit_title = "PR_TITLE"\n'
        'squash_merge_commit_message = "PR_BODY"\n',
        encoding="utf-8",
    )
    cfg = load_config(tmp_path)
    assert cfg.repository_profile.squash_merge_commit_title == "PR_TITLE"
    rendered = install.render_workflow(install.WORKFLOWS / "repository-profile.yml", cfg)
    pair = '"squash_merge_commit_title":"PR_TITLE","squash_merge_commit_message":"PR_BODY"'
    # Twice: once in the PATCH the reconcile sends, once in what the verify step expects.
    assert rendered.count(pair) == 2


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"squash_merge_commit_title": "TITLE", "squash_merge_commit_message": "PR_BODY"},
            "squash_merge_commit_title must be one of",
        ),
        (
            {"squash_merge_commit_title": "PR_TITLE", "squash_merge_commit_message": "BODY"},
            "squash_merge_commit_message must be one of",
        ),
        ({"squash_merge_commit_title": "PR_TITLE"}, "together or not at all"),
        ({"squash_merge_commit_message": "PR_BODY"}, "together or not at all"),
        (
            {
                "squash_merge_commit_title": "COMMIT_OR_PR_TITLE",
                "squash_merge_commit_message": "PR_BODY",
            },
            "only valid with",
        ),
    ],
)
def test_a_squash_message_the_forge_would_refuse_is_refused_at_load(kwargs, message):
    with pytest.raises(ValueError, match=message):
        RepositoryProfileConfig(**kwargs)


def test_githubs_own_default_pairing_is_still_declarable():
    RepositoryProfileConfig(
        squash_merge_commit_title="COMMIT_OR_PR_TITLE",
        squash_merge_commit_message="COMMIT_MESSAGES",
    )
