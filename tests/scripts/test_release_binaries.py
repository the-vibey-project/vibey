# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`scripts/release_binaries.py`: the catalogue, the plan, the drift check, the page, PyPI,
the collected files and the Flatpak manifest.

Each class is driven over a small declaration written into a temporary directory, so every
refusal it makes -- an undeclared job, a missing file, a digest PyPI does not record -- is
exercised without the repository's own configuration or the network.

Module-level test functions rather than a class with an interface beside it (ADR-0016):
pytest collects `test_*` functions, and the rule is about production code.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts import release_binaries as rb

ARCHES = """\
[minimum_specs.linux.arches.x86_64]
runner = "ubuntu-24.04"

[minimum_specs.linux.arches.aarch64]
runner = "ubuntu-24.04-arm"
"""

CONFIG = """\
[release_binaries]
workflow = "wf.yml"
downloads_page = "page.md"
gh_config = ".vibey-gh.toml"
linux_arches_source = "arches.toml"
linux_arches_table = "minimum_specs.linux.arches"
checksums_asset = "SHA256SUMS"
infrastructure_jobs = ["plan", "collect", "attach"]
release_wait_s = 60
poll_s = 5
pypi_wait_s = 10
pypi_json_url = "https://pypi.example/{project}/{version}/json"

[release_binaries.uis.desktop]
name = "krypton desktop"
summary = "desktop"
version_file = "meson.build"
version_pattern = "version:\\\\s*'([^']+)'"

[release_binaries.uis.app]
name = "krypton app"
summary = "app"
version_file = "app.json"
version_pattern = '"version":\\s*"([^"]+)"'

[[release_binaries.targets]]
id = "desktop-flatpak-{arch}"
ui = "desktop"
builder = "desktop-flatpak"
status = "build"
platform = "Linux"
per_linux_arch = true
assets = ["krypton-desktop-{version}-linux-{arch}.flatpak"]
signing = "unsigned"
install = "flatpak install krypton-desktop-{version}-linux-{arch}.flatpak"
note = "A bundle."
with = { module = "krypton-desktop" }

[[release_binaries.targets]]
id = "desktop-macos"
ui = "desktop"
builder = "desktop-macos"
status = "unsupported"
platform = "macOS"
assets = []
signing = "unsigned"
reason = "Never built on macOS."

[[release_binaries.targets]]
id = "app-ios"
ui = "app"
builder = "app-ios"
status = "credential"
platform = "iOS"
runner = "macos-latest"
assets = ["krypton-ios-{version}.ipa"]
signing = "unsigned"
credentials = ["EXPO_TOKEN"]
tracking_key = "ios-key"
needs = "An Apple account."
"""


def _repo(tmp_path: Path, config: str = CONFIG) -> rb.Settings:
    (tmp_path / "arches.toml").write_text(ARCHES, encoding="utf-8")
    (tmp_path / "meson.build").write_text("project('k', version: '1.2.3')\n", encoding="utf-8")
    (tmp_path / "app.json").write_text('{"version": "0.9.0"}\n', encoding="utf-8")
    (tmp_path / "rb.toml").write_text(config, encoding="utf-8")
    return rb.Settings.load(tmp_path / "rb.toml", tmp_path)


def _catalogue(tmp_path: Path, config: str = CONFIG) -> rb.TargetCatalogue:
    return rb.TargetCatalogue(_repo(tmp_path, config))


CONTEXT = rb.ReleaseContext(tag="v-1.0.0", release_branch="main", release_workflow="Release")


