"""Configuration loading and validation for ReasonTree."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, model_validator


class ReasonTreeConfig(BaseModel):
    """Validated configuration for a ReasonTree run.

    All fields have defaults drawn from config.yaml. Override at construction
    time or via environment. Pass ``model_override`` to replace the model for
    both indexing and retrieval in one shot.
    """

    model: str = Field(default="gpt-4o-2024-11-20", description="LLM used for indexing.")
    retrieve_model: Optional[str] = Field(
        default=None,
        description="LLM used for retrieval. Falls back to ``model`` when not set.",
    )
    toc_check_pages: int = Field(
        default=20,
        ge=1,
        description="How many pages to scan for an existing table of contents.",
    )
    max_pages_per_node: int = Field(
        default=10,
        ge=1,
        description="Maximum page span a single tree node may cover.",
    )
    max_tokens_per_node: int = Field(
        default=20000,
        ge=100,
        description="Token ceiling for text within a single node.",
    )
    add_node_summary: bool = Field(
        default=True,
        description="Whether to generate a short summary for each node.",
    )
    add_node_id: bool = Field(
        default=True,
        description="Whether to assign a stable ID to each node.",
    )
    add_doc_description: bool = Field(
        default=False,
        description="Whether to generate a top-level document description.",
    )
    add_node_text: bool = Field(
        default=False,
        description="Whether to include extracted text in each node.",
    )

    @model_validator(mode="after")
    def set_retrieve_model_default(self) -> "ReasonTreeConfig":
        if self.retrieve_model is None:
            self.retrieve_model = self.model
        return self

    @property
    def effective_retrieve_model(self) -> str:
        return self.retrieve_model or self.model


_DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(
    overrides: Optional[dict] = None,
    config_path: Optional[Path] = None,
) -> ReasonTreeConfig:
    """Load configuration from YAML, then apply any caller-supplied overrides.

    Args:
        overrides: Key-value pairs that override YAML defaults. ``None`` values
            within the dict are silently ignored so callers can pass argparse
            namespaces without filtering.
        config_path: Path to an alternative YAML file. Defaults to the bundled
            ``config.yaml`` next to this module.

    Returns:
        A fully validated :class:`ReasonTreeConfig` instance.
    """
    path = config_path or _DEFAULT_CONFIG_PATH
    base: dict = {}
    if path.exists():
        with path.open() as fh:
            base = yaml.safe_load(fh) or {}

    if overrides:
        clean = {k: v for k, v in overrides.items() if v is not None}
        base.update(clean)

    return ReasonTreeConfig(**base)
