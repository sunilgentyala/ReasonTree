# ReasonTree Architecture

## System overview

```
Input Document (PDF or Markdown)
         |
         v
  +------+------+
  |   Indexer   |  (index.py / index_md.py)
  +------+------+
         |
         | Extracts text, detects structure
         v
  +------+------+
  |  LLM calls  |  (utils.py -> LiteLLM -> any provider)
  +------+------+
         |
         | Generates titles, summaries, node IDs
         v
  +------+------+
  |  Tree (JSON)|  Hierarchical nodes, each with:
  |             |  - title
  +------+------+  - start_page / end_page (or line_num for MD)
         |          - optional summary
         |          - optional node text
         | Saved to disk (workspace) or held in memory
         |
         v  (at query time)
  +------+------+
  |  Retriever  |  (retrieve.py)
  |  tree_search|
  +------+------+
         |
         | Walks tree, asks LLM at each branch:
         | "Which children are relevant to this query?"
         v
  +------+------+
  |  LLM calls  |  _select_children() and _evaluate_node()
  +------+------+
         |
         | Returns list of relevant leaf nodes
         v
  +------+------+
  | Page extract|  _extract_pages() -> PyPDF2
  +------+------+
         |
         v
  RetrievalResult
  - pages: [list of page numbers]
  - content: "extracted text"
  - reasoning: [{node, decision, why}]
  - node_ids: ["0004", "0007"]
```

## Module responsibilities

**config.py**
Owns all configuration. Pydantic model ensures values are validated at
load time. load_config() merges YAML defaults with caller overrides.

**utils.py**
All LLM communication goes through here. llm_completion() and
llm_acompletion() handle retries and provider prefix normalization.
extract_json() handles the common case of an LLM wrapping JSON in
markdown fences or surrounding prose.

**index.py**
PDF-specific indexing. Detects whether an existing TOC is present
and uses it if so; falls back to LLM-based content segmentation for
documents without one. Calls are async and run concurrently for
large documents.

**index_md.py**
Markdown-specific indexing. Uses heading levels as the structural
backbone rather than LLM segmentation, which is faster and cheaper.
LLM is used only for summary generation.

**retrieve.py**
Implements the tree search algorithm. _select_children() asks the
LLM which subtrees to explore at each branch. _evaluate_node()
makes the final relevance judgment at each leaf. The search is
depth-limited to prevent runaway recursion on very deep trees.

**client.py**
High-level API. Manages the document registry, handles workspace
persistence, and exposes index() and retrieve() as the primary
entry points.

## Data flow in detail

1. User calls client.index("report.pdf")
2. Client calls build_tree_from_pdf(path, config)
3. Indexer extracts all page text via PyMuPDF
4. Indexer scans first N pages for a TOC
5. If TOC found: parse it and assign page ranges to nodes
   If no TOC: chunk pages by max_pages_per_node and ask LLM to
   name and describe each chunk
6. For each node, optionally call LLM to generate a summary
7. Walk the completed tree and assign sequential node_ids
8. Return tree dict; client stores it (and optionally saves to workspace)

9. User calls client.retrieve(doc_id, "query")
10. Client calls tree_search(tree, path, query, model)
11. Start at root node
12. If node has children: call _select_children(node, children, query)
    -> LLM returns list of indices of relevant children
    -> Recurse into each selected child
13. If node has no children (leaf): call _evaluate_node(node, query)
    -> LLM returns {"relevant": true/false, "reasoning": "..."}
    -> If relevant, add to results list
14. Collect all pages from relevant nodes
15. Extract text from those pages via PyPDF2
16. Return RetrievalResult

## Concurrency model

Indexing uses asyncio for concurrent LLM calls when generating summaries
for multiple nodes. The main event loop is driven by asyncio.run() at the
top level, which means the indexer is safe to call from synchronous code.

The retrieval tree search is currently synchronous and recursive. The
depth limit (_MAX_SEARCH_DEPTH = 6) prevents stack overflow on pathological
inputs. A future version may parallelize sibling branch exploration.
