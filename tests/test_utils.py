"""Tests for shared utility functions."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from reasontree.utils import (
    count_tokens,
    extract_json,
    remove_fields,
    _strip_provider_prefix,
)


class TestCountTokens:
    def test_empty_string_returns_zero(self):
        assert count_tokens("") == 0

    def test_nonempty_string_returns_positive(self):
        result = count_tokens("Hello, this is a test sentence.")
        assert result > 0

    def test_longer_text_has_more_tokens(self):
        short = count_tokens("short text")
        long = count_tokens("This is a much longer piece of text with many more words and tokens.")
        assert long > short


class TestExtractJson:
    def test_plain_json(self):
        text = '{"answer": "yes", "reason": "found it"}'
        result = extract_json(text)
        assert result["answer"] == "yes"

    def test_json_inside_markdown_fence(self):
        text = 'Here is the result:\n```json\n{"relevant": true}\n```'
        result = extract_json(text)
        assert result["relevant"] is True

    def test_json_with_surrounding_text(self):
        text = 'The model says: {"score": 42} and nothing else.'
        result = extract_json(text)
        assert result["score"] == 42

    def test_returns_empty_dict_when_no_json(self):
        result = extract_json("This is just plain text with no JSON.")
        assert result == {}

    def test_returns_empty_dict_for_invalid_json(self):
        result = extract_json("{broken json: [}")
        assert result == {}

    def test_nested_json(self):
        data = {"nodes": [{"id": "001"}, {"id": "002"}], "count": 2}
        result = extract_json(json.dumps(data))
        assert result["count"] == 2
        assert len(result["nodes"]) == 2


class TestRemoveFields:
    def test_removes_field_from_flat_dict(self):
        obj = {"title": "Section", "text": "Full text here", "summary": "Short summary"}
        result = remove_fields(obj, ["text"])
        assert "text" not in result
        assert "title" in result
        assert "summary" in result

    def test_removes_fields_recursively(self):
        obj = {
            "title": "Root",
            "text": "root text",
            "nodes": [
                {"title": "Child", "text": "child text"},
            ],
        }
        result = remove_fields(obj, ["text"])
        assert "text" not in result
        assert "text" not in result["nodes"][0]

    def test_does_not_mutate_original(self):
        obj = {"title": "A", "text": "keep this"}
        original_text = obj["text"]
        remove_fields(obj, ["text"])
        assert obj["text"] == original_text

    def test_remove_multiple_fields(self):
        obj = {"a": 1, "b": 2, "c": 3}
        result = remove_fields(obj, ["a", "b"])
        assert "a" not in result
        assert "b" not in result
        assert result["c"] == 3

    def test_handles_missing_field_gracefully(self):
        obj = {"title": "Section"}
        result = remove_fields(obj, ["nonexistent"])
        assert result == {"title": "Section"}


class TestStripProviderPrefix:
    def test_strips_litellm_prefix(self):
        assert _strip_provider_prefix("litellm/gpt-4o") == "gpt-4o"

    def test_leaves_clean_model_name_unchanged(self):
        assert _strip_provider_prefix("gpt-4o") == "gpt-4o"

    def test_leaves_other_prefixes_unchanged(self):
        assert _strip_provider_prefix("anthropic/claude-opus-4-7") == "anthropic/claude-opus-4-7"

    def test_handles_empty_string(self):
        assert _strip_provider_prefix("") == ""
