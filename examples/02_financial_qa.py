"""
Financial document QA: run a batch of questions against a 10-K or 10-Q filing.

Mirrors the FinanceBench evaluation setup. Each question is answered by
passing the retrieved pages to a separate answer-generation LLM call.

Usage:
    export OPENAI_API_KEY=sk-...
    python examples/02_financial_qa.py --pdf annual_report.pdf
"""

import argparse

from reasontree import ReasonTreeClient
from reasontree.utils import llm_completion

SAMPLE_QUESTIONS = [
    "What were the total revenues for the most recent fiscal year?",
    "What are the primary risk factors disclosed in this filing?",
    "What was the net income compared to the prior year?",
    "What is the company's liquidity position and available credit facilities?",
    "Are there any material pending legal proceedings?",
]


def answer_question(client: ReasonTreeClient, doc_id: str, question: str, model: str) -> dict:
    result = client.retrieve(doc_id, question)

    if not result.content:
        return {"question": question, "answer": "No relevant content found.", "pages": []}

    prompt = f"""You are a financial analyst. Answer the question using only the provided document excerpts.
Be specific. Cite page numbers where possible.

Question: {question}

Document excerpts:
{result.content[:6000]}

Answer:"""

    answer = llm_completion(model=model, prompt=prompt)
    return {"question": question, "answer": answer, "pages": result.pages}


def main() -> None:
    parser = argparse.ArgumentParser(description="Financial document QA")
    parser.add_argument("--pdf", required=True, help="Path to a 10-K or 10-Q PDF")
    parser.add_argument("--model", default="gpt-4o-2024-11-20", help="LiteLLM model name")
    args = parser.parse_args()

    client = ReasonTreeClient(model=args.model, workspace="./workspace")

    print(f"Indexing {args.pdf} ...")
    doc_id = client.index(args.pdf)

    print(f"\nRunning {len(SAMPLE_QUESTIONS)} questions...\n")
    for i, question in enumerate(SAMPLE_QUESTIONS, 1):
        print(f"[{i}/{len(SAMPLE_QUESTIONS)}] {question}")
        qa = answer_question(client, doc_id, question, args.model)
        print(f"  Pages: {qa['pages']}")
        print(f"  Answer: {qa['answer'][:300]}\n")


if __name__ == "__main__":
    main()
