"""Tests for configuration loading and validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from reasontree.config import ReasonTreeConfig, load_config


class TestReasonTreeConfig:
    def test_defaults_are_sensible(self):
        config = ReasonTreeConfig()
        assert config.model == "gpt-4o-2024-11-20"
        assert config.toc_check_pages == 20
        assert config.max_pages_per_node == 10
        assert config.max_tokens_per_node == 20000
        assert config.add_node_summary is True
        assert config.add_node_id is True
        assert config.add_doc_description is False

    def test_retrieve_model_falls_back_to_model(self):
        config = ReasonTreeConfig(model="gpt-4o-mini")
        assert config.effective_retrieve_model == "gpt-4o-mini"

    def test_retrieve_model_can_differ_from_index_model(self):
        config = ReasonTreeConfig(model="gpt-4o", retrieve_model="gpt-4o-mini")
        assert config.model == "gpt-4o"
        assert config.effective_retrieve_model == "gpt-4o-mini"

    def test_toc_check_pages_must_be_positive(self):
        with pytest.raises(Exception):
            ReasonTreeConfig(toc_check_pages=0)

    def test_max_tokens_minimum(self):
        with pytest.raises(Exception):
            ReasonTreeConfig(max_tokens_per_node=50)

    def test_boolean_flags(self):
        config = ReasonTreeConfig(add_node_summary=False, add_doc_description=True)
        assert config.add_node_summary is False
        assert config.add_doc_description is True


class TestLoadConfig:
    def test_loads_from_bundled_yaml(self):
        config = load_config()
        assert isinstance(config, ReasonTreeConfig)
        assert config.model  # should not be empty

    def test_overrides_take_precedence(self):
        config = load_config(overrides={"model": "gpt-4o-mini"})
        assert config.model == "gpt-4o-mini"

    def test_none_values_in_overrides_are_ignored(self):
        config = load_config(overrides={"model": None})
        # None should be filtered; the YAML default should remain
        assert config.model  # still has a value

    def test_custom_yaml_path(self, tmp_path: Path):
        yaml_content = "model: my-custom-model\ntoc_check_pages: 5\n"
        custom_yaml = tmp_path / "custom.yaml"
        custom_yaml.write_text(yaml_content)
        config = load_config(config_path=custom_yaml)
        assert config.model == "my-custom-model"
        assert config.toc_check_pages == 5

    def test_missing_yaml_uses_defaults(self, tmp_path: Path):
        nonexistent = tmp_path / "does_not_exist.yaml"
        config = load_config(config_path=nonexistent)
        assert isinstance(config, ReasonTreeConfig)
