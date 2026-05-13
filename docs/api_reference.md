# API Reference

This page documents every public class and function in ReasonTree.

---

## ReasonTreeClient

The primary entry point for all indexing and retrieval operations.

```python
from reasontree import ReasonTreeClient
```

### Constructor

```python
ReasonTreeClient(
    api_key: str | None = None,
    model: str | None = None,
    retrieve_model: str | None = None,
    workspace: str | None = None,
    config: ReasonTreeConfig | None = None,
)
```

**Parameters:**

- `api_key`: OpenAI API key. Falls back to the `OPENAI_API_KEY` environment variable.
- `model`: LLM for indexing. Overrides the config file default.
- `retrieve_model`: LLM for retrieval. Falls back to `model` if not set.
- `workspace`: Directory for persisting indexed documents across Python sessions. Created automatically if it does not exist. When `None`, documents are held in memory only.
- `config`: A pre-built `ReasonTreeConfig` instance. When supplied, the `model` and `retrieve_model` arguments are ignored.

---

### index

```python
def index(file_path: str, mode: str = "auto") -> str
```

Index a document. Returns a `doc_id` string.

**Parameters:**

- `file_path`: Path to a PDF or Markdown file. Relative paths are resolved against the current working directory.
- `mode`: `"pdf"`, `"markdown"`, or `"auto"`. In auto mode the file extension determines the parser.

**Returns:** A `doc_id` string (UUID) that identifies the document in this client's registry. Pass it to `retrieve()` and `get_tree()`.

**Raises:**
- `FileNotFoundError` if the file does not exist.
- `ValueError` if the file type cannot be determined in auto mode.

---

### retrieve

```python
def retrieve(
    doc_id: str,
    query: str,
    context: str | None = None,
) -> RetrievalResult
```

Run a retrieval query against an indexed document.

**Parameters:**

- `doc_id`: The identifier returned by `index()`.
- `query`: The question or information need.
- `context`: Optional extra context (conversation history, domain notes) passed to the LLM at every navigation step.

**Returns:** A `RetrievalResult`.

**Raises:** `KeyError` if `doc_id` is not found.

---

### get_tree

```python
def get_tree(doc_id: str, strip_text: bool = True) -> dict
```

Return the raw tree structure for a document.

**Parameters:**

- `doc_id`: Document identifier.
- `strip_text`: When `True` (default), removes embedded node text. This keeps the output small for inspection and logging.

**Raises:** `KeyError` if `doc_id` is not found.

---

### list_documents

```python
def list_documents() -> list[dict[str, str]]
```

Return a list of all indexed documents. Each entry is a dict with `doc_id` and `path`.

---

## RetrievalResult

```python
from reasontree import RetrievalResult
```

Returned by `ReasonTreeClient.retrieve()`.

**Attributes:**

- `pages: list[int]` - Sorted list of 1-indexed page numbers.
- `content: str` - Extracted text from those pages, concatenated with page markers.
- `reasoning: list[dict]` - The node-by-node decision trail from the tree search.
- `node_ids: list[str]` - IDs of the nodes that were retrieved.

---

## IndexResult

```python
from reasontree import IndexResult
```

Returned by low-level indexing functions (not by `ReasonTreeClient.index()` directly, which returns a `doc_id` string). Available for programmatic use when you need metadata about the indexed document.

**Attributes:**

- `doc_id: str`
- `path: str`
- `tree: dict` - The full tree structure.
- `node_count: int` - Total number of nodes.

---

## ReasonTreeConfig

```python
from reasontree import ReasonTreeConfig
```

Validated configuration model using Pydantic.

| Field | Type | Default | Description |
|---|---|---|---|
| `model` | `str` | `"gpt-4o-2024-11-20"` | LLM for indexing |
| `retrieve_model` | `str \| None` | `None` | LLM for retrieval (falls back to model) |
| `toc_check_pages` | `int` | `20` | Pages scanned for TOC detection |
| `max_pages_per_node` | `int` | `10` | Max page span per node |
| `max_tokens_per_node` | `int` | `20000` | Token ceiling per node |
| `add_node_summary` | `bool` | `True` | Generate node summaries |
| `add_node_id` | `bool` | `True` | Assign node IDs |
| `add_doc_description` | `bool` | `False` | Generate document description |
| `add_node_text` | `bool` | `False` | Store full text in nodes |

**Properties:**

- `effective_retrieve_model: str` - Returns `retrieve_model` if set, otherwise `model`.

---

## load_config

```python
from reasontree import load_config

def load_config(
    overrides: dict | None = None,
    config_path: Path | None = None,
) -> ReasonTreeConfig
```

Load and validate configuration.

**Parameters:**

- `overrides`: Dict of values to override YAML defaults. `None` values within the dict are silently ignored.
- `config_path`: Path to an alternative YAML configuration file. Defaults to the bundled `config.yaml`.

---

## Low-level functions

These are exported for programmatic use but most callers should use `ReasonTreeClient` instead.

### build_tree_from_pdf

```python
from reasontree.index import build_tree_from_pdf

def build_tree_from_pdf(pdf_path: str, config: ReasonTreeConfig) -> dict
```

### build_tree_from_markdown

```python
from reasontree.index_md import build_tree_from_markdown

async def build_tree_from_markdown(md_path: str, config: ReasonTreeConfig) -> dict
```

### tree_search

```python
from reasontree.retrieve import tree_search

def tree_search(
    tree: dict,
    file_path: str,
    query: str,
    context: str | None = None,
    model: str = "gpt-4o-2024-11-20",
) -> RetrievalResult
```
