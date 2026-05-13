"""Shared pytest fixtures for ReasonTree tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Sample tree fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_tree() -> dict[str, Any]:
    """A minimal two-level document tree for unit tests."""
    return {
        "title": "Document Root",
        "start_page": 1,
        "end_page": 30,
        "node_id": "0001",
        "description": "A sample annual report for testing.",
        "nodes": [
            {
                "title": "Executive Summary",
                "start_page": 1,
                "end_page": 5,
                "node_id": "0002",
                "summary": "High-level overview of the company's annual performance.",
                "nodes": [],
            },
            {
                "title": "Risk Factors",
                "start_page": 6,
                "end_page": 15,
                "node_id": "0003",
                "summary": "Detailed listing of market, operational, and regulatory risks.",
                "nodes": [
                    {
                        "title": "Market Risk",
                        "start_page": 6,
                        "end_page": 10,
                        "node_id": "0004",
                        "summary": "Exposure to interest rate and currency fluctuations.",
                        "nodes": [],
                    },
                    {
                        "title": "Regulatory Risk",
                        "start_page": 11,
                        "end_page": 15,
                        "node_id": "0005",
                        "summary": "Risk arising from changes in financial regulation.",
                        "nodes": [],
                    },
                ],
            },
            {
                "title": "Financial Statements",
                "start_page": 16,
                "end_page": 30,
                "node_id": "0006",
                "summary": "Balance sheet, income statement, and cash flow statement.",
                "nodes": [],
            },
        ],
    }


@pytest.fixture
def sample_pages() -> list[tuple[str, int]]:
    """Synthetic page content for testing text extraction helpers."""
    return [
        ("This is page one content. Annual report introduction.", 1),
        ("Page two contains executive summary details and key metrics.", 2),
        ("Page three covers risk factors including market and credit risk.", 3),
        ("Page four contains financial statements and balance sheet data.", 4),
        ("Page five concludes with notes to the financial statements.", 5),
    ]


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    """Creates a minimal valid PDF file for integration-level tests."""
    # We write a bare-minimum PDF structure that PyPDF2 can open.
    pdf_content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>stream
BT /F1 12 Tf 72 720 Td (Test page content) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000360 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    pdf_path = tmp_path / "test_document.pdf"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_markdown(tmp_path: Path) -> Path:
    """Creates a sample Markdown document for indexing tests."""
    content = """# Annual Technology Report 2025

## Executive Summary

This section provides an overview of the technology landscape.
Key trends include artificial intelligence adoption and cloud migration.

## Technical Architecture

### Data Layer

The data layer consists of distributed storage systems.
Replication factors are configured for high availability.

### Application Layer

The application layer handles business logic and API routing.
Services communicate via message queues.

## Security Considerations

Security policies are enforced at the network and application level.
Zero-trust architecture principles are applied throughout.

## Financial Overview

Capital expenditure for infrastructure totaled 45 million USD.
Operating costs decreased by 12% year over year.
"""
    md_path = tmp_path / "test_document.md"
    md_path.write_text(content, encoding="utf-8")
    return md_path


@pytest.fixture
def tree_json_file(tmp_path: Path, simple_tree: dict[str, Any]) -> Path:
    """Writes the simple_tree fixture to a JSON file on disk."""
    out = tmp_path / "test_tree.json"
    out.write_text(json.dumps(simple_tree, indent=2))
    return out


# ---------------------------------------------------------------------------
# LLM mock fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_completion():
    """Patches llm_completion to return a fixed relevance response."""
    with patch("reasontree.utils.llm_completion") as mock:
        mock.return_value = json.dumps({"relevant": True, "reasoning": "Contains relevant info."})
        yield mock


@pytest.fixture
def mock_llm_acompletion():
    """Patches llm_acompletion (async) to return a fixed summary."""
    async def fake_acompletion(model: str, prompt: str) -> str:
        return "This section discusses financial performance and market risks."

    with patch("reasontree.utils.llm_acompletion", side_effect=fake_acompletion):
        yield


@pytest.fixture
def mock_select_children():
    """Makes _select_children return all children without calling the LLM."""
    with patch("reasontree.retrieve._select_children", side_effect=lambda *a, **kw: a[1]) as mock:
        yield mock
