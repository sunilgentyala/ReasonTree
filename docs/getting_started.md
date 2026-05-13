# Getting Started with ReasonTree

This guide walks through installing ReasonTree, indexing your first document, and running a query. It assumes you have Python 3.10 or newer and a working OpenAI API key (or access to another LiteLLM-compatible provider).

---

## Installation

Clone the repo and install it as a package:

```bash
git clone https://github.com/sunilgentyala/ReasonTree.git
cd ReasonTree
pip install -e .
```

The `-e` flag installs in editable mode, which means changes you make to the source are immediately reflected without reinstalling.

If you only want the runtime dependencies and not the dev tools, use:

```bash
pip install -r requirements.txt
```

---

## Set Up Your API Key

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
```

ReasonTree loads this file automatically on import via `python-dotenv`. Alternatively, export the variable in your shell:

```bash
export OPENAI_API_KEY=your_key_here
```

If you want to use a different provider, set the appropriate key (for example `ANTHROPIC_API_KEY`) and pass the model name in LiteLLM format when you construct the client.

---

## Index Your First Document

### Via the command line

```bash
python -m reasontree index --input /path/to/your/document.pdf
```

The tree structure is saved to `./results/document_tree.json`. You can inspect it with any JSON viewer.

### Via Python

```python
from reasontree import ReasonTreeClient

client = ReasonTreeClient()
doc_id = client.index("annual_report.pdf")
print(f"Indexed. doc_id: {doc_id}")
```

---

## Run a Query

### Via the command line

```bash
python -m reasontree retrieve \
  --index ./results/annual_report_tree.json \
  --query "What are the primary sources of credit risk?"
```

Add `--show-reasoning` to print the full decision trail:

```bash
python -m reasontree retrieve \
  --index ./results/annual_report_tree.json \
  --query "What were the capital expenditures in 2023?" \
  --show-reasoning
```

### Via Python

```python
result = client.retrieve(doc_id, "What are the primary sources of credit risk?")

print("Pages retrieved:", result.pages)
print()
print("Content:")
print(result.content)
print()
print("Reasoning trail:")
for step in result.reasoning:
    print(step)
```

---

## Index a Markdown File

```bash
python -m reasontree index --input /path/to/doc.md --mode markdown
```

Markdown indexing uses heading levels as the tree structure, which is faster and cheaper than PDF indexing because the LLM is called only for summary generation, not for structure detection.

---

## Persist a Workspace

When you index many documents, use a workspace directory to persist them across sessions:

```python
client = ReasonTreeClient(workspace="~/.reasontree/my_project")

# First session: index documents
doc_id_1 = client.index("report_2023.pdf")
doc_id_2 = client.index("report_2024.pdf")

# Later sessions: the client reloads from disk automatically
client2 = ReasonTreeClient(workspace="~/.reasontree/my_project")
result = client2.retrieve(doc_id_1, "What changed between the two years?")
```

---

## Choose Your Model

Override the default model at the client level:

```python
client = ReasonTreeClient(
    model="gpt-4o",
    retrieve_model="gpt-4o-mini",  # cheaper model for retrieval
)
```

Use a different provider:

```python
import os
os.environ["ANTHROPIC_API_KEY"] = "your_key"

client = ReasonTreeClient(model="anthropic/claude-opus-4-7")
```

---

## Next Steps

- Read `docs/how_it_works.md` to understand the tree search algorithm in detail.
- See `docs/configuration.md` for the full list of config options.
- Look at `artifacts/examples/sample_output_tree.json` to understand what the tree structure looks like for a real document.
- Check `docs/troubleshooting.md` if something is not working as expected.
