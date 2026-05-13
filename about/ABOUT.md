# About ReasonTree

## Origin

This project grew out of frustration with a specific class of failure in production RAG systems. Vector similarity search works well enough for factoid questions over general-purpose corpora, but it falls apart systematically when the documents are long, structurally complex, or domain-specific in ways that require domain knowledge to interpret correctly.

The failure mode is always the same. The user asks a question. The retriever finds passages that contain some of the same words. The LLM answers confidently from those passages. The answer is wrong, or incomplete, or misses a qualification on page 47 that changes everything. The vector store did its job technically and still delivered a bad result, because similarity is not relevance.

The core observation behind ReasonTree is that human experts do not retrieve by similarity. A securities analyst looking for a specific risk disclosure does not scan a 200-page 10-K for sentences that sound similar to the question. They know how annual reports are structured, they go to the risk factors section, and they read carefully. The retrieval is guided by structural knowledge and reasoning, not text distance.

ReasonTree attempts to encode that behavior. It builds a tree that represents the document's structure, and it uses a language model to reason over that tree during retrieval. The model does not look up; it navigates.

## Design Goals

**Traceability above all.** Every retrieval result should come with an explanation of how the system got there. Which branches of the tree did it explore? Which did it prune and why? What did it read at each node? A system that produces correct answers opaquely is hard to debug, hard to trust, and impossible to improve systematically.

**Structure as signal.** Document structure is not decoration. Section headers, hierarchy, page ranges, and the relationships between sections carry semantic information that flat chunking destroys. ReasonTree preserves this structure and uses it actively during both indexing and retrieval.

**No permanent infrastructure dependency.** Vector databases are a fine tool for certain problems, but they introduce operational overhead, require embedding pipelines, and create a layer of indirection between the document and the retrieval result. ReasonTree produces a JSON tree that you can inspect, store, version, and diff. There is no daemon to run, no index to maintain, and no embedding model to keep synchronized.

**Provider agnosticism.** The system routes all LLM calls through LiteLLM, which means you can swap the underlying model without changing application code. This matters because the best model for indexing may not be the best model for retrieval, and the best models change over time.

**Honest limitations.** ReasonTree does not do magic. It works better on documents with clear structure and worse on documents that are effectively walls of unformatted text. Standard PDF text extraction is imperfect; scanned documents or complex layouts will produce noisier trees. These limitations are documented honestly rather than glossed over.

## What ReasonTree Is Not

It is not a replacement for all vector-based RAG. For retrieval over large, loosely structured corpora of short documents, vector search is often the right tool.

It is not an autonomous research agent. It retrieves. The decision about what to do with the retrieved content is left to the application layer.

It is not production-hardened infrastructure. It is a research-grade framework that has been used in real applications, but it has not been hardened for high-throughput, multi-tenant production use without additional work.

## Name

The name combines two words that describe what the system does. "Reason" because retrieval is driven by LLM reasoning rather than vector lookup. "Tree" because the document index is a tree structure that the reasoning process navigates. It is a short name that is accurate rather than clever.

An earlier working name was "DocNavigator," which was accurate but bland. "StructRAG" was considered but felt like it could mean anything. "ReasonTree" won because it points at the two things that distinguish this approach from the baseline.
