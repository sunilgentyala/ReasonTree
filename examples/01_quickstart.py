"""
Quickstart: index a PDF and run a retrieval query.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/01_quickstart.py --pdf /path/to/document.pdf --query "Your question"
"""

import argparse
import json

from reasontree import ReasonTreeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="ReasonTree quickstart")
    parser.add_argument("--pdf", required=True, help="Path to a PDF file")
    parser.add_argument("--query", required=True, help="Question to ask")
    parser.add_argument("--model", default="gpt-4o-2024-11-20", help="LiteLLM model name")
    parser.add_argument("--workspace", default="./workspace", help="Directory to persist index")
    args = parser.parse_args()

    client = ReasonTreeClient(model=args.model, workspace=args.workspace)

    print(f"Indexing {args.pdf} ...")
    doc_id = client.index(args.pdf)

    print(f"\nQuerying: {args.query}")
    result = client.retrieve(doc_id, args.query)

    print(f"\nPages retrieved: {result.pages}")
    print("\nReasoning trail:")
    for step in result.reasoning:
        print(f"  {json.dumps(step, indent=2)}")

    print(f"\nContent:\n{result.content[:2000]}")


if __name__ == "__main__":
    main()
