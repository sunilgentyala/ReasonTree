# Troubleshooting

Common problems and how to fix them.

---

## "No module named reasontree"

You either haven't installed the package yet, or you installed it in a different virtual environment than the one currently active.

```bash
pip install -e .
```

Run this from the project root (the directory that contains `pyproject.toml`).

---

## "API key not found" or authentication errors

Check that your API key is set:

```bash
echo $OPENAI_API_KEY
```

If the output is empty, either export it in your shell or create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
```

ReasonTree loads `.env` files automatically on import.

---

## The tree is mostly flat, with no hierarchy

This happens when the PDF has no machine-readable table of contents and the LLM-based segmentation groups all content into large chunks. A few things to try:

1. **Reduce `max_pages_per_node`.** Smaller chunks force more splits:
   ```python
   client = ReasonTreeClient()
   client.config.max_pages_per_node = 5
   ```

2. **Increase `toc_check_pages`.** Some documents have a TOC that appears further into the front matter:
   ```python
   client.config.toc_check_pages = 40
   ```

3. **Use a better-structured source.** If the PDF is a scanned image or was created without proper structure tagging, neither TOC detection nor content segmentation will work well. Converting the source document to a text-layer PDF first usually helps.

---

## Retrieval returns irrelevant pages

This usually means the LLM navigator made a wrong turn somewhere in the tree. Check `result.reasoning` to see exactly where:

```python
result = client.retrieve(doc_id, "your query")
for step in result.reasoning:
    print(step)
```

Common causes:

- **Node summaries are low quality.** If summaries don't accurately describe their section, the navigator can't make good decisions. Index the document with a better model for the `model` parameter.
- **Query is too vague.** A query like "risks" will cause the navigator to explore many branches. Try "What are the counterparty credit risks disclosed in the risk factors section?"
- **Missing context.** If this is a follow-up question in a conversation, pass the conversation history as the `context` argument.

---

## Indexing is very slow

Indexing calls the LLM for each node in the tree. The number of LLM calls scales with the number of nodes, and the number of nodes scales with document length and `max_pages_per_node`.

To speed up indexing:

1. **Disable summaries** (saves one LLM call per node, at the cost of retrieval quality):
   ```python
   config = ReasonTreeConfig(add_node_summary=False)
   client = ReasonTreeClient(config=config)
   ```

2. **Use a faster, cheaper model** for indexing:
   ```python
   client = ReasonTreeClient(model="gpt-4o-mini", retrieve_model="gpt-4o")
   ```
   This uses the faster model for indexing and the stronger model only for retrieval.

3. **Index once, reuse.** Indexing is a one-time cost per document. Use a workspace to persist the result:
   ```python
   client = ReasonTreeClient(workspace="~/.reasontree/my_workspace")
   doc_id = client.index("large_document.pdf")
   # Next time, the client reloads from the workspace automatically
   ```

---

## PyPDF2 extracts garbled text from my PDF

PyPDF2 and PyMuPDF both depend on the PDF having a proper text layer. If your PDF was created by scanning a paper document without OCR, or if it uses unusual font encoding, the extracted text may be garbled.

Options:

1. Pre-process the PDF with an OCR tool (such as Adobe Acrobat, Tesseract, or a commercial OCR service) before indexing.
2. Convert the PDF to Markdown manually or with a document conversion tool, then index the Markdown file.
3. For Markdown files, the quality depends entirely on the quality of the text, not on PDF parsing.

---

## "JSONDecodeError" during indexing

The LLM occasionally produces malformed JSON, especially for documents with unusual formatting that results in unusual prompt content. ReasonTree handles this by returning empty fallback values rather than raising, so a JSON error during indexing usually shows up as missing titles or summaries rather than a crash.

If you see this frequently, it may mean the document content is confusing the LLM. Try:
- Switching to a more capable model
- Reducing `max_pages_per_node` so each prompt contains less content
- Checking whether the PDF contains a lot of non-text content (tables, images) that is being passed as garbled text to the prompt

---

## Tests are failing

Run the tests with verbose output:

```bash
pytest tests/ -v
```

If specific test classes are failing, check whether the relevant dependency is installed. All test dependencies are in the `dev` extras:

```bash
pip install -e ".[dev]"
```

Async tests require `pytest-asyncio`. Check that it is installed:

```bash
pip show pytest-asyncio
```