def _workflow() -> dict[str, Any]:
    """A workflow that agrees with CONFIG in every respect the checker holds it to."""

    def builder(name: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        job: dict[str, Any] = {
            "needs": "plan",
            "runs-on": "${{ matrix.runner }}",
            "strategy": {"matrix": f"${{{{ fromJSON(needs.plan.outputs.{name}) }}}}"},
            "steps": [{"run": "true"}],
        }
        job.update(extra or {})
        return job

    ios_steps = [
        {"env": {"EXPO_TOKEN": "${{ secrets.EXPO_TOKEN }}"}},
        {"run": 'vibey-gh tracking-issue raise --key "$TRACKING_KEY"'},
        {"run": 'vibey-gh tracking-issue resolve --key "$TRACKING_KEY"'},
        {"env": {"TRACKING_KEY": "${{ matrix.tracking_key }}"}},
    ]
    return {
        "on": {
            "workflow_run": {"workflows": ["Release"], "types": ["completed"], "branches": ["main"]}
        },
        "jobs": {
            "plan": {
                "outputs": {
                    "desktop-flatpak": "${{ steps.plan.outputs.desktop-flatpak }}",
                    "app-ios": "${{ steps.plan.outputs.app-ios }}",
                }
            },
            "desktop-flatpak": builder("desktop-flatpak"),
            "app-ios": builder("app-ios", {"steps": ios_steps}),
            "collect": {"needs": ["plan", "desktop-flatpak", "app-ios"]},
            "attach": {"needs": ["plan", "collect"]},
        },
    }


def _checker(tmp_path: Path) -> rb.WorkflowChecker:
    settings = _repo(tmp_path)
    return rb.WorkflowChecker(rb.TargetCatalogue(settings), settings, CONTEXT)


# ------------------------------------------------------------------------ catalogue


def test_a_per_arch_target_is_one_target_per_declared_linux_architecture(tmp_path: Path) -> None:
    targets = {t.id: t for t in _catalogue(tmp_path).targets()}
    x86, arm = targets["desktop-flatpak-x86_64"], targets["desktop-flatpak-aarch64"]
    assert (x86.runner, arm.runner) == ("ubuntu-24.04", "ubuntu-24.04-arm")
    assert x86.assets == ("krypton-desktop-1.2.3-linux-x86_64.flatpak",)
    assert x86.asset_patterns == ("krypton-desktop-<version>-linux-x86_64.flatpak",)
    assert x86.install == "flatpak install krypton-desktop-<version>-linux-x86_64.flatpak"
    assert targets["app-ios"].assets == ("krypton-ios-0.9.0.ipa",)


def test_an_unsupported_target_has_no_builder(tmp_path: Path) -> None:
    assert _catalogue(tmp_path).builders() == ["desktop-flatpak", "app-ios"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (('ui = "app"', 'ui = "nothing"'), "is not a [release_binaries.uis]"),
        (('status = "credential"', 'status = "maybe"'), "status must be one of"),
        (('signing = "unsigned"\ncredentials', 'signing = "wax-seal"\ncredentials'), "signing"),
        (('tracking_key = "ios-key"\n', ""), "lacks tracking_key"),
        (('needs = "An Apple account."\n', ""), "lacks needs"),
        (('runner = "macos-latest"\n', ""), "runner (or per_linux_arch)"),
        (('reason = "Never built on macOS."\n', ""), "lacks reason"),
    ],
)
def test_a_declaration_missing_what_its_status_needs_is_refused(
    tmp_path: Path, change: tuple[str, str], message: str
) -> None:
    old, new = change
    assert old in CONFIG
    with pytest.raises(rb.ReleaseBinariesError, match=re.escape(message)):
        _catalogue(tmp_path, CONFIG.replace(old, new, 1)).targets()


def test_two_targets_may_not_produce_the_same_file(tmp_path: Path) -> None:
    clash = CONFIG.replace(
        '"krypton-ios-{version}.ipa"', '"krypton-desktop-1.2.3-linux-x86_64.flatpak"'
    )
    with pytest.raises(rb.ReleaseBinariesError, match="asset names produced twice"):
        _catalogue(tmp_path, clash).targets()


def test_a_version_the_pattern_cannot_find_is_refused(tmp_path: Path) -> None:
    catalogue = _catalogue(tmp_path)
    (tmp_path / "meson.build").write_text("project('k')\n", encoding="utf-8")
    with pytest.raises(rb.ReleaseBinariesError, match="no version matches"):
        catalogue.targets()


