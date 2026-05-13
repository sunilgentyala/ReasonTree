"""Tests for the tree search retrieval engine."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import pytest

from reasontree.retrieve import (
    _select_children,
    _evaluate_node,
    tree_search,
)
from reasontree.config import ReasonTreeConfig


class TestSelectChildren:
    def test_returns_subset_of_children_based_on_llm(self, simple_tree):
        parent = simple_tree
        children = simple_tree["nodes"]

        llm_response = json.dumps({"relevant_indices": [1], "reasoning": "Risk section is relevant."})

        with patch("reasontree.retrieve.llm_completion", return_value=llm_response):
            selected = _select_children(parent, children, "credit risk exposure", None, "gpt-4o")

        assert len(selected) == 1
        assert selected[0]["title"] == "Risk Factors"

    def test_returns_all_children_when_llm_fails(self, simple_tree):
        parent = simple_tree
        children = simple_tree["nodes"]

        with patch("reasontree.retrieve.llm_completion", return_value="not json at all"):
            selected = _select_children(parent, children, "any query", None, "gpt-4o")

        # Should fall back to returning all children when indices are missing.
        assert len(selected) == len(children)

    def test_ignores_out_of_range_indices(self, simple_tree):
        parent = simple_tree
        children = simple_tree["nodes"]

        llm_response = json.dumps({"relevant_indices": [0, 99, -1]})
        with patch("reasontree.retrieve.llm_completion", return_value=llm_response):
            selected = _select_children(parent, children, "anything", None, "gpt-4o")

        assert len(selected) == 1
        assert selected[0]["title"] == "Executive Summary"

    def test_passes_context_to_llm(self, simple_tree):
        parent = simple_tree
        children = simple_tree["nodes"]

        with patch("reasontree.retrieve.llm_completion") as mock_llm:
            mock_llm.return_value = json.dumps({"relevant_indices": [0]})
            _select_children(parent, children, "query", "extra context here", "gpt-4o")

        call_args = mock_llm.call_args
        assert "extra context here" in call_args.kwargs.get("prompt", call_args.args[1] if len(call_args.args) > 1 else "")


class TestEvaluateNode:
    def test_marks_relevant_node(self):
        node = {
            "title": "Market Risk",
            "start_page": 6,
            "end_page": 10,
            "node_id": "0004",
            "summary": "Discussion of interest rate risk.",
        }
        with patch(
            "reasontree.retrieve.llm_completion",
            return_value='{"relevant": true, "reasoning": "Directly addresses risk."}',
        ):
            result = _evaluate_node(node, "interest rate risk", None, "gpt-4o")

        assert result["relevant"] is True

    def test_marks_irrelevant_node(self):
        node = {
            "title": "Corporate History",
            "start_page": 1,
            "end_page": 3,
            "summary": "History of the company since founding.",
        }
        with patch(
            "reasontree.retrieve.llm_completion",
            return_value='{"relevant": false, "reasoning": "Not related to risk."}',
        ):
            result = _evaluate_node(node, "credit risk", None, "gpt-4o")

        assert result["relevant"] is False

    def test_includes_node_metadata_in_result(self):
        node = {"title": "Section A", "start_page": 5, "end_page": 8}
        with patch("reasontree.retrieve.llm_completion", return_value='{"relevant": true}'):
            result = _evaluate_node(node, "anything", None, "gpt-4o")

        assert result["node"] == "Section A"
        assert result["pages"] == "5-8"


class TestTreeSearch:
    def test_returns_empty_result_when_nothing_relevant(self, simple_tree, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake pdf content")

        with (
            patch("reasontree.retrieve._select_children", return_value=[]),
            patch("reasontree.retrieve._evaluate_node", return_value={"relevant": False}),
        ):
            result = tree_search(
                tree=simple_tree,
                file_path=str(fake_pdf),
                query="something not in the document",
                model="gpt-4o",
            )

        assert result.pages == []
        assert result.content == ""

    def test_returns_pages_from_relevant_nodes(self, simple_tree, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake pdf content")

        # Make the tree search find only the "Market Risk" leaf (pages 6-10).
        def fake_select(parent, children, query, context, model):
            if parent["title"] == "Document Root":
                return [c for c in children if c["title"] == "Risk Factors"]
            if parent["title"] == "Risk Factors":
                return [c for c in children if c["title"] == "Market Risk"]
            return children

        with (
            patch("reasontree.retrieve._select_children", side_effect=fake_select),
            patch(
                "reasontree.retrieve._evaluate_node",
                return_value={"relevant": True, "reasoning": "Matches."},
            ),
            patch("reasontree.retrieve._extract_pages", return_value="[Page 6]\nContent here."),
        ):
            result = tree_search(
                tree=simple_tree,
                file_path=str(fake_pdf),
                query="interest rate risk",
                model="gpt-4o",
            )

        assert 6 in result.pages
        assert "Content here." in result.content
        assert len(result.reasoning) > 0

    def test_reasoning_trail_is_populated(self, simple_tree, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"")

        with (
            patch("reasontree.retrieve._select_children", return_value=[]),
            patch("reasontree.retrieve._evaluate_node", return_value={"relevant": False}),
        ):
            result = tree_search(
                tree=simple_tree,
                file_path=str(fake_pdf),
                query="test",
                model="gpt-4o",
            )

        assert isinstance(result.reasoning, list)

    def test_node_ids_captured_for_relevant_nodes(self, simple_tree, tmp_path):
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"")

        market_risk = simple_tree["nodes"][1]["nodes"][0]  # node_id 0004

        def fake_select(parent, children, *args, **kwargs):
            if parent["title"] == "Document Root":
                return [simple_tree["nodes"][1]]
            if parent["title"] == "Risk Factors":
                return [market_risk]
            return children

        with (
            patch("reasontree.retrieve._select_children", side_effect=fake_select),
            patch(
                "reasontree.retrieve._evaluate_node",
                return_value={"relevant": True},
            ),
            patch("reasontree.retrieve._extract_pages", return_value="page text"),
        ):
            result = tree_search(
                tree=simple_tree,
                file_path=str(fake_pdf),
                query="market risk",
                model="gpt-4o",
            )

        assert "0004" in result.node_ids
