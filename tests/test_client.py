"""Tests for the ReasonTreeClient high-level API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from reasontree import ReasonTreeClient, ReasonTreeConfig


class TestClientInit:
    def test_constructs_without_api_key_when_env_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        client = ReasonTreeClient()
        assert isinstance(client, ReasonTreeClient)

    def test_api_key_sets_environment_variable(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        client = ReasonTreeClient(api_key="sk-test-key")
        import os
        assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"

    def test_custom_model_is_applied(self):
        client = ReasonTreeClient(model="gpt-4o-mini")
        assert client.config.model == "gpt-4o-mini"

    def test_custom_retrieve_model(self):
        client = ReasonTreeClient(model="gpt-4o", retrieve_model="gpt-4o-mini")
        assert client.config.effective_retrieve_model == "gpt-4o-mini"

    def test_explicit_config_overrides_model_args(self):
        config = ReasonTreeConfig(model="custom-model")
        client = ReasonTreeClient(model="ignored-model", config=config)
        assert client.config.model == "custom-model"

    def test_workspace_is_created(self, tmp_path):
        ws = tmp_path / "my_workspace"
        client = ReasonTreeClient(workspace=str(ws))
        assert ws.exists()

    def test_workspace_documents_persisted_and_reloaded(self, tmp_path, simple_tree):
        ws = tmp_path / "ws"
        client1 = ReasonTreeClient(workspace=str(ws))

        # Manually inject a document as if it had been indexed.
        import uuid
        doc_id = str(uuid.uuid4())
        client1._documents[doc_id] = {"path": "/fake/path.pdf", "tree": simple_tree}
        client1._save_document(doc_id)

        # New client loaded from the same workspace should find it.
        client2 = ReasonTreeClient(workspace=str(ws))
        assert doc_id in client2._documents


class TestClientIndex:
    def test_raises_for_missing_file(self):
        client = ReasonTreeClient()
        with pytest.raises(FileNotFoundError):
            client.index("/nonexistent/path/document.pdf")

    def test_raises_for_unknown_extension_in_auto_mode(self, tmp_path):
        unknown = tmp_path / "file.xyz"
        unknown.write_text("content")
        client = ReasonTreeClient()
        with pytest.raises(ValueError, match="Cannot determine file type"):
            client.index(str(unknown))

    def test_indexes_markdown_and_returns_doc_id(self, sample_markdown):
        async def fake_build(path, config):
            return {"title": "Root", "nodes": []}

        with patch("reasontree.client.build_tree_from_markdown", side_effect=fake_build):
            client = ReasonTreeClient()
            doc_id = client.index(str(sample_markdown), mode="markdown")

        assert isinstance(doc_id, str)
        assert len(doc_id) > 0

    def test_indexed_document_appears_in_list(self, sample_markdown):
        async def fake_build(path, config):
            return {"title": "Root", "nodes": []}

        with patch("reasontree.client.build_tree_from_markdown", side_effect=fake_build):
            client = ReasonTreeClient()
            doc_id = client.index(str(sample_markdown), mode="markdown")

        docs = client.list_documents()
        assert any(d["doc_id"] == doc_id for d in docs)


class TestClientRetrieve:
    def test_raises_for_unknown_doc_id(self):
        client = ReasonTreeClient()
        with pytest.raises(KeyError):
            client.retrieve("nonexistent-id", "query")

    def test_calls_tree_search_and_returns_result(self, simple_tree):
        from reasontree.client import RetrievalResult

        client = ReasonTreeClient()
        client._documents["test-id"] = {"path": "/fake.pdf", "tree": simple_tree}

        fake_result = RetrievalResult(pages=[1, 2], content="relevant content")

        with patch("reasontree.client.tree_search", return_value=fake_result):
            result = client.retrieve("test-id", "What are the risks?")

        assert result.pages == [1, 2]
        assert "relevant content" in result.content


class TestClientGetTree:
    def test_returns_tree_without_text_by_default(self, simple_tree):
        node_with_text = dict(simple_tree)
        node_with_text["text"] = "long text content"
        client = ReasonTreeClient()
        client._documents["doc-1"] = {"path": "", "tree": node_with_text}

        result = client.get_tree("doc-1", strip_text=True)
        assert "text" not in result

    def test_returns_tree_with_text_when_requested(self, simple_tree):
        node_with_text = dict(simple_tree)
        node_with_text["text"] = "preserved text"
        client = ReasonTreeClient()
        client._documents["doc-1"] = {"path": "", "tree": node_with_text}

        result = client.get_tree("doc-1", strip_text=False)
        assert result["text"] == "preserved text"

    def test_raises_for_unknown_doc(self):
        client = ReasonTreeClient()
        with pytest.raises(KeyError):
            client.get_tree("does-not-exist")
