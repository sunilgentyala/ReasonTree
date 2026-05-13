"""Markdown tree indexing: build a hierarchical tree from a Markdown file."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from .config import ReasonTreeConfig
from .utils import count_tokens, llm_acompletion

logger = logging.getLogger(__name__)


async def build_tree_from_markdown(md_path: str, config: ReasonTreeConfig) -> dict[str, Any]:
    """Build a hierarchical tree from a Markdown file.

    Uses heading levels (``#``, ``##``, ``###``, etc.) as the structural
    backbone. Sections that exceed the token threshold receive LLM-generated
    summaries when ``config.add_node_summary`` is true.

    Args:
        md_path: Path to the Markdown file.
        config: Validated configuration object.

    Returns:
        A dict representing the root of the document tree.
    """
    with open(md_path, encoding="utf-8") as fh:
        raw = fh.read()

    root = _parse_markdown_tree(raw)

    if config.add_node_id:
        _assign_node_ids(root)

    if config.add_node_summary:
        await _annotate_summaries(root, config)

    if config.add_doc_description:
        root["description"] = await _generate_doc_description(root, config)

    return root


# ---------------------------------------------------------------------------
# Markdown parsing
# ---------------------------------------------------------------------------


def _parse_markdown_tree(text: str) -> dict[str, Any]:
    """Convert Markdown heading structure into a nested node tree.

    Heading levels map directly to tree depth: ``#`` is level 1, ``##`` is
    level 2, and so on. The content between headings becomes the node's text.
    """
    lines = text.splitlines(keepends=True)
    root: dict[str, Any] = {"title": "Document Root", "level": 0, "nodes": [], "text": ""}
    stack: list[dict[str, Any]] = [root]
    current_node = root
    line_num = 0

    for line in lines:
        line_num += 1
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)

        if heading_match:
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()

            node: dict[str, Any] = {
                "title": title,
                "level": level,
                "line_num": line_num,
                "nodes": [],
                "text": "",
            }

            # Pop back to the correct parent level.
            while len(stack) > 1 and stack[-1]["level"] >= level:
                stack.pop()

            parent = stack[-1]
            parent.setdefault("nodes", []).append(node)
            stack.append(node)
            current_node = node
        else:
            current_node["text"] = current_node.get("text", "") + line

    return root


# ---------------------------------------------------------------------------
# Summary annotation
# ---------------------------------------------------------------------------


async def _annotate_summaries(
    node: dict[str, Any], config: ReasonTreeConfig
) -> None:
    """Recursively add summaries to nodes whose text exceeds 200 tokens."""
    text = node.get("text", "")
    if count_tokens(text) > 200:
        node["summary"] = await _summarize(node.get("title", ""), text, config)

    tasks = [_annotate_summaries(child, config) for child in node.get("nodes", [])]
    if tasks:
        await asyncio.gather(*tasks)


async def _summarize(title: str, text: str, config: ReasonTreeConfig) -> str:
    prompt = f"""
Summarize the following document section in 2-3 sentences. Be specific.

Section: {title}

Content:
{text[:5000]}

Return only the summary text.
"""
    return await llm_acompletion(model=config.model, prompt=prompt)


async def _generate_doc_description(tree: dict[str, Any], config: ReasonTreeConfig) -> str:
    top_sections = [n.get("title", "") for n in tree.get("nodes", [])[:8]]
    prompt = f"""
Describe this document in 2-3 sentences based on its top-level sections:
{", ".join(top_sections)}

Return only the description text.
"""
    return await llm_acompletion(model=config.model, prompt=prompt)


# ---------------------------------------------------------------------------
# Node ID assignment
# ---------------------------------------------------------------------------


def _assign_node_ids(tree: dict[str, Any]) -> None:
    counter = [0]

    def _walk(node: dict[str, Any]) -> None:
        counter[0] += 1
        node["node_id"] = f"{counter[0]:04d}"
        for child in node.get("nodes", []):
            _walk(child)

    _walk(tree)
