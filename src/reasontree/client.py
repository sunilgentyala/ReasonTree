"""High-level client API for ReasonTree.

Typical usage::

    from reasontree import ReasonTreeClient

    client = ReasonTreeClient(api_key="sk-...")
    doc_id = client.index("report.pdf")
    result = client.retrieve(doc_id, "What are the key risk factors?")
    print(result.content)
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .config import ReasonTreeConfig, load_config
from .utils import remove_fields


@dataclass
class IndexResult:
    """Result of indexing a document.

    Attributes:
        doc_id: Stable identifier for this document within the workspace.
        path: Absolute path to the source file.
        tree: The full tree structure as a Python dict.
        node_count: Total number of nodes in the tree.
    """

    doc_id: str
    path: str
    tree: dict[str, Any]
    node_count: int


@dataclass
class RetrievalResult:
    """Result of a retrieval query.

    Attributes:
        pages: List of page numbers (1-indexed) that the tree search identified
            as relevant.
        content: Extracted text from those pages, concatenated.
        reasoning: The node-by-node decision trail from the tree search.
        node_ids: IDs of the nodes that were retrieved.
    """

    pages: list[int]
    content: str
    reasoning: list[dict[str, Any]] = field(default_factory=list)
    node_ids: list[str] = field(default_factory=list)


class ReasonTreeClient:
    """Entry point for indexing documents and running retrieval queries.

    Args:
        api_key: OpenAI API key. Falls back to the ``OPENAI_API_KEY`` environment
            variable when not provided.
        model: LLM to use for indexing. Overrides the config file value.
        retrieve_model: LLM to use for retrieval. Defaults to ``model``.
        workspace: Directory for persisting indexed documents across sessions.
            When ``None`` documents are held in memory only.
        config: A pre-built :class:`ReasonTreeConfig`. When supplied, ``model``
            and ``retrieve_model`` arguments are ignored.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        retrieve_model: Optional[str] = None,
        workspace: Optional[str] = None,
        config: Optional[ReasonTreeConfig] = None,
    ) -> None:
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key

        if config is not None:
            self.config = config
        else:
            overrides: dict[str, Any] = {}
            if model:
                overrides["model"] = model
            if retrieve_model:
                overrides["retrieve_model"] = retrieve_model
            self.config = load_config(overrides or None)

        self._workspace: Optional[Path] = (
            Path(workspace).expanduser() if workspace else None
        )
        if self._workspace:
            self._workspace.mkdir(parents=True, exist_ok=True)

        self._documents: dict[str, dict[str, Any]] = {}
        if self._workspace:
            self._load_workspace()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def index(self, file_path: str, mode: str = "auto") -> str:
        """Index a document and return a ``doc_id`` for later retrieval.

        Args:
            file_path: Path to a PDF or Markdown file.
            mode: ``"pdf"``, ``"markdown"``, or ``"auto"`` (detects by extension).

        Returns:
            A string ``doc_id`` that identifies this document in the workspace.
        """
        from .index import build_tree_from_pdf
        from .index_md import build_tree_from_markdown

        abs_path = os.path.abspath(os.path.expanduser(file_path))
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"File not found: {abs_path}")

        ext = Path(abs_path).suffix.lower()
        is_pdf = ext == ".pdf"
        is_md = ext in (".md", ".markdown")

        if mode == "pdf" or (mode == "auto" and is_pdf):
            print(f"Indexing PDF: {abs_path}")
            tree = build_tree_from_pdf(abs_path, self.config)
        elif mode == "markdown" or (mode == "auto" and is_md):
            print(f"Indexing Markdown: {abs_path}")
            import asyncio
            tree = asyncio.run(build_tree_from_markdown(abs_path, self.config))
        else:
            raise ValueError(
                f"Cannot determine file type for '{abs_path}'. "
                "Pass mode='pdf' or mode='markdown' explicitly."
            )

        doc_id = str(uuid.uuid4())
        self._documents[doc_id] = {"path": abs_path, "tree": tree}

        if self._workspace:
            self._save_document(doc_id)

        print(f"Indexed successfully. doc_id={doc_id}")
        return doc_id

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(
        self,
        doc_id: str,
        query: str,
        context: Optional[str] = None,
    ) -> RetrievalResult:
        """Run a retrieval query against an indexed document.

        Args:
            doc_id: The identifier returned by :meth:`index`.
            query: The question or information need.
            context: Optional extra context (e.g. conversation history, domain
                notes) to pass to the LLM navigator.

        Returns:
            A :class:`RetrievalResult` with pages, content, and reasoning.
        """
        from .retrieve import tree_search

        doc = self._get_document(doc_id)
        return tree_search(
            tree=doc["tree"],
            file_path=doc["path"],
            query=query,
            context=context,
            model=self.config.effective_retrieve_model,
        )

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    def list_documents(self) -> list[dict[str, str]]:
        """Return a summary of all indexed documents in this client instance."""
        return [
            {"doc_id": did, "path": meta["path"]}
            for did, meta in self._documents.items()
        ]

    def get_tree(self, doc_id: str, strip_text: bool = True) -> dict[str, Any]:
        """Return the tree structure for a document.

        Args:
            doc_id: Document identifier.
            strip_text: When ``True``, remove embedded node text to keep the
                response small. Useful for inspection.
        """
        doc = self._get_document(doc_id)
        tree = doc["tree"]
        if strip_text:
            return remove_fields(tree, ["text"])
        return tree

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_document(self, doc_id: str) -> dict[str, Any]:
        if doc_id not in self._documents:
            raise KeyError(
                f"No document with id '{doc_id}'. "
                "Index a document first with client.index()."
            )
        return self._documents[doc_id]

    def _save_document(self, doc_id: str) -> None:
        assert self._workspace is not None
        out_path = self._workspace / f"{doc_id}.json"
        with out_path.open("w") as fh:
            json.dump(self._documents[doc_id], fh, indent=2)

    def _load_workspace(self) -> None:
        assert self._workspace is not None
        for json_file in self._workspace.glob("*.json"):
            if json_file.name == "_meta.json":
                continue
            try:
                with json_file.open() as fh:
                    data = json.load(fh)
                doc_id = json_file.stem
                self._documents[doc_id] = data
            except (json.JSONDecodeError, KeyError):
                pass  # Corrupted file; skip silently.
