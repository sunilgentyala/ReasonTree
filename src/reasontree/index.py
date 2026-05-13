"""PDF tree indexing: build a hierarchical node tree from a PDF document."""

from __future__ import annotations

import json
import logging
from typing import Any

from .config import ReasonTreeConfig
from .utils import (
    count_tokens,
    extract_json,
    extract_pdf_text,
    get_pdf_page_count,
    llm_acompletion,
    llm_completion,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def build_tree_from_pdf(pdf_path: str, config: ReasonTreeConfig) -> dict[str, Any]:
    """Build a hierarchical tree index from a PDF file.

    This function orchestrates the full indexing pipeline:

    1. Extract text from all pages.
    2. Detect an existing table of contents if one is present.
    3. Build or refine the tree using the LLM.
    4. Annotate nodes with IDs and summaries as configured.

    Args:
        pdf_path: Absolute path to the PDF.
        config: Validated configuration object.

    Returns:
        A dict representing the root of the document tree.
    """
    import asyncio

    pages = extract_pdf_text(pdf_path)
    total_pages = len(pages)
    logger.info("Extracted %d pages from %s", total_pages, pdf_path)

    toc = _detect_toc(pages, config)
    if toc:
        logger.info("Existing TOC detected with %d entries", len(toc))
        tree = asyncio.run(_build_tree_from_toc(toc, pages, config))
    else:
        logger.info("No TOC detected; building tree from content")
        tree = asyncio.run(_build_tree_from_content(pages, config))

    if config.add_node_id:
        _assign_node_ids(tree)

    if config.add_doc_description:
        tree["description"] = _generate_doc_description(tree, config)

    return tree


# ---------------------------------------------------------------------------
# TOC detection
# ---------------------------------------------------------------------------


def _detect_toc(
    pages: list[tuple[str, int]], config: ReasonTreeConfig
) -> list[dict[str, Any]]:
    """Attempt to detect and parse a table of contents from the early pages."""
    check_pages = min(config.toc_check_pages, len(pages))
    sample_text = "\n---\n".join(text for text, _ in pages[:check_pages])

    prompt = f"""
You are analyzing the first {check_pages} pages of a document to find an existing table of contents.

Page content:
{sample_text}

If a table of contents exists, extract it as a JSON list. Each entry must have:
  - "title": section title (string)
  - "page": page number where the section starts (integer)
  - "level": hierarchy level starting at 1 (integer)

If no table of contents exists, return an empty list: []

Return only a valid JSON array. No explanation.
"""
    response = llm_completion(model=config.model, prompt=prompt)
    try:
        result = json.loads(response.strip())
        if isinstance(result, list) and len(result) > 2:
            return result
    except json.JSONDecodeError:
        pass
    return []


# ---------------------------------------------------------------------------
# Tree building from TOC
# ---------------------------------------------------------------------------


async def _build_tree_from_toc(
    toc: list[dict[str, Any]],
    pages: list[tuple[str, int]],
    config: ReasonTreeConfig,
) -> dict[str, Any]:
    """Convert a flat TOC into a nested tree and attach page ranges."""
    root: dict[str, Any] = {"title": "Document Root", "nodes": []}
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    total_pages = len(pages)

    for i, entry in enumerate(toc):
        level = entry.get("level", 1)
        start_page = entry.get("page", 1)
        end_page = toc[i + 1]["page"] - 1 if i + 1 < len(toc) else total_pages

        node: dict[str, Any] = {
            "title": entry["title"],
            "start_page": start_page,
            "end_page": end_page,
            "nodes": [],
        }

        if config.add_node_summary:
            node_text = " ".join(
                text for text, pg in pages if start_page <= pg <= end_page
            )
            if count_tokens(node_text) > 50:
                node["summary"] = await _summarize_node(node, node_text, config)

        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()

        parent = stack[-1][1]
        parent.setdefault("nodes", []).append(node)
        stack.append((level, node))

    return root


# ---------------------------------------------------------------------------
# Tree building from raw content
# ---------------------------------------------------------------------------


async def _build_tree_from_content(
    pages: list[tuple[str, int]], config: ReasonTreeConfig
) -> dict[str, Any]:
    """Build a tree by asking the LLM to segment the document into sections."""
    # Process in chunks that respect the token-per-node limit.
    chunks = _chunk_pages(pages, config.max_pages_per_node, config.max_tokens_per_node)

    import asyncio

    nodes = await asyncio.gather(*[_build_node_from_chunk(chunk, config) for chunk in chunks])

    return {
        "title": "Document Root",
        "start_page": 1,
        "end_page": len(pages),
        "nodes": list(nodes),
    }


async def _build_node_from_chunk(
    chunk: list[tuple[str, int]], config: ReasonTreeConfig
) -> dict[str, Any]:
    start_page = chunk[0][1]
    end_page = chunk[-1][1]
    text = "\n".join(t for t, _ in chunk)

    prompt = f"""
You are building a structured index of a document section covering pages {start_page} to {end_page}.

Text:
{text[:8000]}

Generate a JSON object representing this section:
{{
  "title": "<descriptive section title>",
  "start_page": {start_page},
  "end_page": {end_page},
  "summary": "<2-3 sentence summary of the content>"
}}

Return only valid JSON.
"""
    response = await llm_acompletion(model=config.model, prompt=prompt)
    node = extract_json(response)

    if not node.get("title"):
        node = {
            "title": f"Pages {start_page}-{end_page}",
            "start_page": start_page,
            "end_page": end_page,
        }

    node.setdefault("nodes", [])
    return node


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------


async def _summarize_node(
    node: dict[str, Any], text: str, config: ReasonTreeConfig
) -> str:
    prompt = f"""
Summarize the following document section in 2-3 sentences. Be specific and include key facts.

Section: {node.get('title', 'Unknown')}
Pages: {node.get('start_page')} - {node.get('end_page')}

Content:
{text[:6000]}

Return only the summary text, no labels or formatting.
"""
    return await llm_acompletion(model=config.model, prompt=prompt)


def _generate_doc_description(tree: dict[str, Any], config: ReasonTreeConfig) -> str:
    top_sections = [n.get("title", "") for n in tree.get("nodes", [])[:10]]
    prompt = f"""
Describe this document in 2-3 sentences based on its top-level sections.

Sections: {", ".join(top_sections)}

Return only the description.
"""
    result = llm_completion(model=config.model, prompt=prompt)
    return str(result)


# ---------------------------------------------------------------------------
# Node ID assignment
# ---------------------------------------------------------------------------


def _assign_node_ids(tree: dict[str, Any], prefix: str = "") -> None:
    """Walk the tree and assign sequential IDs to every node."""
    counter = [0]

    def _walk(node: dict[str, Any]) -> None:
        counter[0] += 1
        node["node_id"] = f"{counter[0]:04d}"
        for child in node.get("nodes", []):
            _walk(child)

    _walk(tree)


# ---------------------------------------------------------------------------
# Page chunking helper
# ---------------------------------------------------------------------------


def _chunk_pages(
    pages: list[tuple[str, int]],
    max_pages: int,
    max_tokens: int,
) -> list[list[tuple[str, int]]]:
    """Group pages into chunks that respect both page count and token limits."""
    chunks: list[list[tuple[str, int]]] = []
    current: list[tuple[str, int]] = []
    current_tokens = 0

    for page_text, page_num in pages:
        page_tokens = count_tokens(page_text)
        if current and (len(current) >= max_pages or current_tokens + page_tokens > max_tokens):
            chunks.append(current)
            current = []
            current_tokens = 0
        current.append((page_text, page_num))
        current_tokens += page_tokens

    if current:
        chunks.append(current)

    return chunks