def test_missing_linux_architectures_are_refused(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    (tmp_path / "arches.toml").write_text("[minimum_specs]\n", encoding="utf-8")
    with pytest.raises(rb.ReleaseBinariesError, match="has no"):
        rb.TargetCatalogue(settings).targets()


def test_settings_without_the_table_or_a_key_are_refused(tmp_path: Path) -> None:
    (tmp_path / "x.toml").write_text("[other]\n", encoding="utf-8")
    with pytest.raises(rb.ReleaseBinariesError, match="no \\[release_binaries\\]"):
        rb.Settings.load(tmp_path / "x.toml", tmp_path)
    (tmp_path / "y.toml").write_text("[release_binaries]\n", encoding="utf-8")
    with pytest.raises(rb.ReleaseBinariesError, match="lacks"):
        rb.Settings.load(tmp_path / "y.toml", tmp_path)


# ----------------------------------------------------------------------------- plan


def test_the_plan_has_a_matrix_per_builder_and_the_files_it_must_produce(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    plan = rb.MatrixPlanner(rb.TargetCatalogue(settings), settings).plan(
        mode="publish", target="abc", tag="v-1.0.0"
    )
    assert plan["expected"] == [
        "krypton-desktop-1.2.3-linux-x86_64.flatpak",
        "krypton-desktop-1.2.3-linux-aarch64.flatpak",
    ]
    assert plan["optional"] == ["krypton-ios-0.9.0.ipa"]
    assert set(plan["builders"]) == {"desktop-flatpak", "app-ios"}
    rows = plan["builders"]["desktop-flatpak"]["include"]
    assert [row["runner"] for row in rows] == ["ubuntu-24.04", "ubuntu-24.04-arm"]
    assert rows[0]["module"] == "krypton-desktop"
    assert rows[0]["artifact"] == "release-binary-desktop-flatpak-x86_64"
    ios = plan["builders"]["app-ios"]["include"][0]
    assert (ios["tracking_key"], ios["credentials"]) == ("ios-key", "EXPO_TOKEN")


def test_the_plan_refuses_an_unknown_mode(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    with pytest.raises(rb.ReleaseBinariesError, match="mode"):
        rb.MatrixPlanner(rb.TargetCatalogue(settings), settings).plan(
            mode="yolo", target="a", tag="t"
        )


def test_the_github_output_has_one_compact_json_line_per_builder(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    plan = rb.MatrixPlanner(rb.TargetCatalogue(settings), settings).plan(
        mode="dry-run", target="abc", tag="v-1.0.0"
    )
    lines = dict(line.split("=", 1) for line in rb.MatrixPlanner.github_output(plan).splitlines())
    assert lines["mode"] == "dry-run" and lines["tag"] == "v-1.0.0"
    assert json.loads(lines["desktop-flatpak"])["include"][1]["arch"] == "aarch64"
    assert json.loads(lines["optional"]) == ["krypton-ios-0.9.0.ipa"]
    assert (lines["release_wait_s"], lines["poll_s"], lines["checksums"]) == (
        "60",
        "5",
        "SHA256SUMS",
    )


# ---------------------------------------------------------------------------- check


def test_a_workflow_that_agrees_has_no_problems(tmp_path: Path) -> None:
    assert _checker(tmp_path).problems(_workflow()) == []


def test_a_declared_builder_without_a_job_is_drift(tmp_path: Path) -> None:
    workflow = _workflow()
    del workflow["jobs"]["desktop-flatpak"]
    assert any("has no job" in p for p in _checker(tmp_path).problems(workflow))


def test_a_job_that_builds_nothing_declared_is_drift(tmp_path: Path) -> None:
    workflow = _workflow()
    workflow["jobs"]["windows"] = {"needs": "plan"}
    assert any("job `windows` builds nothing" in p for p in _checker(tmp_path).problems(workflow))


def test_a_job_for_an_unsupported_target_is_drift(tmp_path: Path) -> None:
    workflow = _workflow()
    workflow["jobs"]["desktop-macos"] = {"needs": "plan"}
    problems = _checker(tmp_path).problems(workflow)
    assert any("declared unsupported" in p for p in problems)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda w: w["jobs"]["desktop-flatpak"].update(strategy={"matrix": {"os": ["x"]}}),
            "matrix",
        ),
        (lambda w: w["jobs"]["desktop-flatpak"].update({"runs-on": "ubuntu-latest"}), "run on"),
        (lambda w: w["jobs"]["desktop-flatpak"].update(needs=[]), "must need `plan`"),
        (lambda w: w["jobs"]["plan"]["outputs"].pop("app-ios"), "declare output `app-ios:"),
        (lambda w: w["jobs"]["collect"].update(needs=["plan"]), "does not wait for"),
        (lambda w: w["jobs"].pop("attach"), "no `attach` job"),
        (lambda w: w["on"]["workflow_run"].update(branches=["develop"]), "must follow"),
        (lambda w: w["jobs"]["app-ios"]["steps"].pop(0), "credential `EXPO_TOKEN`"),
        (lambda w: w["jobs"]["app-ios"]["steps"].pop(2), "tracking-issue resolve"),
        (lambda w: w["jobs"]["app-ios"]["steps"].pop(3), "tracking issue on the target's key"),
    ],
)
def test_each_disagreement_is_named(tmp_path: Path, mutate: Any, message: str) -> None:
    workflow = _workflow()
    mutate(workflow)
    problems = _checker(tmp_path).problems(workflow)
    assert any(message in p for p in problems), problems


def test_the_true_key_pyyaml_gives_on_is_read_too(tmp_path: Path) -> None:
    workflow = _workflow()
    workflow[True] = workflow.pop("on")
    assert _checker(tmp_path).problems(workflow) == []


# ----------------------------------------------------------------------------- page


def test_the_page_lists_built_waiting_and_unsupported_targets(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    text = rb.DownloadsRenderer(rb.TargetCatalogue(settings), settings).render()
    assert (
        "| krypton desktop | Linux | aarch64 | `krypton-desktop-<version>-linux-aarch64.flatpak` |"
        in text
    )
    assert "### Waiting for a credential" in text and "An Apple account." in text
    assert "### Not supported" in text and "Never built on macOS." in text
    assert "1.2.3" not in text, "the page shows names, not one release's numbers"


def test_the_page_block_is_replaced_and_must_be_there_exactly_once(tmp_path: Path) -> None:
    settings = _repo(tmp_path)
    renderer = rb.DownloadsRenderer(rb.TargetCatalogue(settings), settings)
    page = f"# Downloads\n\n{rb.BEGIN}\nstale\n{rb.END}\n\nAfter.\n"
    fresh = renderer.apply(page)
    assert "stale" not in fresh and fresh.endswith(f"{rb.END}\n\nAfter.\n")
    assert renderer.apply(fresh) == fresh
    with pytest.raises(rb.ReleaseBinariesError, match="exactly one"):
        renderer.apply("# no markers\n")


# ----------------------------------------------------------------------------- PyPI


class FakeHttp:
    def __init__(self, pages: dict[str, list[bytes | Exception]]) -> None:
        self.pages = pages
        self.asked: list[str] = []

    def get(self, url: str) -> bytes:
        self.asked.append(url)
        answers = self.pages[url]
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def _listing(body: bytes, digest: str | None = None) -> bytes:
    return json.dumps(
        {
            "urls": [
                {
                    "filename": "pkg-1.0-py3-none-any.whl",
                    "url": "https://files.example/pkg.whl",
                    "digests": {"sha256": digest or hashlib.sha256(body).hexdigest()},
                }
            ]
        }
    ).encode()


def _fetcher(http: FakeHttp, slept: list[float]) -> rb.PypiFetcher:
    return rb.PypiFetcher(
        http,
        "https://pypi.example/{project}/{version}/json",
        wait_s=10,
        poll_s=5,
        sleep=slept.append,
    )


def test_pypi_files_are_written_when_their_digest_matches(tmp_path: Path) -> None:
    http = FakeHttp(
        {
            "https://pypi.example/pkg/1.0/json": [_listing(b"wheel")],
            "https://files.example/pkg.whl": [b"wheel"],
        }
    )
    written = _fetcher(http, []).fetch("pkg", "1.0", tmp_path / "out")
    assert [p.name for p in written] == ["pkg-1.0-py3-none-any.whl"]
    assert written[0].read_bytes() == b"wheel"


def test_a_file_whose_digest_differs_from_pypi_is_refused(tmp_path: Path) -> None:
    http = FakeHttp(
        {
            "https://pypi.example/pkg/1.0/json": [_listing(b"wheel", digest="0" * 64)],
            "https://files.example/pkg.whl": [b"wheel"],
        }
    )
    with pytest.raises(rb.ReleaseBinariesError, match="is not the"):
        _fetcher(http, []).fetch("pkg", "1.0", tmp_path)
    assert not (tmp_path / "pkg-1.0-py3-none-any.whl").exists()


def test_a_late_upload_is_waited_for_then_fetched(tmp_path: Path) -> None:
    slept: list[float] = []
    http = FakeHttp(
        {
            "https://pypi.example/pkg/1.0/json": [
                OSError("404"),
                json.dumps({"urls": []}).encode(),
                _listing(b"w"),
            ],
            "https://files.example/pkg.whl": [b"w"],
        }
    )
    assert len(_fetcher(http, slept).fetch("pkg", "1.0", tmp_path)) == 1
    assert slept == [5, 5]


def test_a_version_never_uploaded_is_reported_after_the_wait(tmp_path: Path) -> None:
    slept: list[float] = []
    http = FakeHttp({"https://pypi.example/pkg/1.0/json": [OSError("404 Not Found")]})
    with pytest.raises(rb.ReleaseBinariesError, match="not on PyPI after 10s: 404 Not Found"):
        _fetcher(http, slept).fetch("pkg", "1.0", tmp_path)
    assert slept == [5, 5]


def test_an_unsafe_file_name_from_the_index_is_refused(tmp_path: Path) -> None:
    listing = json.loads(_listing(b"w"))
    listing["urls"][0]["filename"] = "../escape.whl"
    http = FakeHttp({"https://pypi.example/pkg/1.0/json": [json.dumps(listing).encode()]})
    with pytest.raises(rb.ReleaseBinariesError, match="unsafe"):
        _fetcher(http, []).fetch("pkg", "1.0", tmp_path)


def test_the_real_fetcher_refuses_anything_but_https() -> None:
    with pytest.raises(rb.ReleaseBinariesError, match="non-HTTPS"):
        rb.UrllibFetcher().get("http://pypi.org/simple")


# -------------------------------------------------------------------------- collect


def test_collect_writes_sha256sum_lines_over_exactly_the_declared_files(tmp_path: Path) -> None:
    (tmp_path / "a.flatpak").write_bytes(b"a")
    (tmp_path / "b.ipa").write_bytes(b"b")
    names = rb.AssetCollector(tmp_path, "SHA256SUMS").collect(["a.flatpak"], ["b.ipa"])
    assert names == ["a.flatpak", "b.ipa"]
    sums = (tmp_path / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert sums[0] == f"{hashlib.sha256(b'a').hexdigest()}  a.flatpak"
    assert len(sums) == 2


def test_an_optional_file_may_be_absent(tmp_path: Path) -> None:
    (tmp_path / "a.flatpak").write_bytes(b"a")
    assert rb.AssetCollector(tmp_path, "SHA256SUMS").collect(["a.flatpak"], ["b.ipa"]) == [
        "a.flatpak"
    ]


def test_a_missing_or_undeclared_file_is_refused(tmp_path: Path) -> None:
    (tmp_path / "stray.bin").write_bytes(b"x")
    with pytest.raises(
        rb.ReleaseBinariesError, match=r"missing: a\.flatpak; not declared: stray\.bin"
    ):
        rb.AssetCollector(tmp_path, "SHA256SUMS").collect(["a.flatpak"], [])
    assert not (tmp_path / "SHA256SUMS").exists()


# -------------------------------------------------------------------------- flatpak


def test_the_manifest_builds_one_module_from_the_checkout(tmp_path: Path) -> None:
    manifest = tmp_path / "m.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "app-id": "io.example.App",
                "modules": [
                    {"name": "dep", "sources": [{"type": "archive", "url": "https://x"}]},
                    {"name": "app", "subdir": "clients/desktop", "sources": [{"type": "git"}]},
                ],
            }
        ),
        encoding="utf-8",
    )
    data = rb.FlatpakManifestLocalizer().localize(manifest, "app", tmp_path)
    assert data["modules"][1]["sources"] == [{"type": "dir", "path": str(tmp_path.resolve())}]
    assert data["modules"][1]["subdir"] == "clients/desktop"
    assert data["modules"][0]["sources"] == [{"type": "archive", "url": "https://x"}]
    with pytest.raises(rb.ReleaseBinariesError, match="no single module"):
        rb.FlatpakManifestLocalizer().localize(manifest, "absent", tmp_path)


