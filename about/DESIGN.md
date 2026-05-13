# Design Decisions

This document records the significant design choices made in ReasonTree and the reasoning behind them. Recording these decisions matters because the tempting alternative often exists and was explicitly considered.

---

## Tree as the Index Representation

**Decision:** Represent a document index as a JSON tree where each node holds a title, page range, optional summary, and child nodes.

**Alternatives considered:** Flat list of chunks (standard RAG), directed acyclic graph, hierarchical cluster embeddings.

**Why the tree won:** Professional documents have natural hierarchical structure. A regulatory filing has parts, each part has sections, each section has subsections. This is not an approximation; it is how the document was written. Encoding this structure faithfully preserves information that flat chunking discards, specifically the parent-child and sibling relationships between sections.

A graph was considered and rejected because it adds retrieval complexity without a clear benefit for the document types ReasonTree targets. Graphs make sense when relationships between nodes are non-hierarchical and cross-cutting, but document section relationships are predominantly hierarchical.

---

## LLM as Navigator, Not Just Generator

**Decision:** Use the LLM during retrieval to reason over the tree, deciding which branches to explore. The LLM is a navigating agent, not just a text generator called at the end.

**Alternatives considered:** Rule-based tree traversal using keyword matching, embedding-based node selection, BFS/DFS without LLM guidance.

**Why this won:** The queries that matter most for professional document QA are the ones where the answer is not obviously co-located with the question vocabulary. A question about "counterparty credit risk exposure" in a loan agreement may live in a section titled "Third-Party Obligations." A keyword match would fail. An embedding match might succeed or fail depending on the training distribution. LLM reasoning, given a node summary and the question with context, can recognize the semantic match even across large surface-level gaps.

The cost is LLM calls per retrieval, which is real but acceptable for the document types this system targets. These are not web search queries; they are analytical questions over important professional documents where accuracy matters more than milliseconds.

---

## LiteLLM for All LLM Calls

**Decision:** Route every LLM call through LiteLLM rather than calling provider SDKs directly.

**Alternatives considered:** Direct OpenAI SDK usage, provider-specific adapters, writing our own thin abstraction.

**Why this won:** LiteLLM has already solved the provider normalization problem, handles retries and rate limiting, and supports 100+ providers behind a single interface. Writing our own abstraction would duplicate that work and fall behind as the provider landscape changes. The tradeoff is a dependency on a third-party library, but LiteLLM is well-maintained and its interface is stable.

---

## JSON as the Tree Storage Format

**Decision:** Store the generated tree as a human-readable JSON file.

**Alternatives considered:** SQLite database, pickle, binary formats, proprietary formats.

**Why JSON won:** A JSON file is readable by a human with a text editor. It can be versioned in git, diffed to see what changed, shared as an attachment, loaded by any language, and inspected without any special tools. These are valuable properties when debugging retrieval failures or auditing document processing.

The size cost is real for very large documents, but the trees we generate are small compared to the source PDFs. A 500-page document typically produces a tree of a few hundred kilobytes.

---

## No Built-in Vector Fallback

**Decision:** ReasonTree does not include a vector search fallback or hybrid retrieval mode.

**Alternatives considered:** Hybrid mode that uses vector search when tree traversal confidence is low, optional embedding pipeline.

**Why we skipped it:** Hybrid retrieval complicates the system without a proven benefit on the document types this system targets. Adding vector fallback would require an embedding model, a vector store, and the additional configuration surface area that comes with both. It would also muddy the experimental clarity: when a result is good, was it the tree search or the vector fallback?

If a user wants hybrid retrieval, they can build it at the application layer by calling ReasonTree and a vector store independently and merging results. The framework does not need to own that decision.

---

## Type Annotations Throughout

**Decision:** All public functions and methods are fully type-annotated. Internal helpers use annotations where they aid clarity.

**Alternatives considered:** No annotations (Python 2 style), partial annotations only on public API.

**Why full annotations:** Type annotations make it possible to run a static type checker like mypy or pyright in CI, which catches a class of bugs before code is run. They also serve as machine-checkable documentation. A function signature with proper types is more reliable than a docstring that may be out of date.

---

## Configuration via YAML with Pydantic Validation

**Decision:** Read configuration from a YAML file and validate it at load time using Pydantic.

**Alternatives considered:** `config.py` with Python constants, environment variables only, INI file.

**Why YAML plus Pydantic:** YAML is readable and supports comments, which matters for configuration that needs explanation. Pydantic validation means that a misconfigured value fails loudly at startup rather than silently producing wrong results at retrieval time. Together they give a clean configuration experience without writing a custom parser.

---

## Separate Index and Retrieve Models

**Decision:** Allow different LLM models for indexing and retrieval.

**Alternatives considered:** Single model for all operations.

**Why separate:** Indexing a document is a batch operation done once. Retrieval happens in the request path and may be latency-sensitive. A user may want to use a larger, slower model for high-quality index generation but a faster model for retrieval, or vice versa. Forcing a single model removes that flexibility without any corresponding benefit.
