"""
Markdown knowledge base: index a directory of Markdown files and query across them.

Useful for documentation sites, wikis, or any structured Markdown corpus.
Each file is indexed separately; queries are run against a specified file.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/04_markdown_knowledge_base.py \
        --dir ./docs --query "How do I configure the model?"
"""

import argparse
from pathlib import Path

from reasontree import ReasonTreeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Index a Markdown knowledge base")
    parser.add_argument("--dir", required=True, help="Directory containing .md files")
    parser.add_argument("--query", required=True, help="Query to run against all indexed files")
    parser.add_argument("--model", default="gpt-4o-2024-11-20", help="LiteLLM model name")
    args = parser.parse_args()

    md_files = list(Path(args.dir).rglob("*.md"))
    if not md_files:
        print(f"No .md files found in {args.dir}")
        return

    client = ReasonTreeClient(model=args.model, workspace="./workspace")

    print(f"Indexing {len(md_files)} Markdown files from {args.dir} ...\n")
    doc_ids: dict[str, str] = {}
    for md_file in md_files:
        print(f"  {md_file.name}")
        doc_id = client.index(str(md_file))
        doc_ids[md_file.name] = doc_id

    print(f"\nQuery: {args.query}\n")
    for filename, doc_id in doc_ids.items():
        result = client.retrieve(doc_id, args.query)
        if result.pages:
            print(f"[{filename}] relevant sections found:")
            print(f"  {result.content[:400]}\n")
        else:
            print(f"[{filename}] nothing relevant\n")


if __name__ == "__main__":
    main()
