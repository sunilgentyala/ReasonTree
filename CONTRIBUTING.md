# Contributing to ReasonTree

Thank you for considering a contribution. This document covers the process from finding something to work on through getting a change merged.

---

## The general rule

Open an issue before writing code for anything non-trivial. This avoids the common frustration of building something carefully and then learning it conflicts with existing plans or was already rejected for a reason that is not obvious from the code.

For typos, broken links, and other small fixes, just open a PR directly.

---

## Setting up your development environment

```bash
git clone https://github.com/sunilgentyala/ReasonTree.git
cd ReasonTree
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

This installs the package in editable mode plus all development dependencies: pytest, pytest-cov, pytest-asyncio, mypy, and ruff.

---

## Running the tests

```bash
pytest tests/ -v
```

All 54 tests should pass. If any test is failing before you make changes, open an issue.

---

## Code style

The project uses ruff for linting and formatting. Run it before committing:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

The line length limit is 100 characters. Target Python version is 3.10.

---

## Type checking

All new code should be fully type-annotated. Run mypy before opening a PR:

```bash
mypy src/reasontree/
```

The goal is zero mypy errors.

---

## Writing tests

Every new function should have at least one test. Tests for LLM-dependent code should mock the LLM calls; the project should not require a live API key to run the test suite.

Tests live in `tests/`. Follow the class-per-component pattern you see in the existing test files. Fixtures go in `conftest.py`.

---

## Commit messages

Write a subject line that completes the sentence "This commit will...". Keep it under 72 characters. Add a blank line and then a body if the change needs explanation that is not obvious from the diff.

Good:
```
Fix out-of-range index handling in _select_children
```

Too vague:
```
Fix bug
```

---

## Opening a pull request

1. Fork the repo and create a branch from `main`.
2. Make your changes.
3. Add or update tests.
4. Run `pytest` and `mypy` and confirm both pass.
5. Run `ruff check` and fix any issues.
6. Open a PR with a clear description of what changed and why.

---

## Reporting security issues

Do not open a public issue for security vulnerabilities. See `SECURITY.md` for the disclosure process.
