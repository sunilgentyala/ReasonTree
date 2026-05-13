"""Tests for the Markdown tree indexing module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

from reasontree.config import ReasonTreeConfig
from reasontree.index_md import _parse_markdown_tree, _assign_node_ids


class TestParseMarkdownTree:
    def test_single_heading_becomes_one_node(self):
        md = "# Introduction\n\nSome content here.\n"
        tree = _parse_markdown_tree(md)
        assert len(tree["nodes"]) == 1
        assert tree["nodes"][0]["title"] == "Introduction"

    def test_nested_headings_produce_nested_nodes(self):
        md = """# Part One\n\n## Section A\n\nContent A.\n\n## Section B\n\nContent B.\n"""
        tree = _parse_markdown_tree(md)
        assert len(tree["nodes"]) == 1
        part_one = tree["nodes"][0]
        assert part_one["title"] == "Part One"
        assert len(part_one["nodes"]) == 2

    def test_deeply_nested_headings(self):
        md = "# H1\n## H2\n### H3\n#### H4\nLeaf content.\n"
        tree = _parse_markdown_tree(md)
        h1 = tree["nodes"][0]
        h2 = h1["nodes"][0]
        h3 = h2["nodes"][0]
        h4 = h3["nodes"][0]
        assert h4["title"] == "H4"
        assert "Leaf content." in h4["text"]

    def test_text_between_headings_is_captured(self):
        md = "# Section\n\nThis is the body text.\nMore content.\n"
        tree = _parse_markdown_tree(md)
        node = tree["nodes"][0]
        assert "body text" in node["text"]

    def test_empty_document(self):
        tree = _parse_markdown_tree("")
        assert tree["title"] == "Document Root"
        assert tree["nodes"] == []

    def test_document_without_headings(self):
        md = "Just some plain text\nwith no headings at all.\n"
        tree = _parse_markdown_tree(md)
        assert tree["nodes"] == []
        assert "plain text" in tree["text"]

    def test_line_numbers_are_recorded(self):
        md = "# First Section\n\nContent.\n\n# Second Section\n\nMore content.\n"
        tree = _parse_markdown_tree(md)
        assert tree["nodes"][0]["line_num"] == 1
        assert tree["nodes"][1]["line_num"] == 5

    def test_multiple_top_level_headings(self):
        md = "# Alpha\n\ncontent\n\n# Beta\n\ncontent\n\n# Gamma\n\ncontent\n"
        tree = _parse_markdown_tree(md)
        titles = [n["title"] for n in tree["nodes"]]
        assert titles == ["Alpha", "Beta", "Gamma"]


class TestAssignNodeIds:
    def test_root_gets_id(self):
        tree = {"title": "Root", "nodes": []}
        _assign_node_ids(tree)
        assert "node_id" in tree

    def test_children_get_sequential_ids(self):
        tree = {
            "title": "Root",
            "nodes": [
                {"title": "A", "nodes": []},
                {"title": "B", "nodes": []},
            ],
        }
        _assign_node_ids(tree)
        root_id = int(tree["node_id"])
        a_id = int(tree["nodes"][0]["node_id"])
        b_id = int(tree["nodes"][1]["node_id"])
        assert a_id == root_id + 1
        assert b_id == root_id + 2

    def test_ids_are_zero_padded_four_digits(self):
        tree = {"title": "Root", "nodes": []}
        _assign_node_ids(tree)
        assert len(tree["node_id"]) == 4


class TestBuildTreeFromMarkdown:
    @pytest.mark.asyncio
    async def test_builds_tree_from_file(self, sample_markdown: Path):
        async def fake_acompletion(model: str, prompt: str) -> str:
            return "This section provides a summary of the content."

        with patch("reasontree.index_md.llm_acompletion", side_effect=fake_acompletion):
            from reasontree.index_md import build_tree_from_markdown
            config = ReasonTreeConfig(add_node_summary=True, add_node_id=True)
            tree = await build_tree_from_markdown(str(sample_markdown), config)

        assert tree["title"] == "Document Root"
        assert len(tree["nodes"]) > 0
        assert "node_id" in tree

    @pytest.mark.asyncio
    async def test_summaries_skipped_when_disabled(self, sample_markdown: Path):
        with patch("reasontree.index_md.llm_acompletion") as mock_llm:
            from reasontree.index_md import build_tree_from_markdown
            config = ReasonTreeConfig(add_node_summary=False, add_node_id=False)
            tree = await build_tree_from_markdown(str(sample_markdown), config)
            mock_llm.assert_not_called()

        def has_no_summaries(node):
            assert "summary" not in node
            for child in node.get("nodes", []):
                has_no_summaries(child)

        has_no_summaries(tree)
