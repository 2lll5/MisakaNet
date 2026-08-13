"""Retrieval configuration for BM25/vector hybrid search.

The loader intentionally accepts the small YAML subset used by MisakaNet's
configuration files and has no runtime dependency on PyYAML.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class RetrievalConfig:
    """Weights used when combining normalized BM25 and vector scores."""

    bm25_weight: float = 0.5
    vector_weight: float = 0.5

    def __post_init__(self) -> None:
        for name, value in (("bm25_weight", self.bm25_weight), ("vector_weight", self.vector_weight)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"{name} must be a number")
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.bm25_weight + self.vector_weight <= 0:
            raise ValueError("bm25_weight and vector_weight cannot both be zero")


def _parse_scalar(value: str) -> float:
    value = value.split("#", 1)[0].strip().strip("\"'")
    return float(value)


def load_retrieval_config(path: str | Path | None = None) -> RetrievalConfig:
    """Load ``retrieval.bm25_weight`` and ``retrieval.vector_weight``.

    ``MISAKANET_CONFIG`` takes precedence when no path is supplied. Missing
    files and missing keys use the balanced 0.5/0.5 defaults.
    """
    if path is None:
        path = os.environ.get("MISAKANET_CONFIG", str(REPO_ROOT / "config.yaml"))
    path = Path(path)
    if not path.exists():
        return RetrievalConfig()

    values: dict[str, float] = {}
    in_retrieval = False
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        stripped = raw_line.strip()
        if not raw_line.startswith((" ", "\t")):
            in_retrieval = stripped == "retrieval:"
            continue
        if not in_retrieval or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        if key.strip() in {"bm25_weight", "vector_weight"}:
            values[key.strip()] = _parse_scalar(value)

    return RetrievalConfig(
        bm25_weight=values.get("bm25_weight", 0.5),
        vector_weight=values.get("vector_weight", 0.5),
    )
