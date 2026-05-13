"""
Multi-provider: use any LiteLLM-compatible model with ReasonTree.

ReasonTree routes all LLM calls through LiteLLM, so switching providers
requires only changing the model name and the corresponding API key env var.

Supported providers (and their model name format):
    OpenAI:    gpt-4o-2024-11-20, gpt-4o-mini
    Anthropic: anthropic/claude-opus-4-7, anthropic/claude-sonnet-4-6
    Google:    gemini/gemini-2.0-flash, gemini/gemini-1.5-pro
    Azure:     azure/<your-deployment-name>
    Ollama:    ollama/llama3, ollama/mistral  (no API key needed)

Usage:
    # OpenAI
    OPENAI_API_KEY=sk-... python examples/03_multi_provider.py \
        --pdf doc.pdf --query "..." --model gpt-4o-mini

    # Anthropic Claude
    ANTHROPIC_API_KEY=sk-ant-... python examples/03_multi_provider.py \
        --pdf doc.pdf --query "..." --model anthropic/claude-sonnet-4-6

    # Ollama (local, free)
    python examples/03_multi_provider.py \
        --pdf doc.pdf --query "..." --model ollama/llama3
"""

import argparse

from reasontree import ReasonTreeClient


def main() -> None:
    parser = argparse.ArgumentParser(description="ReasonTree with multiple LLM providers")
    parser.add_argument("--pdf", required=True, help="Path to a PDF file")
    parser.add_argument("--query", required=True, help="Retrieval query")
    parser.add_argument("--model", required=True, help="LiteLLM model name (see docstring)")
    parser.add_argument(
        "--retrieve-model",
        default=None,
        help="Separate model for retrieval (optional — defaults to --model)",
    )
    args = parser.parse_args()

    client = ReasonTreeClient(
        model=args.model,
        retrieve_model=args.retrieve_model,
        workspace="./workspace",
    )

    print(f"Provider/model: {args.model}")
    print(f"Indexing {args.pdf} ...")
    doc_id = client.index(args.pdf)

    print(f"\nQuery: {args.query}")
    result = client.retrieve(doc_id, args.query)

    print(f"Pages: {result.pages}")
    print(f"\nContent (first 1000 chars):\n{result.content[:1000]}")


if __name__ == "__main__":
    main()
