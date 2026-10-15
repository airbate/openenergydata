"""Parquet I/O, hashing and manifest handling for the unified oed format."""
from __future__ import annotations

import hashlib
import json
from importlib import resources
from pathlib import Path

import pandas as pd
from jsonschema import Draft202012Validator

CHANNEL_COLUMNS = ["timestamp", "power_w", "quality"]


def write_channel_parquet(df: pd.DataFrame, path: Path) -> None:
    """Write one channel in the unified physical layout.

    Columns: timestamp (UTC-aware), power_w (float64), quality (int32 bitmask).
    """
    missing = set(CHANNEL_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"channel dataframe missing columns: {sorted(missing)}")
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df[CHANNEL_COLUMNS].copy()
    tz = getattr(out["timestamp"].dt, "tz", None)
    if tz is None or str(tz) != "UTC":
        raise ValueError(f"timestamp must be UTC-aware datetime, got {out['timestamp'].dtype}")
    out["timestamp"] = out["timestamp"].dt.as_unit("us")
    out["power_w"] = out["power_w"].astype("float64")
    out["quality"] = out["quality"].astype("int32")
    out.to_parquet(path, index=False, engine="pyarrow", compression="zstd")


def read_channel_parquet(path: Path) -> pd.DataFrame:
    df = pd.read_parquet(path, engine="pyarrow")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_schema() -> dict:
    ref = resources.files("oed").joinpath("schema/oed-manifest-v1.schema.json")
    return json.loads(ref.read_text(encoding="utf-8"))


def validate_manifest(manifest: dict) -> list[str]:
    """Return a list of validation error strings; empty list means valid."""
    validator = Draft202012Validator(manifest_schema())
    return [f"{'/'.join(str(p) for p in e.absolute_path)}: {e.message}"
            for e in sorted(validator.iter_errors(manifest), key=str)]


def write_manifest(manifest: dict, output_dir: Path, filename: str = "dataset.oed.json") -> Path:
    errors = validate_manifest(manifest)
    if errors:
        raise ValueError("manifest failed schema validation:\n" + "\n".join(errors))
    path = output_dir / filename
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_manifest(output_dir: Path, filename: str = "dataset.oed.json") -> dict:
    return json.loads((output_dir / filename).read_text(encoding="utf-8"))
