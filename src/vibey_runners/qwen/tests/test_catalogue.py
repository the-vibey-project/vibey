# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The model catalogue as data: entries, lookups, and constraints."""

from __future__ import annotations

import re

import pytest

from qwenloop.domain.catalogue import (
    CATALOGUE,
    ModelCatalogue,
    ModelEntry,
    OllamaArtifact,
)
from qwenloop.domain.interfaces import ModelCatalogueInterface
from qwenloop.domain.model import Backend, ModelProfile
from qwenloop.infrastructure.profiles import (
    CATALOGUE_PROFILES,
    NVIDIA_BF16,
    PORTABLE,
    PROFILES,
    QWEN_GGUF_REVISION,
)


def test_every_entry_is_complete_and_dated() -> None:
    expected_names = {"qwen2.5-coder-14b", "gpt-oss-20b"}
    assert expected_names <= {e.name for e in CATALOGUE}
    for entry in CATALOGUE:
        assert entry.license_spdx
        assert re.fullmatch(r"^\d{4}-\d{2}-\d{2}$", entry.recorded)
        assert entry.min_ram_gib > 0
        assert entry.context_window > 0
        assert set(entry.unverified) <= {"llama.cpp", "ollama"}


def test_pinned_ggufs_carry_a_sha256_and_size() -> None:
    for entry in CATALOGUE:
        if entry.gguf is not None:
            gguf = entry.gguf
            assert gguf.sha256 is not None
            assert re.fullmatch(r"[0-9a-f]{64}", gguf.sha256)
            assert gguf.size is not None and gguf.size > 0
            assert re.fullmatch(r"[0-9a-f]{40}", gguf.revision)
            assert gguf.filename is not None and gguf.filename.endswith(".gguf")
            assert gguf.backend is Backend.LLAMA_CPP
            assert not gguf.filename.startswith("eagle3-")


def test_catalogue_rejects_duplicates_and_empty_entries() -> None:
    entry_a = ModelEntry(
        name="test-model",
        family="test",
        total_params_b=7.0,
        active_params_b=7.0,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=8,
        context_window=8192,
        ollama=OllamaArtifact("test:tag"),
        gguf=None,
        evidence="test",
        recorded="2026-09-22",
    )
    entry_dup_name = ModelEntry(
        name="test-model",
        family="test",
        total_params_b=7.0,
        active_params_b=7.0,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=8,
        context_window=8192,
        ollama=OllamaArtifact("other:tag"),
        gguf=None,
        evidence="test",
        recorded="2026-09-22",
    )
    with pytest.raises(ValueError, match="duplicate catalogue entry name: test-model"):
        ModelCatalogue((entry_a, entry_dup_name))

    entry_dup_tag = ModelEntry(
        name="other-model",
        family="test",
        total_params_b=7.0,
        active_params_b=7.0,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=8,
        context_window=8192,
        ollama=OllamaArtifact("test:tag"),
        gguf=None,
        evidence="test",
        recorded="2026-09-22",
    )
    with pytest.raises(
        ValueError, match=re.escape("duplicate Ollama tag in the catalogue: test:tag")
    ):
        ModelCatalogue((entry_a, entry_dup_tag))

    entry_empty = ModelEntry(
        name="empty-model",
        family="test",
        total_params_b=7.0,
        active_params_b=7.0,
        license_spdx="Apache-2.0",
        license_osi=True,
        min_ram_gib=8,
        context_window=8192,
        ollama=None,
        gguf=None,
        evidence="test",
        recorded="2026-09-22",
    )
    with pytest.raises(
        ValueError, match="catalogue entry empty-model pins neither an Ollama tag nor a GGUF"
    ):
        ModelCatalogue((entry_empty,))


def test_lookup_by_name_and_ollama_tag() -> None:
    cat = ModelCatalogue()
    assert cat.get("gpt-oss-20b").family == "gpt-oss"
    gpt = cat.by_ollama_tag("gpt-oss:20b")
    assert gpt is not None
    assert gpt.name == "gpt-oss-20b"
    assert cat.by_ollama_tag("nope:1b") is None
    with pytest.raises(KeyError, match=r"unknown catalogue entry 'nope'; known: .*gpt-oss-20b"):
        cat.get("nope")
    assert cat.entries() == CATALOGUE


def test_the_endpoint_default_is_a_catalogued_ollama_tag() -> None:
    # Under ADR-0099, the sovereign endpoint model may be the Heretic build or stock tag
    cat = ModelCatalogue()
    assert cat.get("gpt-oss-20b").ollama is not None
    assert cat.get("gpt-oss-20b").ollama.tag == "gpt-oss:20b"
    assert cat.by_ollama_tag("gpt-oss:20b") is not None


def test_existing_profiles_are_unchanged() -> None:
    assert set(PROFILES) == {"qwen2.5-coder-14b-q5-k-m", "qwen2.5-coder-14b-bf16"}
    expected_portable = ModelProfile(
        name="qwen2.5-coder-14b-q5-k-m",
        backend=Backend.LLAMA_CPP,
        repository="Qwen/Qwen2.5-Coder-14B-Instruct-GGUF",
        revision="d0a692ef765eefbf2fabb130b3cb2e8917e3d225",
        filename="qwen2.5-coder-14b-instruct-q5_k_m.gguf",
        sha256="98ab25e0132e3f1e6d3554e1b64de2b5021908819b740d9c208430117e49a775",
        size=10_508_873_152,
        quantization="Q5_K_M",
    )
    assert expected_portable == PORTABLE
    assert QWEN_GGUF_REVISION == "d0a692ef765eefbf2fabb130b3cb2e8917e3d225"
    assert ModelCatalogue().get("qwen2.5-coder-14b").gguf is PORTABLE
    assert CATALOGUE_PROFILES[PORTABLE.name] is PORTABLE
    assert NVIDIA_BF16.name not in CATALOGUE_PROFILES


def test_catalogue_satisfies_its_interface() -> None:
    assert isinstance(ModelCatalogue(), ModelCatalogueInterface)
