"""Command-line interface for ReasonTree."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reasontree",
        description="Reasoning-based document retrieval using hierarchical tree indexing.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- index ---
    idx = sub.add_parser("index", help="Index a PDF or Markdown document.")
    idx.add_argument("--input", "-i", required=True, help="Path to the document.")
    idx.add_argument("--output", "-o", default="./results", help="Output directory.")
    idx.add_argument("--model", help="LLM for indexing (overrides config).")
    idx.add_argument("--mode", choices=["auto", "pdf", "markdown"], default="auto")

    # --- retrieve ---
    ret = sub.add_parser("retrieve", help="Run a retrieval query.")
    ret.add_argument("--index", "-i", required=True, help="Path to the tree JSON file.")
    ret.add_argument("--query", "-q", required=True, help="The query to run.")
    ret.add_argument("--context", "-c", help="Optional extra context.")
    ret.add_argument("--model", help="LLM for retrieval (overrides config).")
    ret.add_argument("--show-reasoning", action="store_true", help="Print the decision trail.")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "index":
        _cmd_index(args)
    elif args.command == "retrieve":
        _cmd_retrieve(args)


def _cmd_index(args: argparse.Namespace) -> None:
    from reasontree import ReasonTreeClient

    overrides = {}
    if args.model:
        overrides["model"] = args.model

    client = ReasonTreeClient(**overrides)
    doc_id = client.index(args.input, mode=args.mode)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{Path(args.input).stem}_tree.json"

    tree = client.get_tree(doc_id, strip_text=False)
    with out_file.open("w") as fh:
        json.dump(tree, fh, indent=2, ensure_ascii=False)

    print(f"Tree saved to: {out_file}")


def _cmd_retrieve(args: argparse.Namespace) -> None:
    from reasontree.retrieve import tree_search
    from reasontree.config import load_config

    tree_path = Path(args.index)
    if not tree_path.exists():
        print(f"Tree file not found: {tree_path}", file=sys.stderr)
        sys.exit(1)

    with tree_path.open() as fh:
        tree = json.load(fh)

    overrides = {}
    if args.model:
        overrides["retrieve_model"] = args.model
    config = load_config(overrides or None)

    # The retrieve command needs the original PDF path embedded in the tree
    # or passed via environment. If running standalone, try the path field.
    file_path = tree.get("path", "")

    result = tree_search(
        tree=tree,
        file_path=file_path,
        query=args.query,
        context=args.context,
        model=config.effective_retrieve_model,
    )

    print(f"\nRetrieved pages: {result.pages}")
    print(f"\n--- Content ---\n{result.content}")

    if args.show_reasoning:
        print("\n--- Reasoning trail ---")
        for step in result.reasoning:
            print(json.dumps(step, indent=2))


if __name__ == "__main__":
    main()
