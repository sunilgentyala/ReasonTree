# How ReasonTree Works

This document explains the two-phase pipeline in enough detail to understand why the system behaves the way it does, and what to expect when you change the inputs.

---

## Phase 1: Building the Tree Index

The goal of indexing is to produce a hierarchical representation of the document's structure. The output is a JSON tree where each node represents a document section, and each node knows its page range, a human-readable title, and an optional summary of its content.

### Step 1: Text Extraction

For PDFs, ReasonTree uses PyMuPDF (pymupdf) to extract text page by page. PyMuPDF generally handles text-based PDFs well, including multi-column layouts, though it cannot handle scanned images or PDFs with complex embedded graphics correctly. This is a known limitation of open-source PDF extraction.

For Markdown files, the file is read directly. No text extraction is needed.

### Step 2: TOC Detection (PDF only)

Before trying to infer structure from content, the indexer scans the first N pages (configurable via `toc_check_pages`, default 20) to check whether the document already has an explicit table of contents. It sends this page content to the LLM and asks it to extract TOC entries in a structured format.

If a usable TOC is found (more than 2 entries), the indexer uses it to build the tree directly, which is faster and more accurate than content-based segmentation. If no TOC is found, the system falls back to content-based segmentation.

### Step 3: Tree Construction

**If a TOC exists:** The flat list of TOC entries is converted into a nested tree by tracking heading levels. Each section's page range is inferred from the start page of the next entry. The LLM is called once per node to generate a summary (if enabled).

**If no TOC:** Pages are grouped into chunks that respect both the `max_pages_per_node` limit and the `max_tokens_per_node` limit. Each chunk is sent to the LLM, which generates a title and summary for that section. These chunks become the leaf nodes of the tree. Note that without a TOC, the tree is typically shallower, often just one level deep.

**For Markdown:** The tree is built directly from heading levels. `#` headings become level-1 nodes, `##` become their children, and so on. The LLM is called only for summaries.

### Step 4: Annotation

After the tree structure is built, the indexer optionally:
- Assigns sequential node IDs to every node (`add_node_id: true`)
- Generates a top-level document description (`add_doc_description: true`)
- Stores extracted text within each node (`add_node_text: true`)

---

## Phase 2: Tree Search Retrieval

Given a query and a document tree, the retrieval engine finds the specific pages most likely to contain a relevant answer. It does this by walking the tree from the root, using the LLM as a navigator at each branch.

### The Core Loop

At each internal node (a node with children), the engine calls `_select_children()`. This function:

1. Formats a prompt that includes the current query, any additional context, and a summary of each child node (title, page range, summary).
2. Asks the LLM which children are worth exploring.
3. Returns only the selected children.

The engine then recurses into each selected child. If a child has its own children, the loop repeats. If a child is a leaf (no children), the engine calls `_evaluate_node()`.

At a leaf node, `_evaluate_node()` asks the LLM: given the query and the node's summary and content, is this section actually relevant? If yes, the node is added to the result set.

### Why Two Steps?

`_select_children()` is a coarse-grained filter that prunes the search space. It operates on summaries, which are small. `_evaluate_node()` is a fine-grained judgment that has access to the actual page content. Separating them allows the system to be cheap at the branch level and thorough at the leaf level.

### What the Reasoning Trail Shows

Every call to `_select_children()` and `_evaluate_node()` adds an entry to the reasoning trail. This trail records:
- Which node was evaluated
- Which children were selected (for internal nodes) or whether the node was deemed relevant (for leaves)
- The LLM's reasoning text

This trail is returned with every retrieval result. Inspecting it tells you exactly which branches of the tree the system explored and why it made the decisions it did. When a retrieval result is wrong, the trail usually shows you where the navigation went astray.

### Depth Limit

Tree search is depth-limited to 6 levels to prevent unbounded recursion on very deep trees. In practice, most professional documents have 3-4 levels of hierarchy, so this limit is rarely reached.

---

## Practical Implications

**Query specificity helps.** A specific query like "What was the net interest margin in Q3 2023?" gives the LLM enough signal to navigate directly to the financial statements section. A vague query like "financials" may cause the system to explore more branches than necessary.

**Summaries matter more than you might expect.** The tree search makes decisions based on node summaries, not raw page text. A high-quality summary allows the system to confidently prune irrelevant branches. A low-quality or missing summary may cause the system to be overly cautious and explore more of the tree, which costs more LLM calls.

**Context improves routing.** The optional `context` parameter is passed to every LLM call during retrieval. If you are answering a follow-up question in a conversation, passing the prior conversation history as context allows the system to navigate with that background in mind.

**Indexing cost is paid once.** The expensive part (calling the LLM to generate titles and summaries) happens during indexing. Once a document is indexed and saved to a workspace, retrieval costs only the tree search LLM calls, which are typically much cheaper than re-processing the document.
