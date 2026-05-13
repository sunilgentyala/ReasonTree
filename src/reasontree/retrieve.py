"""Tree search retrieval engine.

Given a document tree and a query, navigates the tree using LLM reasoning to
identify the most relevant pages and return their content.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import PyPDF2

from .client import RetrievalResult
from .utils import extract_json, llm_completion

logger = logging.getLogger(__name__)

_MAX_SEARCH_DEPTH = 6


def tree_search(
    tree: dict[str, Any],
    file_path: str,
    query: str,
    context: Optional[str] = None,
    model: str = "gpt-4o-2024-11-20",
) -> RetrievalResult:
    """Navigate the document tree using LLM reasoning to find relevant pages.

    The search starts at the root and descends branch by branch. At each node,
    the LLM decides whether the subtree is worth exploring based on the node's
    title and summary. When it reaches a leaf or a node small enough to read
    directly, it checks whether the content is genuinely relevant.

    Args:
        tree: The root node dict from the indexing step.
        file_path: Path to the original PDF (used for text extraction).
        query: The user's information need.
        context: Optional additional context passed to the LLM at each step.
        model: LiteLLM model identifier for retrieval.

    Returns:
        A :class:`RetrievalResult` with pages, text content, and decision trail.
    """
    relevant_nodes: list[dict[str, Any]] = []
    reasoning_trail: list[dict[str, Any]] = []

    _search_node(
        node=tree,
        query=query,
        context=context,
        model=model,
        relevant_nodes=relevant_nodes,
        reasoning_trail=reasoning_trail,
        depth=0,
    )

    if not relevant_nodes:
        return RetrievalResult(pages=[], content="", reasoning=reasoning_trail)

    pages = sorted(
        set(
            p
            for node in relevant_nodes
            for p in range(node.get("start_page", 1), node.get("end_page", 1) + 1)
        )
    )

    content = _extract_pages(file_path, pages)
    node_ids = [n.get("node_id", "") for n in relevant_nodes if n.get("node_id")]

    return RetrievalResult(
        pages=pages,
        content=content,
        reasoning=reasoning_trail,
        node_ids=node_ids,
    )


# ---------------------------------------------------------------------------
# Recursive node search
# ---------------------------------------------------------------------------


def _search_node(
    node: dict[str, Any],
    query: str,
    context: Optional[str],
    model: str,
    relevant_nodes: list[dict[str, Any]],
    reasoning_trail: list[dict[str, Any]],
    depth: int,
) -> None:
    if depth > _MAX_SEARCH_DEPTH:
        return

    children = node.get("nodes", [])

    # Leaf node or node without further subdivision: evaluate directly.
    if not children:
        decision = _evaluate_node(node, query, context, model)
        reasoning_trail.append(decision)
        if decision.get("relevant"):
            relevant_nodes.append(node)
        return

    # Internal node: ask the LLM which children are worth exploring.
    relevant_children = _select_children(node, children, query, context, model)
    reasoning_trail.append(
        {
            "node": node.get("title"),
            "depth": depth,
            "selected_children": [c.get("title") for c in relevant_children],
        }
    )

    for child in relevant_children:
        _search_node(
            node=child,
            query=query,
            context=context,
            model=model,
            relevant_nodes=relevant_nodes,
            reasoning_trail=reasoning_trail,
            depth=depth + 1,
        )


def _select_children(
    parent: dict[str, Any],
    children: list[dict[str, Any]],
    query: str,
    context: Optional[str],
    model: str,
) -> list[dict[str, Any]]:
    """Ask the LLM to select which child nodes are relevant to the query."""
    child_summaries = "\n".join(
        f"[{i}] {c.get('title', 'Untitled')} "
        f"(pages {c.get('start_page')}-{c.get('end_page')}): "
        f"{c.get('summary', 'No summary available.')}"
        for i, c in enumerate(children)
    )

    context_block = f"\nAdditional context: {context}" if context else ""

    prompt = f"""
You are navigating a document tree to answer a query. You are currently at section:
"{parent.get('title', 'Root')}"

The query is: {query}{context_block}

The child sections are:
{child_summaries}

Which of these sections might contain information relevant to the query?
Return a JSON object:
{{
  "relevant_indices": [list of integer indices from the list above],
  "reasoning": "brief explanation"
}}

Be inclusive when uncertain. Return only valid JSON.
"""
    response = llm_completion(model=model, prompt=prompt)
    result = extract_json(response)
    indices = result.get("relevant_indices", list(range(len(children))))

    valid_indices = [i for i in indices if isinstance(i, int) and 0 <= i < len(children)]
    return [children[i] for i in valid_indices]


def _evaluate_node(
    node: dict[str, Any],
    query: str,
    context: Optional[str],
    model: str,
) -> dict[str, Any]:
    """Determine if a leaf node is relevant to the query."""
    context_block = f"\nAdditional context: {context}" if context else ""
    text_preview = (node.get("text") or node.get("summary") or "")[:3000]

    prompt = f"""
You are evaluating whether a document section contains information relevant to a query.

Query: {query}{context_block}

Section: {node.get('title', 'Untitled')} (pages {node.get('start_page')}-{node.get('end_page')})
Summary: {node.get('summary', 'Not available.')}
Content preview: {text_preview}

Is this section relevant to the query?
Return JSON:
{{
  "relevant": true or false,
  "reasoning": "brief explanation"
}}
"""
    response = llm_completion(model=model, prompt=prompt)
    result = extract_json(response)
    result["node"] = node.get("title")
    result["pages"] = f"{node.get('start_page')}-{node.get('end_page')}"
    return result


# ---------------------------------------------------------------------------
# Page text extraction
# ---------------------------------------------------------------------------


def _extract_pages(file_path: str, pages: list[int]) -> str:
    """Extract and concatenate text from the specified pages of a PDF."""
    try:
        with open(file_path, "rb") as fh:
            reader = PyPDF2.PdfReader(fh)
            total = len(reader.pages)
            parts: list[str] = []
            for page_num in pages:
                if 1 <= page_num <= total:
                    text = reader.pages[page_num - 1].extract_text() or ""
                    parts.append(f"[Page {page_num}]\n{text}")
            return "\n\n".join(parts)
    except Exception as exc:
        logger.error("Failed to extract pages from %s: %s", file_path, exc)
        return ""
