# Release Notes

All notable changes to ReasonTree are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/). Versions follow semantic versioning.

---

## [1.1.0] - 2026-05-12

### Added

- `ReasonTreeConfig` Pydantic model replaces the previous `SimpleNamespace`-based config, adding field validation at load time. Invalid values (zero or negative page counts, empty model names) now raise immediately on startup rather than failing silently during retrieval.
- `load_config()` function provides a clean public API for loading and merging configuration from YAML and caller overrides.
- Full type annotations on all public functions and most internal helpers. The codebase now passes `mypy --strict` with the exception of third-party library stubs.
- Test suite: 54 unit tests covering config validation, utility functions, Markdown parsing, tree search logic, and the client API. All tests run without network access via LLM mocks.
- `tests/results/` directory with the test run output and coverage report from the 2026-05-12 test session (91% overall coverage).
- `pyproject.toml` for standard Python packaging. The package can now be installed with `pip install -e .` and the `reasontree` command is available after installation.
- `docs/` directory with local documentation: getting started guide, how it works, configuration reference, API reference, and troubleshooting guide.
- `about/` directory with project background (`ABOUT.md`), design decision records (`DESIGN.md`), and author/contributor attribution (`AUTHORS.md`).
- `artifacts/` directory with benchmark results (`financebench_results.json`, `retrieval_accuracy.csv`), sample tree and retrieval outputs, and an architecture diagram.
- GitHub Actions CI workflow (`ci.yml`) running tests and mypy on Python 3.10, 3.11, and 3.12.
- `CONTRIBUTING.md` with contribution guidelines.
- `SECURITY.md` with the security disclosure policy.

### Changed

- Config YAML keys renamed to be consistent with Python attribute names: `toc_check_page_num` -> `toc_check_pages`, `if_add_node_summary` -> `add_node_summary`, etc. The old YAML format is not forward-compatible.
- `PageIndexClient` renamed to `ReasonTreeClient`. The public API is otherwise equivalent.
- `page_index.py` renamed to `index.py`, `page_index_md.py` renamed to `index_md.py`, moving to a cleaner naming scheme.
- `extract_json()` now handles both plain JSON responses and JSON wrapped in markdown code fences (triple backtick blocks), which is a common LLM output pattern.
- `llm_completion()` and `llm_acompletion()` now log at `WARNING` level on each retry attempt rather than printing to stdout.

### Fixed

- Out-of-range indices returned by the LLM in `_select_children()` are now silently filtered rather than causing an `IndexError`.
- Empty string handling in `count_tokens()` now returns 0 rather than calling LiteLLM with an empty payload.
- `remove_fields()` now operates on a deep copy so it does not mutate the original tree dict.

---

## [1.0.0] - 2026-04-01

Initial release. Core functionality ported and extended from the VectifyAI PageIndex open-source framework.

### Added

- PDF tree indexing via TOC detection or LLM-based content segmentation.
- Markdown tree indexing using heading levels.
- Tree search retrieval with LLM-guided navigation.
- `PageIndexClient` (now `ReasonTreeClient`) high-level API.
- CLI via `run_pageindex.py` (now `python -m reasontree`).
- LiteLLM integration for multi-provider support.
- Workspace persistence for indexed documents.
- Example: agentic vectorless RAG with OpenAI Agents SDK.
- MIT License.
