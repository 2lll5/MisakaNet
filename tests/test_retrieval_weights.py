"""Tests for configurable BM25/vector retrieval weights."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from misakanet.search.config import RetrievalConfig, load_retrieval_config
from misakanet.search.engine import CachedDoc, _rank_docs_impl


def test_retrieval_config_defaults(tmp_path):
    assert load_retrieval_config(tmp_path / "missing.yaml") == RetrievalConfig()


def test_retrieval_config_reads_nested_yaml(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("retrieval:\n  bm25_weight: 0.8\n  vector_weight: 0.2\n", encoding="utf-8")
    assert load_retrieval_config(path) == RetrievalConfig(0.8, 0.2)


def test_retrieval_config_rejects_invalid_weights():
    with pytest.raises(ValueError):
        RetrievalConfig(-0.1, 1.1)
    with pytest.raises(ValueError):
        RetrievalConfig(0, 0)


def test_ranker_accepts_explicit_keyword_only_weights(monkeypatch):
    docs = [
        CachedDoc("a.md", Path("lessons/contrib/a.md"), "alpha beta"),
        CachedDoc("b.md", Path("lessons/contrib/b.md"), "alpha gamma"),
    ]
    monkeypatch.setattr(
        "misakanet.search.engine._compute_vector_scores",
        lambda query, docs: [0.0, 1.0],
    )
    ranked = _rank_docs_impl("alpha", docs, bm25_weight=1.0, vector_weight=0.0)
    assert ranked[0][1].filename == "a.md"