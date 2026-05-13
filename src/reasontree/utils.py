"""Shared utilities: LLM wrappers, token counting, JSON extraction, PDF helpers."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

import litellm
import pymupdf
import PyPDF2
from dotenv import load_dotenv

load_dotenv()

# Support legacy key name used by some deployment environments.
if not os.getenv("OPENAI_API_KEY") and os.getenv("CHATGPT_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.getenv("CHATGPT_API_KEY")  # type: ignore[arg-type]

litellm.drop_params = True

logger = logging.getLogger(__name__)

_MAX_RETRIES = 10
_RETRY_DELAY_SECONDS = 1.0


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """Return an approximate token count for ``text`` using LiteLLM's counter."""
    if not text:
        return 0
    return litellm.token_counter(model=model, text=text)


def _strip_provider_prefix(model: str) -> str:
    """Remove the 'litellm/' prefix that some callers add."""
    return model.removeprefix("litellm/") if model else model


def llm_completion(
    model: str,
    prompt: str,
    chat_history: Optional[list[dict[str, str]]] = None,
    return_finish_reason: bool = False,
) -> str | tuple[str, str]:
    """Synchronous LLM call with automatic retry on transient errors.

    Args:
        model: LiteLLM model identifier.
        prompt: The user message to send.
        chat_history: Optional list of prior messages in OpenAI format.
        return_finish_reason: When ``True``, returns ``(content, reason)`` where
            reason is ``"finished"``, ``"max_output_reached"``, or ``"error"``.

    Returns:
        The response text, or a ``(text, reason)`` tuple if requested.
    """
    model = _strip_provider_prefix(model)
    messages: list[dict[str, str]] = list(chat_history or [])
    messages.append({"role": "user", "content": prompt})

    for attempt in range(_MAX_RETRIES):
        try:
            response = litellm.completion(model=model, messages=messages, temperature=0)
            content: str = response.choices[0].message.content or ""
            if return_finish_reason:
                raw_reason = response.choices[0].finish_reason
                reason = "max_output_reached" if raw_reason == "length" else "finished"
                return content, reason
            return content
        except Exception as exc:
            logger.warning("LLM call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY_SECONDS)

    logger.error("All %d retries exhausted for prompt: %.120s", _MAX_RETRIES, prompt)
    return ("", "error") if return_finish_reason else ""


async def llm_acompletion(model: str, prompt: str) -> str:
    """Async LLM call with automatic retry on transient errors."""
    model = _strip_provider_prefix(model)
    messages = [{"role": "user", "content": prompt}]

    for attempt in range(_MAX_RETRIES):
        try:
            response = await litellm.acompletion(model=model, messages=messages, temperature=0)
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning("Async LLM call failed (attempt %d/%d): %s", attempt + 1, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES - 1:
                await asyncio.sleep(_RETRY_DELAY_SECONDS)

    logger.error("All %d retries exhausted.", _MAX_RETRIES)
    return ""


def extract_json(text: str) -> dict[str, Any]:
    """Extract the first JSON object found in ``text``.

    Handles LLM responses that wrap JSON in markdown code fences or include
    explanatory text before the opening brace.

    Returns an empty dict when no valid JSON is found.
    """
    # Try stripping markdown fences first.
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1)
    else:
        # Fall back to the first `{...}` block in the response.
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        candidate = brace_match.group(0) if brace_match else ""

    if not candidate:
        return {}

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        logger.debug("JSON extraction failed for text: %.200s", text)
        return {}


def get_pdf_page_count(path: str | Path) -> int:
    """Return the number of pages in a PDF without loading all content."""
    with open(path, "rb") as fh:
        reader = PyPDF2.PdfReader(fh)
        return len(reader.pages)


def extract_pdf_text(path: str | Path) -> list[tuple[str, int]]:
    """Extract text from every page of a PDF using PyMuPDF.

    Returns a list of ``(page_text, page_number)`` tuples, 1-indexed.
    """
    doc = pymupdf.open(str(path))
    results: list[tuple[str, int]] = []
    for i, page in enumerate(doc, start=1):
        results.append((page.get_text(), i))
    doc.close()
    return results


def remove_fields(obj: Any, fields: list[str]) -> Any:
    """Recursively remove the given keys from a nested dict/list structure.

    Returns a deep copy with the named fields removed.
    """
    import copy
    obj = copy.deepcopy(obj)

    def _strip(node: Any) -> Any:
        if isinstance(node, dict):
            for f in fields:
                node.pop(f, None)
            for v in node.values():
                _strip(v)
        elif isinstance(node, list):
            for item in node:
                _strip(item)
        return node

    return _strip(obj)
