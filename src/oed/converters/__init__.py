"""Converter registry. One module per source dataset."""
from __future__ import annotations

from pathlib import Path
from typing import Protocol


class Converter(Protocol):
    """A converter turns one source dataset directory into the unified
    oed layout (Parquet channels + Croissant-compatible manifest)."""

    dataset_id: str
    source_url: str
    source_license: str
    citation: str

    def convert(self, input_dir: Path, output_dir: Path) -> Path:
        ...


def _register() -> dict[str, Converter]:
    from oed.converters import redd

    instances = [redd.ReddConverter()]
    return {c.dataset_id: c for c in instances}


CONVERTERS: dict[str, Converter] = _register()
