# Authors and Contributors

## Creator

**Sunil Gentyala** — Independent researcher and engineer. Conceived, designed, and built ReasonTree as a research project exploring structured, reasoning-based document retrieval as an alternative to vector similarity search.

## Core Development

This project was developed as an independent research and engineering effort, building on the published work from VectifyAI's PageIndex framework and drawing from a body of literature on structured document retrieval and agentic LLM systems.

## Standing on Shoulders

ReasonTree would not exist without the following public contributions from the broader research community:

**VectifyAI / PageIndex** (https://github.com/VectifyAI/PageIndex)
The original open-source framework that demonstrated tree-based, vectorless document indexing. ReasonTree extends this work with a complete test suite, formal packaging, structured documentation, type annotations throughout the source, and additional configuration and deployment tooling. The core tree-building and retrieval logic draws from the concepts published by Mingtian Zhang, Yu Tang, and the PageIndex team.

**FinanceBench** (Starling AI / Marqueeq)
The public benchmark dataset used to measure retrieval accuracy on financial documents. FinanceBench provides 150 expert-authored QA pairs over real SEC filings, which makes it well-suited for evaluating systems that claim to handle professional documents.

**LiteLLM** (BerriAI)
The provider-routing library that makes it practical to write LLM-agnostic application code. Without LiteLLM, every provider integration would require its own adapter.

**PyMuPDF** (Artifex Software)
High-quality PDF text extraction that handles more complex layouts than the baseline PyPDF2, used in the enhanced extraction path.

## How to Contribute

If you improve the framework and want credit here, open a pull request. The bar is: working code, passing tests, and a clear explanation of what you changed and why. See CONTRIBUTING.md for the full process.