# ------------------------------------------------------------------------------ CLI


def test_the_cli_reports_a_refusal_as_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _repo(tmp_path)
    (tmp_path / "x").mkdir()
    code = rb.Cli(tmp_path / "rb.toml", tmp_path).run(
        ["collect", "--dir", str(tmp_path / "x"), "--expected", '["a"]']
    )
    assert code == 1
    assert "missing: a" in capsys.readouterr().err


def test_the_cli_collects_and_localizes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _repo(tmp_path)
    files = tmp_path / "files"
    files.mkdir()
    (files / "a").write_bytes(b"a")
    cli = rb.Cli(tmp_path / "rb.toml", tmp_path)
    assert cli.run(["collect", "--dir", str(files), "--expected", '["a"]']) == 0
    assert (files / "SHA256SUMS").is_file()
    manifest = tmp_path / "m.yml"
    manifest.write_text("modules:\n  - name: app\n    sources: []\n", encoding="utf-8")
    out = tmp_path / "built" / "m.json"
    args = ["flatpak-manifest", "--manifest", str(manifest), "--module", "app"]
    assert cli.run([*args, "--source", str(tmp_path), "--out", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["modules"][0]["sources"][0]["type"] == "dir"
    assert "wrote" in capsys.readouterr().out


# ------------------------------------------------------------ signing a credential raises

SIGNED = (
    CONFIG
    + """
[[release_binaries.targets]]
id = "desktop-mac-arm64"
ui = "desktop"
builder = "desktop-mac"
status = "build"
platform = "macOS"
arch = "arm64"
runner = "macos-15"
assets = ["krypton-desktop-{version}-macos-arm64.dmg"]
signing = "apple-ad-hoc"
note = "An app."
signing_credentials = ["CERT", "NOTARY"]
signing_tracking_key = "mac-signing"
signing_needs = "A Developer ID."
"""
)


def _signed_workflow(steps: list[dict[str, Any]]) -> dict[str, Any]:
    workflow = _workflow()
    jobs = workflow["jobs"]
    jobs["plan"]["outputs"]["desktop-mac"] = "${{ steps.plan.outputs.desktop-mac }}"
    jobs["desktop-mac"] = {
        "needs": "plan",
        "runs-on": "${{ matrix.runner }}",
        "strategy": {"matrix": "${{ fromJSON(needs.plan.outputs.desktop-mac) }}"},
        "steps": steps,
    }
    jobs["collect"]["needs"].append("desktop-mac")
    return workflow


MAC_STEPS = [
    {"env": {"CERT": "${{ secrets.CERT }}", "NOTARY": "${{ secrets.NOTARY }}"}},
    {"run": 'vibey-gh tracking-issue raise --key "$K"'},
    {"run": 'vibey-gh tracking-issue resolve --key "$K"'},
    {"env": {"K": "${{ matrix.signing_tracking_key }}"}},
]


def test_a_built_target_whose_signing_waits_carries_its_key_in_its_row(tmp_path: Path) -> None:
    target = {t.id: t for t in _catalogue(tmp_path, SIGNED).targets()}["desktop-mac-arm64"]
    row = target.row()
    assert row["signing_tracking_key"] == "mac-signing"
    assert row["signing_credentials"] == "CERT NOTARY"
    assert row["signing_needs"] == "A Developer ID."
    assert target.status == "build", "it is built either way: only its signing waits"


def test_a_job_that_reads_tracks_and_keys_its_signing_credentials_agrees(tmp_path: Path) -> None:
    settings = _repo(tmp_path, SIGNED)
    checker = rb.WorkflowChecker(rb.TargetCatalogue(settings), settings, CONTEXT)
    assert checker.problems(_signed_workflow(MAC_STEPS)) == []


@pytest.mark.parametrize(
    ("drop", "message"),
    [
        (0, "never reads the credential `CERT`"),
        (1, "never runs `vibey-gh tracking-issue raise`"),
        (2, "never runs `vibey-gh tracking-issue resolve`"),
        (3, "matrix.signing_tracking_key"),
    ],
)
def test_a_signing_credential_is_held_to_the_credential_rules(
    tmp_path: Path, drop: int, message: str
) -> None:
    settings = _repo(tmp_path, SIGNED)
    checker = rb.WorkflowChecker(rb.TargetCatalogue(settings), settings, CONTEXT)
    steps = [step for index, step in enumerate(MAC_STEPS) if index != drop]
    problems = checker.problems(_signed_workflow(steps))
    assert any(message in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (('signing_tracking_key = "mac-signing"\n', ""), "signing_tracking_key"),
        (('signing_needs = "A Developer ID."\n', ""), "signing_needs"),
        (
            (
                'builder = "desktop-mac"\nstatus = "build"',
                'builder = "desktop-mac"\nstatus = "credential"',
            ),
            "status = build",
        ),
    ],
)
def test_signing_credentials_need_a_key_a_reason_and_a_built_target(
    tmp_path: Path, change: tuple[str, str], message: str
) -> None:
    old, new = change
    assert old in SIGNED
    with pytest.raises(rb.ReleaseBinariesError, match=re.escape(message)):
        _catalogue(tmp_path, SIGNED.replace(old, new, 1)).targets()


def test_the_page_says_what_signing_waits_for(tmp_path: Path) -> None:
    settings = _repo(tmp_path, SIGNED)
    text = rb.DownloadsRenderer(rb.TargetCatalogue(settings), settings).render()
    section = text.split("### Signing that waits for a credential", 1)[1].split("###", 1)[0]
    assert "**krypton desktop, macOS**: built and attached on every release" in section
    assert "A Developer ID." in section and "(`mac-signing`)" in section
    assert rb.SIGNING["apple-ad-hoc"] in text, "the table says how the file is signed"
