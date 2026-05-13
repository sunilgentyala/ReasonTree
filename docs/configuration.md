# Configuration Reference

All configuration values have defaults set in `src/reasontree/config.yaml`. You can override them in three ways, in increasing priority order:

1. Edit `config.yaml` for persistent defaults.
2. Pass a custom YAML path to `load_config(config_path=...)`.
3. Pass overrides as keyword arguments when constructing `ReasonTreeClient`.

---

## All Parameters

### model

Type: `str`
Default: `"gpt-4o-2024-11-20"`

The LLM used during the indexing phase (TOC detection, section title generation, summary generation). You can use any LiteLLM-supported model identifier. For non-OpenAI providers, use the full LiteLLM format: `"anthropic/claude-opus-4-7"`, `"groq/llama3-70b-8192"`, etc.

This model is also used for retrieval if `retrieve_model` is not set.

---

### retrieve_model

Type: `str | null`
Default: `null` (falls back to `model`)

The LLM used during retrieval (tree navigation and leaf evaluation). Set this when you want a different model for retrieval than for indexing. For example, you might use a large model for high-quality indexing and a smaller, faster model for retrieval.

```yaml
model: "gpt-4o-2024-11-20"
retrieve_model: "gpt-4o-mini"
```

---

### toc_check_pages

Type: `int`
Default: `20`
Minimum: `1`

How many pages from the beginning of the document to scan when looking for an existing table of contents. Increasing this helps for documents where the TOC appears later in the front matter, but it also means more text is sent to the LLM in a single call.

---

### max_pages_per_node

Type: `int`
Default: `10`
Minimum: `1`

When no TOC is detected, the indexer groups pages into chunks. This sets the maximum number of pages per chunk. Smaller values produce a more granular tree with more nodes; larger values produce a flatter tree with fewer but larger nodes.

---

### max_tokens_per_node

Type: `int`
Default: `20000`
Minimum: `100`

The token ceiling for text within a single node during indexing. When adding pages to a chunk would exceed this limit, the current chunk is closed and a new one begins, even if `max_pages_per_node` has not been reached. This prevents sending excessively long prompts to the LLM.

---

### add_node_summary

Type: `bool`
Default: `true`

When true, the indexer generates a 2-3 sentence summary for each node using the LLM. Summaries are used during retrieval to help the LLM make routing decisions without reading full page content. Disabling summaries reduces indexing cost but may degrade retrieval quality on documents with complex structure.

---

### add_node_id

Type: `bool`
Default: `true`

When true, assigns a sequential four-digit ID to every node (`"0001"`, `"0002"`, etc.). Node IDs are included in retrieval results and make it easy to identify which specific nodes contributed to a result.

---

### add_doc_description

Type: `bool`
Default: `false`

When true, generates a top-level description of the entire document. Useful for building document indices where you need a human-readable summary of what each document covers, but not necessary for retrieval itself.

---

### add_node_text

Type: `bool`
Default: `false`

When true, includes the full extracted text of each section within the node. This makes tree files significantly larger but makes it possible to answer queries from the tree alone without accessing the original PDF during retrieval. Useful when the source document may not always be available.

---

## Configuration in Code

```python
from reasontree import ReasonTreeClient, ReasonTreeConfig, load_config

# Option 1: pass model args to the client
client = ReasonTreeClient(
    model="gpt-4o",
    retrieve_model="gpt-4o-mini",
)

# Option 2: build a config manually and pass it
config = ReasonTreeConfig(
    model="anthropic/claude-opus-4-7",
    toc_check_pages=30,
    add_doc_description=True,
)
client = ReasonTreeClient(config=config)

# Option 3: load from a custom YAML file
from pathlib import Path
config = load_config(config_path=Path("/path/to/my_config.yaml"))
client = ReasonTreeClient(config=config)
```

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key (for Claude models) |
| `CHATGPT_API_KEY` | Legacy alias for `OPENAI_API_KEY` |
| Any LiteLLM-supported key | See LiteLLM docs for the full list |
